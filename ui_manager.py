"""
UI Manager for Smart Traffic Counter
Handles all GUI components and user interface management
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional, Callable, Tuple
from PIL import ImageTk
import threading

from config_manager import GUIConfig, AppConfig
from utils.logger import get_logger


class ModernButton(tk.Button):
    """Custom modern-styled button"""
    
    def __init__(self, parent, text: str, command: Optional[Callable] = None,
                 style: str = "primary", **kwargs):
        
        # Define button styles
        styles = {
            "primary": {"bg": "#0078d4", "fg": "white", "activebackground": "#106ebe"},
            "success": {"bg": "#107c10", "fg": "white", "activebackground": "#0e6e0e"},
            "danger": {"bg": "#d13438", "fg": "white", "activebackground": "#b92b2f"},
            "secondary": {"bg": "#6c757d", "fg": "white", "activebackground": "#5a6268"}
        }
        
        style_config = styles.get(style, styles["primary"])
        
        # Default button configuration
        default_config = {
            "font": ('Arial', 9),
            "relief": "flat",
            "bd": 0,
            "pady": 5,
            "cursor": "hand2",
            **style_config
        }
        
        # Override with custom kwargs
        default_config.update(kwargs)
        
        super().__init__(parent, text=text, command=command, **default_config)


class CountingLineWidget(tk.Frame):
    """Widget for displaying and managing a single counting line"""
    
    def __init__(self, parent, line_id: str, line_name: str, 
                 counts: Dict[str, int], enabled: bool = True,
                 on_toggle: Optional[Callable] = None,
                 on_remove: Optional[Callable] = None):
        super().__init__(parent, bg='#2d2d2d', relief='solid', bd=1)
        
        self.line_id = line_id
        self.on_toggle = on_toggle
        self.on_remove = on_remove
        
        self._create_widgets(line_name, counts, enabled)
    
    def _create_widgets(self, line_name: str, counts: Dict[str, int], enabled: bool):
        """Create line widget components"""
        # Header frame
        header_frame = tk.Frame(self, bg='#2d2d2d')
        header_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Line name and status
        self.name_label = tk.Label(header_frame, text=line_name,
                                  bg='#2d2d2d', fg='#ffffff',
                                  font=('Arial', 9, 'bold'))
        self.name_label.pack(side=tk.LEFT)
        
        # Enable/disable toggle
        self.enabled_var = tk.BooleanVar(value=enabled)
        self.toggle_btn = tk.Checkbutton(header_frame, text="Enabled",
                                        variable=self.enabled_var,
                                        bg='#2d2d2d', fg='#ffffff',
                                        selectcolor='#0078d4',
                                        command=self._on_toggle)
        self.toggle_btn.pack(side=tk.RIGHT, padx=5)
        
        # Remove button
        remove_btn = tk.Button(header_frame, text="🗑️", 
                              command=self._on_remove,
                              bg='#d13438', fg='white',
                              font=('Arial', 8), relief='flat',
                              bd=0, width=3)
        remove_btn.pack(side=tk.RIGHT, padx=2)
        
        # Counts frame
        counts_frame = tk.Frame(self, bg='#2d2d2d')
        counts_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Vehicle type counts
        self.count_labels = {}
        for vehicle_type, count in counts.items():
            if vehicle_type != 'total':
                label = tk.Label(counts_frame, 
                               text=f"{vehicle_type.title()}: {count}",
                               bg='#2d2d2d', fg='#ffffff',
                               font=('Arial', 8))
                label.pack(side=tk.LEFT, padx=5)
                self.count_labels[vehicle_type] = label
        
        # Total count (highlighted)
        total_label = tk.Label(counts_frame,
                              text=f"Total: {counts.get('total', 0)}",
                              bg='#2d2d2d', fg='#00d4ff',
                              font=('Arial', 9, 'bold'))
        total_label.pack(side=tk.RIGHT, padx=5)
        self.count_labels['total'] = total_label
    
    def _on_toggle(self):
        """Handle enable/disable toggle"""
        if self.on_toggle:
            self.on_toggle(self.line_id, self.enabled_var.get())
    
    def _on_remove(self):
        """Handle remove button click"""
        if self.on_remove:
            result = messagebox.askyesno("Confirm", 
                                       f"Remove counting line '{self.name_label.cget('text')}'?")
            if result:
                self.on_remove(self.line_id)
    
    def update_counts(self, counts: Dict[str, int]):
        """Update displayed counts"""
        for vehicle_type, count in counts.items():
            if vehicle_type in self.count_labels:
                if vehicle_type == 'total':
                    self.count_labels[vehicle_type].config(text=f"Total: {count}")
                else:
                    self.count_labels[vehicle_type].config(text=f"{vehicle_type.title()}: {count}")


class UIManager:
    """Manages the entire user interface for the Smart Traffic Counter"""
    
    def __init__(self, root: tk.Tk, config: GUIConfig):
        self.root = root
        self.config = config
        self.logger = get_logger(__name__)
        
        # UI state
        self.current_frame_image: Optional[ImageTk.PhotoImage] = None
        self.line_widgets: Dict[str, CountingLineWidget] = {}
        
        # Callbacks (to be set by app controller)
        self.callbacks = {
            'select_region': None,
            'capture_full_screen': None,
            'toggle_preview': None,
            'toggle_capture': None,
            'reset_counts': None,
            'line_settings': None,
            'draw_line': None,
            'clear_line': None,
            'save_settings': None,
            'load_settings': None,
            'view_reports': None,
            'export_data': None,
            'on_line_toggle': None,
            'on_line_remove': None,
            'on_closing': None
        }
        
        # UI components (will be created)
        self.video_canvas: Optional[tk.Canvas] = None
        self.status_label: Optional[tk.Label] = None
        self.fps_label: Optional[tk.Label] = None
        self.connection_status: Optional[tk.Label] = None
        self.lines_frame: Optional[tk.Frame] = None
        self.preview_button: Optional[tk.Button] = None
        self.capture_button: Optional[tk.Button] = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the complete user interface"""
        self._configure_root()
        self._create_header()
        self._create_main_layout()
        self._create_footer()
    
    def _configure_root(self):
        """Configure root window"""
        self.root.title(self.config.window_title)
        self.root.geometry(self.config.window_size)
        self.root.configure(bg='#1e1e1e')
        
        # Set minimum size
        width, height = map(int, self.config.window_size.split('x'))
        self.root.minsize(max(800, width//2), max(600, height//2))
        
        # Configure grid weights
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Set close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_header(self):
        """Create header bar with title and status"""
        header_frame = tk.Frame(self.root, bg='#363636', height=60)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        header_frame.grid_propagate(False)
        
        # App title
        title_frame = tk.Frame(header_frame, bg='#363636')
        title_frame.pack(side=tk.LEFT, padx=15, pady=15)
        
        title_label = tk.Label(title_frame, 
                              text="🚗 Smart Traffic Counter v3.0", 
                              bg='#363636', fg='#00d4ff',
                              font=('Arial', 14, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(title_frame,
                                 text="Real-time Vehicle Detection & Counting with AI",
                                 bg='#363636', fg='#ffffff',
                                 font=('Arial', 10))
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status indicators
        status_frame = tk.Frame(header_frame, bg='#363636')
        status_frame.pack(side=tk.RIGHT, padx=15, pady=15)
        
        # Database connection status
        self.connection_status = tk.Label(status_frame,
                                         text="🔴 DB Disconnected",
                                         bg='#363636', fg='#ffffff',
                                         font=('Arial', 10))
        self.connection_status.pack(side=tk.RIGHT, padx=(0, 10))
        
        # FPS display
        self.fps_label = tk.Label(status_frame,
                                 text="FPS: 0.0",
                                 bg='#363636', fg='#ffffff',
                                 font=('Arial', 10))
        self.fps_label.pack(side=tk.RIGHT, padx=(0, 10))
    
    def _create_main_layout(self):
        """Create main application layout"""
        # Left sidebar
        self._create_left_sidebar()
        
        # Center video area
        self._create_center_video_area()
        
        # Right sidebar
        self._create_right_sidebar()
    
    def _create_left_sidebar(self):
        """Create left sidebar with controls"""
        left_frame = tk.Frame(self.root, bg='#2d2d2d', width=280)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_frame.grid_propagate(False)
        
        # Screen Capture Section
        capture_card = tk.LabelFrame(left_frame, text="📹 Screen Capture", 
                                   bg='#2d2d2d', fg='#ffffff',
                                   font=('Arial', 10, 'bold'),
                                   relief='solid', bd=1)
        capture_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        capture_inner = tk.Frame(capture_card, bg='#2d2d2d')
        capture_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ModernButton(capture_inner, text="🎯 Select Region", 
                    command=self._call_callback('select_region')).pack(fill=tk.X, pady=2)
        
        ModernButton(capture_inner, text="🖥️ Full Screen", 
                    command=self._call_callback('capture_full_screen')).pack(fill=tk.X, pady=2)
        
        self.preview_button = ModernButton(capture_inner, text="▶️ Start Preview", 
                                          command=self._call_callback('toggle_preview'),
                                          state='disabled', style="success")
        self.preview_button.pack(fill=tk.X, pady=(5, 0))
        
        # Line Configuration Section
        line_card = tk.LabelFrame(left_frame, text="📏 Counting Line Setup", 
                                 bg='#2d2d2d', fg='#ffffff',
                                 font=('Arial', 10, 'bold'),
                                 relief='solid', bd=1)
        line_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        line_inner = tk.Frame(line_card, bg='#2d2d2d')
        line_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ModernButton(line_inner, text="⚙️ Line Settings", 
                    command=self._call_callback('line_settings')).pack(fill=tk.X, pady=2)
        
        ModernButton(line_inner, text="✏️ Draw Line", 
                    command=self._call_callback('draw_line')).pack(fill=tk.X, pady=2)
        
        ModernButton(line_inner, text="🗑️ Clear Line", 
                    command=self._call_callback('clear_line'),
                    style="danger").pack(fill=tk.X, pady=2)
        
        # Control Section
        control_card = tk.LabelFrame(left_frame, text="🎮 Controls", 
                                   bg='#2d2d2d', fg='#ffffff',
                                   font=('Arial', 10, 'bold'),
                                   relief='solid', bd=1)
        control_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        control_inner = tk.Frame(control_card, bg='#2d2d2d')
        control_inner.pack(fill=tk.X, padx=10, pady=10)
        
        self.capture_button = ModernButton(control_inner, text="🔴 Start Counting", 
                                          command=self._call_callback('toggle_capture'),
                                          style="success")
        self.capture_button.pack(fill=tk.X, pady=2)
        
        ModernButton(control_inner, text="🔄 Reset Counts", 
                    command=self._call_callback('reset_counts'),
                    style="secondary").pack(fill=tk.X, pady=2)
    
    def _create_center_video_area(self):
        """Create center video display area"""
        center_frame = tk.Frame(self.root, bg='#1e1e1e')
        center_frame.grid(row=1, column=1, sticky="nsew", padx=10)
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)
        
        # Video canvas
        self.video_canvas = tk.Canvas(center_frame, bg='#000000', 
                                     highlightthickness=0)
        self.video_canvas.grid(row=0, column=0, sticky="nsew")
        
        # Status overlay
        self.status_label = tk.Label(self.video_canvas, 
                                   text="Select a screen region or video source to begin",
                                   bg='#000000', fg='#ffffff',
                                   font=('Arial', 12))
        self.status_label.place(relx=0.5, rely=0.5, anchor='center')
    
    def _create_right_sidebar(self):
        """Create right sidebar with statistics and line management"""
        right_frame = tk.Frame(self.root, bg='#2d2d2d', width=300)
        right_frame.grid(row=1, column=2, sticky="nsew", padx=(10, 0))
        right_frame.grid_propagate(False)
        
        # Vehicle Counts Section
        counts_card = tk.LabelFrame(right_frame, text="📊 Vehicle Counts", 
                                  bg='#2d2d2d', fg='#ffffff',
                                  font=('Arial', 10, 'bold'),
                                  relief='solid', bd=1)
        counts_card.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        self.counts_inner = tk.Frame(counts_card, bg='#2d2d2d')
        self.counts_inner.pack(fill=tk.X, padx=10, pady=10)
        
        # Default count labels
        self.count_labels = {}
        for vehicle_type in ['car', 'motorcycle', 'bus', 'truck', 'total']:
            label = tk.Label(self.counts_inner, 
                           text=f"{vehicle_type.title()}: 0",
                           bg='#2d2d2d', 
                           fg='#00d4ff' if vehicle_type == 'total' else '#ffffff',
                           font=('Arial', 11, 'bold' if vehicle_type == 'total' else 'normal'))
            label.pack(anchor='w', pady=2)
            self.count_labels[vehicle_type] = label
        
        # Counting Lines Management
        lines_card = tk.LabelFrame(right_frame, text="📏 Counting Lines", 
                                 bg='#2d2d2d', fg='#ffffff',
                                 font=('Arial', 10, 'bold'),
                                 relief='solid', bd=1)
        lines_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15), padx=10)
        
        # Lines container with scrollbar
        lines_container = tk.Frame(lines_card, bg='#2d2d2d')
        lines_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollable frame
        canvas = tk.Canvas(lines_container, bg='#2d2d2d', highlightthickness=0)
        scrollbar = ttk.Scrollbar(lines_container, orient="vertical", command=canvas.yview)
        self.lines_frame = tk.Frame(canvas, bg='#2d2d2d')
        
        self.lines_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.lines_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Data Management Section
        data_card = tk.LabelFrame(right_frame, text="💾 Data Management", 
                                bg='#2d2d2d', fg='#ffffff',
                                font=('Arial', 10, 'bold'),
                                relief='solid', bd=1)
        data_card.pack(fill=tk.X, padx=10)
        
        data_inner = tk.Frame(data_card, bg='#2d2d2d')
        data_inner.pack(fill=tk.X, padx=10, pady=10)
        
        ModernButton(data_inner, text="📊 View Reports", 
                    command=self._call_callback('view_reports')).pack(fill=tk.X, pady=2)
        
        ModernButton(data_inner, text="📤 Export Data", 
                    command=self._call_callback('export_data')).pack(fill=tk.X, pady=2)
    
    def _create_footer(self):
        """Create footer with additional status information"""
        footer_frame = tk.Frame(self.root, bg='#363636', height=30)
        footer_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        footer_frame.grid_propagate(False)
        
        self.status_text = tk.Label(footer_frame,
                                   text="Ready - Select input source to begin",
                                   bg='#363636', fg='#ffffff',
                                   font=('Arial', 9))
        self.status_text.pack(side=tk.LEFT, padx=10, pady=5)
    
    def _call_callback(self, callback_name: str):
        """Create a wrapper function to call callbacks safely"""
        def wrapper(*args, **kwargs):
            callback = self.callbacks.get(callback_name)
            if callback:
                try:
                    return callback(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error in callback {callback_name}: {e}")
                    messagebox.showerror("Error", f"An error occurred: {e}")
            else:
                self.logger.warning(f"No callback set for {callback_name}")
        return wrapper
    
    def _on_closing(self):
        """Handle window close event"""
        callback = self.callbacks.get('on_closing')
        if callback:
            callback()
        else:
            self.root.quit()
    
    def set_callback(self, name: str, callback: Callable):
        """Set a callback function"""
        if name in self.callbacks:
            self.callbacks[name] = callback
        else:
            self.logger.warning(f"Unknown callback: {name}")
    
    def update_video_display(self, image: ImageTk.PhotoImage):
        """Update the video display with new frame"""
        if self.video_canvas and image:
            self.current_frame_image = image
            
            # Clear canvas
            self.video_canvas.delete("all")
            
            # Get canvas size
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            # Center image
            x = (canvas_width - image.width()) // 2
            y = (canvas_height - image.height()) // 2
            
            self.video_canvas.create_image(x, y, anchor="nw", image=image)
            
            # Hide status label when showing video
            self.status_label.place_forget()
    
    def show_status_message(self, message: str):
        """Show status message in video area"""
        if self.status_label:
            self.status_label.config(text=message)
            self.status_label.place(relx=0.5, rely=0.5, anchor='center')
    
    def update_fps(self, fps: float):
        """Update FPS display"""
        if self.fps_label:
            self.fps_label.config(text=f"FPS: {fps:.1f}")
    
    def update_connection_status(self, connected: bool):
        """Update database connection status"""
        if self.connection_status:
            if connected:
                self.connection_status.config(text="🟢 DB Connected")
            else:
                self.connection_status.config(text="🔴 DB Disconnected")
    
    def update_status_text(self, text: str):
        """Update footer status text"""
        if self.status_text:
            self.status_text.config(text=text)
    
    def update_vehicle_counts(self, counts: Dict[str, int]):
        """Update vehicle count displays"""
        for vehicle_type, count in counts.items():
            if vehicle_type in self.count_labels:
                self.count_labels[vehicle_type].config(text=f"{vehicle_type.title()}: {count}")
    
    def update_button_states(self, states: Dict[str, str]):
        """Update button states and text"""
        if 'preview' in states and self.preview_button:
            self.preview_button.config(text=states['preview'], 
                                      state=states.get('preview_state', 'normal'))
        
        if 'capture' in states and self.capture_button:
            self.capture_button.config(text=states['capture'],
                                      state=states.get('capture_state', 'normal'))
    
    def add_counting_line_widget(self, line_id: str, line_name: str, 
                                counts: Dict[str, int], enabled: bool = True):
        """Add a counting line widget to the UI"""
        if line_id in self.line_widgets:
            # Update existing widget
            self.line_widgets[line_id].update_counts(counts)
            return
        
        # Create new widget
        widget = CountingLineWidget(
            self.lines_frame, line_id, line_name, counts, enabled,
            on_toggle=self._call_callback('on_line_toggle'),
            on_remove=self._call_callback('on_line_remove')
        )
        widget.pack(fill=tk.X, padx=5, pady=2)
        
        self.line_widgets[line_id] = widget
    
    def remove_counting_line_widget(self, line_id: str):
        """Remove a counting line widget from the UI"""
        if line_id in self.line_widgets:
            self.line_widgets[line_id].destroy()
            del self.line_widgets[line_id]
    
    def update_counting_line_widget(self, line_id: str, counts: Dict[str, int]):
        """Update a specific counting line widget"""
        if line_id in self.line_widgets:
            self.line_widgets[line_id].update_counts(counts)
    
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """Show info dialog"""
        messagebox.showinfo(title, message)
    
    def show_warning(self, title: str, message: str):
        """Show warning dialog"""
        messagebox.showwarning(title, message)
    
    def ask_yes_no(self, title: str, message: str) -> bool:
        """Show yes/no dialog"""
        return messagebox.askyesno(title, message)
    
    def get_file_path(self, title: str, filetypes: list = None) -> Optional[str]:
        """Show file selection dialog"""
        if filetypes is None:
            filetypes = [("All files", "*.*")]
        
        return filedialog.askopenfilename(title=title, filetypes=filetypes)
    
    def get_save_file_path(self, title: str, filetypes: list = None) -> Optional[str]:
        """Show save file dialog"""
        if filetypes is None:
            filetypes = [("All files", "*.*")]
        
        return filedialog.asksaveasfilename(title=title, filetypes=filetypes)