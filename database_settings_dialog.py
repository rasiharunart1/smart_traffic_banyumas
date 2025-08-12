import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Any
from config import settings_manager

class DatabaseSettingsDialog:
    def __init__(self, parent, db_handler):
        self.parent = parent
        self.db_handler = db_handler
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Database Settings")
        self.dialog.configure(bg="#2d2d2d")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.result = None
        cur = settings_manager.settings["database"].copy()

        self.var_type = tk.StringVar(value=cur.get("type", "sqlite"))
        self.var_sqlite_path = tk.StringVar(value=cur.get("sqlite_path", "traffic_counts.db"))
        self.var_host = tk.StringVar(value=cur.get("host", "localhost"))
        self.var_port = tk.IntVar(value=int(cur.get("port", 3306)))
        self.var_user = tk.StringVar(value=cur.get("user", "root"))
        self.var_password = tk.StringVar(value=cur.get("password", ""))
        self.var_database = tk.StringVar(value=cur.get("database", "traffic_db"))
        self.var_auto_save = tk.IntVar(value=int(cur.get("auto_save_interval_sec", 0)))

        frm = tk.Frame(self.dialog, bg="#2d2d2d")
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="DB Type:").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(frm, textvariable=self.var_type, values=["sqlite", "mysql", "postgresql"], state="readonly")
        cb.grid(row=0, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self._toggle_fields())

        self.sqlite_row = tk.Frame(frm, bg="#2d2d2d")
        self.sqlite_row.grid(row=1, column=0, columnspan=3, sticky="ew", pady=4)
        ttk.Label(self.sqlite_row, text="SQLite File:").pack(side=tk.LEFT)
        ttk.Entry(self.sqlite_row, textvariable=self.var_sqlite_path, width=30).pack(side=tk.LEFT, padx=6)
        ttk.Button(self.sqlite_row, text="Browse", command=self.pick_sqlite).pack(side=tk.LEFT)

        ttk.Label(frm, text="Host:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_host).grid(row=2, column=1, sticky="ew")

        ttk.Label(frm, text="Port:").grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_port).grid(row=3, column=1, sticky="ew")

        ttk.Label(frm, text="User:").grid(row=4, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_user).grid(row=4, column=1, sticky="ew")

        ttk.Label(frm, text="Password:").grid(row=5, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_password, show="*").grid(row=5, column=1, sticky="ew")

        ttk.Label(frm, text="Database:").grid(row=6, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_database).grid(row=6, column=1, sticky="ew")

        ttk.Label(frm, text="Auto-save (sec, 0=off):").grid(row=7, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_auto_save).grid(row=7, column=1, sticky="ew")

        btns = tk.Frame(frm, bg="#2d2d2d")
        btns.grid(row=8, column=0, columnspan=3, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="Test Connection", command=self.test_connection).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.RIGHT)

        frm.columnconfigure(1, weight=1)
        self._toggle_fields()

    def _toggle_fields(self):
        t = self.var_type.get()
        show_sqlite = (t == "sqlite")
        self.sqlite_row.grid() if show_sqlite else self.sqlite_row.grid_remove()

    def pick_sqlite(self):
        path = filedialog.asksaveasfilename(title="SQLite file", defaultextension=".db", filetypes=[("SQLite DB", "*.db"), ("All Files", "*.*")])
        if path:
            self.var_sqlite_path.set(path)

    def _collect(self) -> Dict[str, Any]:
        return {
            "type": self.var_type.get(),
            "sqlite_path": self.var_sqlite_path.get(),
            "host": self.var_host.get(),
            "port": int(self.var_port.get()),
            "user": self.var_user.get(),
            "password": self.var_password.get(),
            "database": self.var_database.get(),
            "auto_save_interval_sec": int(self.var_auto_save.get())
        }

    def test_connection(self):
        cfg = self._collect()
        ok, msg = self.db_handler.test_connection(cfg)
        if ok:
            messagebox.showinfo("Connection", msg, parent=self.dialog)
        else:
            messagebox.showerror("Connection", msg, parent=self.dialog)

    def on_save(self):
        cfg = self._collect()
        self.db_handler.apply_settings_and_reconnect(cfg)
        self.dialog.destroy()