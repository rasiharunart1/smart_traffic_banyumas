import tkinter as tk
from tkinter import ttk, colorchooser

class LineSettingsDialog:
    def __init__(self, parent, current):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Line Settings")
        self.dialog.configure(bg="#2d2d2d")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.result = None

        self.var_type = tk.StringVar(value=current.get("line_type", "manual"))
        self.var_color = tk.StringVar(value=current.get("line_color", "#00d4ff"))
        self.var_thickness = tk.IntVar(value=current.get("line_thickness", 3))
        self.var_show_label = tk.BooleanVar(value=current.get("show_label", True))
        self.var_label_text = tk.StringVar(value=current.get("label_text", "COUNT LINE"))
        # New: detection band and invert direction
        self.var_band_px = tk.IntVar(value=int(current.get("band_px", 12)))
        self.var_invert_dir = tk.BooleanVar(value=bool(current.get("invert_direction", False)))

        frm = tk.Frame(self.dialog, bg="#2d2d2d")
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        ttk.Label(frm, text="Line Type:").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(frm, textvariable=self.var_type, values=["manual", "horizontal", "vertical"], state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frm, text="Line Color:").grid(row=1, column=0, sticky="w")
        color_frame = tk.Frame(frm, bg="#2d2d2d")
        color_frame.grid(row=1, column=1, sticky="w")
        self.color_btn = tk.Button(color_frame, text="Pick", command=self.pick_color, bg=self.var_color.get(), fg="#000000")
        self.color_btn.pack(side=tk.LEFT)
        ttk.Entry(color_frame, textvariable=self.var_color, width=14).pack(side=tk.LEFT, padx=6)

        ttk.Label(frm, text="Thickness:").grid(row=2, column=0, sticky="w")
        tk.Scale(frm, from_=1, to=10, orient=tk.HORIZONTAL, variable=self.var_thickness, bg="#2d2d2d", fg="#ffffff")\
            .grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(frm, text="Show Label", variable=self.var_show_label).grid(row=3, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_label_text).grid(row=3, column=1, sticky="ew")

        # Detection band and invert direction
        ttk.Label(frm, text="Detection Zone Width (px):").grid(row=4, column=0, sticky="w")
        tk.Scale(frm, from_=2, to=40, orient=tk.HORIZONTAL, variable=self.var_band_px, bg="#2d2d2d", fg="#ffffff")\
            .grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(frm, text="Invert Direction (flip UP/DOWN)", variable=self.var_invert_dir).grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btns = tk.Frame(frm, bg="#2d2d2d")
        btns.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="OK", command=self.on_ok).pack(side=tk.RIGHT)

        frm.columnconfigure(1, weight=1)

    def pick_color(self):
        c = colorchooser.askcolor(title="Choose Line Color", initialcolor=self.var_color.get())
        if c and c[1]:
            self.var_color.set(c[1])
            try:
                self.color_btn.config(bg=c[1])
            except Exception:
                pass

    def on_ok(self):
        self.result = {
            "line_type": self.var_type.get(),
            "line_color": self.var_color.get(),
            "line_thickness": int(self.var_thickness.get()),
            "show_label": bool(self.var_show_label.get()),
            "label_text": self.var_label_text.get().strip() or "COUNT LINE",
            "band_px": int(self.var_band_px.get()),
            "invert_direction": bool(self.var_invert_dir.get())
        }
        self.dialog.destroy()