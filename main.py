from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import time, threading, sys, signal

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timestamps.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Timestamp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Models:
    def __init__(self):
        self.stop_event_add = threading.Event()
        self.stop_event_delete = threading.Event()

    def create_app(self):
        with app.app_context():
            db.create_all()

    def add_timestamp(self):
        while not self.stop_event_add.is_set():
            with app.app_context():
                timestamp = Models()
                db.session.add(timestamp)
                db.session.commit()
            time.sleep(5)

    def delete_old_timestamps(self):
        while not self.stop_event_delete.is_set():
            with app.app_context():
                threshold = datetime.utcnow() - timedelta(minutes=1)
                Timestamp.query.filter(Timestamp.timestamp < threshold).delete()
                db.session.commit()
            time.sleep(10)

    def start_threads(self):
        first_thread = threading.Thread(target=self.add_timestamp)
        second_thread = threading.Thread(target=self.delete_old_timestamps)
        first_thread.start()
        second_thread.start()
        first_thread.join()
        second_thread.join()

    def signal_handler(self, sign, frame):
        self.stop_event_add.set()
        self.stop_event_delete.set()
        print("Threads stopped")
        sys.exit(0)


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

if __name__ == '__main__':
    manager_class = Models()
    signal.signal(signal.SIGINT, manager_class.signal_handler)
    signal.signal(signal.SIGTERM, manager_class.signal_handler)
    manager_class.create_app()
    manager_class.start_threads()
    app.run(debug=True)
