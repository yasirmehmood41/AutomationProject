print("[DIAG] video_logic.py loaded")

"""Video logic module for coordinating video generation."""
import os
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import json
from .scene_renderer import SceneRenderer
from .voice_system import VoiceSystem

logger = logging.getLogger(__name__)

@dataclass
class VideoConfig:
    """Video configuration.
    
    This class holds the configuration for video generation, including style, resolution, voice ID, output directory, and debug mode.
    
    TODO: Add support for more output formats, advanced style profiles, and localization.
    """
    style_name: str = "modern"
    resolution: str = "FHD"
    voice_id: Optional[str] = None
    output_dir: str = "output_manager/videos"
    debug_mode: bool = False

class VideoLogic:
    """Core video logic handler.
    
    This class handles the core logic for video generation, including scene processing, audio handling, and video rendering.
    
    TODO: Add error handling for all file operations, advanced scene analysis, and more unit/integration tests.
    """
    
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
        print(f"[DIAG] _init_scene_renderer called with style: {style}")
        resolution = style.get('resolution', (1920, 1080))
        font = style.get('font', 'Arial')
        font_size = style.get('font_size', 36)
        
        self.scene_renderer = SceneRenderer(
            resolution=resolution,
            font=font,
            default_font_size=font_size
        )
    
    def _extract_highlighted_words(self, text: str) -> List[str]:
        print(f"[DIAG] _extract_highlighted_words called with text: {text}")
        words = []
        for word in text.split():
            # Remove punctuation
            word = word.strip('.,!?()[]{}":;')
            if len(word) > 3:  # Only highlight words longer than 3 chars
                words.append(word)
        
        if not words and self.config.debug_mode:
            print("[DIAG] No words extracted for highlighting")
            logger.debug("No words extracted for highlighting")
        
        return words
    
    def _save_debug_info(self, scene_number: int, data: Dict) -> None:
        print(f"[DIAG] _save_debug_info called for scene_number: {scene_number}")
        if not self.config.debug_mode:
            print("[DIAG] Debug mode not enabled, skipping save_debug_info")
            return
        
        debug_file = os.path.join(self.config.output_dir, 'debug_info.json')
        self.debug_data['scenes'] = self.debug_data.get('scenes', {})
        self.debug_data['scenes'][scene_number] = data
        
        try:
            with open(debug_file, 'w') as f:
                json.dump(self.debug_data, f, indent=2)
            print(f"[DIAG] Debug info saved to {debug_file}")
        except Exception as e:
            print(f"[DIAG] Failed to save debug info: {e}")
            logger.error(f"Failed to save debug info: {e}")
    
    def process_scene(
        self,
        scene: Dict,
        style: Dict,
        audio_file: Optional[str] = None
    ) -> Optional[Dict]:
        print(f"[DIAG] process_scene called for scene: {scene.get('scene_number', '?')}")
        try:
            # Initialize scene renderer if needed
            if not self.scene_renderer:
                print("[DIAG] scene_renderer not initialized, calling _init_scene_renderer")
                self._init_scene_renderer(style)
            # Extract text for highlighting
            scene_text = scene.get('text', '')
            highlighted_words = self._extract_highlighted_words(scene_text)

            # --- ENFORCE MINIMUM SCENE DURATION BASED ON AUDIO ---
            min_duration = scene.get('duration', 5.0)
            if audio_file:
                try:
                    audio_duration = self.voice_system.get_audio_duration(audio_file)
                    print(f"[DIAG] Audio duration for scene {scene.get('scene_number', '?')}: {audio_duration}")
                    # Add a small buffer (e.g. 0.2s) to avoid cutoff
                    min_duration = max(min_duration, audio_duration + 0.2)
                except Exception as e:
                    print(f"[DIAG] Failed to get audio duration: {e}")
            scene['duration'] = min_duration
            # -----------------------------------------------------

            # Render scene (FIX: use render_scene, not render)
            try:
                print(f"[DIAG] Rendering scene {scene.get('scene_number', '?')}")
                rendered_scene = self.scene_renderer.render_scene(scene, style)
                print(f"[DIAG] Rendered scene: {rendered_scene}")
            except Exception as e:
                print(f"[DIAG] Rendering failed for scene {scene.get('scene_number', '?')}: {e}")
                logger.error(f"Rendering failed for scene {scene.get('scene_number', '?')}: {e}")
                if self.config.debug_mode:
                    self.debug_data['rendering_errors'].append({
                        'scene': scene.get('scene_number', '?'),
                        'error': str(e)
                    })
                rendered_scene = None
            return {
                **scene,
                'rendered': rendered_scene,
                'highlighted_words': highlighted_words
            }
        except Exception as e:
            print(f"[DIAG] Error processing scene {scene.get('scene_number', '?')}: {e}")
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
        audio_files: Optional[Union[str, List[str]]] = None,
        style: Optional[Dict] = None
    ) -> Optional[str]:
        print("[DIAG] process_video called")
        try:
            if not scenes:
                print("[DIAG] No scenes provided, aborting.")
                raise ValueError("No scenes provided")
            # Process scene metadata
            processed_scenes = []
            for idx, scene in enumerate(scenes):
                # Pass the correct audio file for duration enforcement
                audio_file = None
                if isinstance(audio_files, list) and idx < len(audio_files):
                    audio_file = audio_files[idx]
                elif isinstance(audio_files, str):
                    audio_file = audio_files
                processed = self.process_scene(scene, style or {}, audio_file)
                if processed:
                    processed_scenes.append(processed)
            print(f"[DIAG] processed_scenes: {processed_scenes}")
            # Generate video clips for each scene
            clips = []
            for i, scene in enumerate(processed_scenes):
                # Get scene audio
                scene_audio = None
                if isinstance(audio_files, list) and i < len(audio_files):
                    scene_audio = audio_files[i]
                elif isinstance(audio_files, str):
                    scene_audio = audio_files
                if 'rendered' in scene:
                    clip = scene['rendered']
                    if scene_audio:
                        try:
                            clip = clip.set_audio(scene_audio)
                        except Exception as e:
                            logger.error(f"Failed to add audio to scene {i+1}: {e}")
                    clips.append(clip)
            print(f"[DIAG] clips before filtering: {clips}")
            # Filter out None values from clips
            clips = [clip for clip in clips if clip is not None]
            print(f"[DIAG] After filtering, clips: {clips}")
            print(f"[DIAG] Types in clips: {[type(c) for c in clips]}")
            if not clips:
                print("[DIAG] No valid video clips to combine. Aborting video generation.")
                logger.error("[DIAG] No valid video clips to combine. Aborting video generation.")
                return None
            # Apply transitions
            print("[DIAG] About to call apply_transitions")
            try:
                from Media_Handler.transitions import TransitionManager
                transition_manager = TransitionManager()
            except Exception as e:
                print(f"[DIAG] ERROR: Could not import or instantiate TransitionManager: {e}")
                logger.error(f"Could not import or instantiate TransitionManager: {e}")
                return None
            transitioned_clips = transition_manager.apply_transitions(clips, transition_type="fade")
            print(f"[DIAG] Type of transitioned_clips: {type(transitioned_clips)}")
            print(f"[DIAG] transitioned_clips: {transitioned_clips}")
            if isinstance(transitioned_clips, list):
                print(f"[DIAG] Length of transitioned_clips: {len(transitioned_clips)}")
                for idx, item in enumerate(transitioned_clips):
                    print(f"[DIAG] transitioned_clips[{idx}] type: {type(item)}, value: {item}")
            # Flatten if list contains lists (robustness for nested lists)
            def flatten(lst):
                for item in lst:
                    if isinstance(item, list):
                        yield from flatten(item)
                    else:
                        yield item
            from moviepy.editor import concatenate_videoclips
            if isinstance(transitioned_clips, list):
                flat_clips = [clip for clip in flatten(transitioned_clips) if clip is not None]
                print(f"[DIAG] After flattening, length: {len(flat_clips)}")
                for idx, item in enumerate(flat_clips):
                    print(f"[DIAG] flat_clips[{idx}] type: {type(item)}, value: {item}")
                if not flat_clips:
                    print("[DIAG] No valid video clips after transitions. Aborting video generation.")
                    logger.error("[DIAG] No valid video clips after transitions. Aborting video generation.")
                    return None
                final_clip = concatenate_videoclips(flat_clips, method="compose")
            else:
                print(f"[DIAG] transitioned_clips is not a list, type: {type(transitioned_clips)}")
                final_clip = transitioned_clips
            # Ensure output directory exists before writing
            os.makedirs(self.config.output_dir, exist_ok=True)
            # Generate output path
            import time
            timestamp = int(time.time())
            style_name = style.get('name', 'default') if style else 'default'
            output_path = os.path.join(
                self.config.output_dir,
                f"video_{style_name}_{timestamp}.mp4"
            )
            print(f"[DIAG] Type of final_clip before write_videofile: {type(final_clip)}")
            print(f"[DIAG] final_clip: {final_clip}")
            if isinstance(final_clip, list):
                print("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                logger.error("[DIAG] FATAL: final_clip is still a list. Aborting video generation.")
                return None
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=24
            )
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return None

# TODO: Add integration tests for full video generation pipeline.
