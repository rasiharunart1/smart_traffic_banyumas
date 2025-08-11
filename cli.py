"""
Command Line Interface for Smart Traffic Counter
Provides headless operation and batch processing capabilities
"""

import argparse
import json
import csv
import sys
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from config_manager import get_config_manager, AppConfig
from detection_manager import DetectionManager
from input_manager import InputManager
from line_manager import LineManager
from drawing_manager import DrawingManager
from utils.logger import setup_logger, get_logger
from utils.error_handler import ErrorHandler
from vehicle_tracker import VehicleTracker


class HeadlessTrafficCounter:
    """Headless version of traffic counter for CLI operation"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize managers
        self.detection_manager = DetectionManager(config.model)
        self.input_manager = InputManager()
        self.line_manager = LineManager(config.line)
        self.drawing_manager = DrawingManager(config.colors)
        self.vehicle_tracker = VehicleTracker()
        
        # Processing state
        self.is_running = False
        self.frame_count = 0
        self.start_time = None
        self.output_data = []
        self.output_file = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop_processing()
    
    def setup_input_source(self, source_type: str, source_path: Optional[str] = None,
                          region: Optional[tuple] = None) -> bool:
        """Setup input source for processing"""
        try:
            if source_type == 'screen':
                success = self.input_manager.set_screen_capture(region)
            elif source_type == 'webcam':
                camera_index = int(source_path) if source_path else 0
                success = self.input_manager.set_webcam_capture(camera_index)
            elif source_type == 'video':
                if not source_path:
                    self.logger.error("Video file path required for video input")
                    return False
                success = self.input_manager.set_video_file(source_path)
            else:
                self.logger.error(f"Unknown input source type: {source_type}")
                return False
            
            if success:
                self.logger.info(f"Input source setup successful: {source_type}")
            else:
                self.logger.error(f"Failed to setup input source: {source_type}")
            
            return success
            
        except Exception as e:
            self.error_handler.handle_capture_error(e, f"setup {source_type}")
            return False
    
    def add_counting_line(self, start_point: tuple, end_point: tuple, 
                         name: str = "Line") -> str:
        """Add a counting line"""
        try:
            line_id = self.line_manager.add_line(name, start_point, end_point)
            self.logger.info(f"Added counting line: {name} ({line_id})")
            return line_id
        except Exception as e:
            self.logger.error(f"Failed to add counting line: {e}")
            return ""
    
    def start_processing(self, duration: Optional[int] = None, 
                        output_file: Optional[str] = None,
                        save_frames: bool = False,
                        frame_output_dir: Optional[str] = None) -> bool:
        """Start headless processing"""
        if not self.detection_manager.is_model_loaded():
            self.logger.error("YOLO model not loaded, cannot start processing")
            return False
        
        self.is_running = True
        self.start_time = time.time()
        self.frame_count = 0
        self.output_file = output_file
        
        # Setup frame output directory if needed
        if save_frames and frame_output_dir:
            Path(frame_output_dir).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Starting headless processing...")
        
        # Start input capture with callback
        success = self.input_manager.start_capture(
            frame_callback=lambda frame: self._process_frame(
                frame, save_frames, frame_output_dir
            )
        )
        
        if not success:
            self.logger.error("Failed to start input capture")
            return False
        
        # Main processing loop
        try:
            while self.is_running:
                # Check duration limit
                if duration and (time.time() - self.start_time) >= duration:
                    self.logger.info(f"Reached duration limit: {duration} seconds")
                    break
                
                # Print progress periodically
                if self.frame_count % 100 == 0 and self.frame_count > 0:
                    elapsed = time.time() - self.start_time
                    fps = self.frame_count / elapsed if elapsed > 0 else 0
                    self.logger.info(f"Processed {self.frame_count} frames, FPS: {fps:.1f}")
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
        except KeyboardInterrupt:
            self.logger.info("Processing interrupted by user")
        
        finally:
            self.stop_processing()
        
        return True
    
    def _process_frame(self, frame, save_frames: bool = False, 
                      frame_output_dir: Optional[str] = None):
        """Process a single frame"""
        try:
            self.frame_count += 1
            
            # Run detection
            detections = self.detection_manager.detect_vehicles(frame)
            
            # Update tracking
            tracked_vehicles = self.vehicle_tracker.update_tracks(detections)
            
            # Check line crossings
            active_track_ids = set()
            for track_id, vehicle_info in tracked_vehicles.items():
                active_track_ids.add(track_id)
                
                if 'detection' in vehicle_info:
                    detection = vehicle_info['detection']
                    vehicle_type = detection.class_name
                    center = detection.center
                    
                    # Check for line crossings
                    crossed_lines = self.line_manager.update_vehicle_tracking(
                        track_id, center, vehicle_type
                    )
                    
                    # Log crossings
                    for line_id in crossed_lines:
                        line = self.line_manager.get_line(line_id)
                        if line:
                            self._log_detection_event(detection, line, track_id)
            
            # Cleanup old tracks
            self.line_manager.cleanup_tracking(active_track_ids)
            
            # Save frame if requested
            if save_frames and frame_output_dir:
                self._save_processed_frame(frame, detections, frame_output_dir)
                
        except Exception as e:
            self.logger.error(f"Error processing frame {self.frame_count}: {e}")
    
    def _log_detection_event(self, detection, line, track_id: int):
        """Log a vehicle detection/counting event"""
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'frame_number': self.frame_count,
            'track_id': track_id,
            'vehicle_type': detection.class_name,
            'confidence': detection.confidence,
            'line_id': line.id,
            'line_name': line.name,
            'center_x': detection.center[0],
            'center_y': detection.center[1],
            'bbox': detection.bbox
        }
        
        self.output_data.append(event_data)
        
        self.logger.info(
            f"Vehicle detected: {detection.class_name} (ID:{track_id}) "
            f"crossed {line.name} at frame {self.frame_count}"
        )
    
    def _save_processed_frame(self, frame, detections, output_dir: str):
        """Save processed frame with annotations"""
        try:
            import cv2
            
            # Draw detections and lines
            annotated_frame = self.drawing_manager.draw_detections(frame, detections)
            annotated_frame = self.drawing_manager.draw_counting_lines(
                annotated_frame, self.line_manager.get_enabled_lines()
            )
            
            # Add statistics overlay
            stats = self.line_manager.get_total_counts()
            annotated_frame = self.drawing_manager.draw_statistics_overlay(
                annotated_frame, stats
            )
            
            # Save frame
            filename = f"frame_{self.frame_count:06d}.jpg"
            filepath = Path(output_dir) / filename
            cv2.imwrite(str(filepath), annotated_frame)
            
        except Exception as e:
            self.logger.warning(f"Failed to save frame {self.frame_count}: {e}")
    
    def stop_processing(self):
        """Stop processing and cleanup"""
        self.is_running = False
        
        # Stop input capture
        self.input_manager.stop_capture()
        
        # Save output data
        if self.output_data and self.output_file:
            self._save_output_data()
        
        # Print final statistics
        self._print_final_stats()
        
        # Cleanup
        self.detection_manager.cleanup()
        self.input_manager.cleanup()
    
    def _save_output_data(self):
        """Save output data to file"""
        try:
            output_path = Path(self.output_file)
            
            if output_path.suffix.lower() == '.json':
                with open(output_path, 'w') as f:
                    json.dump({
                        'metadata': {
                            'total_frames': self.frame_count,
                            'duration_seconds': time.time() - self.start_time,
                            'lines': [line.to_dict() for line in self.line_manager.get_all_lines()]
                        },
                        'detections': self.output_data
                    }, f, indent=2)
            
            elif output_path.suffix.lower() == '.csv':
                with open(output_path, 'w', newline='') as f:
                    if self.output_data:
                        writer = csv.DictWriter(f, fieldnames=self.output_data[0].keys())
                        writer.writeheader()
                        writer.writerows(self.output_data)
            
            self.logger.info(f"Output data saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save output data: {e}")
    
    def _print_final_stats(self):
        """Print final processing statistics"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            fps = self.frame_count / elapsed if elapsed > 0 else 0
            
            self.logger.info("=== Processing Complete ===")
            self.logger.info(f"Total frames processed: {self.frame_count}")
            self.logger.info(f"Total duration: {elapsed:.1f} seconds")
            self.logger.info(f"Average FPS: {fps:.1f}")
            self.logger.info(f"Total detections: {len(self.output_data)}")
            
            # Print counts by line
            for line in self.line_manager.get_all_lines():
                counts = line.vehicle_counts
                self.logger.info(f"Line '{line.name}': {counts}")


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Smart Traffic Counter - Headless Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process video file with output
  python cli.py --input-type video --input-path video.mp4 --output results.json
  
  # Screen capture with custom region
  python cli.py --input-type screen --region 100,100,800,600 --duration 300
  
  # Webcam processing with frame saving
  python cli.py --input-type webcam --save-frames --frame-dir output_frames/
        """
    )
    
    # Input source options
    input_group = parser.add_argument_group('Input Source')
    input_group.add_argument('--input-type', 
                           choices=['screen', 'webcam', 'video'],
                           default='screen',
                           help='Type of input source')
    input_group.add_argument('--input-path',
                           help='Path to video file or camera index')
    input_group.add_argument('--region',
                           help='Screen capture region as x,y,width,height')
    
    # Counting line options
    line_group = parser.add_argument_group('Counting Lines')
    line_group.add_argument('--line',
                          action='append',
                          help='Add counting line as x1,y1,x2,y2,name')
    line_group.add_argument('--load-lines',
                          help='Load counting lines from JSON file')
    
    # Processing options
    proc_group = parser.add_argument_group('Processing')
    proc_group.add_argument('--duration',
                          type=int,
                          help='Processing duration in seconds')
    proc_group.add_argument('--model-path',
                          default='yolo11n.pt',
                          help='Path to YOLO model file')
    proc_group.add_argument('--confidence',
                          type=float,
                          default=0.15,
                          help='Detection confidence threshold')
    
    # Output options
    output_group = parser.add_argument_group('Output')
    output_group.add_argument('--output',
                            help='Output file for results (JSON or CSV)')
    output_group.add_argument('--save-frames',
                            action='store_true',
                            help='Save processed frames')
    output_group.add_argument('--frame-dir',
                            default='output_frames',
                            help='Directory for saved frames')
    
    # Logging options
    log_group = parser.add_argument_group('Logging')
    log_group.add_argument('--log-level',
                         choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                         default='INFO',
                         help='Logging level')
    log_group.add_argument('--log-file',
                         help='Log file path')
    
    return parser


def main():
    """Main CLI entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logger(
        level=getattr(__import__('logging'), args.log_level),
        log_file=args.log_file,
        console_output=True
    )
    
    logger.info("Starting Smart Traffic Counter - Headless Mode")
    
    try:
        # Load configuration
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        # Override with CLI arguments
        config.headless = True
        config.model.model_path = args.model_path
        config.model.detection_confidence = args.confidence
        config.log_level = args.log_level
        
        # Create headless counter
        counter = HeadlessTrafficCounter(config)
        
        # Parse region if provided
        region = None
        if args.region:
            try:
                region = tuple(map(int, args.region.split(',')))
                if len(region) != 4:
                    raise ValueError("Region must have 4 values")
            except ValueError as e:
                logger.error(f"Invalid region format: {e}")
                return 1
        
        # Setup input source
        success = counter.setup_input_source(
            args.input_type, args.input_path, region
        )
        if not success:
            logger.error("Failed to setup input source")
            return 1
        
        # Load or create counting lines
        if args.load_lines:
            counter.line_manager.load_lines(args.load_lines)
        elif args.line:
            for line_spec in args.line:
                try:
                    parts = line_spec.split(',')
                    if len(parts) >= 4:
                        x1, y1, x2, y2 = map(int, parts[:4])
                        name = parts[4] if len(parts) > 4 else "Line"
                        counter.add_counting_line((x1, y1), (x2, y2), name)
                except ValueError as e:
                    logger.error(f"Invalid line specification: {line_spec} - {e}")
        else:
            logger.warning("No counting lines specified")
        
        # Start processing
        success = counter.start_processing(
            duration=args.duration,
            output_file=args.output,
            save_frames=args.save_frames,
            frame_output_dir=args.frame_dir if args.save_frames else None
        )
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())