import json
from pathlib import Path

# Persistent settings file
SETTINGS_FILE = Path("settings.json")


class SettingsManager:
    def __init__(self):
        # Defaults
        self.settings = {
            "model": {
                "model_path": "yolo11n.pt",
                "confidence_threshold": 0.40,
                "iou_threshold": 0.50,
                "detection_confidence": 0.35,
                "device": "auto",
            },
            "database": {
                "type": "sqlite",
                "sqlite_path": "traffic_counts.db",
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "traffic_db",
                "auto_save_interval_sec": 0
            },
            "line_settings": {
                "line_type": "manual",
                "line_color": "#00d4ff",
                "line_thickness": 3,
                "show_label": True,
                "label_text": "COUNT LINE",
                "band_px": 12,
                "invert_direction": False
            },
            "input": {
                "type": "screen",
                "webcam_index": 0,
                "stream_url": "",
                "screen_region": None
            },
            "runtime": {
                "imgsz": 576,
                "use_half": True,
                "use_roi_around_line": True,
                "roi_margin_px": 120,
                "roi_gate_length_px": 480,
                "roi_safe_pad_px": 48,
                "detection_stride": 3,
                "predict_missing": False,
                "max_prediction_frames": 1,
                "use_class_filter": True,
                "draw_paths": True,
                "max_path_points_drawn": 10,
                "flush_frames": 2,
                "use_mss_screen_capture": True,
                "win_force_dpi_awareness": True,

                # Stabilizer & clamp (dipakai di mode tracking non-RAW)
                "strict_clamp_boxes": True,
                "bbox_smooth_mode": "adaptive",
                "bbox_smooth_alpha": 0.4,
                "bbox_smooth_alpha_missed": 0.75,
                "bbox_max_shift_px": 48,

                # RAW modes
                "raw_detections_mode": False,      # RAW tampilan saja, tanpa counting
                "raw_counting_mode": True,         # RAW tampilan + counting via tracker
                "raw_force_full_region": True,     # deteksi full region agar sama seperti skrip
                "raw_show_all_classes": False,     # False = filter ke kendaraan (2,3,5,7)
                "raw_conf": 0.25,                  # threshold RAW (mirip skrip)
                "raw_iou": 0.70,                   # IoU RAW (mirip skrip)
                "raw_draw_ids": True               # tampilkan Track ID di atas bbox RAW saat raw_counting_mode
            }
        }
        self._load()

    def _load(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._deep_update(self.settings, data)
            except Exception:
                pass

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def _deep_update(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v


settings_manager = SettingsManager()

MODEL_CONFIG = settings_manager.settings["model"]
DEFAULT_LINE_SETTINGS = settings_manager.settings["line_settings"]
RUNTIME_CONFIG = settings_manager.settings["runtime"]

TRACKING_CONFIG = {
    "min_detection_size": 20,
    "max_track_lost_frames": 15,
    "max_match_distance": 80,
    "predict_missing": RUNTIME_CONFIG["predict_missing"],
    "max_prediction_frames": RUNTIME_CONFIG["max_prediction_frames"]
}

CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VEHICLE_CLASSES = {2, 3, 5, 7}

COLOR_CONFIG = {
    "active_vehicle": (0, 255, 0),
    "counted_vehicle": (128, 128, 128),
    "center_dot_active": (0, 255, 0),
    "center_dot_counted": (80, 80, 80),
    "tracking_path": (0, 255, 255),
    "tracking_path_counted": (160, 160, 160)
}