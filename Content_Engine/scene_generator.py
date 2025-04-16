"""Scene generation module with NLP-based scene segmentation."""
import re
import logging
from typing import List, Dict
import nltk
from nltk.tokenize import sent_tokenize
from nltk.tokenize.punkt import PunktSentenceTokenizer
import spacy

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

def split_into_scenes(text: str) -> List[str]:
    """Split text into logical scenes using NLP.
    
    Args:
        text: Input text to split into scenes
    
    Returns:
        List of scene text segments
    """
    if not text:
        return []
        
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

def generate_scene_metadata(script_text: str) -> List[Dict]:
    """Generate metadata for each scene using NLP.
    
    Args:
        script_text: Raw script text
    
    Returns:
        List of scene dictionaries with metadata
    """
    try:
        # Split text into scenes
        scenes = split_into_scenes(script_text)
        if not scenes:
            logger.error("No scenes could be extracted from script")
            raise ValueError("Script content could not be split into scenes")
        
        # Generate metadata for each scene
        metadata = []
        for i, scene_text in enumerate(scenes, start=1):
            # Clean scene text
            scene_text = re.sub(r'\s+', ' ', scene_text).strip()
            if not scene_text:
                continue
                
            # Estimate scene duration
            duration = estimate_scene_duration(scene_text)
            
            # Create scene metadata
            scene_data = {
                'scene_number': i,
                'text': scene_text,
                'duration': duration,
                'name': f'Scene {i}'
            }
            
            # Add NLP-based metadata if available
            if nlp:
                doc = nlp(scene_text)
                # Extract key entities
                entities = [
                    {'text': ent.text, 'label': ent.label_}
                    for ent in doc.ents
                ]
                if entities:
                    scene_data['entities'] = entities
                
                # Extract main topics (noun phrases)
                topics = [chunk.text for chunk in doc.noun_chunks]
                if topics:
                    scene_data['topics'] = topics
            
            metadata.append(scene_data)
        
        logger.info(f"Generated metadata for {len(metadata)} scenes")
        return metadata
        
    except Exception as e:
        logger.error(f"Error generating scene metadata: {e}")
        raise

if __name__ == "__main__":
    sample = "Scene 1: Hello.\n\nScene 2: World."
    print("Scene Metadata:", generate_scene_metadata(sample))
