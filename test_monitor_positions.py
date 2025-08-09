import tkinter as tk
import tkinter.messagebox as messagebox

def test_monitor_positioning():
    """Test to find the correct monitor positioning"""
    root = tk.Tk()
    root.title("Monitor Position Test")
    root.geometry("400x300+100+100")
    
    def test_position(x_offset, y_offset, description):
        print(f"Testing position: {description} at {x_offset},{y_offset}")
        
        overlay = tk.Toplevel(root)
        overlay.title(f"Test: {description}")
        overlay.attributes('-topmost', True)
        overlay.configure(bg='red')
        
        # Create a 800x600 test window at the specified position
        overlay.geometry(f"800x600+{x_offset}+{y_offset}")
        
        label = tk.Label(overlay, 
                        text=f"TEST POSITION\n{description}\nX: {x_offset}, Y: {y_offset}",
                        font=('Arial', 16, 'bold'),
                        fg='white', bg='red')
        label.pack(expand=True)
        
        # Auto-close after 3 seconds
        root.after(3000, overlay.destroy)
    
    # Test different positions for multi-monitor setups
    positions = [
        (0, 0, "Position 0,0 (Primary)"),
        (-1920, 0, "Left Monitor (-1920,0)"),
        (1920, 0, "Right Monitor (1920,0)"),
        (640, 0, "Middle of main monitor"),
        (880, 0, "Centered for 1440p"),
    ]
    
    def show_info():
        # Get Tkinter's view of screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Get window position
        root.update_idletasks()
        x = root.winfo_x()
        y = root.winfo_y()
        
        info = f"""Screen Info:
Tkinter screen size: {screen_width}x{screen_height}
This window position: {x},{y}

For your 1440p middle monitor setup, the overlay should probably be positioned at:
- If main monitor is at 0,0: use +0+0
- If main monitor is offset: use +{1920//2 if screen_width > 2560 else 0}+0

We'll test different positions to find the right one."""
        
        messagebox.showinfo("Monitor Info", info)
    
    # Create buttons for each test position
    tk.Label(root, text="Click buttons to test overlay positions:", font=('Arial', 12, 'bold')).pack(pady=10)
    
    for x_offset, y_offset, description in positions:
        btn = tk.Button(root, text=f"Test: {description}", 
                       command=lambda x=x_offset, y=y_offset, desc=description: test_position(x, y, desc),
                       font=('Arial', 10))
        btn.pack(pady=2, padx=10, fill=tk.X)
    
    tk.Button(root, text="Show Screen Info", command=show_info,
             font=('Arial', 12), bg='blue', fg='white').pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    test_monitor_positioning()
