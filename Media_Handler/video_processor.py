"""Video processing module for generating video content."""
import os
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips, ImageClip
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

# Try to import image generator
try:
    from .image_generator import ImageGenerator
except ImportError:
    ImageGenerator = None
    
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
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize video processor."""
        self.config = config or {}
        self.output_dir = os.path.join("output", "videos")
        os.makedirs(self.output_dir, exist_ok=True)
        self.max_workers = os.cpu_count() or 4
        
        # Initialize image generator if available
        self.image_generator = None
        try:
            if ImageGenerator:
                self.image_generator = ImageGenerator(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize image generator: {e}")
    
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
    
    def _process_scene_metadata(self, scene: Dict) -> Dict:
        """Process scene metadata to extract useful information for video generation.
        
        Args:
            scene: Scene data dictionary
            
        Returns:
            Processed scene data
        """
        processed = scene.copy()
        
        # Extract entities if available
        entities = scene.get('entities', [])
        if entities:
            # Collect person names for potential highlighting
            person_names = [
                ent['text'] for ent in entities 
                if ent['label'] == 'PERSON'
            ]
            if person_names:
                processed['highlight_words'] = person_names
            
            # Get locations for potential scene context
            locations = [
                ent['text'] for ent in entities 
                if ent['label'] in ['GPE', 'LOC']
            ]
            if locations:
                processed['locations'] = locations
        
        # Use topics for scene context
        topics = scene.get('topics', [])
        if topics:
            processed['key_topics'] = topics[:3]  # Top 3 topics
        
        return processed

    def _generate_scene_image(self, scene: Dict, style_name: str) -> Optional[str]:
        """Generate an image for a scene based on visual prompts.
        
        Args:
            scene: Scene data
            style_name: Visual style name
            
        Returns:
            Path to generated image or None
        """
        if not self.image_generator:
            return None
            
        try:
            # Extract visual prompt from scene data
            visual_prompt = scene.get('visual_prompt')
            if not visual_prompt:
                # Use text content if no visual prompt is available
                text = scene.get('text', '')
                if not text:
                    return None
                    
                # Use scene title or topics as fallback
                title = scene.get('title', '')
                topics = scene.get('key_topics', [])
                visual_prompt = f"{title} {' '.join(topics)} {text[:100]}"
                
            # Generate image using the prompt
            image_path = self.image_generator.generate_image(
                prompt=visual_prompt,
                style=style_name,
                cache_key=f"scene_{hash(visual_prompt)}.png"
            )
            
            # Add scene text as overlay if configured
            if image_path and self.config.get('scene', {}).get('overlay_text', False):
                text = scene.get('text', '')
                if text:
                    # Truncate if too long
                    if len(text) > 150:
                        text = text[:147] + "..."
                    image_path = self.image_generator.enhance_image(
                        image_path,
                        style=style_name,
                        overlay_text=text
                    )
                    
            return image_path
            
        except Exception as e:
            logger.error(f"Error generating scene image: {e}")
            return None
            
    def _create_background_clip(self, scene: Dict, style: VideoStyle, duration: float) -> ImageClip or ColorClip:
        """Create background clip based on scene data and style.
        
        Args:
            scene: Scene data
            style: Video style
            duration: Clip duration
            
        Returns:
            Background clip (either image or color)
        """
        # Try to create image background if we have an image generator
        if self.image_generator:
            image_path = self._generate_scene_image(scene, style.name.lower())
            if image_path and os.path.exists(image_path):
                try:
                    img_clip = ImageClip(image_path)
                    img_clip = img_clip.resize(style.resolution)
                    img_clip = img_clip.set_duration(duration)
                    return img_clip
                except Exception as e:
                    logger.error(f"Error creating image clip: {e}")
                    
        # Fallback to color background
        bg_color = style.background_color
        if bg_color.startswith('#'):
            bg_color = bg_color[1:]
        rgb_color = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
        
        return ColorClip(size=style.resolution, color=rgb_color, duration=duration)

    def _process_scene(self, scene: Dict, style: VideoStyle, audio_path: Optional[str] = None) -> Optional[CompositeVideoClip]:
        """Process a single scene."""
        try:
            duration = scene.get('duration', 5)
            
            # Create background (either image or color)
            bg_clip = self._create_background_clip(scene, style, duration)
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
            
            # Apply transition if specified in scene
            transition = scene.get('transition', 'fade')
            if transition == 'fade':
                # Add fade in/out
                fade_duration = min(0.5, duration / 4)
                scene_clip = scene_clip.fadein(fade_duration).fadeout(fade_duration)
            
            return scene_clip
            
        except Exception as e:
            logger.error(f"Error processing scene: {e}")
            return None

    def process_video(
        self,
        scenes: List[Dict],
        audio_files: Optional[Union[str, List[str]]] = None,
        style_name: Optional[str] = "modern",
        additional_settings: Optional[Dict[str, Any]] = None,
        output_name: Optional[str] = None
    ) -> Optional[str]:
        """Process scenes into a complete video with branding, transitions, overlays, and intro/outro."""
        try:
            if not scenes:
                raise ValueError("No scenes provided")

            # --- 1. Add Intro Scene (if configured and valid) ---
            intro_path = os.path.join("assets", "intro.mp4")
            intro_clip = None
            use_intro = additional_settings.get('use_intro', False) if additional_settings else False
            if use_intro and os.path.exists(intro_path):
                try:
                    intro_clip = VideoFileClip(intro_path)
                    # Try reading duration to check validity
                    _ = intro_clip.duration
                except Exception as e:
                    logger.warning(f"Intro video found but could not be loaded: {e}. Skipping intro.")
                    intro_clip = None
            elif use_intro:
                logger.warning("Intro video requested but not found. Skipping intro.")

            # --- 2. Add Outro Scene (if configured and valid) ---
            outro_path = os.path.join("assets", "outro.mp4")
            outro_clip = None
            use_outro = additional_settings.get('use_outro', False) if additional_settings else False
            if use_outro and os.path.exists(outro_path):
                try:
                    outro_clip = VideoFileClip(outro_path)
                    _ = outro_clip.duration
                except Exception as e:
                    logger.warning(f"Outro video found but could not be loaded: {e}. Skipping outro.")
                    outro_clip = None
            elif use_outro:
                logger.warning("Outro video requested but not found. Skipping outro.")

            # --- 3. Process scene metadata ---
            processed_scenes = []
            for scene in scenes:
                processed = self._process_scene_metadata(scene)
                processed_scenes.append(processed)

            # --- 4. Style and settings ---
            style = VideoStyle.get_style(style_name)
            if additional_settings:
                # (existing style logic unchanged)
                if 'video_quality' in additional_settings:
                    quality = additional_settings['video_quality']
                    if quality in VideoStyle.RESOLUTIONS:
                        style._resolution = VideoStyle.RESOLUTIONS[quality]
                if 'resolution' in additional_settings:
                    res = additional_settings['resolution']
                    if isinstance(res, (tuple, list)) and len(res) == 2:
                        style._resolution = type(style._resolution)(
                            name=f"Custom {res[0]}x{res[1]}", width=int(res[0]), height=int(res[1])
                        )
                if 'aspect_ratio' in additional_settings:
                    style.aspect_ratio = additional_settings['aspect_ratio']
                if 'fps' in additional_settings:
                    style.fps = int(additional_settings['fps'])
                if 'bitrate' in additional_settings:
                    style.bitrate = additional_settings['bitrate']
                if 'text_style' in additional_settings and additional_settings['text_style'] != 'default':
                    text_style = additional_settings['text_style']
                    if text_style == 'minimal':
                        style.font_size = int(style.font_size * 0.9)
                    elif text_style == 'bold':
                        style.font_size = int(style.font_size * 1.2)
            
            # --- 5. Generate video clips for each scene (with overlays, watermark, transitions) ---
            clips = []
            logo_path = os.path.join("assets", "logo.png")
            use_logo = additional_settings.get('use_logo', False) if additional_settings else False
            for i, scene in enumerate(processed_scenes):
                scene_audio = None
                if isinstance(audio_files, list) and i < len(audio_files):
                    scene_audio = audio_files[i]
                elif isinstance(audio_files, str):
                    scene_audio = audio_files
                # Scene clip
                clip = self._process_scene(
                    scene,
                    style,
                    audio_path=scene_audio
                )
                if clip:
                    # --- Add watermark/logo overlay if requested and valid ---
                    if use_logo and os.path.exists(logo_path):
                        try:
                            logo = (ImageClip(logo_path)
                                    .set_duration(clip.duration)
                                    .resize(height=int(style.resolution[1]*0.08))
                                    .margin(right=10, top=10, opacity=0)
                                    .set_pos(("right", "top")))
                            clip = CompositeVideoClip([clip, logo])
                        except Exception as e:
                            logger.warning(f"Logo found but could not be loaded: {e}. Skipping logo overlay.")
                    elif use_logo:
                        logger.warning("Logo requested but not found. Skipping logo overlay.")
                    # --- Add lower-third/scene title overlay ---
                    if scene.get('title'):
                        title_txt = TextClip(scene['title'], fontsize=style.font_size, font=style.font, color=style.text_color, bg_color="#222222", size=(int(style.resolution[0]*0.7), None)).set_duration(2.5).set_pos(("center", style.resolution[1]*0.85))
                        clip = CompositeVideoClip([clip, title_txt.set_start(0)])
                    clips.append(clip)
                else:
                    logger.warning(f"Failed to create clip for scene {i+1}")

            # --- 6. Add intro/outro to clips ---
            if intro_clip:
                clips = [intro_clip] + clips
            if outro_clip:
                clips = clips + [outro_clip]

            if not clips:
                raise ValueError("No valid clips generated")

            # --- 7. Apply transitions between scenes ---
            from Media_Handler.transitions import TransitionManager
            transition_manager = TransitionManager()
            final_clips = []
            for idx, clip in enumerate(clips):
                final_clips.append(clip)
                # Add transition if not last
                if idx < len(clips)-1:
                    transition_type = style.__dict__.get('transition', 'fade')
                    transition = transition_manager.create_transition(clip, clips[idx+1], duration=style.transition_duration, type=transition_type)
                    if transition:
                        final_clips.append(transition)

            # --- 8. Concatenate all clips ---
            final_clip = concatenate_videoclips(final_clips, method="compose")
            import time
            timestamp = int(time.time())
            style = VideoStyle.get_style(style_name)
            resolution_name = style.resolution[0] if hasattr(style, 'resolution') else 'FHD'
            if output_name:
                output_path = os.path.join(self.output_dir, output_name)
                if not output_path.endswith('.mp4'):
                    output_path += '.mp4'
            else:
                output_path = os.path.join(
                    self.output_dir, 
                    f"video_{style_name}_{resolution_name}_{timestamp}.mp4"
                )
            # --- 9. Render final video ---
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                fps=style.fps,
                threads=self.max_workers,
                logger='bar',
                bitrate=getattr(style, 'bitrate', None)
            )
            logger.info(f"Video generated successfully: {output_path}")
            if os.path.exists(output_path):
                logger.info(f"Output file verified at: {output_path}")
            else:
                logger.error(f"Expected output file not found at: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return None

    def compile_video(self, scenes, audio_files=None, style_name="modern", additional_settings=None, output_name=None):
        """Alias for process_video, for compatibility."""
        return self.process_video(scenes, audio_files, style_name, additional_settings, output_name)

    def create_preview(self, scenes: List[Dict], style_name: str = "modern") -> Optional[str]:
        """Create a preview image grid for the video.
        
        Args:
            scenes: List of scene data
            style_name: Name of the video style
            
        Returns:
            Path to preview image grid
        """
        if not scenes or not self.image_generator:
            return None
            
        try:
            # Generate preview images for each scene
            preview_images = []
            for scene in scenes[:min(len(scenes), 6)]:  # Limit to 6 scenes
                image_path = self._generate_scene_image(scene, style_name)
                if image_path and os.path.exists(image_path):
                    preview_images.append(image_path)
            
            if not preview_images:
                return None
                
            # Create a grid of preview images
            grid_size = (3, 2)  # 3x2 grid
            cell_size = (640, 360)  # 16:9 aspect ratio
            
            # Create a new image for the grid
            grid_img = Image.new('RGB', 
                                (cell_size[0] * grid_size[0], 
                                 cell_size[1] * grid_size[1]))
            
            # Place each preview image in the grid
            for i, img_path in enumerate(preview_images):
                if i >= grid_size[0] * grid_size[1]:
                    break
                    
                x = (i % grid_size[0]) * cell_size[0]
                y = (i // grid_size[0]) * cell_size[1]
                
                try:
                    img = Image.open(img_path)
                    img = img.resize(cell_size)
                    grid_img.paste(img, (x, y))
                except Exception as e:
                    logger.error(f"Error adding image to preview grid: {e}")
            
            # Save the grid image
            timestamp = int(time.time())
            output_path = os.path.join(
                self.output_dir, 
                f"preview_{style_name}_{timestamp}.jpg"
            )
            grid_img.save(output_path, quality=90)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating preview: {e}")
            return None
