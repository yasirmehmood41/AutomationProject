"""Extremely simplified video generation test."""
import os
import sys
import time
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip

def main():
    # Create output dir
    output_dir = "output_manager/videos"
    os.makedirs(output_dir, exist_ok=True)
    
    with open("debug_log.txt", "w") as f:
        f.write("Starting simple video test\n")
        
        try:
            # Create a simple background clip
            f.write("Creating background clip\n")
            bg_clip = ColorClip(size=(640, 360), color=(0, 0, 0), duration=5)
            
            # Create simple text
            f.write("Creating text clip\n")
            text_clip = TextClip("Test Text", fontsize=40, color="white", font="Arial", method='pango')
            text_clip = text_clip.set_position('center').set_duration(5)
            
            # Combine clips
            f.write("Combining clips\n")
            final_clip = CompositeVideoClip([bg_clip, text_clip])
            
            # Write video
            outfile = os.path.join(output_dir, f"simple_test_{int(time.time())}.mp4")
            f.write(f"Writing to {outfile}\n")
            final_clip.write_videofile(outfile, fps=24, verbose=False)
            
            f.write("Video created successfully\n")
            
        except Exception as e:
            import traceback
            f.write(f"ERROR: {str(e)}\n")
            traceback.print_exc(file=f)

if __name__ == "__main__":
    main()
    # Also write completion to a separate file for visibility
    with open("test_complete.txt", "w") as f:
        f.write("Test completed at " + time.strftime("%H:%M:%S"))
