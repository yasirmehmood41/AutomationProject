import os
import moviepy.config as mpy_config
mpy_config.change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
from moviepy.editor import TextClip, ImageClip, VideoClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, ColorClip
from utils.config_loader import load_config
from Content_Engine import media_fetcher
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='./logs/video_processor.log')
logger = logging.getLogger('video_processor')

# Check for ImageMagick and set the path if needed
if os.name == 'nt':  # Windows
    os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"


class VideoProcessor:
    def __init__(self, config=None):
        self.config = config if config else load_config()
        self.media_fetcher = media_fetcher.MediaFetcher(self.config)
        self.resolution = (
            self.config['media']['resolution']['width'],
            self.config['media']['resolution']['height']
        )
        self.font = self.config['video_style']['font']
        self.font_size = self.config['video_style']['font_size']
        self.font_color = self.config['video_style']['font_color']
        self.text_position = self.config['video_style']['text_position']
        self.transition = self.config['video_style']['transition']
        self.transition_duration = self.config['video_style']['transition_duration']

    def create_scene_clip(self, scene_text, duration, keywords=None):
        """Create a video clip for a scene with text overlay on a relevant background."""
        # Extract keywords if not provided
        if not keywords:
            keywords = self.media_fetcher.extract_keywords_from_text(scene_text)
        # Get background media based on keywords
        bg_media_path = self.media_fetcher.fetch_media_for_keywords(keywords, "image")

        if not bg_media_path:
            # Fallback to solid color background if no image is found
            logger.warning(f"No background media found for scene. Using solid background.")

            # Convert hex color to RGB tuple if necessary
            bg_color = self.config['video_style']['background_color']
            if isinstance(bg_color, str) and bg_color.startswith("#"):
                # Convert hex to RGB tuple
                bg_color = tuple(int(bg_color[i:i+2], 16) for i in (1, 3, 5))

            bg_clip = ColorClip(self.resolution, color=bg_color, duration=duration)
        else:
            # Check if it's an image or video
            if bg_media_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                bg_clip = ImageClip(bg_media_path).set_duration(duration)
            else:
                bg_clip = VideoFileClip(bg_media_path).set_duration(duration)

            # Resize to fill screen while maintaining aspect ratio
            bg_clip = bg_clip.resize(height=self.resolution[1])

            # Center crop if needed
            if bg_clip.w > self.resolution[0]:
                x_start = (bg_clip.w - self.resolution[0]) // 2
                bg_clip = bg_clip.crop(x1=x_start, width=self.resolution[0])

        # Create text overlay
        text_clip = TextClip(scene_text,
                             fontsize=self.font_size,
                             color=self.font_color,
                             font=self.font,
                             size=self.resolution,
                             method='caption',
                             align='center')

        # Set text position
        if self.text_position == 'center':
            text_position = 'center'
        elif self.text_position == 'bottom':
            text_position = ('center', self.resolution[1] - self.font_size * 3)
        elif self.text_position == 'top':
            text_position = ('center', self.font_size)
        else:
            text_position = 'center'

        text_clip = text_clip.set_position(text_position).set_duration(duration)

        # Add a semi-transparent background to text for better readability
        txt_col = self.font_color
        if txt_col.lower() == 'white' or txt_col.lower() == '#ffffff':
            bg_col = 'rgba(0,0,0,0.5)'
        else:
            bg_col = 'rgba(255,255,255,0.5)'

        txt_bg = TextClip(' ' * len(scene_text),
                          fontsize=self.font_size,
                          color=bg_col,
                          font=self.font,
                          size=self.resolution,
                          method='caption')
        txt_bg = txt_bg.set_position(text_position).set_duration(duration)

        # Combine background and text
        return CompositeVideoClip([bg_clip, txt_bg, text_clip])

    def process_video(self, scenes, voice_file=None):
        """Process a complete video from multiple scenes and audio."""
        clips = []

        # Create each scene clip
        for i, scene in enumerate(scenes):
            # Calculate scene duration based on text length if auto_timing is enabled
            if self.config['scene']['auto_timing']:
                # ~5 characters per second is a good rule of thumb for reading speed
                words = len(scene.split())
                auto_duration = max(words * 0.5, self.config['scene']['min_duration'])
                auto_duration = min(auto_duration, self.config['scene']['max_duration'])
                duration = auto_duration
            else:
                duration = self.config['scene']['default_duration']

            # Extract keywords from the scene text
            keywords = self.media_fetcher.extract_keywords_from_text(scene)

            # Create the clip
            clip = self.create_scene_clip(scene, duration, keywords)

            # Apply transitions if not the first clip
            if i > 0 and self.transition == 'fade':
                clip = clip.fadein(self.transition_duration)

            if i < len(scenes) - 1 and self.transition == 'fade':
                clip = clip.fadeout(self.transition_duration)

            clips.append(clip)

        # Concatenate all clips
        final_video = concatenate_videoclips(clips, method="compose")

        # Add audio if provided
        if voice_file and os.path.exists(voice_file):
            audio = AudioFileClip(voice_file)
            final_video = final_video.set_audio(audio)

            # Extend video duration if audio is longer
            if audio.duration > final_video.duration:
                logger.info(f"Extending video duration to match audio: {audio.duration} seconds")
                final_video = final_video.set_duration(audio.duration)

        # Prepare output path
        output_dir = self.config['project']['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "final_video.mp4")

        # Write the final video file
        final_video.write_videofile(
            output_path,
            codec="libx264",
            fps=self.config['media']['fps']
        )

        return output_path