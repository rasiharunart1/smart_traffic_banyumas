"""
Enhanced configuration management for Smart Traffic Counter
Provides centralized configuration with validation and environment support
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from utils.validators import ConfigValidator
from utils.logger import get_logger


@dataclass
class ModelConfig:
    """YOLO model configuration"""
    model_path: str = 'yolo11n.pt'
    confidence_threshold: float = 0.05
    iou_threshold: float = 0.5
    detection_confidence: float = 0.15
    device: str = 'auto'  # 'auto', 'cpu', 'cuda'


@dataclass 
class DatabaseConfig:
    """Database configuration"""
    dbname: str = "person_counter"
    user: str = "magang"
    password: str = "magang123#"
    host: str = "10.98.33.122"
    port: str = "5433"
    enabled: bool = True


@dataclass
class GUIConfig:
    """GUI configuration"""
    window_title: str = "🚗 Smart Traffic Counter v3.0 - Modern UI"
    window_size: str = "1600x1000"
    fps_target: int = 30
    theme: str = "dark"  # 'dark', 'light'


@dataclass
class LineConfig:
    """Counting line configuration"""
    line_color: str = '#FF0000'
    line_thickness: int = 3
    line_style: str = 'solid'
    show_label: bool = True
    label_text: str = 'COUNTING LINE'
    detection_threshold: int = 50
    line_type: str = 'manual'


@dataclass
class TrackingConfig:
    """Vehicle tracking configuration"""
    max_distance: int = 50
    path_history_length: int = 10
    track_timeout: float = 3.5
    min_detection_size: int = 20


@dataclass
class ColorConfig:
    """Color configuration for UI elements"""
    active_vehicle: tuple = (0, 255, 0)
    counted_vehicle: tuple = (128, 128, 128)
    center_dot_active: tuple = (0, 0, 255)
    center_dot_counted: tuple = (64, 64, 64)
    tracking_path: tuple = (255, 0, 0)
    tracking_path_counted: tuple = (64, 64, 64)


@dataclass
class AppConfig:
    """Complete application configuration"""
    model: ModelConfig = None
    database: DatabaseConfig = None
    gui: GUIConfig = None
    line: LineConfig = None
    tracking: TrackingConfig = None
    colors: ColorConfig = None
    headless: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.gui is None:
            self.gui = GUIConfig()
        if self.line is None:
            self.line = LineConfig()
        if self.tracking is None:
            self.tracking = TrackingConfig()
        if self.colors is None:
            self.colors = ColorConfig()


class ConfigManager:
    """Enhanced configuration manager with validation and environment support"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.config_file = config_file or "config.json"
        self.validator = ConfigValidator()
        self._config: Optional[AppConfig] = None
        
    def load_config(self) -> AppConfig:
        """Load configuration from file and environment variables"""
        config_data = {}
        
        # Load from file if exists
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                self.logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                self.logger.warning(f"Failed to load config file: {e}")
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Create config object
        self._config = self._dict_to_config(config_data)
        
        # Validate configuration
        self._validate_config()
        
        return self._config
    
    def save_config(self, config: AppConfig) -> bool:
        """Save configuration to file"""
        try:
            config_dict = asdict(config)
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_config(self) -> AppConfig:
        """Get current configuration, loading if necessary"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        env_mappings = {
            # Model config
            'TC_MODEL_PATH': ('model', 'model_path'),
            'TC_MODEL_DEVICE': ('model', 'device'),
            'TC_CONFIDENCE_THRESHOLD': ('model', 'confidence_threshold'),
            
            # Database config
            'TC_DB_HOST': ('database', 'host'),
            'TC_DB_PORT': ('database', 'port'),
            'TC_DB_NAME': ('database', 'dbname'),
            'TC_DB_USER': ('database', 'user'),
            'TC_DB_PASSWORD': ('database', 'password'),
            'TC_DB_ENABLED': ('database', 'enabled'),
            
            # GUI config
            'TC_WINDOW_SIZE': ('gui', 'window_size'),
            'TC_FPS_TARGET': ('gui', 'fps_target'),
            'TC_THEME': ('gui', 'theme'),
            
            # App config
            'TC_HEADLESS': ('headless',),
            'TC_LOG_LEVEL': ('log_level',),
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert value types
                if env_var.endswith('_ENABLED') or env_var == 'TC_HEADLESS':
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif env_var.endswith('_THRESHOLD') or env_var.endswith('_TARGET'):
                    try:
                        value = float(value) if '.' in value else int(value)
                    except ValueError:
                        continue
                
                # Apply to config
                self._set_nested_value(config_data, config_path, value)
                self.logger.info(f"Applied environment override: {env_var}")
        
        return config_data
    
    def _set_nested_value(self, data: Dict[str, Any], path: tuple, value: Any):
        """Set nested dictionary value"""
        if len(path) == 1:
            data[path[0]] = value
        else:
            if path[0] not in data:
                data[path[0]] = {}
            self._set_nested_value(data[path[0]], path[1:], value)
    
    def _dict_to_config(self, config_data: Dict[str, Any]) -> AppConfig:
        """Convert dictionary to AppConfig object"""
        try:
            # Extract nested configs
            model_data = config_data.get('model', {})
            db_data = config_data.get('database', {})
            gui_data = config_data.get('gui', {})
            line_data = config_data.get('line', {})
            tracking_data = config_data.get('tracking', {})
            colors_data = config_data.get('colors', {})
            
            return AppConfig(
                model=ModelConfig(**model_data),
                database=DatabaseConfig(**db_data),
                gui=GUIConfig(**gui_data),
                line=LineConfig(**line_data),
                tracking=TrackingConfig(**tracking_data),
                colors=ColorConfig(**colors_data),
                headless=config_data.get('headless', False),
                log_level=config_data.get('log_level', 'INFO')
            )
        except Exception as e:
            self.logger.warning(f"Error creating config object: {e}. Using defaults.")
            return AppConfig()
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration"""
        if not self._config:
            return
            
        all_errors = []
        
        # Validate model config
        model_dict = asdict(self._config.model)
        model_errors = self.validator.validate_model_config(model_dict)
        all_errors.extend([f"Model: {err}" for err in model_errors])
        
        # Validate database config
        db_dict = asdict(self._config.database)
        db_errors = self.validator.validate_database_config(db_dict)
        all_errors.extend([f"Database: {err}" for err in db_errors])
        
        # Validate GUI config
        gui_dict = asdict(self._config.gui)
        gui_errors = self.validator.validate_gui_config(gui_dict)
        all_errors.extend([f"GUI: {err}" for err in gui_errors])
        
        # Validate line config
        line_dict = asdict(self._config.line)
        line_errors = self.validator.validate_line_settings(line_dict)
        all_errors.extend([f"Line: {err}" for err in line_errors])
        
        if all_errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(all_errors)
            self.logger.error(error_msg)
            # Don't raise exception for non-critical errors, just log them
        else:
            self.logger.info("Configuration validation passed")


# Legacy compatibility functions for existing code
def get_legacy_config() -> Dict[str, Any]:
    """Get configuration in legacy format for backward compatibility"""
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # Convert to legacy format matching original config.py
    return {
        'DATABASE_CONFIG': asdict(config.database),
        'MODEL_CONFIG': asdict(config.model),
        'GUI_CONFIG': asdict(config.gui),
        'DEFAULT_LINE_SETTINGS': asdict(config.line),
        'TRACKING_CONFIG': asdict(config.tracking),
        'COLOR_CONFIG': asdict(config.colors),
        'VEHICLE_CLASSES': [2, 3, 5, 7],  # COCO classes
        'CLASS_NAMES': {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
    }


# Global config manager instance
_global_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get global config manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_app_config() -> AppConfig:
    """Get application configuration"""
    return get_config_manager().get_config()