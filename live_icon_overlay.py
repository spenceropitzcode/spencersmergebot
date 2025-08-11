"""
Live Icon Overlay for real-time game icon detection.
"""

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
import threading
import time
from game_icon_detector import GameIconDetector
from pathlib import Path
from troop_definitions import TROOP_REGISTRY, get_troop_by_icon_name

class LiveIconOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Icon Detector Overlay")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.8)
        
        self.scan_area = {
            'left_percent': 39,
            'right_percent': 57,
            'top_percent': 85,
            'bottom_percent': 100
        }
        
        # Preprocessed template cache for speed optimization
        self.preprocessed_templates = {}
        self.scales = np.array([0.22, 0.24, 0.26, 0.28, 0.30])
        
        self.detector = GameIconDetector(
            threshold=0.8,
            search_bottom_fraction=0.4,
            ignore_top_right_fraction=0,
            use_preprocessing=True
        )
        
        self.running = False
        self.overlay_visible = False
        self.capture_thread = None
        self.overlay_canvas = None
        self.screen_width = pyautogui.size().width
        self.screen_height = pyautogui.size().height
        
        self.monitor_width = self.screen_width
        self.monitor_height = self.screen_height
        
        self.current_detections = []
        
        self.setup_ui()
        self.preprocess_all_templates()
        
    def preprocess_all_templates(self):
        """Preprocess all templates at all scales for maximum speed"""
        print("Preprocessing templates for optimal performance...")
        
        icons_dir = Path("market_icons")
        if not icons_dir.exists():
            print("Warning: market_icons directory not found")
            return
        
        icon_files = list(icons_dir.glob("*.png"))
        total_templates = len(icon_files) * len(self.scales)
        
        print(f"Processing {len(icon_files)} icons at {len(self.scales)} scales = {total_templates} templates")
        
        for icon_file in icon_files:
            icon_name = icon_file.stem
            template_image = cv2.imread(str(icon_file))
            
            if template_image is None:
                continue
                
            # Convert to grayscale once
            template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing once
            if self.detector.use_preprocessing:
                template_gray = cv2.equalizeHist(template_gray)
            
            # Create scaled versions at all scales
            self.preprocessed_templates[icon_name] = {}
            
            for scale in self.scales:
                # Get original dimensions
                template_height, template_width = template_gray.shape
                
                # Calculate new dimensions
                new_width = int(template_width * scale)
                new_height = int(template_height * scale)
                
                # Skip invalid sizes
                if new_width < 5 or new_height < 5:
                    continue
                
                # Create scaled template
                template_scaled = cv2.resize(template_gray, (new_width, new_height))
                
                # Store preprocessed template
                self.preprocessed_templates[icon_name][scale] = template_scaled
        
        print(f"✅ Preprocessing complete! {len(self.preprocessed_templates)} icons ready for high-speed detection")
        
    def setup_ui(self):
        """Setup the user interface"""
        # Control frame
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)
        
        # Start/Stop button
        self.start_button = ttk.Button(control_frame, text="Start Detection", command=self.toggle_detection)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Show/Hide overlay button
        self.overlay_button = ttk.Button(control_frame, text="Show Overlay", command=self.toggle_overlay, state=tk.DISABLED)
        self.overlay_button.pack(side=tk.LEFT, padx=5)
        
        # Position window button
        position_button = ttk.Button(control_frame, text="Keep On Top", command=self.toggle_on_top)
        position_button.pack(side=tk.LEFT, padx=5)
        
        # Test detection zone button
        test_zone_button = ttk.Button(control_frame, text="Test Zone", command=self.test_detection_zone)
        test_zone_button.pack(side=tk.LEFT, padx=5)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(self.root, text="Detection Settings")
        settings_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Threshold setting - updated default to work with detected scale
        ttk.Label(settings_frame, text="Threshold:").grid(row=0, column=0, sticky=tk.W)
        self.threshold_var = tk.DoubleVar(value=0.8)  # Updated to 0.8 as requested
        threshold_scale = ttk.Scale(settings_frame, from_=0.2, to=1.0, variable=self.threshold_var, 
                                  orient=tk.HORIZONTAL, length=200, command=self.update_threshold_label)
        threshold_scale.grid(row=0, column=1, padx=5)
        self.threshold_label = ttk.Label(settings_frame, text="0.8")
        self.threshold_label.grid(row=0, column=2, padx=5)

        # Update rate setting
        ttk.Label(settings_frame, text="Update Rate (sec):").grid(row=1, column=0, sticky=tk.W)
        self.update_rate_var = tk.DoubleVar(value=0.1)
        rate_scale = ttk.Scale(settings_frame, from_=0.05, to=1.0, variable=self.update_rate_var, 
                             orient=tk.HORIZONTAL, length=200, command=self.update_rate_label)
        rate_scale.grid(row=1, column=1, padx=5)
        self.rate_label = ttk.Label(settings_frame, text="0.1")
        self.rate_label.grid(row=1, column=2, padx=5)
        
        # Scan Area Settings
        scan_area_frame = ttk.LabelFrame(self.root, text="Scan Area (% of screen)")
        scan_area_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Left boundary
        ttk.Label(scan_area_frame, text="Left:").grid(row=0, column=0, sticky=tk.W)
        self.left_var = tk.IntVar(value=self.scan_area['left_percent'])
        left_scale = ttk.Scale(scan_area_frame, from_=0, to=50, variable=self.left_var, 
                              orient=tk.HORIZONTAL, length=150, command=self.update_scan_area)
        left_scale.grid(row=0, column=1, padx=5)
        self.left_label = ttk.Label(scan_area_frame, text=f"{self.scan_area['left_percent']}%")
        self.left_label.grid(row=0, column=2, padx=5)
        
        # Right boundary
        ttk.Label(scan_area_frame, text="Right:").grid(row=0, column=3, sticky=tk.W, padx=(20,0))
        self.right_var = tk.IntVar(value=self.scan_area['right_percent'])
        right_scale = ttk.Scale(scan_area_frame, from_=50, to=100, variable=self.right_var, 
                               orient=tk.HORIZONTAL, length=150, command=self.update_scan_area)
        right_scale.grid(row=0, column=4, padx=5)
        self.right_label = ttk.Label(scan_area_frame, text=f"{self.scan_area['right_percent']}%")
        self.right_label.grid(row=0, column=5, padx=5)
        
        # Top boundary
        ttk.Label(scan_area_frame, text="Top:").grid(row=1, column=0, sticky=tk.W)
        self.top_var = tk.IntVar(value=self.scan_area['top_percent'])
        top_scale = ttk.Scale(scan_area_frame, from_=50, to=95, variable=self.top_var, 
                             orient=tk.HORIZONTAL, length=150, command=self.update_scan_area)
        top_scale.grid(row=1, column=1, padx=5)
        self.top_label = ttk.Label(scan_area_frame, text=f"{self.scan_area['top_percent']}%")
        self.top_label.grid(row=1, column=2, padx=5)
        
        # Bottom boundary
        ttk.Label(scan_area_frame, text="Bottom:").grid(row=1, column=3, sticky=tk.W, padx=(20,0))
        self.bottom_var = tk.IntVar(value=self.scan_area['bottom_percent'])
        bottom_scale = ttk.Scale(scan_area_frame, from_=80, to=100, variable=self.bottom_var, 
                                orient=tk.HORIZONTAL, length=150, command=self.update_scan_area)
        bottom_scale.grid(row=1, column=4, padx=5)
        self.bottom_label = ttk.Label(scan_area_frame, text=f"{self.scan_area['bottom_percent']}%")
        self.bottom_label.grid(row=1, column=5, padx=5)
        
        # Monitor info display
        monitor_info_frame = ttk.LabelFrame(self.root, text="Monitor & Scan Area Information")
        monitor_info_frame.pack(pady=5, padx=10, fill=tk.X)
        
        left, top, right, bottom = self.get_scan_area_pixels()
        monitor_info = f"Screen: {self.screen_width}x{self.screen_height}\n"
        monitor_info += f"Scan Area: ({left},{top}) to ({right},{bottom})\n"
        monitor_info += f"Scan Size: {right-left}x{bottom-top} pixels"
        
        self.monitor_label = ttk.Label(monitor_info_frame, text=monitor_info, justify=tk.LEFT)
        self.monitor_label.pack(pady=5, padx=5)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.root, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Detection display
        self.detection_text = tk.Text(self.root, height=8, width=50)
        self.detection_text.pack(pady=5, padx=10)
        
        # Create overlay window
        self.create_overlay_window()
    
    def update_threshold_label(self, value):
        """Update threshold label when slider changes"""
        self.threshold_label.config(text=f"{float(value):.2f}")
    
    def update_rate_label(self, value):
        """Update rate label when slider changes"""
        self.rate_label.config(text=f"{float(value):.1f}")
    
    def update_scan_area(self, value=None):
        """Update scan area when sliders change"""
        self.scan_area['left_percent'] = self.left_var.get()
        self.scan_area['right_percent'] = self.right_var.get()
        self.scan_area['top_percent'] = self.top_var.get()
        self.scan_area['bottom_percent'] = self.bottom_var.get()
        
        # Update labels
        self.left_label.config(text=f"{self.scan_area['left_percent']}%")
        self.right_label.config(text=f"{self.scan_area['right_percent']}%")
        self.top_label.config(text=f"{self.scan_area['top_percent']}%")
        self.bottom_label.config(text=f"{self.scan_area['bottom_percent']}%")
        
        # If overlay is visible, update the detection zone
        if self.overlay_visible and self.overlay_canvas:
            self.draw_detection_zone()

    def get_scan_area_pixels(self):
        """Convert scan area percentages to pixel coordinates"""
        left = int(self.monitor_width * self.scan_area['left_percent'] / 100)
        right = int(self.monitor_width * self.scan_area['right_percent'] / 100)
        top = int(self.monitor_height * self.scan_area['top_percent'] / 100)
        bottom = int(self.monitor_height * self.scan_area['bottom_percent'] / 100)
        return left, top, right, bottom
        
    def create_overlay_window(self):
        """Create a transparent overlay window for drawing detections"""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Detection Overlay")
        self.overlay_window.attributes('-topmost', True)
        self.overlay_window.attributes('-alpha', 0.8)  # Made less transparent for better visibility
        
        # Position for the actual screen (no multi-monitor offset needed)
        monitor_x_offset = 0  # Start at the beginning of the screen
        self.overlay_window.geometry(f"{self.monitor_width}x{self.monitor_height}+{monitor_x_offset}+0")
        self.overlay_window.configure(bg='black')  # Will be made transparent
        self.overlay_window.overrideredirect(True)  # Remove window decorations
        
        # Make the window background transparent
        self.overlay_window.wm_attributes('-transparentcolor', 'black')
        
        print(f"Overlay positioned for main screen: {self.monitor_width}x{self.monitor_height}+{monitor_x_offset}+0")
        
        # Make the window click-through if possible (Windows specific)
        # Temporarily commented out to ensure visibility
        """
        try:
            import win32gui
            import win32con
            hwnd = self.overlay_window.winfo_id()
            extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                                 extended_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
        except ImportError:
            pass
        except Exception as e:
            pass
        """
        
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
            # Window already destroyed
            self.overlay_visible = False
            self.overlay_button.config(text="Show Overlay")
    
    def toggle_on_top(self):
        """Toggle whether main window stays on top"""
        current = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not current)
    
    def test_detection_zone(self):
        """Show just the detection zone for testing"""
        try:
            if not self.overlay_window or not self.overlay_window.winfo_exists():
                self.create_overlay_window()
            
            self.overlay_window.deiconify()
            self.overlay_visible = True
            
            # Clear and draw just the detection zone with maximum visibility
            self.overlay_canvas.delete("all")
            self.draw_detection_zone()
            
            # Force canvas update
            self.overlay_canvas.update()
            self.overlay_window.update()
            
            print("Test detection zone displayed - should be VERY visible with bright colors!")
            
            self.root.after(5000, self.hide_test_zone)
        except Exception as e:
            pass
    
    def hide_test_zone(self):
        """Hide the test detection zone"""
        try:
            if not self.running:  # Only hide if not actively detecting
                self.overlay_window.withdraw()
                self.overlay_visible = False
        except:
            pass
        
    def toggle_detection(self):
        """Start or stop the detection process"""
        if not self.running:
            self.start_detection()
        else:
            self.stop_detection()
            
    def start_detection(self):
        """Start the continuous detection"""
        self.running = True
        self.start_button.config(text="Stop Detection")
        self.overlay_button.config(state=tk.NORMAL)
        self.status_var.set("Starting detection...")
        
        # Show overlay window
        try:
            if self.overlay_window and self.overlay_window.winfo_exists():
                self.overlay_window.deiconify()
                self.overlay_visible = True
                self.overlay_button.config(text="Hide Overlay")
                
                # Always draw the detection zone immediately
                self.draw_detection_zone()
        except tk.TclError:
            # Recreate overlay window if it was destroyed
            self.create_overlay_window()
            self.overlay_window.deiconify()
            self.overlay_visible = True
            self.overlay_button.config(text="Hide Overlay")
            
            # Draw the detection zone
            self.draw_detection_zone()
        
        # Start detection thread
        self.capture_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.capture_thread.start()
        
    def stop_detection(self):
        """Stop the detection process"""
        self.running = False
        self.start_button.config(text="Start Detection")
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
            # Window already destroyed
            self.overlay_visible = False
            self.overlay_button.config(text="Show Overlay")
            
        self.status_var.set("Ready")
        
    def detection_loop(self):
        """Main detection loop running in separate thread"""
        while self.running:
            try:
                start_time = time.time()
                
                # Update detector settings
                self.detector.threshold = self.threshold_var.get()
                
                # Capture screen
                screenshot = pyautogui.screenshot()
                
                # Convert PIL image to OpenCV format
                screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Process with detector
                detections = self.process_screenshot(screenshot_cv)
                
                # Update UI in main thread
                self.root.after(0, self.update_overlay, detections)
                
                # Calculate processing time
                process_time = time.time() - start_time
                
                # Update status
                self.root.after(0, lambda: self.status_var.set(
                    f"Detecting... ({process_time:.2f}s) - Found {len(detections)} icons"))
                
                # Wait for next update
                sleep_time = max(0, self.update_rate_var.get() - process_time)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                time.sleep(1)
                
    def process_screenshot(self, screenshot_cv):
        """Process screenshot with the icon detector using custom scan area"""
        detections = []
        
        # Get custom scan area coordinates
        left, top, right, bottom = self.get_scan_area_pixels()
        
        scan_region = screenshot_cv[top:bottom, left:right]
        
        icon_files = list(self.detector.icons_dir.glob("*.png"))
        if not icon_files:
            return detections
            
        icon_files = self.detector.prioritize_icon_search(icon_files)
        
        for icon_file in icon_files:
            if len(detections) >= 3:
                break
                
            icon_name = icon_file.stem
            
            # Skip if we don't have preprocessed templates for this icon
            if icon_name not in self.preprocessed_templates:
                continue
            
            matches, best_confidence = self.find_matches_optimized(scan_region, icon_name, left, top)
            
            if matches:
                for match in matches:
                    adjusted_match = {
                        'icon_name': icon_name,
                        'x': match['x'],
                        'y': match['y'],
                        'width': match['width'],
                        'height': match['height'],
                        'center_x': match['center_x'],
                        'center_y': match['center_y'],
                        'confidence': match['confidence']
                    }
                    detections.append(adjusted_match)
                    
        return detections
    
    def find_matches_optimized(self, region_image, icon_name, offset_x, offset_y):
        """Find template matches using preprocessed templates for maximum speed"""
        # Convert region to grayscale once
        region_gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
        
        # Apply preprocessing to region
        if self.detector.use_preprocessing:
            region_gray = cv2.equalizeHist(region_gray)
        
        # Check if we have preprocessed templates for this icon
        if icon_name not in self.preprocessed_templates:
            return []
        
        all_matches = []
        best_confidence = 0
        
        pad_size = 5
        region_padded = cv2.copyMakeBorder(region_gray, pad_size, pad_size, pad_size, pad_size, 
                                         cv2.BORDER_REFLECT)
        
        # Use preprocessed templates for maximum speed
        for scale in self.scales:
            # Get preprocessed template for this scale
            if scale not in self.preprocessed_templates[icon_name]:
                continue
                
            template_scaled = self.preprocessed_templates[icon_name][scale]
            template_height, template_width = template_scaled.shape
            
            # Skip if template becomes too large for region
            if template_width > region_image.shape[1] * 0.8 or template_height > region_image.shape[0] * 0.8:
                continue
            
            # Perform template matching on padded region (no resizing needed!)
            result = cv2.matchTemplate(region_padded, template_scaled, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match for this scale
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_confidence:
                best_confidence = max_val
            
            # Use a slightly lower threshold for initial detection, then filter by quality
            detection_threshold = max(0.25, self.detector.threshold - 0.15)
            
            # Find all matches above threshold for this scale
            if max_val >= detection_threshold:
                locations = np.where(result >= detection_threshold)
                
                for pt in zip(*locations[::-1]):  # Switch x and y coordinates
                    x, y = pt
                    confidence = result[y, x]
                    
                    # Only accept matches that meet the original threshold
                    if confidence < self.detector.threshold:
                        continue
                    
                    # Adjust coordinates to account for padding and scan region offset
                    actual_x = int(x - pad_size + offset_x)
                    actual_y = int(y - pad_size + offset_y)
                    
                    # Skip matches too close to edges (likely edge artifacts)
                    if (x < pad_size + 5 or y < pad_size + 5 or 
                        x > result.shape[1] - 5 or y > result.shape[0] - 5):
                        continue
                    
                    match_info = {
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
        
        # Remove overlapping matches
        filtered_matches = self.detector._remove_overlapping_matches(all_matches)
        
        # Return only the best match for this icon
        if filtered_matches:
            best_match = max(filtered_matches, key=lambda x: x['confidence'])
            return [best_match], best_confidence
        
        return filtered_matches, best_confidence
        
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
        
        # Draw detection zone rectangle
        self.draw_detection_zone()
        
        # Get scan area coordinates to position icons above it
        left, top, right, bottom = self.get_scan_area_pixels()
        
        for i, detection in enumerate(detections):
            try:
                colors = ['#00FF00', '#FF0000', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF']
                color = colors[i % len(colors)]
                
                x, y = detection['x'], detection['y']
                w, h = detection['width'], detection['height']
                cx, cy = detection['center_x'], detection['center_y']
                
                display_x = left + (i * 100)
                display_y = top - 80
                
                if display_y < 10:
                    display_y = 10
                
                icon_size = 40
                self.overlay_canvas.create_rectangle(display_x, display_y, 
                                                   display_x + icon_size, display_y + icon_size,
                                                   outline=color, width=3, fill=color, stipple='gray25')
                
                # Get troop information
                troop = get_troop_by_icon_name(detection['icon_name'])
                
                if troop:
                    # Enhanced label with troop stats
                    stars = "⭐" * troop.stars.value
                    label = f"{troop.name}\n{troop.cost}💧 {stars}\n{detection['confidence']:.2f}"
                    
                    # Show key traits (convert enum to names)
                    key_traits = troop.traits[:2]  # Show first 2 traits
                    if key_traits:
                        traits_text = ", ".join([trait.name for trait in key_traits])
                        label += f"\n{traits_text}"
                else:
                    # Fallback to basic info
                    label = f"{detection['icon_name']}\n{detection['confidence']:.2f}"
                
                # Draw text with outline for better visibility
                text_x = display_x + icon_size//2
                text_y = display_y + icon_size + 5
                
                # Black outline
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            self.overlay_canvas.create_text(text_x + dx, text_y + dy, 
                                                          text=label, fill='black', font=('Arial', 8, 'bold'),
                                                          anchor='n')
                
                # White text on top
                self.overlay_canvas.create_text(text_x, text_y, 
                                              text=label, fill='white', font=('Arial', 8, 'bold'),
                                              anchor='n')
                                              
            except tk.TclError:
                break
                
        self.update_detection_text(detections)
    
    def draw_detection_zone(self):
        try:
            left, top, right, bottom = self.get_scan_area_pixels()
            
            self.overlay_canvas.delete("detection_zone")
            
            self.overlay_canvas.create_rectangle(
                left, top, right, bottom,
                outline='lime', width=3, tags="detection_zone", fill=''
            )
            
            self.overlay_canvas.update_idletasks()
            
        except (tk.TclError, AttributeError) as e:
            pass
        
    def update_detection_text(self, detections):
        """Update the detection text display"""
        try:
            self.detection_text.delete(1.0, tk.END)
            
            if not detections:
                self.detection_text.insert(tk.END, "No icons detected")
                return
                
            for detection in detections:
                text = f"{detection['icon_name']}: {detection['confidence']:.3f} "
                text += f"at ({detection['center_x']}, {detection['center_y']})\n"
                self.detection_text.insert(tk.END, text)
        except tk.TclError:
            # Widget destroyed, ignore
            pass
            
    def run(self):
        """Start the application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle window closing"""
        print("Shutting down overlay...")
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
    print("Starting Live Icon Overlay...")
    print("Make sure you have the market_icons folder in the same directory!")
    
    try:
        app = LiveIconOverlay()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
