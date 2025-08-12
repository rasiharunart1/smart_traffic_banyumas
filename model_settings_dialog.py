import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import torch

class ModelSettingsDialog:
    def __init__(self, parent, current_model_cfg: dict):
        self.parent = parent
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Model Settings")
        self.dialog.configure(bg="#2d2d2d")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.result = None

        self.var_model_path = tk.StringVar(value=current_model_cfg.get("model_path", "yolo-Weights/yolo11n.pt"))
        self.var_conf = tk.DoubleVar(value=float(current_model_cfg.get("confidence_threshold", 0.35)))
        self.var_iou = tk.DoubleVar(value=float(current_model_cfg.get("iou_threshold", 0.45)))
        self.var_device = tk.StringVar(value=current_model_cfg.get("device", "cpu"))
        self.var_det_conf = tk.DoubleVar(value=float(current_model_cfg.get("detection_confidence", 0.35)))

        frm = tk.Frame(self.dialog, bg="#2d2d2d")
        frm.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Model file
        ttk.Label(frm, text="Model File:").grid(row=0, column=0, sticky="w")
        ent = ttk.Entry(frm, textvariable=self.var_model_path)
        ent.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(frm, text="Browse", command=self.pick_model).grid(row=0, column=2, padx=6)

        # Conf
        ttk.Label(frm, text=f"Confidence ({self.var_conf.get():.2f})").grid(row=1, column=0, sticky="w")
        sc1 = ttk.Scale(frm, from_=0.1, to=1.0, orient=tk.HORIZONTAL, variable=self.var_conf, command=lambda e: self._update_label(frm, 1, 0, "Confidence", self.var_conf.get()))
        sc1.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

        # IoU
        ttk.Label(frm, text=f"IoU ({self.var_iou.get():.2f})").grid(row=2, column=0, sticky="w")
        sc2 = ttk.Scale(frm, from_=0.1, to=1.0, orient=tk.HORIZONTAL, variable=self.var_iou, command=lambda e: self._update_label(frm, 2, 0, "IoU", self.var_iou.get()))
        sc2.grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

        # Detection confidence
        ttk.Label(frm, text=f"Det. Filter ({self.var_det_conf.get():.2f})").grid(row=3, column=0, sticky="w")
        sc3 = ttk.Scale(frm, from_=0.1, to=1.0, orient=tk.HORIZONTAL, variable=self.var_det_conf, command=lambda e: self._update_label(frm, 3, 0, "Det. Filter", self.var_det_conf.get()))
        sc3.grid(row=3, column=1, columnspan=2, sticky="ew", pady=4)

        # Device
        ttk.Label(frm, text="Device:").grid(row=4, column=0, sticky="w")
        devices = ["cpu"]
        try:
            if torch.cuda.is_available():
                devices.append("cuda")
        except Exception:
            pass
        ttk.Combobox(frm, textvariable=self.var_device, values=devices, state="readonly").grid(row=4, column=1, sticky="w")

        # Buttons
        btns = tk.Frame(frm, bg="#2d2d2d")
        btns.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text="Save", command=self.on_save).pack(side=tk.RIGHT)

        frm.columnconfigure(1, weight=1)

    def _update_label(self, frm, row, col, name, val):
        for w in frm.grid_slaves(row=row, column=col):
            if isinstance(w, ttk.Label):
                w.config(text=f"{name} ({float(val):.2f})")

    def pick_model(self):
        path = filedialog.askopenfilename(
            title="Select YOLO model file",
            filetypes=[("YOLO Weights", "*.pt *.onnx"), ("All Files", "*.*")]
        )
        if path:
            self.var_model_path.set(path)

    def on_save(self):
        model_path = self.var_model_path.get().strip()
        if not model_path:
            messagebox.showwarning("Validation", "Model file must be provided.", parent=self.dialog)
            return
        self.result = {
            "model_path": model_path,
            "confidence_threshold": float(self.var_conf.get()),
            "iou_threshold": float(self.var_iou.get()),
            "detection_confidence": float(self.var_det_conf.get()),
            "device": self.var_device.get()
        }
        self.dialog.destroy()