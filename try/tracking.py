from dataclasses import dataclass
from typing import List, Optional, Tuple
import itertools
import numpy as np


@dataclass
class Track:
    id: int
    bbox: Tuple[float, float, float, float]  # x1,y1,x2,y2
    centroid: Tuple[float, float]
    prev_centroid: Optional[Tuple[float, float]]
    label: str
    conf: float
    missing: int = 0


class SimpleTracker:
    """
    Pelacak sederhana berbasis nearest-centroid matching.
    - Cocok untuk FPS realtime dan jumlah objek moderat.
    - Tidak sekuat ByteTrack/SORT, namun tanpa dependensi eksternal.

    Parameter:
    - max_missing: jumlah frame tanpa kecocokan sebelum track dihapus.
    - max_dist: jarak maksimum (piksel) untuk mencocokkan deteksi dengan track yang ada.
    """
    def __init__(self, max_missing: int = 15, max_dist: float = 60.0):
        self.max_missing = max_missing
        self.max_dist = max_dist
        self.tracks: List[Track] = []
        self._next_id = itertools.count(1)

    def reset(self):
        self.tracks = []
        self._next_id = itertools.count(1)

    def update(self, detections: List[List[float]], labels: List[str], confs: List[float]) -> List[Track]:
        # detections: list of [x1,y1,x2,y2]
        det_centroids = [((d[0]+d[2])/2.0, (d[1]+d[3])/2.0) for d in detections]
        det_used = [False]*len(detections)
        tr_used = [False]*len(self.tracks)

        # Build distance matrix
        if self.tracks and detections:
            dist = np.zeros((len(self.tracks), len(detections)), dtype=np.float32)
            for i, tr in enumerate(self.tracks):
                tx, ty = tr.centroid
                for j, (cx, cy) in enumerate(det_centroids):
                    dist[i, j] = np.hypot(tx - cx, ty - cy)
            # Greedy matching by min distance
            pairs = []
            for _ in range(min(len(self.tracks), len(detections))):
                i, j = np.unravel_index(np.argmin(dist, axis=None), dist.shape)
                if np.isinf(dist[i, j]) or dist[i, j] > self.max_dist:
                    break
                pairs.append((i, j))
                dist[i, :] = np.inf
                dist[:, j] = np.inf
            # Apply matches
            for i, j in pairs:
                tr = self.tracks[i]
                tr.prev_centroid = tr.centroid
                tr.centroid = det_centroids[j]
                tr.bbox = tuple(detections[j])
                tr.label = labels[j]
                tr.conf = confs[j]
                tr.missing = 0
                tr_used[i] = True
                det_used[j] = True

        # Unmatched detections -> new tracks
        for j, used in enumerate(det_used):
            if not used:
                cx, cy = det_centroids[j]
                new_tr = Track(
                    id=next(self._next_id),
                    bbox=tuple(detections[j]),
                    centroid=(cx, cy),
                    prev_centroid=None,
                    label=labels[j],
                    conf=confs[j],
                    missing=0
                )
                self.tracks.append(new_tr)

        # Unmatched tracks -> increase missing
        for i, tr in enumerate(self.tracks):
            if not tr_used[i]:
                tr.missing += 1

        # Remove old tracks
        self.tracks = [t for t in self.tracks if t.missing <= self.max_missing]

        return list(self.tracks)