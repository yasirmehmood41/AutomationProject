"""Scene rendering module with NLP-aware text processing."""
import logging
import os
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ColorClip, CompositeVideoClip, ImageClip, TextClip
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TextElement:
    """Text element configuration for scene rendering.
    
    TODO: Add support for text animation, font fallback, and multi-language rendering.
    """
    text: str
    position: Tuple[str, int] = ('center', 0)
    font_size: int = 36
    color: str = "white"
    highlight_color: str = "#FFFF00"
    is_highlighted: bool = False
    duration: Optional[float] = None
    entities: List[Dict] = None  # NLP entities
    topics: List[str] = None     # NLP topics

class SceneRenderer:
    """Scene renderer with NLP-aware text processing.
    
    TODO: Add support for additional rendering effects, overlays, and error handling for all rendering steps.
    """
    def __init__(self, resolution: Tuple[int, int], font: str = None, default_font_size: int = 36):
        """Initialize scene renderer.
        
        Args:
            resolution: Video resolution (width, height)
            font: Font name to use
            default_font_size: Default font size for text
        """
        self.resolution = resolution
        self.default_font_size = default_font_size
        self.min_margin = 20
        self.line_spacing = 1.5
        # Use bundled font if not provided
        if font is None:
            font = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf')
        self.font_name = font
        try:
            self.font = ImageFont.truetype(font, default_font_size)
            logger.info(f"Loaded font: {font}")
        except OSError as e:
            logger.warning(f"Font {font} not found or error: {e}, using default")
            self.font = ImageFont.load_default()
    
    def _process_text_with_entities(
        self,
        text: str,
        entities: List[Dict],
        topics: List[str]
    ) -> List[TextElement]:
        """Process text with NLP entities to create text elements.
        
        Args:
            text: Raw text content
            entities: List of NLP entities
            topics: List of main topics
            
        Returns:
            List of text elements with highlighting
        """
        elements = []
        
        # Create initial text element
        base_element = TextElement(
            text=text,
            position=('center', self.min_margin)
        )
        elements.append(base_element)
        
        # Add entity highlights if available
        if entities:
            y_pos = self.min_margin + self.default_font_size * 2
            for entity in entities[:3]:  # Show top 3 entities
                if entity['label'] in ['PERSON', 'ORG', 'GPE']:
                    element = TextElement(
                        text=f"{entity['label']}: {entity['text']}",
                        position=('center', y_pos),
                        font_size=int(self.default_font_size * 0.8),
                        is_highlighted=True
                    )
                    elements.append(element)
                    y_pos += int(self.default_font_size * 1.2)
        
        # Add topics if available
        if topics:
            y_pos = self.resolution[1] - self.min_margin - len(topics) * self.default_font_size
            for topic in topics[:2]:  # Show top 2 topics
                element = TextElement(
                    text=f"Topic: {topic}",
                    position=('center', y_pos),
                    font_size=int(self.default_font_size * 0.7),
                    color="#CCCCCC"
                )
                elements.append(element)
                y_pos += int(self.default_font_size * 1.2)
        
        return elements
    
    def create_text_clip(
        self,
        element: TextElement,
        scene_duration: float
    ) -> Optional[TextClip]:
        """Create a text clip with proper positioning and highlighting.
        
        Args:
            element: Text element configuration
            scene_duration: Duration of the scene
            
        Returns:
            TextClip object or None if creation fails
        """
        try:
            duration = element.duration or scene_duration
            if isinstance(element.position[1], (int, float)):
                y_pos = element.position[1]
            else:
                logger.warning("Invalid y_position, using fallback")
                y_pos = None
            x_pos, y_pos = self._calculate_text_position(element.text, y_pos)
            try:
                text_clip = TextClip(
                    element.text,
                    fontsize=element.font_size,
                    color=element.highlight_color if element.is_highlighted else element.color,
                    font=self.font_name,
                    size=self.resolution,
                    method='caption',
                    align='center',
                    stroke_color='black',
                    stroke_width=2
                ).set_duration(duration).set_position((x_pos, y_pos))
                logger.info(f"TextClip created successfully: '{element.text}' at {(x_pos, y_pos)}")
                return text_clip
            except Exception as e:
                logger.error(f"TextClip failed for '{element.text}' with font '{self.font_name}': {e}")
                # PIL fallback
                try:
                    img = Image.new('RGBA', self.resolution, (0,0,0,0))
                    draw = ImageDraw.Draw(img)
                    font = self.font
                    text_color = element.highlight_color if element.is_highlighted else element.color
                    # Draw outline for contrast
                    outline_range = 2
                    for ox in range(-outline_range, outline_range+1):
                        for oy in range(-outline_range, outline_range+1):
                            if ox != 0 or oy != 0:
                                draw.text((x_pos+ox, y_pos+oy), element.text, font=font, fill='black')
                    draw.text((x_pos, y_pos), element.text, font=font, fill=text_color)
                    np_img = np.array(img)
                    text_clip = ImageClip(np_img).set_duration(duration).set_position((0,0))
                    logger.info(f"PIL fallback text rendered for '{element.text}' at {(x_pos, y_pos)}")
                    return text_clip
                except Exception as pil_e:
                    logger.error(f"PIL fallback failed for '{element.text}': {pil_e}")
                    return None
        except Exception as e:
            logger.error(f"Error creating text clip: {e}")
            return None
    
    def _calculate_text_position(
        self,
        text: str,
        y_pos: Optional[int] = None,
        margin: int = 50
    ) -> Tuple[int, int]:
        """Calculate text position ensuring it's within bounds.
        
        Args:
            text: Text to position
            y_pos: Vertical position (optional)
            margin: Margin from edges
            
        Returns:
            (x, y) position tuple
        """
        # Create temporary image to measure text
        img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(img)
        
        # Get text size
        text_bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Calculate x position (centered)
        x_pos = (self.resolution[0] - text_width) // 2
        
        # Calculate y position
        if y_pos is None:
            # Default to vertical center if not specified
            y_pos = (self.resolution[1] - text_height) // 2
        else:
            # Ensure y_pos is within bounds
            min_y = margin
            max_y = self.resolution[1] - text_height - margin
            y_pos = max(min_y, min(y_pos, max_y))
        
        return (x_pos, y_pos)
    
    def create_overlay(self, *args, **kwargs):
        # DEPRECATED: Overlay bar removed.
        return None

    def render_scene_with_overlay(self, scene, duration, title, author, logo_bytes=None, slogan=None, overlay_color=None, watermark_bytes=None, animate=False, style=None, subtitle_position='center'):
        # DEPRECATED: No overlay bar. Use direct overlays only if present.
        return self.render_scene(scene, style, subtitle_position)

    def render_scene(
        self,
        scene: Dict,
        style: Optional[Dict] = None,
        subtitle_position: str = 'center',  # NEW: user-selectable subtitle position
        debug: bool = False
    ) -> Optional[CompositeVideoClip]:
        """Render a scene with NLP-aware text elements.
        
        Args:
            scene: Scene data dictionary with NLP metadata
            style: Style configuration dictionary
            subtitle_position: 'center' or 'bottom'
            debug: Debug mode flag
        
        Returns:
            CompositeVideoClip object or None if rendering fails
        """
        try:
            from moviepy.editor import TextClip, ImageClip
            import io
            from PIL import Image as PILImage
            import numpy as np
            if style is None:
                style = {}
            # Ensure resolution is always present
            resolution = style.get('resolution', getattr(self, 'resolution', (1920, 1080)))
            # Get scene properties
            duration = scene.get('duration', 5.0)
            # --- Background rendering ---
            bg = scene.get('background', {})
            bg_type = bg.get('type')
            bg_value = bg.get('value')
            background_clip = None
            debug_bg = (255, 255, 0)  # bright yellow
            
            # Use safe summaries for debug prints to avoid binary data in output
            def _summarize_scene(scene):
                summary = {}
                for k, v in scene.items():
                    if isinstance(v, (bytes, bytearray)):
                        summary[k] = f"<bytes, length={len(v)}>"
                    else:
                        summary[k] = v
                return summary
            
            overlay_logo_bytes = scene.get('overlay_logo_bytes')
            if isinstance(overlay_logo_bytes, (bytes, bytearray)):
                print(f"[DIAG] overlay_logo_bytes received: type={type(overlay_logo_bytes)}, length={len(overlay_logo_bytes)}")
            else:
                print(f"[DIAG] overlay_logo_bytes received: type={type(overlay_logo_bytes)}, value={overlay_logo_bytes}")
            
            print("[DIAG] overlay_title:", scene.get('overlay_title'))
            print("[DIAG] overlay_author:", scene.get('overlay_author'))
            print("[DIAG] overlay_slogan:", scene.get('overlay_slogan'))
            
            overlay_watermark_bytes = scene.get('overlay_watermark_bytes')
            if isinstance(overlay_watermark_bytes, (bytes, bytearray)):
                print(f"[DIAG] overlay_watermark_bytes received: type={type(overlay_watermark_bytes)}, length={len(overlay_watermark_bytes)}")
            else:
                print(f"[DIAG] overlay_watermark_bytes received: type={type(overlay_watermark_bytes)}, value={overlay_watermark_bytes}")
            
            print("[DIAG] background type/value:", bg_type, bg_value)
            if debug:
                background_clip = ColorClip(size=resolution, color=debug_bg, duration=duration)
            elif bg_type == 'color' and bg_value:
                def hex_to_rgb(hex_color):
                    hex_color = hex_color.lstrip('#')
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                default_bg = (30, 30, 30)  # dark gray
                bg_val = bg_value
                if isinstance(bg_val, str) and bg_val.startswith('#'):
                    try:
                        bg_val = hex_to_rgb(bg_val)
                    except Exception:
                        bg_val = default_bg
                if not (isinstance(bg_val, tuple) and len(bg_val) == 3):
                    bg_val = default_bg
                background_clip = ColorClip(size=resolution, color=bg_val, duration=duration)
            elif bg_type == 'image' and bg_value:
                background_clip = ImageClip(bg_value).set_duration(duration).resize(resolution)
            elif bg_type == 'api' and bg_value:
                if bg_value.startswith('http'):
                    background_clip = ImageClip(bg_value).set_duration(duration).resize(resolution)
            elif bg_type == 'upload' and bg_value:
                print("[DIAG] Loading uploaded background image:", _summarize_scene({'bg_value': bg_value})['bg_value'])
                background_clip = ImageClip(bg_value).set_duration(duration).resize(resolution)
            if not background_clip:
                default_bg = (30, 30, 30)  # dark gray
                background_clip = ColorClip(size=resolution, color=default_bg, duration=duration)
            # --- PROFESSIONAL OVERLAY LOGIC ---
            clips = [background_clip]
            duration = float(duration)
            # 1. Logo (top-right, semi-transparent)
            if overlay_logo_bytes:
                try:
                    logo_img = PILImage.open(io.BytesIO(overlay_logo_bytes)).convert('RGBA')
                    logo_w = int(self.resolution[0] * 0.13)
                    logo_h = int(logo_img.height * (logo_w / logo_img.width))
                    logo_img = logo_img.resize((logo_w, logo_h), PILImage.Resampling.LANCZOS)
                    arr = np.array(logo_img)
                    arr[..., 3] = (arr[..., 3].astype(np.float32) * 0.7).astype(np.uint8)  # 70% opacity
                    logo_clip = ImageClip(arr, ismask=False).set_duration(duration)
                    logo_clip = logo_clip.set_position((self.resolution[0] - logo_w - 30, 30))
                    clips.append(logo_clip)
                except Exception as e:
                    logger.error(f"[ERROR] Failed to process overlay_logo_bytes: {e}")
                    print(f"[ERROR] Failed to process overlay_logo_bytes: {e}")
                    print(f"[DEBUG] Exception type: {type(e)}")
            # 2. Title (centered, only first 5s, fade out)
            overlay_title = scene.get('overlay_title')
            if overlay_title:
                title_clip = TextClip(
                    overlay_title,
                    fontsize=int(self.default_font_size * 1.8),
                    color='white',
                    font=self.font_name,
                    size=(self.resolution[0] - 120, None),
                    method='caption',
                    align='center',
                    stroke_color='black',
                    stroke_width=3
                ).set_duration(min(5, duration)).set_position(('center', self.resolution[1]//4))
                title_clip = title_clip.crossfadeout(1.0)
                clips.append(title_clip)
            # 3. Author (bottom-left, small, semi-transparent)
            overlay_author = scene.get('overlay_author')
            if overlay_author:
                author_clip = TextClip(
                    overlay_author,
                    fontsize=int(self.default_font_size * 0.9),
                    color='white',
                    font=self.font_name,
                    size=(self.resolution[0]//2, None),
                    method='caption',
                    align='west',
                    stroke_color='black',
                    stroke_width=2
                ).set_duration(duration).set_position((30, self.resolution[1] - 90)).set_opacity(0.7)
                clips.append(author_clip)
            # 4. Slogan (bottom-left, below author, small, semi-transparent)
            overlay_slogan = scene.get('overlay_slogan')
            if overlay_slogan:
                slogan_clip = TextClip(
                    overlay_slogan,
                    fontsize=int(self.default_font_size * 0.9),
                    color='white',
                    font=self.font_name,
                    size=(self.resolution[0]//2, None),
                    method='caption',
                    align='west',
                    stroke_color='black',
                    stroke_width=2
                ).set_duration(duration).set_position((30, self.resolution[1] - 50)).set_opacity(0.7)
                clips.append(slogan_clip)
            # 5. Watermark (bottom-right, semi-transparent)
            if overlay_watermark_bytes:
                try:
                    watermark_img = PILImage.open(io.BytesIO(overlay_watermark_bytes)).convert('RGBA')
                    wm_w = int(self.resolution[0] * 0.12)
                    wm_h = int(watermark_img.height * (wm_w / watermark_img.width))
                    watermark_img = watermark_img.resize((wm_w, wm_h), PILImage.Resampling.LANCZOS)
                    arr = np.array(watermark_img)
                    arr[..., 3] = (arr[..., 3].astype(np.float32) * 0.5).astype(np.uint8)  # 50% opacity
                    watermark_clip = ImageClip(arr, ismask=False).set_duration(duration)
                    watermark_clip = watermark_clip.set_position((self.resolution[0] - wm_w - 30, self.resolution[1] - wm_h - 30))
                    clips.append(watermark_clip)
                except Exception as e:
                    logger.error(f"[ERROR] Failed to process overlay_watermark_bytes: {e}")
                    print(f"[ERROR] Failed to process overlay_watermark_bytes: {e}")
            # --- Subtitle (always visible, bottom, safe margin) ---
            y_pos = self.resolution[1] - int(self.default_font_size * 1.5) - 60
            text = scene.get('text')
            if text is None:
                text = scene.get('script', '')
            default_text_color = 'white'
            if text and text.strip():
                text_clip = TextClip(
                    text,
                    fontsize=self.default_font_size,
                    color=default_text_color,
                    font=self.font_name,
                    size=(self.resolution[0] - 80, None),
                    method='caption',
                    align='center',
                    stroke_color='black',
                    stroke_width=2
                ).set_duration(duration).set_position(('center', y_pos))
                clips.append(text_clip)
            return CompositeVideoClip(clips, size=self.resolution)
        except Exception as e:
            logger.error(f"Error rendering scene: {e}")
            return None

# TODO: Add unit tests for text element rendering and entity/topic highlighting.
