"""
Detection Manager for Smart Traffic Counter
Handles YOLO model loading, inference, and vehicle detection processing
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Union
from pathlib import Path
import time

from config_manager import ModelConfig
from utils.error_handler import ErrorHandler, ModelLoadError
from utils.logger import get_logger


class Detection:
    """Represents a single vehicle detection"""
    
    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float, 
                 class_id: int, class_name: str):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.class_id = class_id
        self.class_name = class_name
        self.center = self._calculate_center()
        
    def _calculate_center(self) -> Tuple[int, int]:
        """Calculate center point of bounding box"""
        x1, y1, x2, y2 = self.bbox
        return (int((x1 + x2) / 2), int((y1 + y2) / 2))
    
    @property
    def area(self) -> int:
        """Calculate bounding box area"""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)
    
    @property
    def width(self) -> int:
        """Get bounding box width"""
        x1, y1, x2, y2 = self.bbox
        return x2 - x1
    
    @property
    def height(self) -> int:
        """Get bounding box height"""
        x1, y1, x2, y2 = self.bbox
        return y2 - y1


class DetectionManager:
    """Manages YOLO model loading and vehicle detection processing"""
    
    # COCO dataset vehicle classes
    VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck
    CLASS_NAMES = {
        2: 'car',
        3: 'motorcycle', 
        5: 'bus',
        7: 'truck'
    }
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        self.model = None
        self.model_loaded = False
        self.last_inference_time = 0.0
        
        # Initialize model
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Load YOLO model with enhanced error handling
        Returns True if successful, False otherwise
        """
        try:
            # Dynamic import to handle missing dependencies gracefully
            try:
                from ultralytics import YOLO
            except ImportError as e:
                raise ModelLoadError(
                    "YOLO library not available. Install with: pip install ultralytics"
                ) from e
            
            model_path = Path(self.config.model_path)
            
            # Check if model file exists
            if not model_path.exists():
                # Try to download default model if using standard name
                if model_path.name in ['yolo11n.pt', 'yolov8n.pt', 'yolov5s.pt']:
                    self.logger.info(f"Model file not found, attempting to download {model_path.name}")
                    self.model = YOLO(model_path.name)
                else:
                    raise FileNotFoundError(f"Model file not found: {model_path}")
            else:
                self.logger.info(f"Loading YOLO model from {model_path}")
                self.model = YOLO(str(model_path))
            
            # Configure device
            if self.config.device == 'auto':
                # Auto-detect best device
                device = self._detect_best_device()
            else:
                device = self.config.device
            
            # Move model to device
            if hasattr(self.model.model, 'to'):
                self.model.model.to(device)
            
            self.model_loaded = True
            self.logger.info(f"✅ YOLO model loaded successfully on {device}")
            return True
            
        except Exception as e:
            self.error_handler.handle_model_load_error(e, self.config.model_path)
            self.model_loaded = False
            return False
    
    def _detect_best_device(self) -> str:
        """Auto-detect the best available device"""
        try:
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
                self.logger.info(f"CUDA available with {torch.cuda.device_count()} GPU(s)")
            else:
                device = 'cpu'
                self.logger.info("CUDA not available, using CPU")
        except ImportError:
            device = 'cpu'
            self.logger.info("PyTorch not available, using CPU")
        
        return device
    
    def is_model_loaded(self) -> bool:
        """Check if model is successfully loaded"""
        return self.model_loaded and self.model is not None
    
    def detect_vehicles(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect vehicles in frame
        
        Args:
            frame: Input image as numpy array
            
        Returns:
            List of Detection objects for vehicles found
        """
        if not self.is_model_loaded():
            self.logger.warning("Model not loaded, returning empty detections")
            return []
        
        try:
            start_time = time.time()
            
            # Run inference
            results = self.model(
                frame,
                conf=self.config.confidence_threshold,
                iou=self.config.iou_threshold,
                verbose=False
            )
            
            self.last_inference_time = time.time() - start_time
            
            # Process results
            detections = []
            if results and len(results) > 0:
                result = results[0]  # First result
                
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    
                    for i in range(len(boxes)):
                        # Extract box data
                        box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls = int(boxes.cls[i].cpu().numpy())
                        
                        # Filter for vehicle classes and minimum confidence
                        if (cls in self.VEHICLE_CLASSES and 
                            conf >= self.config.detection_confidence):
                            
                            bbox = tuple(map(int, box))
                            class_name = self.CLASS_NAMES.get(cls, f"class_{cls}")
                            
                            detection = Detection(bbox, conf, cls, class_name)
                            
                            # Filter by minimum size
                            if (detection.width >= self.config.min_detection_size and 
                                detection.height >= self.config.min_detection_size):
                                detections.append(detection)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Error during vehicle detection: {e}")
            return []
    
    def get_inference_stats(self) -> Dict[str, Any]:
        """Get inference performance statistics"""
        return {
            'model_loaded': self.model_loaded,
            'last_inference_time': self.last_inference_time,
            'fps': 1.0 / self.last_inference_time if self.last_inference_time > 0 else 0,
            'device': getattr(self.model, 'device', 'unknown') if self.model else 'none'
        }
    
    def reload_model(self, new_config: Optional[ModelConfig] = None) -> bool:
        """
        Reload model with new configuration
        
        Args:
            new_config: Optional new model configuration
            
        Returns:
            True if reload successful
        """
        if new_config:
            self.config = new_config
        
        self.model = None
        self.model_loaded = False
        
        return self._load_model()
    
    def cleanup(self) -> None:
        """Clean up model resources"""
        if self.model is not None:
            try:
                # Clear model from memory
                del self.model
                self.model = None
                self.model_loaded = False
                self.logger.info("Model resources cleaned up")
            except Exception as e:
                self.logger.warning(f"Error during model cleanup: {e}")


# Convenience function for backward compatibility
def create_detection_manager(model_path: str = 'yolo11n.pt', 
                           confidence_threshold: float = 0.05,
                           detection_confidence: float = 0.15) -> DetectionManager:
    """Create detection manager with simplified parameters"""
    config = ModelConfig(
        model_path=model_path,
        confidence_threshold=confidence_threshold,
        detection_confidence=detection_confidence
    )
    return DetectionManager(config)