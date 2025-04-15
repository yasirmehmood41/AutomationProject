"""Voice generation system with local and cloud TTS support."""
import os
import tempfile
from typing import Dict, List, Type
from dataclasses import dataclass
import pyttsx3
import requests
from pydub import AudioSegment
import hashlib
import re
from abc import ABC, abstractmethod
import yaml
from pathlib import Path

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

    @classmethod
    def create(cls, provider: str, config: Dict) -> 'VoiceBackend':
        """Factory method to create voice backend instance."""
        backends = {
            'elevenlabs': ElevenLabsVoiceBackend,
            'local': LocalTTSVoiceBackend,
            # Add more backends here as needed
        }
        
        backend_class = backends.get(provider.lower())
        if not backend_class:
            raise ValueError(f"Unsupported voice provider: {provider}")
        
        return backend_class(config)

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

        output_dir = Path(self.config.get('project', {}).get('output_dir', './output/audio'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_file = os.path.join(output_dir, f"{voice_id}_{text_hash}.mp3")
        with open(output_file, 'wb') as f:
            f.write(response.content)
        return output_file

class LocalTTSVoiceBackend(VoiceBackend):
    def __init__(self, config: Dict):
        self.engine = pyttsx3.init()
        self.voices = self._load_voices()
        
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

        output_dir = Path(self.config.get('project', {}).get('output_dir', './output/audio'))
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(self.config.get('project', {}).get('temp_dir', './output/temp'))
        temp_dir.mkdir(parents=True, exist_ok=True)

        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        temp_wav = os.path.join(temp_dir, f"{voice_id}_{text_hash}.wav")
        output_file = os.path.join(output_dir, f"{voice_id}_{text_hash}.mp3")

        try:
            self.engine.save_to_file(text, temp_wav)
            self.engine.runAndWait()

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
        """Initialize voice system with configuration."""
        self.config = self._load_config(config_path)
        self.backend = self._initialize_backend()
        self.output_dir = self._ensure_output_dir()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                if 'voice' not in config:
                    raise ValueError("Missing 'voice' section in config")
                return config
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")

    def _initialize_backend(self) -> VoiceBackend:
        """Initialize the appropriate voice backend based on config."""
        voice_config = self.config.get('voice', {})
        provider = voice_config.get('provider', 'local')
        
        try:
            provider_config = voice_config.get(provider, {})
            return VoiceBackend.create(provider, provider_config)
        except Exception as e:
            raise ValueError(f"Failed to initialize voice backend '{provider}': {e}")

    def _ensure_output_dir(self) -> str:
        """Ensure output directory exists and return its path."""
        output_dir = Path(self.config.get('project', {}).get('output_dir', './output/audio'))
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)

    def list_available_voices(self) -> Dict[str, VoiceConfig]:
        """List available voices from the current backend."""
        return self.backend.list_voices()

    def generate_voice_for_scenes(self, scenes: List[Dict], voice_id: str) -> List[str]:
        """Generate voice audio for multiple scenes using the current backend."""
        audio_files = []
        try:
            for scene in scenes:
                if 'text' not in scene:
                    continue
                
                audio_path = self.backend.generate_voice(scene['text'], voice_id)
                if audio_path:
                    audio_files.append(audio_path)
            
            return audio_files
        except Exception as e:
            raise RuntimeError(f"Error generating voice audio: {e}")

if __name__ == "__main__":
    try:
        voice_system = VoiceSystem()
        voices = voice_system.list_available_voices()
        print("Available voices:")
        for voice_id, voice in voices.items():
            print(f"- {voice.name} ({voice_id})")
            
        scenes = [
            {"text": "Welcome to our video! Today we'll be discussing an interesting topic."},
            {"text": "Thanks for watching! Don't forget to like and subscribe."}
        ]
        
        if voices:
            first_voice_id = next(iter(voices.keys()))
            audio_files = voice_system.generate_voice_for_scenes(scenes, first_voice_id)
            print(f"Generated {len(audio_files)} audio files: {audio_files}")
    except Exception as e:
        print(f"Error: {e}")
