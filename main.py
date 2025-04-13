"""Main script for video generation."""
import os
from typing import Dict, List, Optional
import json
from Content_Engine.api_generator import ScriptGenerator
from Media_Handler.voice_system import VoiceSystem
from Media_Handler.video_processor import VideoProcessor

def parse_manual_script(script_text: str) -> List[Dict]:
    """Parse manually entered script into scenes."""
    scenes = []
    current_scene = None
    
    # Split script into lines
    lines = script_text.strip().split('\n')
    collecting_voiceover = False
    current_voiceover = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if collecting_voiceover and current_voiceover:
                if current_scene:
                    current_scene['voiceover'] = '\n'.join(current_voiceover)
                collecting_voiceover = False
                current_voiceover = []
            continue
            
        # Check for scene markers
        if line.startswith('[') and ']' in line:
            # Save previous scene if exists
            if current_scene:
                if collecting_voiceover and current_voiceover:
                    current_scene['voiceover'] = '\n'.join(current_voiceover)
                scenes.append(current_scene)
            
            # Start new scene
            scene_name = line[1:line.find(']')]
            timing = ""
            if '–' in line or '-' in line:
                timing = line.split('–')[-1].split('-')[-1].strip()
            
            current_scene = {
                'name': scene_name,
                'timing': timing,
                'visuals': [],
                'voiceover': '',
                'text': [],
                'background': '',
                'transitions': []
            }
            collecting_voiceover = False
            current_voiceover = []
            continue
        
        # Parse scene content
        if current_scene:
            if line.lower().startswith('visual:'):
                current_scene['visuals'].append(line.split(':', 1)[1].strip())
                collecting_voiceover = False
            elif line.lower().startswith('voice-over:') or line.lower().startswith('voice-over/text on screen:'):
                collecting_voiceover = True
                text = line.split(':', 1)[1].strip().strip('"')
                if text:  # Only add if there's actual text after the colon
                    current_voiceover.append(text)
                if line.lower().startswith('voice-over/text on screen:'):
                    current_scene['text'].append(text)
            elif collecting_voiceover and line.startswith('"') and line.endswith('"'):
                # Add to current voice-over
                current_voiceover.append(line.strip('"'))
            elif line.lower().startswith('on-screen text:'):
                collecting_voiceover = False
                text_items = line.split(':', 1)[1].strip().strip('"').split('|')
                current_scene['text'].extend([t.strip().strip('"') for t in text_items])
            elif line.lower().startswith('bullet points on-screen:'):
                collecting_voiceover = False
                # Don't add the "Bullet points On-screen:" line itself
                continue
            elif line.startswith('"') and line.endswith('"'):
                # Additional text items
                current_scene['text'].append(line.strip('"'))
            elif line.lower().startswith('background music:'):
                collecting_voiceover = False
                current_scene['background'] = line.split(':', 1)[1].strip()
    
    # Add last scene
    if current_scene:
        if collecting_voiceover and current_voiceover:
            current_scene['voiceover'] = '\n'.join(current_voiceover)
        scenes.append(current_scene)
    
    return scenes

def preview_script(scenes: List[Dict]) -> bool:
    """Show script preview and get user confirmation."""
    print("\n=== Script Preview ===")
    print(f"Format: Professional Video Script")
    print(f"Total Scenes: {len(scenes)}")
    
    # Calculate estimated duration
    total_duration = 0
    for scene in scenes:
        if scene['timing']:
            try:
                # Parse timing like "0:06 to 0:20"
                start, end = scene['timing'].split('to')
                start_mins, start_secs = map(int, start.strip().split(':'))
                end_mins, end_secs = map(int, end.strip().split(':'))
                duration = (end_mins * 60 + end_secs) - (start_mins * 60 + start_secs)
                total_duration += duration
            except:
                # If timing can't be parsed, estimate based on content
                duration = len(scene['voiceover'].split()) / 2  # Assume 2 words per second
                total_duration += duration
    
    print(f"Estimated Duration: {total_duration}s\n")
    print("Scenes:\n")
    
    for i, scene in enumerate(scenes, 1):
        print(f"Scene {i}: [{scene['name']}]")
        if scene['timing']:
            print(f"Duration: {scene['timing']}")
        if scene['voiceover']:
            print(f"Words: {len(scene['voiceover'].split())}")
        print("-" * 40)
        if scene['voiceover']:
            print(scene['voiceover'])
        if scene['text']:
            print("\nOn-screen text:")
            for text in scene['text']:
                print(f"- {text}")
        print("\n")
    
    while True:
        choice = input("Proceed with this script? (y/n): ").lower()
        if choice in ['y', 'n']:
            return choice == 'y'
        print("Please enter 'y' or 'n'")

def select_voice() -> str:
    """Select voice for the video."""
    voice_system = VoiceSystem()
    voices = voice_system.list_available_voices()
    
    print("\n=== Voice Selection ===")
    for i, (voice_id, voice) in enumerate(voices.items(), 1):
        print(f"{i}. {voice.name}")
        print(f"   Language: {voice.language}")
        print(f"   Gender: {voice.gender}")
        print(f"   Engine: {voice.engine}\n")
    
    while True:
        try:
            choice = int(input(f"Select voice (1-{len(voices)}): "))
            if 1 <= choice <= len(voices):
                return list(voices.keys())[choice - 1]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(voices)}")

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
    print("\n=== Script Generation ===")
    print("1. Generate from template")
    print("2. Manual input\n")
    
    while True:
        try:
            choice = int(input("Select option (1-2): "))
            if choice in [1, 2]:
                break
        except ValueError:
            pass
        print("Please enter 1 or 2")
    
    # Initialize components
    script_generator = ScriptGenerator()
    voice_system = VoiceSystem()
    video_processor = VideoProcessor()
    
    if choice == 1:
        # Template-based generation
        templates = script_generator.get_available_templates()
        print("\nAvailable templates:")
        for i, template in enumerate(templates, 1):
            print(f"\n{i}. {template['name']}")
            print(f"   {template['description']}\n")
        
        while True:
            try:
                template_choice = int(input(f"Select template (1-{len(templates)}): "))
                if 1 <= template_choice <= len(templates):
                    break
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {len(templates)}")
        
        template = templates[template_choice - 1]
        print(f"\n=== {template['name']} Template ===")
        print(f"{template['description']}\n")
        
        print("Required information:")
        context = {}
        for field in template['fields']:
            value = input(f"{field['name']}: ").strip()
            context[field['id']] = value
        
        # Generate script
        script_text = script_generator.generate_script(template['id'], context)
        scenes = parse_manual_script(script_text)
        
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
        
        script_text = "\n".join(lines)
        scenes = parse_manual_script(script_text)
    
    # Preview and confirm
    if not scenes:
        print("No valid scenes found in script.")
        return
    
    if not preview_script(scenes):
        print("Script generation cancelled.")
        return
    
    # Select voice
    voice_id = select_voice()
    
    # Select style
    style_name = select_style()
    
    # Generate video
    print("\nGenerating video...")
    try:
        # Make sure there's text in every scene
        for i, scene in enumerate(scenes):
            if not scene.get('text'):
                # If no specific text is set, use voiceover as text
                if scene.get('voiceover'):
                    scenes[i]['text'] = [scene['voiceover']]
                else:
                    # Default text if nothing else is available
                    scenes[i]['text'] = [f"Scene {i+1}: {scene.get('name', 'Untitled')}"]
            
            # Ensure timing is properly formatted
            if not scene.get('timing') or 'to' not in scene.get('timing', ''):
                # Calculate a default timing if none exists
                start_time = i * 5  # 5 seconds per scene as default
                end_time = start_time + 5
                scenes[i]['timing'] = f"{start_time} to {end_time}"
        
        # Generate voice audio (optional for now)
        # audio_file = voice_system.generate_voice_for_scenes(scenes, voice_id)
        audio_file = ""  # Temporarily skip audio to focus on video
        
        # Process video with better error handling
        output_file = video_processor.process_video(scenes, audio_file, style_name)
        
        if output_file:
            print(f"\nVideo generated successfully: {output_file}")
        else:
            print("\nVideo generation failed.")
        
    except Exception as e:
        import traceback
        print(f"Error generating video: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
