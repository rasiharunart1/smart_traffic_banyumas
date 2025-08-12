import threading
import time
import os
import sys
import sqlite3
import csv
import datetime as dt
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Set

import cv2
import numpy as np
import mss
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Ultralytics YOLO
try:
    from ultralytics import YOLO
except ImportError as e:
    raise SystemExit("Ultralytics belum terpasang. Jalankan: pip install ultralytics") from e

try:
    import torch
except ImportError:
    torch = None

# Local modules
from region_selector import select_region_interactive
from tracking import SimpleTracker, Track
from db import Database


VEHICLE_CLASSES_DEFAULT: Set[str] = {"bicycle", "car", "motorcycle", "bus", "train", "truck"}


@dataclass
class AppState:
    # Configurable
    weights: str = "yolo11n.pt"
    conf: float = 0.25
    device: str = "auto"  # 'auto' | 'cpu' | 'cuda'
    all_classes: bool = False
    enabled_classes: Set[str] = field(default_factory=lambda: set(VEHICLE_CLASSES_DEFAULT))
    region: Optional[Tuple[int, int, int, int]] = None  # (left, top, width, height)

    # Line
    line_points: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None  # ((x1,y1),(x2,y2))
    line_name: str = "Line A"

    # Runtime
    running: bool = False
    paused: bool = False
    stop_event: threading.Event = field(default_factory=threading.Event)
    reload_model_event: threading.Event = field(default_factory=threading.Event)
    edit_line_mode: bool = False

    # Counters
    count_a2b: int = 0
    count_b2a: int = 0

    # Internal
    window_title: str = "Vehicle Counter - Screen Region"
    fps: float = 0.0


class VehicleCounterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YOLO11 Vehicle Counter (Screen Region)")
        self.state = AppState()

        # UI Vars
        self.var_weights = tk.StringVar(value=self.state.weights)
        self.var_conf = tk.DoubleVar(value=self.state.conf)
        self.var_device = tk.StringVar(value=self.state.device)
        self.var_all_classes = tk.BooleanVar(value=self.state.all_classes)
        self.var_line_name = tk.StringVar(value=self.state.line_name)
        self.var_region_text = tk.StringVar(value="Belum dipilih")
        self.var_a2b = tk.IntVar(value=0)
        self.var_b2a = tk.IntVar(value=0)
        self.var_fps = tk.StringVar(value="0.0")

        # Class checkboxes
        self.class_names_default = ["bicycle", "car", "motorcycle", "bus", "train", "truck"]
        self.class_vars: Dict[str, tk.BooleanVar] = {n: tk.BooleanVar(value=(n in self.state.enabled_classes)) for n in self.class_names_default}

        # Model and processing
        self.model: Optional[YOLO] = None
        self.model_device: str = "cpu"
        self.frame_size: Tuple[int, int] = (640, 480)
        self.monitor = None
        self.sct = None
        self.tracker = SimpleTracker(max_missing=20, max_dist=80.0)

        # DB
        self.db = Database(db_path="vehicle_counter.db")
        self._build_ui()

        # OpenCV line edit helpers
        self._cv_mouse_down = False
        self._cv_line_p1 = None  # type: Optional[Tuple[int, int]]
        self._cv_line_p2 = None  # type: Optional[Tuple[int, int]]

        # Thread
        self.thread: Optional[threading.Thread] = None

    def _build_ui(self):
        # Top frame for settings
        frm = ttk.Frame(self.root, padding=8)
        frm.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Weights path
        row = 0
        ttk.Label(frm, text="Weights (.pt):").grid(row=row, column=0, sticky="w")
        ent_weights = ttk.Entry(frm, textvariable=self.var_weights, width=42)
        ent_weights.grid(row=row, column=1, sticky="we", padx=4)
        ttk.Button(frm, text="Browse", command=self._browse_weights).grid(row=row, column=2, sticky="w")

        # Confidence
        row += 1
        ttk.Label(frm, text="Confidence:").grid(row=row, column=0, sticky="w")
        scl_conf = ttk.Scale(frm, from_=0.05, to=0.85, variable=self.var_conf, command=lambda e: None)
        scl_conf.grid(row=row, column=1, sticky="we", padx=4)
        ttk.Label(frm, textvariable=self.var_conf, width=5).grid(row=row, column=2, sticky="w")

        # Device
        row += 1
        ttk.Label(frm, text="Device:").grid(row=row, column=0, sticky="w")
        cmb_device = ttk.Combobox(frm, textvariable=self.var_device, values=["auto", "cpu", "cuda"], state="readonly", width=8)
        cmb_device.grid(row=row, column=1, sticky="w", padx=4)

        # Classes
        row += 1
        chk_all = ttk.Checkbutton(frm, text="Tampilkan semua kelas", variable=self.var_all_classes, command=self._on_toggle_all_classes)
        chk_all.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        classes_frame = ttk.Frame(frm)
        classes_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 8))
        for i, cname in enumerate(self.class_names_default):
            cb = ttk.Checkbutton(classes_frame, text=cname, variable=self.class_vars[cname], command=self._on_class_change)
            cb.grid(row=0, column=i, sticky="w", padx=2)
        self._update_class_check_state()

        # Region select
        row += 1
        ttk.Label(frm, text="Region:").grid(row=row, column=0, sticky="w")
        ttk.Label(frm, textvariable=self.var_region_text).grid(row=row, column=1, sticky="w")
        ttk.Button(frm, text="Pilih Region", command=self._select_region).grid(row=row, column=2, sticky="w")

        # Line
        row += 1
        ttk.Label(frm, text="Line Name:").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_line_name, width=20).grid(row=row, column=1, sticky="w", padx=4)
        ttk.Button(frm, text="Edit Line (di jendela video)", command=self._enable_edit_line).grid(row=row, column=2, sticky="w")

        # Start/Stop buttons
        row += 1
        self.btn_start = ttk.Button(frm, text="Start", command=self._start)
        self.btn_start.grid(row=row, column=0, sticky="we", pady=(6, 0))
        self.btn_stop = ttk.Button(frm, text="Stop", command=self._stop, state="disabled")
        self.btn_stop.grid(row=row, column=1, sticky="we", pady=(6, 0))
        ttk.Button(frm, text="Export CSV", command=self._export_csv).grid(row=row, column=2, sticky="we", pady=(6, 0))

        # Counters and FPS
        row += 1
        stats = ttk.Frame(frm)
        stats.grid(row=row, column=0, columnspan=3, sticky="we", pady=8)
        ttk.Label(stats, text="A -> B:").grid(row=0, column=0, sticky="e")
        ttk.Label(stats, textvariable=self.var_a2b, width=6).grid(row=0, column=1, sticky="w")
        ttk.Label(stats, text="B -> A:").grid(row=0, column=2, sticky="e")
        ttk.Label(stats, textvariable=self.var_b2a, width=6).grid(row=0, column=3, sticky="w")
        ttk.Label(stats, text="FPS:").grid(row=0, column=4, sticky="e", padx=(16, 0))
        ttk.Label(stats, textvariable=self.var_fps, width=6).grid(row=0, column=5, sticky="w")

        # Hint
        row += 1
        hint = ttk.Label(frm, text="Hotkeys (jendela video): q=quit, p=pause, l=edit line", foreground="#555")
        hint.grid(row=row, column=0, columnspan=3, sticky="w")

        for c in range(3):
            frm.columnconfigure(c, weight=1)

    def _browse_weights(self):
        path = filedialog.askopenfilename(title="Pilih file weights .pt", filetypes=[("PyTorch Weights", "*.pt"), ("Semua File", "*.*")])
        if path:
            self.var_weights.set(path)

    def _select_region(self):
        self._stop_if_running()
        messagebox.showinfo("Pilih Region", "Setelah menekan OK, pilih area layar dengan drag dan lepas (ESC untuk batal).")
        region = select_region_interactive()
        if region:
            self.state.region = region
            l, t, w, h = region
            self.var_region_text.set(f"{l},{t},{w},{h}")
        else:
            self.var_region_text.set("Belum dipilih")

    def _enable_edit_line(self):
        if not self.state.running:
            messagebox.showinfo("Info", "Mulai dulu (Start). Setelah jendela video terbuka, tekan tombol ini lalu gambar garis dengan dua klik.")
        self.state.edit_line_mode = True

    def _on_toggle_all_classes(self):
        self.state.all_classes = self.var_all_classes.get()
        self._update_class_check_state()

    def _on_class_change(self):
        enabled = {name for name, var in self.class_vars.items() if var.get()}
        self.state.enabled_classes = enabled

    def _update_class_check_state(self):
        all_classes = self.var_all_classes.get()
        for name, var in self.class_vars.items():
            state = "disabled" if all_classes else "normal"
            var.set(True if (all_classes or name in self.state.enabled_classes) else False)
            # Disable/enable checkboxes
            # We get the Checkbutton widget via grid_slaves if needed; simplified: state managed logically.

    def _stop_if_running(self):
        if self.state.running:
            self._stop()
            # wait a tiny for thread
            self.root.update()
            time.sleep(0.2)

    def _start(self):
        if self.state.region is None:
            messagebox.showwarning("Region belum dipilih", "Silakan pilih region layar terlebih dahulu.")
            return
        # Apply settings to state
        self.state.weights = self.var_weights.get().strip()
        self.state.conf = float(self.var_conf.get())
        self.state.device = self.var_device.get()
        self.state.line_name = self.var_line_name.get().strip() or "Line A"
        self.state.count_a2b = 0
        self.state.count_b2a = 0
        self.var_a2b.set(0)
        self.var_b2a.set(0)
        self.state.stop_event.clear()
        self.state.running = True
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

        # Start processing thread
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _stop(self):
        if not self.state.running:
            return
        self.state.stop_event.set()
        self.state.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _export_csv(self):
        dest = filedialog.asksaveasfilename(title="Simpan CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not dest:
            return
        try:
            self.db.export_csv(dest)
            messagebox.showinfo("Sukses", f"Data diekspor ke {dest}")
        except Exception as e:
            messagebox.showerror("Gagal ekspor", str(e))

    def _resolve_device(self, requested: str) -> str:
        if requested == "auto":
            if torch is not None and hasattr(torch, "cuda") and torch.cuda.is_available():
                return "cuda"
            return "cpu"
        if requested not in ("cpu", "cuda"):
            return "cpu"
        if requested == "cuda":
            if torch is None or not torch.cuda.is_available():
                print("Peringatan: CUDA diminta tetapi tidak tersedia. Menggunakan CPU.")
                return "cpu"
        return requested

    def _load_model(self):
        device = self._resolve_device(self.state.device)
        if self.model is None or self.model_device != device or self.model.ckpt_path != self.state.weights:
            print(f"Memuat model: {self.state.weights} pada device: {device}")
            self.model = YOLO(self.state.weights)
            try:
                self.model.to(device)
            except Exception as e:
                print(f"Peringatan: gagal memindahkan model ke device '{device}': {e}")
            self.model_device = device

        # Names
        try:
            self.model_names = self.model.model.names
        except Exception:
            self.model_names = None

    def _run_loop(self):
        # Setup capture
        left, top, width, height = self.state.region
        self.frame_size = (width, height)
        self.sct = mss.mss()
        self.monitor = {"left": left, "top": top, "width": width, "height": height}

        self._load_model()

        cv2.namedWindow(self.state.window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.state.window_title, width, height)
        cv2.setMouseCallback(self.state.window_title, self._cv_mouse_handler)

        last_time = time.time()
        alpha = 0.9
        paused = False

        # Tracker state across frames
        self.tracker.reset()
        # Per-track side-of-line state for crossing detection
        track_side: Dict[int, int] = {}  # track_id -> side sign (-1, 0, +1)

        print("Hotkeys (jendela video): q=quit, p=pause, l=edit line")
        while not self.state.stop_event.is_set():
            if not paused:
                img = np.array(self.sct.grab(self.monitor))  # BGRA
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Inference
                results = self.model.predict(source=frame, conf=self.state.conf, verbose=False, device=0 if self.model_device == "cuda" else None)
                annotated = frame.copy()

                dets = []
                cls_names = []
                confs = []

                if results and len(results) > 0:
                    r = results[0]
                    boxes = getattr(r, "boxes", None)
                    names_map = getattr(r, "names", self.model_names)
                    if boxes is not None and names_map is not None:
                        xyxy = boxes.xyxy
                        conf_arr = boxes.conf
                        cls_arr = boxes.cls
                        if xyxy is not None and conf_arr is not None and cls_arr is not None:
                            xyxy = xyxy.detach().cpu().numpy()
                            conf_arr = conf_arr.detach().cpu().numpy()
                            cls_arr = cls_arr.detach().cpu().numpy().astype(int)
                            for (x1, y1, x2, y2), c, cls_id in zip(xyxy, conf_arr, cls_arr):
                                name = names_map.get(int(cls_id), str(cls_id)) if isinstance(names_map, dict) else str(cls_id)
                                if not self.state.all_classes:
                                    if name not in self.state.enabled_classes:
                                        continue
                                dets.append([x1, y1, x2, y2])
                                cls_names.append(name)
                                confs.append(float(c))

                # Update tracker
                tracks: List[Track] = self.tracker.update(dets, labels=cls_names, confs=confs)

                # Draw detections and tracks
                for tr in tracks:
                    x1, y1, x2, y2 = map(int, tr.bbox)
                    cx, cy = map(int, tr.centroid)
                    color = (0, 255, 0)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    label = f"ID {tr.id} {tr.label} {tr.conf:.2f}"
                    self._draw_label(annotated, label, x1, max(0, y1 - 5), color)

                    # Crossing logic if line exists
                    if self.state.line_points is not None:
                        (lx1, ly1), (lx2, ly2) = self.state.line_points
                        # Draw previous trajectory segment
                        if tr.prev_centroid is not None:
                            pcx, pcy = map(int, tr.prev_centroid)
                            cv2.line(annotated, (pcx, pcy), (cx, cy), (255, 255, 0), 1)
                            # Check crossing
                            crossed, direction = self._check_crossing((pcx, pcy), (cx, cy), (lx1, ly1), (lx2, ly2))
                            if crossed:
                                # To avoid multiple counts due to jitter, ensure side changed and not re-counted same frame
                                prev_side = self._point_side((pcx, pcy), (lx1, ly1), (lx2, ly2))
                                curr_side = self._point_side((cx, cy), (lx1, ly1), (lx2, ly2))
                                if prev_side != 0 and curr_side != 0 and prev_side != curr_side:
                                    # Count event
                                    if direction > 0:
                                        self.state.count_a2b += 1
                                        self.var_a2b.set(self.state.count_a2b)
                                        dlabel = "A->B"
                                    else:
                                        self.state.count_b2a += 1
                                        self.var_b2a.set(self.state.count_b2a)
                                        dlabel = "B->A"
                                    # Log to DB
                                    self.db.insert_crossing(
                                        ts=dt.datetime.utcnow().isoformat(),
                                        line_name=self.state.line_name,
                                        direction=dlabel,
                                        cls=tr.label,
                                        track_id=tr.id,
                                        conf=tr.conf,
                                    )
                                    # Visual marker
                                    cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), 2)

                # Draw counting line
                if self.state.line_points is not None:
                    (lx1, ly1), (lx2, ly2) = self.state.line_points
                    cv2.line(annotated, (lx1, ly1), (lx2, ly2), (0, 0, 255), 2)
                    # A and B endpoints
                    cv2.circle(annotated, (lx1, ly1), 5, (0, 255, 255), -1)
                    cv2.circle(annotated, (lx2, ly2), 5, (255, 0, 255), -1)
                    self._draw_label(annotated, f"{self.state.line_name} (A)", lx1 + 6, ly1 + 6, (0, 255, 255))
                    self._draw_label(annotated, f"{self.state.line_name} (B)", lx2 + 6, ly2 + 6, (255, 0, 255))

                # HUD
                hud_lines = [
                    f"FPS: {self.state.fps:.1f}",
                    f"Conf: {self.state.conf:.2f}",
                    f"Classes: {'ALL' if self.state.all_classes else ','.join(sorted(self.state.enabled_classes))}",
                    f"A->B: {self.state.count_a2b}  B->A: {self.state.count_b2a}",
                    f"Hotkeys: q=quit p=pause l=edit-line",
                ]
                y0 = 20
                for i, text in enumerate(hud_lines):
                    cv2.putText(annotated, text, (10, y0 + 20 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

                cv2.imshow(self.state.window_title, annotated)

                # FPS update
                now = time.time()
                inst_fps = 1.0 / max(1e-6, (now - last_time))
                self.state.fps = alpha * self.state.fps + (1 - alpha) * inst_fps
                last_time = now
                self.var_fps.set(f"{self.state.fps:.1f}")
            else:
                # paused: still need to keep window responsive
                cv2.waitKey(10)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.state.stop_event.set()
                break
            elif key == ord('p'):
                paused = not paused
            elif key == ord('l'):
                self.state.edit_line_mode = True

        cv2.destroyAllWindows()
        self.state.running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _draw_label(self, img, text, x, y, color=(0, 255, 0), font_scale=0.5, thickness=1):
        (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        cv2.rectangle(img, (x, y - h - baseline), (x + w, y + baseline), color, -1)
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

    def _cv_mouse_handler(self, event, x, y, flags, userdata):
        if not self.state.edit_line_mode:
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            self._cv_mouse_down = True
            if self._cv_line_p1 is None:
                self._cv_line_p1 = (x, y)
            else:
                self._cv_line_p2 = (x, y)
                # Finish line
                if self._cv_line_p1 != self._cv_line_p2:
                    self.state.line_points = (self._cv_line_p1, self._cv_line_p2)
                    self.state.edit_line_mode = False
                    self._cv_line_p1 = None
                    self._cv_line_p2 = None
                    print(f"Garis ditetapkan: {self.state.line_points} (A->B)")
                else:
                    # reset if same point
                    self._cv_line_p1 = None
                    self._cv_line_p2 = None
        elif event == cv2.EVENT_MOUSEMOVE and self._cv_mouse_down:
            # Optional: live preview
            pass
        elif event == cv2.EVENT_LBUTTONUP:
            self._cv_mouse_down = False

    def _point_side(self, p, a, b) -> int:
        # sign of cross product (b-a) x (p-a)
        ax, ay = a
        bx, by = b
        px, py = p
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if abs(cross) < 1e-6:
            return 0
        return 1 if cross > 0 else -1

    def _segments_intersect(self, p1, p2, q1, q2) -> bool:
        def orient(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        def on_segment(a, b, c):
            # c on segment ab
            return min(a[0], b[0]) - 1e-6 <= c[0] <= max(a[0], b[0]) + 1e-6 and \
                   min(a[1], b[1]) - 1e-6 <= c[1] <= max(a[1], b[1]) + 1e-6
        o1 = orient(p1, p2, q1)
        o2 = orient(p1, p2, q2)
        o3 = orient(q1, q2, p1)
        o4 = orient(q1, q2, p2)
        if (o1 * o2 < 0) and (o3 * o4 < 0):
            return True
        # Colinear cases
        if abs(o1) < 1e-6 and on_segment(p1, p2, q1): return True
        if abs(o2) < 1e-6 and on_segment(p1, p2, q2): return True
        if abs(o3) < 1e-6 and on_segment(q1, q2, p1): return True
        if abs(o4) < 1e-6 and on_segment(q1, q2, p2): return True
        return False

    def _check_crossing(self, prev_pt, curr_pt, a, b) -> Tuple[bool, int]:
        # direction: +1 if prev on right and curr on left (A->B based on side change), else -1
        crossed = self._segments_intersect(prev_pt, curr_pt, a, b)
        if not crossed:
            return False, 0
        prev_side = self._point_side(prev_pt, a, b)
        curr_side = self._point_side(curr_pt, a, b)
        if prev_side == curr_side:
            return False, 0
        direction = 1 if (prev_side < curr_side) else -1  # arbitrary but consistent
        return True, direction


def main():
    root = tk.Tk()
    app = VehicleCounterApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app._stop(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()