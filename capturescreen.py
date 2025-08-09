import pyautogui

# Define the region of the BlueStacks window (x, y, width, height)
region = (100, 100, 1280, 720)  # Example values; update these for your setup

# Take a screenshot of the specified region
screenshot = pyautogui.screenshot(region=region)

# Save the screenshot to a file
screenshot.save("bluestacks_screenshot.png")

print("Screenshot saved as bluestacks_screenshot.png")