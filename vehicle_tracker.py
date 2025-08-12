from typing import List, Dict, Any, Tuple
import math
from collections import deque
from config import CLASS_NAMES, TRACKING_CONFIG

class VehicleTracker:
    def __init__(self):
        self.next_id = 1
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.counts = {
            "up": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
            "down": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
            "total_up": 0,
            "total_down": 0
        }

    def reset_counts(self):
        for k in self.counts["up"].keys():
            self.counts["up"][k] = 0
            self.counts["down"][k] = 0
        self.counts["total_up"] = 0
        self.counts["total_down"] = 0
        for tid in list(self.tracks.keys()):
            self.tracks[tid]["is_counted"] = False
            self.tracks[tid]["last_side"] = None
            self.tracks[tid]["missed"] = 0

    def update_tracking(self, detections: List[Dict[str, Any]]):
        for t in self.tracks.values():
            t["age"] += 1
            t["_updated"] = False

        used = set()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            best_id = None
            best_dist = 1e9
            for tid, tr in self.tracks.items():
                if tid in used:
                    continue
                tx1, ty1, tx2, ty2 = tr["bbox"]
                tcx, tcy = (tx1 + tx2) // 2, (ty1 + ty2) // 2
                d = math.hypot(cx - tcx, cy - tcy)
                if d < best_dist and d <= TRACKING_CONFIG["max_match_distance"]:
                    best_dist = d
                    best_id = tid

            if best_id is None:
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {
                    "bbox": det["bbox"],
                    "class": det["class"],
                    "confidence": det["confidence"],
                    "path": deque(maxlen=64),
                    "is_counted": False,
                    "age": 0,
                    "last_side": None,
                    "missed": 0,
                    "_updated": True
                }
                bx1, by1, bx2, by2 = det["bbox"]
                self.tracks[tid]["path"].append(((bx1 + bx2) // 2, (by1 + by2) // 2))
                used.add(tid)
            else:
                tr = self.tracks[best_id]
                tr["bbox"] = det["bbox"]
                tr["class"] = det["class"]
                tr["confidence"] = det["confidence"]
                tr["age"] = 0
                tr["missed"] = 0
                bx1, by1, bx2, by2 = det["bbox"]
                tr["path"].append(((bx1 + bx2) // 2, (by1 + by2) // 2))
                tr["_updated"] = True
                used.add(best_id)

        do_predict = TRACKING_CONFIG.get("predict_missing", False)
        max_pred = int(TRACKING_CONFIG.get("max_prediction_frames", 1))
        for tid, tr in list(self.tracks.items()):
            if tr.get("_updated"):
                continue
            tr["missed"] = tr.get("missed", 0) + 1
            if do_predict and tr["missed"] <= max_pred:
                path = list(tr["path"])
                if len(path) >= 2:
                    (x0, y0), (x1, y1) = path[-2], path[-1]
                    vx, vy = (x1 - x0), (y1 - y0)
                    bx1, by1, bx2, by2 = tr["bbox"]
                    nb = [int(bx1 + vx), int(by1 + vy), int(bx2 + vx), int(by2 + vy)]
                    tr["bbox"] = nb
                    tr["path"].append((int(x1 + vx), int(y1 + vy)))
                else:
                    if tr["path"]:
                        tr["path"].append(tr["path"][-1])

        stale = [tid for tid, tr in self.tracks.items() if tr["age"] > TRACKING_CONFIG["max_track_lost_frames"]]
        for tid in stale:
            self.tracks.pop(tid, None)

    # ===== directional crossing =====
    def _line_vec(self, line):
        (x1, y1), (x2, y2) = line
        vx, vy = (x2 - x1), (y2 - y1)
        L2 = vx * vx + vy * vy
        L = math.sqrt(L2) if L2 > 0 else 1.0
        nx, ny = (-vy / L, vx / L)
        return (x1, y1, x2, y2, vx, vy, L2, L, nx, ny)

    def _signed_distance_px(self, p, line_geom) -> float:
        x, y = p
        x1, y1, x2, y2, vx, vy, L2, L, nx, ny = line_geom
        cross = vx * (y - y1) - vy * (x - x1)
        return cross / (L if L != 0 else 1.0)

    def _projection_t(self, p, line_geom) -> float:
        x, y = p
        x1, y1, x2, y2, vx, vy, L2, L, nx, ny = line_geom
        if L2 == 0:
            return 0.0
        return ((x - x1) * vx + (y - y1) * vy) / L2

    def check_line_crossings_directional(self, line, line_settings) -> bool:
        if not line:
            return False
        changed = False

        band_px = int(line_settings.get("band_px", 12))
        invert_dir = bool(line_settings.get("invert_direction", False))

        geom = self._line_vec(line)
        nx, ny = geom[8], geom[9]

        for tid, tr in self.tracks.items():
            path = list(tr["path"])
            if len(path) < 2 or tr.get("is_counted", False):
                continue

            prev_pt = path[-2]
            last_pt = path[-1]

            d_prev = self._signed_distance_px(prev_pt, geom)
            d_now = self._signed_distance_px(last_pt, geom)

            if d_prev == 0:
                d_prev = 1e-6
            if d_now == 0:
                d_now = -1e-6

            if d_prev * d_now < 0:
                if min(abs(d_prev), abs(d_now)) <= band_px + 2:
                    mid_pt = ((prev_pt[0] + last_pt[0]) * 0.5, (prev_pt[1] + last_pt[1]) * 0.5)
                    t_mid = self._projection_t(mid_pt, geom)
                    if -0.1 <= t_mid <= 1.1:
                        mvx = last_pt[0] - prev_pt[0]
                        mvy = last_pt[1] - prev_pt[1]
                        dot_mn = mvx * nx + mvy * ny
                        if invert_dir:
                            dot_mn = -dot_mn
                        direction = "up" if dot_mn < 0 else "down"

                        cname = CLASS_NAMES.get(tr["class"], "car")
                        if direction == "up":
                            tr["is_counted"] = True
                            self.counts["up"][cname] = self.counts["up"].get(cname, 0) + 1
                            self.counts["total_up"] += 1
                        else:
                            tr["is_counted"] = True
                            self.counts["down"][cname] = self.counts["down"].get(cname, 0) + 1
                            self.counts["total_down"] += 1
                        changed = True

        return changed

    def get_tracked_vehicles_with_status(self) -> Dict[int, Dict[str, Any]]:
        out = {}
        for tid, tr in self.tracks.items():
            out[tid] = {
                "bbox": tr["bbox"],
                "class": tr["class"],
                "confidence": tr["confidence"],
                "path": list(tr["path"]),
                "is_counted": tr["is_counted"],
                "age": tr.get("age", 0),
                "missed": tr.get("missed", 0)
            }
        return out

    def get_counts(self) -> Dict[str, Any]:
        return {
            "up": dict(self.counts["up"]),
            "down": dict(self.counts["down"]),
            "total_up": int(self.counts["total_up"]),
            "total_down": int(self.counts["total_down"])
        }