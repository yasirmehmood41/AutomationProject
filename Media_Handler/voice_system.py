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
    """Voice system that coordinates between different voice backends and user voices.
    
    Handles voice selection, fallback logic, and mock/dev voices.
    """
    def __init__(self, config: Optional[Dict] = None):
        self.config = self._load_config() if config is None else config
        self.backends = {}
        self.user_voices = []  # List of UserVoiceClone
        self._init_backends()
        # Always enable dev mode to ensure test voices are available
        self.dev_mode = True
        self.api_key_set = False
        self.default_voice_id = None
        self.system_default_voice_id = None
        self._set_default_working_voice()
        # Add mock voices to ensure we always have at least one option
        self.add_mock_voices()

    def _load_config(self, config_path: str = "config.yaml") -> dict:
        """Load configuration from YAML file. Returns dict or empty dict on failure."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading voice system config: {e}")
            return {}

    def _set_default_working_voice(self):
        """Detect and set the first working system voice as default, and always test the system default voice (no id)."""
        voices = self.backends.get('local', None)
        # 1. Test system default voice (no id specified)
        try:
            sample_path = voices.generate_voice("Test", None)
            if sample_path:
                self.system_default_voice_id = 'system_default'
        except Exception:
            pass
        # 2. Test all listed voices
        if voices:
            for vid, v in voices.list_voices().items():
                try:
                    sample_path = voices.generate_voice("Test", vid)
                    if sample_path:
                        if not self.default_voice_id:
                            self.default_voice_id = vid
                        # If system default not set, use first working
                        if not self.system_default_voice_id:
                            self.system_default_voice_id = vid
                        break
                except Exception:
                    continue
        # 3. Fallback to user voice if no system voice works
        if not self.default_voice_id and self.user_voices:
            self.default_voice_id = self.user_voices[0].id
            if not self.system_default_voice_id:
                self.system_default_voice_id = self.user_voices[0].id

    def get_default_voice(self):
        return self.default_voice_id or self.system_default_voice_id

    def get_system_default_voice(self):
        return self.system_default_voice_id

    def add_user_voice(self, name: str, audio_samples: list, metadata: dict = None):
        clone = UserVoiceClone(name, audio_samples, metadata)
        self.user_voices.append(clone)

    def _init_backends(self):
        """Initialize voice backends."""
        self.backend = LocalTTSVoiceBackend(self.config)
        self.backends = {
            'local': self.backend
        }
        
        # Try to load other backends
        try:
            if self.config.get('elevenlabs', {}).get('api_key') or os.getenv("ELEVENLABS_API_KEY"):
                self.backends['elevenlabs'] = ElevenLabsVoiceBackend(self.config.get('elevenlabs', {}))
                self.api_key_set = True
        except Exception as e:
            logger.warning(f"Failed to initialize ElevenLabs backend: {e}")

    def add_mock_voices(self):
        """Add mock voices for development/testing purposes."""
        if not self.dev_mode:
            return
        
        # Always add at least one working test voice
        mock_voice_id = "mock_voice_1"
        self._mock_voices = {
            mock_voice_id: VoiceConfig(
                id=mock_voice_id,
                name="Test Voice (Always Available)",
                gender="neutral",
                language="en",
                engine="mock",
                preview_text="This is a sample of the test voice that is always available."
            )
        }
        
        # Set as default if no other default exists
        if not self.default_voice_id:
            self.default_voice_id = mock_voice_id
        if not self.system_default_voice_id:
            self.system_default_voice_id = mock_voice_id

    def list_available_voices(self) -> Dict[str, VoiceConfig]:
        voices = {}
        # Local/system TTS voices
        for backend_name, backend in self.backends.items():
            try:
                backend_voices = backend.list_voices()
                voices.update(backend_voices)
            except Exception as e:
                logger.warning(f"Failed to list voices from {backend_name}: {e}")
        # User-imported/cloned voices
        for clone in self.user_voices:
            voices[clone.id] = VoiceConfig(
                id=clone.id,
                name=clone.name,
                gender=clone.gender,
                language=clone.language,
                engine=clone.engine,
                preview_text=clone.preview_text
            )
        # Add mock voices if present
        if hasattr(self, '_mock_voices'):
            voices.update(self._mock_voices)
        return voices
    
    def generate_voice(self, text: str, voice_id: str = None) -> str:
        """Generate voice audio from text using the appropriate backend. Always fallback to a working voice if requested one is missing."""
        try:
            available_voices = self.list_available_voices()
            # Always handle mock voices first
            if voice_id and str(voice_id).startswith("mock"):
                return self._generate_mock_voice(text, voice_id)
            # Handle system default
            if voice_id == 'system_default':
                voice_id = None  # pyttsx3 uses None for system default
                backend = self.backends.get('local')
                if not backend:
                    raise ValueError("No local TTS backend available")
                return backend.generate_voice(text, voice_id)
            # Handle user/cloned voices
            for voice in self.user_voices:
                if voice.id == voice_id:
                    return voice.generate_voice(text)
            # Look for voice in all backends
            for backend_name, backend in self.backends.items():
                try:
                    voices = backend.list_voices()
                    if voice_id in voices:
                        return backend.generate_voice(text, voice_id)
                except Exception as e:
                    logger.warning(f"Error generating voice with {backend_name}: {e}")
                    continue
            # If requested voice_id is not available, fallback to any available voice
            fallback_voice_id = None
            if available_voices:
                fallback_voice_id = next(iter(available_voices.keys()))
                logger.warning(f"Requested voice '{voice_id}' not found. Falling back to available voice '{fallback_voice_id}'.")
                # Try to use the fallback voice
                for backend_name, backend in self.backends.items():
                    try:
                        voices = backend.list_voices()
                        if fallback_voice_id in voices:
                            return backend.generate_voice(text, fallback_voice_id)
                    except Exception as e:
                        logger.warning(f"Error generating fallback voice with {backend_name}: {e}")
                        continue
            # Fallback to default voice if none specified
            if self.default_voice_id:
                logger.warning(f"Falling back to default voice '{self.default_voice_id}'.")
                return self.generate_voice(text, self.default_voice_id)
            # No voice found, generate fallback audio
            logger.warning("No available voices found. Generating silent fallback audio.")
            return self._generate_fallback_audio(text, voice_id)
        except Exception as e:
            logger.error(f"Failed to generate voice: {e}")
            return self._generate_fallback_audio(text)

    def _generate_mock_voice(self, text: str, voice_id: str) -> str:
        """Generate audio for mock test voices used in development mode."""
        try:
            from gtts import gTTS
            # Create a temporary file for the audio
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(temp_dir, f"mock_voice_{hash(text) % 100000}.mp3")
            # Use Google TTS as a reliable fallback
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_file)
            return output_file
        except Exception as e:
            logger.error(f"Failed to generate mock voice: {e}")
            # If gTTS fails, create a silent audio file as last resort
            return self._generate_fallback_audio(text, f"Mock Voice {voice_id}")

    def generate_voice_for_scenes(self, scenes: List[Dict], voice_id: str) -> List[str]:
        """Generate voice audio for multiple scenes using the current backend."""
        audio_files = []
        try:
            for scene in scenes:
                if 'text' not in scene:
                    continue
                
                audio_path = self.generate_voice(scene['text'], voice_id)
                if audio_path:
                    audio_files.append(audio_path)
            
            return audio_files
        except Exception as e:
            raise RuntimeError(f"Error generating voice audio: {e}")

    def _generate_fallback_audio(self, text: str, voice_name: str = None) -> str:
        """Generate a silent audio file as fallback."""
        try:
            # Generate a silent audio file with duration based on text length
            words = len(re.findall(r'\w+', text))
            duration_ms = max(1000, words * 300)  # Rough estimate: 300ms per word, minimum 1 second
            
            silence = AudioSegment.silent(duration=duration_ms)
            
            # Save to a temporary file
            temp_dir = Path("output/temp_audio") 
            temp_dir.mkdir(parents=True, exist_ok=True)
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            voice_suffix = f"_{voice_name}" if voice_name else ""
            temp_file = temp_dir / f"mock_audio{voice_suffix}_{text_hash}.mp3"
            
            silence.export(str(temp_file), format="mp3")
            
            return str(temp_file)
        except Exception as e:
            logger.error(f"Failed to generate fallback audio: {e}")
            # As a final fallback, just return an empty string
            return ""

    def list_system_voices(self) -> Dict[str, VoiceConfig]:
        """Return only working system/local voices."""
        voices = {}
        backend = self.backends.get('local')
        if backend:
            voices = backend.list_voices()
        return voices

    def list_user_voices(self) -> Dict[str, VoiceConfig]:
        """Return only user-imported/cloned voices with samples."""
        voices = {}
        for clone in self.user_voices:
            try:
                # Check if at least one sample exists
                if clone.audio_samples and len(clone.audio_samples) > 0:
                    voices[clone.id] = VoiceConfig(
                        id=clone.id,
                        name=clone.name,
                        gender=clone.gender,
                        language=clone.language,
                        engine=clone.engine,
                        preview_text=clone.preview_text
                    )
            except Exception as e:
                logger.warning(f"Skipping invalid user voice '{clone.name}': {e}")
        return voices

    def list_api_voices(self) -> Dict[str, VoiceConfig]:
        """Return only API/outsource voices with valid config/API key."""
        voices = {}
        for backend_name, backend in self.backends.items():
            if backend_name == 'local':
                continue
            try:
                backend_voices = backend.list_voices()
                voices.update(backend_voices)
            except Exception as e:
                logger.warning(f"Failed to list API voices from {backend_name}: {e}")
        return voices

    def list_all_voices(self) -> Dict[str, Dict[str, VoiceConfig]]:
        """Return a dict of all validated voices by category, always including mock voices if present."""
        voices_system = self.list_system_voices()
        voices_user = self.list_user_voices()
        voices_api = self.list_api_voices()
        # Always merge in mock voices
        if hasattr(self, '_mock_voices'):
            voices_system = {**voices_system, **self._mock_voices}
        return {
            "system": voices_system,
            "user": voices_user,
            "api": voices_api
        }

    def list_all_voices_human_readable(self):
        """
        List all available voices, grouped and labeled for human understanding.
        Returns a dict with categories as keys and lists of voice info dicts as values.
        """
        voices = self.list_all_voices() if hasattr(self, 'list_all_voices') else {}
        categorized = {}
        # Mock/dev voices
        if hasattr(self, '_mock_voices') and self._mock_voices:
            categorized['Development/Test Voices'] = [
                {
                    'id': v.id,
                    'name': v.name,
                    'description': 'Mock/dev voice for testing',
                    'engine': v.engine,
                    'language': v.language,
                    'gender': v.gender
                }
                for v in self._mock_voices.values()
            ]
        # System voices
        sys_voices = self.list_system_voices() if hasattr(self, 'list_system_voices') else []
        if sys_voices:
            categorized['Windows System Voices'] = [
                {
                    'id': v.id,
                    'name': v.name,
                    'description': 'Built-in Windows TTS voice',
                    'engine': v.engine,
                    'language': v.language,
                    'gender': v.gender
                }
                for v in sys_voices
            ]
        # User/clone voices
        user_voices = self.list_user_voices() if hasattr(self, 'list_user_voices') else []
        if user_voices:
            categorized['User/Cloned Voices'] = [
                {
                    'id': v.id,
                    'name': v.name,
                    'description': 'User-imported or cloned voice',
                    'engine': v.engine,
                    'language': v.language,
                    'gender': v.gender
                }
                for v in user_voices
            ]
        # API/Cloud voices
        api_voices = self.list_api_voices() if hasattr(self, 'list_api_voices') else []
        if api_voices:
            categorized['Cloud/API Voices'] = [
                {
                    'id': v.id,
                    'name': v.name,
                    'description': 'Cloud/API voice (e.g., ElevenLabs)',
                    'engine': v.engine,
                    'language': v.language,
                    'gender': v.gender
                }
                for v in api_voices
            ]
        return categorized

    def print_all_voices_human_readable(self):
        """
        Print all available voices with human-friendly headings and details.
        """
        voices_by_cat = self.list_all_voices_human_readable()
        for category, voices in voices_by_cat.items():
            print(f"\n=== {category} ===")
            for v in voices:
                print(f"- ID: {v['id']}")
                print(f"  Name: {v['name']}")
                print(f"  Description: {v['description']}")
                print(f"  Engine: {v['engine']}")
                print(f"  Language: {v['language']}")
                print(f"  Gender: {v['gender']}")
                print()

if __name__ == "__main__":
    try:
        voice_system = VoiceSystem()
        voice_system.add_mock_voices()
        print("Available voices:", voice_system.list_available_voices())
        voice_system.print_all_voices_human_readable()
    except Exception as e:
        logger.error(f"VoiceSystem main error: {e}")
        print(f"VoiceSystem main error: {e}")
