"""
Field Board Reader for detecting troops on the game board.
Uses color template matching for accurate troop detection on the battlefield.
"""

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
import threading
import time
from pathlib import Path
from troop_definitions import TROOP_REGISTRY, get_troop_by_icon_name
import math

class HexagonalBoardState:
    """
    Represents the hexagonal board state with 8 rows of 5 hexagons each.
    Rows are offset every other row. Only bottom 4 rows are playable.
    """
    
    def __init__(self, board_left, board_top, board_width, board_height):
        self.board_left = board_left
        self.board_top = board_top
        self.board_width = board_width
        self.board_height = board_height
        
        # Board configuration
        self.rows = 8
        self.cols = 5
        self.playable_rows = 4  # Bottom 4 rows only
        
        # Store troop positions
        self.hexagon_troops = {}  # {(row, col): [troop_detections]}
        
        # Calculate hexagon positions based on the pink dot pattern
        self.hexagon_centers = self.calculate_hexagon_centers()
    
    def calculate_hexagon_centers(self):
        """Calculate the precise hexagon center positions based on actual game coordinates"""
        centers = {}
        
        print("Using precise hexagon coordinates from game analysis")
        
        # Precise Y coordinates for each row (8 rows total)
        row_y_positions = [538, 594, 650, 706, 763, 819, 875, 932]

        # X starting positions alternate between rows (honeycomb pattern)
        # Odd rows (1, 3, 5, 7) start at 1136
        # Even rows (2, 4, 6, 8) start at 1094
        x_start_odd = 1136   # Rows 0, 2, 4, 6 (0-indexed)
        x_start_even = 1094  # Rows 1, 3, 5, 7 (0-indexed)
        x_spacing = 82       # 82 pixels between hexagons
        
        for row in range(self.rows):
            y = row_y_positions[row]
            
            # Determine starting X position based on row
            if row % 2 == 0:  # Even row index (odd row number)
                x_start = x_start_odd
            else:  # Odd row index (even row number)
                x_start = x_start_even
            
            for col in range(self.cols):
                x = x_start + (col * x_spacing)
                centers[(row, col)] = (x, y)
                
                print(f"  Hex Row {row+1}, Col {col+1} at ({x}, {y})")
        
        return centers
    
    def find_closest_hexagon(self, x, y):
        """Find the closest hexagon to a given screen coordinate"""
        min_distance = float('inf')
        closest_hex = None
        
        # Check ALL hexagons to find the closest
        for (row, col), (hex_x, hex_y) in self.hexagon_centers.items():
            distance = math.sqrt((x - hex_x)**2 + (y - hex_y)**2)
            
            if distance < min_distance:
                min_distance = distance
                closest_hex = (row, col)
        
        # Generous distance check
        max_hex_radius = max(self.board_width / self.cols, self.board_height / self.rows) * 1.5
        
        if min_distance <= max_hex_radius:
            return closest_hex
        
        return None
    
    def add_troop_to_hexagon(self, troop_detection):
        """Add a troop detection to the appropriate hexagon"""
        hex_pos = self.find_closest_hexagon(troop_detection['center_x'], troop_detection['center_y'])
        
        if hex_pos:
            if hex_pos not in self.hexagon_troops:
                self.hexagon_troops[hex_pos] = []
            self.hexagon_troops[hex_pos].append(troop_detection)
            return hex_pos
        return None
    
    def clear_board(self):
        """Clear all troops from the board"""
        self.hexagon_troops.clear()
    
    def get_hexagon_troops(self, row, col):
        """Get all troops in a specific hexagon"""
        return self.hexagon_troops.get((row, col), [])
    
    def get_all_troops(self):
        """Get all troops on the board organized by hexagon"""
        return dict(self.hexagon_troops)
    
    def get_playable_hexagons(self):
        """Get all playable hexagon positions (bottom 4 rows)"""
        playable = []
        for row in range(self.rows - self.playable_rows, self.rows):
            for col in range(self.cols):
                playable.append((row, col))
        return playable
    
    def is_hexagon_occupied(self, row, col):
        """Check if a hexagon has any troops"""
        return (row, col) in self.hexagon_troops and len(self.hexagon_troops[(row, col)]) > 0
    
    def get_board_summary(self):
        """Get a text summary of the board state"""
        summary = []
        summary.append(f"=== HEXAGONAL BOARD STATE ===")
        summary.append(f"Total hexagons: {self.rows}x{self.cols} (playable: {self.playable_rows} bottom rows)")
        summary.append(f"Occupied hexagons: {len(self.hexagon_troops)}")
        
        total_troops = sum(len(troops) for troops in self.hexagon_troops.values())
        summary.append(f"Total troops: {total_troops}")
        summary.append("")
        
        # Show occupied hexagons with human-readable indexing (1-based)
        for (row, col), troops in sorted(self.hexagon_troops.items()):
            hex_name = f"Row {row+1}, Col {col+1}"  # Convert to 1-based indexing
            troop_names = [troop['troop_name'] for troop in troops]
            summary.append(f"{hex_name}: {', '.join(troop_names)}")
        
        return "\n".join(summary)

class FieldBoardReader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Field Board Reader")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.9)
        
        # Initial board area (will be adjustable) - Optimized settings from user testing
        self.board_area = {
            'left_percent': 40,  # 1024/2560 = 40%
            'right_percent': 60, # 1536/2560 = 60%
            'top_percent': 37,   # 532/1440 = 37% (includes both sides of battlefield)
            'bottom_percent': 71 # 1022/1440 = 71% (bottom of your side)
        }
        
        # Detection settings optimized for field troops
        self.preprocessed_templates = {}
        self.scales = np.array([0.8, 0.9, 1.0, 1.1, 1.2])  # Different scales for field detection
        self.threshold = 0.7  # Lower threshold for color matching
        
        self.running = False
        self.overlay_visible = False
        self.capture_thread = None
        self.overlay_canvas = None
        self.screen_width = pyautogui.size().width
        self.screen_height = pyautogui.size().height
        
        self.monitor_width = self.screen_width
        self.monitor_height = self.screen_height
        
        self.current_detections = []
        self.hexagonal_board = None  # Will be initialized when board area is set
        
        self.setup_ui()
        self.preprocess_all_templates()
        self.update_hexagonal_board()  # Initialize the hexagonal board
        
    def preprocess_all_templates(self):
        """Preprocess all field templates at all scales for color matching"""
        print("Preprocessing field templates for color detection...")
        
        icons_dir = Path("field_icons")
        if not icons_dir.exists():
            print("Warning: field_icons directory not found")
            return
        
        icon_files = list(icons_dir.glob("*.png"))
        total_templates = len(icon_files) * len(self.scales)
        
        print(f"Processing {len(icon_files)} field icons at {len(self.scales)} scales = {total_templates} templates")
        
        for icon_file in icon_files:
            icon_name = icon_file.stem
            template_image = cv2.imread(str(icon_file))
            
            if template_image is None:
                continue
            
            # Keep in color (BGR) for color matching
            template_bgr = template_image
            
            # Create scaled versions at all scales
            self.preprocessed_templates[icon_name] = {}
            
            for scale in self.scales:
                # Get original dimensions
                template_height, template_width = template_bgr.shape[:2]
                
                # Calculate new dimensions
                new_width = int(template_width * scale)
                new_height = int(template_height * scale)
                
                # Skip invalid sizes
                if new_width < 10 or new_height < 10:
                    continue
                
                # Create scaled template
                template_scaled = cv2.resize(template_bgr, (new_width, new_height))
                
                # Store preprocessed template (in color)
                self.preprocessed_templates[icon_name][scale] = template_scaled
        
        print(f"✅ Color preprocessing complete! {len(self.preprocessed_templates)} field icons ready for detection")
        
    def setup_ui(self):
        """Setup the user interface"""
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # Start/Stop button
        self.start_button = ttk.Button(control_frame, text="Start Board Reading", command=self.toggle_detection)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Show/Hide overlay button
        self.overlay_button = ttk.Button(control_frame, text="Show Overlay", command=self.toggle_overlay, state=tk.DISABLED)
        self.overlay_button.pack(side=tk.LEFT, padx=5)
        
        # Position window button
        position_button = ttk.Button(control_frame, text="Keep On Top", command=self.toggle_on_top)
        position_button.pack(side=tk.LEFT, padx=5)
        
        # Test board area button
        test_area_button = ttk.Button(control_frame, text="Test Board Area", command=self.test_board_area)
        test_area_button.pack(side=tk.LEFT, padx=5)
        
        # Capture board state button
        capture_button = ttk.Button(control_frame, text="Capture Board State", command=self.capture_board_state)
        capture_button.pack(side=tk.LEFT, padx=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(self.root, text="Detection Settings")
        settings_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Threshold setting
        ttk.Label(settings_frame, text="Threshold:").grid(row=0, column=0, sticky=tk.W)
        self.threshold_var = tk.DoubleVar(value=0.7)
        threshold_scale = ttk.Scale(settings_frame, from_=0.3, to=0.9, variable=self.threshold_var, 
                                  orient=tk.HORIZONTAL, length=200, command=self.update_threshold_label)
        threshold_scale.grid(row=0, column=1, padx=5)
        self.threshold_label = ttk.Label(settings_frame, text="0.7")
        self.threshold_label.grid(row=0, column=2, padx=5)

        # Update rate setting
        ttk.Label(settings_frame, text="Update Rate (sec):").grid(row=1, column=0, sticky=tk.W)
        self.update_rate_var = tk.DoubleVar(value=0.5)
        rate_scale = ttk.Scale(settings_frame, from_=0.1, to=2.0, variable=self.update_rate_var, 
                             orient=tk.HORIZONTAL, length=200, command=self.update_rate_label)
        rate_scale.grid(row=1, column=1, padx=5)
        self.rate_label = ttk.Label(settings_frame, text="0.5")
        self.rate_label.grid(row=1, column=2, padx=5)
        
        # Board Area Settings
        board_area_frame = ttk.LabelFrame(self.root, text="Board Area (% of screen)")
        board_area_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Left boundary
        ttk.Label(board_area_frame, text="Left:").grid(row=0, column=0, sticky=tk.W)
        self.left_var = tk.IntVar(value=self.board_area['left_percent'])
        left_scale = ttk.Scale(board_area_frame, from_=0, to=50, variable=self.left_var, 
                              orient=tk.HORIZONTAL, length=150, command=self.update_board_area)
        left_scale.grid(row=0, column=1, padx=5)
        self.left_label = ttk.Label(board_area_frame, text=f"{self.board_area['left_percent']}%")
        self.left_label.grid(row=0, column=2, padx=5)
        
        # Right boundary
        ttk.Label(board_area_frame, text="Right:").grid(row=0, column=3, sticky=tk.W, padx=(20,0))
        self.right_var = tk.IntVar(value=self.board_area['right_percent'])
        right_scale = ttk.Scale(board_area_frame, from_=50, to=100, variable=self.right_var, 
                               orient=tk.HORIZONTAL, length=150, command=self.update_board_area)
        right_scale.grid(row=0, column=4, padx=5)
        self.right_label = ttk.Label(board_area_frame, text=f"{self.board_area['right_percent']}%")
        self.right_label.grid(row=0, column=5, padx=5)
        
        # Top boundary
        ttk.Label(board_area_frame, text="Top:").grid(row=1, column=0, sticky=tk.W)
        self.top_var = tk.IntVar(value=self.board_area['top_percent'])
        top_scale = ttk.Scale(board_area_frame, from_=10, to=60, variable=self.top_var, 
                             orient=tk.HORIZONTAL, length=150, command=self.update_board_area)
        top_scale.grid(row=1, column=1, padx=5)
        self.top_label = ttk.Label(board_area_frame, text=f"{self.board_area['top_percent']}%")
        self.top_label.grid(row=1, column=2, padx=5)
        
        # Bottom boundary
        ttk.Label(board_area_frame, text="Bottom:").grid(row=1, column=3, sticky=tk.W, padx=(20,0))
        self.bottom_var = tk.IntVar(value=self.board_area['bottom_percent'])
        bottom_scale = ttk.Scale(board_area_frame, from_=60, to=90, variable=self.bottom_var, 
                                orient=tk.HORIZONTAL, length=150, command=self.update_board_area)
        bottom_scale.grid(row=1, column=4, padx=5)
        self.bottom_label = ttk.Label(board_area_frame, text=f"{self.board_area['bottom_percent']}%")
        self.bottom_label.grid(row=1, column=5, padx=5)
        
        # Monitor info display
        monitor_info_frame = ttk.LabelFrame(self.root, text="Monitor & Board Area Information")
        monitor_info_frame.pack(pady=5, padx=10, fill=tk.X)
        
        left, top, right, bottom = self.get_board_area_pixels()
        monitor_info = f"Screen: {self.screen_width}x{self.screen_height}\n"
        monitor_info += f"Board Area: ({left},{top}) to ({right},{bottom})\n"
        monitor_info += f"Board Size: {right-left}x{bottom-top} pixels"
        
        self.monitor_label = ttk.Label(monitor_info_frame, text=monitor_info, justify=tk.LEFT)
        self.monitor_label.pack(pady=5, padx=5)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.root, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Board state display
        board_frame = ttk.LabelFrame(self.root, text="Board State")
        board_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        self.board_text = tk.Text(board_frame, height=12, width=60)
        board_scrollbar = ttk.Scrollbar(board_frame, orient=tk.VERTICAL, command=self.board_text.yview)
        self.board_text.configure(yscrollcommand=board_scrollbar.set)
        
        self.board_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        board_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create overlay window
        self.create_overlay_window()
    
    def update_threshold_label(self, value):
        """Update threshold label when slider changes"""
        self.threshold_label.config(text=f"{float(value):.2f}")
        self.threshold = float(value)
    
    def update_rate_label(self, value):
        """Update rate label when slider changes"""
        self.rate_label.config(text=f"{float(value):.1f}")
    
    def update_board_area(self, value=None):
        """Update board area when sliders change"""
        self.board_area['left_percent'] = self.left_var.get()
        self.board_area['right_percent'] = self.right_var.get()
        self.board_area['top_percent'] = self.top_var.get()
        self.board_area['bottom_percent'] = self.bottom_var.get()
        
        # Update labels
        self.left_label.config(text=f"{self.board_area['left_percent']}%")
        self.right_label.config(text=f"{self.board_area['right_percent']}%")
        self.top_label.config(text=f"{self.board_area['top_percent']}%")
        self.bottom_label.config(text=f"{self.board_area['bottom_percent']}%")
        
        # Update monitor info
        left, top, right, bottom = self.get_board_area_pixels()
        monitor_info = f"Screen: {self.screen_width}x{self.screen_height}\n"
        monitor_info += f"Board Area: ({left},{top}) to ({right},{bottom})\n"
        monitor_info += f"Board Size: {right-left}x{bottom-top} pixels"
        self.monitor_label.config(text=monitor_info)
        
        # If overlay is visible, update the board area display
        if self.overlay_visible and self.overlay_canvas:
            self.draw_board_grid()
        
        # Update hexagonal board dimensions
        self.update_hexagonal_board()
    
    def update_hexagonal_board(self):
        """Update the hexagonal board state with current dimensions"""
        left, top, right, bottom = self.get_board_area_pixels()
        board_width = right - left
        board_height = bottom - top
        
        self.hexagonal_board = HexagonalBoardState(left, top, board_width, board_height)

    def get_board_area_pixels(self):
        """Convert board area percentages to pixel coordinates"""
        left = int(self.monitor_width * self.board_area['left_percent'] / 100)
        right = int(self.monitor_width * self.board_area['right_percent'] / 100)
        top = int(self.monitor_height * self.board_area['top_percent'] / 100)
        bottom = int(self.monitor_height * self.board_area['bottom_percent'] / 100)
        return left, top, right, bottom
        
    def create_overlay_window(self):
        """Create a transparent overlay window for drawing board grid and detections"""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Board Overlay")
        self.overlay_window.attributes('-topmost', True)
        self.overlay_window.attributes('-alpha', 0.7)
        
        # Position for the screen
        monitor_x_offset = 0
        self.overlay_window.geometry(f"{self.monitor_width}x{self.monitor_height}+{monitor_x_offset}+0")
        self.overlay_window.configure(bg='black')
        self.overlay_window.overrideredirect(True)
        
        # Make the window background transparent
        self.overlay_window.wm_attributes('-transparentcolor', 'black')
        
        self.overlay_canvas = tk.Canvas(self.overlay_window, 
                                      width=self.monitor_width, 
                                      height=self.monitor_height,
                                      bg='black', highlightthickness=0)
        self.overlay_canvas.pack()
        
        # Initially hide the overlay
        self.overlay_window.withdraw()
    
    def toggle_overlay(self):
        """Toggle overlay visibility"""
        if not self.overlay_window or not self.overlay_window.winfo_exists():
            return
            
        try:
            if self.overlay_visible:
                self.overlay_window.withdraw()
                self.overlay_visible = False
                self.overlay_button.config(text="Show Overlay")
            else:
                self.overlay_window.deiconify()
                self.overlay_visible = True
                self.overlay_button.config(text="Hide Overlay")
        except tk.TclError:
            self.overlay_visible = False
            self.overlay_button.config(text="Show Overlay")
    
    def toggle_on_top(self):
        """Toggle whether main window stays on top"""
        current = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not current)
    
    def test_board_area(self):
        """Show just the board area for testing"""
        try:
            if not self.overlay_window or not self.overlay_window.winfo_exists():
                self.create_overlay_window()
            
            self.overlay_window.deiconify()
            self.overlay_visible = True
            
            # Clear and draw just the board area
            self.overlay_canvas.delete("all")
            self.draw_board_grid()
            
            # Force canvas update
            self.overlay_canvas.update()
            self.overlay_window.update()
            
            print("Test board area displayed with grid!")
            
            self.root.after(5000, self.hide_test_area)
        except Exception as e:
            print(f"Error showing test area: {e}")
    
    def hide_test_area(self):
        """Hide the test board area"""
        try:
            if not self.running:  # Only hide if not actively reading
                self.overlay_window.withdraw()
                self.overlay_visible = False
        except:
            pass
        
    def toggle_detection(self):
        """Start or stop the board reading process"""
        if not self.running:
            self.start_detection()
        else:
            self.stop_detection()
            
    def start_detection(self):
        """Start the continuous board reading"""
        self.running = True
        self.start_button.config(text="Stop Board Reading")
        self.overlay_button.config(state=tk.NORMAL)
        self.status_var.set("Starting board reading...")
        
        # Show overlay window
        try:
            if self.overlay_window and self.overlay_window.winfo_exists():
                self.overlay_window.deiconify()
                self.overlay_visible = True
                self.overlay_button.config(text="Hide Overlay")
                
                # Draw the board grid
                self.draw_board_grid()
        except tk.TclError:
            # Recreate overlay window if it was destroyed
            self.create_overlay_window()
            self.overlay_window.deiconify()
            self.overlay_visible = True
            self.overlay_button.config(text="Hide Overlay")
            
            # Draw the board grid
            self.draw_board_grid()
        
        # Start detection thread
        self.capture_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.capture_thread.start()
        
    def stop_detection(self):
        """Stop the board reading process"""
        self.running = False
        self.start_button.config(text="Start Board Reading")
        self.overlay_button.config(state=tk.DISABLED)
        self.status_var.set("Stopping...")
        
        # Hide overlay window
        try:
            if self.overlay_window and self.overlay_window.winfo_exists():
                self.overlay_window.withdraw()
                self.overlay_visible = False
                self.overlay_button.config(text="Show Overlay")
                
                # Clear overlay
                if self.overlay_canvas:
                    self.overlay_canvas.delete("all")
        except tk.TclError:
            self.overlay_visible = False
            self.overlay_button.config(text="Show Overlay")
            
        self.status_var.set("Ready")
        
    def detection_loop(self):
        """Main board reading loop running in separate thread"""
        while self.running:
            try:
                start_time = time.time()
                
                # Capture screen
                screenshot = pyautogui.screenshot()
                
                # Convert PIL image to OpenCV format (keep in color)
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Process with board reader
                detections = self.process_board_screenshot(screenshot_cv)
                
                # Update UI in main thread
                self.root.after(0, self.update_overlay, detections)
                
                # Calculate processing time
                process_time = time.time() - start_time
                
                # Update status
                self.root.after(0, lambda: self.status_var.set(
                    f"Reading board... ({process_time:.2f}s) - Found {len(detections)} troops"))
                
                # Wait for next update
                sleep_time = max(0, self.update_rate_var.get() - process_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                time.sleep(1)
                
    def process_board_screenshot(self, screenshot_cv):
        """Process screenshot to find troops on the board and assign to hexagons"""
        detections = []
        
        # Get board area coordinates
        left, top, right, bottom = self.get_board_area_pixels()
        
        # Extract board region (keep in color)
        board_region = screenshot_cv[top:bottom, left:right]
        
        # Get list of field icon files
        icons_dir = Path("field_icons")
        if not icons_dir.exists():
            return detections
            
        icon_files = list(icons_dir.glob("*.png"))
        if not icon_files:
            return detections
        
        # Process each icon type
        for icon_file in icon_files:
            icon_name = icon_file.stem
            
            # Skip if we don't have preprocessed templates for this icon
            if icon_name not in self.preprocessed_templates:
                continue
            
            matches = self.find_field_matches(board_region, icon_name, left, top)
            
            for match in matches:
                detections.append(match)
        
        # Clear previous board state and assign troops to hexagons
        if self.hexagonal_board:
            self.hexagonal_board.clear_board()
            
            for detection in detections:
                hex_pos = self.hexagonal_board.add_troop_to_hexagon(detection)
                if hex_pos:
                    detection['hexagon'] = hex_pos  # Add hexagon info to detection
        else:
            print("❌ Hexagonal board not initialized!")
                    
        return detections
    
    def find_field_matches(self, region_image, icon_name, offset_x, offset_y):
        """Find template matches using color template matching"""
        all_matches = []
        
        # Check if we have preprocessed templates for this icon
        if icon_name not in self.preprocessed_templates:
            return all_matches
        
        # Use preprocessed color templates
        for scale in self.scales:
            # Get preprocessed template for this scale
            if scale not in self.preprocessed_templates[icon_name]:
                continue
                
            template_scaled = self.preprocessed_templates[icon_name][scale]
            template_height, template_width = template_scaled.shape[:2]
            
            # Skip if template becomes too large for region
            if template_width > region_image.shape[1] * 0.9 or template_height > region_image.shape[0] * 0.9:
                continue
            
            # Perform color template matching
            result = cv2.matchTemplate(region_image, template_scaled, cv2.TM_CCOEFF_NORMED)
            
            # Find matches above threshold
            locations = np.where(result >= self.threshold)
            
            for pt in zip(*locations[::-1]):  # Switch x and y coordinates
                x, y = pt
                confidence = result[y, x]
                
                # Calculate actual screen coordinates
                actual_x = int(x + offset_x)
                actual_y = int(y + offset_y)
                
                match_info = {
                    'icon_name': icon_name,
                    'troop_name': icon_name.replace('field_', ''),  # Remove field_ prefix
                    'x': actual_x,
                    'y': actual_y,
                    'width': int(template_width),
                    'height': int(template_height),
                    'center_x': int(actual_x + template_width // 2),
                    'center_y': int(actual_y + template_height // 2),
                    'confidence': float(confidence),
                    'scale': float(scale)
                }
                all_matches.append(match_info)
        
        # Remove overlapping matches (keep highest confidence)
        filtered_matches = self.remove_overlapping_detections(all_matches)
        
        return filtered_matches
    
    def remove_overlapping_detections(self, detections, overlap_threshold=0.5):
        """Remove overlapping detections, keeping the one with highest confidence"""
        if not detections:
            return []
        
        # Sort by confidence (highest first)
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        
        for detection in detections:
            overlap_found = False
            
            for existing in filtered:
                # Calculate overlap
                x1 = max(detection['x'], existing['x'])
                y1 = max(detection['y'], existing['y'])
                x2 = min(detection['x'] + detection['width'], existing['x'] + existing['width'])
                y2 = min(detection['y'] + detection['height'], existing['y'] + existing['height'])
                
                if x1 < x2 and y1 < y2:
                    # Calculate overlap area
                    overlap_area = (x2 - x1) * (y2 - y1)
                    detection_area = detection['width'] * detection['height']
                    
                    overlap_ratio = overlap_area / detection_area
                    
                    if overlap_ratio > overlap_threshold:
                        overlap_found = True
                        break
            
            if not overlap_found:
                filtered.append(detection)
        
        return filtered
    
    def capture_board_state(self):
        """Capture a single board state snapshot"""
        try:
            # Capture screen
            screenshot = pyautogui.screenshot()
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Process board
            detections = self.process_board_screenshot(screenshot_cv)
            
            # Update display with hexagonal board state
            self.update_board_state_display(detections)
            
            self.status_var.set(f"Board state captured! Found {len(detections)} troops in hexagons")
            
        except Exception as e:
            self.status_var.set(f"Error capturing board state: {e}")
        
    def update_overlay(self, detections):
        """Update the overlay with current detections"""
        if not self.overlay_canvas or not self.overlay_window:
            return
            
        try:
            if not self.overlay_window.winfo_exists():
                return
        except tk.TclError:
            return
            
        # Clear previous overlays
        try:
            self.overlay_canvas.delete("all")
        except tk.TclError:
            return
        
        # Draw board grid
        self.draw_board_grid()
        
        # Draw detections
        for i, detection in enumerate(detections):
            try:
                colors = ['#00FF00', '#FF0000', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#FF69B4']
                color = colors[i % len(colors)]
                
                x, y = detection['x'], detection['y']
                w, h = detection['width'], detection['height']
                
                # Draw detection rectangle
                self.overlay_canvas.create_rectangle(x, y, x + w, y + h,
                                                   outline=color, width=2, fill='', tags="detection")
                
                # Get troop information
                troop = get_troop_by_icon_name(detection['troop_name'])
                
                if troop:
                    stars = "⭐" * troop.stars.value
                    label = f"{troop.name}\n{troop.cost}💧 {stars}\n{detection['confidence']:.2f}"
                else:
                    label = f"{detection['troop_name']}\n{detection['confidence']:.2f}"
                
                # Draw label with background
                text_x = x + w//2
                text_y = y - 5
                
                # Black outline for text visibility
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            self.overlay_canvas.create_text(text_x + dx, text_y + dy, 
                                                          text=label, fill='black', font=('Arial', 8, 'bold'),
                                                          anchor='s', tags="detection")
                
                # White text on top
                self.overlay_canvas.create_text(text_x, text_y, 
                                              text=label, fill='white', font=('Arial', 8, 'bold'),
                                              anchor='s', tags="detection")
                                              
            except tk.TclError:
                break
                
        # Update board state display
        self.update_board_state_display(detections)
    
    def draw_board_grid(self):
        """Draw the board area only (no grid since board is not traditional grid)"""
        try:
            left, top, right, bottom = self.get_board_area_pixels()
            
            # Draw main board rectangle only
            self.overlay_canvas.create_rectangle(
                left, top, right, bottom,
                outline='lime', width=3, tags="board_area", fill=''
            )
            
            self.overlay_canvas.update_idletasks()
            
        except (tk.TclError, AttributeError):
            pass
    
    def update_board_state_display(self, detections):
        """Update the board state text display with hexagonal organization"""
        try:
            self.board_text.delete(1.0, tk.END)
            
            if not detections:
                self.board_text.insert(tk.END, "No troops detected on board\n")
                return
            
            if not self.hexagonal_board:
                self.board_text.insert(tk.END, "Hexagonal board not initialized\n")
                return
            
            # Display hexagonal board state
            board_summary = self.hexagonal_board.get_board_summary()
            self.board_text.insert(tk.END, board_summary)
            self.board_text.insert(tk.END, "\n\n")
            
            # Display detailed troop information
            self.board_text.insert(tk.END, "=== DETAILED TROOP INFORMATION ===\n")
            
            for detection in detections:
                troop_info = get_troop_by_icon_name(detection['troop_name'])
                hex_info = ""
                
                if 'hexagon' in detection:
                    row, col = detection['hexagon']
                    hex_info = f" [Row {row+1}, Col {col+1}]"  # Convert to 1-based indexing
                
                if troop_info:
                    stars = "⭐" * troop_info.stars.value
                    traits = ", ".join([trait.name for trait in troop_info.traits[:2]])
                    text = f"{troop_info.name} {stars} ({troop_info.cost}💧){hex_info}\n"
                    text += f"  Traits: {traits}\n"
                    text += f"  Confidence: {detection['confidence']:.3f}\n"
                    text += f"  Position: ({detection['center_x']}, {detection['center_y']})\n\n"
                else:
                    text = f"{detection['troop_name']}{hex_info}\n"
                    text += f"  Confidence: {detection['confidence']:.3f}\n"
                    text += f"  Position: ({detection['center_x']}, {detection['center_y']})\n\n"
                
                self.board_text.insert(tk.END, text)
                
        except tk.TclError:
            pass
            
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle window closing"""
        print("Shutting down field board reader...")
        self.stop_detection()
        
        # Wait a moment for threads to finish
        time.sleep(0.1)
        
        # Destroy overlay window safely
        try:
            if self.overlay_window and self.overlay_window.winfo_exists():
                self.overlay_window.destroy()
        except tk.TclError:
            pass
        
        # Destroy main window
        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass

def main():
    """Main function"""
    print("Starting Field Board Reader...")
    print("Make sure you have the field_icons folder in the same directory!")
    
    try:
        app = FieldBoardReader()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
