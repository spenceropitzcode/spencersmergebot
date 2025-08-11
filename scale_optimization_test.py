"""
Scale Optimization Test for Icon Detection

This script tests a wide variety of scales to find the optimal ones
for your specific icon detection setup.
"""

import cv2
import numpy as np
import pyautogui
import time
from pathlib import Path
from game_icon_detector import GameIconDetector
import json

class ScaleOptimizationTester:
    def __init__(self):
        self.detector = GameIconDetector(
            threshold=0.8,
            search_bottom_fraction=0.4,
            ignore_top_right_fraction=0,
            use_preprocessing=True
        )
        
        # Custom scan area (your optimized settings)
        self.scan_area = {
            'left_percent': 39,
            'right_percent': 57,
            'top_percent': 85,
            'bottom_percent': 100
        }
        
        # Get screen dimensions
        self.screen_width = pyautogui.size().width
        self.screen_height = pyautogui.size().height
        
    def get_scan_area_pixels(self):
        """Convert scan area percentages to pixel coordinates"""
        left = int(self.screen_width * self.scan_area['left_percent'] / 100)
        right = int(self.screen_width * self.scan_area['right_percent'] / 100)
        top = int(self.screen_height * self.scan_area['top_percent'] / 100)
        bottom = int(self.screen_height * self.scan_area['bottom_percent'] / 100)
        return left, top, right, bottom
    
    def test_scale_ranges(self):
        """Test different scale ranges to find optimal ones"""
        print("Starting Scale Optimization Test...")
        print("=" * 60)
        
        # Define scale ranges to test
        scale_tests = {
            "Very Small": np.linspace(0.1, 0.2, 10),
            "Small": np.linspace(0.2, 0.3, 10), 
            "Medium-Small": np.linspace(0.3, 0.4, 10),
            "Medium": np.linspace(0.4, 0.5, 10),
            "Medium-Large": np.linspace(0.5, 0.6, 10),
            "Large": np.linspace(0.6, 0.8, 10),
            "Very Large": np.linspace(0.8, 1.0, 10),
            "Extra Large": np.linspace(1.0, 1.5, 10)
        }
        
        # Take a screenshot for testing
        print("Taking screenshot for analysis...")
        screenshot = pyautogui.screenshot()
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Get scan region
        left, top, right, bottom = self.get_scan_area_pixels()
        scan_region = screenshot_cv[top:bottom, left:right]
        
        print(f"Scan region: {scan_region.shape[1]}x{scan_region.shape[0]} pixels")
        print(f"Scan area: ({left},{top}) to ({right},{bottom})")
        print()
        
        # Get icon templates
        icon_files = list(self.detector.icons_dir.glob("*.png"))
        if not icon_files:
            print("ERROR: No icon templates found in market_icons folder!")
            return
        
        print(f"Testing {len(icon_files)} icon templates")
        print("=" * 60)
        
        results = {}
        
        for range_name, scales in scale_tests.items():
            print(f"\nTesting {range_name} range: {scales[0]:.2f} to {scales[-1]:.2f}")
            range_results = []
            
            for icon_file in icon_files[:5]:  # Test first 5 icons for speed
                icon_name = icon_file.stem
                template_image = cv2.imread(str(icon_file))
                if template_image is None:
                    continue
                
                best_scale_confidence = 0
                best_scale = 0
                scale_confidences = []
                
                for scale in scales:
                    confidence = self.test_single_scale(scan_region, template_image, scale)
                    scale_confidences.append(confidence)
                    
                    if confidence > best_scale_confidence:
                        best_scale_confidence = confidence
                        best_scale = scale
                
                if best_scale_confidence > 0.5:  # Only include meaningful results
                    range_results.append({
                        'icon': icon_name,
                        'best_scale': best_scale,
                        'best_confidence': best_scale_confidence,
                        'scale_confidences': scale_confidences
                    })
                    
                    print(f"  {icon_name}: Best scale {best_scale:.3f} (confidence: {best_scale_confidence:.3f})")
            
            results[range_name] = range_results
            
            if range_results:
                avg_best_scale = np.mean([r['best_scale'] for r in range_results])
                avg_confidence = np.mean([r['best_confidence'] for r in range_results])
                print(f"  Range Summary: Avg scale {avg_best_scale:.3f}, Avg confidence {avg_confidence:.3f}")
            else:
                print(f"  No significant detections in {range_name} range")
        
        # Analyze results
        self.analyze_results(results)
        return results
    
    def test_single_scale(self, region_image, template_image, scale):
        """Test a single scale and return best confidence"""
        try:
            # Convert to grayscale
            region_gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
            
            # Apply preprocessing
            if self.detector.use_preprocessing:
                region_gray = cv2.equalizeHist(region_gray)
                template_gray = cv2.equalizeHist(template_gray)
            
            # Get template dimensions
            template_height, template_width = template_gray.shape
            
            # Calculate new dimensions
            new_width = int(template_width * scale)
            new_height = int(template_height * scale)
            
            # Skip if template becomes too small or too large
            if new_width < 5 or new_height < 5:
                return 0.0
            if new_width > region_image.shape[1] or new_height > region_image.shape[0]:
                return 0.0
            
            # Resize template
            template_scaled = cv2.resize(template_gray, (new_width, new_height))
            
            # Perform template matching
            result = cv2.matchTemplate(region_gray, template_scaled, cv2.TM_CCOEFF_NORMED)
            
            # Get best match
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            return float(max_val)
            
        except Exception as e:
            return 0.0
    
    def analyze_results(self, results):
        """Analyze results and provide recommendations"""
        print("\n" + "=" * 60)
        print("ANALYSIS & RECOMMENDATIONS")
        print("=" * 60)
        
        all_detections = []
        for range_name, range_results in results.items():
            for detection in range_results:
                all_detections.append({
                    'range': range_name,
                    'scale': detection['best_scale'],
                    'confidence': detection['best_confidence'],
                    'icon': detection['icon']
                })
        
        if not all_detections:
            print("No significant detections found. Try:")
            print("1. Ensure game is visible in scan area")
            print("2. Lower the threshold")
            print("3. Check icon templates are correct")
            return
        
        # Sort by confidence
        all_detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"\nTOP 10 DETECTIONS:")
        for i, detection in enumerate(all_detections[:10]):
            print(f"{i+1:2d}. {detection['icon']:15s} | Scale: {detection['scale']:.3f} | Confidence: {detection['confidence']:.3f} | Range: {detection['range']}")
        
        # Find optimal scale range
        best_scales = [d['scale'] for d in all_detections[:15]]  # Top 15 scales
        
        if best_scales:
            min_optimal = min(best_scales)
            max_optimal = max(best_scales)
            avg_optimal = np.mean(best_scales)
            
            print(f"\nOPTIMAL SCALE ANALYSIS:")
            print(f"Range: {min_optimal:.3f} to {max_optimal:.3f}")
            print(f"Average: {avg_optimal:.3f}")
            print(f"Standard deviation: {np.std(best_scales):.3f}")
            
            # Recommend 3-5 scales around the optimal range
            recommended_scales = [
                avg_optimal - np.std(best_scales),
                avg_optimal - np.std(best_scales)/2,
                avg_optimal,
                avg_optimal + np.std(best_scales)/2,
                avg_optimal + np.std(best_scales)
            ]
            
            # Filter to reasonable range
            recommended_scales = [s for s in recommended_scales if 0.1 <= s <= 1.0]
            
            print(f"\nRECOMMENDED SCALES FOR CODE:")
            print("Replace this line in your code:")
            print("scales = np.array([0.25, 0.3, 0.35])")
            print("With:")
            scales_str = ", ".join([f"{s:.2f}" for s in recommended_scales])
            print(f"scales = np.array([{scales_str}])")
        
        # Save detailed results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scale_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {filename}")
    
    def quick_test(self):
        """Quick test with current optimal scales"""
        print("Quick test with current scales...")
        screenshot = pyautogui.screenshot()
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        left, top, right, bottom = self.get_scan_area_pixels()
        scan_region = screenshot_cv[top:bottom, left:right]
        
        current_scales = [0.25, 0.3, 0.35]
        
        icon_files = list(self.detector.icons_dir.glob("*.png"))[:5]
        
        print(f"Testing scales: {current_scales}")
        print("-" * 40)
        
        for icon_file in icon_files:
            icon_name = icon_file.stem
            template_image = cv2.imread(str(icon_file))
            if template_image is None:
                continue
            
            print(f"{icon_name}:")
            for scale in current_scales:
                confidence = self.test_single_scale(scan_region, template_image, scale)
                print(f"  Scale {scale}: {confidence:.3f}")

def main():
    tester = ScaleOptimizationTester()
    
    print("Scale Optimization Tester")
    print("1. Full test (comprehensive)")
    print("2. Quick test (current scales)")
    
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == "1":
        tester.test_scale_ranges()
    elif choice == "2":
        tester.quick_test()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
