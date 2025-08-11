"""
Configuration and data validation utilities
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import re


class ValidationError(Exception):
    """Exception raised for validation errors"""
    pass


class ConfigValidator:
    """Validates configuration parameters"""
    
    @staticmethod
    def validate_model_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate YOLO model configuration
        Returns list of validation errors
        """
        errors = []
        
        # Check model path
        if 'model_path' not in config:
            errors.append("model_path is required")
        else:
            model_path = Path(config['model_path'])
            if not model_path.exists():
                errors.append(f"Model file not found: {config['model_path']}")
            elif not model_path.suffix.lower() in ['.pt', '.onnx', '.engine']:
                errors.append(f"Invalid model format: {model_path.suffix}")
        
        # Check confidence thresholds
        confidence_fields = ['confidence_threshold', 'detection_confidence', 'iou_threshold']
        for field in confidence_fields:
            if field in config:
                value = config[field]
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    errors.append(f"{field} must be a number between 0 and 1")
        
        return errors
    
    @staticmethod
    def validate_database_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate database configuration
        Returns list of validation errors
        """
        errors = []
        
        required_fields = ['host', 'port', 'dbname', 'user', 'password']
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Database {field} is required")
        
        # Validate port
        if 'port' in config:
            try:
                port = int(config['port'])
                if not 1 <= port <= 65535:
                    errors.append("Database port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("Database port must be a valid integer")
        
        # Validate host format (basic check)
        if 'host' in config and config['host']:
            host = config['host']
            # Check for valid IP or hostname format
            ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
            hostname_pattern = r'^[a-zA-Z0-9.-]+$'
            if not (re.match(ip_pattern, host) or re.match(hostname_pattern, host)):
                errors.append("Invalid host format")
        
        return errors
    
    @staticmethod
    def validate_gui_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate GUI configuration
        Returns list of validation errors
        """
        errors = []
        
        # Validate window size format
        if 'window_size' in config:
            size = config['window_size']
            if not re.match(r'^\d+x\d+$', size):
                errors.append("window_size must be in format 'WIDTHxHEIGHT'")
            else:
                try:
                    width, height = map(int, size.split('x'))
                    if width < 800 or height < 600:
                        errors.append("Minimum window size is 800x600")
                except ValueError:
                    errors.append("Invalid window size format")
        
        # Validate FPS target
        if 'fps_target' in config:
            fps = config['fps_target']
            if not isinstance(fps, int) or not 1 <= fps <= 120:
                errors.append("fps_target must be an integer between 1 and 120")
        
        return errors
    
    @staticmethod
    def validate_line_settings(settings: Dict[str, Any]) -> List[str]:
        """
        Validate counting line settings
        Returns list of validation errors
        """
        errors = []
        
        # Validate color format
        if 'line_color' in settings:
            color = settings['line_color']
            if not re.match(r'^#[0-9a-fA-F]{6}$', color):
                errors.append("line_color must be in hex format #RRGGBB")
        
        # Validate thickness
        if 'line_thickness' in settings:
            thickness = settings['line_thickness']
            if not isinstance(thickness, int) or not 1 <= thickness <= 20:
                errors.append("line_thickness must be an integer between 1 and 20")
        
        # Validate detection threshold
        if 'detection_threshold' in settings:
            threshold = settings['detection_threshold']
            if not isinstance(threshold, (int, float)) or not 1 <= threshold <= 200:
                errors.append("detection_threshold must be a number between 1 and 200")
        
        return errors


def validate_coordinates(x1: float, y1: float, x2: float, y2: float, 
                        width: int, height: int) -> bool:
    """
    Validate that coordinates are within frame bounds
    
    Args:
        x1, y1, x2, y2: Line coordinates
        width, height: Frame dimensions
        
    Returns:
        True if coordinates are valid
    """
    return (0 <= x1 <= width and 0 <= y1 <= height and
            0 <= x2 <= width and 0 <= y2 <= height)


def validate_region(x: int, y: int, width: int, height: int, 
                   screen_width: int, screen_height: int) -> bool:
    """
    Validate screen capture region
    
    Args:
        x, y: Top-left corner
        width, height: Region dimensions
        screen_width, screen_height: Screen dimensions
        
    Returns:
        True if region is valid
    """
    return (x >= 0 and y >= 0 and 
            x + width <= screen_width and 
            y + height <= screen_height and
            width > 0 and height > 0)