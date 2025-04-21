"""Main script for video generation system."""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from Content_Engine.api_generator import ScriptGenerator
from Content_Engine.scene_generator import generate_scene_metadata
from Media_Handler.voice_system import VoiceSystem
from Media_Handler.video_processor import VideoProcessor
from Media_Handler.video_logic import VideoLogic
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file. Returns config dict or empty dict on failure."""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        print(f"Error loading config: {e}")
        return {}

def preview_script(script_text: str) -> bool:
    """Preview the script and get user confirmation."""
    print("\n=== Script Preview ===")
    print(script_text)
    
    while True:
        choice = input("\nApprove script? (y/n): ").lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print("Please enter 'y' or 'n'")

def select_niche(script_generator: ScriptGenerator) -> str:
    """Select content niche."""
    niches = script_generator.get_available_niches()
    print("\n=== Content Niche Selection ===")
    for i, niche in enumerate(niches, 1):
        print(f"{i}. {niche.title()}")
    
    while True:
        try:
            choice = int(input(f"\nSelect niche (1-{len(niches)}): "))
            if 1 <= choice <= len(niches):
                selected_niche = niches[choice - 1]
                if script_generator.switch_niche(selected_niche):
                    return selected_niche
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(niches)}")

def select_voice(voice_system: VoiceSystem) -> str:
    """Select voice for the video."""
    voices = voice_system.list_available_voices()
    print("\n=== Voice Selection ===")
    
    # Group voices by provider
    voices_by_provider = {}
    for voice_id, voice in voices.items():
        provider = voice.engine
        if provider not in voices_by_provider:
            voices_by_provider[provider] = []
        voices_by_provider[provider].append((voice_id, voice))
    
    # Display voices grouped by provider
    voice_options = []
    for provider, provider_voices in voices_by_provider.items():
        print(f"\n{provider.upper()} Voices:")
        for voice_id, voice in provider_voices:
            idx = len(voice_options) + 1
            print(f"{idx}. {voice.name} ({voice.gender}, {voice.language})")
            voice_options.append(voice_id)
    
    while True:
        try:
            choice = int(input(f"\nSelect voice (1-{len(voice_options)}): "))
            if 1 <= choice <= len(voice_options):
                return voice_options[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(voice_options)}")

def select_style() -> str:
    """Select video style."""
    styles = {
        "modern": "Clean, minimalist design with smooth transitions",
        "corporate": "Professional and polished look",
        "creative": "Dynamic and artistic elements",
        "tech": "High-tech, digital aesthetic",
        "casual": "Friendly and approachable style"
    }
    
    print("\n=== Style Selection ===")
    for i, (style_id, desc) in enumerate(styles.items(), 1):
        print(f"{i}. {style_id.title()}")
        print(f"   {desc}\n")
    
    while True:
        try:
            choice = int(input(f"Select style (1-{len(styles)}): "))
            if 1 <= choice <= len(styles):
                return list(styles.keys())[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(styles)}")

def main():
    """Main function."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize components
        script_generator = ScriptGenerator()
        voice_system = VoiceSystem()
        video_processor = VideoProcessor()
        video_logic_handler = VideoLogic(config.get('video', {}))
        
        print("\n=== Video Generation System ===")
        
        # Select content niche
        selected_niche = select_niche(script_generator)
        print(f"\nSelected niche: {selected_niche.title()}")
        
        # Get script content
        script_text = get_script_content(script_generator)
        if not script_text:
            print("\nScript generation cancelled.")
            return
            
        # Preview and confirm script
        if not preview_script(script_text):
            print("\nScript generation cancelled.")
            return
            
        # Generate scene metadata
        logger.info("Generating scene metadata...")
        scenes = generate_scene_metadata(script_text)
        
        # Validate scene metadata
        if not scenes:
            error_msg = "Script content could not be split into scenes. Please check the template or enter a valid script."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Generated metadata for {len(scenes)} scenes")
        
        # Select voice
        voice_id = select_voice(voice_system)
        if not voice_id:
            print("\nVoice selection cancelled.")
            return
        
        # Generate voice-overs for each scene
        print("\nGenerating voice-overs...")
        try:
            audio_files = []
            for scene in scenes:
                if 'text' in scene:
                    audio_file = voice_system.backend.generate_voice(scene['text'], voice_id)
                    if audio_file:
                        audio_files.append(audio_file)
            print(f"Generated {len(audio_files)} audio files")
        except Exception as e:
            logger.error(f"Error generating voice-overs: {e}")
            return
        
        # Select video style
        style = select_style()
        if not style:
            print("\nStyle selection cancelled.")
            return
        
        # Process video with scene metadata
        print("\nProcessing video...")
        try:
            # First process scenes through video logic
            processed_scenes = []
            for i, scene in enumerate(scenes):
                scene_audio = audio_files[i] if i < len(audio_files) else None
                processed = video_logic_handler.process_scene(scene, style, scene_audio)
                if processed:
                    processed_scenes.append(processed)
                else:
                    logger.warning(f"Failed to process scene {i+1}")
            
            if not processed_scenes:
                logger.error("No scenes were successfully processed")
                return
            
            # Then generate final video
            output_file = video_processor.process_video(processed_scenes, audio_files, style)
            if output_file:
                print(f"\nVideo generated successfully: {output_file}")
                
                # Save debug info if enabled
                if config.get('debug_mode', False):
                    debug_file = os.path.join(os.path.dirname(output_file), 'debug_info.json')
                    try:
                        with open(debug_file, 'w') as f:
                            json.dump(video_logic_handler.debug_data, f, indent=2)
                        print(f"Debug information saved to: {debug_file}")
                    except Exception as e:
                        logger.error(f"Failed to save debug info: {e}")
            else:
                print("\nError: Failed to generate video")
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return

def get_script_content(script_generator: ScriptGenerator) -> Optional[str]:
    """Get script content either from template or manual input."""
    print("\n=== Script Generation ===")
    print("1. Generate from template")
    print("2. Manual input")
    
    while True:
        try:
            choice = int(input("\nSelect option (1-2): "))
            if choice in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")
    
    if choice == 1:
        # Template-based generation
        templates = script_generator.get_available_templates()
        print("\nAvailable templates:")
        for i, template in enumerate(templates, 1):
            print(f"\n{i}. {template['name']}")
            print(f"   Description: {template['description']}")
            print(f"   Style: {template['style']}")
            print(f"   Version: {template['version']}")
        
        while True:
            try:
                template_choice = int(input(f"\nSelect template (1-{len(templates)}): "))
                if 1 <= template_choice <= len(templates):
                    break
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {len(templates)}")
        
        template = templates[template_choice - 1]
        print(f"\n=== {template['name']} Template ===")
        print(f"{template['description']}\n")
        
        # Get template fields
        fields = script_generator.get_template_fields(template['id'])
        
        print("Required information:")
        context = {}
        for field in fields:
            if field['default']:
                value = input(f"{field['name']} [{field['default']}]: ").strip()
                if not value:
                    value = field['default']
            else:
                while True:
                    value = input(f"{field['name']}: ").strip()
                    if value or not field['required']:
                        break
                    print(f"{field['name']} is required")
            
            if value:
                context[field['id']] = value
        
        # Generate script
        try:
            return script_generator.generate_script(template['id'], context)
        except ValueError as e:
            logger.error(f"Error generating script: {e}")
            return None
        
    else:
        # Manual input
        print("\nEnter your script:")
        print("Use [Scene Name] to start new scenes")
        print("Use 'Visual:', 'Voice-over:', and 'On-screen text:' to specify content")
        print("Press Enter twice when done\n")
        
        lines = []
        while True:
            line = input()
            if not line and lines and not lines[-1]:
                break
            lines.append(line)
        
        return "\n".join(lines)

if __name__ == "__main__":
    main()
