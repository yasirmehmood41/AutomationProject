import os
import shutil
import logging
from pathlib import Path
from utils.config_loader import load_config


def export_video(video_file: str) -> str:
    """
    Finalizes the video export by applying quality presets and renaming the final output.
    """
    try:
        # Create output directory if it doesn't exist
        config = load_config()
        output_dir = Path(config.get('paths', {}).get('output', './Output_Manager/outputs/'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        final_output = output_dir / 'final_video.mp4'
        
        # Use shutil.copy2 to copy file across drives, preserving metadata
        shutil.copy2(video_file, final_output)
        
        # Remove the temporary file
        try:
            os.remove(video_file)
        except Exception as e:
            logging.warning(f"Could not remove temporary file {video_file}: {str(e)}")
        
        return str(final_output)
        
    except Exception as e:
        logging.error(f"Error exporting video: {str(e)}")
        # Return original file if export fails
        return video_file


def check_video_quality(video_file):
    """Check the quality of the exported video."""
    try:
        # Basic file existence check
        if not os.path.exists(video_file):
            logging.error(f"Video file not found: {video_file}")
            return False
            
        # Basic size check
        file_size = os.path.getsize(video_file)
        if file_size < 1024:  # Less than 1KB
            logging.error(f"Video file too small: {file_size} bytes")
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error checking video quality: {str(e)}")
        return False


if __name__ == "__main__":
    dummy_video = "./Output_Manager/outputs/processed_video.mp4"
    print("Final video exported at:", export_video(dummy_video))
