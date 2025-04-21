"""Core video logic module."""
import os
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import json
from Media_Handler.scene_renderer import SceneRenderer
from Media_Handler.voice_system import VoiceSystem

logger = logging.getLogger(__name__)

@dataclass
class VideoConfig:
    """Video configuration."""
    style_name: str = "modern"
    resolution: str = "FHD"
    voice_id: Optional[str] = None
    output_dir: str = "output_manager/videos"
    debug_mode: bool = False

class VideoLogic:
    """Core video logic handler."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize video logic.
        
        Args:
            config: Configuration dictionary
        """
        self.config = VideoConfig()
        if config:
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Initialize components
        self.voice_system = VoiceSystem()
        self.scene_renderer = None  # Will be initialized when style is set
        
        # Debug data
        self.debug_data = {
            'highlighted_words': [],
            'skipped_scenes': [],
            'rendering_errors': []
        }
    
    def _init_scene_renderer(self, style: Dict) -> None:
        """Initialize scene renderer with style settings."""
        resolution = style.get('resolution', (1920, 1080))
        font = style.get('font', 'Arial')
        font_size = style.get('font_size', 36)
        
        self.scene_renderer = SceneRenderer(
            resolution=resolution,
            font=font,
            default_font_size=font_size
        )
    
    def _extract_highlighted_words(self, text: str) -> List[str]:
        """Extract words to highlight from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of words to highlight
        """
        # Simple word extraction (can be enhanced with NLP)
        words = []
        for word in text.split():
            # Remove punctuation
            word = word.strip('.,!?()[]{}":;')
            if len(word) > 3:  # Only highlight words longer than 3 chars
                words.append(word)
        
        if not words and self.config.debug_mode:
            logger.debug("No words extracted for highlighting")
            
        return words
    
    def _save_debug_info(self, scene_number: int, data: Dict) -> None:
        """Save debug information if debug mode is enabled."""
        if not self.config.debug_mode:
            return
            
        debug_file = os.path.join(self.config.output_dir, 'debug_info.json')
        self.debug_data['scenes'] = self.debug_data.get('scenes', {})
        self.debug_data['scenes'][scene_number] = data
        
        try:
            with open(debug_file, 'w') as f:
                json.dump(self.debug_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save debug info: {e}")
    
    def process_scene(
        self,
        scene: Dict,
        style: Dict,
        audio_file: Optional[str] = None
    ) -> Optional[Dict]:
        """Process a single scene.
        
        Args:
            scene: Scene data dictionary
            style: Style configuration
            audio_file: Path to audio file for this scene
            
        Returns:
            Processed scene data or None if processing fails
        """
        try:
            # Initialize scene renderer if needed
            if not self.scene_renderer:
                self._init_scene_renderer(style)
            
            # Extract text for highlighting
            scene_text = scene.get('text', '')
            if not scene_text:
                if self.config.debug_mode:
                    logger.debug(f"Scene {scene.get('scene_number', '?')} has no text")
                    self.debug_data['skipped_scenes'].append(scene.get('scene_number', '?'))
                return None
            
            # Extract words to highlight
            highlighted_words = self._extract_highlighted_words(scene_text)
            if self.config.debug_mode:
                logger.debug(f"Extracted {len(highlighted_words)} words for highlighting")
                self.debug_data['highlighted_words'].extend(highlighted_words)
            
            # Render scene
            rendered_scene = self.scene_renderer.render_scene(
                scene=scene,
                highlighted_words=highlighted_words,
                style=style
            )
            
            if not rendered_scene:
                if self.config.debug_mode:
                    logger.debug(f"Failed to render scene {scene.get('scene_number', '?')}")
                    self.debug_data['rendering_errors'].append({
                        'scene': scene.get('scene_number', '?'),
                        'error': 'Rendering failed'
                    })
                return None
            
            # Add audio if provided
            if audio_file and os.path.exists(audio_file):
                try:
                    rendered_scene = rendered_scene.set_audio(audio_file)
                except Exception as e:
                    logger.error(f"Failed to add audio to scene: {e}")
                    if self.config.debug_mode:
                        self.debug_data['rendering_errors'].append({
                            'scene': scene.get('scene_number', '?'),
                            'error': f'Audio error: {str(e)}'
                        })
            
            # Save debug info
            if self.config.debug_mode:
                self._save_debug_info(scene.get('scene_number', 0), {
                    'text': scene_text,
                    'highlighted_words': highlighted_words,
                    'has_audio': bool(audio_file)
                })
            
            return {
                **scene,
                'rendered': rendered_scene,
                'highlighted_words': highlighted_words
            }
            
        except Exception as e:
            logger.error(f"Error processing scene: {e}")
            if self.config.debug_mode:
                self.debug_data['rendering_errors'].append({
                    'scene': scene.get('scene_number', '?'),
                    'error': str(e)
                })
            return None
    
    def process_video(
        self,
        scenes: List[Dict],
        style: Dict,
        audio_files: Optional[Union[str, List[str]]] = None
    ) -> Optional[str]:
        """Process scenes into a complete video.
        
        Args:
            scenes: List of scene dictionaries
            style: Style configuration dictionary
            audio_files: Single audio file or list of audio files (one per scene)
            
        Returns:
            Path to the generated video file, or None if processing fails
        """
        try:
            processed_scenes = []
            
            for i, scene in enumerate(scenes):
                # Get audio file for this scene
                scene_audio = None
                if isinstance(audio_files, list) and i < len(audio_files):
                    scene_audio = audio_files[i]
                elif isinstance(audio_files, str):
                    scene_audio = audio_files
                
                # Process scene
                processed = self.process_scene(scene, style, scene_audio)
                if processed:
                    processed_scenes.append(processed)
                else:
                    logger.warning(f"Failed to process scene {i+1}")
            
            if not processed_scenes:
                logger.error("No scenes were successfully processed")
                return None
            
            # Combine scenes into final video
            # (This part would typically be handled by video_processor.py)
            
            return "path/to/output/video.mp4"  # Placeholder
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return None
