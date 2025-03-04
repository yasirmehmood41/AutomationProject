import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
from moviepy.editor import TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
from utils.config_loader import load_config

def create_scene_clip(scene_text: str, duration: int, resolution="1920x1080") -> TextClip:
    """
    Create a text clip for a scene with the given duration and resolution.
    """
    clip = TextClip(scene_text, fontsize=70, color='white', size=resolution, bg_color='black')
    clip = clip.set_duration(duration)
    return clip

def process_video(scenes: list, voice_audio: str, output_path: str = "./Output_Manager/outputs/") -> str:
    """
    Assemble video clips from scenes, overlay voice audio, and export the final video.
    Uses MoviePy to concatenate scene clips and overlay the audio.
    """
    # Load video settings from config
    config = load_config()
    video_config = config.get('video', {})
    fps = video_config.get('fps', 30)
    resolution = video_config.get('resolution', '1920x1080')
    video_format = video_config.get('format', 'mp4')

    os.makedirs(output_path, exist_ok=True)
    video_file = os.path.join(output_path, f"processed_video.{video_format}")

    # Create clips for each scene (using 5 seconds per scene for now)
    clips = [create_scene_clip(scene, 5, resolution=resolution) for scene in scenes]

    # Concatenate the scene clips into a single video clip
    final_clip = concatenate_videoclips(clips, method="compose")

    # Add voice audio if available
    if os.path.exists(voice_audio):
        audio_clip = AudioFileClip(voice_audio)
        final_clip = final_clip.set_audio(audio_clip)

    # Write the final video file
    final_clip.write_videofile(video_file, fps=fps, codec='libx264', bitrate=video_config.get('bitrate', '5M'))
    return video_file

if __name__ == "__main__":
    sample_scenes = ["Scene 1: Introduce product.", "Scene 2: Showcase benefits.", "Scene 3: Conclude with a call-to-action."]
    dummy_voice = "./Output_Manager/outputs/voice_sample.mp3"  # Ensure this exists from your voice system
    output = process_video(sample_scenes, dummy_voice)
    print("Processed video created at:", output)
