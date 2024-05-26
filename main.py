from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import time, sys, threading, signal

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timestamps.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Timestamp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


def create_app():
    with app.app_context():
        db.create_all()


def add_timestamp(stop_event):
    while not stop_event.is_set():
        with app.app_context():
            timestamp = Timestamp()
            db.session.add(timestamp)
            db.session.commit()
        time.sleep(5)


def delete_old_timestamps(stop_event):
    while not stop_event.is_set():
        with app.app_context():
            threshold = datetime.utcnow() - timedelta(minutes=1)
            Timestamp.query.filter(
                Timestamp.timestamp < threshold).delete()
            db.session.commit()
        time.sleep(10)

stop_event_add = threading.Event()
stop_event_delete = threading.Event()

@app.route("/timestamps", methods=["GET"])
def get_timestamps():
    timestamps = Timestamp.query.all()
    return jsonify([
        {
            'id': stamp.id,
            'timestamp': stamp.timestamp.isoformat()
        }
        for stamp in timestamps])


@app.route("/timestamps", methods=["DELETE"])
def delete_timestamps():
    db.session.query(Timestamp).delete()
    db.session.commit()
    return "", 204

def signal_handler(sign, frame):
    stop_event_add.set()
    stop_event_delete.set()
    print("Поток остановлен")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    create_app()
    first_thread = threading.Thread(target=add_timestamp,
                                    args=(stop_event_add,),
                                    daemon=True)
    second_thread = threading.Thread(target=delete_old_timestamps,
                                     args=(stop_event_delete,),
                                     daemon=True)
    first_thread.start()
    second_thread.start()
    app.run(debug=True)
    first_thread.join()
    second_thread.join()
