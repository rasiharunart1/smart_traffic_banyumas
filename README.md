# Smart Traffic Counter v3.3

Real-time vehicle detection and directional counting with a modern Tkinter GUI, powered by Ultralytics YOLO. Supports Screen capture, Webcam, and Network streams. Includes RAW visualization mode with active counting, database save, data viewer, and Windows .exe packaging.

- App name: SmartTrafficCounter
- Default model: yolo11n.pt
- Output (exe): dist/SmartTrafficCounter/SmartTrafficCounter.exe

## Table of Contents
- [Features](#features)
- [System Requirements](#system-requirements)
- [Quick Start (Run the .exe)](#quick-start-run-the-exe)
- [Build the .exe (Windows, PyInstaller)](#build-the-exe-windows-pyinstaller)
- [Usage Guide](#usage-guide)
- [Modes](#modes)
- [Key Settings](#key-settings)
- [Database](#database)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [License](#license)

## Features
- Multi-input:
  - Screen region capture (select region/fullscreen)
  - Webcam
  - Network stream (RTSP/HTTP)
- RAW + Counting mode:
  - Show YOLO RAW bounding boxes exactly like baseline scripts
  - Counting stays active via tracker in the background
  - Optional Track ID labels on RAW boxes
- RAW-only mode (no counting) and Tracking mode (non-RAW) with ID/path rendering
- Directional counting (UP/DOWN) using a single user-drawn counting line
- ROI optimization (non-RAW), FPS controls, screen capture via mss
- Database integration (SQLite/MySQL), Data Viewer, backup/restore
- Settings persisted in settings.json

## System Requirements
- Windows 10/11 64-bit
- CPU: modern Intel/AMD; GPU NVIDIA optional for CUDA acceleration
- RAM: 8 GB minimum (16 GB recommended)
- Disk: ≥ 2 GB free (Torch/OpenCV are large)
- If using GPU: NVIDIA driver + Torch CUDA build that matches your system

## Quick Start (Run the .exe)
- After building (see below), open:
  - `dist/SmartTrafficCounter/`
- Double-click:
  - `SmartTrafficCounter.exe`
- Notes:
  - If SmartScreen appears, click "More info" → "Run anyway"
  - `settings.json` is created in the working folder on first run
  - `yolo11n.pt` should be alongside the exe (already bundled if using the provided spec)

## Build the .exe (Windows, PyInstaller)
Prerequisites:
- Python 3.9–3.11 recommended
- A virtual environment (.venv) in the repo (optional but recommended)

Quick steps (from repository root):
1) Create and activate venv
- `python -m venv .venv`
- `.venv\Scripts\activate`
- `python -m pip install --upgrade pip`

2) Install tools and dependencies (minimal for build)
- `pip install pyinstaller ultralytics torch torchvision opencv-python numpy Pillow mss pyautogui`

3) Build using the provided spec (recommended onedir)
- `python -m PyInstaller --noconfirm --clean SmartTrafficCounter.spec`

4) Run
- `explorer dist\SmartTrafficCounter`
- Double‑click `SmartTrafficCounter.exe`

Onefile build (optional):
- Onefile requires small path handling changes for model/resources (not included here). Onedir is recommended for simplicity and reliability.

Where is the exe?
- `dist/SmartTrafficCounter/SmartTrafficCounter.exe`

## Usage Guide
1) Select Input Source:
- Screen: "Select Region" or "Full Screen", then "Start Preview"
- Webcam: choose index (0/1/…), then "Start Preview"
- Network: paste Stream URL, then "Start Preview"

2) Draw the Counting Line (one line):
- Click "Draw Line", click-and-drag on the video, release to set
- If UP/DOWN is inverted from your expectation, toggle "invert_direction" in Line Settings

3) Start Detection:
- Click "Start Detection"
- Default mode is RAW + Counting (RAW boxes rendered; counting active)

4) Save Results:
- Click "Save to Database" and view data in "Data Viewer"

## Modes
- RAW + Counting (default)
  - Renders RAW detections from YOLO
  - Tracker runs in the background for counting
  - Optional: show Track ID in RAW labels (`runtime.raw_draw_ids=true`)
- RAW-only
  - Shows RAW boxes only (no tracker, no counting)
- Tracking (non-RAW)
  - Renders tracker boxes + IDs + paths; counting active

Tip: For dense scenes (vehicles side-by-side), increase `runtime.raw_iou` (e.g., 0.70 → 0.75) so NMS doesn't merge nearby boxes.

## Key Settings
All settings persist in `settings.json`.

- model
  - `model_path`: "yolo11n.pt"
  - `confidence_threshold`, `iou_threshold`: non-RAW
  - `detection_confidence`: filter passed to tracker
  - `device`: "auto" | "cpu" | "cuda"
- input
  - `type`: "screen" | "webcam" | "network"
  - `webcam_index`, `stream_url`, `screen_region`
- line_settings
  - `band_px`: 12–18 recommended
  - `invert_direction`: flip UP/DOWN interpretation if needed
- runtime
  - `imgsz`: 576 (tune for FPS/accuracy)
  - `use_half`: true on CUDA (FP16)
  - `use_roi_around_line`: optimize non-RAW
  - RAW:
    - `raw_detections_mode`: RAW-only
    - `raw_counting_mode`: RAW visual + counting (default true)
    - `raw_force_full_region`: true for "script-like" behavior
    - `raw_show_all_classes`: false → only vehicles when rendering
    - `raw_conf`: 0.25
    - `raw_iou`: 0.70 (raise if boxes merge)
    - `raw_draw_ids`: true to show Track ID on RAW labels

Tracking tuning (in `config.py` → `TRACKING_CONFIG`):
- `max_match_distance`: lower (50–60) if IDs merge in dense traffic
- `max_track_lost_frames`: track persistence

## Database
- SQLite (default) or MySQL supported
- Use "DB Settings" in the app to configure
- "Save to Database" stores UP/DOWN totals per class and globally
- "Data Viewer" shows saved history; Backup/Restore available

## Troubleshooting
- No `dist/` or exe: you haven't built yet. Run PyInstaller with the spec above.
- RAW boxes not showing:
  - Ensure `runtime.raw_counting_mode=true`
  - Ensure `raw_detections_mode=false`
  - Check `raw_conf=0.25`, `raw_iou=0.70`
- Not counting when crossing:
  - Make sure the counting line crosses the traffic lane
  - Increase `band_px` (12–18)
  - Toggle `invert_direction` if needed
- Three adjacent vehicles counted as < 3:
  - Raise `runtime.raw_iou` to 0.75; consider lowering `max_match_distance`
- Low FPS:
  - Lower `imgsz` to 512/448
  - Disable `raw_draw_ids`
  - Use CUDA build of Torch

## Documentation
- Full User Manual: [docs/User_Manual_SmartTrafficCounter.md](docs/User_Manual_SmartTrafficCounter.md)
- Quick Start: [docs/Quick_Start_CheatSheet.md](docs/Quick_Start_CheatSheet.md)
- Troubleshooting & FAQ: [docs/Troubleshooting_FAQ.md](docs/Troubleshooting_FAQ.md)
- Settings Reference: [docs/Settings_Reference.md](docs/Settings_Reference.md)
- Release Notes v3.3: [docs/Release_Notes_v3.3.md](docs/Release_Notes_v3.3.md)

## License
Specify your project license here (e.g., MIT). If unsure, add a LICENSE file to the repo.
