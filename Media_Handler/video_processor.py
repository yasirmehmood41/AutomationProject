"""Video processing module for generating video content."""
import os
import time
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

@dataclass
class Resolution:
    """Video resolution configuration."""
    name: str
    width: int
    height: int
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        return (self.width, self.height)

class VideoStyle:
    """Video style configuration."""
    
    RESOLUTIONS = {
        'HD': Resolution('HD', 1280, 720),
        'FHD': Resolution('Full HD', 1920, 1080),
        '4K': Resolution('4K', 3840, 2160)
    }
    
    def __init__(self, 
                 name: str,
                 font: str = "Arial",
                 font_size: int = 36,
                 text_color: str = "white",
                 background_color: str = "#000000",
                 resolution: str = "FHD",
                 fps: int = 30,
                 transition_duration: float = 0.5,
                 text_margin: int = 50):
        """Initialize video style."""
        self.name = name
        self.font = font
        self.font_size = font_size
        self.text_color = text_color
        self.background_color = background_color
        self._resolution = self.RESOLUTIONS.get(resolution, self.RESOLUTIONS['FHD'])
        self.fps = fps
        self.transition_duration = transition_duration
        self.text_margin = text_margin
        
        # Validate colors
        self._validate_color(text_color, "text_color")
        self._validate_color(background_color, "background_color")
    
    @property
    def resolution(self) -> Tuple[int, int]:
        """Get resolution dimensions."""
        return self._resolution.dimensions
    
    @staticmethod
    def _validate_color(color: str, field_name: str) -> None:
        """Validate color format."""
        if not isinstance(color, str):
            raise ValueError(f"{field_name} must be a string")
        if color.startswith('#'):
            if not len(color) == 7:
                raise ValueError(f"Invalid hex color for {field_name}: {color}")
            try:
                int(color[1:], 16)
            except ValueError:
                raise ValueError(f"Invalid hex color for {field_name}: {color}")
        else:
            valid_colors = {"white", "black", "red", "green", "blue", "yellow"}
            if color.lower() not in valid_colors:
                raise ValueError(f"Invalid color name for {field_name}: {color}")
    
    @classmethod
    def get_style(cls, style_name: str) -> 'VideoStyle':
        """Get predefined style by name."""
        styles = {
            'modern': cls(
                name="Modern",
                background_color="#1E1E1E",
                text_color="white",
                font_size=42
            ),
            'corporate': cls(
                name="Corporate",
                background_color="#FFFFFF",
                text_color="#000000",
                font_size=36
            ),
            'tech': cls(
                name="Tech",
                background_color="#000000",
                text_color="#00FF00",
                font_size=40
            ),
            'creative': cls(
                name="Creative",
                background_color="#2C3E50",
                text_color="#ECF0F1",
                font_size=44
            ),
            'casual': cls(
                name="Casual",
                background_color="#F5F5F5",
                text_color="#333333",
                font_size=38
            )
        }
        
        if style_name not in styles:
            logger.warning(f"Style {style_name} not found, using modern")
            return styles['modern']
        return styles[style_name]

class VideoProcessor:
    """Video processor for generating video content."""
    
    def __init__(self):
        """Initialize video processor."""
        self.output_dir = os.path.join("output_manager", "videos")
        os.makedirs(self.output_dir, exist_ok=True)
        self.max_workers = os.cpu_count() or 4
    
    def create_text_image(self, text: str, style: VideoStyle) -> np.ndarray:
        """Create text image using PIL."""
        if not text or not isinstance(text, str):
            raise ValueError("Invalid text input")
            
        try:
            # Create image with alpha channel
            img = Image.new('RGBA', style.resolution, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype(style.font, style.font_size)
            except OSError:
                logger.warning(f"Font {style.font} not found, using default")
                font = ImageFont.load_default()
            
            # Calculate text position
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = (style.resolution[0] - text_width) // 2
            y = (style.resolution[1] - text_height) // 2
            
            # Draw text
            draw.text((x, y), text, font=font, fill=style.text_color)
            
            # Convert to numpy array for MoviePy
            return np.array(img)
            
        except Exception as e:
            logger.error(f"Error creating text image: {e}")
            raise
    
    def _process_scene(self, scene: Dict, style: VideoStyle, audio_path: Optional[str] = None) -> Optional[CompositeVideoClip]:
        """Process a single scene."""
        try:
            duration = scene.get('duration', 5)
            
            # Create background
            bg_color = style.background_color
            if bg_color.startswith('#'):
                bg_color = bg_color[1:]
            rgb_color = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
            
            bg_clip = ColorClip(size=style.resolution, color=rgb_color, duration=duration)
            clips = [bg_clip]
            
            # Add text elements
            text_elements = scene.get('text', '').split('\n')
            for j, text in enumerate(text_elements):
                if not text.strip():
                    continue
                    
                try:
                    y_pos = style.text_margin + (j * (style.font_size + 10))
                    text_clip = TextClip(
                        text,
                        fontsize=style.font_size,
                        color=style.text_color,
                        font=style.font,
                        size=style.resolution,
                        method='caption',
                        align='center'
                    )
                    text_clip = text_clip.set_duration(duration)
                    text_clip = text_clip.set_position(('center', y_pos))
                    clips.append(text_clip)
                except Exception as e:
                    logger.warning(f"Error creating text clip, trying PIL alternative: {e}")
                    try:
                        text_array = self.create_text_image(text, style)
                        pil_text_clip = ImageClip(text_array)
                        pil_text_clip = pil_text_clip.set_duration(duration)
                        pil_text_clip = pil_text_clip.set_position(('center', y_pos))
                        clips.append(pil_text_clip)
                    except Exception as e2:
                        logger.error(f"Error with PIL alternative: {e2}")
                        continue
            
            # Create scene clip
            scene_clip = CompositeVideoClip(clips, size=style.resolution)
            scene_clip = scene_clip.set_duration(duration)
            
            # Add audio if available
            if audio_path and os.path.exists(audio_path):
                try:
                    audio = AudioFileClip(audio_path)
                    scene_clip = scene_clip.set_audio(audio)
                except Exception as e:
                    logger.error(f"Error adding audio to scene: {e}")
            
            return scene_clip
            
        except Exception as e:
            logger.error(f"Error processing scene: {e}")
            return None
    
    def process_video(self, scenes: List[Dict], audio_files: Union[str, List[str]], style_name: str = "modern") -> Optional[str]:
        """Process scenes into a video.
        
        Args:
            scenes: List of scene dictionaries with text and metadata
            audio_files: Single audio file path or list of audio file paths (one per scene)
            style_name: Name of the video style to use
        
        Returns:
            Path to the generated video file, or None if processing failed
        """
        if not scenes:
            logger.error("No scenes provided")
            return None
            
        try:
            style = VideoStyle.get_style(style_name)
            scene_clips = []
            
            logger.info(f"Processing {len(scenes)} scenes with {style_name} style")
            
            # Process scenes in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_scene = {
                    executor.submit(
                        self._process_scene,
                        scene,
                        style,
                        audio_files[i] if isinstance(audio_files, list) and i < len(audio_files) else None
                    ): i for i, scene in enumerate(scenes)
                }
                
                for future in as_completed(future_to_scene):
                    scene_idx = future_to_scene[future]
                    try:
                        scene_clip = future.result()
                        if scene_clip:
                            scene_clips.append((scene_idx, scene_clip))
                            logger.info(f"Scene {scene_idx + 1} processed successfully")
                        else:
                            logger.error(f"Failed to process scene {scene_idx + 1}")
                    except Exception as e:
                        logger.error(f"Error processing scene {scene_idx + 1}: {e}")
            
            if not scene_clips:
                logger.error("No valid scene clips generated")
                return None
            
            # Sort clips by original index
            scene_clips.sort(key=lambda x: x[0])
            final_clips = [clip for _, clip in scene_clips]
            
            logger.info(f"Combining {len(final_clips)} clips into final video")
            final_video = concatenate_videoclips(final_clips)
            
            # Add global audio if provided as single file
            if isinstance(audio_files, str) and os.path.exists(audio_files):
                try:
                    audio = AudioFileClip(audio_files)
                    final_video = final_video.set_audio(audio)
                    logger.info("Added global audio to video")
                except Exception as e:
                    logger.error(f"Error adding global audio: {e}")
            
            # Generate output filename
            timestamp = int(time.time())
            resolution_name = style._resolution.name.replace(' ', '')
            output_file = os.path.join(
                self.output_dir,
                f"video_{style_name}_{resolution_name}_{timestamp}.mp4"
            )
            
            # Write video file
            final_video.write_videofile(
                output_file,
                fps=style.fps,
                codec='libx264',
                audio_codec='aac'
            )
            
            logger.info(f"Video saved to: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return None
