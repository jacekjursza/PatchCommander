#!/usr/bin/env python3
"""
Generate basic icons for PatchCommander.
This script creates simple icons for Windows (.ico), macOS (.icns), and Linux (.png).
"""

import os
import sys
import platform

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow library not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image, ImageDraw, ImageFont

def create_basic_icon():
    """Create a basic icon image with text."""
    # Create a blank image with a blue background
    img = Image.new('RGB', (512, 512), color=(0, 102, 204))
    draw = ImageDraw.Draw(img)

    # Try to add text (if font is available)
    try:
        # First try to find a system font
        font_size = 72
        text = "PC"

        # Choose a system font based on platform
        system = platform.system()
        if system == "Windows":
            font_path = "arial.ttf"
        elif system == "Darwin":  # macOS
            font_path = "/System/Library/Fonts/Helvetica.ttc"
        else:  # Linux and others
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        try:
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            # Fallback to default
            font = ImageFont.load_default()

        # Get text size
        text_width, text_height = draw.textsize(text, font=font) if hasattr(draw, 'textsize') else (200, 100)

        # Position text in center
        position = ((512 - text_width) // 2, (512 - text_height) // 2)

        # Draw text
        draw.text(position, text, fill="white", font=font)
    except Exception as e:
        print(f"Could not add text to icon: {e}")
        # Draw a simple shape instead
        draw.rectangle([128, 128, 384, 384], fill="white")

    return img

def generate_windows_icon(img):
    """Generate Windows .ico file."""
    if not os.path.exists("resources"):
        os.makedirs("resources")

    # Create different sizes
    sizes = [16, 32, 48, 64, 128, 256]
    icons = []

    for size in sizes:
        icons.append(img.resize((size, size), Image.LANCZOS))

    # Save as ICO
    icons[0].save("resources/icon.ico",
                  format="ICO",
                  sizes=[(icon.width, icon.height) for icon in icons],
                  append_images=icons[1:])

    print("Generated Windows icon: resources/icon.ico")

def generate_macos_icon(img):
    """Generate macOS .icns file (simplified approach)."""
    if not os.path.exists("resources"):
        os.makedirs("resources")

    # For a true .icns file, you need additional tools
    # This is a simplified approach that creates a PNG that can be converted
    # to .icns on macOS using the iconutil command

    img.resize((1024, 1024), Image.LANCZOS).save("resources/icon.png", "PNG")

    # Just rename the file for now (this won't work as a real .icns file)
    # But at least our script will skip this error
    with open("resources/icon.icns", "wb") as f:
        with open("resources/icon.png", "rb") as source:
            f.write(source.read())

    print("Generated placeholder macOS icon: resources/icon.icns")
    print("Note: This is not a valid .icns file. On macOS, you should replace this with a proper .icns file.")

def generate_linux_icon(img):
    """Generate Linux .png file."""
    if not os.path.exists("resources"):
        os.makedirs("resources")

    img.resize((256, 256), Image.LANCZOS).save("resources/icon.png", "PNG")
    print("Generated Linux icon: resources/icon.png")

def main():
    """Main function."""
    print("Generating icons for PatchCommander...")

    # Create basic icon
    img = create_basic_icon()

    # Generate platform-specific icons
    generate_windows_icon(img)
    generate_macos_icon(img)
    generate_linux_icon(img)

    print("Icon generation complete!")

if __name__ == "__main__":
    main()