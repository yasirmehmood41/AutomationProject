import pyttsx3
import os


def generate_voice(text: str, output_path: str = "./output_manager/outputs/") -> str:
    """
    Generate voice-over audio for the given text using pyttsx3 (an offline TTS engine).
    Returns the path to the generated audio file.
    """
    engine = pyttsx3.init()
    # Optionally, adjust voice properties here:
    engine.setProperty('rate', 150)  # Speed of speech
    engine.setProperty('volume', 1.0)  # Volume (0.0 to 1.0)

    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    audio_file = os.path.join(output_path, "voice_sample.mp3")
    engine.save_to_file(text, audio_file)
    engine.runAndWait()
    return audio_file


if __name__ == "__main__":
    sample_text = "This is a test voice-over for our automation project."
    print("Generated audio at:", generate_voice(sample_text))
