#!/usr/bin/env python3
"""
Lucidchart Image Crop Tool
This script crops large Lucidchart PNG exports (e.g., 6000x6000px) into smaller,
readable chunks so that LLMs (and humans) can visually verify decision tree branches,
intents, and transition routes.

Usage:
  python3 crop_image.py --input <path_to_png> --coords <left> <top> <right> <bottom> [--output <path_to_output>] [--resize <width> <height>]

Example:
  python3 crop_image.py --input docs/designs/identification.png --coords 2300 1250 3650 2150 --output /tmp/crop.png --resize 2025 1350
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: The 'Pillow' library is required to run this script.")
    print("Please install it using: pip install Pillow")
    sys.exit(1)


def crop_lucid_png(input_path: str, coords: tuple[int, int, int, int], output_path: str, resize: tuple[int, int] = None):
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file '{input_path}' does not exist.")
        sys.exit(1)

    print(f"Opening {input_file.name}...")
    with Image.open(input_file) as img:
        print(f"Original size: {img.size[0]}x{img.size[1]} | Format: {img.format}")
        
        # Ensure crop coordinates are within bounds
        left, top, right, bottom = coords
        left = max(0, min(left, img.size[0]))
        top = max(0, min(top, img.size[1]))
        right = max(left, min(right, img.size[0]))
        bottom = max(top, min(bottom, img.size[1]))
        
        print(f"Cropping region: ({left}, {top}, {right}, {bottom})...")
        cropped_img = img.crop((left, top, right, bottom))
        
        if resize:
            print(f"Resizing crop to: {resize[0]}x{resize[1]}...")
            cropped_img = cropped_img.resize(resize)
            
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        cropped_img.save(output_file)
        print(f"Successfully saved cropped image to: {output_file.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crop large Lucidchart PNG exports.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input PNG image file.")
    parser.add_argument("-c", "--coords", required=True, type=int, nargs=4, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                        help="Crop box coordinates: left top right bottom.")
    parser.add_argument("-o", "--output", default="/tmp/lucid_crop.png", help="Path to save the cropped PNG (default: /tmp/lucid_crop.png).")
    parser.add_argument("-r", "--resize", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"), help="Optional resize dimensions: width height.")
    
    args = parser.parse_args()
    
    crop_lucid_png(
        input_path=args.input,
        coords=tuple(args.coords),
        output_path=args.output,
        resize=tuple(args.resize) if args.resize else None
    )
