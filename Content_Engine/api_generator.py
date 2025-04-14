"""Script generation with templates and internet search."""
import os
from typing import Dict, List
from dataclasses import dataclass
import openai
import requests
from bs4 import BeautifulSoup
import json
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
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
        
        self.templates = {
            "product_demo": ScriptTemplate(
                id="product_demo",
                name="Product Demo",
                description="Showcase product features and benefits",
                style="professional",
                fields=[
                    {"id": "product_name", "name": "Product Name"},
                    {"id": "key_features", "name": "Key Features (comma-separated)"},
                    {"id": "target_audience", "name": "Target Audience"},
                    {"id": "call_to_action", "name": "Call to Action"}
                ],
                prompt_template="Create a product demo script for {product_name}. Features: {key_features}. Target: {target_audience}. CTA: {call_to_action}",
                example="Scene 1: [Product Shot]\nIntroducing our product..."
            ),
            "explainer": ScriptTemplate(
                id="explainer",
                name="Explainer Video",
                description="Break down complex concepts simply",
                style="educational",
                fields=[
                    {"id": "topic", "name": "Topic"},
                    {"id": "complexity", "name": "Complexity Level (beginner/intermediate/advanced)"},
                    {"id": "key_points", "name": "Key Points (comma-separated)"},
                    {"id": "duration", "name": "Target Duration (minutes)"}
                ],
                prompt_template="Create an explainer video script about {topic} at {complexity} level covering: {key_points}",
                example="Scene 1: [Introduction]\nToday we'll explore..."
            ),
            "vlog": ScriptTemplate(
                id="vlog",
                name="Vlog Style",
                description="Personal, engaging storytelling format",
                style="casual",
                fields=[
                    {"id": "topic", "name": "Topic"},
                    {"id": "mood", "name": "Mood (fun/serious/inspirational)"},
                    {"id": "story_points", "name": "Story Points (comma-separated)"},
                    {"id": "outro", "name": "Call to Action"}
                ],
                prompt_template="Create a {mood} vlog script about {topic} covering: {story_points}. Outro: {outro}",
                example="Scene 1: [Intro Shot]\nHey everyone! Welcome back..."
            ),
            "interview": ScriptTemplate(
                id="interview",
                name="Interview Format",
                description="Q&A style with expert insights",
                style="professional",
                fields=[
                    {"id": "topic", "name": "Interview Topic"},
                    {"id": "expert_background", "name": "Expert's Background"},
                    {"id": "questions", "name": "Key Questions (comma-separated)"},
                    {"id": "duration", "name": "Target Duration (minutes)"}
                ],
                prompt_template="Create an interview script about {topic} with an expert in {expert_background}. Questions: {questions}",
                example="Scene 1: [Studio Shot]\nWelcome to our show..."
            ),
            "story": ScriptTemplate(
                id="story",
                name="Storytelling",
                description="Narrative-driven content",
                style="cinematic",
                fields=[
                    {"id": "story_type", "name": "Story Type (case study/journey/transformation)"},
                    {"id": "main_character", "name": "Main Character/Subject"},
                    {"id": "key_events", "name": "Key Events (comma-separated)"},
                    {"id": "message", "name": "Core Message"}
                ],
                prompt_template="Create a {story_type} story about {main_character} with events: {key_events}. Message: {message}",
                example="Scene 1: [Opening Shot]\nThis is a story of..."
            ),
            "news": ScriptTemplate(
                id="news",
                name="News Report",
                description="Professional news coverage style",
                style="broadcast",
                fields=[
                    {"id": "headline", "name": "Headline"},
                    {"id": "key_points", "name": "Key Points (comma-separated)"},
                    {"id": "sources", "name": "Sources (comma-separated)"},
                    {"id": "angle", "name": "Story Angle"}
                ],
                prompt_template="Create a news report script about: {headline}. Key points: {key_points}. Sources: {sources}. Angle: {angle}",
                example="Scene 1: [News Desk]\nBreaking news..."
            )
        }
    
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
    
    def generate_script(self, template: str, additional_context: Dict) -> str:
        """Generate script using specified template and context."""
        if template not in self.templates:
            raise ValueError(f"Unknown template: {template}")
        
        template_obj = self.templates[template]
        
        try:
            # Search internet for relevant information
            search_results = self._search_internet(additional_context)
            
            # Format prompt with search results
            prompt = template_obj.prompt_template.format(**additional_context)
            if search_results:
                print("\nFound relevant information:")
                print(search_results)
                prompt += f"\n\nAdditional context from web search:\n{search_results}"
            
            if not self.api_key:
                # Fallback to template-based generation
                print("No OpenAI API key found. Using template-based generation.")
                return self._generate_template_script(template_obj, additional_context)
            
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
            
        except Exception as e:
            print(f"Error generating script: {str(e)}")
            # Fallback to template on error
            return self._generate_template_script(template_obj, additional_context)
    
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
    
    # List available templates
    print("Available templates:", generator.get_available_templates())
    
    # Generate a script with preview
    template_id = "product_demo"
    additional_context = {
        "product_name": "AI-Powered Video Editor",
        "key_features": "AI-powered editing, automatic color correction, and audio ducking",
        "target_audience": "Professional videographers and content creators",
        "call_to_action": "Try it now and transform your video editing workflow!"
    }
    
    script = generator.generate_script(template_id, additional_context)
    print("\nGenerated Script:")
    print(script)
    
    preview = generator.get_script_preview(script)
    print("\nScript Preview:")
    print(json.dumps(preview, indent=2))
