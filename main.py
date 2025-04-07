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
        "Scene 1: Introduction to Smart Investing\n\n"
        "Start by explaining the importance of financial literacy. "
        "Introduce the idea of smart investing and how it helps in wealth growth.\n\n"

        "Scene 2: Understanding Risk and Reward\n\n"
        "Discuss different investment options like stocks, bonds, and real estate. "
        "Explain the concept of risk vs. reward and how diversification can help.\n\n"

        "Scene 3: The Power of Compound Interest\n\n"
        "Illustrate how compound interest works using simple examples. "
        "Show how early investments grow significantly over time.\n\n"

        "Scene 4: Avoiding Common Financial Mistakes\n\n"
        "Talk about emotional investing, lack of planning, and ignoring inflation. "
        "Give practical tips to avoid these financial pitfalls.\n\n"

        "Scene 5: Call to Action - Start Today!\n\n"
        "Encourage viewers to start investing today, even with small amounts. "
        "Provide resources or platforms to help them begin their financial journey."
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
