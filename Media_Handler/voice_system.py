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
        pass

class ElevenLabsVoiceBackend(VoiceBackend):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_voice(self, text: str, voice_id: str) -> str:
        # Logic for generating voice using ElevenLabs
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
        if response.status_code == 200:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
            output_file = os.path.join("output_manager", "audio", f"{voice_id}_{text_hash}.mp3")
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return output_file
        else:
            raise Exception(f"ElevenLabs API error: {response.text}")

class LocalTTSVoiceBackend(VoiceBackend):
    def __init__(self):
        self.engine = pyttsx3.init()
        self.local_voices = {}
        for voice in self.engine.getProperty('voices'):
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

    def generate_voice(self, text: str, voice_id: str) -> str:
        # Logic for generating voice using local TTS
        if voice_id not in self.local_voices:
            raise ValueError(f"Unknown voice: {voice_id}")
        
        voice = self.local_voices[voice_id]
        
        # Create a safe filename using hash of text
        text_hash = hashlib.md5(text.encode()).hexdigest()[:10]
        output_file = os.path.join("output_manager", "audio", f"{voice_id}_{text_hash}.mp3")
        
        try:
            # Use local TTS
            temp_wav = os.path.join("output_manager", "temp", f"{voice_id}_{text_hash}.wav")
            
            # Set voice and save to WAV first
            self.engine.setProperty('voice', next(v.id for v in self.engine.getProperty('voices')))
            self.engine.save_to_file(text, temp_wav)
            self.engine.runAndWait()
            
            # Convert WAV to MP3 using pydub
            if os.path.exists(temp_wav):
                audio = AudioSegment.from_wav(temp_wav)
                audio.export(output_file, format="mp3")
                os.remove(temp_wav)  # Clean up temp file
            else:
                raise Exception("Failed to generate WAV file")
            
            return output_file
            
        except Exception as e:
            print(f"Error generating voice: {str(e)}")
            raise

class VoiceSystem:
    """Voice generation system."""
    def __init__(self, config):
        self.config = config
        self.backend = self._load_backend(config['voice']['backend'])

    def _load_backend(self, backend_name: str) -> VoiceBackend:
        if backend_name == 'elevenlabs':
            return ElevenLabsVoiceBackend(
                api_key=self.config['voice']['elevenlabs']['api_key']
            )
        elif backend_name == 'local':
            return LocalTTSVoiceBackend()
        else:
            raise ValueError(f"Unknown backend: {backend_name}")

    def generate_voice_for_scenes(self, scenes: List[Dict], voice_id: str) -> str:
        # Use the selected backend to generate voice
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
                    scene_file = self.backend.generate_voice(scene['voiceover'], voice_id)
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

if __name__ == "__main__":
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize voice system
    voice_system = VoiceSystem(config)
    # Example usage
    scenes = [{'voiceover': 'Hello world'}]
    voice_system.generate_voice_for_scenes(scenes, "local_1")
