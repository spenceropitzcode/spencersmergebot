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
                 output_dir="highlighted_screenshots", threshold=0.6, search_bottom_fraction=0.25,
                 ignore_top_right_fraction=0.2, use_preprocessing=True):
        """
        Initialize the Game Icon Detector.
        
        Args:
            icons_dir (str): Directory containing icon templates
            screenshots_dir (str): Directory containing game screenshots
            output_dir (str): Directory to save highlighted images
            threshold (float): Confidence threshold for matches (0.0 to 1.0)
            search_bottom_fraction (float): Fraction of image to search from bottom (0.25 = bottom quarter)
            ignore_top_right_fraction (float): Fraction of template to mask in top-right corner (0.0 to 1.0)
            use_preprocessing (bool): Whether to use histogram equalization for grayed-out icons
        """
        self.icons_dir = Path(icons_dir)
        self.screenshots_dir = Path(screenshots_dir)
        self.output_dir = Path(output_dir)
        self.threshold = threshold
        self.search_bottom_fraction = search_bottom_fraction
        self.ignore_top_right_fraction = ignore_top_right_fraction
        self.use_preprocessing = use_preprocessing
        self.results = []
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
    
    def prioritize_icon_search(self, icon_files):
        """
        Prioritize icon search order - put likely icons first for faster detection.
        """
        # Priority list - put important icons first
        priority_names = ['pekka', 'mega_knight', 'knight', 'archer', 'goblin', 'skeleton_king']
        
        priority_files = []
        remaining_files = []
        
        # First, add priority icons in order
        for priority_name in priority_names:
            for icon_file in icon_files:
                if icon_file.stem == priority_name:
                    priority_files.append(icon_file)
                    break
        
        # Then add remaining icons
        for icon_file in icon_files:
            if icon_file not in priority_files:
                remaining_files.append(icon_file)
        
        return priority_files + remaining_files
    
    def get_adaptive_scale_range(self, template_image, search_region):
        """
        Calculate adaptive scale range based on template and search region sizes.
        """
        template_h, template_w = template_image.shape[:2]
        search_h, search_w = search_region.shape[:2]
        
        # Calculate reasonable scale bounds based on sizes
        min_scale = max(0.1, 15.0 / max(template_w, template_h))  # Minimum 15px icons
        max_scale = min(3.0, min(search_w * 0.6 / template_w, search_h * 0.6 / template_h))  # Max 60% of search area
        
        return (min_scale, max_scale)
    
    def find_matches_multiscale(self, main_image, template_image, scale_range=(0.1, 2.0), scale_steps=15):
        """
        Find template matches using multi-scale template matching.
        
        Args:
            main_image: The main screenshot image (BGR format)
            template_image: The template/icon to search for (BGR format)
            scale_range: Tuple of (min_scale, max_scale) to try
            scale_steps: Number of scale levels to test (reduced for speed)
        
        Returns:
            List of dictionaries containing match information
        """
        # Calculate search region (bottom fraction of the image)
        image_height = main_image.shape[0]
        search_start_y = int(image_height * (1 - self.search_bottom_fraction))
        
        # Crop image to search region only
        search_region = main_image[search_start_y:, :]
        
        # Get adaptive scale range based on template and search region sizes
        if scale_range == (0.1, 2.0):  # Use default adaptive scaling
            scale_range = self.get_adaptive_scale_range(template_image, search_region)
        
    # Logging suppressed: only show near matches
        
        # Convert main image to grayscale once (outside loop for speed)
        main_gray = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        
        # Normalize both images to handle grayed-out/unaffordable icons
        if self.use_preprocessing:
            # Apply histogram equalization to improve matching between normal and grayed icons
            main_gray = cv2.equalizeHist(main_gray)
            template_gray = cv2.equalizeHist(template_gray)
        
        # Alternative: normalize brightness and contrast
        # main_gray = cv2.normalize(main_gray, None, 0, 255, cv2.NORM_MINMAX)
        # template_gray = cv2.normalize(template_gray, None, 0, 255, cv2.NORM_MINMAX)
        
        # Get original template dimensions
        template_height, template_width = template_gray.shape
        
        all_matches = []
        best_confidence = 0
        found_good_match = False  # Track if we found a good match early
        
        # Generate scale factors - use more fine-grained scaling for better detection
        min_scale, max_scale = scale_range
        # Reduce scale steps for speed - fewer steps but still good coverage
        scales_coarse = np.linspace(min_scale, max_scale, 15)  # Reduced from 25
        scales_fine = np.linspace(0.4, 1.0, 8)  # Reduced and narrowed range
        scales = np.unique(np.concatenate([scales_coarse, scales_fine]))
        scales = np.sort(scales)
        
        for scale in scales:
            # Calculate new dimensions
            new_width = int(template_width * scale)
            new_height = int(template_height * scale)
            
            # Skip if template becomes too small or too large
            if new_width < 8 or new_height < 8:  # Allow smaller icons
                continue
            if new_width > search_region.shape[1] * 0.8 or new_height > search_region.shape[0] * 0.8:  # Allow larger but not overwhelming
                continue
            
            # Resize template
            template_scaled = cv2.resize(template_gray, (new_width, new_height))
            
            # Mask out top-right corner of template if specified
            if self.ignore_top_right_fraction > 0:
                th, tw = template_scaled.shape
                mask_h = int(th * self.ignore_top_right_fraction)
                mask_w = int(tw * self.ignore_top_right_fraction)
                # Zero out top-right region to ignore obstructed parts
                template_scaled[0:mask_h, tw-mask_w:tw] = 0
            
            # Perform template matching on the cropped region
            result = cv2.matchTemplate(main_gray, template_scaled, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match for this scale
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_confidence:
                best_confidence = max_val
            
            # Early exit optimization: if we found good matches, reduce remaining scales
            if best_confidence >= self.threshold and len(all_matches) >= 1:
                # For single icon detection, if we found a good match, we can exit early
                if best_confidence > self.threshold * 1.2:  # Very confident match
                    break
                # Skip some remaining scales for speed once we have good matches
                remaining_scales = scales[scales > scale]
                if len(remaining_scales) > 3:
                    scales = np.concatenate([scales[scales <= scale], remaining_scales[::2]])
            
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
        
        # Remove overlapping matches - limit to 1 per icon since each can only appear once
        filtered_matches = self._remove_overlapping_matches(all_matches)
        
        # For single icon detection, return only the best match
        if filtered_matches:
            best_match = max(filtered_matches, key=lambda x: x['confidence'])
            return [best_match], best_confidence
        
        return filtered_matches, best_confidence
    
    def _remove_overlapping_matches(self, matches, overlap_threshold=0.2):
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
    
    def highlight_matches(self, image, matches, color=(0, 255, 0), thickness=3, icon_name=""):
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
            
            # Add icon name and confidence
            label = f"{icon_name}: {confidence:.2f}"
            cv2.putText(highlighted_image, label, 
                       (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 2)
            cv2.putText(highlighted_image, label, 
                       (x + 5, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        return highlighted_image
    
    def process_all_screenshots(self):
        """Process all screenshots and detect icons."""
        # Get all icon templates and prioritize search order
        icon_files = list(self.icons_dir.glob("*.png"))
        if not icon_files:
            return
        icon_files = self.prioritize_icon_search(icon_files)  # Optimize search order
        
        screenshot_files = list(self.screenshots_dir.glob("*.png"))
        if not screenshot_files:
            return
        
        # Process each screenshot
        for screenshot_file in screenshot_files:
            # Load the screenshot
            main_image = cv2.imread(str(screenshot_file))
            if main_image is None:
                continue
            screenshot_result = {
                'screenshot': screenshot_file.name,
                'timestamp': datetime.now().isoformat(),
                'image_size': {'width': main_image.shape[1], 'height': main_image.shape[0]},
                'icons_detected': []
            }
            highlighted_image = main_image.copy()
            total_matches = 0
            colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
            found_icons = set()  # Track which icons we've already found
            
            for icon_idx, icon_file in enumerate(icon_files):
                # Early exit: stop if we've found 3 icons (max per picture)
                # But ensure we process all priority icons first
                if total_matches >= 3:
                    priority_names = ['pekka', 'mega_knight', 'knight', 'archer', 'goblin', 'skeleton_king']
                    if icon_file.stem not in priority_names:
                        print(f"✓ Found maximum 3 icons, skipping non-priority templates")
                        break
                    
                icon_name = icon_file.stem
                # Load the template
                template_image = cv2.imread(str(icon_file))
                if template_image is None:
                    continue
                matches, best_confidence = self.find_matches_multiscale(main_image, template_image)
                
                # Only create detailed JSON object if matches were found (speed optimization)
                if matches:
                    found_icons.add(icon_name)  # Mark this icon as found
                    icon_result = {
                        'icon_name': icon_name,
                        'template_size': {'width': template_image.shape[1], 'height': template_image.shape[0]},
                        'best_confidence': float(best_confidence),
                        'matches_found': len(matches),
                        'matches': matches
                    }
                    print(f"✓ {icon_name}: {len(matches)} match(es)")
                    for i, match in enumerate(matches):
                        print(f"  Match {i+1}: Center ({match['center_x']}, {match['center_y']}), Size {match['width']}x{match['height']}, Confidence {match['confidence']:.3f}")
                    color = colors[icon_idx % len(colors)]
                    highlighted_image = self.highlight_matches(highlighted_image, matches, color, icon_name=icon_name)
                    total_matches += len(matches)
                    screenshot_result['icons_detected'].append(icon_result)
                else:
                    # Always record results for priority icons or when we have < 3 matches
                    priority_names = ['pekka', 'mega_knight', 'knight', 'archer', 'goblin', 'skeleton_king']
                    should_record = (icon_name in priority_names or 
                                   total_matches < 3 or 
                                   best_confidence > self.threshold * 0.7)
                    
                    print(f"✗ {icon_name}: No matches (best: {best_confidence:.3f})")
                    
                    if should_record:
                        screenshot_result['icons_detected'].append({
                            'icon_name': icon_name,
                            'best_confidence': float(best_confidence),
                            'matches_found': 0
                        })
            if total_matches > 0:
                output_filename = f"detected_{screenshot_file.name}"
                output_path = self.output_dir / output_filename
                cv2.imwrite(str(output_path), highlighted_image)
                print(f"→ Saved highlighted image: {output_filename}")
                screenshot_result['highlighted_image'] = output_filename
            else:
                screenshot_result['highlighted_image'] = None
            screenshot_result['total_matches'] = total_matches
            self.results.append(screenshot_result)
        
        # Save JSON results only if matches were found (speed optimization)
        if any(r['total_matches'] > 0 for r in self.results):
            self.save_results()
            print(f"\nProcessing complete! Results saved to detection_results.json")
        else:
            print(f"\nProcessing complete! No matches found, skipping JSON save.")
    
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
        
    # Logging suppressed

def main():
    """Main function to run the icon detector."""
    try:
        detector = GameIconDetector(
            threshold=0.75,
            search_bottom_fraction=0.3,
            ignore_top_right_fraction=0,
            use_preprocessing=True  # Enable preprocessing for grayed-out icons
        )
        detector.process_all_screenshots()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
