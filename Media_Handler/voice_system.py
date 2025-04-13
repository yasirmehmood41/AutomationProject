"""Voice generation system with local and cloud TTS support."""
import os
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass
import pyttsx3
import requests
from pydub import AudioSegment
import hashlib
import re

@dataclass
class VoiceConfig:
    """Voice configuration."""
    id: str
    name: str
    gender: str
    language: str
    engine: str
    preview_text: str = "This is a sample voice preview."

class VoiceSystem:
    """Voice generation system."""
    def __init__(self):
        # Initialize local TTS engine
        self.local_engine = pyttsx3.init()
        
        # Configure local voices
        self.local_voices = {}
        for voice in self.local_engine.getProperty('voices'):
            try:
                # Use a simple name for local voices
                voice_id = f"local_{len(self.local_voices) + 1}"
                language = voice.languages[0] if voice.languages else "en-US"
                self.local_voices[voice_id] = VoiceConfig(
                    id=voice_id,
                    name=voice.name,
                    gender=voice.gender if hasattr(voice, 'gender') else "neutral",
                    language=language,
                    engine="local"
                )
            except (IndexError, AttributeError) as e:
                print(f"Skipping voice {voice.id}: {str(e)}")
                continue
        
        # Add default voice if no voices found
        if not self.local_voices:
            self.local_voices["local_1"] = VoiceConfig(
                id="local_1",
                name="Default",
                gender="neutral",
                language="en-US",
                engine="local"
            )
        
        # Configure ElevenLabs voices
        self.elevenlabs_voices = {
            "elevenlabs_josh": VoiceConfig(
                id="elevenlabs_josh",
                name="Josh",
                gender="male",
                language="en-US",
                engine="elevenlabs"
            ),
            "elevenlabs_rachel": VoiceConfig(
                id="elevenlabs_rachel",
                name="Rachel",
                gender="female",
                language="en-US",
                engine="elevenlabs"
            ),
            "elevenlabs_sam": VoiceConfig(
                id="elevenlabs_sam",
                name="Sam",
                gender="male",
                language="en-US",
                engine="elevenlabs"
            ),
            "elevenlabs_emily": VoiceConfig(
                id="elevenlabs_emily",
                name="Emily",
                gender="female",
                language="en-US",
                engine="elevenlabs"
            )
        }
        
        # Combine all voices
        self.voices = {**self.local_voices, **self.elevenlabs_voices}
        
        # Create output directory
        os.makedirs("output_manager/audio", exist_ok=True)
        os.makedirs("output_manager/temp", exist_ok=True)
    
    def list_available_voices(self) -> Dict[str, VoiceConfig]:
        """Get available voices."""
        return self.voices
    
    def generate_voice(self, text: str, voice_id: str) -> str:
        """Generate voice audio for text."""
        if not text or not voice_id:
            raise ValueError("Text and voice_id are required")
        
        if voice_id not in self.voices:
            raise ValueError(f"Unknown voice: {voice_id}")
        
        voice = self.voices[voice_id]
        
        # Create a safe filename using hash of text
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_file = os.path.join("output_manager", "audio", f"{voice_id}_{text_hash}.mp3")
        
        try:
            if voice.engine == "local":
                # Use local TTS
                temp_wav = os.path.join("output_manager", "temp", f"{voice_id}_{text_hash}.wav")
                
                # Set voice and save to WAV first
                self.local_engine.setProperty('voice', next(v.id for v in self.local_engine.getProperty('voices')))
                self.local_engine.save_to_file(text, temp_wav)
                self.local_engine.runAndWait()
                
                # Convert WAV to MP3 using pydub
                if os.path.exists(temp_wav):
                    audio = AudioSegment.from_wav(temp_wav)
                    audio.export(output_file, format="mp3")
                    os.remove(temp_wav)  # Clean up temp file
                else:
                    raise Exception("Failed to generate WAV file")
                
            elif voice.engine == "elevenlabs":
                # Use ElevenLabs API
                api_key = os.getenv("ELEVENLABS_API_KEY")
                if not api_key:
                    raise ValueError("ElevenLabs API key not found")
                
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id.replace('elevenlabs_', '')}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": api_key
                }
                data = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.75,
                        "similarity_boost": 0.75
                    }
                }
                
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                else:
                    raise Exception(f"ElevenLabs API error: {response.text}")
            
            return output_file
            
        except Exception as e:
            print(f"Error generating voice: {str(e)}")
            # Fallback to local TTS
            if voice.engine != "local":
                print("Falling back to local TTS...")
                return self.generate_voice(text, list(self.local_voices.keys())[0])
            raise
    
    def generate_voice_for_scenes(self, scenes: List[Dict], voice_id: str) -> str:
        """Generate voice audio for multiple scenes."""
        if not scenes:
            raise ValueError("No scenes provided")
        
        # Create temporary directory for scene audio
        temp_dir = "output_manager/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate audio for each scene
        scene_files = []
        for i, scene in enumerate(scenes):
            if scene.get('voiceover'):
                try:
                    # Generate audio for scene
                    scene_file = self.generate_voice(scene['voiceover'], voice_id)
                    if os.path.exists(scene_file):  # Only add if file was created
                        scene_files.append(scene_file)
                except Exception as e:
                    print(f"Error generating voice for scene {i + 1}: {str(e)}")
                    continue
        
        if not scene_files:
            raise ValueError("No voice-over content generated")
        
        # Combine all scene audio
        text_hash = hashlib.md5(''.join(str(s) for s in scenes).encode()).hexdigest()[:10]
        output_file = os.path.join("output_manager", "audio", f"combined_{voice_id}_{text_hash}.mp3")
        
        try:
            # Load first file
            combined = AudioSegment.from_mp3(scene_files[0])
            
            # Add silence between scenes and append remaining files
            for file in scene_files[1:]:
                silence = AudioSegment.silent(duration=500)  # 0.5 seconds
                scene_audio = AudioSegment.from_mp3(file)
                combined = combined + silence + scene_audio
            
            # Export combined audio
            combined.export(output_file, format="mp3")
            
            return output_file
            
        except Exception as e:
            print(f"Error combining audio: {str(e)}")
            # Return first scene audio as fallback
            return scene_files[0] if scene_files else None
    
    def preview_voice(self, voice_id: str, text: Optional[str] = None) -> str:
        """Generate a voice preview."""
        if not text:
            voice = self.voices.get(voice_id)
            if not voice:
                raise ValueError(f"Unknown voice: {voice_id}")
            text = voice.preview_text
        
        return self.generate_voice(text, voice_id)

if __name__ == "__main__":
    # Example usage
    voice_system = VoiceSystem()
    
    # List available voices
    voices = voice_system.list_available_voices()
    print("\nAvailable voices:")
    for voice_id, config in voices.items():
        print(f"- {config.name} ({config.gender}, {config.language}, {config.engine})")
    
    # Generate preview
    preview_file = voice_system.preview_voice("local_1")
    if preview_file:
        print(f"\nPreview generated: {preview_file}")
    
    # Generate voice
    voice_file = voice_system.generate_voice(
        "Welcome to the automated video generation system.",
        "local_1"
    )
    if voice_file:
        print(f"\nVoice generated: {voice_file}")
