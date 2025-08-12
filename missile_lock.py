#!/usr/bin/env python3
"""
Missile-lock style YOLO object tracker with mouse target selection, smoothing, and lock indication.

Features:
- YOLOv8 detection + ByteTrack multi-object tracking (stable IDs)
- Click on a detection to "lock" it as your target
- Smooth aiming reticle that eases onto the target
- "LOCKED" state when the reticle is sufficiently centered on the target for N frames
- Simple reacquisition when the original ID is lost (match by IoU/nearest)
- Optional class filtering (e.g., --classes person,car)

Controls:
- Left-click: lock onto the clicked detection
- R: release (reset) target
- +/-: increase/decrease lock radius
- Q or ESC: quit

Requirements:
- Python 3.9+
- ultralytics, opencv-python, numpy
"""

import argparse
import time
import math
import sys
from collections import deque
from typing import Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO


# --------------------------- Drawing utilities ---------------------------

def draw_crosshair(img, center, color=(0, 255, 255), size=20, thickness=2):
    x, y = int(center[0]), int(center[1])
    cv2.line(img, (x - size, y), (x + size, y), color, thickness, cv2.LINE_AA)
    cv2.line(img, (x, y - size), (x, y + size), color, thickness, cv2.LINE_AA)


def draw_target_ring(img, center, radius, color=(0, 255, 255), thickness=2):
    cv2.circle(img, (int(center[0]), int(center[1])), int(radius), color, thickness, cv2.LINE_AA)


def draw_label(img, text, org, bg_color=(0, 0, 0), fg_color=(255, 255, 255), scale=0.5, thickness=1, pad=4):
    (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    x, y = int(org[0]), int(org[1])
    cv2.rectangle(img, (x, y - th - 2 * pad), (x + tw + 2 * pad, y + bl), bg_color, -1)
    cv2.putText(img, text, (x + pad, y - pad), cv2.FONT_HERSHEY_SIMPLEX, scale, fg_color, thickness, cv2.LINE_AA)


def iou_xyxy(a, b):
    # a, b: [x1, y1, x2, y2]
    xi1 = max(a[0], b[0])
    yi1 = max(a[1], b[1])
    xi2 = min(a[2], b[2])
    yi2 = min(a[3], b[3])
    inter = max(0.0, xi2 - xi1) * max(0.0, yi2 - yi1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter + 1e-6
    return inter / union


# --------------------------- Target state ---------------------------

class TargetState:
    def __init__(self):
        self.id: Optional[int] = None          # tracker ID to follow
        self.cls: Optional[int] = None         # class id (for reacquisition)
        self.name: Optional[str] = None        # class name
        self.last_box: Optional[np.ndarray] = None  # last xyxy
        self.last_center: Optional[Tuple[float, float]] = None
        self.center_history = deque(maxlen=15)
        self.lost_frames: int = 0
        self.lock_frames: int = 0

    def reset(self):
        self.__init__()


# --------------------------- Mouse handling ---------------------------

class MouseState:
    def __init__(self):
        self.click_point: Optional[Tuple[int, int]] = None
        self.select_requested: bool = False

    def on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.click_point = (x, y)
            self.select_requested = True


# --------------------------- Main loop ---------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="Missile-lock style YOLO tracker")
    ap.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path or name (e.g., yolov8n.pt)")
    ap.add_argument("--source", type=str, default="0", help="Video source: index like '0' for webcam or path to file/URL")
    ap.add_argument("--imgsz", type=int, default=960, help="Inference image size")
    ap.add_argument("--conf", type=float, default=0.35, help="Confidence threshold")
    ap.add_argument("--iou", type=float, default=0.5, help="NMS IoU threshold")
    ap.add_argument("--device", type=str, default=None, help="Device: 'cpu' or like '0' for GPU")
    ap.add_argument("--classes", type=str, default="", help="Only detect these classes (comma-separated names or ids)")
    ap.add_argument("--display-scale", type=float, default=1.0, help="Scale factor for display window")
    ap.add_argument("--lock-radius", type=float, default=40.0, help="Pixels radius to consider 'centered' for lock")
    ap.add_argument("--lock-hold-frames", type=int, default=15, help="Consecutive frames within radius to declare LOCKED")
    ap.add_argument("--aim-smooth", type=float, default=6.0, help="Aiming smoothing gain (higher snaps faster)")
    ap.add_argument("--predict-lead", type=float, default=0.25, help="Seconds of linear lead to visualize")
    ap.add_argument("--no-boxes", action="store_true", help="Do not render YOLO boxes, only reticle overlay")
    return ap.parse_args()


def map_classes_arg(names_map, arg: str):
    if not arg:
        return None
    raw = [s.strip() for s in arg.split(",") if s.strip() != ""]
    out = []
    name_to_id = {v: k for k, v in names_map.items()}
    for token in raw:
        if token.isdigit():
            out.append(int(token))
        else:
            if token in name_to_id:
                out.append(name_to_id[token])
            else:
                # try case-insensitive match
                candidates = [k for k, v in names_map.items() if v.lower() == token.lower()]
                if candidates:
                    out.append(candidates[0])
                else:
                    print(f"[WARN] Unknown class '{token}' ignored.")
    return sorted(list(set(out))) if out else None


def main():
    args = parse_args()

    # Prepare source
    source = args.source
    if source.isdigit():
        source = int(source)

    model = YOLO(args.model)
    names = model.names

    class_ids = map_classes_arg(names, args.classes)

    # Mouse/window setup
    window_name = "Missile Lock Tracker"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    mouse = MouseState()
    cv2.setMouseCallback(window_name, mouse.on_mouse)

    # Tracking state
    target = TargetState()

    # Aiming reticle state (start at center later once frame known)
    aim_pos = None
    last_time = None

    # Start tracker stream
    stream = model.track(
        source=source,
        stream=True,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        classes=class_ids,
        tracker="bytetrack.yaml",
        verbose=False,
        persist=True,
    )

    print("Controls: Left-click to lock, 'R' to reset, '+'/'-' to change lock radius, 'Q' or ESC to quit.")
    for result in stream:
        # Raw frame and boxes
        frame = result.orig_img  # BGR
        if frame is None:
            continue

        if aim_pos is None:
            h, w = frame.shape[:2]
            aim_pos = (w / 2.0, h / 2.0)
            last_time = time.time()

        if not args.no_boxes:
            # Use YOLO's nice annotations as a base
            canvas = result.plot(conf=False, line_width=2)
        else:
            canvas = frame.copy()

        boxes = result.boxes
        det_xyxy = []
        det_conf = []
        det_cls = []
        det_id = []

        if boxes is not None and len(boxes) > 0:
            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy() if boxes.conf is not None else np.ones((len(boxes),), dtype=float)
            cls = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else np.zeros((len(boxes),), dtype=int)
            if boxes.id is not None:
                ids = boxes.id.cpu().numpy().astype(int)
            else:
                ids = np.array([-1] * len(boxes), dtype=int)

            det_xyxy = [xyxy[i] for i in range(len(xyxy))]
            det_conf = [float(conf[i]) for i in range(len(conf))]
            det_cls = [int(cls[i]) for i in range(len(cls))]
            det_id = [int(ids[i]) for i in range(len(ids))]

            # Handle mouse click to select target
            if mouse.select_requested:
                mouse.select_requested = False
                if mouse.click_point is not None:
                    cx, cy = mouse.click_point
                    # Candidates containing the click
                    candidates = []
                    for i, b in enumerate(det_xyxy):
                        if cx >= b[0] and cy >= b[1] and cx <= b[2] and cy <= b[3]:
                            bx = (b[0] + b[2]) / 2.0
                            by = (b[1] + b[3]) / 2.0
                            d2 = (bx - cx) ** 2 + (by - cy) ** 2
                            candidates.append((d2, i))
                    if candidates:
                        _, best_i = min(candidates, key=lambda t: t[0])
                        target.id = det_id[best_i] if det_id[best_i] != -1 else None
                        target.cls = det_cls[best_i]
                        target.name = names.get(target.cls, str(target.cls))
                        target.last_box = np.array(det_xyxy[best_i], dtype=float)
                        bx, by = (target.last_box[0] + target.last_box[2]) / 2.0, (target.last_box[1] + target.last_box[3]) / 2.0
                        target.last_center = (bx, by)
                        target.center_history.clear()
                        target.center_history.append(target.last_center)
                        target.lost_frames = 0
                        target.lock_frames = 0
                        print(f"[INFO] Target selected: id={target.id} class={target.name} conf={det_conf[best_i]:.2f}")
                    else:
                        print("[INFO] Click did not hit any detection.")

        # Compute dt for smoothing
        now = time.time()
        dt = max(1e-3, now - (last_time if last_time else now))
        last_time = now

        # If we have a target, update its state from current frame (by ID) or attempt reacquire
        target_center = None
        target_visible = False

        if target.cls is not None:
            # Try to find current frame's target box
            match_idx = -1
            if target.id is not None and len(det_id) > 0:
                # Exact ID match
                for i, tid in enumerate(det_id):
                    if tid == target.id:
                        match_idx = i
                        break

            if match_idx == -1 and len(det_xyxy) > 0 and target.last_box is not None:
                # ID lost; try reacquire by highest IoU among same class, else nearest center
                best_score = 0.0
                best_i = -1
                # Prefer same class
                for i, b in enumerate(det_xyxy):
                    if det_cls[i] == target.cls:
                        score = iou_xyxy(target.last_box, b)
                        if score > best_score:
                            best_score = score
                            best_i = i
                # If weak IoU match, fallback to nearest center among same class
                if best_i == -1 or best_score < 0.05:
                    best_dist = 1e9
                    for i, b in enumerate(det_xyxy):
                        if det_cls[i] == target.cls:
                            bx, by = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
                            lx, ly = target.last_center if target.last_center else (bx, by)
                            d2 = (bx - lx) ** 2 + (by - ly) ** 2
                            if d2 < best_dist:
                                best_dist = d2
                                best_i = i
                match_idx = best_i

            if match_idx != -1:
                b = np.array(det_xyxy[match_idx], dtype=float)
                target.last_box = b
                target.id = det_id[match_idx] if det_id[match_idx] != -1 else target.id  # update id if available
                bx, by = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
                target.last_center = (bx, by)
                target.center_history.append(target.last_center)
                target.lost_frames = 0
                target_visible = True
                target_center = target.last_center
            else:
                target.lost_frames += 1
                # Decay history a bit to keep prediction sensible
                if target.center_history:
                    target.center_history.append(target.center_history[-1])

        # Aim smoothing (move aim_pos toward target_center)
        if target_center is not None:
            # Time-based smoothing: alpha = 1 - exp(-k*dt)
            k = float(args.aim_smooth)
            alpha = 1.0 - math.exp(-k * dt)
            ax = aim_pos[0] + alpha * (target_center[0] - aim_pos[0])
            ay = aim_pos[1] + alpha * (target_center[1] - aim_pos[1])
            aim_pos = (ax, ay)

        # Lock logic
        locked = False
        if target_center is not None:
            dx = aim_pos[0] - target_center[0]
            dy = aim_pos[1] - target_center[1]
            dist = math.hypot(dx, dy)
            if dist <= args.lock_radius:
                target.lock_frames += 1
            else:
                target.lock_frames = max(0, target.lock_frames - 1)  # mild hysteresis
            locked = target.lock_frames >= args.lock_hold_frames
        else:
            target.lock_frames = max(0, target.lock_frames - 1)
            locked = False

        # Draw overlay
        h, w = canvas.shape[:2]
        # Aim reticle
        ring_color = (0, 0, 255) if locked else ((0, 255, 0) if target_center is not None else (0, 255, 255))
        draw_target_ring(canvas, aim_pos, args.lock_radius, ring_color, 2)
        draw_crosshair(canvas, aim_pos, ring_color, size=16, thickness=2)

        # Target line/label
        status_text = "NO TARGET"
        if target.cls is not None:
            if target_visible:
                status_text = f"TARGET {target.name}  ID={target.id if target.id is not None else '-'}"
            else:
                status_text = f"TARGET LOST ({target.name}) {target.lost_frames}f"
        if locked:
            status_text += "  [LOCKED]"

        # Predict simple lead and draw point
        if target_center is not None and len(target.center_history) >= 2 and args.predict_lead > 0:
            # Estimate velocity (px/s)
            # Use average of last N differences to reduce noise
            pts = list(target.center_history)
            diffs = [(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1)]
            if diffs:
                vx = sum(d[0] for d in diffs) / len(diffs) / max(dt, 1e-3)
                vy = sum(d[1] for d in diffs) / len(diffs) / max(dt, 1e-3)
                px = int(np.clip(target_center[0] + vx * args.predict_lead, 0, w-1))
                py = int(np.clip(target_center[1] + vy * args.predict_lead, 0, h-1))
                cv2.circle(canvas, (px, py), 4, (255, 255, 0), -1, cv2.LINE_AA)
                cv2.line(canvas, (int(target_center[0]), int(target_center[1])), (px, py), (255, 255, 0), 1, cv2.LINE_AA)

        # Draw a line from aim to target
        if target_center is not None:
            cv2.line(canvas, (int(aim_pos[0]), int(aim_pos[1])), (int(target_center[0]), int(target_center[1])), (200, 200, 200), 1, cv2.LINE_AA)

        # Heads-up info
        draw_label(
            canvas,
            f"{status_text} | lock_radius={int(args.lock_radius)} px",
            (10, 30),
            bg_color=(0, 0, 0),
            fg_color=(255, 255, 255),
            scale=0.6,
            thickness=1
        )

        disp = canvas
        if args.display_scale and args.display_scale != 1.0:
            disp = cv2.resize(disp, (int(disp.shape[1] * args.display_scale), int(disp.shape[0] * args.display_scale)), interpolation=cv2.INTER_LINEAR)

        cv2.imshow(window_name, disp)
        key = cv2.waitKey(1) & 0xFF

        if key in (27, ord('q'), ord('Q')):  # ESC or Q
            break
        elif key in (ord('r'), ord('R')):
            print("[INFO] Target reset.")
            target.reset()
        elif key == ord('+') or key == ord('='):
            args.lock_radius = min(300.0, args.lock_radius + 5.0)
        elif key == ord('-') or key == ord('_'):
            args.lock_radius = max(5.0, args.lock_radius - 5.0)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        sys.exit(0)