"""
Live Icon Overlay using PyAutoGUI and GameIconDetector

This program continuously captures the screen and displays an overlay
showing detected game icons in real-time.

Author: AI Assistant
Date: August 2025
"""

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk
import threading
import time
from game_icon_detector import GameIconDetector

class LiveIconOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Live Icon Detector Overlay")
        self.root.attributes('-topmost', True)  # Keep window on top
        self.root.attributes('-alpha', 0.8)  # Semi-transparent
        
        # Initialize the game icon detector
        self.detector = GameIconDetector(
            threshold=0.65,
            search_bottom_fraction=0.4,  # Search larger area for live detection
            ignore_top_right_fraction=0,
            use_preprocessing=True
        )
        
        # Control variables
        self.running = False
        self.overlay_visible = False
        self.capture_thread = None
        self.overlay_canvas = None
        # Get screen information for multi-monitor setups
        self.screen_width = pyautogui.size().width
        self.screen_height = pyautogui.size().height
        
        # Print screen info for debugging
        print(f"Detected screen size: {self.screen_width}x{self.screen_height}")
        
        # For multi-monitor setups, use the same dimensions
        self.monitor_width = self.screen_width
        self.monitor_height = self.screen_height
        print(f"Monitor size: {self.monitor_width}x{self.monitor_height}")
        
        # Detection results
        self.current_detections = []
        
        self.setup_ui()
        
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
        settings_frame = ttk.LabelFrame(self.root, text="Settings")
        settings_frame.pack(pady=5, padx=10, fill=tk.X)
        
        # Threshold setting
        ttk.Label(settings_frame, text="Threshold:").grid(row=0, column=0, sticky=tk.W)
        self.threshold_var = tk.DoubleVar(value=0.65)
        threshold_scale = ttk.Scale(settings_frame, from_=0.3, to=0.9, variable=self.threshold_var, 
                                  orient=tk.HORIZONTAL, length=200, command=self.update_threshold_label)
        threshold_scale.grid(row=0, column=1, padx=5)
        self.threshold_label = ttk.Label(settings_frame, text="0.65")
        self.threshold_label.grid(row=0, column=2, padx=5)

        # Update rate setting
        ttk.Label(settings_frame, text="Update Rate (sec):").grid(row=1, column=0, sticky=tk.W)
        self.update_rate_var = tk.DoubleVar(value=1.0)
        rate_scale = ttk.Scale(settings_frame, from_=0.5, to=3.0, variable=self.update_rate_var, 
                             orient=tk.HORIZONTAL, length=200, command=self.update_rate_label)
        rate_scale.grid(row=1, column=1, padx=5)
        self.rate_label = ttk.Label(settings_frame, text="1.0")
        self.rate_label.grid(row=1, column=2, padx=5)
        
        # Monitor info display
        monitor_info_frame = ttk.LabelFrame(self.root, text="Monitor Information")
        monitor_info_frame.pack(pady=5, padx=10, fill=tk.X)
        
        monitor_info = f"PyAutoGUI Screen: {self.screen_width}x{self.screen_height}\n"
        monitor_info += f"Tkinter Screen: {self.monitor_width}x{self.monitor_height}\n"
        monitor_info += f"Detection Zone Height: {int(self.monitor_height * 0.4)} pixels"
        
        monitor_label = ttk.Label(monitor_info_frame, text=monitor_info, justify=tk.LEFT)
        monitor_label.pack(pady=5, padx=5)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.root, textvariable=self.status_var)
        status_label.pack(pady=5)
        
        # Detection display
        self.detection_text = tk.Text(self.root, height=8, width=50)
        self.detection_text.pack(pady=5, padx=10)
        
        # Usage instructions
        instructions_frame = ttk.LabelFrame(self.root, text="How to Use")
        instructions_frame.pack(pady=5, padx=10, fill=tk.X)
        
        instructions = """1. Position this window where you can see it
2. Open your game in another window
3. Click 'Start Detection' 
4. The overlay will appear over your ENTIRE screen
5. Play your game - detected icons will show colored boxes
6. Adjust threshold if detection is too sensitive/not sensitive enough
7. Click 'Stop Detection' to remove overlay"""
        
        instructions_label = ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT)
        instructions_label.pack(pady=5, padx=5)
        
        # Create overlay window
        self.create_overlay_window()
    
    def update_threshold_label(self, value):
        """Update threshold label when slider changes"""
        self.threshold_label.config(text=f"{float(value):.2f}")
    
    def update_rate_label(self, value):
        """Update rate label when slider changes"""
        self.rate_label.config(text=f"{float(value):.1f}")
        
    def create_overlay_window(self):
        """Create a transparent overlay window for drawing detections"""
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Detection Overlay")
        self.overlay_window.attributes('-topmost', True)
        self.overlay_window.attributes('-alpha', 0.7)
        
        # Position for center monitor in 3-monitor setup (main monitor starts at x=1920)
        monitor_x_offset = 1920  # Your main monitor starts after the left monitor
        self.overlay_window.geometry(f"{self.monitor_width}x{self.monitor_height}+{monitor_x_offset}+0")
        self.overlay_window.configure(bg='black')
        self.overlay_window.overrideredirect(True)  # Remove window decorations
        
        print(f"Overlay positioned for center monitor: {self.monitor_width}x{self.monitor_height}+{monitor_x_offset}+0")
        
        # Make the window click-through if possible (Windows specific)
        try:
            import win32gui
            import win32con
            hwnd = self.overlay_window.winfo_id()
            extended_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, 
                                 extended_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)
            print("Click-through overlay enabled")
        except ImportError:
            print("Note: Install pywin32 for click-through overlay functionality")
        except Exception as e:
            print(f"Could not enable click-through: {e}")
        
        # Canvas for drawing overlays
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
            
            # Hide after 5 seconds
            self.root.after(5000, self.hide_test_zone)
            
        except Exception as e:
            print(f"Error testing detection zone: {e}")
    
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
                print(f"Detection error: {e}")
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                time.sleep(1)
                
    def process_screenshot(self, screenshot_cv):
        """Process screenshot with the icon detector"""
        detections = []
        
        # Get all icon templates
        icon_files = list(self.detector.icons_dir.glob("*.png"))
        if not icon_files:
            return detections
            
        icon_files = self.detector.prioritize_icon_search(icon_files)
        
        # Process each icon type
        for icon_file in icon_files:
            if len(detections) >= 3:  # Max 3 icons
                break
                
            icon_name = icon_file.stem
            template_image = cv2.imread(str(icon_file))
            if template_image is None:
                continue
                
            matches, best_confidence = self.detector.find_matches_multiscale(screenshot_cv, template_image)
            
            if matches:
                for match in matches:
                    detections.append({
                        'icon_name': icon_name,
                        'x': match['x'],
                        'y': match['y'],
                        'width': match['width'],
                        'height': match['height'],
                        'center_x': match['center_x'],
                        'center_y': match['center_y'],
                        'confidence': match['confidence']
                    })
                    
        return detections
        
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
        
        # Colors for different icons
        colors = ['#00FF00', '#FF0000', '#0000FF', '#FFFF00', '#FF00FF']
        
        # Draw detection boxes and labels
        for i, detection in enumerate(detections):
            try:
                color = colors[i % len(colors)]
                
                x, y = detection['x'], detection['y']
                w, h = detection['width'], detection['height']
                
                # Draw rectangle
                self.overlay_canvas.create_rectangle(x, y, x + w, y + h, 
                                                   outline=color, width=3, fill='')
                
                # Draw center point
                cx, cy = detection['center_x'], detection['center_y']
                self.overlay_canvas.create_oval(cx-4, cy-4, cx+4, cy+4, 
                                              fill='red', outline='white')
                
                # Draw label
                label = f"{detection['icon_name']}: {detection['confidence']:.2f}"
                self.overlay_canvas.create_text(x + 5, y - 15, text=label, 
                                              fill='white', font=('Arial', 10, 'bold'),
                                              anchor='nw')
            except tk.TclError:
                break
                
        # Update detection text
        self.update_detection_text(detections)
    
    def draw_detection_zone(self):
        """Draw a rectangle showing the detection zone"""
        try:
            # Use the detector's actual search area
            screen_height = self.monitor_height
            search_height = int(screen_height * self.detector.search_bottom_fraction)
            search_start_y = screen_height - search_height
            
            print(f"Drawing detection zone: y={search_start_y} to {screen_height}, width={self.monitor_width}")
            
            # Clear any existing detection zone
            self.overlay_canvas.delete("detection_zone")
            
            # Draw a VERY thick, bright green outer border
            self.overlay_canvas.create_rectangle(
                0, search_start_y, 
                self.monitor_width, screen_height,
                outline='lime', width=8, tags="detection_zone"
            )
            
            # Draw a thick red inner border
            self.overlay_canvas.create_rectangle(
                10, search_start_y + 10, 
                self.monitor_width - 10, screen_height - 10,
                outline='red', width=5, tags="detection_zone"
            )
            
            # Draw large corner squares for maximum visibility
            corner_size = 60
            # Top-left - bright yellow square
            self.overlay_canvas.create_rectangle(
                20, search_start_y + 20, 
                20 + corner_size, search_start_y + 20 + corner_size,
                fill='yellow', outline='black', width=3, tags="detection_zone"
            )
            
            # Top-right - bright blue square
            self.overlay_canvas.create_rectangle(
                self.monitor_width - 20 - corner_size, search_start_y + 20, 
                self.monitor_width - 20, search_start_y + 20 + corner_size,
                fill='blue', outline='white', width=3, tags="detection_zone"
            )
            
            # Bottom-left - bright magenta square
            self.overlay_canvas.create_rectangle(
                20, screen_height - 20 - corner_size, 
                20 + corner_size, screen_height - 20,
                fill='magenta', outline='white', width=3, tags="detection_zone"
            )
            
            # Bottom-right - bright orange square
            self.overlay_canvas.create_rectangle(
                self.monitor_width - 20 - corner_size, screen_height - 20 - corner_size, 
                self.monitor_width - 20, screen_height - 20,
                fill='orange', outline='black', width=3, tags="detection_zone"
            )
            
            # Large text label with high contrast background
            label_text = "*** DETECTION ZONE ACTIVE ***"
            text_x = self.monitor_width // 2
            text_y = search_start_y + 100
            
            # Large black background rectangle
            self.overlay_canvas.create_rectangle(
                text_x - 180, text_y - 25, 
                text_x + 180, text_y + 25,
                fill='black', outline='white', width=4, tags="detection_zone"
            )
            
            # Large white text
            self.overlay_canvas.create_text(
                text_x, text_y, 
                text=label_text,
                fill='white', font=('Arial', 18, 'bold'),
                tags="detection_zone"
            )
            
            # Force immediate update
            self.overlay_canvas.update_idletasks()
            
        except (tk.TclError, AttributeError) as e:
            print(f"Error drawing detection zone: {e}")
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
