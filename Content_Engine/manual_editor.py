"""Manual script and style editor for video content."""
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import os

@dataclass
class ManualStyle:
    font_size: int = 70
    font_family: str = "Impact"
    text_color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 2
    background_type: str = "color"  # color, image, or video
    background_value: str = "#000000"
    transition_type: str = "fade"
    transition_duration: float = 0.8
    text_position: str = "center"
    scene_duration: float = 5.0

class ContentEditor:
    def __init__(self):
        self.styles_path = os.path.join('Content_Engine', 'styles')
        os.makedirs(self.styles_path, exist_ok=True)
        self.default_style = ManualStyle()

    def save_style(self, name: str, style: ManualStyle):
        """Save a custom style configuration."""
        style_file = os.path.join(self.styles_path, f"{name}.json")
        with open(style_file, 'w') as f:
            json.dump(vars(style), f, indent=4)

    def load_style(self, name: str) -> ManualStyle:
        """Load a saved style configuration."""
        try:
            style_file = os.path.join(self.styles_path, f"{name}.json")
            with open(style_file, 'r') as f:
                style_dict = json.load(f)
                return ManualStyle(**style_dict)
        except FileNotFoundError:
            return self.default_style

    def create_script(self, scenes: List[Dict]) -> str:
        """Create a properly formatted script from scene data."""
        script = []
        for i, scene in enumerate(scenes, 1):
            title = scene.get('title', f'Scene {i}')
            content = scene.get('content', '')
            script.append(f"Scene {i}: {title}\n{content}\n")
        return "\n".join(script)

    def parse_script(self, script: str) -> List[Dict]:
        """Parse a script into scene data."""
        scenes = []
        current_scene = None

        for line in script.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.lower().startswith('scene'):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {'title': line, 'content': []}
            elif current_scene:
                current_scene['content'].append(line)

        if current_scene:
            scenes.append(current_scene)

        return [{
            'title': scene['title'],
            'content': '\n'.join(scene['content'])
        } for scene in scenes]

    def apply_style_to_scene(self, scene: Dict, style: ManualStyle) -> Dict:
        """Apply style settings to a scene."""
        return {
            **scene,
            'style': vars(style)
        }

def example_usage():
    # Create editor instance
    editor = ContentEditor()

    # Create a custom style
    custom_style = ManualStyle(
        font_size=80,
        text_color="yellow",
        background_type="image",
        background_value="path/to/image.jpg"
    )

    # Save the style
    editor.save_style("custom_bright", custom_style)

    # Create a script
    scenes = [
        {'title': 'Introduction', 'content': 'This is the intro scene'},
        {'title': 'Main Point', 'content': 'This is the main content'},
        {'title': 'Conclusion', 'content': 'This is the ending'}
    ]

    # Generate formatted script
    script = editor.create_script(scenes)
    print("\nGenerated Script:")
    print(script)

    # Parse the script back
    parsed_scenes = editor.parse_script(script)
    print("\nParsed Scenes:")
    for scene in parsed_scenes:
        print(f"\nTitle: {scene['title']}")
        print(f"Content: {scene['content']}")

if __name__ == "__main__":
    example_usage()
