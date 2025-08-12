"""
Smart Traffic Counter v3.3
- Multi-input (Screen/Webcam/Network)
- Faster screen capture via mss (fallback PIL)
- Auto CUDA + FP16
- RAW counting mode → render bbox RAW (seperti skrip) + counting aktif
- RAW-only mode → hanya render RAW (tanpa counting)
- ROI gate + class filter (saat non-RAW)
- Flush camera frames + frame locks + DPI-aware Windows
"""

import sys
import math
import time
import threading
import traceback

import cv2
cv2.setUseOptimized(True)

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageGrab
import pyautogui

# DPI awareness (Windows)
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Try MSS for faster screen capture
try:
    import mss  # noqa: F401
    HAS_MSS = True
except Exception:
    HAS_MSS = False

from ultralytics import YOLO

from config import (
    MODEL_CONFIG,
    DEFAULT_LINE_SETTINGS,
    TRACKING_CONFIG,
    CLASS_NAMES,
    VEHICLE_CLASSES,
    COLOR_CONFIG,
    settings_manager,
    RUNTIME_CONFIG,
)
from database_handler import DatabaseHandler
from line_settings_dialog import LineSettingsDialog
from model_settings_dialog import ModelSettingsDialog
from database_settings_dialog import DatabaseSettingsDialog
from data_viewer import DataViewer
from vehicle_tracker import VehicleTracker


class ModernScreenVehicleCounter:
    def __init__(self):
        self.root = tk.Tk()
        try:
            self.root.tk.call('tk', 'scaling', 1.0)
        except Exception:
            pass

        self.root.title("🚗 Smart Traffic Counter v3.3 - Modern UI")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#1e1e1e')

        self.init_variables()
        self.model = None
        self.init_yolo_model()

        self.db_handler = DatabaseHandler(self.on_db_status_changed)
        self.vehicle_tracker = VehicleTracker()

        self.setup_modern_gui()
        self.update_input_source_ui()
        self.update_preview_button_state()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def init_variables(self):
        # Input source
        self.input_cfg = settings_manager.settings["input"]
        self.input_type = self.input_cfg.get("type", "screen")
        self.stream_url = self.input_cfg.get("stream_url", "")
        self.webcam_index = self.input_cfg.get("webcam_index", 0)

        # Capture + locks
        self.cap = None
        self.cap_lock = threading.Lock()
        self.frame_lock = threading.Lock()

        # Screen region
        self.capture_region = None
        reg = self.input_cfg.get("screen_region", None)
        if reg and isinstance(reg, list) and len(reg) == 4:
            self.capture_region = tuple(reg)
        self.is_capturing = False
        self.is_previewing = False

        # MSS thread-local instance
        self.use_mss = bool(RUNTIME_CONFIG.get("use_mss_screen_capture", True)) and HAS_MSS
        self._has_mss = HAS_MSS
        self._tls = threading.local()

        # Line settings
        self.counting_line = None
        self.line_drawn = False
        self.drawing_line = False
        self.line_draw_enabled = False
        self.line_settings = DEFAULT_LINE_SETTINGS.copy()

        # Frame state
        self.current_frame = None
        self.capture_thread = None
        self.preview_thread = None

        # RAW: class names cache
        self._model_names = None

    def resolve_device(self):
        dev = MODEL_CONFIG.get('device', 'auto')
        if dev == 'auto':
            try:
                import torch  # noqa: F401
                return 'cuda' if torch.cuda.is_available() else 'cpu'
            except Exception:
                return 'cpu'
        return dev

    def init_yolo_model(self):
        try:
            self.model = YOLO(MODEL_CONFIG['model_path'])
            device = self.resolve_device()
            try:
                self.model.to(device)
                if device.startswith("cuda") and RUNTIME_CONFIG.get("use_half", True):
                    if hasattr(self.model, "model") and hasattr(self.model.model, "half"):
                        self.model.model.half()
                MODEL_CONFIG['device'] = device
                settings_manager.save()
            except Exception:
                pass
            try:
                self._model_names = self.model.model.names
            except Exception:
                self._model_names = None
            print(f"✅ YOLO loaded: {MODEL_CONFIG['model_path']} on {MODEL_CONFIG.get('device','cpu')}")
        except Exception as e:
            messagebox.showerror("Model Error", f"Failed to load YOLO model: {e}")

    def reload_yolo_model(self, new_config: dict):
        MODEL_CONFIG.update(new_config)
        settings_manager.save()
        try:
            self.model = YOLO(MODEL_CONFIG['model_path'])
            device = self.resolve_device()
            try:
                self.model.to(device)
                if device.startswith("cuda") and RUNTIME_CONFIG.get("use_half", True):
                    if hasattr(self.model, "model") and hasattr(self.model.model, "half"):
                        self.model.model.half()
                MODEL_CONFIG['device'] = device
                settings_manager.save()
            except Exception:
                pass
            try:
                self._model_names = self.model.model.names
            except Exception:
                self._model_names = None
            messagebox.showinfo("Model Reloaded", f"Model: {MODEL_CONFIG['model_path']} on {MODEL_CONFIG.get('device','cpu')}")
        except Exception as e:
            messagebox.showerror("Model Error", f"Failed to load YOLO model: {e}\n{traceback.format_exc()}")

    def setup_modern_gui(self):
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_container = tk.Frame(self.root, bg='#2d2d2d')
        main_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_container.rowconfigure(1, weight=1)
        main_container.columnconfigure(1, weight=1)

        self.create_header_bar(main_container)
        self.create_left_sidebar(main_container)
        self.create_center_video_area(main_container)
        self.create_right_sidebar(main_container)

    def on_db_status_changed(self, connected: bool):
        if hasattr(self, 'connection_status'):
            self.connection_status.config(text="🟢 DB Connected" if connected else "🔴 DB Disconnected")
        if hasattr(self, 'db_status_label'):
            self.db_status_label.config(
                text="🔌 Database: Connected" if connected else "❌ Database: Disconnected",
                fg='#28a745' if connected else '#dc3545'
            )

    def create_header_bar(self, parent):
        header_frame = tk.Frame(parent, bg='#363636', relief='raised', bd=1)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        title_frame = tk.Frame(header_frame, bg='#363636')
        title_frame.pack(side=tk.LEFT, padx=15, pady=15)
        tk.Label(title_frame, text="🚗 Smart Traffic Counter v3.3", bg='#363636', fg='#00d4ff', font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        tk.Label(title_frame, text="Real-time Vehicle Detection & Counting with AI", bg='#363636', fg='#ffffff', font=('Arial', 10)).pack(side=tk.LEFT, padx=(10, 0))

        actions = tk.Frame(header_frame, bg='#363636'); actions.pack(side=tk.LEFT, padx=20)
        tk.Button(actions, text="🤖 Model Settings", command=self.open_model_settings, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=4, padx=8).pack(side=tk.LEFT, padx=5)
        tk.Button(actions, text="💾 DB Settings", command=self.open_database_settings, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=4, padx=8).pack(side=tk.LEFT, padx=5)
        tk.Button(actions, text="📚 Data Viewer", command=self.view_reports, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=4, padx=8).pack(side=tk.LEFT, padx=5)

        status_frame = tk.Frame(header_frame, bg='#363636'); status_frame.pack(side=tk.RIGHT, padx=15, pady=15)
        self.connection_status = tk.Label(status_frame, text="🔴 DB Disconnected", bg='#363636', fg='#ffffff', font=('Arial', 10))
        self.connection_status.pack(side=tk.RIGHT, padx=(0, 10))
        tk.Label(status_frame, text="📅 Running | 👤 Rasiharunar", bg='#363636', fg='#ffffff', font=('Arial', 9)).pack(side=tk.RIGHT, padx=(0, 20))

    def create_left_sidebar(self, parent):
        left_frame = tk.Frame(parent, bg='#2d2d2d', width=320)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_frame.grid_propagate(False)

        input_card = tk.LabelFrame(left_frame, text="🎛️ Input Source", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        input_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        input_inner = tk.Frame(input_card, bg='#2d2d2d'); input_inner.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(input_inner, text="Type", bg='#2d2d2d', fg='white').grid(row=0, column=0, sticky='w')
        self.var_input_type = tk.StringVar(value=self.input_type)
        self.input_type_cb = ttk.Combobox(input_inner, textvariable=self.var_input_type, values=["screen", "webcam", "network"], state="readonly", width=16)
        self.input_type_cb.grid(row=0, column=1, sticky='ew', pady=2)
        self.input_type_cb.bind("<<ComboboxSelected>>", lambda e: self.on_input_type_changed())
        # Webcam row
        self.webcam_row = tk.Frame(input_inner, bg='#2d2d2d')
        tk.Label(self.webcam_row, text="Webcam index", bg='#2d2d2d', fg='white').pack(side=tk.LEFT)
        self.var_webcam_index = tk.IntVar(value=int(self.webcam_index))
        ttk.Spinbox(self.webcam_row, from_=0, to=10, textvariable=self.var_webcam_index, width=6).pack(side=tk.LEFT, padx=6)
        # Network row
        self.net_row = tk.Frame(input_inner, bg='#2d2d2d')
        tk.Label(self.net_row, text="Stream URL", bg='#2d2d2d', fg='white').pack(side=tk.LEFT)
        self.var_stream_url = tk.StringVar(value=self.stream_url)
        ttk.Entry(self.net_row, textvariable=self.var_stream_url, width=24).pack(side=tk.LEFT, padx=6)
        # Test
        tk.Button(input_inner, text="🔌 Test Source", command=self.test_source, bg='#6a6a6a', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=4).grid(row=3, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        input_inner.columnconfigure(1, weight=1)

        # Screen Capture
        self.capture_card = tk.LabelFrame(left_frame, text="📹 Screen Capture", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        self.capture_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        capture_inner = tk.Frame(self.capture_card, bg='#2d2d2d'); capture_inner.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(capture_inner, text="🎯 Select Region", command=self.select_screen_region, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        tk.Button(capture_inner, text="🖥️ Full Screen", command=self.capture_full_screen, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        self.preview_button = tk.Button(capture_inner, text="▶️ Start Preview", command=self.toggle_preview, state='disabled', bg='#107c10', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5)
        self.preview_button.pack(fill=tk.X, pady=(5, 0))

        # Line settings
        line_card = tk.LabelFrame(left_frame, text="📏 Counting Line Setup", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        line_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        line_inner = tk.Frame(line_card, bg='#2d2d2d'); line_inner.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(line_inner, text="⚙️ Line Settings", command=self.open_line_settings, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        self.draw_line_button = tk.Button(line_inner, text="✏️ Draw Line", command=self.enable_line_drawing, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5)
        self.draw_line_button.pack(fill=tk.X, pady=2)
        tk.Button(line_inner, text="🗑️ Clear Line", command=self.clear_line, bg='#d13438', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)

        # Detection control
        detection_card = tk.LabelFrame(left_frame, text="🚀 Detection Control", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        detection_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        detection_inner = tk.Frame(detection_card, bg='#2d2d2d'); detection_inner.pack(fill=tk.X, padx=10, pady=10)
        self.start_button = tk.Button(detection_inner, text="🎬 Start Detection", command=self.toggle_capture, bg='#107c10', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5)
        self.start_button.pack(fill=tk.X, pady=2)
        tk.Button(detection_inner, text="🔄 Reset Counts", command=self.reset_count, bg='#d13438', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=(5, 0))

        # Status
        status_card = tk.LabelFrame(left_frame, text="📊 System Status", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        status_card.pack(fill=tk.X, padx=10)
        status_inner = tk.Frame(status_card, bg='#2d2d2d'); status_inner.pack(fill=tk.X, padx=10, pady=10)
        self.region_status = tk.Label(status_inner, text="📺 Region/Source: Not ready", bg='#2d2d2d', fg='#ffffff', font=('Arial', 9))
        self.region_status.pack(anchor=tk.W, pady=1)
        self.line_status = tk.Label(status_inner, text="📏 Line: Not drawn", bg='#2d2d2d', fg='#ffffff', font=('Arial', 9))
        self.line_status.pack(anchor=tk.W, pady=1)
        self.preview_status = tk.Label(status_inner, text="👁️ Preview: Off", bg='#2d2d2d', fg='#ffffff', font=('Arial', 9))
        self.preview_status.pack(anchor=tk.W, pady=1)

    def create_center_video_area(self, parent):
        video_container = tk.Frame(parent, bg='#363636', relief='solid', bd=1)
        video_container.grid(row=1, column=1, sticky="nsew", padx=(0, 10))
        video_container.rowconfigure(1, weight=1)
        video_container.columnconfigure(0, weight=1)

        video_header = tk.Frame(video_container, bg='#363636')
        video_header.grid(row=0, column=0, sticky="ew", pady=10, padx=10)
        self.video_title = tk.Label(video_header, text="🎥 Live Video Feed - Modern AI Detection", bg='#363636', fg='#00d4ff', font=('Arial', 14, 'bold'))
        self.video_title.pack(side=tk.LEFT)

        info_frame = tk.Frame(video_header, bg='#363636'); info_frame.pack(side=tk.RIGHT)
        self.fps_label = tk.Label(info_frame, text="📈 FPS: 0", bg='#363636', fg='#ffffff', font=('Arial', 9)); self.fps_label.pack(side=tk.RIGHT, padx=(0, 15))
        self.detection_label = tk.Label(info_frame, text="🎯 Detections: 0", bg='#363636', fg='#ffffff', font=('Arial', 9)); self.detection_label.pack(side=tk.RIGHT, padx=(0, 15))

        canvas_frame = tk.Frame(video_container, bg='#363636')
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg='#1a1a1a', highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        instruction_frame = tk.Frame(video_container, bg='#363636')
        instruction_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=10)
        self.instructions = tk.Label(instruction_frame, text="🟢 Active Vehicle | ⚫ Counted Vehicle | Select input → Preview → Draw line → Start detection", bg='#363636', fg='#ffffff', font=('Arial', 9))
        self.instructions.pack()

        self.canvas.bind("<Button-1>", self.start_line)
        self.canvas.bind("<B1-Motion>", self.draw_line_preview)
        self.canvas.bind("<ButtonRelease-1>", self.end_line)

    def create_right_sidebar(self, parent):
        right_frame = tk.Frame(parent, bg='#2d2d2d', width=320)
        right_frame.grid(row=1, column=2, sticky="nsew")
        right_frame.grid_propagate(False)

        stats_card = tk.LabelFrame(right_frame, text="📊 Live Statistics Dashboard", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        stats_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        total_frame = tk.Frame(stats_card, bg='#363636', relief='solid', bd=1); total_frame.pack(fill=tk.X, pady=10, padx=10)
        self.total_up_label = tk.Label(total_frame, text="📈 Total UP: 0", bg='#363636', fg='#28a745', font=('Arial', 12, 'bold')); self.total_up_label.pack(pady=5)
        self.total_down_label = tk.Label(total_frame, text="📉 Total DOWN: 0", bg='#363636', fg='#dc3545', font=('Arial', 12, 'bold')); self.total_down_label.pack(pady=5)
        self.create_modern_vehicle_counts(stats_card)

        database_card = tk.LabelFrame(right_frame, text="💾 Database Operations", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        database_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        db_status_frame = tk.Frame(database_card, bg='#363636', relief='solid', bd=1); db_status_frame.pack(fill=tk.X, pady=10, padx=10)
        self.db_status_label = tk.Label(db_status_frame, text="❌ Database: Disconnected", bg='#363636', fg='#dc3545', font=('Arial', 9)); self.db_status_label.pack(pady=5)
        db_inner = tk.Frame(database_card, bg='#2d2d2d'); db_inner.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(db_inner, text="💾 Save to Database", command=self.save_counts_to_db, bg='#107c10', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        tk.Button(db_inner, text="📚 Open Data Viewer", command=self.view_reports, bg='#0078d4', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        tk.Button(db_inner, text="⚙️ Database Settings", command=self.open_database_settings, bg='#6a6a6a', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        tk.Button(db_inner, text="🗄️ Backup Database", command=self.backup_database, bg='#6a6a6a', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)
        tk.Button(db_inner, text="📥 Restore Database", command=self.restore_database, bg='#6a6a6a', fg='white', font=('Arial', 9), relief='flat', bd=0, pady=5).pack(fill=tk.X, pady=2)

        system_card = tk.LabelFrame(right_frame, text="⚙️ System Information", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        system_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        system_inner = tk.Frame(system_card, bg='#2d2d2d'); system_inner.pack(fill=tk.X, padx=10, pady=10)
        self.model_info = tk.Label(system_inner, text=f"🤖 Model: {MODEL_CONFIG.get('model_path','')}", bg='#2d2d2d', fg='#ffffff', font=('Arial', 9)); self.model_info.pack(anchor=tk.W, pady=1)
        tk.Label(system_inner, text=f"Conf: {MODEL_CONFIG['confidence_threshold']} | IoU: {MODEL_CONFIG['iou_threshold']} | Device: {MODEL_CONFIG.get('device','cpu')}", bg='#2d2d2d', fg='#bbbbbb', font=('Arial', 8)).pack(anchor=tk.W)

        performance_frame = tk.Frame(system_inner, bg='#363636', relief='solid', bd=1); performance_frame.pack(fill=tk.X, pady=5)
        tk.Label(performance_frame, text="Performance Metrics:", bg='#363636', fg='#ffffff', font=('Arial', 9, 'bold')).pack(anchor=tk.W, padx=5, pady=2)
        self.accuracy_label = tk.Label(performance_frame, text="🎯 Optimize via settings.json > runtime", bg='#363636', fg='#ffffff', font=('Arial', 9))
        self.accuracy_label.pack(anchor=tk.W, pady=1, padx=5)

        legend_card = tk.LabelFrame(right_frame, text="🧭 Direction Legend", bg='#2d2d2d', fg='#ffffff', font=('Arial', 10, 'bold'), relief='solid', bd=1)
        legend_card.pack(fill=tk.X, padx=10)
        legend_inner = tk.Frame(legend_card, bg='#2d2d2d'); legend_inner.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(legend_inner, text="📈 ↑ UP/LEFT direction", bg='#2d2d2d', fg='#28a745', font=('Arial', 8)).pack(anchor=tk.W, pady=1)
        tk.Label(legend_inner, text="📉 ↓ DOWN/RIGHT direction", bg='#2d2d2d', fg='#dc3545', font=('Arial', 8)).pack(anchor=tk.W, pady=1)
        tk.Label(legend_inner, text="🟢 Active Vehicle", bg='#2d2d2d', fg='#ffffff', font=('Arial', 8)).pack(anchor=tk.W, pady=1)
        tk.Label(legend_inner, text="⚫ Counted Vehicle", bg='#2d2d2d', fg='#ffffff', font=('Arial', 8)).pack(anchor=tk.W, pady=1)

    def create_modern_vehicle_counts(self, parent):
        vehicles = [('🚗 Cars', 'car'), ('🏍️ Motorcycles', 'motorcycle'), ('🚌 Buses', 'bus'), ('🚛 Trucks', 'truck')]
        for emoji_name, vehicle_type in vehicles:
            vehicle_frame = tk.Frame(parent, bg='#363636', relief='solid', bd=1)
            vehicle_frame.pack(fill=tk.X, pady=2, padx=10)
            tk.Label(vehicle_frame, text=emoji_name, bg='#363636', fg='#ffffff', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=10, pady=5)
            count_frame = tk.Frame(vehicle_frame, bg='#363636'); count_frame.pack(side=tk.RIGHT, padx=10, pady=5)
            up_label = tk.Label(count_frame, text="↑0", bg='#363636', fg='#28a745', font=('Arial', 10)); up_label.pack(side=tk.RIGHT, padx=(10, 5))
            down_label = tk.Label(count_frame, text="↓0", bg='#363636', fg='#dc3545', font=('Arial', 10)); down_label.pack(side=tk.RIGHT, padx=5)
            setattr(self, f'{vehicle_type}_up_label', up_label)
            setattr(self, f'{vehicle_type}_down_label', down_label)

    # ========== Input source management ==========
    def on_input_type_changed(self):
        self.input_type = self.var_input_type.get()
        self.input_cfg["type"] = self.input_type
        settings_manager.save()
        self.update_input_source_ui()
        self.update_preview_button_state()

    def update_input_source_ui(self):
        if self.input_type == "webcam":
            self.webcam_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
            self.net_row.grid_forget()
            self.capture_card.pack_forget()
            self.region_status.config(text=f"📺 Source: Webcam (index {self.var_webcam_index.get()})")
        elif self.input_type == "network":
            self.net_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=4)
            self.webcam_row.grid_forget()
            self.capture_card.pack_forget()
            self.region_status.config(text="📺 Source: Network stream")
        else:
            self.webcam_row.grid_forget()
            self.net_row.grid_forget()
            try:
                self.capture_card.pack_info()
            except Exception:
                self.capture_card.pack(fill=tk.X, pady=(0, 15), padx=10)
            if self.capture_region:
                w = self.capture_region[2] - self.capture_region[0]
                h = self.capture_region[3] - self.capture_region[1]
                self.region_status.config(text=f"📺 Region: {w}×{h}px")
            else:
                self.region_status.config(text="📺 Region: Not selected")

    def update_preview_button_state(self):
        if self.input_type == "screen":
            self.preview_button.config(state='normal' if self.capture_region else 'disabled')
        elif self.input_type == "webcam":
            self.preview_button.config(state='normal')
        elif self.input_type == "network":
            self.preview_button.config(state='normal' if self.var_stream_url.get().strip() else 'disabled')

    def open_video_source(self) -> bool:
        self.close_video_source()
        try:
            if self.input_type == "webcam":
                idx = int(self.var_webcam_index.get())
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                except Exception:
                    pass
            elif self.input_type == "network":
                url = self.var_stream_url.get().strip()
                if not url:
                    return False
                cap = cv2.VideoCapture(url)
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
            else:
                return True
            if not cap or not cap.isOpened():
                messagebox.showerror("Input Source", "Failed to open input source.")
                return False
            with self.cap_lock:
                self.cap = cap
            return True
        except Exception as e:
            messagebox.showerror("Input Source", f"Failed to open source: {e}")
            return False

    def close_video_source(self):
        with self.cap_lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

    def test_source(self):
        if self.input_type == "screen":
            if not self.capture_region:
                messagebox.showinfo("Screen", "Select a screen region or use Full Screen first.")
                return
            frame = self.capture_screen()
            if frame is None:
                messagebox.showerror("Screen", "Failed to capture screen.")
                return
            h, w = frame.shape[:2]
            self.region_status.config(text=f"📺 Screen OK: {w}×{h}px")
            with self.frame_lock:
                self.current_frame = frame
            self.root.after(0, self.update_display)
        else:
            if not self.open_video_source():
                return
            with self.cap_lock:
                cap = self.cap
            ret, frame = (False, None)
            if cap:
                ret, frame = cap.read()
            if not ret or frame is None:
                messagebox.showerror("Input Source", "No frame received from source.")
                self.close_video_source()
                return
            h, w = frame.shape[:2]
            if self.input_type == "webcam":
                self.region_status.config(text=f"📺 Webcam OK: {w}×{h}px (index {self.var_webcam_index.get()})")
            else:
                self.region_status.config(text=f"📺 Stream OK: {w}×{h}px")
            with self.frame_lock:
                self.current_frame = frame
            self.root.after(0, self.update_display)
        self.persist_input_settings()

    def persist_input_settings(self):
        self.input_cfg["type"] = self.input_type
        self.input_cfg["stream_url"] = self.var_stream_url.get().strip()
        self.input_cfg["webcam_index"] = int(self.var_webcam_index.get())
        if self.capture_region:
            self.input_cfg["screen_region"] = list(self.capture_region)
        settings_manager.save()

    # ===== Model/DB dialogs =====
    def open_model_settings(self):
        dlg = ModelSettingsDialog(self.root, MODEL_CONFIG)
        self.root.wait_window(dlg.dialog)
        if dlg.result:
            self.reload_yolo_model(dlg.result)
            self.model_info.config(text=f"🤖 Model: {MODEL_CONFIG.get('model_path','')}")

    def open_database_settings(self):
        dlg = DatabaseSettingsDialog(self.root, self.db_handler)
        self.root.wait_window(dlg.dialog)

    def backup_database(self):
        try:
            self.db_handler.backup_database(self.root)
        except Exception as e:
            messagebox.showerror("Backup Error", str(e))

    def restore_database(self):
        try:
            self.db_handler.restore_database(self.root)
        except Exception as e:
            messagebox.showerror("Restore Error", str(e))

    # ===== Screen region selection =====
    def select_screen_region(self):
        if self.input_type != "screen":
            messagebox.showinfo("Input", "Region selection is only for Screen input.")
            return
        self.root.withdraw()
        time.sleep(0.4)
        try:
            overlay = tk.Toplevel()
            overlay.attributes('-fullscreen', True)
            overlay.attributes('-alpha', 0.3)
            overlay.configure(bg='#1a1a1a')
            overlay.attributes('-topmost', True)

            canvas = tk.Canvas(overlay, highlightthickness=0, bg='#1a1a1a'); canvas.pack(fill=tk.BOTH, expand=True)
            canvas.create_text(overlay.winfo_screenwidth()//2, 50, text="🎯 Drag untuk memilih area | ESC untuk batal", fill='#00d4ff', font=('Arial', 18, 'bold'))

            start_pos = None
            selection_rect = None

            def start_selection(event):
                nonlocal start_pos, selection_rect
                start_pos = (event.x, event.y)
                if selection_rect:
                    canvas.delete(selection_rect)

            def drag_selection(event):
                nonlocal selection_rect
                if start_pos:
                    if selection_rect:
                        canvas.delete(selection_rect)
                    selection_rect = canvas.create_rectangle(start_pos[0], start_pos[1], event.x, event.y, outline='#00d4ff', width=3)

            def end_selection(event):
                if start_pos:
                    x1, y1 = start_pos; x2, y2 = event.x, event.y
                    left = min(x1, x2); top = min(y1, y2)
                    width = abs(x2 - x1); height = abs(y2 - y1)
                    overlay.destroy(); self.root.deiconify()
                    if width > 50 and height > 50:
                        self.capture_region = (left, top, left + width, top + height)
                        self.region_status.config(text=f"📺 Region: {width}×{height}px")
                        self.preview_button.config(state='normal')
                        self.persist_input_settings()
                        self.root.after(400, self.start_preview_automatically)

            def cancel_selection(event):
                overlay.destroy(); self.root.deiconify()

            canvas.bind('<Button-1>', start_selection)
            canvas.bind('<B1-Motion>', drag_selection)
            canvas.bind('<ButtonRelease-1>', end_selection)
            overlay.bind('<Escape>', cancel_selection)
            canvas.focus_set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to select region: {str(e)}")
            self.root.deiconify()

    def capture_full_screen(self):
        if self.input_type != "screen":
            messagebox.showinfo("Input", "Full Screen is only for Screen input.")
            return
        screen_width, screen_height = pyautogui.size()
        self.capture_region = (0, 0, screen_width, screen_height)
        self.region_status.config(text=f"📺 Region: Full Screen ({screen_width}×{screen_height})")
        self.preview_button.config(state='normal')
        self.persist_input_settings()
        self.start_preview_automatically()

    def start_preview_automatically(self):
        if not self.is_previewing:
            self.toggle_preview()

    # ===== Preview / Capture =====
    def toggle_preview(self):
        if self.input_type == "screen" and not self.capture_region:
            messagebox.showwarning("⚠️", "Pilih capture region terlebih dahulu"); return
        if self.input_type == "network" and not self.var_stream_url.get().strip():
            messagebox.showwarning("⚠️", "Isi stream URL terlebih dahulu"); return

        self.is_previewing = not self.is_previewing
        self.preview_button.config(text="⏹️ Stop Preview" if self.is_previewing else "▶️ Start Preview")

        if self.is_previewing:
            if self.input_type in ("webcam", "network"):
                if not self.open_video_source():
                    self.is_previewing = False
                    self.preview_button.config(text="▶️ Start Preview")
                    return
            self.preview_status.config(text="👁️ Preview: Active", fg='#28a745')
            self.video_title.config(text="🎥 Live Preview - Draw Your Counting Line")
            self.instructions.config(text="🟢 Active Vehicle | ⚫ Counted Vehicle | Draw ONE counting line for directional detection.")
            self.preview_thread = threading.Thread(target=self.preview_loop, daemon=True)
            self.preview_thread.start()
        else:
            self.preview_status.config(text="👁️ Preview: Off", fg='#ffffff')
            self.video_title.config(text="🎥 Live Video Feed - Modern AI Detection")
            self.canvas.delete("all"); self.canvas.configure(bg='#1a1a1a')
            if not self.is_capturing:
                self.close_video_source()

    def get_frame(self):
        if self.input_type == "screen":
            return self.capture_screen()
        else:
            with self.cap_lock:
                cap = self.cap
            if cap is None:
                return None
            # flush camera frames
            flush_n = max(1, int(RUNTIME_CONFIG.get("flush_frames", 2)))
            try:
                for _ in range(flush_n - 1):
                    cap.grab()
            except Exception:
                pass
            ret, frame = cap.read()
            if not ret:
                return None
            return frame

    def preview_loop(self):
        fps_counter = 0
        fps_start = time.time()
        while self.is_previewing and not self.is_capturing:
            try:
                frame = self.get_frame()
                if frame is None:
                    time.sleep(0.05); continue
                if self.counting_line:
                    self.draw_counting_line(frame)
                with self.frame_lock:
                    self.current_frame = frame.copy()
                self.root.after(0, self.update_display)
                fps_counter += 1
                if fps_counter % 10 == 0:
                    now = time.time()
                    fps = 10 / (now - fps_start)
                    fps_start = now
                    self.root.after(0, lambda f=fps: self.fps_label.config(text=f"📈 Preview FPS: {f:.1f}"))
                time.sleep(0.03)
            except Exception:
                time.sleep(0.1)

    def toggle_capture(self):
        if self.input_type == "screen" and not self.capture_region:
            messagebox.showwarning("⚠️", "Pilih capture region terlebih dahulu"); return
        if self.input_type == "network" and not self.var_stream_url.get().strip():
            messagebox.showwarning("⚠️", "Isi stream URL terlebih dahulu"); return
        if not self.is_capturing and (not self.line_drawn or not self.counting_line):
            messagebox.showwarning("⚠️", "Gambar garis hitung dulu"); return

        self.is_capturing = not self.is_capturing
        self.start_button.config(text="⏹️ Stop Detection" if self.is_capturing else "🎬 Start Detection")

        if self.is_capturing:
            if self.input_type in ("webcam", "network"):
                if not self.open_video_source():
                    self.is_capturing = False
                    self.start_button.config(text="🎬 Start Detection")
                    return
            if self.is_previewing:
                self.is_previewing = False
                self.preview_button.config(text="▶️ Start Preview")
                self.preview_status.config(text="👁️ Preview: Off")
            self.line_draw_enabled = False
            self.draw_line_button.config(text="✏️ Draw Line", state='normal')
            self.video_title.config(text="🎥 AI Detection Active - Real-time Counting")
            self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
            self.capture_thread.start()
        else:
            self.video_title.config(text="🎥 Detection Stopped")
            if self.input_type in ("webcam", "network") and not self.is_previewing:
                self.close_video_source()
            if self.input_type == "screen":
                self.root.after(400, lambda: self.toggle_preview() if not self.is_previewing else None)

    def capture_screen(self):
        """Capture screen region. MSS per-thread; fallback ke PIL bila gagal."""
        try:
            if not self.capture_region:
                return None

            left, top, right, bottom = self.capture_region
            # Clip to screen bounds
            try:
                screen_w, screen_h = pyautogui.size()
            except Exception:
                screen_w, screen_h = 99999, 99999

            left = max(0, int(left))
            top = max(0, int(top))
            right = min(int(right), int(screen_w))
            bottom = min(int(bottom), int(screen_h))
            width = max(1, right - left)
            height = max(1, bottom - top)

            if self.use_mss and self._has_mss:
                try:
                    sct = getattr(self._tls, "sct", None)
                    if sct is None:
                        import mss  # local import safe
                        self._tls.sct = mss.mss()
                        sct = self._tls.sct

                    monitor = {"left": left, "top": top, "width": width, "height": height}
                    img = np.array(sct.grab(monitor))  # BGRA
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    return frame

                except Exception:
                    # reinit once
                    try:
                        import mss
                        self._tls.sct = mss.mss()
                        monitor = {"left": left, "top": top, "width": width, "height": height}
                        img = np.array(self._tls.sct.grab(monitor))
                        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        return frame
                    except Exception as e2:
                        print(f"Screen capture (MSS) error: {e2}. Falling back to PIL.")
                        self.use_mss = False

            # Fallback to PIL
            screenshot = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame

        except Exception as e:
            print(f"Screen capture error: {e}")
            return None

    # ===== Utils =====
    def _clamp_bbox(self, bbox, width, height):
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(width - 1, int(x1)))
        y1 = max(0, min(height - 1, int(y1)))
        x2 = max(0, min(width - 1, int(x2)))
        y2 = max(0, min(height - 1, int(y2)))
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1
        return [x1, y1, x2, y2]

    def _bbox_iou(self, a, b):
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        aw, ah = max(0, ax2 - ax1), max(0, ay2 - ay1)
        bw, bh = max(0, bx2 - bx1), max(0, by2 - by1)
        union = aw * ah + bw * bh - inter
        return inter / union if union > 0 else 0.0

    # ===== RAW draw (seperti skrip) + opsional Track ID =====
    def _draw_raw_detections(self, frame, results, x_off=0, y_off=0, tracked=None):
        annotated = frame
        names = None
        try:
            if results and len(results) > 0:
                r0 = results[0]
                names = getattr(r0, "names", self._model_names)
        except Exception:
            names = self._model_names

        show_all = bool(RUNTIME_CONFIG.get("raw_show_all_classes", False))
        veh_ids = VEHICLE_CLASSES
        draw_ids = bool(RUNTIME_CONFIG.get("raw_draw_ids", True)) and isinstance(tracked, dict)

        if not results:
            return

        r = results[0]
        boxes = getattr(r, "boxes", None)
        if boxes is None:
            return

        xyxy = getattr(boxes, "xyxy", None)
        confs = getattr(boxes, "conf", None)
        clss = getattr(boxes, "cls", None)
        if xyxy is None or confs is None or clss is None:
            return

        xyxy = xyxy.detach().cpu().numpy()
        confs = confs.detach().cpu().numpy()
        clss = clss.detach().cpu().numpy().astype(int)

        H, W = annotated.shape[:2]
        # Siapkan list tracked boxes untuk IoU match
        tracked_list = []
        if draw_ids:
            for tid, tr in tracked.items():
                tracked_list.append((tid, tr["bbox"]))

        for (x1, y1, x2, y2), c, cls_id in zip(xyxy, confs, clss):
            if not show_all and cls_id not in veh_ids:
                continue
            x1i = int(x1 + x_off); y1i = int(y1 + y_off)
            x2i = int(x2 + x_off); y2i = int(y2 + y_off)
            x1i, y1i, x2i, y2i = self._clamp_bbox([x1i, y1i, x2i, y2i], W, H)

            cv2.rectangle(annotated, (x1i, y1i), (x2i, y2i), (0, 255, 0), 2)
            # Label nama + conf
            label_name = str(cls_id)
            if isinstance(names, dict):
                label_name = names.get(int(cls_id), str(cls_id))
            base_label = f"{label_name} {c:.2f}"

            # Cari track ID terdekat via IoU
            tid_text = ""
            if draw_ids and tracked_list:
                best_tid = None
                best_iou = 0.0
                for tid, tb in tracked_list:
                    iou = self._bbox_iou([x1i, y1i, x2i, y2i], tb)
                    if iou > best_iou:
                        best_iou = iou
                        best_tid = tid
                if best_tid is not None and best_iou >= 0.1:
                    tid_text = f" | ID:{best_tid}"

            label = base_label + tid_text
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y_text = max(th + base + 2, y1i)
            cv2.rectangle(annotated, (x1i, y_text - th - base), (x1i + tw, y_text), (0, 255, 0), -1)
            cv2.putText(annotated, label, (x1i, y_text - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    def capture_loop(self):
        fps_counter = 0
        fps_start = time.time()
        frame_idx = 0

        # Modes
        raw_mode = bool(RUNTIME_CONFIG.get("raw_detections_mode", False))
        raw_counting = bool(RUNTIME_CONFIG.get("raw_counting_mode", True))
        raw_full = bool(RUNTIME_CONFIG.get("raw_force_full_region", True))
        raw_conf = float(RUNTIME_CONFIG.get("raw_conf", 0.25))
        raw_iou = float(RUNTIME_CONFIG.get("raw_iou", 0.70))

        # Non-RAW params
        use_roi = bool(RUNTIME_CONFIG.get("use_roi_around_line", True)) and not (raw_full and (raw_mode or raw_counting))
        roi_margin = int(RUNTIME_CONFIG.get("roi_margin_px", 120))
        gate_len = int(RUNTIME_CONFIG.get("roi_gate_length_px", 480))
        safe_pad = int(RUNTIME_CONFIG.get("roi_safe_pad_px", 48))
        stride = 1 if (raw_mode or raw_counting) else max(1, int(RUNTIME_CONFIG.get("detection_stride", 3)))
        imgsz = int(RUNTIME_CONFIG.get("imgsz", 576))
        half = (MODEL_CONFIG.get("device", "cpu").startswith("cuda") and RUNTIME_CONFIG.get("use_half", True))
        use_class_filter = bool(RUNTIME_CONFIG.get("use_class_filter", True))
        classes_arg = list(VEHICLE_CLASSES) if (use_class_filter and not (raw_mode or raw_counting) and not RUNTIME_CONFIG.get("raw_show_all_classes", False)) else None

        while self.is_capturing:
            try:
                frame = self.get_frame()
                if frame is None:
                    time.sleep(0.01); continue

                run_det = (frame_idx % stride == 0)

                det_frame = frame
                x_off = 0; y_off = 0

                if run_det:
                    if (raw_mode or raw_counting) and raw_full:
                        pass
                    else:
                        if use_roi and self.counting_line:
                            (lx1, ly1), (lx2, ly2) = self.counting_line
                            vx = lx2 - lx1; vy = ly2 - ly1
                            L = math.hypot(vx, vy) if (vx or vy) else 1.0
                            ux = vx / L; uy = vy / L
                            mx = (lx1 + lx2) * 0.5; my = (ly1 + ly2) * 0.5
                            if gate_len and gate_len > 0:
                                half_len = gate_len * 0.5
                                gx1 = int(mx - ux * half_len); gy1 = int(my - uy * half_len)
                                gx2 = int(mx + ux * half_len); gy2 = int(my + uy * half_len)
                            else:
                                gx1, gy1, gx2, gy2 = lx1, ly1, lx2, ly2

                            xmin = max(0, min(gx1, gx2) - roi_margin - safe_pad)
                            ymin = max(0, min(gy1, gy2) - roi_margin - safe_pad)
                            xmax = min(frame.shape[1], max(gx1, gx2) + roi_margin + safe_pad)
                            ymax = min(frame.shape[0], max(gy1, gy2) + roi_margin + safe_pad)
                            if xmax - xmin > 40 and ymax - ymin > 40:
                                det_frame = frame[ymin:ymax, xmin:xmax]
                                x_off, y_off = xmin, ymin

                    # YOLO inference
                    if raw_mode or raw_counting:
                        results = self.model(det_frame, verbose=False, conf=raw_conf, iou=raw_iou, imgsz=imgsz, half=half)
                    else:
                        if classes_arg is not None:
                            results = self.model(det_frame, verbose=False,
                                                 conf=MODEL_CONFIG['confidence_threshold'],
                                                 iou=MODEL_CONFIG['iou_threshold'],
                                                 imgsz=imgsz, half=half, classes=classes_arg)
                        else:
                            results = self.model(det_frame, verbose=False,
                                                 conf=MODEL_CONFIG['confidence_threshold'],
                                                 iou=MODEL_CONFIG['iou_threshold'],
                                                 imgsz=imgsz, half=half)

                    # Siapkan detections untuk tracker bila counting aktif
                    detections = []
                    if raw_counting or not (raw_mode or raw_counting):
                        for r in results:
                            boxes = getattr(r, "boxes", None)
                            if boxes is not None:
                                for box in boxes:
                                    cls = int(box.cls[0])
                                    conf = float(box.conf[0])
                                    if cls in VEHICLE_CLASSES and conf >= MODEL_CONFIG['detection_confidence']:
                                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                        x1 += x_off; y1 += y_off; x2 += x_off; y2 += y_off
                                        w = x2 - x1; h = y2 - y1
                                        if w > TRACKING_CONFIG['min_detection_size'] and h > TRACKING_CONFIG['min_detection_size']:
                                            H, W = frame.shape[:2]
                                            x1, y1, x2, y2 = self._clamp_bbox([x1, y1, x2, y2], W, H)
                                            detections.append({
                                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                                'class': cls, 'confidence': conf
                                            })

                    # Update tracker lebih dulu jika raw_counting agar ID siap untuk ditampilkan
                    tracked = None
                    if raw_counting:
                        self.vehicle_tracker.update_tracking(detections)
                        tracked = self.vehicle_tracker.get_tracked_vehicles_with_status()

                    # Gambar RAW (dengan ID jika ada tracked)
                    if raw_mode or raw_counting:
                        self._draw_raw_detections(frame, results, x_off, y_off, tracked=tracked)
                    else:
                        # Non-RAW: tracking + draw dari tracker
                        self.vehicle_tracker.update_tracking(detections)

                # Counting (keduanya: raw_counting dan non-RAW)
                if raw_counting or not (raw_mode or raw_counting):
                    if self.vehicle_tracker.check_line_crossings_directional(self.counting_line, self.line_settings):
                        self.update_count_labels()
                    # Draw tracked boxes hanya di non-RAW
                    if not (raw_mode or raw_counting):
                        self.draw_detections_with_colors(frame)

                # Garis hitung
                self.draw_counting_line(frame)

                # Show
                with self.frame_lock:
                    self.current_frame = frame.copy()
                self.root.after(0, self.update_display)

                # FPS
                fps_counter += 1
                if fps_counter % 5 == 0:
                    now = time.time()
                    fps = 5 / (now - fps_start)
                    fps_start = now
                    if raw_mode and not raw_counting:
                        mode_tag = "RAW"
                    elif raw_counting:
                        mode_tag = "RAW+Count"
                    else:
                        mode_tag = "Det"
                    self.root.after(0, lambda f=fps, m=mode_tag: self.fps_label.config(text=f"📈 {m} FPS: {f:.1f}"))

                frame_idx += 1
                time.sleep(0.005)
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.02)

    # ===== Tracked drawing (non-RAW) =====
    def draw_detections_with_colors(self, frame):
        tracked = self.vehicle_tracker.get_tracked_vehicles_with_status()
        draw_paths = bool(RUNTIME_CONFIG.get("draw_paths", True))
        max_pts = int(RUNTIME_CONFIG.get("max_path_points_drawn", 10))

        H, W = frame.shape[:2]

        for track_id, tr in tracked.items():
            bbox = tr['bbox']
            bbox = self._clamp_bbox(bbox, W, H)
            x1, y1, x2, y2 = map(int, bbox)

            cls_name = CLASS_NAMES.get(tr['class'], 'unknown')
            conf = tr['confidence']
            counted = tr.get('is_counted', False)

            if counted:
                box_color = COLOR_CONFIG['counted_vehicle']
                center_color = COLOR_CONFIG['center_dot_counted']
                path_color = COLOR_CONFIG['tracking_path_counted']
                prefix = f"[COUNTED] ID:{track_id}"
            else:
                box_color = COLOR_CONFIG['active_vehicle']
                center_color = COLOR_CONFIG['center_dot_active']
                path_color = COLOR_CONFIG['tracking_path']
                prefix = f"[ACTIVE] ID:{track_id}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            label = f"{prefix} {cls_name} {conf:.2f}"
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            y_text = max(th + base + 2, y1)
            cv2.rectangle(frame, (x1, y_text - th - base), (x1 + tw, y_text), box_color, -1)
            cv2.putText(frame, label, (x1, y_text - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.circle(frame, (cx, cy), 3, center_color, -1)

            if draw_paths:
                path = tr['path']
                if len(path) > 1:
                    start_idx = max(1, len(path) - max_pts)
                    for i in range(start_idx, len(path)):
                        cv2.line(frame, path[i-1], path[i], path_color, 2)

    def draw_counting_line(self, frame):
        if not self.counting_line:
            return
        hex_color = self.line_settings['line_color'].lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        bgr = (rgb[2], rgb[1], rgb[0])
        th = self.line_settings['line_thickness']
        p1, p2 = self.counting_line
        cv2.line(frame, p1, p2, bgr, th)

        band_px = int(self.line_settings.get("band_px", 12))
        x1, y1 = p1; x2, y2 = p2
        vx, vy = (x2 - x1), (y2 - y1)
        L = math.hypot(vx, vy) if (vx or vy) else 1.0
        nx, ny = (-vy / L, vx / L)
        off = band_px
        p1a = (int(x1 + nx * off), int(y1 + ny * off)); p2a = (int(x2 + nx * off), int(y2 + ny * off))
        p1b = (int(x1 - nx * off), int(y1 - ny * off)); p2b = (int(x2 - nx * off), int(y2 - ny * off))
        band_color = (bgr[0]//2, bgr[1]//2, bgr[2]//2)
        cv2.line(frame, p1a, p2a, band_color, 1, lineType=cv2.LINE_AA)
        cv2.line(frame, p1b, p2b, band_color, 1, lineType=cv2.LINE_AA)

        if self.line_settings['show_label']:
            label_text = self.line_settings['label_text']
            mid_x = (p1[0] + p2[0]) // 2; mid_y = (p1[1] + p2[1]) // 2
            cv2.putText(frame, label_text, (mid_x + 10, mid_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr, 2)
            cv2.putText(frame, "UP", (p1[0] - 30, p1[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, "DOWN", (p2[0] + 10, p2[1] + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # ===== Line drawing on canvas =====
    def start_line(self, event):
        if self.line_draw_enabled:
            self.drawing_line = True
            self.line_start_canvas = (event.x, event.y)
            self.canvas.delete("temp_line")

    def draw_line_preview(self, event):
        if self.drawing_line and hasattr(self, 'line_start_canvas'):
            self.canvas.delete("temp_line")
            self.canvas.create_line(self.line_start_canvas[0], self.line_start_canvas[1], event.x, event.y,
                                    fill=self.line_settings['line_color'], width=self.line_settings['line_thickness'], tags="temp_line")

    def end_line(self, event):
        if self.drawing_line and hasattr(self, 'line_start_canvas'):
            self.drawing_line = False
            self.canvas.delete("temp_line")
            p1_canvas = self.line_start_canvas; p2_canvas = (event.x, event.y)
            canvas_w = self.canvas.winfo_width(); canvas_h = self.canvas.winfo_height()
            with self.frame_lock:
                frame = None if self.current_frame is None else self.current_frame.copy()
            if frame is not None:
                fh, fw = frame.shape[:2]
            else:
                if self.input_type == "screen" and self.capture_region:
                    fw = self.capture_region[2] - self.capture_region[0]
                    fh = self.capture_region[3] - self.capture_region[1]
                else:
                    fw, fh = canvas_w, canvas_h

            frame_aspect = fw / fh; canvas_aspect = canvas_w / canvas_h
            if frame_aspect > canvas_aspect:
                scale = canvas_w / fw; new_h = int(fh * scale)
                y_off = (canvas_h - new_h) // 2; x_off = 0
            else:
                scale = canvas_h / fh; new_w = int(fw * scale)
                x_off = (canvas_w - new_w) // 2; y_off = 0

            def canvas_to_frame(x, y):
                x_adj = x - x_off; y_adj = y - y_off
                xf = int(x_adj / scale); yf = int(y_adj / scale)
                xf = max(0, min(fw - 1, xf)); yf = max(0, min(fh - 1, yf))
                return (xf, yf)

            p1 = canvas_to_frame(*p1_canvas); p2 = canvas_to_frame(*p2_canvas)
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 10:
                self.counting_line = [p1, p2]
                self.line_drawn = True
                self.line_draw_enabled = False
                self.draw_line_button.config(text="✏️ Draw Line", state='normal')
                self.line_status.config(text="📏 Line: 1 drawn")
                self.instructions.config(text="✅ Counting line ready! Start detection to count vehicles.")
            else:
                messagebox.showwarning("⚠️", "Line too short. Draw longer line.")
            del self.line_start_canvas

    def update_display(self):
        with self.frame_lock:
            frame = None if self.current_frame is None else self.current_frame.copy()
        if frame is not None:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            canvas_w = self.canvas.winfo_width(); canvas_h = self.canvas.winfo_height()
            if canvas_w < 10 or canvas_h < 10:
                return
            iw, ih = img.size
            ar = iw / ih; car = canvas_w / canvas_h
            if ar > car:
                new_w = canvas_w; new_h = int(canvas_w / ar)
            else:
                new_h = canvas_h; new_w = int(canvas_h * ar)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(image=img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w // 2, canvas_h // 2, image=self.photo, anchor=tk.CENTER)
        self.root.update_idletasks()

    # ===== DB ops =====
    def save_counts_to_db(self):
        try:
            counts = self.vehicle_tracker.get_counts()
            self.db_handler.save_counts(counts['up'], counts['down'], counts['total_up'], counts['total_down'], self.root)
            self.connection_status.config(text="🟢 DB Saved", fg='#28a745')
            self.root.after(3000, lambda: self.on_db_status_changed(self.db_handler.connected))
        except Exception as e:
            messagebox.showerror("💾 Database Error", f"Failed to save to database: {e}")

    def view_reports(self):
        try:
            DataViewer(self.root, self.db_handler)
        except Exception as e:
            messagebox.showerror("📚 Data Viewer", f"Unable to open data viewer: {e}")

    # ===== helpers =====
    def open_line_settings(self):
        dialog = LineSettingsDialog(self.root, self.line_settings)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.line_settings.update(dialog.result)
            settings_manager.settings['line_settings'] = self.line_settings
            settings_manager.save()
            if dialog.result['line_type'] != 'manual':
                self.create_automatic_line()

    def create_automatic_line(self):
        fw, fh = None, None
        with self.frame_lock:
            frame = None if self.current_frame is None else self.current_frame.copy()
        if frame is not None:
            fh, fw = frame.shape[:2]
        elif self.input_type == "screen" and self.capture_region:
            fw = self.capture_region[2] - self.capture_region[0]
            fh = self.capture_region[3] - self.capture_region[1]
        if not fw or not fh:
            return
        if self.line_settings['line_type'] == 'horizontal':
            y = fh // 2; self.counting_line = [(0, y), (fw, y)]
        elif self.line_settings['line_type'] == 'vertical':
            x = fw // 2; self.counting_line = [(x, 0), (x, fh)]
        self.line_drawn = True
        self.line_status.config(text="📏 Line: Auto-generated")
        self.instructions.config(text="✅ Line created automatically. Ready to start detection!")

    def enable_line_drawing(self):
        if self.input_type == "screen" and not self.capture_region:
            messagebox.showwarning("⚠️", "Pilih capture region terlebih dahulu"); return
        if self.input_type == "network" and not self.var_stream_url.get().strip():
            messagebox.showwarning("⚠️", "Isi stream URL terlebih dahulu"); return
        if self.is_capturing:
            messagebox.showwarning("⚠️", "Stop detection before drawing a new line"); return
        self.line_draw_enabled = True
        self.line_settings['line_type'] = 'manual'
        self.draw_line_button.config(text="✏️ Drawing Enabled", state='disabled')
        self.instructions.config(text="✏️ LINE DRAWING ENABLED: Click and drag on the video to create ONE counting line.")

    def clear_line(self):
        if messagebox.askyesno("🗑️ Clear Line", "Clear counting line?"):
            self.counting_line = None
            self.line_drawn = False
            self.line_status.config(text="📏 Line: Not drawn")
            self.instructions.config(text="🚫 Counting line cleared. Draw a new line for directional detection.")
            if self.is_capturing:
                self.toggle_capture()

    def reset_count(self):
        if messagebox.askyesno("🔄 Reset Counts", "Reset all counts?"):
            self.vehicle_tracker.reset_counts()
            self.update_count_labels()

    def update_count_labels(self):
        counts = self.vehicle_tracker.get_counts()
        self.root.after(0, lambda: self.total_up_label.config(text=f"📈 Total UP: {counts['total_up']}"))
        self.root.after(0, lambda: self.total_down_label.config(text=f"📉 Total DOWN: {counts['total_down']}"))
        for vehicle in ['car', 'motorcycle', 'bus', 'truck']:
            up_count = counts['up'].get(vehicle, 0)
            down_count = counts['down'].get(vehicle, 0)
            up_label = getattr(self, f'{vehicle}_up_label')
            down_label = getattr(self, f'{vehicle}_down_label')
            self.root.after(0, lambda ul=up_label, uc=up_count: ul.config(text=f"↑{uc}"))
            self.root.after(0, lambda dl=down_label, dc=down_count: dl.config(text=f"↓{dc}"))

    def on_closing(self):
        if self.is_capturing:
            self.is_capturing = False
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=1)
        if self.is_previewing:
            self.is_previewing = False
            if self.preview_thread and self.preview_thread.is_alive():
                self.preview_thread.join(timeout=1)
        self.close_video_source()
        self.db_handler.close_connection()
        self.persist_input_settings()
        settings_manager.save()
        self.root.destroy()


if __name__ == "__main__":
    app = ModernScreenVehicleCounter()
    app.root.mainloop()