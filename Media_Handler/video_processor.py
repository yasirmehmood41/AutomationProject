"""Video processing module for generating video content."""
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import textwrap
from moviepy.config import change_settings
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, ColorClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip
)
from moviepy.video.fx.resize import resize

# Configure MoviePy to use ImageMagick
change_settings({"IMAGEMAGICK_BINARY": "magick"})

@dataclass
class VideoStyle:
    """Video style configuration."""
    name: str
    font: str = "Arial"
    font_size: int = 36
    text_color: str = "white"
    background_color: str = "#000000"
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    transition_duration: float = 0.5
    text_margin: int = 50

    @classmethod
    def get_style(cls, style_name: str) -> 'VideoStyle':
        """Get predefined style by name."""
        styles = {
            "modern": cls(
                name="modern",
                font="Arial",
                text_color="white",
                background_color="#2C3333"
            ),
            "corporate": cls(
                name="corporate",
                font="Arial",
                text_color="white",
                background_color="#395B64"
            ),
            "creative": cls(
                name="creative",
                font="Arial",
                text_color="#FFD369",
                background_color="#222831"
            ),
            "tech": cls(
                name="tech",
                font="Arial",
                text_color="#00FF00",
                background_color="#000000"
            ),
            "casual": cls(
                name="casual",
                font="Arial",
                text_color="white",
                background_color="#3F4E4F"
            )
        }
        return styles.get(style_name, styles["modern"])

class VideoProcessor:
    """Video processor for generating video content."""
    def __init__(self):
        self.output_dir = os.path.join("output_manager", "videos")
        os.makedirs(self.output_dir, exist_ok=True)

    def create_text_image(self, text: str, style: VideoStyle, width=None) -> np.ndarray:
        """Create text image using PIL."""
        if width is None:
            width = style.resolution[0] - 2 * style.text_margin
        
        # Use a basic font that's guaranteed to exist
        try:
            # For Windows, don't add .ttf extension
            font = ImageFont.truetype("Arial", style.font_size)
        except:
            try:
                # Try with ttf extension
                font = ImageFont.truetype("Arial.ttf", style.font_size)
            except:
                # Last resort fallback
                font = ImageFont.load_default()
        
        # Parse color
        if style.text_color.startswith('#'):
            r = int(style.text_color[1:3], 16)
            g = int(style.text_color[3:5], 16)
            b = int(style.text_color[5:7], 16)
            text_color = (r, g, b, 255)
        else:
            colors = {
                'white': (255, 255, 255, 255),
                'black': (0, 0, 0, 255),
                'green': (0, 255, 0, 255),
                'red': (255, 0, 0, 255),
                'blue': (0, 0, 255, 255)
            }
            text_color = colors.get(style.text_color.lower(), (255, 255, 255, 255))
        
        # Wrap text to fit width
        wrapped_text = textwrap.fill(text, width=40)  # Approximate characters per line
        
        # Create a temporary image to measure text
        temp_img = Image.new('RGBA', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Measure text dimensions (newer PIL versions)
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox(wrapped_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            # Older PIL versions - estimate size
            text_width = len(wrapped_text) * (style.font_size // 2)
            text_height = wrapped_text.count('\n') * style.font_size + style.font_size
        
        # Create image with proper size
        img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw text
        draw.text((10, 10), wrapped_text, font=font, fill=text_color)
        
        # Convert to numpy array for MoviePy
        return np.array(img)

    def process_video(self, scenes: List[Dict], audio_file: str = "", style_name: str = "modern") -> Optional[str]:
        """Process scenes into a video."""
        try:
            # Input validation
            if not scenes or len(scenes) == 0:
                print("Error: No scenes provided")
                return None
            
            print(f"Processing {len(scenes)} scenes with {style_name} style")
            style = VideoStyle.get_style(style_name)
            scene_clips = []
            
            # Process each scene
            for i, scene in enumerate(scenes):
                try:
                    print(f"\nProcessing scene {i+1}: {scene.get('name', 'Untitled')}")
                    
                    # Calculate duration
                    duration = 5.0  # Default 5 seconds
                    if scene.get('timing') and 'to' in scene.get('timing'):
                        try:
                            parts = scene['timing'].split('to')
                            start_time = float(parts[0].strip())
                            end_time = float(parts[1].strip())
                            duration = end_time - start_time
                            duration = max(duration, 1.0)  # Minimum 1 second
                            print(f"  Duration: {duration:.1f} seconds")
                        except:
                            print(f"  Invalid timing format, using default duration")
                    
                    # Create background clip
                    try:
                        color = style.background_color.lstrip('#')
                        rgb_color = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                        bg_clip = ColorClip(
                            size=style.resolution,
                            color=rgb_color,
                            duration=duration
                        )
                        print("  Created background clip")
                        
                        clips = [bg_clip]
                        
                        # Add text clips
                        if scene.get('text'):
                            print(f"  Adding {len(scene['text'])} text elements")
                            screen_height = style.resolution[1]
                            margin = style.text_margin
                            spacing = (screen_height - 2 * margin) // (len(scene['text']) + 1)
                            
                            for j, text in enumerate(scene['text']):
                                try:
                                    # Directly use TextClip with preset font
                                    text_clip = TextClip(
                                        text, 
                                        fontsize=style.font_size,
                                        color=style.text_color,
                                        bg_color=None,
                                        font='Arial',
                                        method='pango'  # Try pango method (should work without ImageMagick)
                                    )
                                    
                                    # Position text and set duration
                                    y_pos = margin + spacing * (j + 1)
                                    text_clip = text_clip.set_position(('center', y_pos))
                                    text_clip = text_clip.set_duration(duration)
                                    
                                    clips.append(text_clip)
                                    print(f"  Added text clip {j+1}")
                                except Exception as e:
                                    print(f"  Error creating text clip {j+1}: {str(e)}")
                                    # Try alternative method with PIL if TextClip fails
                                    try:
                                        text_array = self.create_text_image(text, style)
                                        pil_text_clip = ImageClip(text_array)
                                        pil_text_clip = pil_text_clip.set_duration(duration)
                                        pil_text_clip = pil_text_clip.set_position(('center', y_pos))
                                        clips.append(pil_text_clip)
                                        print(f"  Added text clip {j+1} using PIL alternative")
                                    except Exception as e2:
                                        print(f"  Error with PIL alternative: {str(e2)}")
                        
                        # Composite all clips
                        scene_clip = CompositeVideoClip(clips, size=style.resolution)
                        scene_clip = scene_clip.set_duration(duration)
                        
                        scene_clips.append(scene_clip)
                        print(f"  Scene {i+1} processed successfully")
                        
                    except Exception as e:
                        print(f"  Error creating background: {str(e)}")
                        
                except Exception as e:
                    print(f"  Error processing scene {i+1}: {str(e)}")
            
            # Final check before compositing
            if not scene_clips or len(scene_clips) == 0:
                print("Error: No valid scene clips generated")
                return None
            
            print(f"\nCombining {len(scene_clips)} clips into final video")
            final_video = concatenate_videoclips(scene_clips)
            
            # Add audio if provided
            if audio_file and os.path.exists(audio_file):
                try:
                    audio = AudioFileClip(audio_file)
                    final_video = final_video.set_audio(audio)
                    print("Added audio to video")
                except Exception as e:
                    print(f"Error adding audio: {str(e)}")
            
            # Generate unique output filename
            timestamp = int(time.time())
            output_file = os.path.join(self.output_dir, f"video_{style_name}_{timestamp}.mp4")
            
            # Write video file
            print(f"Writing video to {output_file}")
            final_video.write_videofile(
                output_file,
                fps=style.fps,
                codec='libx264',
                audio_codec='aac' if audio_file else None,
                verbose=False
            )
            
            print("Video completed successfully")
            return output_file
            
        except Exception as e:
            import traceback
            print(f"Error processing video: {str(e)}")
            traceback.print_exc()
            return None
