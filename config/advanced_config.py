"""
Advanced Configuration System for Vehicle Counter Application
Updated: 2025-08-11 11:48:05 UTC by rasiharunart1
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

# Application Metadata
APP_INFO = {
    'name': 'Smart Traffic Counter',
    'version': '4.0.0',
    'author': 'rasiharunart1',
    'updated': '2025-08-11 11:48:05 UTC',
    'description': 'Advanced AI-powered vehicle detection and counting system'
}

# Default Paths
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / 'config'
DATA_DIR = BASE_DIR / 'data'
MODELS_DIR = BASE_DIR / 'models'
EXPORTS_DIR = BASE_DIR / 'exports'
LOGS_DIR = BASE_DIR / 'logs'

# Create directories if they don't exist
for directory in [CONFIG_DIR, DATA_DIR, MODELS_DIR, EXPORTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Enhanced Model Configuration
MODEL_CONFIGS = {
    'yolov8n': {
        'path': 'yolov8n.pt',
        'description': 'YOLOv8 Nano - Fastest, lowest accuracy',
        'size': '6MB',
        'speed': 'Very Fast',
        'accuracy': 'Good',
        'recommended_for': 'Real-time applications with limited resources'
    },
    'yolov8s': {
        'path': 'yolov8s.pt',
        'description': 'YOLOv8 Small - Balanced speed and accuracy',
        'size': '22MB',
        'speed': 'Fast',
        'accuracy': 'Better',
        'recommended_for': 'General purpose detection'
    },
    'yolov8m': {
        'path': 'yolov8m.pt',
        'description': 'YOLOv8 Medium - Higher accuracy',
        'size': '52MB',
        'speed': 'Medium',
        'accuracy': 'Very Good',
        'recommended_for': 'High accuracy requirements'
    },
    'yolov8l': {
        'path': 'yolov8l.pt',
        'description': 'YOLOv8 Large - Best accuracy',
        'size': '87MB',
        'speed': 'Slow',
        'accuracy': 'Excellent',
        'recommended_for': 'Maximum accuracy needs'
    },
    'yolov11n': {
        'path': 'yolo11n.pt',
        'description': 'YOLOv11 Nano - Latest version, optimized',
        'size': '5MB',
        'speed': 'Very Fast',
        'accuracy': 'Good',
        'recommended_for': 'Latest features with speed'
    }
}

# Advanced Detection Settings
DETECTION_SETTINGS = {
    'confidence_threshold': 0.25,
    'iou_threshold': 0.45,
    'max_detections': 300,
    'agnostic_nms': False,
    'classes': None,  # None means all classes
    'device': 'auto',  # 'auto', 'cpu', 'cuda', 'mps'
    'half_precision': False,
    'augment': False,
    'visualize': False,
    'save_conf': True,
    'save_crop': False,
    'hide_labels': False,
    'hide_conf': False,
    'vid_stride': 1,
    'line_thickness': 3,
    'retina_masks': False
}

# Database Configurations
DATABASE_CONFIGS = {
    'sqlite': {
        'type': 'sqlite',
        'description': 'SQLite - Local file database (recommended for single user)',
        'file_path': str(DATA_DIR / 'vehicle_counter.db'),
        'advantages': ['No setup required', 'Portable', 'Fast for small datasets'],
        'disadvantages': ['Single user', 'Limited concurrent access']
    },
    'mysql': {
        'type': 'mysql',
        'description': 'MySQL - Production ready database server',
        'host': 'localhost',
        'port': 3306,
        'database': 'vehicle_counter',
        'username': 'root',
        'password': '',
        'advantages': ['Multi-user', 'Scalable', 'ACID compliant'],
        'disadvantages': ['Requires setup', 'Server needed']
    },
    'postgresql': {
        'type': 'postgresql',
        'description': 'PostgreSQL - Advanced open source database',
        'host': 'localhost',
        'port': 5432,
        'database': 'vehicle_counter',
        'username': 'postgres',
        'password': '',
        'advantages': ['Advanced features', 'JSON support', 'Extensible'],
        'disadvantages': ['Complex setup', 'Higher resource usage']
    }
}

# Enhanced Vehicle Classes
ENHANCED_VEHICLE_CLASSES = {
    0: {'name': 'person', 'emoji': '🚶', 'count': False, 'color': '#FFB6C1'},
    1: {'name': 'bicycle', 'emoji': '🚲', 'count': True, 'color': '#98FB98'},
    2: {'name': 'car', 'emoji': '🚗', 'count': True, 'color': '#87CEEB'},
    3: {'name': 'motorcycle', 'emoji': '🏍️', 'count': True, 'color': '#DDA0DD'},
    4: {'name': 'airplane', 'emoji': '✈️', 'count': False, 'color': '#F0E68C'},
    5: {'name': 'bus', 'emoji': '🚌', 'count': True, 'color': '#FFA07A'},
    6: {'name': 'train', 'emoji': '🚊', 'count': True, 'color': '#20B2AA'},
    7: {'name': 'truck', 'emoji': '🚛', 'count': True, 'color': '#F4A460'},
    8: {'name': 'boat', 'emoji': '🚤', 'count': False, 'color': '#778899'}
}

# Line Configuration Presets
LINE_PRESETS = {
    'highway_horizontal': {
        'name': 'Highway Horizontal',
        'description': 'Standard horizontal line for highway monitoring',
        'line_type': 'horizontal',
        'position': 0.5,  # Center of frame
        'thickness': 4,
        'color': '#00FF00',
        'direction_sensitivity': 0.8
    },
    'highway_vertical': {
        'name': 'Highway Vertical',
        'description': 'Vertical line for highway lane monitoring',
        'line_type': 'vertical',
        'position': 0.5,
        'thickness': 4,
        'color': '#FF0000',
        'direction_sensitivity': 0.8
    },
    'intersection_cross': {
        'name': 'Intersection Cross',
        'description': 'Cross lines for intersection monitoring',
        'line_type': 'cross',
        'thickness': 3,
        'color': '#FFFF00',
        'direction_sensitivity': 0.6
    },
    'parking_zone': {
        'name': 'Parking Zone',
        'description': 'Zone-based detection for parking areas',
        'line_type': 'zone',
        'thickness': 2,
        'color': '#FF00FF',
        'direction_sensitivity': 0.3
    }
}

# Theme Configurations
THEMES = {
    'dark': {
        'name': 'Dark Professional',
        'primary_bg': '#1e1e1e',
        'secondary_bg': '#2d2d2d',
        'accent_bg': '#363636',
        'primary_fg': '#ffffff',
        'secondary_fg': '#cccccc',
        'accent_color': '#00d4ff',
        'success_color': '#28a745',
        'warning_color': '#ffc107',
        'error_color': '#dc3545',
        'button_bg': '#0078d4',
        'button_hover': '#106ebe'
    },
    'light': {
        'name': 'Light Professional',
        'primary_bg': '#ffffff',
        'secondary_bg': '#f8f9fa',
        'accent_bg': '#e9ecef',
        'primary_fg': '#212529',
        'secondary_fg': '#6c757d',
        'accent_color': '#0066cc',
        'success_color': '#198754',
        'warning_color': '#fd7e14',
        'error_color': '#dc3545',
        'button_bg': '#0d6efd',
        'button_hover': '#0b5ed7'
    },
    'blue': {
        'name': 'Blue Ocean',
        'primary_bg': '#0f1419',
        'secondary_bg': '#1a252f',
        'accent_bg': '#253341',
        'primary_fg': '#ffffff',
        'secondary_fg': '#b3d4fc',
        'accent_color': '#39bae6',
        'success_color': '#7cc142',
        'warning_color': '#ffb74d',
        'error_color': '#f28b82',
        'button_bg': '#1976d2',
        'button_hover': '#1565c0'
    }
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    'max_fps': 30,
    'buffer_size': 10,
    'thread_pool_size': 4,
    'memory_limit_mb': 512,
    'gpu_memory_fraction': 0.8,
    'enable_profiling': False,
    'auto_optimize': True,
    'cache_detections': True,
    'parallel_processing': True
}

# Export Settings
EXPORT_SETTINGS = {
    'formats': ['csv', 'excel', 'json', 'pdf'],
    'include_timestamps': True,
    'include_coordinates': False,
    'include_confidence': True,
    'date_format': '%Y-%m-%d %H:%M:%S',
    'auto_export_interval': 0,  # 0 = disabled, minutes
    'max_export_records': 10000,
    'compress_exports': True
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_enabled': True,
    'console_enabled': True,
    'max_file_size_mb': 10,
    'backup_count': 5,
    'log_performance': True,
    'log_detections': False
}

class SettingsManager:
    """Advanced settings management with persistence"""
    
    def __init__(self):
        self.settings_file = CONFIG_DIR / 'user_settings.json'
        self.profiles_file = CONFIG_DIR / 'user_profiles.json'
        self.current_settings = self.load_settings()
        self.current_profile = 'default'
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create defaults"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                return self.validate_settings(settings)
            else:
                return self.get_default_settings()
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.get_default_settings()
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings"""
        return {
            'model': {
                'current_model': 'yolov8n',
                'settings': DETECTION_SETTINGS.copy()
            },
            'database': {
                'current_type': 'sqlite',
                'configs': DATABASE_CONFIGS.copy()
            },
            'ui': {
                'theme': 'dark',
                'window_size': (1600, 1000),
                'auto_save': True,
                'show_tooltips': True,
                'language': 'en'
            },
            'performance': PERFORMANCE_SETTINGS.copy(),
            'export': EXPORT_SETTINGS.copy(),
            'logging': LOGGING_CONFIG.copy(),
            'tracking': {
                'max_disappeared': 30,
                'max_distance': 50,
                'min_hits': 3,
                'iou_threshold': 0.3
            }
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix settings if needed"""
        defaults = self.get_default_settings()
        
        # Recursively merge with defaults
        def merge_dict(default, user):
            for key, value in default.items():
                if key not in user:
                    user[key] = value
                elif isinstance(value, dict) and isinstance(user[key], dict):
                    merge_dict(value, user[key])
            return user
        
        return merge_dict(defaults, settings)
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.current_settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_setting(self, category: str, key: str = None):
        """Get a specific setting"""
        if key is None:
            return self.current_settings.get(category, {})
        return self.current_settings.get(category, {}).get(key)
    
    def set_setting(self, category: str, key: str, value: Any):
        """Set a specific setting"""
        if category not in self.current_settings:
            self.current_settings[category] = {}
        self.current_settings[category][key] = value
        if self.current_settings['ui']['auto_save']:
            self.save_settings()
    
    def export_settings(self, filepath: str) -> bool:
        """Export settings to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, filepath: str) -> bool:
        """Import settings from file"""
        try:
            with open(filepath, 'r') as f:
                imported_settings = json.load(f)
            self.current_settings = self.validate_settings(imported_settings)
            self.save_settings()
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False

# Create global settings manager instance
settings_manager = SettingsManager()