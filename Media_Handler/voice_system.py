"""Voice generation system with local and cloud TTS support."""
import os
import tempfile
from typing import Dict, List
from dataclasses import dataclass
import pyttsx3
import requests
from pydub import AudioSegment
import hashlib
import re
from abc import ABC, abstractmethod
import yaml

@dataclass
class VoiceConfig:
    """Voice configuration."""
    id: str
    name: str
    gender: str
    language: str
    engine: str
    preview_text: str = "This is a sample voice preview."

class VoiceBackend(ABC):
    @abstractmethod
    def generate_voice(self, text: str, voice_id: str) -> str:
        """Generate voice audio from text."""
        pass

    @abstractmethod
    def list_voices(self) -> Dict[str, VoiceConfig]:
        """List available voices for this backend."""
        pass

class ElevenLabsVoiceBackend(VoiceBackend):
    def __init__(self, config: Dict):
        self.api_key = config.get('api_key') or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found in config or environment")
        self.voices = self._load_voices()

    def _load_voices(self) -> Dict[str, VoiceConfig]:
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"ElevenLabs API error: {response.text}")

        voices = {}
        for voice in response.json().get('voices', []):
            voice_id = f"elevenlabs_{voice['voice_id']}"
            voices[voice_id] = VoiceConfig(
                id=voice_id,
                name=voice['name'],
                gender=voice.get('labels', {}).get('gender', 'unknown'),
                language=voice.get('labels', {}).get('language', 'en'),
                engine="elevenlabs"
            )
        return voices

    def list_voices(self) -> Dict[str, VoiceConfig]:
        return self.voices

    def generate_voice(self, text: str, voice_id: str) -> str:
        if not text or not voice_id:
            raise ValueError("Text and voice_id are required")

        if voice_id not in self.voices:
            raise ValueError(f"Unknown voice: {voice_id}")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id.replace('elevenlabs_', '')}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
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
        if response.status_code != 200:
            raise Exception(f"ElevenLabs API error: {response.text}")

        # Create output directory if it doesn't exist
        os.makedirs("output_manager/audio", exist_ok=True)
        
        # Save the audio file
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_file = os.path.join("output_manager", "audio", f"{voice_id}_{text_hash}.mp3")
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file

class LocalTTSVoiceBackend(VoiceBackend):
    def __init__(self, config: Dict):
        self.engine = pyttsx3.init()
        self.voices = self._load_voices()
        
        # Configure voice settings from config
        voice_name = config.get('voice_name', 'Default')
        for voice in self.engine.getProperty('voices'):
            if voice_name.lower() in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break

    def _load_voices(self) -> Dict[str, VoiceConfig]:
        voices = {}
        for voice in self.engine.getProperty('voices'):
            try:
                voice_id = f"local_{len(voices) + 1}"
                language = voice.languages[0] if voice.languages else "en-US"
                voices[voice_id] = VoiceConfig(
                    id=voice_id,
                    name=voice.name,
                    gender=voice.gender if hasattr(voice, 'gender') else "neutral",
                    language=language,
                    engine="local"
                )
            except (IndexError, AttributeError) as e:
                print(f"Skipping voice {voice.id}: {str(e)}")
                continue
        return voices

    def list_voices(self) -> Dict[str, VoiceConfig]:
        return self.voices

    def generate_voice(self, text: str, voice_id: str) -> str:
        if not text or not voice_id:
            raise ValueError("Text and voice_id are required")

        if voice_id not in self.voices:
            raise ValueError(f"Unknown voice: {voice_id}")

        # Create output directories if they don't exist
        os.makedirs("output_manager/audio", exist_ok=True)
        os.makedirs("output_manager/temp", exist_ok=True)

        # Generate unique filename
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        temp_wav = os.path.join("output_manager", "temp", f"{voice_id}_{text_hash}.wav")
        output_file = os.path.join("output_manager", "audio", f"{voice_id}_{text_hash}.mp3")

        try:
            # Save to WAV first
            self.engine.save_to_file(text, temp_wav)
            self.engine.runAndWait()

            # Convert WAV to MP3
            if os.path.exists(temp_wav):
                audio = AudioSegment.from_wav(temp_wav)
                audio.export(output_file, format="mp3")
                os.remove(temp_wav)  # Clean up temp file
                return output_file
            else:
                raise Exception("Failed to generate WAV file")
        except Exception as e:
            print(f"Error generating voice: {str(e)}")
            raise

class VoiceSystem:
    """Voice generation system with dynamic backend loading."""
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.backend = self._initialize_backend()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise Exception(f"Error loading config: {str(e)}")

    def _initialize_backend(self) -> VoiceBackend:
        """Initialize the appropriate voice backend based on config."""
        voice_config = self.config.get('voice', {})
        backend_name = voice_config.get('backend', 'local')

        if backend_name == 'elevenlabs':
            return ElevenLabsVoiceBackend(voice_config.get('elevenlabs', {}))
        elif backend_name == 'local':
            return LocalTTSVoiceBackend(voice_config.get('local', {}))
        else:
            raise ValueError(f"Unknown voice backend: {backend_name}")

    def list_available_voices(self) -> Dict[str, VoiceConfig]:
        """List available voices from the current backend."""
        return self.backend.list_voices()

    def generate_voice_for_scenes(self, scenes: List[Dict], voice_id: str) -> str:
        """Generate voice audio for multiple scenes using the current backend."""
        if not scenes:
            raise ValueError("No scenes provided")

        scene_files = []
        for scene in scenes:
            if scene.get('voiceover'):
                try:
                    scene_file = self.backend.generate_voice(scene['voiceover'], voice_id)
                    if os.path.exists(scene_file):
                        scene_files.append(scene_file)
                except Exception as e:
                    print(f"Error generating voice for scene: {str(e)}")
                    continue

        if not scene_files:
            raise Exception("No audio files were generated")

        # If only one file, return it directly
        if len(scene_files) == 1:
            return scene_files[0]

        # Combine multiple files
        try:
            combined = AudioSegment.from_mp3(scene_files[0])
            for file in scene_files[1:]:
                combined += AudioSegment.from_mp3(file)

            output_file = os.path.join("output_manager", "audio", f"combined_{hashlib.md5(str(scenes).encode()).hexdigest()[:10]}.mp3")
            combined.export(output_file, format="mp3")
            return output_file
        except Exception as e:
            print(f"Error combining audio: {str(e)}")
            return scene_files[0]  # Return first scene audio as fallback

if __name__ == "__main__":
    # Example usage
    voice_system = VoiceSystem()
    
    # List available voices
    voices = voice_system.list_available_voices()
    print("\nAvailable voices:")
    for voice_id, config in voices.items():
        print(f"- {config.name} ({config.gender}, {config.language}, {config.engine})")

    # Generate voice for scenes
    scenes = [
        {'voiceover': 'Welcome to our demo!'},
        {'voiceover': 'This is an example of multi-scene voice generation.'}
    ]
    
    try:
        output_file = voice_system.generate_voice_for_scenes(scenes, next(iter(voices.keys())))
        print(f"\nGenerated audio file: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
