import os
import json
import shutil
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from tkinter import filedialog, messagebox

try:
    import pymysql  # optional
except Exception:
    pymysql = None

try:
    import psycopg2  # optional
except Exception:
    psycopg2 = None

from config import settings_manager


class DatabaseHandler:
    def __init__(self, status_callback=None):
        self.conn = None
        self.connected = False
        self.status_callback = status_callback
        self.connect()  # try initial connect

    @property
    def db_type(self):
        return settings_manager.settings["database"]["type"]

    def connect(self):
        self.close_connection()
        cfg = settings_manager.settings["database"]
        try:
            if cfg["type"] == "sqlite":
                self.conn = sqlite3.connect(cfg["sqlite_path"], check_same_thread=False)
                self._init_sqlite()
                self.connected = True
            elif cfg["type"] == "mysql":
                if pymysql is None:
                    raise RuntimeError("pymysql not installed")
                self.conn = pymysql.connect(
                    host=cfg["host"],
                    port=int(cfg["port"]),
                    user=cfg["user"],
                    password=cfg["password"],
                    database=cfg["database"],
                    autocommit=True,
                )
                self._init_generic()
                self.connected = True
            elif cfg["type"] == "postgresql":
                if psycopg2 is None:
                    raise RuntimeError("psycopg2 not installed")
                self.conn = psycopg2.connect(
                    host=cfg["host"],
                    port=int(cfg["port"]),
                    user=cfg["user"],
                    password=cfg["password"],
                    dbname=cfg["database"],
                )
                self.conn.autocommit = True
                self._init_generic()
                self.connected = True
            else:
                raise ValueError("Unsupported database type")
        except Exception:
            self.conn = None
            self.connected = False
        finally:
            if self.status_callback:
                self.status_callback(self.connected)

    def close_connection(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = None
        self.connected = False

    def _init_sqlite(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                up_json TEXT NOT NULL,
                down_json TEXT NOT NULL,
                total_up INTEGER NOT NULL,
                total_down INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def _init_generic(self):
        # create table if not exists in MySQL/PostgreSQL (JSON as TEXT for portability)
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS counts (
                id SERIAL PRIMARY KEY,
                created_at VARCHAR(32) NOT NULL,
                up_json TEXT NOT NULL,
                down_json TEXT NOT NULL,
                total_up INT NOT NULL,
                total_down INT NOT NULL
            )
            """
        )
        try:
            self.conn.commit()
        except Exception:
            pass

    def test_connection(self, tmp_cfg: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            if tmp_cfg["type"] == "sqlite":
                test = sqlite3.connect(tmp_cfg["sqlite_path"])
                test.close()
                return True, "SQLite OK"
            elif tmp_cfg["type"] == "mysql":
                if pymysql is None:
                    return False, "pymysql not installed"
                c = pymysql.connect(
                    host=tmp_cfg["host"],
                    port=int(tmp_cfg["port"]),
                    user=tmp_cfg["user"],
                    password=tmp_cfg["password"],
                    database=tmp_cfg["database"],
                )
                c.close()
                return True, "MySQL OK"
            elif tmp_cfg["type"] == "postgresql":
                if psycopg2 is None:
                    return False, "psycopg2 not installed"
                c = psycopg2.connect(
                    host=tmp_cfg["host"],
                    port=int(tmp_cfg["port"]),
                    user=tmp_cfg["user"],
                    password=tmp_cfg["password"],
                    dbname=tmp_cfg["database"],
                )
                c.close()
                return True, "PostgreSQL OK"
            else:
                return False, "Unsupported DB type"
        except Exception as e:
            return False, f"Failed: {e}"

    def apply_settings_and_reconnect(self, new_cfg: Dict[str, Any]):
        settings_manager.settings["database"].update(new_cfg)
        settings_manager.save()
        self.connect()

    def save_counts(
        self,
        up: Dict[str, int],
        down: Dict[str, int],
        total_up: int,
        total_down: int,
        root=None,
    ):
        if not self.connected or self.conn is None:
            raise RuntimeError("Database not connected")

        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        up_json = json.dumps(up)
        down_json = json.dumps(down)

        cur = self.conn.cursor()
        if settings_manager.settings["database"]["type"] == "sqlite":
            cur.execute(
                "INSERT INTO counts (created_at, up_json, down_json, total_up, total_down) VALUES (?, ?, ?, ?, ?)",
                (created_at, up_json, down_json, int(total_up), int(total_down)),
            )
            self.conn.commit()
        else:
            cur.execute(
                "INSERT INTO counts (created_at, up_json, down_json, total_up, total_down) VALUES (%s, %s, %s, %s, %s)",
                (created_at, up_json, down_json, int(total_up), int(total_down)),
            )
            try:
                self.conn.commit()
            except Exception:
                pass
        if root:
            messagebox.showinfo("Saved", "Counts saved to database successfully!", parent=root)

    def fetch_counts(
        self,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        sort_col: str = "created_at",
        sort_dir: str = "DESC",
    ) -> Tuple[List[Dict[str, Any]], int]:
        if not self.connected or self.conn is None:
            return [], 0
        offset = (page - 1) * page_size

        base_query = "SELECT id, created_at, up_json, down_json, total_up, total_down FROM counts"
        where = ""
        params: List[Any] = []
        if search:
            if settings_manager.settings["database"]["type"] == "sqlite":
                where = " WHERE created_at LIKE ? OR up_json LIKE ? OR down_json LIKE ?"
                like = f"%{search}%"
                params.extend([like, like, like])
            else:
                where = " WHERE created_at ILIKE %s OR up_json ILIKE %s OR down_json ILIKE %s"
                like = f"%{search}%"
                params.extend([like, like, like])

        order = f" ORDER BY {sort_col} {sort_dir}"
        limit = (
            " LIMIT ? OFFSET ?"
            if settings_manager.settings["database"]["type"] == "sqlite"
            else " LIMIT %s OFFSET %s"
        )

        cur = self.conn.cursor()
        query = base_query + where + order + limit

        if settings_manager.settings["database"]["type"] == "sqlite":
            cur.execute(query, (*params, page_size, offset))
        else:
            cur.execute(query, (*params, page_size, offset))

        rows = cur.fetchall()
        data: List[Dict[str, Any]] = []
        for r in rows:
            rid, created_at, up_json, down_json, tu, td = r
            try:
                up = json.loads(up_json)
                down = json.loads(down_json)
            except Exception:
                up, down = {}, {}
            data.append(
                {
                    "id": rid,
                    "created_at": created_at,
                    "up": up,
                    "down": down,
                    "total_up": tu,
                    "total_down": td,
                }
            )

        if where:
            count_query = "SELECT COUNT(1) FROM counts" + where
            cur2 = self.conn.cursor()
            if settings_manager.settings["database"]["type"] == "sqlite":
                cur2.execute(count_query, (*params,))
            else:
                cur2.execute(count_query, (*params,))
            total = cur2.fetchone()[0]
        else:
            cur2 = self.conn.cursor()
            cur2.execute("SELECT COUNT(1) FROM counts")
            total = cur2.fetchone()[0]
        return data, int(total)

    def delete_rows(self, ids: List[int]):
        if not ids or self.conn is None:
            return
        cur = self.conn.cursor()
        placeholders = (
            ",".join(["?"] * len(ids))
            if self.db_type == "sqlite"
            else ",".join(["%s"] * len(ids))
        )
        q = f"DELETE FROM counts WHERE id IN ({placeholders})"
        cur.execute(q, ids)
        try:
            self.conn.commit()
        except Exception:
            pass

    def backup_database(self, root=None):
        cfg = settings_manager.settings["database"]
        if cfg["type"] != "sqlite":
            messagebox.showinfo("Backup", "Backup is only implemented for SQLite in this app.", parent=root)
            return
        src = cfg["sqlite_path"]
        if not os.path.exists(src):
            messagebox.showwarning("Backup", "No SQLite database file found.", parent=root)
            return
        dest = filedialog.asksaveasfilename(
            parent=root,
            title="Save SQLite Backup",
            defaultextension=".db",
            filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")],
        )
        if not dest:
            return
        shutil.copy2(src, dest)
        messagebox.showinfo("Backup", f"Database backed up to:\n{dest}", parent=root)

    def restore_database(self, root=None):
        cfg = settings_manager.settings["database"]
        if cfg["type"] != "sqlite":
            messagebox.showinfo("Restore", "Restore is only implemented for SQLite in this app.", parent=root)
            return
        src = filedialog.askopenfilename(
            parent=root, title="Select SQLite Backup", filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")]
        )
        if not src:
            return
        dest = cfg["sqlite_path"]
        self.close_connection()
        shutil.copy2(src, dest)
        self.connect()
        messagebox.showinfo("Restore", f"Database restored from:\n{src}", parent=root)