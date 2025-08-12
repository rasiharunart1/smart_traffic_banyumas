import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import json
from typing import List, Dict, Any

class DataViewer:
    def __init__(self, parent, db_handler, start_immediately_export: bool = False):
        self.parent = parent
        self.db = db_handler
        self.win = tk.Toplevel(parent)
        self.win.title("Data Viewer")
        self.win.geometry("900x600")
        self.win.configure(bg="#2d2d2d")
        self.page = 1
        self.page_size = 25
        this_total = 0
        self.total = 0
        self.sort_col = "created_at"
        self.sort_dir = "DESC"

        ctrls = tk.Frame(self.win, bg="#2d2d2d")
        ctrls.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(ctrls, text="Search:", bg="#2d2d2d", fg="#ffffff").pack(side=tk.LEFT)
        self.var_search = tk.StringVar()
        ent = ttk.Entry(ctrls, textvariable=self.var_search, width=30)
        ent.pack(side=tk.LEFT, padx=6)
        ttk.Button(ctrls, text="Apply", command=self.reload).pack(side=tk.LEFT)

        ttk.Button(ctrls, text="Export CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrls, text="Export JSON", command=self.export_json).pack(side=tk.RIGHT, padx=4)
        ttk.Button(ctrls, text="Delete Selected", command=self.delete_selected).pack(side=tk.RIGHT, padx=4)

        cols = ("id", "created_at", "total_up", "total_down", "up", "down")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            self.tree.heading(c, text=c, command=lambda col=c: self.on_sort(col))
            self.tree.column(c, anchor="w", width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        pager = tk.Frame(self.win, bg="#2d2d2d")
        pager.pack(fill=tk.X, padx=10, pady=8)
        ttk.Button(pager, text="Prev", command=self.prev_page).pack(side=tk.LEFT)
        ttk.Button(pager, text="Next", command=self.next_page).pack(side=tk.LEFT, padx=4)
        self.page_label = tk.Label(pager, text="", bg="#2d2d2d", fg="#ffffff")
        self.page_label.pack(side=tk.LEFT, padx=8)

        self.reload()

        if start_immediately_export:
            self.export_csv()

    def on_sort(self, col):
        if self.sort_col == col:
            self.sort_dir = "ASC" if self.sort_dir == "DESC" else "DESC"
        else:
            self.sort_col = col
            self.sort_dir = "ASC"
        self.reload()

    def reload(self):
        self.tree.delete(*self.tree.get_children())
        rows, total = self.db.fetch_counts(self.page, self.page_size, self.var_search.get().strip(), self.sort_col, self.sort_dir)
        self.total = total
        for r in rows:
            self.tree.insert("", tk.END, values=(
                r["id"],
                r["created_at"],
                r["total_up"],
                r["total_down"],
                json.dumps(r["up"]),
                json.dumps(r["down"])
            ))
        last_page = max(1, (self.total + self.page_size - 1) // self.page_size)
        self.page_label.config(text=f"Page {self.page}/{last_page} • Total rows: {self.total}")

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.reload()

    def next_page(self):
        last_page = max(1, (self.total + self.page_size - 1) // self.page_size)
        if self.page < last_page:
            self.page += 1
            self.reload()

    def get_selected_ids(self) -> List[int]:
        items = self.tree.selection()
        ids = []
        for it in items:
            vals = self.tree.item(it, "values")
            if vals:
                ids.append(int(vals[0]))
        return ids

    def delete_selected(self):
        ids = self.get_selected_ids()
        if not ids:
            messagebox.showinfo("Delete", "No rows selected.", parent=self.win)
            return
        if not messagebox.askyesno("Delete", f"Delete {len(ids)} selected rows?", parent=self.win):
            return
        self.db.delete_rows(ids)
        self.reload()

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.win, title="Export CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        page = 1
        page_size = 500
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "created_at", "total_up", "total_down", "up_json", "down_json"])
            while True:
                rows, total = self.db.fetch_counts(page, page_size, self.var_search.get().strip(), self.sort_col, self.sort_dir)
                if not rows:
                    break
                for r in rows:
                    writer.writerow([r["id"], r["created_at"], r["total_up"], r["total_down"], json.dumps(r["up"]), json.dumps(r["down"])])
                if page * page_size >= total:
                    break
                page += 1
        messagebox.showinfo("Export", f"Exported to {path}", parent=self.win)

    def export_json(self):
        path = filedialog.asksaveasfilename(parent=self.win, title="Export JSON", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        page = 1
        page_size = 500
        all_rows: List[Dict[str, Any]] = []
        while True:
            rows, total = self.db.fetch_counts(page, page_size, self.var_search.get().strip(), self.sort_col, self.sort_dir)
            if not rows:
                break
            all_rows.extend(rows)
            if page * page_size >= total:
                break
            page += 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, indent=2)
        messagebox.showinfo("Export", f"Exported to {path}", parent=self.win)