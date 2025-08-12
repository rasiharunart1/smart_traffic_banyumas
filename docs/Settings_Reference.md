# Referensi Pengaturan — Smart Traffic Counter v3.3

File: `settings.json`

## 1) model
- `model_path`: string — path model YOLO (contoh: "yolo11n.pt")
- `confidence_threshold`: float — ambang deteksi (non-RAW)
- `iou_threshold`: float — IoU/NMS (non-RAW)
- `detection_confidence`: float — ambang deteksi untuk diteruskan ke tracker
- `device`: "auto" | "cpu" | "cuda"

## 2) database
- `type`: "sqlite" | "mysql"
- `sqlite_path`: string (contoh: "traffic_counts.db")
- `host`, `port`, `user`, `password`, `database` (untuk MySQL)
- `auto_save_interval_sec`: integer (0 = hanya manual)

## 3) line_settings
- `line_type`: "manual" | "horizontal" | "vertical"
- `line_color`: string hex (contoh: "#00d4ff")
- `line_thickness`: integer (contoh: 3)
- `show_label`: boolean
- `label_text`: string
- `band_px`: integer — toleransi jarak crossing terhadap garis
- `invert_direction`: boolean — membalik definisi UP/DOWN

## 4) input
- `type`: "screen" | "webcam" | "network"
- `webcam_index`: integer
- `stream_url`: string (rtsp/http)
- `screen_region`: [left, top, right, bottom]

## 5) runtime
- `imgsz`: integer — resolusi inference YOLO (contoh: 576)
- `use_half`: boolean — gunakan FP16 (GPU)
- `use_roi_around_line`: boolean (non-RAW)
- `roi_margin_px`: integer
- `roi_gate_length_px`: integer
- `roi_safe_pad_px`: integer
- `detection_stride`: integer — jalankan deteksi setiap n frame (non-RAW)
- `predict_missing`: boolean — prediksi posisi track saat deteksi hilang sementara
- `max_prediction_frames`: integer
- `use_class_filter`: boolean — filter kelas kendaraan (non-RAW)
- `draw_paths`: boolean — gambar jejak lintasan (non-RAW)
- `max_path_points_drawn`: integer — jumlah titik jejak
- `flush_frames`: integer — "grab" frame kamera untuk kurangi lag
- `use_mss_screen_capture`: boolean — mss untuk screen capture
- `win_force_dpi_awareness`: boolean — DPI aware (Windows)

### Mode RAW
- `raw_detections_mode`: boolean — RAW-only (tanpa counting)
- `raw_counting_mode`: boolean — RAW visual + counting
- `raw_force_full_region`: boolean — deteksi full frame agar mirip skrip
- `raw_show_all_classes`: boolean — tampilkan semua kelas (jika false, hanya kendaraan saat render)
- `raw_conf`: float — threshold RAW
- `raw_iou`: float — IoU RAW (pengaruh NMS)
- `raw_draw_ids`: boolean — tampilkan Track ID pada bbox RAW (hanya saat `raw_counting_mode`)

### TRACKING_CONFIG (di `config.py`)
- `min_detection_size`: integer — minimal ukuran bbox untuk tracking
- `max_track_lost_frames`: integer — usia track sebelum dihapus
- `max_match_distance`: integer (px) — toleransi matching pusat bbox lintas frame