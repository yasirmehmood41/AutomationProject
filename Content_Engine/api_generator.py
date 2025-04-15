"""Script generation with templates and internet search."""
import os
import json
import yaml
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import openai
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from pathlib import Path

@dataclass
class ScriptTemplate:
    """Template for script generation."""
    id: str
    name: str
    description: str
    style: str
    fields: List[Dict]
    prompt_template: str
    example: str = ""
    niche: str = "general"
    version: str = "1.0"

class TemplateManager:
    """Manages loading and validation of templates."""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    def get_template_path(self, niche: str) -> Optional[Path]:
        """Get the template file path for a given niche."""
        yaml_path = self.templates_dir / f"{niche}_script.yaml"
        json_path = self.templates_dir / f"{niche}_script.json"
        
        if yaml_path.exists():
            return yaml_path
        elif json_path.exists():
            return json_path
        return None

    def list_available_niches(self) -> List[str]:
        """List all available niche templates."""
        niches = []
        for file in self.templates_dir.glob("*_script.*"):
            if file.suffix in ['.json', '.yaml']:
                niche = file.stem.replace('_script', '')
                niches.append(niche)
        return sorted(list(set(niches)))

    def load_templates(self, niche: str) -> Dict[str, ScriptTemplate]:
        """Load templates for a specific niche."""
        template_path = self.get_template_path(niche)
        if not template_path:
            raise FileNotFoundError(f"No template file found for niche: {niche}")
            
        if template_path.suffix == '.json':
            return self._load_json_templates(template_path)
        else:
            return self._load_yaml_templates(template_path)

    def _load_json_templates(self, path: Path) -> Dict[str, ScriptTemplate]:
        """Load templates from a JSON file."""
        try:
            with path.open('r') as file:
                templates_data = json.load(file)
                return self._process_templates(templates_data, path.stem.replace('_script', ''))
        except json.JSONDecodeError as e:
            raise ValueError(f"Error decoding JSON from {path}: {e}")

    def _load_yaml_templates(self, path: Path) -> Dict[str, ScriptTemplate]:
        """Load templates from a YAML file."""
        try:
            with path.open('r') as file:
                templates_data = yaml.safe_load(file)
                return self._process_templates(templates_data, path.stem.replace('_script', ''))
        except yaml.YAMLError as e:
            raise ValueError(f"Error decoding YAML from {path}: {e}")

    def _process_templates(self, data: Dict, niche: str) -> Dict[str, ScriptTemplate]:
        """Process and validate template data."""
        templates = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Ensure required fields are present
                required_fields = ['name', 'description', 'style', 'fields', 'prompt_template']
                missing_fields = [f for f in required_fields if f not in value]
                if missing_fields:
                    raise ValueError(f"Template '{key}' missing required fields: {missing_fields}")
                
                # Add template metadata
                value['id'] = key
                value['niche'] = niche
                templates[key] = ScriptTemplate(**value)
            else:
                # Handle flat template structure (like in tech_script.yaml)
                templates[key] = ScriptTemplate(
                    id=key,
                    name=key.title(),
                    description=f"{key.title()} template for {niche} niche",
                    style="default",
                    fields=[],
                    prompt_template=str(value),
                    niche=niche
                )
        return templates

class ScriptGenerator:
    """Generates scripts using templates and AI."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the script generator."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key

        # Load configuration
        self.config = self._load_config(config_path)
        self.niche = self.config.get('project', {}).get('default_niche', 'tech')
        
        # Initialize template manager
        self.template_manager = TemplateManager()
        self.templates = self.template_manager.load_templates(self.niche)
        
        # Cache available niches
        self.available_niches = self.template_manager.list_available_niches()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                if 'project' not in config:
                    raise ValueError("Missing 'project' section in config")
                return config
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")

    def get_available_templates(self, niche: Optional[str] = None) -> List[Dict]:
        """Get list of available templates for a specific niche or current niche."""
        if niche and niche != self.niche:
            try:
                templates = self.template_manager.load_templates(niche)
            except FileNotFoundError:
                return []
        else:
            templates = self.templates

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "style": t.style,
                "fields": t.fields,
                "niche": t.niche,
                "version": t.version
            }
            for t in templates.values()
        ]

    def get_available_niches(self) -> List[str]:
        """Get list of all available niches."""
        return self.available_niches

    def switch_niche(self, niche: str) -> bool:
        """Switch to a different niche template set."""
        if niche not in self.available_niches:
            return False
        
        try:
            self.templates = self.template_manager.load_templates(niche)
            self.niche = niche
            return True
        except Exception:
            return False

    def generate_script(self, template_id: str, context: Dict) -> str:
        """Generate script using specified template and context."""
        if template_id not in self.templates:
            raise ValueError(f"Unknown template ID: {template_id}")

        template = self.templates[template_id]
        try:
            # Search internet for relevant information
            search_results = self._search_internet(context)

            # Format prompt with search results
            prompt = template.prompt_template.format(**context)
            if search_results:
                print("\nFound relevant information:")
                print(search_results)
                prompt += f"\n\nAdditional context from web search:\n{search_results}"

            if not self.api_key:
                # Fallback to template-based generation
                print("No OpenAI API key found. Using template-based generation.")
                return self._generate_template_script(template, context)

            # Generate script using OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional video script writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content

        except KeyError as e:
            raise ValueError(f"Missing required context field: {e}")
        except Exception as e:
            print(f"Error generating script: {str(e)}")
            # Fallback to template on error
            return self._generate_template_script(template, context)

    def _search_internet(self, context: Dict) -> str:
        """Search internet for relevant information."""
        try:
            # Combine context values into search query
            query = " ".join(str(v) for v in context.values() if v)

            # Try multiple search endpoints
            results = []

            # Try Google News
            try:
                url = f"https://news.google.com/rss/search?q={quote_plus(query)}"
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')
                    items = soup.find_all('item', limit=3)
                    for item in items:
                        title = item.title.text if item.title else ""
                        desc = item.description.text if item.description else ""
                        results.append(f"- {title}: {desc}")
            except Exception as e:
                print(f"Google News search failed: {str(e)}")

            # Try DuckDuckGo
            try:
                url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if "RelatedTopics" in data:
                        for topic in data["RelatedTopics"][:3]:
                            results.append(f"- {topic.get('Text', '')}")
            except Exception as e:
                print(f"DuckDuckGo search failed: {str(e)}")

            # Try Wikipedia
            try:
                url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&format=json"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if "query" in data and "search" in data["query"]:
                        for result in data["query"]["search"][:3]:
                            results.append(f"- {result.get('title', '')}: {result.get('snippet', '')}")
            except Exception as e:
                print(f"Wikipedia search failed: {str(e)}")

            return "\n".join(results) if results else ""

        except Exception as e:
            print(f"Error searching internet: {str(e)}")
            return ""

    def _generate_template_script(self, template: ScriptTemplate, context: Dict) -> str:
        """Generate a basic script using the template example."""
        if template.id == "product_demo":
            return f"""Scene 1: [Product Shot]
Introducing {context['product_name']}, the revolutionary solution designed for {context['target_audience']}.

Scene 2: [Feature Showcase]
Let me show you our key features:
{self._format_list(context['key_features'])}

Scene 3: [Benefits]
Perfect for {context['target_audience']}, this product will transform your experience.

Scene 4: [Call to Action]
{context['call_to_action']}"""

        elif template.id == "explainer":
            return f"""Scene 1: [Introduction]
Today, we'll explore {context['topic']} at a {context['complexity']} level.

Scene 2: [Key Points]
Let's break down the main concepts:
{self._format_list(context['key_points'])}

Scene 3: [Summary]
Now you understand the basics of {context['topic']}."""

        elif template.id == "vlog":
            return f"""Scene 1: [Intro Shot]
Hey everyone! Welcome back to the channel. Today we're talking about {context['topic']}.

Scene 2: [Main Content]
{self._format_list(context['story_points'])}

Scene 3: [Outro]
{context['outro']}"""

        elif template.id == "interview":
            return f"""Scene 1: [Studio Shot]
Welcome to our show. Today we're joined by an expert in {context['topic']}.

Scene 2: [Interview]
{self._format_list(context['questions'], prefix='Q:')}

Scene 3: [Closing]
Thank you for sharing your insights with us."""

        elif template.id == "story":
            return f"""Scene 1: [Opening Shot]
This is the story of {context['main_character']}.

Scene 2: [Story Development]
{self._format_list(context['key_events'])}

Scene 3: [Conclusion]
{context['message']}"""

        elif template.id == "news":
            return f"""Scene 1: [News Desk]
Breaking news: {context['headline']}

Scene 2: [Report]
{self._format_list(context['key_points'])}

Scene 3: [Sources]
According to {context['sources']}."""

        else:
            return template.example

    def _format_list(self, items: str, prefix: str = "-") -> str:
        """Format a comma-separated string into a bulleted list."""
        if isinstance(items, str):
            items = [item.strip() for item in items.split(",")]
        return "\n".join(f"{prefix} {item}" for item in items)

    def get_script_preview(self, script: str) -> Dict:
        """Generate preview information for a script."""
        try:
            if not self.api_key:
                # Fallback to basic preview if no API key
                print("No OpenAI API key found. Using basic preview generation.")
                return self._generate_basic_preview(script)

            # Use OpenAI to analyze script
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Analyze this video script and provide scene breakdown."},
                    {"role": "user", "content": script}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            # Parse analysis
            analysis = response.choices[0].message.content
            return self._parse_script_preview(analysis)

        except Exception as e:
            print(f"Error generating preview: {str(e)}")
            return self._generate_basic_preview(script)

    def _generate_basic_preview(self, script: str) -> Dict:
        """Generate basic preview information without API."""
        scenes = []
        current_scene = None

        for line in script.split("\n"):
            if line.startswith("Scene"):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {
                    "title": line.strip(),
                    "content": "",
                    "estimated_duration": 0,
                    "word_count": 0
                }
            elif current_scene and line.strip():
                current_scene["content"] += line + "\n"
                current_scene["word_count"] = len(current_scene["content"].split())
                current_scene["estimated_duration"] = current_scene["word_count"] / 2

        if current_scene:
            scenes.append(current_scene)

        return {
            "format": "Standard Video Script",
            "total_scenes": len(scenes),
            "estimated_duration": sum(s["estimated_duration"] for s in scenes),
            "scenes": scenes
        }

    def _parse_script_preview(self, analysis: str) -> Dict:
        """Parse script analysis into preview format."""
        scenes = []
        current_scene = None

        for line in analysis.split("\n"):
            if line.startswith("Scene"):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {
                    "title": line,
                    "content": "",
                    "estimated_duration": 0,
                    "word_count": 0
                }
            elif current_scene:
                current_scene["content"] += line + "\n"
                current_scene["word_count"] = len(current_scene["content"].split())
                current_scene["estimated_duration"] = current_scene["word_count"] / 2

        if current_scene:
            scenes.append(current_scene)

        return {
            "format": "Standard Video Script",
            "total_scenes": len(scenes),
            "estimated_duration": sum(s["estimated_duration"] for s in scenes),
            "scenes": scenes
        }

if __name__ == "__main__":
    # Example usage
    generator = ScriptGenerator()
    try:
        script = generator.generate_script("product_demo", {
            "product_name": "Gizmo",
            "key_features": "fast, efficient",
            "target_audience": "tech enthusiasts",
            "call_to_action": "buy now"
        })
        print(script)
    except Exception as e:
        print(f"Error generating script: {e}")
