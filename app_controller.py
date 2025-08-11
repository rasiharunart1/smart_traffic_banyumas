"""
Application Controller for Smart Traffic Counter
Main controller that orchestrates all components and manages application state
"""

import tkinter as tk
import threading
import time
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np

from config_manager import get_config_manager, AppConfig
from detection_manager import DetectionManager
from input_manager import InputManager
from line_manager import LineManager
from drawing_manager import DrawingManager
from ui_manager import UIManager
from database_handler import DatabaseHandler
from vehicle_tracker import VehicleTracker
from line_settings_dialog import LineSettingsDialog
from utils.logger import get_logger
from utils.error_handler import ErrorHandler


class AppController:
    """Main application controller for Smart Traffic Counter"""
    
    def __init__(self, headless: bool = False):
        # Load configuration
        self.config_manager = get_config_manager()
        self.config = self.config_manager.get_config()
        self.config.headless = headless
        
        # Setup logging
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize core managers
        self.detection_manager = DetectionManager(self.config.model)
        self.input_manager = InputManager()
        self.line_manager = LineManager(self.config.line)
        self.drawing_manager = DrawingManager(self.config.colors)
        
        # Initialize supporting components
        self.vehicle_tracker = VehicleTracker()
        self.db_handler = DatabaseHandler() if self.config.database.enabled else None
        
        # Application state
        self.is_previewing = False
        self.is_capturing = False
        self.is_line_drawing_mode = False
        self.current_frame = None
        self.current_detections = []
        self.performance_stats = {
            'fps': 0.0,
            'detection_time': 0.0,
            'total_detections': 0
        }
        
        # UI components (None for headless mode)
        self.root = None
        self.ui_manager = None
        
        # Threading
        self.processing_thread = None
        self.ui_update_thread = None
        
        if not headless:
            self._setup_gui()
    
    def _setup_gui(self):
        """Setup GUI components"""
        self.root = tk.Tk()
        self.ui_manager = UIManager(self.root, self.config.gui)
        
        # Set up UI callbacks
        self._setup_ui_callbacks()
        
        # Load saved lines
        self.line_manager.load_lines()
        self._update_line_widgets()
        
        # Update initial UI state
        self._update_ui_status()
        
        # Start UI update thread
        self.ui_update_thread = threading.Thread(target=self._ui_update_loop, daemon=True)
        self.ui_update_thread.start()
    
    def _setup_ui_callbacks(self):
        """Setup all UI callback functions"""
        callbacks = {
            'select_region': self.select_screen_region,
            'capture_full_screen': self.capture_full_screen,
            'toggle_preview': self.toggle_preview,
            'toggle_capture': self.toggle_capture,
            'reset_counts': self.reset_counts,
            'line_settings': self.open_line_settings,
            'draw_line': self.enable_line_drawing,
            'clear_line': self.clear_lines,
            'view_reports': self.view_reports,
            'export_data': self.export_data,
            'on_line_toggle': self.on_line_toggle,
            'on_line_remove': self.on_line_remove,
            'on_closing': self.on_closing
        }
        
        for name, callback in callbacks.items():
            self.ui_manager.set_callback(name, callback)
    
    def select_screen_region(self):
        """Handle screen region selection"""
        try:
            self.logger.info("Starting screen region selection")
            
            # Create selection overlay
            selection_root = tk.Toplevel(self.root)
            selection_root.attributes('-fullscreen', True)
            selection_root.attributes('-alpha', 0.3)
            selection_root.configure(bg='gray')
            selection_root.attributes('-topmost', True)
            
            # Selection variables
            selection_data = {'start_x': 0, 'start_y': 0, 'end_x': 0, 'end_y': 0, 'selecting': False}
            selection_canvas = tk.Canvas(selection_root, highlightthickness=0)
            selection_canvas.pack(fill=tk.BOTH, expand=True)
            
            def start_selection(event):
                selection_data['start_x'] = event.x
                selection_data['start_y'] = event.y
                selection_data['selecting'] = True
            
            def drag_selection(event):
                if selection_data['selecting']:
                    selection_canvas.delete("selection")
                    selection_canvas.create_rectangle(
                        selection_data['start_x'], selection_data['start_y'],
                        event.x, event.y, 
                        outline="red", width=2, tags="selection"
                    )
            
            def end_selection(event):
                if selection_data['selecting']:
                    selection_data['end_x'] = event.x
                    selection_data['end_y'] = event.y
                    selection_data['selecting'] = False
                    
                    # Calculate region
                    x1 = min(selection_data['start_x'], selection_data['end_x'])
                    y1 = min(selection_data['start_y'], selection_data['end_y'])
                    x2 = max(selection_data['start_x'], selection_data['end_x'])
                    y2 = max(selection_data['start_y'], selection_data['end_y'])
                    
                    width = x2 - x1
                    height = y2 - y1
                    
                    if width > 50 and height > 50:  # Minimum size
                        region = (x1, y1, width, height)
                        self.input_manager.set_screen_capture(region)
                        self.logger.info(f"Screen region selected: {region}")
                        self.ui_manager.update_button_states({'preview': '▶️ Start Preview', 'preview_state': 'normal'})
                    else:
                        self.ui_manager.show_warning("Invalid Selection", "Please select a larger region")
                    
                    selection_root.destroy()
            
            def cancel_selection(event):
                selection_root.destroy()
            
            # Bind events
            selection_canvas.bind("<Button-1>", start_selection)
            selection_canvas.bind("<B1-Motion>", drag_selection)
            selection_canvas.bind("<ButtonRelease-1>", end_selection)
            selection_canvas.bind("<Escape>", cancel_selection)
            
            # Instructions
            instruction_label = tk.Label(selection_canvas, 
                                        text="Click and drag to select capture region. Press ESC to cancel.",
                                        bg='black', fg='white', font=('Arial', 12))
            instruction_label.pack(pady=20)
            
            selection_canvas.focus_set()
            
        except Exception as e:
            self.error_handler.handle_capture_error(e, "region selection")
            self.ui_manager.show_error("Selection Error", str(e))
    
    def capture_full_screen(self):
        """Setup full screen capture"""
        try:
            success = self.input_manager.set_screen_capture()
            if success:
                self.logger.info("Full screen capture enabled")
                self.ui_manager.update_button_states({'preview': '▶️ Start Preview', 'preview_state': 'normal'})
                self.ui_manager.show_info("Success", "Full screen capture enabled")
            else:
                self.ui_manager.show_error("Error", "Failed to enable screen capture")
        except Exception as e:
            self.error_handler.handle_capture_error(e, "full screen setup")
            self.ui_manager.show_error("Capture Error", str(e))
    
    def toggle_preview(self):
        """Toggle preview mode"""
        try:
            if not self.is_previewing:
                # Start preview
                success = self.input_manager.start_capture(self._process_preview_frame)
                if success:
                    self.is_previewing = True
                    self.ui_manager.update_button_states({
                        'preview': '⏸️ Stop Preview',
                        'capture': '🔴 Start Counting',
                        'capture_state': 'normal'
                    })
                    self.logger.info("Preview started")
                else:
                    self.ui_manager.show_error("Preview Error", "Failed to start preview")
            else:
                # Stop preview
                self.input_manager.stop_capture()
                self.is_previewing = False
                self.ui_manager.update_button_states({
                    'preview': '▶️ Start Preview',
                    'capture': '🔴 Start Counting',
                    'capture_state': 'disabled'
                })
                self.ui_manager.show_status_message("Preview stopped")
                self.logger.info("Preview stopped")
                
        except Exception as e:
            self.logger.error(f"Error toggling preview: {e}")
            self.ui_manager.show_error("Preview Error", str(e))
    
    def toggle_capture(self):
        """Toggle vehicle counting mode"""
        try:
            if not self.is_capturing:
                # Start capturing
                if not self.is_previewing:
                    # Start input first
                    success = self.input_manager.start_capture(self._process_capture_frame)
                    if not success:
                        self.ui_manager.show_error("Capture Error", "Failed to start input capture")
                        return
                
                self.is_capturing = True
                self.vehicle_tracker = VehicleTracker()  # Reset tracking
                self.performance_stats['total_detections'] = 0
                
                self.ui_manager.update_button_states({
                    'capture': '⏹️ Stop Counting',
                    'preview': '⏸️ Stop Preview' if self.is_previewing else '▶️ Start Preview',
                    'preview_state': 'disabled'
                })
                self.logger.info("Vehicle counting started")
                
            else:
                # Stop capturing
                self.is_capturing = False
                
                self.ui_manager.update_button_states({
                    'capture': '🔴 Start Counting',
                    'preview_state': 'normal'
                })
                
                # Save counts to database if available
                if self.db_handler:
                    self._save_counts_to_database()
                
                self.logger.info("Vehicle counting stopped")
                
        except Exception as e:
            self.logger.error(f"Error toggling capture: {e}")
            self.ui_manager.show_error("Capture Error", str(e))
    
    def _process_preview_frame(self, frame: np.ndarray):
        """Process frame in preview mode (no detection)"""
        self.current_frame = frame
        
        # Draw counting lines on frame
        if self.line_manager.get_enabled_lines():
            frame_with_lines = self.drawing_manager.draw_counting_lines(
                frame, self.line_manager.get_enabled_lines()
            )
        else:
            frame_with_lines = frame
        
        # Update UI in main thread
        if self.ui_manager:
            self.root.after(0, self._update_video_display, frame_with_lines)
    
    def _process_capture_frame(self, frame: np.ndarray):
        """Process frame in capture mode (with detection and counting)"""
        start_time = time.time()
        
        self.current_frame = frame
        
        # Run vehicle detection
        detections = self.detection_manager.detect_vehicles(frame)
        self.current_detections = detections
        
        # Update vehicle tracking
        tracked_vehicles = self.vehicle_tracker.update_tracks(detections)
        
        # Check line crossings and update counts
        active_track_ids = set()
        for track_id, vehicle_info in tracked_vehicles.items():
            active_track_ids.add(track_id)
            
            if 'detection' in vehicle_info and not vehicle_info.get('counted', False):
                detection = vehicle_info['detection']
                vehicle_type = detection.class_name
                center = detection.center
                
                # Check for line crossings
                crossed_lines = self.line_manager.update_vehicle_tracking(
                    track_id, center, vehicle_type
                )
                
                # Mark as counted if crossed any line
                if crossed_lines:
                    vehicle_info['counted'] = True
                    self.performance_stats['total_detections'] += 1
        
        # Cleanup old tracks
        self.line_manager.cleanup_tracking(active_track_ids)
        
        # Draw detections and lines
        annotated_frame = self.drawing_manager.draw_detections(frame, detections, tracked_vehicles)
        annotated_frame = self.drawing_manager.draw_counting_lines(
            annotated_frame, self.line_manager.get_enabled_lines()
        )
        
        # Update performance stats
        self.performance_stats['detection_time'] = time.time() - start_time
        
        # Update UI in main thread
        if self.ui_manager:
            self.root.after(0, self._update_video_display, annotated_frame)
            self.root.after(0, self._update_vehicle_counts)
    
    def _update_video_display(self, frame: np.ndarray):
        """Update video display (runs in main thread)"""
        try:
            # Convert frame to PhotoImage
            photo = self.drawing_manager.frame_to_tkinter(frame, (640, 480))
            self.ui_manager.update_video_display(photo)
        except Exception as e:
            self.logger.error(f"Error updating video display: {e}")
    
    def _update_vehicle_counts(self):
        """Update vehicle count displays (runs in main thread)"""
        try:
            total_counts = self.line_manager.get_total_counts()
            self.ui_manager.update_vehicle_counts(total_counts)
            
            # Update individual line widgets
            for line in self.line_manager.get_all_lines():
                self.ui_manager.update_counting_line_widget(line.id, line.vehicle_counts)
                
        except Exception as e:
            self.logger.error(f"Error updating vehicle counts: {e}")
    
    def _ui_update_loop(self):
        """Background UI update loop"""
        while True:
            try:
                if self.ui_manager:
                    # Update FPS
                    capture_stats = self.input_manager.get_capture_stats()
                    fps = capture_stats.get('current_fps', 0.0)
                    self.root.after(0, self.ui_manager.update_fps, fps)
                    
                    # Update connection status
                    db_connected = self.db_handler and self.db_handler.db_conn is not None
                    self.root.after(0, self.ui_manager.update_connection_status, db_connected)
                
                time.sleep(1.0)  # Update every second
                
            except Exception as e:
                self.logger.error(f"Error in UI update loop: {e}")
                time.sleep(5.0)  # Longer delay on error
    
    def reset_counts(self):
        """Reset all vehicle counts"""
        try:
            if self.ui_manager.ask_yes_no("Confirm Reset", "Reset all vehicle counts?"):
                self.line_manager.reset_all_counts()
                self.performance_stats['total_detections'] = 0
                self._update_vehicle_counts()
                self.logger.info("Vehicle counts reset")
        except Exception as e:
            self.logger.error(f"Error resetting counts: {e}")
            self.ui_manager.show_error("Reset Error", str(e))
    
    def open_line_settings(self):
        """Open line settings dialog"""
        try:
            dialog = LineSettingsDialog(self.root, self.config.line)
            if dialog.result:
                # Update line configuration
                self.config.line = dialog.result
                self.line_manager.default_config = dialog.result
                self.logger.info("Line settings updated")
        except Exception as e:
            self.logger.error(f"Error opening line settings: {e}")
            self.ui_manager.show_error("Settings Error", str(e))
    
    def enable_line_drawing(self):
        """Enable line drawing mode"""
        try:
            if not self.current_frame is None:
                self.is_line_drawing_mode = True
                self.ui_manager.show_info("Line Drawing", 
                                         "Click and drag on the video to draw a counting line")
                # TODO: Implement line drawing on canvas
            else:
                self.ui_manager.show_warning("No Video", "Start preview first to draw lines")
        except Exception as e:
            self.logger.error(f"Error enabling line drawing: {e}")
    
    def clear_lines(self):
        """Clear all counting lines"""
        try:
            if self.ui_manager.ask_yes_no("Confirm Clear", "Remove all counting lines?"):
                self.line_manager.clear_all_lines()
                self._update_line_widgets()
                self.logger.info("All counting lines cleared")
        except Exception as e:
            self.logger.error(f"Error clearing lines: {e}")
            self.ui_manager.show_error("Clear Error", str(e))
    
    def view_reports(self):
        """View counting reports"""
        try:
            # TODO: Implement reports viewing
            self.ui_manager.show_info("Reports", "Reports feature coming soon")
        except Exception as e:
            self.logger.error(f"Error viewing reports: {e}")
    
    def export_data(self):
        """Export counting data"""
        try:
            filename = self.ui_manager.get_save_file_path(
                "Export Data", 
                [("JSON files", "*.json"), ("CSV files", "*.csv")]
            )
            
            if filename:
                # TODO: Implement data export
                self.ui_manager.show_info("Export", f"Data export to {filename} coming soon")
                
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            self.ui_manager.show_error("Export Error", str(e))
    
    def on_line_toggle(self, line_id: str, enabled: bool):
        """Handle line enable/disable"""
        try:
            if enabled:
                self.line_manager.enable_line(line_id)
            else:
                self.line_manager.disable_line(line_id)
            self.logger.info(f"Line {line_id} {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            self.logger.error(f"Error toggling line: {e}")
    
    def on_line_remove(self, line_id: str):
        """Handle line removal"""
        try:
            success = self.line_manager.remove_line(line_id)
            if success:
                self.ui_manager.remove_counting_line_widget(line_id)
                self.logger.info(f"Line {line_id} removed")
        except Exception as e:
            self.logger.error(f"Error removing line: {e}")
    
    def _update_line_widgets(self):
        """Update all line widgets in UI"""
        try:
            if not self.ui_manager:
                return
                
            # Remove all existing widgets
            for line_id in list(self.ui_manager.line_widgets.keys()):
                self.ui_manager.remove_counting_line_widget(line_id)
            
            # Add current lines
            for line in self.line_manager.get_all_lines():
                self.ui_manager.add_counting_line_widget(
                    line.id, line.name, line.vehicle_counts, line.enabled
                )
                
        except Exception as e:
            self.logger.error(f"Error updating line widgets: {e}")
    
    def _update_ui_status(self):
        """Update UI status indicators"""
        try:
            if not self.ui_manager:
                return
                
            # Update model status
            if self.detection_manager.is_model_loaded():
                self.ui_manager.update_status_text("YOLO model loaded successfully")
            else:
                self.ui_manager.update_status_text("Warning: YOLO model not loaded")
                
        except Exception as e:
            self.logger.error(f"Error updating UI status: {e}")
    
    def _save_counts_to_database(self):
        """Save current counts to database"""
        try:
            if not self.db_handler:
                return
                
            total_counts = self.line_manager.get_total_counts()
            # TODO: Implement database saving with proper schema
            self.logger.info("Counts saved to database")
            
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        try:
            self.logger.info("Application closing...")
            
            # Stop all operations
            if self.is_capturing or self.is_previewing:
                self.input_manager.stop_capture()
            
            # Save configuration and lines
            self.line_manager.save_lines()
            
            # Cleanup resources
            self.detection_manager.cleanup()
            self.input_manager.cleanup()
            
            if self.db_handler:
                self.db_handler.close_connection()
            
            # Close UI
            if self.root:
                self.root.quit()
                self.root.destroy()
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            if self.root:
                self.root.quit()
    
    def run(self):
        """Run the application"""
        if self.config.headless:
            self.logger.error("Use CLI interface for headless mode")
            return
        
        if not self.root:
            self.logger.error("GUI not initialized")
            return
        
        try:
            self.logger.info("Starting Smart Traffic Counter GUI")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error running application: {e}")
        finally:
            self.on_closing()


def create_app(headless: bool = False) -> AppController:
    """Create application controller instance"""
    return AppController(headless=headless)