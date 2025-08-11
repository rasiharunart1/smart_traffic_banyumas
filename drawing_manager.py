"""
Drawing Manager for Smart Traffic Counter
Handles all visualization and drawing operations for the application
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image, ImageTk
import tkinter as tk

from detection_manager import Detection
from line_manager import CountingLine
from config_manager import ColorConfig
from utils.logger import get_logger


class DrawingManager:
    """Manages all drawing and visualization operations"""
    
    def __init__(self, color_config: Optional[ColorConfig] = None):
        self.logger = get_logger(__name__)
        self.colors = color_config or ColorConfig()
        
        # Font settings for text
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.font_thickness = 2
        
        # Drawing settings
        self.bbox_thickness = 2
        self.center_dot_radius = 4
        self.path_thickness = 2
    
    def draw_detections(self, frame: np.ndarray, detections: List[Detection], 
                       tracked_vehicles: Optional[Dict[int, Any]] = None) -> np.ndarray:
        """
        Draw vehicle detections on frame
        
        Args:
            frame: Input frame
            detections: List of Detection objects
            tracked_vehicles: Optional tracking information
            
        Returns:
            Frame with drawn detections
        """
        if not detections:
            return frame
        
        result_frame = frame.copy()
        
        for detection in detections:
            # Determine if vehicle is tracked/counted
            is_counted = False
            track_id = None
            
            if tracked_vehicles:
                # Find matching tracked vehicle (simplified matching by center proximity)
                for tid, vehicle_info in tracked_vehicles.items():
                    if 'center' in vehicle_info:
                        vehicle_center = vehicle_info['center']
                        distance = np.sqrt(
                            (detection.center[0] - vehicle_center[0]) ** 2 + 
                            (detection.center[1] - vehicle_center[1]) ** 2
                        )
                        if distance < 50:  # Threshold for matching
                            track_id = tid
                            is_counted = vehicle_info.get('counted', False)
                            break
            
            # Choose colors based on status
            bbox_color = self.colors.counted_vehicle if is_counted else self.colors.active_vehicle
            center_color = self.colors.center_dot_counted if is_counted else self.colors.center_dot_active
            
            # Draw bounding box
            self._draw_bounding_box(result_frame, detection, bbox_color, track_id)
            
            # Draw center point
            self._draw_center_point(result_frame, detection.center, center_color)
            
            # Draw tracking path if available
            if tracked_vehicles and track_id and 'path' in tracked_vehicles[track_id]:
                path = tracked_vehicles[track_id]['path']
                path_color = self.colors.tracking_path_counted if is_counted else self.colors.tracking_path
                self._draw_tracking_path(result_frame, path, path_color)
        
        return result_frame
    
    def _draw_bounding_box(self, frame: np.ndarray, detection: Detection, 
                          color: Tuple[int, int, int], track_id: Optional[int] = None) -> None:
        """Draw bounding box with labels"""
        x1, y1, x2, y2 = detection.bbox
        
        # Draw rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.bbox_thickness)
        
        # Prepare label text
        label_parts = [detection.class_name, f"{detection.confidence:.2f}"]
        if track_id is not None:
            label_parts.append(f"ID:{track_id}")
        label = " ".join(label_parts)
        
        # Calculate label size and position
        (label_width, label_height), baseline = cv2.getTextSize(
            label, self.font, self.font_scale, self.font_thickness
        )
        
        # Draw label background
        label_y = y1 - 10 if y1 - 10 > label_height else y1 + label_height + 10
        cv2.rectangle(
            frame,
            (x1, label_y - label_height - baseline),
            (x1 + label_width, label_y + baseline),
            color,
            -1
        )
        
        # Draw label text
        cv2.putText(
            frame, label, (x1, label_y - baseline),
            self.font, self.font_scale, (255, 255, 255), self.font_thickness
        )
    
    def _draw_center_point(self, frame: np.ndarray, center: Tuple[int, int], 
                          color: Tuple[int, int, int]) -> None:
        """Draw center point of detection"""
        cv2.circle(frame, center, self.center_dot_radius, color, -1)
    
    def _draw_tracking_path(self, frame: np.ndarray, path: List[Tuple[int, int]], 
                           color: Tuple[int, int, int]) -> None:
        """Draw vehicle tracking path"""
        if len(path) < 2:
            return
        
        # Draw path as connected lines
        for i in range(len(path) - 1):
            cv2.line(frame, path[i], path[i + 1], color, self.path_thickness)
    
    def draw_counting_lines(self, frame: np.ndarray, lines: List[CountingLine]) -> np.ndarray:
        """
        Draw counting lines on frame
        
        Args:
            frame: Input frame
            lines: List of counting lines
            
        Returns:
            Frame with drawn counting lines
        """
        if not lines:
            return frame
        
        result_frame = frame.copy()
        
        for line in lines:
            if not line.enabled:
                continue
            
            self._draw_counting_line(result_frame, line)
        
        return result_frame
    
    def _draw_counting_line(self, frame: np.ndarray, line: CountingLine) -> None:
        """Draw a single counting line with label"""
        # Parse color from hex string
        color_hex = line.config.line_color.lstrip('#')
        color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
        color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])  # Convert RGB to BGR
        
        # Draw line
        if line.config.line_style == 'dashed':
            self._draw_dashed_line(frame, line.start_point, line.end_point, 
                                  color_bgr, line.config.line_thickness)
        else:
            cv2.line(frame, line.start_point, line.end_point, 
                    color_bgr, line.config.line_thickness)
        
        # Draw label if enabled
        if line.config.show_label:
            self._draw_line_label(frame, line, color_bgr)
    
    def _draw_dashed_line(self, frame: np.ndarray, start: Tuple[int, int], 
                         end: Tuple[int, int], color: Tuple[int, int, int], 
                         thickness: int, dash_length: int = 10) -> None:
        """Draw dashed line"""
        x1, y1 = start
        x2, y2 = end
        
        # Calculate line length and direction
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        dx = (x2 - x1) / length
        dy = (y2 - y1) / length
        
        # Draw dashes
        current_pos = 0
        draw_dash = True
        
        while current_pos < length:
            next_pos = min(current_pos + dash_length, length)
            
            if draw_dash:
                start_x = int(x1 + dx * current_pos)
                start_y = int(y1 + dy * current_pos)
                end_x = int(x1 + dx * next_pos)
                end_y = int(y1 + dy * next_pos)
                
                cv2.line(frame, (start_x, start_y), (end_x, end_y), color, thickness)
            
            current_pos = next_pos
            draw_dash = not draw_dash
    
    def _draw_line_label(self, frame: np.ndarray, line: CountingLine, 
                        color: Tuple[int, int, int]) -> None:
        """Draw label for counting line"""
        # Calculate label position (middle of line, offset upward)
        center_x, center_y = line.center_point
        label_pos = (center_x, center_y - 15)
        
        # Prepare label text
        label = f"{line.config.label_text}: {line.vehicle_counts['total']}"
        
        # Calculate label size
        (label_width, label_height), baseline = cv2.getTextSize(
            label, self.font, self.font_scale, self.font_thickness
        )
        
        # Draw label background
        cv2.rectangle(
            frame,
            (label_pos[0] - label_width // 2 - 5, label_pos[1] - label_height - 5),
            (label_pos[0] + label_width // 2 + 5, label_pos[1] + 5),
            (0, 0, 0),  # Black background
            -1
        )
        
        # Draw label text
        cv2.putText(
            frame, label, 
            (label_pos[0] - label_width // 2, label_pos[1]),
            self.font, self.font_scale, color, self.font_thickness
        )
    
    def draw_statistics_overlay(self, frame: np.ndarray, stats: Dict[str, Any],
                               position: Tuple[int, int] = (10, 30)) -> np.ndarray:
        """
        Draw statistics overlay on frame
        
        Args:
            frame: Input frame
            stats: Statistics dictionary
            position: Top-left position for overlay
            
        Returns:
            Frame with statistics overlay
        """
        result_frame = frame.copy()
        x, y = position
        line_height = 25
        
        # Background for statistics
        overlay_height = len(stats) * line_height + 20
        overlay_width = 250
        
        # Semi-transparent background
        overlay = result_frame.copy()
        cv2.rectangle(overlay, (x - 10, y - 15), 
                     (x + overlay_width, y + overlay_height), 
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, result_frame, 0.3, 0, result_frame)
        
        # Draw statistics text
        current_y = y
        for key, value in stats.items():
            text = f"{key}: {value}"
            cv2.putText(result_frame, text, (x, current_y),
                       self.font, self.font_scale, (255, 255, 255), 
                       self.font_thickness)
            current_y += line_height
        
        return result_frame
    
    def create_status_image(self, text: str, size: Tuple[int, int] = (640, 480),
                           bg_color: Tuple[int, int, int] = (50, 50, 50)) -> np.ndarray:
        """
        Create status image with text (for when no input is available)
        
        Args:
            text: Status text to display
            size: Image size (width, height)
            bg_color: Background color
            
        Returns:
            Status image as numpy array
        """
        width, height = size
        image = np.full((height, width, 3), bg_color, dtype=np.uint8)
        
        # Calculate text position for centering
        (text_width, text_height), baseline = cv2.getTextSize(
            text, self.font, self.font_scale, self.font_thickness
        )
        
        text_x = (width - text_width) // 2
        text_y = (height + text_height) // 2
        
        # Draw text
        cv2.putText(image, text, (text_x, text_y),
                   self.font, self.font_scale, (255, 255, 255), 
                   self.font_thickness)
        
        return image
    
    def frame_to_tkinter(self, frame: np.ndarray, size: Optional[Tuple[int, int]] = None) -> ImageTk.PhotoImage:
        """
        Convert OpenCV frame to Tkinter PhotoImage
        
        Args:
            frame: OpenCV frame (BGR format)
            size: Optional resize dimensions (width, height)
            
        Returns:
            Tkinter PhotoImage object
        """
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Resize if requested
        if size:
            pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        return ImageTk.PhotoImage(pil_image)
    
    def update_colors(self, color_config: ColorConfig) -> None:
        """Update color configuration"""
        self.colors = color_config
        self.logger.info("Drawing colors updated")
    
    def get_drawing_stats(self) -> Dict[str, Any]:
        """Get drawing performance statistics"""
        return {
            'font': self.font,
            'font_scale': self.font_scale,
            'bbox_thickness': self.bbox_thickness,
            'colors_loaded': True
        }