"""
Input Manager for Smart Traffic Counter
Handles various input sources including screen capture, webcam, and files
"""

import cv2
import numpy as np
import threading
import time
from typing import Optional, Tuple, Callable, Dict, Any, Union
from pathlib import Path
from abc import ABC, abstractmethod

from utils.error_handler import ErrorHandler, CaptureError
from utils.logger import get_logger
from utils.validators import validate_region


class InputSource(ABC):
    """Abstract base class for input sources"""
    
    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a frame from the input source"""
        pass
    
    @abstractmethod
    def release(self) -> None:
        """Release the input source"""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if input source is active"""
        pass


class ScreenCaptureSource(InputSource):
    """Screen capture input source"""
    
    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None):
        self.region = region  # (x, y, width, height)
        self.logger = get_logger(__name__)
        self._active = False
        
        # Try to import screen capture libraries
        self._init_capture_method()
    
    def _init_capture_method(self):
        """Initialize the best available screen capture method"""
        self.capture_method = None
        
        # Try MSS (fastest)
        try:
            import mss
            self.mss = mss.mss()
            self.capture_method = 'mss'
            self.logger.info("Using MSS for screen capture")
        except ImportError:
            pass
        
        # Fallback to PIL
        if self.capture_method is None:
            try:
                from PIL import ImageGrab
                self.capture_method = 'pil'
                self.logger.info("Using PIL for screen capture")
            except ImportError:
                pass
        
        # Last resort: pyautogui
        if self.capture_method is None:
            try:
                import pyautogui
                self.capture_method = 'pyautogui'
                self.logger.info("Using pyautogui for screen capture")
            except ImportError:
                raise ImportError("No screen capture library available. Install mss, PIL, or pyautogui")
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture frame from screen"""
        try:
            if self.capture_method == 'mss':
                return self._capture_mss()
            elif self.capture_method == 'pil':
                return self._capture_pil()
            elif self.capture_method == 'pyautogui':
                return self._capture_pyautogui()
            else:
                return False, None
        except Exception as e:
            self.logger.error(f"Screen capture error: {e}")
            return False, None
    
    def _capture_mss(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture using MSS"""
        try:
            if self.region:
                x, y, width, height = self.region
                monitor = {"top": y, "left": x, "width": width, "height": height}
            else:
                monitor = self.mss.monitors[1]  # Primary monitor
            
            screenshot = self.mss.grab(monitor)
            frame = np.array(screenshot)[:, :, :3]  # Remove alpha channel
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame
        except Exception as e:
            self.logger.error(f"MSS capture error: {e}")
            return False, None
    
    def _capture_pil(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture using PIL"""
        try:
            from PIL import ImageGrab
            
            if self.region:
                x, y, width, height = self.region
                bbox = (x, y, x + width, y + height)
                screenshot = ImageGrab.grab(bbox)
            else:
                screenshot = ImageGrab.grab()
            
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame
        except Exception as e:
            self.logger.error(f"PIL capture error: {e}")
            return False, None
    
    def _capture_pyautogui(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Capture using pyautogui"""
        try:
            import pyautogui
            
            if self.region:
                x, y, width, height = self.region
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
            else:
                screenshot = pyautogui.screenshot()
            
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame
        except Exception as e:
            self.logger.error(f"pyautogui capture error: {e}")
            return False, None
    
    def set_region(self, region: Tuple[int, int, int, int]) -> bool:
        """Set capture region"""
        try:
            # Validate region
            screen_width, screen_height = self._get_screen_size()
            x, y, width, height = region
            
            if validate_region(x, y, width, height, screen_width, screen_height):
                self.region = region
                self.logger.info(f"Screen capture region set to: {region}")
                return True
            else:
                self.logger.error(f"Invalid region: {region}")
                return False
        except Exception as e:
            self.logger.error(f"Error setting region: {e}")
            return False
    
    def _get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions"""
        try:
            if self.capture_method == 'mss':
                monitor = self.mss.monitors[1]
                return monitor['width'], monitor['height']
            else:
                import pyautogui
                return pyautogui.size()
        except Exception:
            return 1920, 1080  # Default fallback
    
    def release(self) -> None:
        """Release screen capture resources"""
        if hasattr(self, 'mss'):
            self.mss.close()
        self._active = False
    
    def is_active(self) -> bool:
        """Check if screen capture is active"""
        return self._active


class WebcamSource(InputSource):
    """Webcam input source"""
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.logger = get_logger(__name__)
        self.cap = None
        self._active = False
        
        self._initialize_camera()
    
    def _initialize_camera(self) -> bool:
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                self._active = True
                self.logger.info(f"Camera {self.camera_index} initialized")
                return True
            else:
                self.logger.error(f"Failed to open camera {self.camera_index}")
                return False
        except Exception as e:
            self.logger.error(f"Camera initialization error: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from camera"""
        if not self._active or self.cap is None:
            return False, None
        
        try:
            ret, frame = self.cap.read()
            return ret, frame if ret else None
        except Exception as e:
            self.logger.error(f"Camera read error: {e}")
            return False, None
    
    def release(self) -> None:
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self._active = False
    
    def is_active(self) -> bool:
        """Check if camera is active"""
        return self._active and self.cap is not None and self.cap.isOpened()


class VideoFileSource(InputSource):
    """Video file input source"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.logger = get_logger(__name__)
        self.cap = None
        self._active = False
        
        self._initialize_video()
    
    def _initialize_video(self) -> bool:
        """Initialize video file"""
        try:
            if not self.file_path.exists():
                self.logger.error(f"Video file not found: {self.file_path}")
                return False
            
            self.cap = cv2.VideoCapture(str(self.file_path))
            if self.cap.isOpened():
                self._active = True
                self.logger.info(f"Video file opened: {self.file_path}")
                return True
            else:
                self.logger.error(f"Failed to open video file: {self.file_path}")
                return False
        except Exception as e:
            self.logger.error(f"Video initialization error: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from video file"""
        if not self._active or self.cap is None:
            return False, None
        
        try:
            ret, frame = self.cap.read()
            return ret, frame if ret else None
        except Exception as e:
            self.logger.error(f"Video read error: {e}")
            return False, None
    
    def release(self) -> None:
        """Release video file resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self._active = False
    
    def is_active(self) -> bool:
        """Check if video file is active"""
        return self._active and self.cap is not None and self.cap.isOpened()


class InputManager:
    """Manages different input sources and frame processing"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        self.current_source: Optional[InputSource] = None
        self.capture_thread: Optional[threading.Thread] = None
        self.is_capturing = False
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_callback: Optional[Callable[[np.ndarray], None]] = None
        self.frame_lock = threading.Lock()
        
        # Performance metrics
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0.0
    
    def set_screen_capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Set screen capture as input source"""
        try:
            self.stop_capture()
            self.current_source = ScreenCaptureSource(region)
            self.logger.info("Screen capture source set")
            return True
        except Exception as e:
            self.error_handler.handle_capture_error(e, "screen capture setup")
            return False
    
    def set_webcam_capture(self, camera_index: int = 0) -> bool:
        """Set webcam as input source"""
        try:
            self.stop_capture()
            self.current_source = WebcamSource(camera_index)
            if self.current_source.is_active():
                self.logger.info(f"Webcam {camera_index} source set")
                return True
            else:
                self.current_source = None
                return False
        except Exception as e:
            self.error_handler.handle_capture_error(e, "webcam setup")
            return False
    
    def set_video_file(self, file_path: str) -> bool:
        """Set video file as input source"""
        try:
            self.stop_capture()
            self.current_source = VideoFileSource(file_path)
            if self.current_source.is_active():
                self.logger.info(f"Video file source set: {file_path}")
                return True
            else:
                self.current_source = None
                return False
        except Exception as e:
            self.error_handler.handle_capture_error(e, "video file setup")
            return False
    
    def start_capture(self, frame_callback: Optional[Callable[[np.ndarray], None]] = None) -> bool:
        """Start capturing frames in a separate thread"""
        if not self.current_source or not self.current_source.is_active():
            self.logger.error("No active input source available")
            return False
        
        if self.is_capturing:
            self.logger.warning("Capture already in progress")
            return True
        
        self.frame_callback = frame_callback
        self.is_capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.logger.info("Frame capture started")
        return True
    
    def stop_capture(self) -> None:
        """Stop frame capture"""
        self.is_capturing = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.current_source:
            self.current_source.release()
            self.current_source = None
        
        self.logger.info("Frame capture stopped")
    
    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread"""
        while self.is_capturing and self.current_source:
            try:
                ret, frame = self.current_source.read_frame()
                
                if ret and frame is not None:
                    # Update latest frame
                    with self.frame_lock:
                        self.latest_frame = frame.copy()
                    
                    # Call frame callback if provided
                    if self.frame_callback:
                        self.frame_callback(frame)
                    
                    # Update FPS counter
                    self._update_fps_counter()
                else:
                    # Handle end of video file or capture error
                    if isinstance(self.current_source, VideoFileSource):
                        self.logger.info("End of video file reached")
                        self.is_capturing = False
                    else:
                        time.sleep(0.01)  # Brief pause on capture failure
                
                # Control frame rate (optional)
                time.sleep(0.001)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)  # Longer pause on error
    
    def _update_fps_counter(self) -> None:
        """Update FPS calculation"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_timer)
            self.fps_counter = 0
            self.fps_timer = current_time
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the latest captured frame (thread-safe)"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def get_capture_stats(self) -> Dict[str, Any]:
        """Get capture performance statistics"""
        return {
            'is_capturing': self.is_capturing,
            'has_source': self.current_source is not None,
            'source_active': self.current_source.is_active() if self.current_source else False,
            'current_fps': self.current_fps,
            'source_type': type(self.current_source).__name__ if self.current_source else 'None'
        }
    
    def cleanup(self) -> None:
        """Clean up input manager resources"""
        self.stop_capture()
        self.latest_frame = None
        self.frame_callback = None