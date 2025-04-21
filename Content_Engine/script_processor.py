from typing import Dict, List, Optional
import re
from dataclasses import dataclass

@dataclass
class Scene:
    title: str
    content: str
    duration: float = 5.0
    transitions: Dict = None
    visual_style: Dict = None
    audio_style: Dict = None
    # TODO: Add support for scene metadata, tags, and multi-language content.

    def __str__(self):
        """String representation of the scene for display"""
        return self.content  # Return only content for video display

    def get_full_text(self):
        """Get full text including title for voice-over"""
        return f"{self.title}\n\n{self.content}"

class ScriptProcessor:
    """
    Processes script text into structured scenes with niche-specific settings.
    
    TODO: Add error handling for parsing, support for more niches, and unit tests.
    """
    def __init__(self):
        self.niche_settings = {
            "entertainment": {
                "scene_duration": 8.0,
                "transitions": {
                    "type": "dynamic",
                    "duration": 0.8
                },
                "visual_style": {
                    "effects": True,
                    "animations": True,
                    "quick_cuts": True,
                    "font_size": 70,
                    "font": "Impact",
                    "text_color": "white",
                    "stroke_width": 2,
                    "stroke_color": "black"
                },
                "audio_style": {
                    "pace": "fast",
                    "tone": "energetic",
                    "background_music": "upbeat"
                }
            }
        }

    def process_script(self, script_text: str, niche: str = "entertainment") -> List[Scene]:
        """Process script text into scenes."""
        try:
            # Get niche settings
            settings = self.niche_settings.get(niche, self.niche_settings["entertainment"])
            
            # Split into scenes
            raw_scenes = self._split_into_scenes(script_text)
            
            # Process each scene
            scenes = []
            for title, content in raw_scenes:
                # Clean up the text
                title = title.strip()
                content = content.strip()
                
                # Create scene with settings
                scene = Scene(
                    title=title,
                    content=content,
                    duration=settings["scene_duration"],
                    transitions=settings["transitions"],
                    visual_style=settings["visual_style"],
                    audio_style=settings["audio_style"]
                )
                scenes.append(scene)
            
            return scenes
            
        except Exception as e:
            print(f"Error processing script: {str(e)}")
            return []

    def _split_into_scenes(self, script_text: str) -> List[tuple]:
        """Split script text into scenes."""
        # Remove empty lines and normalize whitespace
        script_text = "\n".join(line.strip() for line in script_text.split("\n") if line.strip())
        
        # Split by "Scene X:" pattern
        scenes = []
        current_title = ""
        current_content = []
        
        for line in script_text.split("\n"):
            if line.lower().startswith("scene"):
                # If we have a previous scene, save it
                if current_title and current_content:
                    scenes.append((current_title, "\n".join(current_content)))
                # Start new scene
                current_title = line
                current_content = []
            else:
                current_content.append(line)
        
        # Add the last scene
        if current_title and current_content:
            scenes.append((current_title, "\n".join(current_content)))
        
        return scenes

def process_script(script_text: str, niche: str = "entertainment") -> List[Scene]:
    """Convenience function to process a script."""
    processor = ScriptProcessor()
    return processor.process_script(script_text, niche)

if __name__ == "__main__":
    # Example usage
    sample = """
    Scene 1: Introduction
    This is the first scene content.
    It can have multiple lines.

    Scene 2: Main Topic
    This is the second scene.
    With more content.

    Scene 3: Conclusion
    Final thoughts and wrap-up.
    """
    
    scenes = process_script(sample)
    for scene in scenes:
        print(f"\nTitle: {scene.title}")
        print(f"Content: {scene.content}")
        print(f"Duration: {scene.duration}s")

# TODO: Add integration tests for script processing and scene splitting.
