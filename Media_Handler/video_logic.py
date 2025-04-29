print("[DIAG] video_logic.py loaded")

"""Video logic module for coordinating video generation."""
import os
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import json
from .scene_renderer import SceneRenderer
from .voice_system import VoiceSystem
from proglog import ProgressBarLogger

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
        # Defensive: ensure style is a dict
        if isinstance(style, str):
            from Media_Handler.video_processor import VideoStyle
            style = VideoStyle.get_style(style)
        if hasattr(style, '__dict__'):
            style = dict(style.__dict__)
        elif not isinstance(style, dict):
            style = {}
        resolution = style.get('resolution', (1920, 1080))
        font = style.get('font', 'Arial')
        font_size = style.get('font_size', 36)
        
        self.scene_renderer = SceneRenderer(
            resolution=resolution,
            font=font,
            default_font_size=font_size
        )
    
    def _extract_highlighted_words(self, text: str) -> List[str]:
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
        audio_file: Optional[str] = None,
        subtitle_position: str = 'center',
        overlay_title: str = '',
        overlay_author: str = '',
        overlay_logo_bytes = None,
        overlay_slogan = None,
        overlay_color = None,
        overlay_watermark_bytes = None,
        overlay_animate = False
    ) -> Optional[Dict]:
        print(f"[DIAG] process_scene called with type(scene)={type(scene)}, scene={scene}")
        if not isinstance(scene, dict):
            logger.error(f"process_scene called with non-dict: {scene!r}")
            return None
        try:
            # Defensive: ensure scene is a dict before .get
            if not isinstance(scene, dict):
                logger.error(f"process_scene: scene is not a dict (type={type(scene)}): {scene}")
                return None
            # Defensive: ensure all .get usage is on dict
            scene_text = scene.get('text', '')
            if scene_text is None:
                scene_text = scene.get('script', '')
            if not isinstance(scene_text, str):
                logger.error(f"scene['text'] or ['script'] is not a string (type={type(scene_text)}): {scene_text}")
                scene_text = str(scene_text)
            highlighted_words = self._extract_highlighted_words(scene_text)
            rendered_scene = None
            try:
                # Ensure scene_renderer is initialized
                if self.scene_renderer is None:
                    self._init_scene_renderer(style)
                scene_subtitle_position = scene.get('subtitle_position') if isinstance(scene, dict) else None
                if not scene_subtitle_position or scene_subtitle_position == '(use global)':
                    scene_subtitle_position = subtitle_position
                rendered_scene = self.scene_renderer.render_scene_with_overlay(
                    scene,
                    scene.get('duration', 5.0) if isinstance(scene, dict) else 5.0,
                    overlay_title,
                    overlay_author,
                    overlay_logo_bytes,
                    overlay_slogan,
                    overlay_color,
                    overlay_watermark_bytes,
                    overlay_animate,
                    style,
                    scene_subtitle_position
                )
            except Exception as e:
                import traceback
                logger.error(f"Rendering failed for scene {scene.get('scene_number', '?') if isinstance(scene, dict) else '?'}: {e}\n{traceback.format_exc()}")
                print(f"Rendering failed for scene {scene.get('scene_number', '?') if isinstance(scene, dict) else '?'}: {e}")
                traceback.print_exc()
                if self.config.debug_mode and isinstance(scene, dict):
                    self.debug_data['rendering_errors'].append({
                        'scene': scene.get('scene_number', '?'),
                        'error': str(e)
                    })
                rendered_scene = None
            # --- Ensure scene duration >= audio duration ---
            if audio_file and os.path.exists(audio_file):
                try:
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_file)
                    audio_duration = audio_clip.duration
                    if isinstance(scene, dict) and scene.get('duration', 0) < audio_duration:
                        scene['duration'] = audio_duration
                    audio_clip.close()
                except Exception as e:
                    logger.error(f"Could not check audio duration for scene {scene.get('scene_number','?') if isinstance(scene, dict) else '?'}: {e}")
            return {
                **scene,
                'rendered': rendered_scene,
                'highlighted_words': highlighted_words
            }
        except Exception as e:
            logger.error(f"Error processing scene: {e}")
            if self.config.debug_mode and isinstance(scene, dict):
                self.debug_data['rendering_errors'].append({
                    'scene': scene.get('scene_number', '?'),
                    'error': str(e)
                })
            return None
    
    def process_video(
        self,
        scenes: List[Dict],
        audio_files: Optional[Union[str, List[str]]] = None,
        style: Optional[Dict] = None,
        music_config: Optional[dict] = None,
        logger=None,
        subtitle_position: str = 'center',
        overlay_title: str = '',
        overlay_author: str = '',
        overlay_logo_bytes = None,
        overlay_slogan = None,
        overlay_color = None,
        overlay_watermark_bytes = None,
        overlay_animate = False,
        additional_settings: Optional[Dict] = None
    ) -> Optional[str]:
        print("[DIAG] video_logic.process_video called with additional_settings:", additional_settings, flush=True)
        if additional_settings is not None and 'streamlit_logger' in additional_settings:
            print("[DIAG] streamlit_logger found in additional_settings", flush=True)
        else:
            print("[DIAG] streamlit_logger NOT found in additional_settings", flush=True)
        try:
            if not scenes:
                raise ValueError("No scenes provided")
            # Process scene metadata
            processed_scenes = []
            total = len(scenes)
            for idx, scene in enumerate(scenes):
                if not isinstance(scene, dict):
                    logger.error(f"Scene at index {idx} is not a dict: {scene!r}")
                    continue
                logger.debug(f"[DIAG] Calling process_scene for idx={idx}, type(scene)={type(scene)}, scene={scene}")
                # --- Inject overlays into scene dict ---
                scene['overlay_logo_bytes'] = overlay_logo_bytes
                scene['overlay_title'] = overlay_title
                scene['overlay_author'] = overlay_author
                scene['overlay_slogan'] = overlay_slogan
                scene['overlay_watermark_bytes'] = overlay_watermark_bytes
                # --- Robust audio logic: uploaded > TTS > silent ---
                audio_file = None
                # 1. Uploaded audio (must be provided in scene dict as 'uploaded_audio')
                if scene.get('uploaded_audio'):
                    audio_file = scene['uploaded_audio']
                # 2. TTS (if no uploaded audio and script text exists)
                elif scene.get('script'):
                    try:
                        audio_file = self.voice_system.generate_voice(scene['script'])
                    except Exception as e:
                        logger.error(f"TTS generation failed for scene {scene.get('scene_number','?')}: {e}")
                        audio_file = None
                # Defensive: ensure audio_file is a valid path (applies to all cases)
                if audio_file is not None and not (isinstance(audio_file, str) and os.path.isfile(audio_file)):
                    logger.error(f"Audio file for scene {scene.get('scene_number', '?')} is invalid: {audio_file!r}")
                    audio_file = None
                # 3. Fallback: silent
                if not audio_file:
                    logger.warning(f"No audio for scene {scene.get('scene_number','?')}, video will be silent.")
                logger.debug(f"[DIAG] About to call process_scene with scene type: {type(scene)}, value: {scene}")
                processed = self.process_scene(
                    scene,
                    style or {},
                    audio_file,
                    subtitle_position,
                    overlay_title,
                    overlay_author,
                    overlay_logo_bytes,
                    overlay_slogan,
                    overlay_color,
                    overlay_watermark_bytes,
                    overlay_animate
                )
                if processed:
                    processed_scenes.append(processed)
                else:
                    logger.warning(f"Scene {idx+1} failed to process or missing audio.")
            clips = []
            for i, scene in enumerate(processed_scenes):
                # Use the audio_file selected/created above for each scene
                audio_file = None
                if scene.get('uploaded_audio'):
                    audio_file = scene['uploaded_audio']
                elif scene.get('script'):
                    # Try to infer the TTS file path used earlier
                    tts_path = self.voice_system.generate_voice(scene['script'])
                    if os.path.exists(tts_path):
                        audio_file = tts_path
                if 'rendered' in scene:
                    clip = scene['rendered']
                    if audio_file and os.path.exists(audio_file):
                        try:
                            from moviepy.editor import AudioFileClip
                            clip = clip.set_audio(AudioFileClip(audio_file))
                        except Exception as e:
                            logger.error(f"Failed to add audio to scene {i+1}: {e}")
                    else:
                        logger.warning(f"No audio for scene {i+1}, video will be silent.")
                    clips.append(clip)
                else:
                    logger.warning(f"No 'rendered' key in scene {i+1}, skipping.")
            # Defensive: filter out None
            clips = [c for c in clips if c is not None]
            if not clips:
                return None
            # --- Compile video ---
            from moviepy.editor import concatenate_videoclips, AudioFileClip, CompositeAudioClip
            
            def get_music_clip(music_file, music_url, music_volume, fallback_path=None):
                """Robustly get a music clip from file, url, or fallback."""
                import tempfile
                from urllib.request import urlopen
                try:
                    if music_file and hasattr(music_file, 'read'):
                        import traceback
                        # Save uploaded file to disk, rewind if needed
                        try:
                            music_file.seek(0)
                        except Exception:
                            pass
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                            data = music_file.read()
                            tmp.write(data)
                            music_path = tmp.name
                        return AudioFileClip(music_path).volumex(5.0)
                    elif music_url:
                        with urlopen(music_url) as response, tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
                            tmp.write(response.read())
                            music_path = tmp.name
                        return AudioFileClip(music_path).volumex(5.0)
                    elif fallback_path and os.path.exists(fallback_path):
                        return AudioFileClip(fallback_path).volumex(5.0)
                    else:
                        logger.warning("No background music provided or found.")
                        return None
                except Exception as e:
                    import traceback
                    logger.error(f"Failed to load music: {e}\n{traceback.format_exc()}")
                    return None

            final_clip = concatenate_videoclips(clips, method='compose')
            # --- Add background music ---
            if music_config:
                fallback_music = music_config.get('fallback')  # Optional: set fallback path in config
                if music_config.get('mode') == 'global':
                    music = music_config.get('music')
                    music_volume = music.get('volume', 0.1) if music else 0.1
                    music_file = music.get('file') if music else None
                    music_url = music.get('url') if music else None
                    music_clip = get_music_clip(music_file, music_url, music_volume, fallback_music)
                    if music_clip:
                        from moviepy.audio.fx.all import audio_loop
                        music_clip = music_clip.fx(audio_loop, duration=final_clip.duration).subclip(0, final_clip.duration)
                        if final_clip.audio:
                            from moviepy.editor import CompositeAudioClip
                            scene_audio = final_clip.audio.volumex(0.3)
                            final_audio = CompositeAudioClip([scene_audio, music_clip])
                        else:
                            final_audio = music_clip
                        final_clip = final_clip.set_audio(final_audio)
                elif music_config.get('mode') == 'per_scene':
                    per_scene_music = music_config.get('music', [])
                    fallback_music = music_config.get('fallback')  # Optional
                    for idx, music in enumerate(per_scene_music):
                        if not music:
                            continue
                        music_file = music.get('file')
                        music_url = music.get('url')
                        music_volume = music.get('volume', 0.1)
                        music_clip = get_music_clip(music_file, music_url, music_volume, fallback_music)
                        if music_clip and idx < len(clips):
                            from moviepy.audio.fx.all import audio_loop
                            music_clip = music_clip.fx(audio_loop, duration=clips[idx].duration).subclip(0, clips[idx].duration)
                            if clips[idx].audio:
                                scene_audio = clips[idx].audio.volumex(0.3)
                                clips[idx] = clips[idx].set_audio(CompositeAudioClip([scene_audio, music_clip]))
                            else:
                                clips[idx] = clips[idx].set_audio(music_clip)
            import time
            timestamp = int(time.time())
            output_path = f"output_manager/videos/video_default_{timestamp}.mp4"
            # Determine logger for MoviePy
            class StreamlitProglogLogger(ProgressBarLogger):
                def __init__(self, st_progress_bar):
                    super().__init__()
                    self.st_progress_bar = st_progress_bar
                def callback(self, **changes):
                    if 'progress' in changes:
                        percent = changes['progress']
                        percent = max(0.0, min(1.0, percent))
                        print(f"[DIAG] StreamlitProglogLogger percent: {percent}", flush=True)
                        try:
                            # If st_progress_bar is a function (circle), call it, else use .progress
                            if callable(self.st_progress_bar):
                                print(f"[DIAG] Calling st_progress_bar as function with {percent}", flush=True)
                                self.st_progress_bar(percent)
                            else:
                                print(f"[DIAG] Calling st_progress_bar.progress({percent})", flush=True)
                                self.st_progress_bar.progress(percent, text=f"Rendering video... {int(percent*100)}%")
                        except Exception as e:
                            print(f"[ERROR] Exception updating progress bar: {e}", flush=True)

            class TerminalPercentageLogger(ProgressBarLogger):
                def callback(self, **changes):
                    print("[DIAG] TerminalPercentageLogger callback called with:", changes, flush=True)
                    if 'progress' in changes:
                        percent = changes['progress']
                        print(f"[DIAG] TerminalPercentageLogger percent: {percent}", flush=True)
                        percent_int = int(percent * 100)
                        print(f"[PROGRESS] {percent_int}% finished", flush=True)

            print(f"[DIAG] additional_settings before logger selection: {additional_settings}", flush=True)
            logger_bar = None
            if 'streamlit_logger' in additional_settings and additional_settings['streamlit_logger'] is not None:
                print(f"[DIAG] Using StreamlitProglogLogger for UI progress bar, type: {type(additional_settings['streamlit_logger'])}", flush=True)
                logger_bar = StreamlitProglogLogger(additional_settings['streamlit_logger'])
            elif logger is not None:
                print("[DIAG] Using provided logger", flush=True)
                logger_bar = logger
            else:
                # DIRECT FIX: Force Streamlit progress if available
                try:
                    import streamlit as st
                    print("[DIAG] EMERGENCY FIX: Creating Streamlit progress bar directly in video_logic.py", flush=True)
                    progress_bar = st.progress(0, text="Video rendering...")
                    logger_bar = StreamlitProglogLogger(progress_bar)
                    print("[DIAG] Emergency Streamlit progress bar created successfully", flush=True)
                except Exception as e:
                    print(f"[DIAG] Emergency Streamlit progress bar failed: {e}", flush=True)
                    print("[DIAG] Using TerminalPercentageLogger for terminal progress", flush=True)
                    logger_bar = TerminalPercentageLogger()
            # TEST: Call logger_bar.callback with fake progress before write_videofile
            try:
                print("[DIAG] Calling logger_bar.callback with fake progress=0.42", flush=True)
                logger_bar.callback(progress=0.42)
            except Exception as e:
                print(f"[ERROR] Exception calling logger_bar.callback: {e}", flush=True)
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=f"output_manager/videos/tmp_audio_{timestamp}.m4a",
                remove_temp=True,
                threads=1,
                logger=logger_bar,
                fps=24
            )
            # Progress: after video writing
            if logger is not None:
                try:
                    logger(100)
                except Exception:
                    pass
            return output_path
        except Exception as e:
            if hasattr(logger, 'error'):
                logger.error(f"Error in process_video: {e}")
            elif callable(logger):
                logger(f"Error in process_video: {e}")
            else:
                print(f"[ERROR] Error in process_video: {e}")
            return None

# TODO: Add integration tests for full video generation pipeline.
