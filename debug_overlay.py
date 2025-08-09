import tkinter as tk
import threading
import time

class DebugOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Debug Overlay Control")
        self.root.geometry("400x300+100+100")
        
        self.overlay_window = None
        self.running = False
        
        # Create control buttons
        tk.Button(self.root, text="Show Simple Overlay", 
                 command=self.show_simple_overlay, 
                 font=('Arial', 12), bg='green', fg='white').pack(pady=10)
        
        tk.Button(self.root, text="Show Full Screen Overlay", 
                 command=self.show_fullscreen_overlay,
                 font=('Arial', 12), bg='blue', fg='white').pack(pady=10)
        
        tk.Button(self.root, text="Hide Overlay", 
                 command=self.hide_overlay,
                 font=('Arial', 12), bg='red', fg='white').pack(pady=10)
        
        self.status_label = tk.Label(self.root, text="Ready", font=('Arial', 10))
        self.status_label.pack(pady=10)
        
    def show_simple_overlay(self):
        """Show a simple, definitely visible overlay window"""
        if self.overlay_window:
            self.overlay_window.destroy()
            
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Debug Overlay")
        self.overlay_window.geometry("800x600+500+200")  # Fixed size and position
        self.overlay_window.configure(bg='red')
        self.overlay_window.attributes('-topmost', True)
        
        # Add visible content
        label = tk.Label(self.overlay_window, 
                        text="THIS IS THE DEBUG OVERLAY\nIf you can see this, overlays work!",
                        font=('Arial', 20, 'bold'),
                        fg='white', bg='red')
        label.pack(expand=True)
        
        self.status_label.config(text="Simple overlay shown")
        
    def show_fullscreen_overlay(self):
        """Show a fullscreen overlay with detection zone"""
        if self.overlay_window:
            self.overlay_window.destroy()
            
        self.overlay_window = tk.Toplevel(self.root)
        self.overlay_window.title("Fullscreen Debug Overlay")
        self.overlay_window.attributes('-fullscreen', True)
        self.overlay_window.attributes('-topmost', True)
        self.overlay_window.configure(bg='black')
        
        # Make it semi-transparent
        self.overlay_window.attributes('-alpha', 0.3)
        
        # Create canvas for drawing
        canvas = tk.Canvas(self.overlay_window, bg='black', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw detection zone in bottom portion
        screen_width = 2560
        screen_height = 1440
        zone_start_y = 864
        
        # Draw bright detection zone
        canvas.create_rectangle(0, zone_start_y, screen_width, screen_height,
                              outline='lime', width=10, fill='')
        
        canvas.create_rectangle(20, zone_start_y + 20, screen_width - 20, screen_height - 20,
                              outline='red', width=5, fill='')
        
        # Add corner markers
        corner_size = 100
        canvas.create_rectangle(50, zone_start_y + 50, 50 + corner_size, zone_start_y + 50 + corner_size,
                              fill='yellow', outline='black', width=3)
        
        canvas.create_rectangle(screen_width - 50 - corner_size, zone_start_y + 50,
                              screen_width - 50, zone_start_y + 50 + corner_size,
                              fill='blue', outline='white', width=3)
        
        # Large text
        canvas.create_text(screen_width // 2, zone_start_y + 150,
                         text="DETECTION ZONE - FULLSCREEN DEBUG",
                         fill='white', font=('Arial', 24, 'bold'))
        
        # Add close instruction
        canvas.create_text(screen_width // 2, 100,
                         text="Press ESC or click Hide Overlay to close",
                         fill='white', font=('Arial', 16))
        
        # Bind escape key to close
        self.overlay_window.bind('<Escape>', lambda e: self.hide_overlay())
        self.overlay_window.focus_set()
        
        self.status_label.config(text="Fullscreen overlay shown")
        
    def hide_overlay(self):
        """Hide the overlay"""
        if self.overlay_window:
            self.overlay_window.destroy()
            self.overlay_window = None
        self.status_label.config(text="Overlay hidden")
        
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.hide_overlay)
        self.root.mainloop()

if __name__ == "__main__":
    app = DebugOverlay()
    app.run()
