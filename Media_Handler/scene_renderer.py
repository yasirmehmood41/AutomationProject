"""Scene rendering module with NLP-aware text processing."""
import logging
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, ImageClip
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
    def __init__(self, resolution: Tuple[int, int], font: str = "Arial", default_font_size: int = 36):
        """Initialize scene renderer.
        
        Args:
            resolution: Video resolution (width, height)
            font: Font name to use
            default_font_size: Default font size for text
        """
        self.resolution = resolution
        self.font_name = font
        self.default_font_size = default_font_size
        self.min_margin = 20
        self.line_spacing = 1.5
        
        # Load font
        try:
            self.font = ImageFont.truetype(font, default_font_size)
        except OSError:
            logger.warning(f"Font {font} not found, using default")
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
            # Set clip duration
            duration = element.duration or scene_duration
            
            # Calculate position
            if isinstance(element.position[1], (int, float)):
                y_pos = element.position[1]
            else:
                logger.warning("Invalid y_position, using fallback")
                y_pos = None
                
            x_pos, y_pos = self._calculate_text_position(element.text, y_pos)
            
            # Create text clip
            text_clip = TextClip(
                element.text,
                fontsize=element.font_size,
                color=element.highlight_color if element.is_highlighted else element.color,
                font=self.font_name,
                size=self.resolution,
                method='caption',
                align='center'
            )
            
            # Set duration and position
            text_clip = text_clip.set_duration(duration)
            text_clip = text_clip.set_position((x_pos, y_pos))
            
            return text_clip
            
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
    
    def render_scene(
        self,
        scene: Dict,
        style: Optional[Dict] = None
    ) -> Optional[CompositeVideoClip]:
        """Render a scene with NLP-aware text elements.
        
        Args:
            scene: Scene data dictionary with NLP metadata
            style: Style configuration dictionary
            
        Returns:
            CompositeVideoClip object or None if rendering fails
        """
        try:
            # Get scene properties
            duration = scene.get('duration', 5.0)
            bg_color = style.get('background_color', '#000000') if style else '#000000'
            
            # Create background clip
            if bg_color.startswith('#'):
                bg_color = bg_color[1:]
            rgb_color = tuple(int(bg_color[i:i+2], 16) for i in (0, 2, 4))
            bg_clip = ColorClip(size=self.resolution, color=rgb_color, duration=duration)
            
            clips = [bg_clip]
            
            # Get scene text and metadata
            text = scene.get('text', '')
            entities = scene.get('entities', [])
            topics = scene.get('topics', [])
            
            if not text:
                logger.error("Scene has no text content")
                return None
            
            # Process text with NLP metadata
            text_elements = self._process_text_with_entities(text, entities, topics)
            
            # Create clips for each text element
            for element in text_elements:
                text_clip = self.create_text_clip(element, duration)
                if text_clip:
                    clips.append(text_clip)
            
            # Create composite clip
            if len(clips) > 1:
                return CompositeVideoClip(clips, size=self.resolution)
            else:
                logger.error("No text clips were created")
                return None
                
        except Exception as e:
            logger.error(f"Error rendering scene: {e}")
            return None

# TODO: Add unit tests for text element rendering and entity/topic highlighting.
