import os
import moviepy.config as mpy_config
mpy_config.change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

from concurrent.futures import ThreadPoolExecutor
import numpy as np
from moviepy.editor import (
    TextClip, ImageClip, VideoFileClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip, ColorClip, vfx,
    AudioClip, CompositeAudioClip
)
from utils.config_loader import load_config
from Content_Engine import media_fetcher
import logging
from PIL import Image
import tempfile
import time
import json
import requests
import librosa
import soundfile as sf
from pydub import AudioSegment

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='./logs/video_processor.log')
logger = logging.getLogger('video_processor')

# Ensure ImageMagick is correctly set up
if os.name == 'nt':
    os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

class VideoProcessor:
    def __init__(self, config=None):
        self.config = config if config else load_config()
        self.media_fetcher = media_fetcher.MediaFetcher(self.config)
        # Assume an AudioProcessor is integrated in your project; if not, voice processing is done externally.
        # self.audio_processor = AudioProcessor(self.config)
        self.resolution = (
            self.config['media']['resolution']['width'],
            self.config['media']['resolution']['height']
        )
        self.temp_dir = tempfile.mkdtemp()
        self._load_style_settings()
        self.clip_cache = {}

    def _load_style_settings(self):
        """Load style settings from configuration."""
        style = self.config['video_style']
        self.font = style.get('font', 'Arial')
        self.font_size = style.get('font_size', 70)
        self.font_color = style.get('font_color', 'white')
        self.text_position = style.get('text_position', 'bottom')
        self.transition = style.get('transition', 'fade')
        self.transition_duration = style.get('transition_duration', 1.0)
        self.background_color = style.get('background_color', '#000000')
        self.text_opacity = style.get('text_opacity', 1.0)
        self.stroke_width = style.get('stroke_width', 2)
        self.stroke_color = style.get('stroke_color', 'black')
        self.text_effect = style.get('text_effect', 'none')
        self.background_blur = style.get('background_blur', 0)
        self.zoom_effect = style.get('zoom_effect', False)
        self.zoom_ratio = style.get('zoom_ratio', 0.05)
        # Additional effects
        self.motion_graphics = style.get('motion_graphics', False)
        self.animation_style = style.get('animation_style', 'simple')
        self.subtitle_style = style.get('subtitle_style', 'standard')
        self.overlay_logo = style.get('overlay_logo', None)
        self.captions_enabled = style.get('captions_enabled', True)

    def _hex_to_rgb(self, hex_color):
        """Convert hex color (e.g., '#0000FF') to an RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _resize_and_crop_background(self, clip):
        """Resize and crop background media to exactly match target resolution."""
        target_ratio = self.resolution[0] / self.resolution[1]
        clip_ratio = clip.w / clip.h
        if clip_ratio > target_ratio:
            clip = clip.resize(height=self.resolution[1])
            excess_width = clip.w - self.resolution[0]
            clip = clip.crop(x1=excess_width // 2, width=self.resolution[0])
        else:
            clip = clip.resize(width=self.resolution[0])
            excess_height = clip.h - self.resolution[1]
            clip = clip.crop(y1=excess_height // 2, height=self.resolution[1])
        return clip

    def _apply_motion_graphics(self, clip):
        """Optional: Apply dynamic motion effects (e.g., Ken Burns, parallax) to a clip."""
        # For example, if animation_style is 'ken_burns', apply a zoom effect:
        if self.animation_style == 'ken_burns':
            # Apply a slow zoom effect
            return clip.fx(vfx.zoom_in, factor=1 + self.zoom_ratio)
        # Additional effects can be added here (parallax, particles, etc.)
        return clip

    def _create_dynamic_background(self, duration, keywords=None):
        """Create a dynamic background clip based on keywords or use a fallback gradient background."""
        if not keywords:
            bg_color = self._hex_to_rgb(self.background_color)
            bg_clip = ColorClip(size=self.resolution, color=bg_color, duration=duration)
            return bg_clip

        bg_media_path = self.media_fetcher.fetch_media_for_keywords(keywords, "image")
        if bg_media_path in self.clip_cache:
            bg_clip = self.clip_cache[bg_media_path].copy().set_duration(duration)
        else:
            if not bg_media_path:
                logger.warning("No background media found. Using solid background.")
                return ColorClip(size=self.resolution, color=self._hex_to_rgb(self.background_color), duration=duration)
            elif bg_media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                bg_clip = ImageClip(bg_media_path)
                if self.zoom_effect:
                    bg_clip = bg_clip.resize(height=int(self.resolution[1] * (1 + self.zoom_ratio)))
            else:
                bg_clip = VideoFileClip(bg_media_path).without_audio()
            self.clip_cache[bg_media_path] = bg_clip.copy()
            bg_clip = bg_clip.set_duration(duration)
        bg_clip = self._resize_and_crop_background(bg_clip)
        if self.background_blur > 0:
            bg_clip = bg_clip.fx(vfx.blur, self.background_blur)
        if self.motion_graphics:
            bg_clip = self._apply_motion_graphics(bg_clip)
        return bg_clip

    def _calculate_text_position(self, text_clip, font_size):
        """Calculate text position based on configuration."""
        if self.text_position == 'center':
            return 'center'
        elif self.text_position == 'bottom':
            return ('center', self.resolution[1] - text_clip.h - font_size // 2)
        elif self.text_position == 'top':
            return ('center', font_size // 2)
        else:
            return 'center'

    def _create_synchronized_captions(self, text, duration, word_timings, font_size):
        """
        Create captions that reveal words gradually based on word_timings.
        word_timings should be a list of dictionaries with keys 'word' and 'time' (in seconds).
        """
        # Ensure word_timings is sorted by time
        word_timings = sorted(word_timings, key=lambda x: x['time'])
        total_words = text.split()

        # Define a function that returns text up to the current time t
        def caption_func(t):
            # Reveal words for which timing is less than or equal to current time t
            revealed = [wt['word'] for wt in word_timings if wt['time'] <= t]
            # Fallback: if no timing data, reveal based on average duration per word
            if not revealed:
                avg_word_duration = duration / len(total_words)
                words_to_show = int(t / avg_word_duration)
                revealed = total_words[:words_to_show]
            return " ".join(revealed)

        # Create a dynamic text clip using the caption function
        # (MoviePy's TextClip supports a callable if method='caption')
        text_clip = TextClip(caption_func,
                             fontsize=font_size,
                             color=self.font_color,
                             font=self.font,
                             method='caption',
                             size=(int(self.resolution[0] * 0.8), None),
                             stroke_width=self.stroke_width,
                             stroke_color=self.stroke_color
                             ).set_duration(duration)

        # Set text position using your existing logic
        pos = self._calculate_text_position(text_clip, font_size)
        text_clip = text_clip.set_position(pos)

        # Apply fade effects (if desired)
        fade_duration = min(0.7, duration / 4)
        text_clip = text_clip.fadein(fade_duration).fadeout(fade_duration)

        return text_clip

    def create_scene_clip(self, scene_text, duration, keywords=None):
        """Create a scene clip by combining background and text overlay."""
        if not keywords:
            keywords = self.media_fetcher.extract_keywords_from_text(scene_text)

        try:
            bg_clip = self._create_dynamic_background(duration, keywords)
            text_clip = self._create_text_clip(scene_text, duration)
            final_clip = CompositeVideoClip([bg_clip, text_clip])
            return final_clip
        except Exception as e:
            logger.error(f"Error creating scene clip: {str(e)}")
            bg_clip = ColorClip(size=self.resolution, color=(30, 30, 30), duration=duration)
            text_clip = TextClip(
                scene_text, fontsize=40, color="white", font="Arial",
                method='caption', size=(int(self.resolution[0]*0.8), None)
            ).set_duration(duration).set_position('center')
            return CompositeVideoClip([bg_clip, text_clip])

    def _calculate_scene_durations(self, scenes, voice_file=None):
        """Calculate durations for each scene based on text length and audio duration."""
        scene_settings = self.config['scene']
        default_duration = scene_settings.get('default_duration', 5)
        min_duration = scene_settings.get('min_duration', 3)
        max_duration = scene_settings.get('max_duration', 15)
        auto_timing = scene_settings.get('auto_timing', True)
        durations = []
        for scene in scenes:
            if auto_timing:
                word_count = len(scene.split())
                reading_time = word_count * 0.65
                punctuation_count = sum(1 for char in scene if char in '.,:;?!()-')
                complexity_factor = 1 + (punctuation_count / max(1, word_count)) * 0.5
                duration = reading_time * complexity_factor
            else:
                duration = default_duration
            duration = max(min_duration, min(duration, max_duration))
            durations.append(duration)
        if voice_file and os.path.exists(voice_file):
            try:
                audio = AudioFileClip(voice_file)
                total_duration = sum(durations)
                if total_duration < audio.duration:
                    ratio = audio.duration / total_duration
                    durations = [d * ratio for d in durations]
            except Exception as e:
                logger.error(f"Error processing audio file: {str(e)}")
        return durations

    def _add_clip_with_transition(self, clips, clip, index):
        """Apply transitions to clip and add it to the clip list."""
        if index > 0:
            if self.transition == 'fade':
                clip = clip.crossfadein(self.transition_duration)
            elif self.transition == 'slide':
                clip = clip.crossfadein(self.transition_duration)
        clips.append(clip)
        return clips

    def _finalize_video(self, clips, voice_file=None):
        """Concatenate clips, sync with audio, and export the final video."""
        if not clips:
            logger.error("No clips to process")
            clip = ColorClip(size=self.resolution, color=(0, 0, 0), duration=5)
            text = TextClip("Error generating video", fontsize=70, color="white", font="Arial")
            text = text.set_position('center').set_duration(5)
            clips = [CompositeVideoClip([clip, text])]
        final_video = concatenate_videoclips(clips, method="compose")
        if voice_file and os.path.exists(voice_file):
            try:
                audio = AudioFileClip(voice_file)
                if audio.duration > final_video.duration:
                    logger.info(f"Extending video duration to match audio ({audio.duration}s).")
                    last_frame = final_video.get_frame(final_video.duration - 0.1)
                    freeze_clip = ImageClip(last_frame).set_duration(audio.duration - final_video.duration)
                    final_video = concatenate_videoclips([final_video, freeze_clip])
                elif audio.duration < final_video.duration:
                    logger.info(f"Trimming video to match audio ({audio.duration}s).")
                    final_video = final_video.subclip(0, audio.duration)
                final_video = final_video.set_audio(audio)
            except Exception as e:
                logger.error(f"Error adding audio to video: {str(e)}")
        output_dir = self.config['project']['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "final_video.mp4")
        try:
            final_video.write_videofile(
                output_path,
                codec="libx264",
                fps=self.config['media']['fps'],
                bitrate=self.config['media'].get('bitrate', '5000k'),
                threads=os.cpu_count(),
                preset="medium"
            )
        except Exception as e:
            logger.error(f"Error writing video file: {str(e)}")
            try:
                final_video.write_videofile(
                    output_path,
                    codec="libx264",
                    fps=24,
                    preset="ultrafast",
                    threads=1
                )
            except Exception as e2:
                logger.error(f"Error writing video with fallback settings: {str(e2)}")
                raise
        for clip in self.clip_cache.values():
            try:
                clip.close()
            except:
                pass
        self.clip_cache.clear()
        return final_video, output_path

    def process_video(self, scenes, voice_file=None):
        """Main method to process the full video from scenes and voice-over."""
        scene_durations = self._calculate_scene_durations(scenes, voice_file)
        clips = []
        try:
            use_parallel = self.config.get('performance', {}).get('parallel_processing', False)
            if use_parallel:
                with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                    future_clips = [
                        executor.submit(self.create_scene_clip, scene, duration)
                        for scene, duration in zip(scenes, scene_durations)
                    ]
                    for i, future in enumerate(future_clips):
                        clip = future.result()
                        self._add_clip_with_transition(clips, clip, i)
            else:
                for i, (scene, duration) in enumerate(zip(scenes, scene_durations)):
                    clip = self.create_scene_clip(scene, duration)
                    self._add_clip_with_transition(clips, clip, i)
        except Exception as e:
            logger.error(f"Error in parallel processing: {str(e)}")
            clips = []
            for i, (scene, duration) in enumerate(zip(scenes, scene_durations)):
                try:
                    clip = self.create_scene_clip(scene, duration)
                    self._add_clip_with_transition(clips, clip, i)
                except Exception as e:
                    logger.error(f"Error processing scene {i}: {str(e)}")
                    bg_clip = ColorClip(size=self.resolution, color=(30, 30, 30), duration=duration)
                    text_clip = TextClip(
                        scene, fontsize=40, color="white", font="Arial"
                    ).set_position('center').set_duration(duration)
                    clip = CompositeVideoClip([bg_clip, text_clip])
                    self._add_clip_with_transition(clips, clip, i)
        final_video, output_path = self._finalize_video(clips, voice_file)
        return output_path


# End of VideoProcessor class
