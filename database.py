# database.py


import sqlite3
import json
from datetime import datetime
from typing import List, Dict


class HistoryStorage:
    def __init__(self, db_path: str = "history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    patient_json TEXT,
                    result_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    test_id TEXT,
                    description TEXT,
                    expected TEXT,
                    actual TEXT,
                    status TEXT
                )
            """)

    def save_history(self, patient: Dict, result):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (timestamp, patient_json, result_json) VALUES (?, ?, ?)",
                (
                    datetime.now().isoformat(timespec="seconds"),
                    json.dumps(patient, ensure_ascii=False),
                    json.dumps({
                        "recommended": [d.name for d in result.recommended],
                        "excluded": result.excluded,
                        "groups": result.groups,
                        "elapsed": result.elapsed,
                    }, ensure_ascii=False),
                ),
            )

    def save_test_result(self, tc_id: str, desc: str, expected: str, actual: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO test_results (timestamp, test_id, description, expected, actual, status) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), tc_id, desc, expected, actual, status),
            )

    def get_history(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT timestamp, patient_json, result_json FROM history ORDER BY id DESC")
            return [
                {"timestamp": t, "patient": json.loads(p), "result": json.loads(r)}
                for t, p, r in cur.fetchall()
            ]

    def get_test_results(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT timestamp, test_id, description, expected, actual, status FROM test_results ORDER BY id"
            )
            return [
                {"timestamp": t, "test_id": tid, "desc": d, "expected": e, "actual": a, "status": s}
                for t, tid, d, e, a, s in cur.fetchall()
            ]