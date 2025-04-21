"""Script generation with templates and internet search."""
import os
import json
import yaml
from typing import Dict, List, Optional, Union, Set
from dataclasses import dataclass
import openai
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from pathlib import Path
import logging
import re
from .ai_integrations import create_api_hub
import hashlib
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: Remove unused imports after full audit

@dataclass
class TemplateField:
    """Field in a script template.
    
    Attributes:
        id: Field identifier
        name: Human-readable name
        description: Description of field
        required: Whether field is required
        default: Default value
    """
    id: str
    name: str
    description: str
    required: bool = True
    default: str = ""

@dataclass
class ScriptTemplate:
    """Template for script generation.
    
    Attributes:
        id: Template identifier
        name: Template name
        description: Template description
        style: Style label
        prompt_template: Prompt format string
        fields: List of TemplateField
        example: Example script
        niche: Content niche
        version: Version string
    """
    id: str
    name: str
    description: str
    style: str
    prompt_template: str
    fields: List[TemplateField]
    example: str = ""
    niche: str = "general"
    version: str = "1.0"

    def extract_field_names(self) -> Set[str]:
        """Extract field names from the prompt template."""
        return set(re.findall(r'\{(\w+)\}', self.prompt_template))

    def validate_context(self, context: Dict[str, str]) -> Dict[str, str]:
        """Validate and prepare context for template."""
        required_fields = self.extract_field_names()
        missing_fields = required_fields - set(context.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        # Only include fields that are actually used in the template
        return {k: v for k, v in context.items() if k in required_fields}

class TemplateManager:
    """Manages loading and validation of templates."""
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            logger.error(f"Templates directory not found: {templates_dir}")
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
            logger.error(f"No template file found for niche: {niche}")
            raise FileNotFoundError(f"No template file found for niche: {niche}")
        if template_path.suffix == '.json':
            return self._load_json_templates(template_path)
        else:
            return self._load_yaml_templates(template_path)

    def _extract_template_fields(self, template_str: str) -> List[TemplateField]:
        """Extract fields from a template string."""
        field_names = set(re.findall(r'\{(\w+)\}', template_str))
        # ... implementation ...
        pass

    def _load_yaml_templates(self, template_path: Path) -> Dict[str, ScriptTemplate]:
        """Load templates from a YAML file."""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            templates = {}
            for key, value in yaml_data.items():
                if not isinstance(value, dict):
                    logger.warning(f"Template '{key}' is not a dict and will be skipped. Value: {value}")
                    continue
                templates[key] = ScriptTemplate(
                    id=value.get('id', key),
                    name=value.get('name', key),
                    description=value.get('description', ''),
                    style=value.get('style', ''),
                    prompt_template=value.get('prompt_template', ''),
                    fields=[TemplateField(**field) for field in value.get('fields', [])],
                    example=value.get('example', ''),
                    niche=value.get('niche', key),
                    version=value.get('version', '1.0')
                )
            return templates
        except Exception as e:
            logger.error(f"Failed to load YAML templates: {e}")
            raise

class ScriptGenerator:
    """Generates scripts using templates and AI.
    
    Handles template management, AI integration, and caching.
    """
    def __init__(self, config_path: str = "config.yaml", cache_dir: str = "cache"):
        """Initialize the script generator."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        # Load configuration
        self.config = self._load_config(config_path)
        self.niche = self.config.get('project', {}).get('default_niche', 'tech')
        self.dev_mode = self.config.get('project', {}).get('dev_mode', False)
        self.use_cache = self.config.get('project', {}).get('use_cache', True)
        # Initialize template manager
        self.template_manager = TemplateManager()
        self.templates = self.template_manager.load_templates(self.niche)
        # Cache available niches
        self.available_niches = self.template_manager.list_available_niches()
        # Initialize AI API Hub
        self.ai_hub = create_api_hub(self.config.get('ai_providers', {}))
        self.default_provider = self.config.get('ai_providers', {}).get('default_provider', 'openai')
        # Store API keys for different providers
        self.api_keys = {}
        # Initialize cache directory
        self.cache_dir = cache_dir
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
    # ... (rest of class unchanged for this pass)

# TODO: Remove unused imports and add robust error handling for all file operations and external calls.

    def get_template_fields(self, template_id: str) -> List[Dict]:
        """Get required fields for a template."""
        if template_id not in self.templates:
            raise ValueError(f"Unknown template ID: {template_id}")
        
        template = self.templates[template_id]
        return [
            {
                "id": field.id,
                "name": field.name,
                "description": field.description,
                "required": field.required,
                "default": field.default
            }
            for field in template.fields
        ]

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

    def generate_from_template(self, template_id: str, context: Dict[str, str]) -> str:
        """Generate script using specified template and context, with AI enhancement."""
        if template_id not in self.templates:
            raise ValueError(f"Unknown template ID: {template_id}")

        template = self.templates[template_id]
        try:
            # Validate and prepare context
            validated_context = template.validate_context(context)
            
            # Search internet for relevant information if needed
            search_results = self._search_internet(validated_context)
            if search_results:
                validated_context['search_results'] = search_results

            # Format template with validated context
            formatted_prompt = template.prompt_template.format(**validated_context)
            
            # Enhance with AI
            try:
                # Construct a comprehensive prompt for the AI
                ai_prompt = f"""
                Create a professional video script for the {self.niche} niche based on the following details:
                
                {formatted_prompt}
                
                Format the script with scene numbers and include visual descriptions in [brackets].
                Each scene should have:
                1. A clear headline
                2. Visual description in brackets
                3. The actual narration text
                
                Example format:
                Scene 1: Introduction
                [Visual description of what should be shown]
                Narration text goes here...
                """
                
                # Use AI provider to generate enhanced script
                script = self.ai_hub.generate_content(
                    ai_prompt, 
                    provider=self.default_provider,
                    content_type="script"
                )
                
                return script
            except Exception as e:
                logger.warning(f"AI enhancement failed: {e}. Using template-only generation.")
                return formatted_prompt
            
        except KeyError as e:
            raise ValueError(f"Missing required field: {str(e).strip('')}")
        except Exception as e:
            raise ValueError(f"Error generating script: {e}")

    def generate_script(self, template_id: str, context: Dict[str, str]) -> str:
        """Generate script using specified template and context (legacy method)."""
        # For backward compatibility, use the new method
        return self.generate_from_template(template_id, context)

    def _search_internet(self, context: Dict[str, str]) -> str:
        """Search internet for relevant information."""
        try:
            # Combine context values into search query
            query = " ".join(str(v) for v in context.values() if v)

            # Try multiple search endpoints
            results = []

            # Try Google News
            try:
                url = f"https://news.google.com/rss/search?q={quote_plus(query)}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')
                    items = soup.find_all('item', limit=3)
                    for item in items:
                        title = item.title.text if item.title else ""
                        desc = item.description.text if item.description else ""
                        results.append(f"- {title}: {desc}")
            except Exception as e:
                logger.error(f"Google News search failed: {str(e)}")

            # Try DuckDuckGo
            try:
                url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "RelatedTopics" in data:
                        for topic in data["RelatedTopics"][:3]:
                            results.append(f"- {topic.get('Text', '')}")
            except Exception as e:
                logger.error(f"DuckDuckGo search failed: {str(e)}")

            # Try Wikipedia
            try:
                url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&format=json"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "query" in data and "search" in data["query"]:
                        for result in data["query"]["search"][:3]:
                            results.append(f"- {result.get('title', '')}: {result.get('snippet', '')}")
            except Exception as e:
                logger.error(f"Wikipedia search failed: {str(e)}")

            return "\n".join(results) if results else ""

        except Exception as e:
            logger.error(f"Error searching internet: {str(e)}")
            return ""

    def set_api_key(self, provider: str, api_key: str) -> bool:
        """Set API key for a specific provider.
        
        Args:
            provider: Name of the AI provider (e.g., 'openai', 'anthropic')
            api_key: API key for the provider
            
        Returns:
            bool: True if API key was set successfully
        """
        provider = provider.lower()
        
        try:
            # Set API key in the appropriate place depending on provider
            if provider == 'openai':
                openai.api_key = api_key
                
            # Store the key for future use
            self.api_keys[provider] = api_key
            
            # Update the AI hub with the new key
            self.ai_hub.set_api_key(provider, api_key)
            
            logger.info(f"API key set for {provider}")
            return True
        except Exception as e:
            logger.error(f"Error setting API key for {provider}: {e}")
            return False

    def generate_with_ai(self, prompt: str, provider: str = None, options: Dict = None) -> str:
        """Generate script directly using AI without templates.
        
        Args:
            prompt: The prompt to send to the AI
            provider: Name of the AI provider to use (defaults to provider in config)
            options: Additional options for the AI provider
            
        Returns:
            str: Generated script text
        """
        if provider is None:
            provider = self.default_provider
            
        provider = provider.lower()
        
        if provider not in self.api_keys and provider not in ['openai', 'anthropic', 'llama', 'custom']:
            # Use development mode response if in dev mode
            if self.dev_mode:
                logger.warning(f"No API key for {provider}, using development mode response")
                return self._generate_dev_mode_script(prompt)
            else:
                raise ValueError(f"No API key set for provider: {provider}")
                
        if options is None:
            options = {}
            
        # Generate cache key based on provider, niche and prompt
        cache_key = f"{provider}_{self.niche}_{hashlib.md5(prompt.encode()).hexdigest()}"
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.txt")
        
        # Check if we have a cached response
        if os.path.exists(cache_file) and self.use_cache:
            with open(cache_file, 'r', encoding='utf-8') as f:
                logger.info(f"Using cached script for {provider}/{self.niche}")
                return f.read()
        
        # Default prompt enhancement based on the current niche
        enhanced_prompt = f"Write a video script for the {self.niche} niche. {prompt}\n\n"
        enhanced_prompt += "Format the script with scenes like this:\n"
        enhanced_prompt += "Scene 1: [Brief description]\n[Visual description in brackets]\nNarration text...\n\n"
        enhanced_prompt += "Scene 2: [Brief description]\n[Visual description in brackets]\nNarration text...\n"
        enhanced_prompt += "\nInclude at least 4-6 scenes with clear visual descriptions in brackets."
        
        try:
            # Use the AI hub to generate the script
            script_text = self.ai_hub.generate_content(
                prompt=enhanced_prompt,
                provider=provider,
                content_type="script",
                temperature=options.get('temperature', 0.7),
                max_tokens=options.get('max_tokens', 2000)
            )
            
            # Clean up and format the response if needed
            script_text = self._clean_script_format(script_text)
            
            # Cache the result
            if self.use_cache:
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(script_text)
            
            return script_text
            
        except Exception as e:
            logger.error(f"Error generating script with {provider}: {e}")
            
            # Fall back to a basic script format if AI generation fails
            return self._generate_fallback_script(prompt)
    
    def _generate_dev_mode_script(self, prompt: str) -> str:
        """Generate a mock script for development mode.
        
        Args:
            prompt: The prompt that would be sent to the AI
            
        Returns:
            str: A pre-defined mock script
        """
        # Generate a deterministic but varied script based on the niche and prompt
        seed = hashlib.md5((self.niche + prompt).encode()).hexdigest()
        random.seed(seed)
        
        scene_count = random.randint(4, 7)
        script_lines = []
        
        niche_terms = {
            "tech": ["technology", "innovation", "digital", "future", "AI", "gadgets", "breakthroughs"],
            "fitness": ["workout", "exercise", "health", "strength", "endurance", "nutrition", "training"],
            "cooking": ["recipe", "ingredients", "cuisine", "flavor", "technique", "dish", "chef"],
            "travel": ["destination", "adventure", "culture", "explore", "journey", "landscape", "experience"],
            "business": ["strategy", "success", "entrepreneur", "market", "growth", "innovation", "leadership"],
            "education": ["learning", "knowledge", "skills", "teaching", "development", "concepts", "understanding"]
        }
        
        terms = niche_terms.get(self.niche.lower(), ["content", "topic", "focus", "area", "subject", "theme"])
        
        for i in range(1, scene_count + 1):
            title = f"Scene {i}: Introduction to {random.choice(terms).title()}"
            if i > 1:
                title = f"Scene {i}: Exploring {random.choice(terms).title()}"
            if i == scene_count:
                title = f"Scene {i}: Conclusion and Call to Action"
                
            visual = f"[Visual: {random.choice(['Close-up shot', 'Wide angle view', 'Overhead perspective', 'Slow motion capture', 'Time-lapse sequence'])} of {random.choice(terms)}]"
            
            narration = f"In this section, we'll discuss the importance of {random.choice(terms)} and how it relates to {self.niche}. "
            style_options = ['modern', 'contemporary', 'current', 'effective']
            chosen_style = random.choice(style_options)
            narration += f"As you can see, {random.choice(terms)} plays a crucial role in {chosen_style} {self.niche} strategies."
            
            if i == scene_count:
                narration = f"To summarize, we've covered several key aspects of {self.niche}. Remember to like, subscribe, and share this video if you found it helpful."
                
            script_lines.append(f"{title}\n{visual}\n{narration}")
            
        return "\n\n".join(script_lines)
        
    def _clean_script_format(self, script_text: str) -> str:
        """Clean up and standardize the script format."""
        # Add scene numbers if missing
        if "Scene 1:" not in script_text and "SCENE 1:" not in script_text:
            # Split by double newlines and add scene numbers
            scenes = re.split(r'\n\s*\n', script_text)
            numbered_scenes = []
            
            for i, scene in enumerate(scenes, 1):
                if scene.strip():
                    numbered_scenes.append(f"Scene {i}:\n{scene.strip()}")
                    
            script_text = "\n\n".join(numbered_scenes)
            
        return script_text
        
    def _generate_fallback_script(self, prompt: str) -> str:
        """Generate a basic script format when AI generation fails."""
        # Extract a potential topic from the prompt
        topic_match = re.search(r"about ['\"]?([^'\"]+)['\"]?", prompt)
        topic = topic_match.group(1) if topic_match else "the requested topic"
        
        # Create a simple script structure
        return f"""Scene 1: Introduction
[Fade in with relevant imagery]
Welcome to our video about {topic}. Today we'll explore some key aspects that make this topic interesting and important.

Scene 2: Main Point One
[Visual showing first key concept]
Let's start by looking at the first important aspect of {topic}.

Scene 3: Main Point Two
[Visual illustrating second concept]
Another critical element to understand is how this connects to everyday applications.

Scene 4: Conclusion
[Closing visual with call to action]
Thank you for watching this introduction to {topic}. If you found this helpful, please like and subscribe for more content.
"""

    def get_script_preview(self, script: str) -> Dict:
        """Generate preview information for a script."""
        try:
            # Try using AI Hub first
            try:
                analysis_prompt = f"""
                Analyze this video script and provide a scene breakdown.
                For each scene include:
                - Scene number
                - Title
                - Description
                - Key points
                - Visual elements
                
                Return the analysis in a structured format.
                
                SCRIPT:
                {script}
                """
                
                analysis_json = self.ai_hub.generate_content(
                    analysis_prompt,
                    provider=self.default_provider,
                    content_type="script_analysis"
                )
                
                # Try to parse the response as JSON
                try:
                    return json.loads(analysis_json)
                except json.JSONDecodeError:
                    # If not JSON, try to parse the text format
                    return self._parse_script_preview(analysis_json)
                    
            except Exception as e:
                logger.warning(f"AI Hub analysis failed: {e}. Falling back to legacy method.")
                
                if not self.api_key:
                    # Fallback to basic preview if no API key
                    logger.info("No OpenAI API key found. Using basic preview generation.")
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
            logger.error(f"Error generating preview: {str(e)}")
            return self._generate_basic_preview(script)

    def generate_visual_prompts(self, scenes: List[Dict]) -> List[Dict]:
        """Generate enhanced visual prompts for scenes using AI."""
        enhanced_scenes = []
        
        for scene in scenes:
            try:
                if 'text' in scene and not scene.get('visual_prompt'):
                    # Create visual prompt from scene text
                    prompt = f"""
                    Generate a detailed visual description for a video scene based on this text:
                    "{scene['text']}"
                    
                    The description should be specific, vivid, and filmable.
                    Focus on visual elements like setting, action, colors, and mood.
                    Keep it under 50 words and make it appropriate for the {self.niche} niche.
                    """
                    
                    visual_prompt = self.ai_hub.generate_content(
                        prompt,
                        provider=self.default_provider,
                        content_type="visual_prompt"
                    )
                    
                    # Clean up and format
                    visual_prompt = visual_prompt.strip('"\'').strip()
                    scene['visual_prompt'] = visual_prompt
                    
                enhanced_scenes.append(scene)
            except Exception as e:
                logger.error(f"Error generating visual prompt: {e}")
                enhanced_scenes.append(scene)
                
        return enhanced_scenes

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
        logger.error(f"Error generating script: {e}")
