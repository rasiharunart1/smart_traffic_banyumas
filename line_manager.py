"""
Line Manager for Smart Traffic Counter
Handles counting lines, multi-line support, and intersection detection
"""

import math
from typing import List, Tuple, Dict, Any, Optional, Set
from dataclasses import dataclass
import json
from pathlib import Path

from config_manager import LineConfig
from utils.logger import get_logger
from utils.validators import validate_coordinates


@dataclass
class CountingLine:
    """Represents a counting line for vehicle detection"""
    
    id: str
    name: str
    start_point: Tuple[int, int]  # (x1, y1)
    end_point: Tuple[int, int]    # (x2, y2)
    config: LineConfig
    enabled: bool = True
    vehicle_counts: Dict[str, int] = None  # {vehicle_type: count}
    
    def __post_init__(self):
        if self.vehicle_counts is None:
            self.vehicle_counts = {
                'car': 0,
                'motorcycle': 0,
                'bus': 0,
                'truck': 0,
                'total': 0
            }
    
    @property
    def center_point(self) -> Tuple[int, int]:
        """Get center point of the line"""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))
    
    @property
    def length(self) -> float:
        """Calculate line length"""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    @property
    def angle(self) -> float:
        """Calculate line angle in degrees"""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        return math.degrees(math.atan2(y2 - y1, x2 - x1))
    
    def distance_to_point(self, point: Tuple[int, int]) -> float:
        """Calculate perpendicular distance from point to line"""
        x0, y0 = point
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        
        # Line equation: Ax + By + C = 0
        A = y2 - y1
        B = x1 - x2
        C = x2 * y1 - x1 * y2
        
        # Distance formula
        distance = abs(A * x0 + B * y0 + C) / math.sqrt(A * A + B * B)
        return distance
    
    def is_point_near_line(self, point: Tuple[int, int], threshold: Optional[int] = None) -> bool:
        """Check if point is within detection threshold of the line"""
        threshold = threshold or self.config.detection_threshold
        return self.distance_to_point(point) <= threshold
    
    def reset_counts(self) -> None:
        """Reset all vehicle counts"""
        for key in self.vehicle_counts:
            self.vehicle_counts[key] = 0
    
    def increment_count(self, vehicle_type: str) -> None:
        """Increment count for specific vehicle type"""
        if vehicle_type in self.vehicle_counts:
            self.vehicle_counts[vehicle_type] += 1
            self.vehicle_counts['total'] += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'start_point': self.start_point,
            'end_point': self.end_point,
            'enabled': self.enabled,
            'vehicle_counts': self.vehicle_counts,
            'config': {
                'line_color': self.config.line_color,
                'line_thickness': self.config.line_thickness,
                'line_style': self.config.line_style,
                'show_label': self.config.show_label,
                'label_text': self.config.label_text,
                'detection_threshold': self.config.detection_threshold,
                'line_type': self.config.line_type
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CountingLine':
        """Create CountingLine from dictionary"""
        config_data = data.get('config', {})
        config = LineConfig(**config_data)
        
        return cls(
            id=data['id'],
            name=data['name'],
            start_point=tuple(data['start_point']),
            end_point=tuple(data['end_point']),
            config=config,
            enabled=data.get('enabled', True),
            vehicle_counts=data.get('vehicle_counts')
        )


class LineIntersectionTracker:
    """Tracks vehicle intersections with counting lines"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.vehicle_histories: Dict[int, List[Tuple[int, int]]] = {}  # {track_id: [positions]}
        self.crossed_lines: Dict[int, Set[str]] = {}  # {track_id: {line_ids}}
    
    def update_vehicle_position(self, track_id: int, center_point: Tuple[int, int]) -> None:
        """Update vehicle position history"""
        if track_id not in self.vehicle_histories:
            self.vehicle_histories[track_id] = []
            self.crossed_lines[track_id] = set()
        
        self.vehicle_histories[track_id].append(center_point)
        
        # Limit history size
        if len(self.vehicle_histories[track_id]) > self.max_history:
            self.vehicle_histories[track_id].pop(0)
    
    def check_line_crossing(self, track_id: int, line: CountingLine) -> bool:
        """
        Check if vehicle has crossed the counting line
        Returns True if crossing detected (and not already counted)
        """
        if track_id not in self.vehicle_histories or len(self.vehicle_histories[track_id]) < 2:
            return False
        
        # Check if already counted for this line
        if line.id in self.crossed_lines[track_id]:
            return False
        
        history = self.vehicle_histories[track_id]
        
        # Check if vehicle path intersects with line
        for i in range(len(history) - 1):
            p1 = history[i]
            p2 = history[i + 1]
            
            if self._lines_intersect(p1, p2, line.start_point, line.end_point):
                # Mark as crossed to prevent double counting
                self.crossed_lines[track_id].add(line.id)
                return True
        
        return False
    
    def _lines_intersect(self, p1: Tuple[int, int], p2: Tuple[int, int], 
                        p3: Tuple[int, int], p4: Tuple[int, int]) -> bool:
        """Check if two line segments intersect"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return False  # Lines are parallel
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def remove_vehicle(self, track_id: int) -> None:
        """Remove vehicle from tracking when it disappears"""
        self.vehicle_histories.pop(track_id, None)
        self.crossed_lines.pop(track_id, None)
    
    def cleanup_old_vehicles(self, active_track_ids: Set[int]) -> None:
        """Remove tracking data for vehicles no longer active"""
        inactive_ids = set(self.vehicle_histories.keys()) - active_track_ids
        for track_id in inactive_ids:
            self.remove_vehicle(track_id)


class LineManager:
    """Manages multiple counting lines and intersection detection"""
    
    def __init__(self, default_config: Optional[LineConfig] = None):
        self.logger = get_logger(__name__)
        self.default_config = default_config or LineConfig()
        
        self.lines: Dict[str, CountingLine] = {}
        self.intersection_tracker = LineIntersectionTracker()
        self.frame_width = 0
        self.frame_height = 0
        
        # Auto-save settings
        self.auto_save_enabled = True
        self.save_file = "counting_lines.json"
    
    def set_frame_dimensions(self, width: int, height: int) -> None:
        """Set frame dimensions for validation"""
        self.frame_width = width
        self.frame_height = height
    
    def add_line(self, name: str, start_point: Tuple[int, int], end_point: Tuple[int, int],
                 config: Optional[LineConfig] = None, line_id: Optional[str] = None) -> str:
        """
        Add a new counting line
        
        Args:
            name: Display name for the line
            start_point: Line start coordinates (x1, y1)
            end_point: Line end coordinates (x2, y2)
            config: Line configuration (uses default if None)
            line_id: Optional specific ID (auto-generated if None)
            
        Returns:
            Line ID
        """
        # Validate coordinates if frame dimensions are set
        if self.frame_width > 0 and self.frame_height > 0:
            x1, y1 = start_point
            x2, y2 = end_point
            if not validate_coordinates(x1, y1, x2, y2, self.frame_width, self.frame_height):
                raise ValueError(f"Invalid line coordinates: {start_point} to {end_point}")
        
        # Generate unique ID if not provided
        if line_id is None:
            line_id = f"line_{len(self.lines) + 1}"
        
        # Ensure unique ID
        counter = 1
        original_id = line_id
        while line_id in self.lines:
            line_id = f"{original_id}_{counter}"
            counter += 1
        
        # Use provided config or default
        line_config = config or self.default_config
        
        # Create and store line
        line = CountingLine(
            id=line_id,
            name=name,
            start_point=start_point,
            end_point=end_point,
            config=line_config
        )
        
        self.lines[line_id] = line
        
        if self.auto_save_enabled:
            self.save_lines()
        
        self.logger.info(f"Added counting line '{name}' (ID: {line_id})")
        return line_id
    
    def remove_line(self, line_id: str) -> bool:
        """Remove a counting line"""
        if line_id in self.lines:
            line_name = self.lines[line_id].name
            del self.lines[line_id]
            
            if self.auto_save_enabled:
                self.save_lines()
            
            self.logger.info(f"Removed counting line '{line_name}' (ID: {line_id})")
            return True
        return False
    
    def get_line(self, line_id: str) -> Optional[CountingLine]:
        """Get a counting line by ID"""
        return self.lines.get(line_id)
    
    def get_all_lines(self) -> List[CountingLine]:
        """Get all counting lines"""
        return list(self.lines.values())
    
    def get_enabled_lines(self) -> List[CountingLine]:
        """Get only enabled counting lines"""
        return [line for line in self.lines.values() if line.enabled]
    
    def enable_line(self, line_id: str) -> bool:
        """Enable a counting line"""
        if line_id in self.lines:
            self.lines[line_id].enabled = True
            return True
        return False
    
    def disable_line(self, line_id: str) -> bool:
        """Disable a counting line"""
        if line_id in self.lines:
            self.lines[line_id].enabled = False
            return True
        return False
    
    def clear_all_lines(self) -> None:
        """Remove all counting lines"""
        self.lines.clear()
        
        if self.auto_save_enabled:
            self.save_lines()
        
        self.logger.info("Cleared all counting lines")
    
    def reset_all_counts(self) -> None:
        """Reset counts for all lines"""
        for line in self.lines.values():
            line.reset_counts()
        
        self.logger.info("Reset all line counts")
    
    def update_vehicle_tracking(self, track_id: int, center_point: Tuple[int, int], 
                               vehicle_type: str) -> List[str]:
        """
        Update vehicle position and check for line crossings
        
        Args:
            track_id: Unique vehicle tracking ID
            center_point: Vehicle center coordinates
            vehicle_type: Type of vehicle ('car', 'motorcycle', etc.)
            
        Returns:
            List of line IDs that were crossed
        """
        self.intersection_tracker.update_vehicle_position(track_id, center_point)
        
        crossed_lines = []
        for line in self.get_enabled_lines():
            if self.intersection_tracker.check_line_crossing(track_id, line):
                line.increment_count(vehicle_type)
                crossed_lines.append(line.id)
                self.logger.info(
                    f"Vehicle {track_id} ({vehicle_type}) crossed line '{line.name}'"
                )
        
        return crossed_lines
    
    def cleanup_tracking(self, active_track_ids: Set[int]) -> None:
        """Clean up tracking data for inactive vehicles"""
        self.intersection_tracker.cleanup_old_vehicles(active_track_ids)
    
    def get_total_counts(self) -> Dict[str, int]:
        """Get aggregated counts across all lines"""
        total_counts = {
            'car': 0,
            'motorcycle': 0,
            'bus': 0,
            'truck': 0,
            'total': 0
        }
        
        for line in self.lines.values():
            if line.enabled:
                for vehicle_type, count in line.vehicle_counts.items():
                    if vehicle_type in total_counts:
                        total_counts[vehicle_type] += count
        
        return total_counts
    
    def save_lines(self, file_path: Optional[str] = None) -> bool:
        """Save counting lines to file"""
        try:
            save_path = file_path or self.save_file
            data = {
                'lines': [line.to_dict() for line in self.lines.values()],
                'frame_dimensions': (self.frame_width, self.frame_height)
            }
            
            with open(save_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved {len(self.lines)} lines to {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save lines: {e}")
            return False
    
    def load_lines(self, file_path: Optional[str] = None) -> bool:
        """Load counting lines from file"""
        try:
            load_path = file_path or self.save_file
            if not Path(load_path).exists():
                self.logger.info(f"No saved lines file found at {load_path}")
                return False
            
            with open(load_path, 'r') as f:
                data = json.load(f)
            
            # Clear existing lines
            self.lines.clear()
            
            # Load lines
            lines_data = data.get('lines', [])
            for line_data in lines_data:
                line = CountingLine.from_dict(line_data)
                self.lines[line.id] = line
            
            # Load frame dimensions if available
            frame_dims = data.get('frame_dimensions')
            if frame_dims:
                self.frame_width, self.frame_height = frame_dims
            
            self.logger.info(f"Loaded {len(self.lines)} lines from {load_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load lines: {e}")
            return False
    
    def get_line_stats(self) -> Dict[str, Any]:
        """Get statistics about counting lines"""
        enabled_lines = [line for line in self.lines.values() if line.enabled]
        
        return {
            'total_lines': len(self.lines),
            'enabled_lines': len(enabled_lines),
            'total_counts': self.get_total_counts(),
            'lines_summary': [
                {
                    'id': line.id,
                    'name': line.name,
                    'enabled': line.enabled,
                    'total_count': line.vehicle_counts['total']
                }
                for line in self.lines.values()
            ]
        }