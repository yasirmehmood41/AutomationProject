"""Video processing module for generating video content."""
import os
import time
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips, ImageClip
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path
from moviepy.video.io.ffmpeg_writer import ffmpeg_write_video
from proglog import ProgressBarLogger
import streamlit as st
import tempfile

# Try to import image generator
try:
    from .image_generator import ImageGenerator
except ImportError:
    ImageGenerator = None
    
logger = logging.getLogger(__name__)

# TODO: Remove unused imports after full audit

@dataclass
class Resolution:
    """Video resolution configuration.
    
    Attributes:
        name: Resolution label
        width: Width in pixels
        height: Height in pixels
    """
    name: str
    width: int
    height: int
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        return (self.width, self.height)

class VideoStyle:
    """Video style configuration for customizing appearance and rendering.
    
    Attributes:
        name: Style name
        font: Font family
        font_size: Size of text
        text_color: Color for text
        background_color: Background color
        resolution: Resolution label
        fps: Frames per second
        transition_duration: Duration of transitions
        text_margin: Margin around text
    """
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
    """Video processor for generating video content.
    
    Handles scene processing, video compilation, and integration with image generation.
    """
    def __init__(self, config: Optional[Dict] = None):
        """Initialize video processor."""
        self.config = config or {}
        self.output_dir = os.path.join("output", "videos")
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
        self.max_workers = os.cpu_count() or 4
        
        # Initialize image generator if available
        self.image_generator = None
        try:
            if ImageGenerator:
                self.image_generator = ImageGenerator(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize image generator: {e}")
    
    def create_text_image(self, text: str, style: VideoStyle) -> np.ndarray:
        """Create text image using PIL. Returns numpy array."""
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
    
    def _create_text_clip(self, text: str, style: VideoStyle, duration: float, y_pos: int = None) -> ImageClip:
        """Create a text clip using PIL fallback, returns an ImageClip for MoviePy."""
        try:
            text_array = self.create_text_image(text, style)
            text_clip = ImageClip(text_array)
            text_clip = text_clip.set_duration(duration)
            if y_pos is not None:
                text_clip = text_clip.set_position(('center', y_pos))
            else:
                text_clip = text_clip.set_position('center')
            return text_clip
        except Exception as e:
            logger.error(f"Error in _create_text_clip: {e}")
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
        bg = scene.get('background', {})
        if isinstance(bg, dict):
            bg_type = bg.get('type')
            if bg_type == 'upload' and bg.get('value'):
                try:
                    return ImageClip(bg['value']).set_duration(duration).resize(style.resolution)
                except Exception as e:
                    logger.warning(f"Failed to use uploaded background: {e}")
            elif bg_type == 'api' and bg.get('value'):
                try:
                    # If value is a URL, use it directly; if a search term, fallback to color
                    if bg['value'].startswith('http'):
                        return ImageClip(bg['value']).set_duration(duration).resize(style.resolution)
                except Exception as e:
                    logger.warning(f"Failed to use API background: {e}")
            elif bg_type == 'color':
                color = bg.get('value', '#000000')
                if color.startswith('#'):
                    color = color[1:]
                rgb_color = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
                return ColorClip(size=style.resolution, color=rgb_color, duration=duration)
        # Fallback to legacy handling or default
        return ColorClip(size=style.resolution, color=(0,0,0), duration=duration)

    def _process_scene(self, scene: Dict, style: VideoStyle, audio_path: Optional[str] = None) -> Optional[CompositeVideoClip]:
        print(f"[DIAG] _process_scene called for scene: {scene.get('scene_number', '?')}")
        try:
            duration = scene.get('duration', 5)
            print(f"[DIAG] Scene duration: {duration}")
            # --- Ensure scene duration >= audio duration ---
            if audio_path and os.path.exists(audio_path):
                try:
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    if duration < audio_duration:
                        print(f"[DIAG] Adjusting scene {scene.get('scene_number','?')} duration from {duration} to audio duration {audio_duration}")
                        duration = audio_duration
                        scene['duration'] = audio_duration
                    audio_clip.close()
                except Exception as e:
                    print(f"[DIAG] Could not check audio duration for scene {scene.get('scene_number','?')}: {e}")
            # Create background (either image or color)
            bg_clip = self._create_background_clip(scene, style, duration)
            print(f"[DIAG] Background clip type: {type(bg_clip)}")
            clips = [bg_clip]
            # Add text elements
            text_elements = scene.get('text', '').split('\n')
            for i, text in enumerate(text_elements):
                if text.strip():
                    txt_clip = TextClip(
                        text,
                        fontsize=style.font_size,
                        color=style.text_color,
                        font=style.font,
                        size=style.resolution,
                        method='caption',
                        align='center'
                    ).set_duration(duration)
                    clips.append(txt_clip)
            # Compose scene
            scene_clip = CompositeVideoClip(clips, size=style.resolution).set_duration(duration)
            transition = scene.get('transition', 'fade')
            if transition == 'fade':
                # Add fade in/out
                fade_duration = min(0.5, duration / 4)
                scene_clip = scene_clip.fadein(fade_duration).fadeout(fade_duration)
                print(f"[DIAG] Applied fadein/fadeout with duration {fade_duration}")
            print(f"[DIAG] Returning scene_clip for scene {scene.get('scene_number', '?')}")
            return scene_clip
        except Exception as e:
            print(f"[DIAG] Error processing scene {scene.get('scene_number', '?')}: {e}")
            logger.error(f"Error processing scene: {e}")
            return None

    def process_video(
        self,
        scenes: List[Dict],
        audio_files: Optional[Union[str, List[str]]] = None,
        style_name: Optional[str] = "modern",
        additional_settings: Optional[Dict[str, Any]] = None,
        output_name: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> Optional[str]:
        print("[DIAG] video_processor.process_video called")
        try:
            if not scenes:
                print("[DIAG] No scenes provided for video generation. Returning None.")
                st.error("No scenes provided for video generation. Please add scenes and try again.")
                return None
            print(f"[DIAG] scenes: {scenes}")
            style = VideoStyle.get_style(style_name)
            print(f"[DIAG] Using style: {style}")
            clips = []
            voice_system = None
            try:
                from Media_Handler.voice_system import VoiceSystem
                voice_system = VoiceSystem()
                print("[DIAG] VoiceSystem instantiated for TTS.")
            except Exception as e:
                print(f"[DIAG] ERROR: Could not import or instantiate VoiceSystem: {e}")
                logger.error(f"Could not import or instantiate VoiceSystem: {e}")
            for i, scene in enumerate(scenes):
                scene_audio = None
                # Always use ONLY 'script' for narration/subtitles/overlay
                narration = scene.get('script', '').strip()
                # Remove all legacy/extra fields from scene_for_clip except allowed
                allowed_fields = {'scene_number', 'background', 'script', 'duration', 'transition'}
                scene_for_clip = {k: v for k, v in scene.items() if k in allowed_fields}
                scene_for_clip['text'] = narration
                # --- Overlay Metadata ---
                # Get overlay info from config/session or scene meta
                meta = self.config.get('meta', {})
                overlay_title = meta.get('title', '')
                overlay_author = meta.get('author', '')
                overlay_logo_bytes = meta.get('logo_bytes', None)
                overlay_slogan = meta.get('slogan', None)
                overlay_color = meta.get('overlay_color', None)
                overlay_watermark_bytes = meta.get('watermark_bytes', None)
                overlay_animate = meta.get('animate', False)
                # ---
                if narration:
                    try:
                        audio_hash = str(hash(narration + str(i)))
                        output_dir = os.path.join('.', 'Output_Manager', 'outputs')
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, f'voice_scene_{i+1}_{audio_hash}.mp3')
                        if not os.path.exists(output_file):
                            from gtts import gTTS
                            config = voice_system.config if hasattr(voice_system, 'config') else {}
                            tts_config = config.get('tts', {}) if config else {}
                            language = tts_config.get('language', 'en')
                            speed = float(tts_config.get('speed', 1.0))
                            slow = True if speed != 1.0 else False
                            tts = gTTS(text=narration, lang=language, slow=slow)
                            tts.save(output_file)
                        scene_audio = os.path.abspath(output_file)
                        print(f"[DIAG] Generated audio for scene {i+1}: {scene_audio}")
                    except Exception as e:
                        print(f"[DIAG] Error generating audio for scene {i+1}: {e}")
                        logger.error(f"Error generating audio for scene {i+1}: {e}")
                # Warn if legacy/extra fields exist
                for legacy in ['text', 'content', 'title', 'subtitle', 'narration']:
                    if legacy in scene and legacy != 'script':
                        logger.warning(f"Scene {i+1} contains legacy field '{legacy}'. It will be ignored for overlays/subtitles.")
                # Backend warning for likely background description
                if narration.lower().startswith(('show ', 'display ', 'background', 'visual')) or len(narration) > 220:
                    print(f"[WARN] Scene {i+1} narration may contain background/visual description. Please check your script field.")
                try:
                    # --- Use render_scene_with_overlay for every scene ---
                    from Media_Handler.scene_renderer import SceneRenderer
                    renderer = SceneRenderer(style.resolution, font=style.font, default_font_size=style.font_size)
                    duration = scene.get('duration', 5)
                    clip = renderer.render_scene_with_overlay(
                        scene_for_clip,
                        duration,
                        overlay_title,
                        overlay_author,
                        overlay_logo_bytes,
                        overlay_slogan,
                        overlay_color,
                        overlay_watermark_bytes,
                        overlay_animate
                    )
                    # Add audio if available
                    if clip and scene_audio:
                        from moviepy.editor import AudioFileClip
                        clip = clip.set_audio(AudioFileClip(scene_audio))
                    print(f"[DIAG] scene {i} clip: {clip}, type: {type(clip)}")
                    if clip:
                        clips.append(clip)
                    else:
                        print(f"[DIAG] Failed to create clip for scene {i}")
                except Exception as e:
                    print(f"[DIAG] Exception processing scene {i}: {e}")
            print(f"[DIAG] All clips: {clips}")
            print(f"[DIAG] Types in clips: {[type(c) for c in clips]}")
            # Defensive: filter out None
            clips = [c for c in clips if c is not None]
            if not clips:
                print("[DIAG] No valid clips to compile. Returning None.")
                return None
            print("[DIAG] About to call apply_transitions")
            try:
                from Media_Handler.transitions import TransitionManager
                transition_manager = TransitionManager()
            except Exception as e:
                print(f"[DIAG] ERROR: Could not import or instantiate TransitionManager: {e}")
                logger.error(f"Could not import or instantiate TransitionManager: {e}")
                return None
            final_clip = transition_manager.apply_transitions(clips, transition_type="fade")
            print(f"[DIAG] final_clip after transitions: {final_clip}, type: {type(final_clip)}")
            if isinstance(final_clip, list):
                print("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                logger.error("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                return None
            # --- Background Music Mixing ---
            background_music_path = None
            if additional_settings and 'background_music_path' in additional_settings:
                background_music_path = additional_settings['background_music_path']
                print(f"[DIAG] video_processor got background_music_path: {background_music_path}")
            else:
                print(f"[DIAG] video_processor got NO background_music_path")
            final_audio = None
            if background_music_path and os.path.exists(background_music_path):
                try:
                    print(f"[DIAG] Adding background music: {background_music_path}")
                    from moviepy.editor import AudioFileClip, CompositeAudioClip
                    music_clip = AudioFileClip(background_music_path).volumex(0.15)  # Lower volume for background
                    if final_clip.audio:
                        print(f"[DIAG] Video has narration audio. Mixing with background music.")
                        final_audio = CompositeAudioClip([final_clip.audio, music_clip.set_duration(final_clip.duration)])
                    else:
                        print(f"[DIAG] Video has NO narration audio. Using only background music.")
                        final_audio = music_clip.set_duration(final_clip.duration)
                    final_clip = final_clip.set_audio(final_audio)
                except Exception as e:
                    print(f"[DIAG] Failed to add background music: {e}")
            else:
                print(f"[DIAG] No valid background music file found or path does not exist: {background_music_path}")
            # --- End Background Music Mixing ---
            # Clean up old temp video files (>5 min)
            temp_dir = tempfile.gettempdir()
            now = time.time()
            for fname in os.listdir(temp_dir):
                if fname.endswith('.mp4') and fname.startswith('tmp'):
                    fpath = os.path.join(temp_dir, fname)
                    try:
                        if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 300:
                            os.remove(fpath)
                    except Exception:
                        pass
            # Write new video to a temp file
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            output_path = temp_video.name
            temp_video.close()
            print(f"[DIAG] Writing video file to {output_path}. final_clip type: {type(final_clip)}")
            try:
                final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=4, fps=style.fps)
            except Exception as e:
                print(f"[DIAG] Error writing video file: {e}")
                logger.error(f"Error writing video file: {e}")
                return None
            print(f"[DIAG] Video file written: {output_path}")
            return output_path
        except Exception as e:
            print(f"[DIAG] Error in process_video: {e}")
            logger.error(f"Error in process_video: {e}")
            return None

    def compile_video(self, scenes, audio_files=None, style_name="modern", additional_settings=None, output_name=None, logger=None):
        print("[DIAG] video_processor.compile_video called with additional_settings:", additional_settings, flush=True)
        result = self.process_video(scenes, audio_files, style_name, additional_settings, output_name, logger=logger)
        print("[DIAG] video_processor.compile_video done", flush=True)
        return result

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

# TODO: Review and complete all method implementations. Add robust error handling and logging for all file operations and external calls.

    def process_video(
        self,
        scenes: List[Dict],
        audio_files: Optional[Union[str, List[str]]] = None,
        style_name: Optional[str] = "modern",
        additional_settings: Optional[Dict[str, Any]] = None,
        output_name: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> Optional[str]:
        print("[DIAG] video_processor.process_video called")
        try:
            if not scenes:
                print("[DIAG] No scenes provided for video generation. Returning None.")
                st.error("No scenes provided for video generation. Please add scenes and try again.")
                return None
            print(f"[DIAG] scenes: {scenes}")
            style = VideoStyle.get_style(style_name)
            print(f"[DIAG] Using style: {style}")
            clips = []
            voice_system = None
            try:
                from Media_Handler.voice_system import VoiceSystem
                voice_system = VoiceSystem()
                print("[DIAG] VoiceSystem instantiated for TTS.")
            except Exception as e:
                print(f"[DIAG] ERROR: Could not import or instantiate VoiceSystem: {e}")
                logger.error(f"Could not import or instantiate VoiceSystem: {e}")
            for i, scene in enumerate(scenes):
                scene_audio = None
                # Always use ONLY 'script' for narration/subtitles/overlay
                narration = scene.get('script', '').strip()
                # Remove all legacy/extra fields from scene_for_clip except allowed
                allowed_fields = {'scene_number', 'background', 'script', 'duration', 'transition'}
                scene_for_clip = {k: v for k, v in scene.items() if k in allowed_fields}
                scene_for_clip['text'] = narration
                # --- Overlay Metadata ---
                # Get overlay info from config/session or scene meta
                meta = self.config.get('meta', {})
                overlay_title = meta.get('title', '')
                overlay_author = meta.get('author', '')
                overlay_logo_bytes = meta.get('logo_bytes', None)
                overlay_slogan = meta.get('slogan', None)
                overlay_color = meta.get('overlay_color', None)
                overlay_watermark_bytes = meta.get('watermark_bytes', None)
                overlay_animate = meta.get('animate', False)
                # ---
                if narration:
                    try:
                        audio_hash = str(hash(narration + str(i)))
                        output_dir = os.path.join('.', 'Output_Manager', 'outputs')
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, f'voice_scene_{i+1}_{audio_hash}.mp3')
                        if not os.path.exists(output_file):
                            from gtts import gTTS
                            config = voice_system.config if hasattr(voice_system, 'config') else {}
                            tts_config = config.get('tts', {}) if config else {}
                            language = tts_config.get('language', 'en')
                            speed = float(tts_config.get('speed', 1.0))
                            slow = True if speed != 1.0 else False
                            tts = gTTS(text=narration, lang=language, slow=slow)
                            tts.save(output_file)
                        scene_audio = os.path.abspath(output_file)
                        print(f"[DIAG] Generated audio for scene {i+1}: {scene_audio}")
                    except Exception as e:
                        print(f"[DIAG] Error generating audio for scene {i+1}: {e}")
                        logger.error(f"Error generating audio for scene {i+1}: {e}")
                # Warn if legacy/extra fields exist
                for legacy in ['text', 'content', 'title', 'subtitle', 'narration']:
                    if legacy in scene and legacy != 'script':
                        logger.warning(f"Scene {i+1} contains legacy field '{legacy}'. It will be ignored for overlays/subtitles.")
                # Backend warning for likely background description
                if narration.lower().startswith(('show ', 'display ', 'background', 'visual')) or len(narration) > 220:
                    print(f"[WARN] Scene {i+1} narration may contain background/visual description. Please check your script field.")
                try:
                    # --- Use render_scene_with_overlay for every scene ---
                    from Media_Handler.scene_renderer import SceneRenderer
                    renderer = SceneRenderer(style.resolution, font=style.font, default_font_size=style.font_size)
                    duration = scene.get('duration', 5)
                    clip = renderer.render_scene_with_overlay(
                        scene_for_clip,
                        duration,
                        overlay_title,
                        overlay_author,
                        overlay_logo_bytes,
                        overlay_slogan,
                        overlay_color,
                        overlay_watermark_bytes,
                        overlay_animate
                    )
                    # Add audio if available
                    if clip and scene_audio:
                        from moviepy.editor import AudioFileClip
                        clip = clip.set_audio(AudioFileClip(scene_audio))
                    print(f"[DIAG] scene {i} clip: {clip}, type: {type(clip)}")
                    if clip:
                        clips.append(clip)
                    else:
                        print(f"[DIAG] Failed to create clip for scene {i}")
                except Exception as e:
                    print(f"[DIAG] Exception processing scene {i}: {e}")
            print(f"[DIAG] All clips: {clips}")
            print(f"[DIAG] Types in clips: {[type(c) for c in clips]}")
            # Defensive: filter out None
            clips = [c for c in clips if c is not None]
            if not clips:
                print("[DIAG] No valid clips to compile. Returning None.")
                return None
            print("[DIAG] About to call apply_transitions")
            try:
                from Media_Handler.transitions import TransitionManager
                transition_manager = TransitionManager()
            except Exception as e:
                print(f"[DIAG] ERROR: Could not import or instantiate TransitionManager: {e}")
                logger.error(f"Could not import or instantiate TransitionManager: {e}")
                return None
            final_clip = transition_manager.apply_transitions(clips, transition_type="fade")
            print(f"[DIAG] final_clip after transitions: {final_clip}, type: {type(final_clip)}")
            if isinstance(final_clip, list):
                print("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                logger.error("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                return None
            # --- Background Music Mixing ---
            background_music_path = None
            if additional_settings and 'background_music_path' in additional_settings:
                background_music_path = additional_settings['background_music_path']
                print(f"[DIAG] video_processor got background_music_path: {background_music_path}")
            else:
                print(f"[DIAG] video_processor got NO background_music_path")
            final_audio = None
            if background_music_path and os.path.exists(background_music_path):
                try:
                    print(f"[DIAG] Adding background music: {background_music_path}")
                    from moviepy.editor import AudioFileClip, CompositeAudioClip
                    music_clip = AudioFileClip(background_music_path).volumex(0.15)  # Lower volume for background
                    if final_clip.audio:
                        print(f"[DIAG] Video has narration audio. Mixing with background music.")
                        final_audio = CompositeAudioClip([final_clip.audio, music_clip.set_duration(final_clip.duration)])
                    else:
                        print(f"[DIAG] Video has NO narration audio. Using only background music.")
                        final_audio = music_clip.set_duration(final_clip.duration)
                    final_clip = final_clip.set_audio(final_audio)
                except Exception as e:
                    print(f"[DIAG] Failed to add background music: {e}")
            else:
                print(f"[DIAG] No valid background music file found or path does not exist: {background_music_path}")
            # --- End Background Music Mixing ---
            # Clean up old temp video files (>5 min)
            temp_dir = tempfile.gettempdir()
            now = time.time()
            for fname in os.listdir(temp_dir):
                if fname.endswith('.mp4') and fname.startswith('tmp'):
                    fpath = os.path.join(temp_dir, fname)
                    try:
                        if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 300:
                            os.remove(fpath)
                    except Exception:
                        pass
            # Write new video to a temp file
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            output_path = temp_video.name
            temp_video.close()
            print(f"[DIAG] Writing video file to {output_path}. final_clip type: {type(final_clip)}")
            try:
                final_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=4, fps=style.fps)
            except Exception as e:
                print(f"[DIAG] Error writing video file: {e}")
                logger.error(f"Error writing video file: {e}")
                return None
            print(f"[DIAG] Video file written: {output_path}")
            return output_path
        except Exception as e:
            print(f"[DIAG] Error in process_video: {e}")
            logger.error(f"Error in process_video: {e}")
            return None

    def compile_video(self, scenes, audio_files=None, style_name="modern", additional_settings=None, output_name=None, logger=None):
        print("[DIAG] video_processor.compile_video called with additional_settings:", additional_settings, flush=True)
        result = self.process_video(scenes, audio_files, style_name, additional_settings, output_name, logger=logger)
        print("[DIAG] video_processor.compile_video done", flush=True)
        return result

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

# TODO: Review and complete all method implementations. Add robust error handling and logging for all file operations and external calls.
