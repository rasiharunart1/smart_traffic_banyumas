import sqlite3
from typing import Optional
import csv


class Database:
    def __init__(self, db_path: str = "vehicle_counter.db"):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
            CREATE TABLE IF NOT EXISTS crossings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                line_name TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('A->B','B->A')),
                class TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                conf REAL NOT NULL
            )
            """)
            conn.commit()

    def insert_crossing(self, ts: str, line_name: str, direction: str, cls: str, track_id: int, conf: float):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO crossings (ts, line_name, direction, class, track_id, conf) VALUES (?, ?, ?, ?, ?, ?)",
                (ts, line_name, direction, cls, track_id, float(conf))
            )
            conn.commit()

    def export_csv(self, csv_path: str):
        with sqlite3.connect(self.db_path) as conn, open(csv_path, "w", newline="", encoding="utf-8") as f:
            c = conn.cursor()
            c.execute("SELECT id, ts, line_name, direction, class, track_id, conf FROM crossings ORDER BY id ASC")
            writer = csv.writer(f)
            writer.writerow(["id", "ts", "line_name", "direction", "class", "track_id", "conf"])
            for row in c.fetchall():
                writer.writerow(row)