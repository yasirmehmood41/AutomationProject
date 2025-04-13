"""
Simple Automation Solution for Video Creation
============================================
This script provides a straightforward approach to create videos from scripts.
It works without complex dependencies and produces reliable results.
"""
import os
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip, concatenate_videoclips

# =========================================================
# STEP 1: Create the output directory
# =========================================================
OUTPUT_DIR = "D:/AutomationProject/videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory: {OUTPUT_DIR}")

# =========================================================
# STEP 2: Text rendering functions (using PIL instead of ImageMagick)
# =========================================================
def create_text_image(text, font_size=60, width=1280, height=720, bg_color=(0,0,0,0), text_color=(255,255,255,255)):
    """Create text image using PIL - doesn't require ImageMagick"""
    # Create transparent image
    image = Image.new('RGBA', (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Use a guaranteed system font
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\Arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Get text size for centering
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(text) * font_size // 2
        text_height = font_size
    
    # Position text in center
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Convert to numpy array for MoviePy
    return np.array(image)

# =========================================================
# STEP 3: Scene creation function
# =========================================================
def create_scene(text, bg_color=(0,0,0), duration=5, resolution=(1280, 720)):
    """Create a video scene with background and text"""
    print(f"Creating scene: {text[:30]}...")
    
    # Create background
    bg_clip = ColorClip(size=resolution, color=bg_color, duration=duration)
    
    # Create text using PIL (more reliable than MoviePy's text)
    text_img = create_text_image(text, width=resolution[0], height=resolution[1])
    text_clip = ImageClip(text_img).set_duration(duration)
    
    # Combine background and text
    return CompositeVideoClip([bg_clip, text_clip], size=resolution)

# =========================================================
# STEP 4: Main video generation function
# =========================================================
def create_video(scenes, output_name="video"):
    """Create a video from a list of scene information"""
    print(f"Creating video with {len(scenes)} scenes...")
    
    # Create clips for each scene
    clips = []
    for i, scene in enumerate(scenes):
        try:
            # Get scene properties (with defaults)
            text = scene.get('text', f"Scene {i+1}")
            color = scene.get('color', (0, 0, 0))
            duration = scene.get('duration', 5)
            
            # Create scene clip
            clip = create_scene(text, bg_color=color, duration=duration)
            clips.append(clip)
            print(f"  Scene {i+1} created successfully")
        except Exception as e:
            print(f"  Error in scene {i+1}: {str(e)}")
    
    # Combine all clips
    if not clips:
        print("Error: No valid clips created")
        return None
    
    # Generate final video
    print("Combining clips...")
    final_video = concatenate_videoclips(clips)
    
    # Create output file path with timestamp
    timestamp = int(time.time())
    output_file = os.path.join(OUTPUT_DIR, f"{output_name}_{timestamp}.mp4")
    
    # Write video file
    print(f"Writing video to {output_file}")
    final_video.write_videofile(
        output_file, 
        fps=24, 
        codec='libx264',
        audio_codec=None,
        verbose=False
    )
    
    print(f"Video created successfully: {output_file}")
    return output_file

# =========================================================
# STEP 5: Sample usage with demonstration
# =========================================================
if __name__ == "__main__":
    # Demo scenes (modify these for your content)
    demo_scenes = [
        {
            'text': "Welcome to Our Presentation",
            'color': (0, 0, 0),  # RGB black
            'duration': 5
        },
        {
            'text': "Key Features and Benefits",
            'color': (0, 50, 0),  # Dark green
            'duration': 5
        },
        {
            'text': "Thank You for Watching!",
            'color': (0, 0, 50),  # Dark blue
            'duration': 3
        }
    ]
    
    # Generate demo video
    create_video(demo_scenes, "demo_video")
    
    print("\nTo create your own video:")
    print("1. Edit the 'demo_scenes' list with your content")
    print("2. Run this script")
    print("3. Find the video in the 'videos' folder")
