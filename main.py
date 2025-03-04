from utils.config_loader import load_config
from Content_Engine.script_processor import process_script
from Content_Engine.template_manager import get_default_template
from Content_Engine.scene_generator import generate_scene_metadata
from Content_Engine.text_analyzer import extract_keywords
from Media_Handler.voice_system import generate_voice
from Media_Handler.video_processor import VideoProcessor
from Output_Manager.export_manager import export_video
from Output_Manager.quality_checker import check_video_quality

def main():
    # Load configuration
    config = load_config()
    print("Configuration Loaded:")
    print(config)

    # Sample script
    sample_script = (
        "Scene 1: Introduce the product.\n\n"
        "Scene 2: Explain its benefits.\n\n"
        "Scene 3: Conclude with a call-to-action."
    )

    # Content Engine
    scenes = process_script(sample_script)
    template = get_default_template()
    scene_metadata = generate_scene_metadata(sample_script)
    keywords = extract_keywords(sample_script)
    print("\nProcessed Scenes:", scenes)
    print("\nDefault Template:", template)
    print("\nScene Metadata:")
    for meta in scene_metadata:
        print(meta)
    print("\nExtracted Keywords:", keywords)

    # Media Handler
    voice_file = generate_voice(sample_script)
    print("\nVoice file generated at:", voice_file)
    video_processor = VideoProcessor(config)  # Initialize the processor
    processed_video = video_processor.process_video(scenes, voice_file)  # Call the method
    print("\nProcessed video created at:", processed_video)

    # Output Manager
    final_video = export_video(processed_video)
    quality_ok = check_video_quality(final_video)
    print("\nFinal video exported at:", final_video)
    print("Quality check passed:", quality_ok)

if __name__ == "__main__":
    main()
