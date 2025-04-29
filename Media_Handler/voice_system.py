"""Voice generation system with local and cloud TTS support."""
import os
import tempfile
from typing import Dict, List, Type, Optional
from dataclasses import dataclass
import pyttsx3
import requests
from pydub import AudioSegment
import hashlib
import re
from abc import ABC, abstractmethod
import yaml
from pathlib import Path
import logging
from gtts import gTTS
from utils.config_loader import load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: Remove any unused imports after full audit

@dataclass
class VoiceConfig:
    """Voice configuration for TTS systems.
    
    Attributes:
        id: Unique voice identifier
        name: Human-readable name
        gender: Voice gender
        language: Language code
        engine: Backend engine name
        preview_text: Text for preview playback
    """
    id: str
    name: str
    gender: str
    language: str
    engine: str
    preview_text: str = "This is a sample voice preview."

class VoiceBackend(ABC):
    @abstractmethod
    def generate_voice(self, text: str, voice_id: str) -> str:
        """Generate voice audio from text. Returns path to audio file."""
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
        }
        backend_class = backends.get(provider.lower())
        if not backend_class:
            logger.error(f"Unsupported voice provider: {provider}")
            raise ValueError(f"Unsupported voice provider: {provider}")
        try:
            return backend_class(config)
        except Exception as e:
            logger.warning(f"Failed to initialize {provider} backend: {e}")
            if provider != 'local':
                logger.info("Falling back to local TTS backend")
                return LocalTTSVoiceBackend({})
            raise

class ElevenLabsVoiceBackend(VoiceBackend):
    def __init__(self, config: Dict):
        """Initialize ElevenLabs backend."""
        self.api_key = config.get('api_key') or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found in config or environment")
        
        # Test API key validity
        self._test_api_key()
        self.voices = self._load_voices()

    def _test_api_key(self):
        """Test if the API key is valid."""
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise ValueError("Invalid ElevenLabs API key")

    def _load_voices(self) -> Dict[str, VoiceConfig]:
        """Load available voices from ElevenLabs API."""
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
            voices[voice['voice_id']] = VoiceConfig(
                id=voice['voice_id'],
                name=voice['name'],
                gender=voice.get('labels', {}).get('gender', 'unknown'),
                language=voice.get('labels', {}).get('language', 'en'),
                engine='elevenlabs'
            )
        return voices

    def list_voices(self) -> Dict[str, VoiceConfig]:
        return self.voices

    def generate_voice(self, text: str, voice_id: str) -> str:
        if not text or not voice_id:
            raise ValueError("Text and voice_id are required")

        if voice_id not in self.voices:
            raise ValueError(f"Unknown voice: {voice_id}")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
        self.config = config
        self.engine = pyttsx3.init()
        self.voices = self._load_voices()

    def _load_voices(self):
        # Dynamically load all voices from pyttsx3, but only include those that can actually generate audio
        voices = {}
        test_phrase = "Test"
        
        # Skip problematic voices (David is often broken on Windows)
        problem_voices = ["DAVID", "ZIRA"]
        
        for v in self.engine.getProperty('voices'):
            # Skip known problem voices
            if any(problem in v.id.upper() for problem in problem_voices):
                logger.warning(f"Skipping known problematic voice: {v.id}")
                continue
                
            gender = getattr(v, 'gender', None)
            if not gender:
                gender = 'female' if 'female' in v.name.lower() else ('male' if 'male' in v.name.lower() else 'unknown')
            voice_id = v.id
            # Test if this voice can actually generate audio
            try:
                temp_dir = tempfile.gettempdir()
                temp_wav = os.path.join(temp_dir, f"sample_{hash(voice_id)}.wav")
                # Remove file if it exists
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                self.engine.setProperty('voice', voice_id)
                self.engine.save_to_file(test_phrase, temp_wav)
                self.engine.runAndWait()
                import time
                retries = 5
                for _ in range(retries):
                    if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 100:
                        # Try loading with pydub to ensure it's a valid WAV
                        try:
                            from pydub import AudioSegment
                            AudioSegment.from_file(temp_wav)
                            break
                        except Exception:
                            pass
                    time.sleep(0.2)
                else:
                    raise Exception("Voice test file not generated or invalid WAV.")
                # If we get here, the voice works
                voices[voice_id] = VoiceConfig(
                    id=voice_id,
                    name=v.name,
                    gender=gender,
                    language=','.join([str(l) for l in getattr(v, 'languages', ['en'])]),
                    engine='local',
                    preview_text="This is a sample voice preview."
                )
                # Clean up
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
            except Exception as e:
                logger.warning(f"Skipping non-working voice '{voice_id}': {e}")
                continue
        return voices

    def list_voices(self):
        return self.voices

    def generate_voice(self, text: str, voice_id: str) -> str:
        if voice_id not in self.voices:
            raise ValueError(f"Unknown voice: {voice_id}")
        self.engine.setProperty('voice', voice_id)
        temp_dir = tempfile.gettempdir()
        temp_wav = os.path.join(temp_dir, f"sample_{voice_id}.wav")
        self.engine.save_to_file(text, temp_wav)
        self.engine.runAndWait()
        # Wait for file to appear (pyttsx3 can be async)
        import time
        retries = 5
        for _ in range(retries):
            if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 100:
                return temp_wav
            time.sleep(0.2)
        # If still not found, raise clear error
        raise Exception(f"Failed to generate WAV file for voice '{voice_id}'. This may be a system TTS issue. Try installing more voices in Windows settings.")

class UserVoiceClone:
    """Represents a user-imported or cloned voice for local use."""
    def __init__(self, name: str, audio_samples: list, metadata: dict = None):
        self.name = name
        self.audio_samples = audio_samples  # List of file paths or audio buffers
        self.metadata = metadata or {}
        self.id = f"user_{hash(name) % 1000000}"
        self.engine = 'local-clone'
        self.gender = metadata.get('gender', 'unknown')
        self.language = metadata.get('language', 'en')
        self.preview_text = metadata.get('preview_text', "This is a sample of my custom voice.")

    def generate_voice(self, text: str) -> str:
        # Placeholder: Implement voice cloning logic or integrate with a local TTS/voice cloning library
        # For now, return one of the uploaded samples as a mock
        if self.audio_samples:
            return self.audio_samples[0]
        raise Exception("No audio samples available for this cloned voice.")

class VoiceSystem:
    """Voice system that only uses gTTS for text-to-speech."""
    def __init__(self, config: Optional[Dict] = None):
        self.config = self._load_config() if config is None else config

    def _load_config(self, config_path: str = "config.yaml") -> dict:
        try:
            return load_config(config_path)
        except Exception:
            return {}

    def get_audio_duration(self, audio_path: str) -> float:
        """Utility function to get audio duration in seconds."""
        audio = AudioSegment.from_file(audio_path)
        return audio.duration_seconds

    def generate_voice(self, text: str, voice_id: str = None) -> str:
        """Generate voice audio from text using gTTS, using language and speed from config."""
        print(f"[DIAG] VoiceSystem.generate_voice called with text='{text[:30]}...' voice_id={voice_id}")
        try:
            config = load_config()
            if not isinstance(config, dict):
                logger.error(f"Loaded config is not a dict (type={type(config)}): {config}")
                config = {}
            tts_config = config.get('tts', {}) if config else {}
            if not isinstance(tts_config, dict):
                logger.error(f"tts_config is not a dict (type={type(tts_config)}): {tts_config}")
                tts_config = {}
            language = tts_config.get('language', 'en')
            speed = float(tts_config.get('speed', 1.0))
            slow = True if speed != 1.0 else False
            output_dir = os.path.join('.', 'Output_Manager', 'outputs')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'voice_sample.mp3')
            print(f"[DIAG] gTTS params: lang={language}, slow={slow}, output_file={output_file}")
            tts = gTTS(text=text, lang=language, slow=slow)
            tts.save(output_file)
            print(f"[DIAG] gTTS saved to {output_file}")
            return os.path.abspath(output_file)
        except Exception as e:
            print(f"[DIAG] Failed to generate voice with gTTS: {e}")
            logger.error(f"Failed to generate voice with gTTS: {e}")
            return ""

if __name__ == "__main__":
    try:
        voice_system = VoiceSystem()
        print("Available voices:", {})
        print("Default voice:", None)
    except Exception as e:
        logger.error(f"VoiceSystem main error: {e}")
        print(f"VoiceSystem main error: {e}")
