"""
Game Icon Detector using OpenCV Template Matching

This program scans game screenshots to find icons from the market_icons folder
using multi-scale template matching. It outputs the coordinates of found icons
and generates highlighted images showing the detection results.

Author: AI Assistant
Date: August 2025
"""

import cv2
import numpy as np
import os
import json
from pathlib import Path
from datetime import datetime

class GameIconDetector:
    def __init__(self, icons_dir="market_icons", screenshots_dir="test_game_screenshots", 
                 output_dir="highlighted_screenshots", threshold=0.6, search_bottom_fraction=0.25):
        """
        Initialize the Game Icon Detector.
        
        Args:
            icons_dir (str): Directory containing icon templates
            screenshots_dir (str): Directory containing game screenshots
            output_dir (str): Directory to save highlighted images
            threshold (float): Confidence threshold for matches (0.0 to 1.0)
            search_bottom_fraction (float): Fraction of image to search from bottom (0.25 = bottom quarter)
        """
        self.icons_dir = Path(icons_dir)
        self.screenshots_dir = Path(screenshots_dir)
        self.output_dir = Path(output_dir)
        self.threshold = threshold
        self.search_bottom_fraction = search_bottom_fraction
        self.results = []
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
    
    def find_matches_multiscale(self, main_image, template_image, scale_range=(0.2, 1.0), scale_steps=15):
        """
        Find template matches using multi-scale template matching.
        
        Args:
            main_image: The main screenshot image (BGR format)
            template_image: The template/icon to search for (BGR format)
            scale_range: Tuple of (min_scale, max_scale) to try
            scale_steps: Number of scale levels to test
        
        Returns:
            List of dictionaries containing match information
        """
        # Calculate search region (bottom fraction of the image)
        image_height = main_image.shape[0]
        search_start_y = int(image_height * (1 - self.search_bottom_fraction))
        
        # Crop image to search region only
        search_region = main_image[search_start_y:, :]
        
        print(f"      Original image size: {main_image.shape[1]}x{main_image.shape[0]}")
        print(f"      Search region size: {search_region.shape[1]}x{search_region.shape[0]} (bottom {self.search_bottom_fraction*100:.0f}%)")
        print(f"      Search region starts at y={search_start_y}")
        
        # Convert images to grayscale for template matching
        main_gray = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        
        # Get original template dimensions
        template_height, template_width = template_gray.shape
        
        all_matches = []
        best_confidence = 0
        
        # Generate scale factors
        min_scale, max_scale = scale_range
        scales = np.linspace(min_scale, max_scale, scale_steps)
        
        for scale in scales:
            # Calculate new dimensions
            new_width = int(template_width * scale)
            new_height = int(template_height * scale)
            
            # Skip if template becomes too small or too large
            if new_width < 10 or new_height < 10:
                continue
            if new_width > search_region.shape[1] or new_height > search_region.shape[0]:
                continue
            
            # Resize template
            template_scaled = cv2.resize(template_gray, (new_width, new_height))
            
            # Perform template matching on the cropped region
            result = cv2.matchTemplate(main_gray, template_scaled, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match for this scale
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_confidence:
                best_confidence = max_val
            
            # Find all matches above threshold for this scale
            if max_val >= self.threshold:
                locations = np.where(result >= self.threshold)
                
                for pt in zip(*locations[::-1]):  # Switch x and y coordinates
                    x, y = pt
                    confidence = result[y, x]
                    
                    # Adjust coordinates to account for the cropped search region
                    actual_x = int(x)
                    actual_y = int(y + search_start_y)  # Add offset for cropped region
                    
                    match_info = {
                        'x': actual_x,
                        'y': actual_y,
                        'width': int(new_width),
                        'height': int(new_height),
                        'center_x': int(actual_x + new_width // 2),
                        'center_y': int(actual_y + new_height // 2),
                        'confidence': float(confidence),
                        'scale': float(scale)
                    }
                    all_matches.append(match_info)
        
        # Remove overlapping matches
        filtered_matches = self._remove_overlapping_matches(all_matches)
        
        return filtered_matches, best_confidence
    
    def _remove_overlapping_matches(self, matches, overlap_threshold=0.3):
        """Remove overlapping matches, keeping the highest confidence ones."""
        if not matches:
            return matches
        
        # Sort matches by confidence (highest first)
        matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
        
        filtered_matches = []
        for current_match in matches:
            x1, y1 = current_match['x'], current_match['y']
            w1, h1 = current_match['width'], current_match['height']
            
            # Check if this match overlaps significantly with any existing match
            overlaps = False
            for existing_match in filtered_matches:
                x2, y2 = existing_match['x'], existing_match['y']
                w2, h2 = existing_match['width'], existing_match['height']
                
                # Calculate intersection area
                ix1 = max(x1, x2)
                iy1 = max(y1, y2)
                ix2 = min(x1 + w1, x2 + w2)
                iy2 = min(y1 + h1, y2 + h2)
                
                if ix1 < ix2 and iy1 < iy2:
                    intersection_area = (ix2 - ix1) * (iy2 - iy1)
                    smaller_area = min(w1 * h1, w2 * h2)
                    
                    if intersection_area / smaller_area > overlap_threshold:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered_matches.append(current_match)
        
        return filtered_matches
    
    def highlight_matches(self, image, matches, color=(0, 255, 0), thickness=3):
        """Draw rectangles and labels around found matches."""
        highlighted_image = image.copy()
        
        for i, match in enumerate(matches):
            x, y, w, h = match['x'], match['y'], match['width'], match['height']
            confidence = match['confidence']
            
            # Draw rectangle around the match
            cv2.rectangle(highlighted_image, (x, y), (x + w, y + h), color, thickness)
            
            # Add center point
            center_x, center_y = match['center_x'], match['center_y']
            cv2.circle(highlighted_image, (center_x, center_y), 8, (0, 0, 255), -1)
            
            # Add match number and confidence
            label = f"{i+1}: {confidence:.2f}"
            cv2.putText(highlighted_image, label, 
                       (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(highlighted_image, label, 
                       (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        return highlighted_image
    
    def process_all_screenshots(self):
        """Process all screenshots and detect icons."""
        # Get all icon templates
        icon_files = list(self.icons_dir.glob("*.png"))
        if not icon_files:
            print("No icon files found in market_icons directory!")
            return
        
        # Get all screenshot files
        screenshot_files = list(self.screenshots_dir.glob("*.png"))
        if not screenshot_files:
            print("No screenshot files found in test_game_screenshots directory!")
            return
        
        print(f"Found {len(icon_files)} icon templates and {len(screenshot_files)} screenshots")
        print("=" * 80)
        
        # Process each screenshot
        for screenshot_file in screenshot_files:
            print(f"\nProcessing: {screenshot_file.name}")
            
            # Load the screenshot
            main_image = cv2.imread(str(screenshot_file))
            if main_image is None:
                print(f"  Error: Could not load {screenshot_file}")
                continue
            
            screenshot_result = {
                'screenshot': screenshot_file.name,
                'timestamp': datetime.now().isoformat(),
                'image_size': {'width': main_image.shape[1], 'height': main_image.shape[0]},
                'icons_detected': []
            }
            
            highlighted_image = main_image.copy()
            total_matches = 0
            
            # Search for each icon template
            colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
            
            for icon_idx, icon_file in enumerate(icon_files):
                icon_name = icon_file.stem
                print(f"  Searching for {icon_name}...")
                
                # Load the template
                template_image = cv2.imread(str(icon_file))
                if template_image is None:
                    print(f"    Error: Could not load template {icon_file}")
                    continue
                
                # Find matches
                matches, best_confidence = self.find_matches_multiscale(main_image, template_image)
                
                icon_result = {
                    'icon_name': icon_name,
                    'template_size': {'width': template_image.shape[1], 'height': template_image.shape[0]},
                    'best_confidence': float(best_confidence),
                    'matches_found': len(matches),
                    'matches': matches
                }
                
                if matches:
                    print(f"    ✓ Found {len(matches)} match(es):")
                    for i, match in enumerate(matches):
                        print(f"      Match {i+1}: Center ({match['center_x']}, {match['center_y']}), "
                              f"Size {match['width']}x{match['height']}, Confidence {match['confidence']:.3f}")
                    
                    # Highlight matches
                    color = colors[icon_idx % len(colors)]
                    highlighted_image = self.highlight_matches(highlighted_image, matches, color)
                    total_matches += len(matches)
                else:
                    print(f"    ✗ No matches found (best confidence: {best_confidence:.3f})")
                
                screenshot_result['icons_detected'].append(icon_result)
            
            # Save results
            if total_matches > 0:
                output_filename = f"detected_{screenshot_file.name}"
                output_path = self.output_dir / output_filename
                cv2.imwrite(str(output_path), highlighted_image)
                print(f"  → Saved highlighted image: {output_filename}")
                screenshot_result['highlighted_image'] = output_filename
            else:
                print(f"  → No matches found, skipping image save")
                screenshot_result['highlighted_image'] = None
            
            screenshot_result['total_matches'] = total_matches
            self.results.append(screenshot_result)
        
        # Save JSON results
        self.save_results()
        print(f"\nProcessing complete! Results saved to detection_results.json")
    
    def save_results(self):
        """Save detection results to JSON file."""
        results_file = self.output_dir / "detection_results.json"
        
        summary = {
            'detection_summary': {
                'timestamp': datetime.now().isoformat(),
                'total_screenshots': len(self.results),
                'total_matches': sum(r['total_matches'] for r in self.results),
                'threshold_used': self.threshold
            },
            'results': self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Results saved to: {results_file}")

def main():
    """Main function to run the icon detector."""
    print("Game Icon Detector - Multi-Scale Template Matching")
    print("=" * 80)
    
    try:
        # Check OpenCV
        print(f"OpenCV version: {cv2.__version__}")
        print(f"Working directory: {os.getcwd()}")
          # Create detector instance
        detector = GameIconDetector(
            threshold=0.6,  # Confidence threshold
            search_bottom_fraction=0.25,  # Search only bottom 25% of screenshots for faster performance
        )
        
        # Process all screenshots
        detector.process_all_screenshots()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Game Icon Detector...")
    import sys
    sys.stdout.flush()
    main()
