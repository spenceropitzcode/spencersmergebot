import tkinter as tk
import pyautogui
import time

def test_overlay():
    """Simple test to verify overlay is visible"""
    print("Testing overlay visibility...")
    
    # Get screen info
    screen_width, screen_height = pyautogui.size()
    print(f"PyAutoGUI screen size: {screen_width}x{screen_height}")
    
    # Create test window
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Create overlay window
    overlay = tk.Toplevel(root)
    overlay.title("TEST OVERLAY")
    overlay.attributes('-topmost', True)
    overlay.attributes('-transparentcolor', 'black')
    overlay.configure(bg='black')
    overlay.geometry(f"{screen_width}x{screen_height}+0+0")
    overlay.overrideredirect(True)
    
    # Create canvas
    canvas = tk.Canvas(overlay, width=screen_width, height=screen_height, bg='black', highlightthickness=0)
    canvas.pack()
    
    # Draw a VERY visible test rectangle
    test_x = screen_width // 4
    test_y = screen_height // 4
    test_width = screen_width // 2
    test_height = screen_height // 2
    
    # Multiple colored rectangles for maximum visibility
    canvas.create_rectangle(test_x, test_y, test_x + test_width, test_y + test_height, 
                          outline='red', width=10, fill='')
    canvas.create_rectangle(test_x + 20, test_y + 20, test_x + test_width - 20, test_y + test_height - 20, 
                          outline='yellow', width=8, fill='')
    canvas.create_rectangle(test_x + 40, test_y + 40, test_x + test_width - 40, test_y + test_height - 40, 
                          outline='cyan', width=6, fill='')
    
    # Add text
    canvas.create_text(screen_width//2, screen_height//2, text="TEST OVERLAY - CAN YOU SEE THIS?", 
                      fill='white', font=('Arial', 24, 'bold'))
    
    print(f"Created test overlay at 0,0 size {screen_width}x{screen_height}")
    print("Looking for red/yellow/cyan rectangles in center of screen...")
    print("Window will close in 10 seconds...")
    
    # Show for 10 seconds
    root.after(10000, root.quit)
    root.mainloop()

if __name__ == "__main__":
    test_overlay()
