"""Script generation with templates and internet search."""
import os
import json
import yaml
from typing import Dict, List
from dataclasses import dataclass
import openai
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

@dataclass
class ScriptTemplate:
    id: str
    name: str
    description: str
    style: str
    fields: List[Dict]
    prompt_template: str
    example: str

class ScriptGenerator:
    def __init__(self, config_path="config.yaml"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key

        # Load config
        self.config = self._load_config(config_path)
        self.niche = self.config.get('project', {}).get('default_niche', 'tech')
        
        # Load templates based on niche
        self.templates = self.load_templates_for_niche(self.niche)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")

    def load_templates_for_niche(self, niche: str) -> Dict[str, ScriptTemplate]:
        """Load templates based on niche from either JSON or YAML file."""
        # Try JSON first
        json_path = f"templates/{niche}_script.json"
        yaml_path = f"templates/{niche}_script.yaml"
        
        if os.path.exists(json_path):
            return self._load_json_templates(json_path)
        elif os.path.exists(yaml_path):
            return self._load_yaml_templates(yaml_path)
        else:
            raise FileNotFoundError(f"No template file found for niche '{niche}' in either JSON or YAML format")

    def _load_json_templates(self, path: str) -> Dict[str, ScriptTemplate]:
        """Load templates from a JSON file."""
        try:
            with open(path, "r") as file:
                templates_data = json.load(file)
                return {key: ScriptTemplate(**value) for key, value in templates_data.items()}
        except json.JSONDecodeError:
            raise ValueError(f"Error decoding JSON from file: {path}")

    def _load_yaml_templates(self, path: str) -> Dict[str, ScriptTemplate]:
        """Load templates from a YAML file."""
        try:
            with open(path, "r") as file:
                templates_data = yaml.safe_load(file)
                return {key: ScriptTemplate(**value) for key, value in templates_data.items()}
        except yaml.YAMLError:
            raise ValueError(f"Error decoding YAML from file: {path}")

    def get_available_templates(self) -> List[Dict]:
        """Get list of available templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "style": t.style,
                "fields": t.fields
            }
            for t in self.templates.values()
        ]

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
