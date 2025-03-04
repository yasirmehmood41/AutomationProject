import os
from utils.config_loader import load_config


def export_video(video_file: str) -> str:
    """
    Finalizes the video export by applying quality presets and renaming the final output.
    """
    config = load_config()
    output_dir = config.get('paths', {}).get('output', './Output_Manager/outputs/')
    os.makedirs(output_dir, exist_ok=True)
    final_output = os.path.join(output_dir, "final_video.mp4")

    # Simulate final export by renaming or copying the file.
    # In practice, you might call additional ffmpeg commands here.
    os.rename(video_file, final_output)
    return final_output


if __name__ == "__main__":
    dummy_video = "./Output_Manager/outputs/processed_video.mp4"
    print("Final video exported at:", export_video(dummy_video))
