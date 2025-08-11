"""
Advanced Settings Dialog untuk mengatur semua parameter konfigurasi
Updated: 2025-08-01 04:31:16 UTC by Rasiharunar
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import json
import time
from config import *

class AdvancedSettingsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
        # Load current settings
        self.settings = {
            'model': MODEL_CONFIG.copy(),
            'tracking': TRACKING_CONFIG.copy(),
            'line': DEFAULT_LINE_SETTINGS.copy(),
            'colors': COLOR_CONFIG.copy(),
            'gui': GUI_CONFIG.copy()
        }
        
        self.create_dialog()
        
    def create_dialog(self):
        """Create the advanced settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("⚙️ Advanced Configuration Settings")
        self.dialog.geometry("800x700")
        self.dialog.configure(bg='#1e1e1e')
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            (self.dialog.winfo_screenwidth() // 2) - 400,
            (self.dialog.winfo_screenheight() // 2) - 350
        ))
        
        self.create_widgets()
        self.load_current_values()
        
    def create_widgets(self):
        """Create all widgets"""
        main_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Notebook for tabs
        self.create_notebook(main_frame)
        
        # Buttons
        self.create_buttons(main_frame)
    
    def create_header(self, parent):
        """Create header section"""
        header_frame = tk.Frame(parent, bg='#363636', relief='solid', bd=1)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(header_frame,
                              text="⚙️ Advanced Configuration Settings",
                              bg='#363636', fg='#00d4ff',
                              font=('Arial', 16, 'bold'))
        title_label.pack(pady=15)
        
        subtitle_label = tk.Label(header_frame,
                                 text="Configure YOLO Model, Tracking, Colors, and GUI Parameters",
                                 bg='#363636', fg='#ffffff',
                                 font=('Arial', 10))
        subtitle_label.pack(pady=(0, 15))
    
    def create_notebook(self, parent):
        """Create notebook with configuration tabs"""
        style = ttk.Style()
        style.configure('Settings.TNotebook', background='#2d2d2d')
        style.configure('Settings.TNotebook.Tab', background='#363636', foreground='#ffffff', padding=[15, 8])
        style.map('Settings.TNotebook.Tab', background=[('selected', '#0078d4')])
        
        self.notebook = ttk.Notebook(parent, style='Settings.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create tabs
        self.create_model_tab()
        self.create_tracking_tab()
        self.create_line_tab()
        self.create_colors_tab()
        self.create_gui_tab()
    
    def create_model_tab(self):
        """Create YOLO model configuration tab"""
        model_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(model_frame, text="🤖 YOLO Model")
        
        # Model file section
        model_file_frame = tk.LabelFrame(model_frame, text="Model Configuration",
                                        bg='#2d2d2d', fg='#ffffff',
                                        font=('Arial', 11, 'bold'),
                                        relief='solid', bd=1)
        model_file_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Model path
        path_frame = tk.Frame(model_file_frame, bg='#2d2d2d')
        path_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(path_frame, text="Model Path:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.model_path_var = tk.StringVar(value=self.settings['model']['model_path'])
        model_path_entry = tk.Entry(path_frame, textvariable=self.model_path_var,
                                   bg='#4a4a4a', fg='#ffffff',
                                   font=('Arial', 10), width=30)
        model_path_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        
        tk.Button(path_frame, text="📁 Browse",
                 command=self.browse_model_file,
                 bg='#0078d4', fg='white',
                 font=('Arial', 9), relief='flat',
                 bd=0, pady=3, padx=8).pack(side=tk.RIGHT)
        
        # Detection parameters
        detection_frame = tk.LabelFrame(model_frame, text="Detection Parameters",
                                       bg='#2d2d2d', fg='#ffffff',
                                       font=('Arial', 11, 'bold'),
                                       relief='solid', bd=1)
        detection_frame.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Create parameter controls
        params = [
            ('Confidence Threshold:', 'confidence_threshold', 0.01, 1.0, 0.01),
            ('IoU Threshold:', 'iou_threshold', 0.1, 1.0, 0.01),
            ('Detection Confidence:', 'detection_confidence', 0.01, 1.0, 0.01)
        ]
        
        self.model_vars = {}
        for i, (label, key, min_val, max_val, step) in enumerate(params):
            param_frame = tk.Frame(detection_frame, bg='#2d2d2d')
            param_frame.pack(fill=tk.X, padx=15, pady=8)
            
            tk.Label(param_frame, text=label,
                    bg='#2d2d2d', fg='#ffffff',
                    font=('Arial', 10)).pack(side=tk.LEFT, anchor='w')
            
            self.model_vars[key] = tk.DoubleVar(value=self.settings['model'][key])
            
            # Entry for precise control
            entry_frame = tk.Frame(param_frame, bg='#2d2d2d')
            entry_frame.pack(side=tk.RIGHT)
            
            entry = tk.Entry(entry_frame, textvariable=self.model_vars[key],
                           bg='#4a4a4a', fg='#ffffff',
                           font=('Arial', 10), width=8,
                           validate='key', validatecommand=(self.dialog.register(self.validate_float), '%P'))
            entry.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Scale for visual control
            scale = tk.Scale(param_frame, variable=self.model_vars[key],
                           from_=min_val, to=max_val, resolution=step,
                           orient=tk.HORIZONTAL, bg='#2d2d2d', fg='#ffffff',
                           highlightthickness=0, length=200)
            scale.pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_tracking_tab(self):
        """Create tracking configuration tab"""
        tracking_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(tracking_frame, text="🎯 Tracking")
        
        # Tracking parameters
        tracking_params_frame = tk.LabelFrame(tracking_frame, text="Tracking Parameters",
                                            bg='#2d2d2d', fg='#ffffff',
                                            font=('Arial', 11, 'bold'),
                                            relief='solid', bd=1)
        tracking_params_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tracking_params = [
            ('Max Distance (pixels):', 'max_distance', 10, 500, 10, 'int'),
            ('Path History Length:', 'path_history_length', 3, 50, 1, 'int'),
            ('Track Timeout (seconds):', 'track_timeout', 0.5, 10.0, 0.1, 'float'),
            ('Min Detection Size (pixels):', 'min_detection_size', 5, 200, 5, 'int')
        ]
        
        self.tracking_vars = {}
        for label, key, min_val, max_val, step, var_type in tracking_params:
            param_frame = tk.Frame(tracking_params_frame, bg='#2d2d2d')
            param_frame.pack(fill=tk.X, padx=15, pady=8)
            
            tk.Label(param_frame, text=label,
                    bg='#2d2d2d', fg='#ffffff',
                    font=('Arial', 10)).pack(side=tk.LEFT, anchor='w')
            
            if var_type == 'int':
                self.tracking_vars[key] = tk.IntVar(value=self.settings['tracking'][key])
                validate_cmd = (self.dialog.register(self.validate_int), '%P')
            else:
                self.tracking_vars[key] = tk.DoubleVar(value=self.settings['tracking'][key])
                validate_cmd = (self.dialog.register(self.validate_float), '%P')
            
            # Entry for precise control
            entry_frame = tk.Frame(param_frame, bg='#2d2d2d')
            entry_frame.pack(side=tk.RIGHT)
            
            entry = tk.Entry(entry_frame, textvariable=self.tracking_vars[key],
                           bg='#4a4a4a', fg='#ffffff',
                           font=('Arial', 10), width=8,
                           validate='key', validatecommand=validate_cmd)
            entry.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Scale for visual control
            scale = tk.Scale(param_frame, variable=self.tracking_vars[key],
                           from_=min_val, to=max_val, resolution=step,
                           orient=tk.HORIZONTAL, bg='#2d2d2d', fg='#ffffff',
                           highlightthickness=0, length=200)
            scale.pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_line_tab(self):
        """Create line settings tab"""
        line_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(line_frame, text="📏 Line Settings")
        
        # Default line settings
        default_line_frame = tk.LabelFrame(line_frame, text="Default Line Settings",
                                         bg='#2d2d2d', fg='#ffffff',
                                         font=('Arial', 11, 'bold'),
                                         relief='solid', bd=1)
        default_line_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Line color
        color_frame = tk.Frame(default_line_frame, bg='#2d2d2d')
        color_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(color_frame, text="Default Line Color:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.line_color_var = tk.StringVar(value=self.settings['line']['line_color'])
        self.line_color_button = tk.Button(color_frame, text="   ", width=5,
                                          bg=self.settings['line']['line_color'],
                                          command=self.choose_line_color)
        self.line_color_button.pack(side=tk.RIGHT)
        
        # Line thickness
        thickness_frame = tk.Frame(default_line_frame, bg='#2d2d2d')
        thickness_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(thickness_frame, text="Default Thickness:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.line_thickness_var = tk.IntVar(value=self.settings['line']['line_thickness'])
        thickness_entry = tk.Entry(thickness_frame, textvariable=self.line_thickness_var,
                                  bg='#4a4a4a', fg='#ffffff',
                                  font=('Arial', 10), width=8,
                                  validate='key', validatecommand=(self.dialog.register(self.validate_int), '%P'))
        thickness_entry.pack(side=tk.RIGHT)
        
        # Detection threshold
        threshold_frame = tk.Frame(default_line_frame, bg='#2d2d2d')
        threshold_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(threshold_frame, text="Detection Threshold:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.detection_threshold_var = tk.IntVar(value=self.settings['line']['detection_threshold'])
        
        threshold_entry = tk.Entry(threshold_frame, textvariable=self.detection_threshold_var,
                                 bg='#4a4a4a', fg='#ffffff',
                                 font=('Arial', 10), width=8,
                                 validate='key', validatecommand=(self.dialog.register(self.validate_int), '%P'))
        threshold_entry.pack(side=tk.RIGHT, padx=(10, 0))
        
        threshold_scale = tk.Scale(threshold_frame, variable=self.detection_threshold_var,
                                 from_=5, to=200, resolution=5,
                                 orient=tk.HORIZONTAL, bg='#2d2d2d', fg='#ffffff',
                                 highlightthickness=0, length=200)
        threshold_scale.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Label settings
        label_frame = tk.Frame(default_line_frame, bg='#2d2d2d')
        label_frame.pack(fill=tk.X, padx=15, pady=8)
        
        self.show_label_var = tk.BooleanVar(value=self.settings['line']['show_label'])
        tk.Checkbutton(label_frame, text="Show Labels by Default",
                      variable=self.show_label_var,
                      bg='#2d2d2d', fg='#ffffff',
                      selectcolor='#363636',
                      font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        # Default label text
        label_text_frame = tk.Frame(default_line_frame, bg='#2d2d2d')
        label_text_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(label_text_frame, text="Default Label Text:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.label_text_var = tk.StringVar(value=self.settings['line']['label_text'])
        tk.Entry(label_text_frame, textvariable=self.label_text_var,
                bg='#4a4a4a', fg='#ffffff',
                font=('Arial', 10), width=20).pack(side=tk.RIGHT)
    
    def create_colors_tab(self):
        """Create color configuration tab"""
        colors_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(colors_frame, text="🎨 Colors")
        
        # Vehicle colors
        vehicle_colors_frame = tk.LabelFrame(colors_frame, text="Vehicle Visualization Colors",
                                           bg='#2d2d2d', fg='#ffffff',
                                           font=('Arial', 11, 'bold'),
                                           relief='solid', bd=1)
        vehicle_colors_frame.pack(fill=tk.X, padx=15, pady=15)
        
        color_configs = [
            ('Active Vehicle Box:', 'active_vehicle', 'Green color for active vehicles'),
            ('Counted Vehicle Box:', 'counted_vehicle', 'Gray color for counted vehicles'),
            ('Active Center Dot:', 'center_dot_active', 'Red dot for active vehicle centers'),
            ('Counted Center Dot:', 'center_dot_counted', 'Gray dot for counted vehicle centers'),
            ('Active Tracking Path:', 'tracking_path', 'Blue path for active vehicles'),
            ('Counted Tracking Path:', 'tracking_path_counted', 'Gray path for counted vehicles')
        ]
        
        self.color_vars = {}
        self.color_buttons = {}
        
        for label, key, description in color_configs:
            color_frame = tk.Frame(vehicle_colors_frame, bg='#2d2d2d')
            color_frame.pack(fill=tk.X, padx=15, pady=5)
            
            # Label
            label_frame = tk.Frame(color_frame, bg='#2d2d2d')
            label_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(label_frame, text=label,
                    bg='#2d2d2d', fg='#ffffff',
                    font=('Arial', 10, 'bold')).pack(anchor='w')
            
            tk.Label(label_frame, text=description,
                    bg='#2d2d2d', fg='#888888',
                    font=('Arial', 8)).pack(anchor='w')
            
            # Color button (convert BGR to RGB for display)
            bgr_color = self.settings['colors'][key]
            rgb_color = f"#{bgr_color[2]:02x}{bgr_color[1]:02x}{bgr_color[0]:02x}"
            
            self.color_vars[key] = tk.StringVar(value=rgb_color)
            self.color_buttons[key] = tk.Button(color_frame, text="   ", width=8,
                                               bg=rgb_color,
                                               command=lambda k=key: self.choose_vehicle_color(k))
            self.color_buttons[key].pack(side=tk.RIGHT, padx=5)
    
    def create_gui_tab(self):
        """Create GUI configuration tab"""
        gui_frame = tk.Frame(self.notebook, bg='#2d2d2d')
        self.notebook.add(gui_frame, text="🖥️ GUI")
        
        # Window settings
        window_frame = tk.LabelFrame(gui_frame, text="Window Settings",
                                    bg='#2d2d2d', fg='#ffffff',
                                    font=('Arial', 11, 'bold'),
                                    relief='solid', bd=1)
        window_frame.pack(fill=tk.X, padx=15, pady=15)
        
        # Window title
        title_frame = tk.Frame(window_frame, bg='#2d2d2d')
        title_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(title_frame, text="Window Title:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.window_title_var = tk.StringVar(value=self.settings['gui']['window_title'])
        tk.Entry(title_frame, textvariable=self.window_title_var,
                bg='#4a4a4a', fg='#ffffff',
                font=('Arial', 10), width=40).pack(side=tk.RIGHT)
        
        # Window size
        size_frame = tk.Frame(window_frame, bg='#2d2d2d')
        size_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(size_frame, text="Default Window Size:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.window_size_var = tk.StringVar(value=self.settings['gui']['window_size'])
        size_combo = ttk.Combobox(size_frame, textvariable=self.window_size_var,
                                 values=['1200x800', '1400x900', '1600x1000', '1920x1080'],
                                 width=15, font=('Arial', 10))
        size_combo.pack(side=tk.RIGHT)
        
        # FPS target
        fps_frame = tk.Frame(window_frame, bg='#2d2d2d')
        fps_frame.pack(fill=tk.X, padx=15, pady=8)
        
        tk.Label(fps_frame, text="Target FPS:",
                bg='#2d2d2d', fg='#ffffff',
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        self.fps_target_var = tk.IntVar(value=self.settings['gui']['fps_target'])
        
        fps_entry = tk.Entry(fps_frame, textvariable=self.fps_target_var,
                           bg='#4a4a4a', fg='#ffffff',
                           font=('Arial', 10), width=8,
                           validate='key', validatecommand=(self.dialog.register(self.validate_int), '%P'))
        fps_entry.pack(side=tk.RIGHT, padx=(10, 0))
        
        fps_scale = tk.Scale(fps_frame, variable=self.fps_target_var,
                           from_=10, to=60, resolution=5,
                           orient=tk.HORIZONTAL, bg='#2d2d2d', fg='#ffffff',
                           highlightthickness=0, length=200)
        fps_scale.pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_buttons(self, parent):
        """Create dialog buttons with save functionality"""
        button_frame = tk.Frame(parent, bg='#1e1e1e')
        button_frame.pack(fill=tk.X)
        
        # Left side buttons
        left_buttons = tk.Frame(button_frame, bg='#1e1e1e')
        left_buttons.pack(side=tk.LEFT)
        
        tk.Button(left_buttons, text="💾 Save Config",
                 command=self.save_config_to_file,
                 bg='#107c10', fg='white',
                 font=('Arial', 10, 'bold'), relief='flat',
                 bd=0, pady=8, padx=15).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(left_buttons, text="📁 Load Config",
                 command=self.load_config_from_file,
                 bg='#0078d4', fg='white',
                 font=('Arial', 10, 'bold'), relief='flat',
                 bd=0, pady=8, padx=15).pack(side=tk.LEFT)
        
        # Right side buttons
        right_buttons = tk.Frame(button_frame, bg='#1e1e1e')
        right_buttons.pack(side=tk.RIGHT)
        
        tk.Button(right_buttons, text="✅ Apply Settings",
                 command=self.apply_settings,
                 bg='#107c10', fg='white',
                 font=('Arial', 11, 'bold'), relief='flat',
                 bd=0, pady=10, padx=20).pack(side=tk.RIGHT, padx=10)
        
        tk.Button(right_buttons, text="❌ Cancel",
                 command=self.cancel_settings,
                 bg='#d13438', fg='white',
                 font=('Arial', 11, 'bold'), relief='flat',
                 bd=0, pady=10, padx=20).pack(side=tk.RIGHT)
    
    # Validation methods
    def validate_float(self, value):
        """Validate float input"""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def validate_int(self, value):
        """Validate integer input"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def load_current_values(self):
        """Load current configuration values"""
        pass
    
    def browse_model_file(self):
        """Browse for YOLO model file"""
        filename = filedialog.askopenfilename(
            title="Select YOLO Model File",
            filetypes=[("YOLO Models", "*.pt"), ("All files", "*.*")]
        )
        if filename:
            self.model_path_var.set(filename)
    
    def choose_line_color(self):
        """Choose line color"""
        color = colorchooser.askcolor(initialcolor=self.line_color_var.get())
        if color[1]:
            self.line_color_var.set(color[1])
            self.line_color_button.config(bg=color[1])
    
    def choose_vehicle_color(self, color_key):
        """Choose vehicle color"""
        current_rgb = self.color_vars[color_key].get()
        color = colorchooser.askcolor(initialcolor=current_rgb)
        if color[1]:
            self.color_vars[color_key].set(color[1])
            self.color_buttons[color_key].config(bg=color[1])
    
    def save_config_to_file(self):
        """Save current config to file"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialvalue=f"advanced_config_{timestamp}.json"
        )
        if filename:
            try:
                config = self.get_current_settings()
                config["metadata"] = {
                    "app_name": "Smart Traffic Counter v3.0",
                    "version": "3.0.0",
                    "created_by": "Rasiharunar",
                    "created_date": "2025-08-01 04:31:16 UTC",
                    "description": "Advanced settings configuration export",
                    "config_type": "advanced_settings"
                }
                
                with open(filename, 'w') as f:
                    json.dump(config, f, indent=4)
                    
                messagebox.showinfo("Config Saved", 
                                  f"✅ Advanced configuration saved!\n\n"
                                  f"📁 File: {filename}\n"
                                  f"🕐 Time: 2025-08-01 04:31:16 UTC\n"
                                  f"👤 By: Rasiharunar")
            except Exception as e:
                messagebox.showerror("Save Error", f"❌ Failed to save config:\n{str(e)}")
    
    def load_config_from_file(self):
        """Load config from file"""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                
                # Update UI with loaded values
                self.apply_loaded_config(config)
                messagebox.showinfo("Config Loaded", f"✅ Configuration loaded from:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Load Error", f"❌ Failed to load config:\n{str(e)}")
    
    def apply_loaded_config(self, config):
        """Apply loaded configuration to UI"""
        try:
            # Model settings
            if 'model' in config:
                model_config = config['model']
                if 'model_path' in model_config:
                    self.model_path_var.set(model_config['model_path'])
                if 'confidence_threshold' in model_config:
                    self.model_vars['confidence_threshold'].set(model_config['confidence_threshold'])
                if 'iou_threshold' in model_config:
                    self.model_vars['iou_threshold'].set(model_config['iou_threshold'])
                if 'detection_confidence' in model_config:
                    self.model_vars['detection_confidence'].set(model_config['detection_confidence'])
            
            # Add other config sections...
            
        except Exception as e:
            messagebox.showerror("Config Error", f"❌ Error applying loaded config:\n{str(e)}")
    
    def get_current_settings(self):
        """Get current settings from UI"""
        # Convert RGB hex colors back to BGR tuples for COLOR_CONFIG
        colors = {}
        for key, var in self.color_vars.items():
            rgb_hex = var.get()
            if rgb_hex.startswith('#') and len(rgb_hex) == 7:
                try:
                    r = int(rgb_hex[1:3], 16)
                    g = int(rgb_hex[3:5], 16)
                    b = int(rgb_hex[5:7], 16)
                    colors[key] = (b, g, r)  # Convert to BGR
                except ValueError:
                    colors[key] = COLOR_CONFIG[key]  # Use default if invalid
            else:
                colors[key] = COLOR_CONFIG[key]
        
        return {
            'model': {
                'model_path': self.model_path_var.get(),
                'confidence_threshold': self.model_vars['confidence_threshold'].get(),
                'iou_threshold': self.model_vars['iou_threshold'].get(),
                'detection_confidence': self.model_vars['detection_confidence'].get()
            },
            'tracking': {
                key: var.get() for key, var in self.tracking_vars.items()
            },
            'line': {
                'line_color': self.line_color_var.get(),
                'line_thickness': self.line_thickness_var.get(),
                'line_style': 'solid',
                'show_label': self.show_label_var.get(),
                'label_text': self.label_text_var.get(),
                'detection_threshold': self.detection_threshold_var.get(),
                'line_type': 'manual'
            },
            'colors': colors,
            'gui': {
                'window_title': self.window_title_var.get(),
                'window_size': self.window_size_var.get(),
                'fps_target': self.fps_target_var.get()
            }
        }
    
    def apply_settings(self):
        """Apply settings and close dialog"""
        self.result = self.get_current_settings()
        messagebox.showinfo("Settings Applied", "✅ Settings have been applied!\nChanges will take effect immediately.")
        self.dialog.destroy()
    
    def cancel_settings(self):
        """Cancel and close dialog"""
        self.result = None
        self.dialog.destroy()