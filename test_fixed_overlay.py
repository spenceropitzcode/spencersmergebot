import tkinter as tk

def test_fixed_overlay():
    """Test the exact same approach as the fixed live overlay"""
    print("Testing fixed overlay approach...")
    
    root = tk.Tk()
    root.title("Test Control")
    root.geometry("300x200+100+100")
    
    def show_overlay():
        print("Creating overlay window...")
        overlay = tk.Toplevel(root)
        overlay.title("Test Overlay")
        overlay.attributes('-topmost', True)
        overlay.attributes('-alpha', 0.7)
        
        # Use the same approach as the fixed version
        width, height = 2560, 1440
        overlay.geometry(f"{width}x{height}+0+0")
        overlay.configure(bg='black')
        overlay.overrideredirect(True)
        
        print(f"Overlay geometry set to: {width}x{height}+0+0")
        
        # Create canvas
        canvas = tk.Canvas(overlay, width=width, height=height, bg='black', highlightthickness=0)
        canvas.pack()
        
        # Draw detection zone (bottom 40% of screen)
        zone_start_y = int(height * 0.6)  # Start at 60% down (y=864)
        
        print(f"Drawing detection zone from y={zone_start_y} to y={height}")
        
        # Very bright, thick borders
        canvas.create_rectangle(0, zone_start_y, width, height,
                              outline='lime', width=10, fill='')
        
        canvas.create_rectangle(20, zone_start_y + 20, width - 20, height - 20,
                              outline='red', width=8, fill='')
        
        # Large corner squares
        canvas.create_rectangle(50, zone_start_y + 50, 150, zone_start_y + 150,
                              fill='yellow', outline='black', width=3)
        
        canvas.create_rectangle(width - 150, zone_start_y + 50, width - 50, zone_start_y + 150,
                              fill='blue', outline='white', width=3)
        
        # Large text
        canvas.create_text(width // 2, zone_start_y + 100,
                         text="*** FIXED DETECTION ZONE TEST ***",
                         fill='white', font=('Arial', 20, 'bold'))
        
        # Instructions
        canvas.create_text(width // 2, zone_start_y + 150,
                         text="This should be visible in the bottom 40% of your screen",
                         fill='cyan', font=('Arial', 14))
        
        print("Overlay should now be visible!")
        
        # Auto-close after 8 seconds
        root.after(8000, overlay.destroy)
    
    tk.Button(root, text="Show Fixed Overlay", command=show_overlay,
             font=('Arial', 12), bg='green', fg='white').pack(pady=20)
    
    tk.Label(root, text="Click button to test\nthe fixed overlay approach").pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    test_fixed_overlay()
