"""Scene generation module with NLP-based scene segmentation."""
import re
import logging
import json
from typing import List, Dict, Optional, Union
import nltk
from nltk.tokenize import sent_tokenize
from nltk.tokenize.punkt import PunktSentenceTokenizer
import spacy
from pathlib import Path
import os
from .ai_integrations import create_api_hub

# Initialize logging
logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
except Exception as e:
    logger.warning(f"Failed to download NLTK data: {e}")

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except Exception as e:
    logger.warning(f"Failed to load spaCy model: {e}. Using basic tokenization.")
    nlp = None

# Initialize AI API Hub
try:
    from yaml import safe_load
    config_path = Path("config.yaml")
    config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = safe_load(f)
    ai_hub = create_api_hub(config.get('ai_providers', {}))
    default_provider = config.get('ai_providers', {}).get('default_provider', 'openai')
except Exception as e:
    logger.warning(f"Failed to initialize AI Hub: {e}. Using fallback methods.")
    ai_hub = None
    default_provider = None

def estimate_scene_duration(text: str, words_per_second: float = 2.5) -> float:
    """Estimate scene duration based on word count.
    
    Args:
        text: Scene text content
        words_per_second: Average speaking speed (default 2.5 words/sec)
    
    Returns:
        Estimated duration in seconds
    """
    words = len(text.split())
    duration = words / words_per_second
    return max(5.0, duration)  # Minimum 5 seconds

def extract_visual_cues(text: str) -> str:
    """Extract visual cues from bracketed text.
    
    Args:
        text: Scene text content
    
    Returns:
        Extracted visual cue text or empty string
    """
    matches = re.findall(r'\[(.*?)\]', text)
    if matches:
        return ' '.join(matches)
    return ""

def generate_ai_visual_description(text: str, niche: str = "tech") -> str:
    """Generate a visual description using AI if available.
    
    Args:
        text: Scene text content
        niche: Content niche
        
    Returns:
        AI-generated visual description or empty string
    """
    if not ai_hub:
        return ""
        
    try:
        prompt = f"""
        Generate a detailed visual description for a video scene based on this text:
        "{text}"
        
        The description should be specific, vivid, and filmable.
        Focus on visual elements like setting, action, colors, and mood.
        Keep it under 50 words and make it appropriate for the {niche} niche.
        """
        
        description = ai_hub.generate_content(
            prompt,
            provider=default_provider,
            content_type="visual_prompt"
        )
        
        # Clean up and format
        return description.strip('"\'').strip()
    except Exception as e:
        logger.error(f"Error generating visual description: {e}")
        return ""

def split_into_scenes(text: str) -> List[str]:
    """Split text into logical scenes using NLP.
    
    Args:
        text: Input text to split into scenes
    
    Returns:
        List of scene text segments
    """
    if not text:
        return []
    
    # First check if the script is already formatted with scene markers
    scene_markers = re.findall(r'Scene\s+\d+[:\.-]', text, re.IGNORECASE)
    if scene_markers:
        # Script is already structured with scene markers
        scenes = []
        parts = re.split(r'(Scene\s+\d+[:\.-])', text, flags=re.IGNORECASE)
        # --- FIX: Correctly group scene headers and their content ---
        current_scene = ''
        for idx in range(1, len(parts), 2):
            header = parts[idx]
            content = parts[idx + 1] if (idx + 1) < len(parts) else ''
            scene_text = (header + content).strip()
            if scene_text:
                scenes.append(scene_text)
        # Edge case: if script starts with a scene header
        if len(scenes) == 0 and len(parts) >= 2:
            scenes.append(parts[0] + parts[1])
        # --- FIX: Remove empty scenes and strip whitespace ---
        scenes = [s.strip() for s in scenes if s.strip()]
        print(f"[DEBUG] split_into_scenes (scene marker logic) found {len(scenes)} scenes.")
        return scenes
        
    try:
        # Try using spaCy for advanced NLP
        if nlp:
            doc = nlp(text)
            scenes = []
            current_scene = []
            
            for sent in doc.sents:
                current_scene.append(sent.text)
                
                # Start new scene on topic change or strong punctuation
                if (
                    sent.text.strip().endswith(('.', '!', '?')) and
                    len(current_scene) >= 2
                ):
                    scenes.append(' '.join(current_scene))
                    current_scene = []
            
            # Add remaining sentences
            if current_scene:
                scenes.append(' '.join(current_scene))
                
            return scenes
            
        # Fallback to NLTK sentence tokenization
        sentences = sent_tokenize(text)
        scenes = []
        current_scene = []
        
        for sent in sentences:
            current_scene.append(sent)
            if len(current_scene) >= 2:
                scenes.append(' '.join(current_scene))
                current_scene = []
        
        # Add remaining sentences
        if current_scene:
            scenes.append(' '.join(current_scene))
        
        return scenes
        
    except Exception as e:
        logger.error(f"Error splitting scenes: {e}")
        # Basic fallback using double newlines
        return [scene.strip() for scene in text.split('\n\n') if scene.strip()]

def ai_scene_segmentation(script_text: str) -> List[Dict]:
    """Use AI to segment script into scenes with rich metadata.
    
    Args:
        script_text: Raw script text
        
    Returns:
        List of scene dictionaries with metadata
    """
    if not ai_hub:
        return []
        
    try:
        prompt = f"""
        Analyze this script and break it down into scenes:
        
        {script_text}
        
        For each scene, extract the following information:
        1. Scene number
        2. Scene title/name
        3. Scene content (text)
        4. Visual description (what should be shown)
        5. Suggested duration in seconds
        6. Transition type (cut, fade, dissolve, etc.)
        
        Return the results as a valid JSON array of objects with these properties:
        - scene_number: integer
        - title: string
        - text: string (the narration/speech text)
        - visual_prompt: string (description of what to show)
        - duration: float (in seconds)
        - transition: string
        """
        
        result = ai_hub.generate_content(
            prompt,
            provider=default_provider,
            content_type="scene_data"
        )
        
        try:
            # Parse the JSON response
            scenes = json.loads(result)
            if isinstance(scenes, list) and len(scenes) > 0:
                # Validate the structure
                valid_scenes = []
                for scene in scenes:
                    if 'text' in scene and ('scene_number' in scene or 'title' in scene):
                        # Clean scene text
                        scene['text'] = re.sub(r'\s+', ' ', scene['text']).strip()
                        
                        # Add default duration if missing
                        if 'duration' not in scene:
                            scene['duration'] = estimate_scene_duration(scene['text'])
                            
                        valid_scenes.append(scene)
                
                if valid_scenes:
                    return valid_scenes
        except Exception as e:
            logger.error(f"Error parsing AI scene segmentation: {e}")
            
        return []
            
    except Exception as e:
        logger.error(f"Error in AI scene segmentation: {e}")
        return []

def generate_scene_metadata(script_text: str) -> List[Dict]:
    """Generate metadata for each scene using NLP and AI.
    
    Args:
        script_text: Raw script text
    
    Returns:
        List of scene dictionaries with metadata
    """
    try:
        # --- FORCE DISABLE AI SEGMENTATION (ALWAYS USE LOCAL LOGIC FOR SCENE SPLITTING) ---
        # This ensures we NEVER use fallback/mock/AI API for segmentation, always parse the user's script directly
        ai_hub = None
        
        # Split text into scenes using NLP
        scenes = split_into_scenes(script_text)
        print(f"[DEBUG] split_into_scenes returned {len(scenes)} scenes.")
        if not scenes:
            logger.error("No scenes could be extracted from script")
            raise ValueError("Script content could not be split into scenes")
        
        # Generate metadata for each scene
        metadata = []
        for i, scene_text in enumerate(scenes, start=1):
            scene_text = re.sub(r'\s+', ' ', scene_text).strip()
            if not scene_text:
                continue
            visual_prompt = extract_visual_cues(scene_text)
            clean_text = re.sub(r'\[.*?\]', '', scene_text).strip()
            scene_title = f"Scene {i}"
            title_match = re.match(r'Scene\s+\d+[:\.\-]\s*(.*?)[\.\n]', scene_text, re.IGNORECASE)
            if title_match:
                scene_title = title_match.group(1).strip()
            duration = estimate_scene_duration(clean_text)
            scene_data = {
                'scene_number': i,
                'title': scene_title,
                'text': clean_text,
                'duration': duration,
                'transition': 'fade'
            }
            if visual_prompt:
                scene_data['visual_prompt'] = visual_prompt
            # Don't use AI for visual description
            if nlp:
                doc = nlp(clean_text)
                entities = [
                    {'text': ent.text, 'label': ent.label_}
                    for ent in doc.ents
                ]
                if entities:
                    scene_data['entities'] = entities
                topics = [chunk.text for chunk in doc.noun_chunks]
                if topics:
                    scene_data['topics'] = topics
            metadata.append(scene_data)
        logger.info(f"Generated metadata for {len(metadata)} scenes")
        print(f"[DEBUG] Final scene metadata count: {len(metadata)}")
        return metadata
    except Exception as e:
        logger.error(f"Error generating scene metadata: {e}")
        raise

def enhance_scene_metadata(scenes: List[Dict], niche: str = "tech") -> List[Dict]:
    """Enhance existing scene metadata with AI-generated suggestions.
    
    Args:
        scenes: List of scene dictionaries
        niche: Content niche
        
    Returns:
        Enhanced scene metadata
    """
    if not ai_hub or not scenes:
        return scenes
        
    try:
        current_scenes_json = json.dumps(scenes, indent=2)
        
        prompt = f"""
        Enhance these video scenes for the {niche} niche:
        
        {current_scenes_json}
        
        For each scene, suggest improvements for:
        1. More engaging titles
        2. Better visual descriptions if missing or generic
        3. Optimized duration (5-15 seconds per scene)
        4. Appropriate transitions (cut, fade, dissolve, wipe, zoom)
        5. Add a mood/tone suggestion (serious, upbeat, emotional, etc.)
        
        Return the enhanced scenes as a valid JSON array with the same structure plus any new fields.
        """
        
        result = ai_hub.generate_content(
            prompt,
            provider=default_provider,
            content_type="scene_enhancements"
        )
        
        try:
            enhanced_scenes = json.loads(result)
            if isinstance(enhanced_scenes, list) and len(enhanced_scenes) > 0:
                logger.info(f"Enhanced {len(enhanced_scenes)} scenes with AI")
                return enhanced_scenes
        except Exception as e:
            logger.error(f"Error parsing AI scene enhancements: {e}")
            
    except Exception as e:
        logger.error(f"Error enhancing scenes with AI: {e}")
        
    return scenes

if __name__ == "__main__":
    sample = "Scene 1: Hello.\n\nScene 2: World."
    print("Scene Metadata:", generate_scene_metadata(sample))
