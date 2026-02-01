import json
from datetime import datetime

class Logger:
    def __init__(self, db):
        self.db = db

    def log(self, action, message="", data=None):
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_json = json.dumps(data, ensure_ascii=False) if data else None

        self.db.cursor.execute(
            """
            INSERT INTO logs (action, message, data_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (action, message, data_json, created_at)
        )
        self.db.conn.commit()