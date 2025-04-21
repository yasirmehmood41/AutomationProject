print("[DIAG] app.py loaded")

import time
import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

import streamlit as st
st.set_page_config(
    page_title="Multi-Niche Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

"""Streamlit web interface for video generation system."""

import yaml
import json
from typing import Dict, List, Optional, Tuple
from Content_Engine.api_generator import ScriptGenerator
from Content_Engine.scene_generator import generate_scene_metadata
from Media_Handler.video_processor import VideoProcessor, StreamlitProglogLogger
from Media_Handler.video_logic import VideoLogic
import logging
from pathlib import Path
from utils.config_loader import load_config
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.25rem;
        background-color: #d4edda;
        color: #155724;
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.25rem;
        background-color: #cce5ff;
        color: #004085;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        st.error(f"Error loading config: {e}")
        if st.button("Retry Loading Config", key="retry_config"):
            st.rerun()
        return {}

def load_project(project_path: str) -> dict:
    """Load a saved project from JSON file."""
    try:
        with open(project_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading project: {e}")
        st.error(f"Error loading project: {e}")
        if st.button("Retry Loading Project", key="retry_project"):
            st.rerun()
        return {}

def save_project(project_data: dict, project_name: str) -> str:
    """Save project data to a JSON file."""
    try:
        os.makedirs("projects", exist_ok=True)
        project_path = f"projects/{project_name}.json"
        with open(project_path, 'w') as file:
            json.dump(project_data, file, indent=2)
        return project_path
    except Exception as e:
        logger.error(f"Error saving project: {e}")
        st.error(f"Error saving project: {e}")
        if st.button("Retry Saving Project", key="retry_save_project"):
            st.rerun()
        return None

def generate_script(script_generator: ScriptGenerator, generation_method: str) -> Tuple[str, Dict]:
    """Generate script based on selected method."""
    script_text = ""
    metadata = {}
    try:
        if generation_method == "AI Generation":
            col1, col2 = st.columns([3, 1])
            with col1:
                ai_provider = st.selectbox(
                    "Select AI Provider:",
                    options=["OpenAI", "Anthropic", "Llama", "Custom"],
                    index=0
                )
                topic = st.text_input("Enter Topic:")
                if st.button("Generate Script"):
                    try:
                        script_text, metadata = script_generator.generate(topic, ai_provider)
                        st.session_state.script_text = script_text
                        st.session_state.script_metadata = metadata
                        st.success("Script generated successfully!")
                    except Exception as e:
                        logger.error(f"Failed to generate script: {e}")
                        st.error(f"Failed to generate script: {e}")
                        if st.button("Retry Script Generation", key="retry_script_gen"):
                            st.rerun()
            with col2:
                st.markdown("### Script Writing Tips")
                st.markdown("- Keep scenes concise and focused")
                st.markdown("- Include visual cues in [brackets]")
                st.markdown("- Use engaging hooks at the beginning")
                st.markdown("- Consider your target audience")
                st.markdown("### Example Format")
                st.code("""
Scene 1: Intro
[Show cityscape at sunset]
Welcome to our guide on...

Scene 2: Main Point
[Display chart showing data]
The key insight here is...
                """)
        else:
            st.markdown("""
**Paste your script in the following format (copy-paste ready):**

```json
[
  {
    "scene_number": 1,
    "title": "Introduction",
    "background": "Show cityscape at sunset with a mosque in the foreground, modern, clean design, minimalist, professional lighting, high quality, 4k",
    "script": "Welcome! Today we explore the Five Pillars of Islam—the foundation of a Muslim's faith and practice.",
    "duration": 6
  },
  {
    "scene_number": 2,
    "title": "Shahada",
    "background": "Show a family gathered for prayer in a cozy home.",
    "script": "The first pillar is Shahada, the declaration of faith.",
    "duration": 5
  }
]
```

- Each scene **must** have `scene_number`, `title`, and `script` fields.
- Only the `script` field is used for voiceover/subtitles. It must be unique per scene and not contain background/visual descriptions.
- No two scenes can have the same `scene_number`.
- This matches the format returned by AI APIs.
""")
            script_text = st.text_area("Paste or write your script below:")
            valid = True
            error_msgs = []
            scenes = []
            if script_text.strip():
                try:
                    parsed = json.loads(script_text)
                    if not isinstance(parsed, list):
                        valid = False
                        error_msgs.append("Script must be a JSON array of scenes.")
                    else:
                        seen_numbers = set()
                        for idx, s in enumerate(parsed):
                            if not isinstance(s, dict):
                                valid = False
                                error_msgs.append(f"Scene {idx+1} is not an object.")
                                continue
                            for field in ["scene_number", "title", "script"]:
                                if field not in s or not str(s[field]).strip():
                                    valid = False
                                    error_msgs.append(f"Scene {idx+1} is missing required field: '{field}'.")
                            # scene_number uniqueness
                            if 'scene_number' in s:
                                if s['scene_number'] in seen_numbers:
                                    valid = False
                                    error_msgs.append(f"Duplicate scene_number: {s['scene_number']}.")
                                seen_numbers.add(s['scene_number'])
                            # script must be unique and not similar to title or background
                            script = s.get('script', '').strip()
                            title = s.get('title', '').strip().lower()
                            background = s.get('background', '').strip().lower()
                            if script.lower() == title or script.lower() == background:
                                valid = False
                                error_msgs.append(f"Scene {idx+1} 'script' must not duplicate the title or background.")
                            if script.lower().startswith(('show ', 'display ', 'background', 'visual')):
                                valid = False
                                error_msgs.append(f"Scene {idx+1} 'script' looks like a background/visual description.")
                            if len(script) < 2:
                                valid = False
                                error_msgs.append(f"Scene {idx+1} 'script' is too short.")
                        scenes = parsed if valid else []
                except Exception as e:
                    valid = False
                    error_msgs = [f"Script is not valid JSON: {e}"]
            if not valid:
                for msg in error_msgs:
                    st.error(msg)
            if st.button("Save Script"):
                if valid and scenes:
                    st.session_state.script_text = script_text
                    st.session_state.script_metadata = {"scenes": scenes}
                    st.success("Script saved successfully!")
                else:
                    st.error("Script format is invalid. Please fix errors before saving.")
            return script_text, {"scenes": scenes if valid else []}
        return script_text, metadata
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        st.error(f"Script generation error: {e}")
        if st.button("Retry Script Generation", key="retry_script_gen2"):
            st.rerun()
        return "", {}

def scene_editor(scenes: List[Dict]) -> List[Dict]:
    """Interactive scene editor for modifying scene metadata."""
    edited_scenes = scenes.copy()
    
    st.markdown("### Scene Editor")
    st.info("Edit each scene to customize your video. You can modify text, duration, and visual elements.")
    
    for i, scene in enumerate(edited_scenes):
        with st.expander(f"Scene {i+1}"):
            st.markdown("**Scene Narration/Subtitle** (words to be spoken and shown as subtitles)")
            narration = scene.get('script', '')
            narration_input = st.text_area("Narration/Subtitle", narration, key=f"scene_script_{i}")
            edited_scenes[i]['script'] = narration_input

            st.markdown("**Background Source**")
            bg_option = st.selectbox(
                "Choose background type",
                ["Upload", "API Search", "Color/System"],
                key=f"bg_type_{i}"
            )
            bg_value = None
            if bg_option == "Upload":
                uploaded_file = st.file_uploader("Upload background image", type=["jpg", "jpeg", "png"], key=f"bg_upload_{i}")
                if uploaded_file:
                    # Save the uploaded file to a temp location and store path
                    import tempfile
                    temp_dir = tempfile.gettempdir()
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    bg_value = {"type": "upload", "value": file_path}
            elif bg_option == "API Search":
                search_term = st.text_input("Image search term (Pixabay/Unsplash)", value=scene.get('background', {}).get('search', ''), key=f"bg_api_search_{i}")
                # Placeholder for UI: In production, show thumbnails from API
                bg_value = {"type": "api", "value": search_term}
            elif bg_option == "Color/System":
                color = st.color_picker("Pick a color", value=scene.get('background', {}).get('color', '#000000'), key=f"bg_color_{i}")
                system_bg = st.selectbox("Or select system background", ["None", "Blur", "Gradient", "Pattern1", "Pattern2"], key=f"bg_sys_{i}")
                bg_value = {"type": "color", "value": color, "system": system_bg}
            if bg_value:
                edited_scenes[i]['background'] = bg_value

            # Additional fields
            edited_scenes[i]['duration'] = st.number_input("Duration (seconds)", min_value=1.0, max_value=60.0, value=float(scene.get('duration', 5)), step=0.5, key=f"scene_duration_{i}")
            edited_scenes[i]['transition'] = st.selectbox("Transition", ["fade", "cut", "slide", "none"], index=["fade", "cut", "slide", "none"].index(scene.get('transition', 'fade')), key=f"scene_transition_{i}")
            edited_scenes[i]['speaker'] = st.text_input("Speaker", value=scene.get('speaker', ''), key=f"scene_speaker_{i}")
            edited_scenes[i]['emotion'] = st.selectbox("Emotion", ["neutral", "happy", "sad", "excited", "angry", "surprised", "fearful"], index=["neutral", "happy", "sad", "excited", "angry", "surprised", "fearful"].index(scene.get('emotion', 'neutral')), key=f"scene_emotion_{i}")
            edited_scenes[i]['visual_prompt'] = st.text_area("Visual Prompt (for AI image gen)", value=scene.get('visual_prompt', ''), key=f"scene_visual_prompt_{i}")
            edited_scenes[i]['audio_effects'] = st.text_input("Audio Effects (comma separated)", value=scene.get('audio_effects', ''), key=f"scene_audio_effects_{i}")
            edited_scenes[i]['background_music'] = st.text_input("Background Music", value=scene.get('background_music', ''), key=f"scene_bg_music_{i}")
            edited_scenes[i]['sound_effects'] = st.text_input("Sound Effects (comma separated)", value=scene.get('sound_effects', ''), key=f"scene_sound_effects_{i}")
            edited_scenes[i]['subtitle_style'] = st.selectbox("Subtitle Style", ["default", "bold", "large", "italic", "highlight"], index=["default", "bold", "large", "italic", "highlight"].index(scene.get('subtitle_style', 'default')), key=f"scene_subtitle_style_{i}")
            edited_scenes[i]['voice_style'] = st.selectbox("Voice Style", ["male", "female", "child", "robotic", "narrator"], index=["male", "female", "child", "robotic", "narrator"].index(scene.get('voice_style', 'male')), key=f"scene_voice_style_{i}")
            edited_scenes[i]['notes'] = st.text_area("Internal Notes", value=scene.get('notes', ''), key=f"scene_notes_{i}")
    
    return edited_scenes

def script_input_section(prepopulate=None):
    st.header("Video Script Input")
    st.markdown("""
    Paste the entire script below in the following JSON format:
    ```json
    {
      "title": "Video Title",
      "description": "Short description...",
      "author": "...",
      "category": "Education",
      "language": "en",
      "tags": ["tag1", "tag2"],
      "scenes": [
        {"scene_number": 1, "script": "...", "background": {"type": "color", "value": "#000000"}},
        {"scene_number": 2, "script": "...", "background": {"type": "api", "value": "office"}}
      ]
    }
    ```
    - Only `scene_number`, `script`, and `background` are required per scene initially.
    - All other fields can be added/edited in the Scene section.
    """)
    script_text = st.text_area("Paste your script JSON here", height=300, key="script_json_input", value=prepopulate if prepopulate else "")
    if st.button("Validate & Continue", key="validate_script_btn"):
        import json
        try:
            data = json.loads(script_text)
            required_globals = ["title", "scenes"]
            for g in required_globals:
                if g not in data:
                    st.error(f"Missing required global field: {g}")
                    return None
            if not isinstance(data['scenes'], list) or not data['scenes']:
                st.error("'scenes' must be a non-empty list.")
                return None
            seen_numbers = set()
            for idx, scene in enumerate(data['scenes']):
                if 'scene_number' not in scene or 'script' not in scene or 'background' not in scene:
                    st.error(f"Scene {idx+1} missing required fields.")
                    return None
                if scene['scene_number'] in seen_numbers:
                    st.error(f"Duplicate scene_number: {scene['scene_number']}")
                    return None
                seen_numbers.add(scene['scene_number'])
            st.session_state['script_data'] = data
            st.session_state['scenes'] = data['scenes']
            st.session_state['current_step'] = 2
            st.success("Script validated! Proceed to Scene editing.")
            return data
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    return st.session_state.get('script_data')

def voice_and_style_selector_tts(default_lang='en', default_speed=1.0):
    import streamlit as st
    from utils.config_loader import load_config
    import yaml, os
    config = load_config()
    tts_config = config.get('tts', {}) if config else {}
    def_lang = tts_config.get('language', default_lang)
    def_speed = float(tts_config.get('speed', default_speed))
    st.markdown('### Voice and Style Selection')
    st.info('Configure Text-to-Speech (TTS) for your video.')
    tts_lang = st.text_input('TTS Language Code', value=def_lang, help='e.g. en, ur, fr, etc.')
    tts_speed = st.slider('TTS Speed', min_value=0.5, max_value=2.0, value=def_speed, step=0.1, help='1.0 = normal, other values set slow mode')
    st.info(f'Current config: language = {tts_lang}, speed = {tts_speed}')
    if tts_lang != def_lang or tts_speed != def_speed:
        config['tts'] = {'language': tts_lang, 'speed': tts_speed}
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        st.success('TTS config updated!')
    # Style selection (reuse your style_selector logic here if needed)
    return tts_lang, tts_speed

def style_selector(prepopulate=None) -> dict:
    """Enhanced video style selector with preview and customization."""
    styles = {
        "modern": {
            "description": "Clean, minimalist design with smooth transitions",
            "color_scheme": "blue-white",
            "transitions": ["fade", "dissolve"],
            "preview_image": "templates/style_previews/modern.jpg"
        },
        "corporate": {
            "description": "Professional and polished look",
            "color_scheme": "navy-gray",
            "transitions": ["fade", "wipe"],
            "preview_image": "templates/style_previews/corporate.jpg"
        },
        "creative": {
            "description": "Dynamic and artistic elements",
            "color_scheme": "vibrant",
            "transitions": ["slide", "zoom"],
            "preview_image": "templates/style_previews/creative.jpg"
        },
        "tech": {
            "description": "High-tech, digital aesthetic",
            "color_scheme": "dark-blue",
            "transitions": ["glitch", "digital"],
            "preview_image": "templates/style_previews/tech.jpg"
        },
        "casual": {
            "description": "Friendly and approachable style",
            "color_scheme": "warm",
            "transitions": ["smooth", "fade"],
            "preview_image": "templates/style_previews/casual.jpg"
        }
    }
    st.markdown("### Video Style Selection")
    cols = st.columns(3)
    selected_style = None
    for i, (style_name, style_details) in enumerate(styles.items()):
        with cols[i % 3]:
            st.markdown(f"#### {style_name.title()}")
            st.markdown(f"*{style_details['description']}*")
            preview_path = style_details.get("preview_image")
            if preview_path and os.path.exists(preview_path):
                st.image(preview_path, use_column_width=True)
            if st.button(f"Select {style_name.title()}", key=f"style_{style_name}"):
                selected_style = style_name
                st.session_state.selected_style = style_name
                st.rerun()
    if 'selected_style' in st.session_state:
        selected_style = st.session_state.selected_style
        style_details = styles.get(selected_style, {})
        st.markdown(f"**Selected Style:** {selected_style.title()}")
        st.markdown("#### Style Customization")
        # Video quality selection
        quality_options = [
            ("HD (1280x720)", "HD"),
            ("Full HD (1920x1080)", "FHD"),
            ("4K (3840x2160)", "4K")
        ]
        quality_labels = [q[0] for q in quality_options]
        quality_keys = [q[1] for q in quality_options]
        default_quality_idx = 1  # Default to Full HD
        selected_quality_label = st.selectbox(
            "Video Quality (Resolution)",
            options=quality_labels,
            index=default_quality_idx
        )
        selected_quality = quality_keys[quality_labels.index(selected_quality_label)]
        st.session_state.selected_quality = selected_quality
        customized_style = {
            "base_style": selected_style,
            "color_scheme": st.selectbox(
                "Color Scheme",
                options=["default"] + list(set([s["color_scheme"] for s in styles.values()])),
                index=0
            ),
            "transition_preference": st.selectbox(
                "Transition Preference",
                options=["default"] + list(set([t for s in styles.values() for t in s.get("transitions", [])])),
                index=0
            ),
            "text_style": st.selectbox(
                "Text Style",
                options=["default", "minimal", "bold"],
                index=0
            ),
            "video_quality": selected_quality
        }
        return customized_style
    return {}

def process_video_generation(
    scenes: List[Dict], 
    video_processor: VideoProcessor,
    video_logic_handler: VideoLogic,
    style_config: Dict = None
) -> None:
    print("[DIAG] process_video_generation called")
    print(f"[DIAG] scenes: {scenes}")
    print(f"[DIAG] video_processor: {video_processor}")
    print(f"[DIAG] video_logic_handler: {video_logic_handler}")
    print(f"[DIAG] style_config: {style_config}")
    if not scenes:
        print("[DIAG] No scenes available for processing. Returning None.")
        st.error("No scenes available for processing.")
        return
        
    # Create a placeholder for progress bar
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    
    # Create status text
    status_text = st.empty()
    
    try:
        with st.spinner("Generating your video..."):
            # Phase 1: Scene Processing
            status_text.markdown("**Processing scenes...**")
            processed_scenes = []
            
            # Convert style_config to a proper style dictionary
            style_dict = {
                "style_name": style_config.get("base_style", "modern"),
                "font": style_config.get("font", "Arial"),
                "font_size": style_config.get("font_size", 36),
                "color": style_config.get("color", "#FFFFFF"),
                "background_color": style_config.get("background_color", "#000000"),
                "aspect_ratio": style_config.get("aspect_ratio", "16:9"),
                "resolution": style_config.get("resolution", (1920, 1080)),
                "fps": style_config.get("fps", 30),
                "bitrate": style_config.get("bitrate", "8M"),
                "use_intro": st.checkbox("Include Intro Video (if available)", value=False),
                "use_outro": st.checkbox("Include Outro Video (if available)", value=False),
                "use_logo": st.checkbox("Include Logo Overlay (if available)", value=False)
            }
            
            for i, scene in enumerate(scenes):
                processed = video_logic_handler.process_scene(
                    scene, 
                    style_dict,
                    None
                )
                if processed:
                    processed_scenes.append(processed)
                progress_bar.progress((i + 1) / (len(scenes) * 2))  # First half of progress
            
            status_text.markdown("✅ Scene processing complete!")
            
            # Phase 2: Video Compilation
            status_text.markdown("**Compiling final video...**")
            
            # Create a Streamlit progress bar for video rendering
            video_progress_bar = st.progress(0, text="Rendering video...")
            style_dict["streamlit_logger"] = StreamlitProglogLogger(lambda: video_progress_bar)
            
            print("[DIAG] About to call video_processor.compile_video")
            output_file = video_processor.compile_video(
                scenes=processed_scenes,
                output_name=f"{style_config.get('base_style', 'video')}_{int(time.time())}.mp4",
                additional_settings=style_dict
            )
            print(f"[DIAG] video_processor.compile_video returned: {output_file}")
            
            for i in range(len(scenes)):
                progress_bar.progress((len(scenes) + i + 1) / (len(scenes) * 2))  # Second half of progress
                time.sleep(0.1)  # Simulate processing time
                
            status_text.markdown("✅ Video compilation complete!")
            progress_bar.progress(1.0)
            
            # Clear progress bar after rendering
            video_progress_bar.empty()
            
            # Display completion message and video
            retry_count = 0
            max_retries = 5
            retry_delay = 1  # seconds
            while output_file and not os.path.exists(output_file) and retry_count < max_retries:
                time.sleep(retry_delay)
                retry_count += 1

            output_dir = os.path.dirname(output_file) if output_file else None
            if output_file and os.path.exists(output_file):
                st.success(f"\U0001F389 Your video has been successfully generated!\n\nSaved at: {output_file}")
                st.video(output_file)
                # Add download button
                with open(output_file, "rb") as file:
                    st.download_button(
                        label="Download Video",
                        data=file,
                        file_name=os.path.basename(output_file),
                        mime="video/mp4"
                    )
            elif output_dir and os.path.exists(output_dir):
                # Fallback: show most recent video in output directory if exists
                import glob
                video_files = sorted(
                    glob.glob(os.path.join(output_dir, '*.mp4')),
                    key=os.path.getmtime,
                    reverse=True
                )
                if video_files:
                    latest_video = video_files[0]
                    st.warning(f"Video not found at expected path, showing latest video in directory: {latest_video}")
                    st.video(latest_video)
                    with open(latest_video, "rb") as file:
                        st.download_button(
                            label="Download Latest Video",
                            data=file,
                            file_name=os.path.basename(latest_video),
                            mime="video/mp4"
                        )
                else:
                    st.error(f"Video generation completed, but the output file was not found.\nExpected directory: {output_dir}")
            else:
                st.error("Video generation completed, but the output file was not found. Output directory does not exist.")
                
    except Exception as e:
        print(f"[DIAG] Exception in process_video_generation: {e}")
        logger.error(f"Error generating video: {str(e)}")
        st.error(f"Error generating video: {str(e)}")
        
    finally:
        # Always clear the progress bar and status text
        progress_placeholder.empty()
        status_text.empty()

def main() -> None:
    """Main application function."""
    if 'script_data' not in st.session_state:
        st.session_state['script_data'] = None
    if 'scenes' not in st.session_state:
        st.session_state['scenes'] = []
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 1
    if 'selected_tab' not in st.session_state:
        st.session_state['selected_tab'] = 0

    st.markdown('<h1 class="main-header">Multi-Niche Video Generator</h1>', unsafe_allow_html=True)

    config = load_config()
    script_generator = ScriptGenerator()
    video_processor = VideoProcessor()
    video_logic_handler = VideoLogic(config.get('video', {}))

    section_titles = [
        "Script",
        "Scene",
        "Voice Over",
        "Video Generation"
    ]
    current_tab = st.session_state.selected_tab

    st.sidebar.title("Navigation")
    for i, title in enumerate(section_titles):
        if st.sidebar.button(title, key=f"nav_{i}"):
            print("[DIAG] About to rerun after sidebar navigation")
            st.session_state.selected_tab = i
            st.session_state.current_step = i + 1
            st.rerun()

    # --- Step 1: Script ---
    if st.session_state['current_step'] == 1:
        st.markdown('<h2 class="section-header">Script Input</h2>', unsafe_allow_html=True)
        st.markdown("""
        Select how you want to start your project:
        """)
        method = st.radio('Choose input method:', ['Manual', 'API/AI'], index=0, horizontal=True, key='script_input_method')
        script_text = st.session_state.get('script_data', "")
        script_data = None
        api_niches = [
            "Education", "Health", "Finance", "Technology", "Travel", "Lifestyle", "Custom..."
        ]
        if method == 'API/AI':
            st.markdown('#### 1. Fill API Script Request Details')
            selected_niche = st.selectbox('Niche/Topic:', api_niches, key='niche_select')
            custom_topic = ""
            if selected_niche == "Custom...":
                custom_topic = st.text_input('Custom Niche/Topic:', key='custom_topic')
            topic = custom_topic if selected_niche == "Custom..." else selected_niche
            video_title = st.text_input('Video Title:', value="", key='api_video_title')
            num_scenes = st.number_input('Number of Scenes:', min_value=1, max_value=20, value=5, step=1, key='api_num_scenes')
            language = st.text_input('Language:', value="en", key='api_language')
            audience = st.text_input('Target Audience (optional):', value="", key='api_audience')
            custom_instructions = st.text_area('Custom Instructions (optional):', value="", key='api_custom_instructions')
            api_url = st.text_input('API Endpoint URL', value='', help='Paste the API endpoint that returns your script in JSON format.', key='api_url')
            st.markdown('''<small>Example API: <code>https://api.example.com/video-script</code></small>''', unsafe_allow_html=True)
            st.markdown('**Summary of API Request:**')
            st.json({
                "topic": topic,
                "title": video_title,
                "num_scenes": num_scenes,
                "language": language,
                "audience": audience,
                "instructions": custom_instructions
            })
            if st.button('Fetch Script from API'):
                import requests
                try:
                    payload = {
                        "topic": topic,
                        "title": video_title,
                        "num_scenes": num_scenes,
                        "language": language,
                        "audience": audience,
                        "instructions": custom_instructions
                    }
                    resp = requests.post(api_url, json=payload)
                    resp.raise_for_status()
                    script_json = resp.text
                    st.session_state['script_data'] = script_json
                    st.session_state['scenes'] = json.loads(script_json)['scenes'] if 'scenes' in json.loads(script_json) else json.loads(script_json)
                    st.success('Script fetched successfully!')
                except Exception as e:
                    st.error(f'Failed to fetch script: {e}')
            st.markdown('---')
        else:
            st.markdown('#### Paste or Edit Your Script')
        st.markdown('**Copy and use the sample format below (works for both manual and API):**')
        st.code('''{
  "title": "Video Title",
  "description": "Short description...",
  "author": "...",
  "category": "Education",
  "language": "en",
  "tags": ["tag1", "tag2"],
  "scenes": [
    {"scene_number": 1, "script": "...", "background": {"type": "color", "value": "#000000"}},
    {"scene_number": 2, "script": "...", "background": {"type": "api", "value": "office"}}
  ]
}''', language='json')
        script_area = st.text_area("Paste or edit your script JSON here", height=300, key="script_json_input", value=script_text)
        if st.button("💾 Save Script", key="save_script_btn"):
            import json
            try:
                data = json.loads(script_area)
                st.session_state['script_data'] = data
                st.session_state['scenes'] = data['scenes']
                st.success("Script saved!")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
        st.markdown('---')
        st.markdown('**Tip:** The API endpoint must return a JSON with a `scenes` array as shown above.')
        col1, col2 = st.columns([1, 1])
        with col2:
            if st.button("➡️ Continue to Scene Editor", key="continue_to_scene_btn"):
                import json
                try:
                    data = json.loads(st.session_state['script_data']) if isinstance(st.session_state['script_data'], str) else st.session_state['script_data']
                    st.session_state['script_data'] = data
                    st.session_state['scenes'] = data['scenes']
                    st.session_state['current_step'] = 2
                    print("[DIAG] Advancing to Scene Editor step")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
    # --- Step 2: Scene ---
    elif st.session_state['current_step'] == 2:
        st.markdown('<h2 class="section-header">Scene Editor</h2>', unsafe_allow_html=True)
        scenes = st.session_state['scenes'] if 'scenes' in st.session_state else []
        edited_scenes = scene_editor(scenes)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown('<style>div.stButton > button {background-color: #1976d2; color: white;}</style>', unsafe_allow_html=True)
            if st.button("⬅️ Back to Script", key="back_to_script_btn"):
                st.session_state['current_step'] = 1
                print("[DIAG] Going back to Script section")
                st.rerun()
        with col2:
            st.markdown('<style>div.stButton > button {background-color: #43a047; color: white;}</style>', unsafe_allow_html=True)
            if st.button("💾 Save Scenes", key="save_scenes_btn"):
                st.session_state['scenes'] = edited_scenes
                st.success("Scenes saved!")
        with col3:
            st.markdown('<style>div.stButton > button {background-color: #8bc34a; color: black;}</style>', unsafe_allow_html=True)
            if st.button("➡️ Continue to Voice Over", key="continue_to_voiceover_btn"):
                st.session_state['scenes'] = edited_scenes
                st.session_state['current_step'] = 3
                print("[DIAG] Advancing to Voice Over step")
                st.rerun()

    # --- Step 3: Voice Over ---
    elif st.session_state['current_step'] == 3:
        st.markdown('<h2 class="section-header">Voice Over</h2>', unsafe_allow_html=True)
        st.info(f"Current number of scenes: {len(st.session_state['scenes'])}")
        tts_lang = st.session_state.get('tts_lang', 'en')
        tts_speed = st.session_state.get('tts_speed', 1.0)
        tts_lang, tts_speed = voice_and_style_selector_tts(default_lang=tts_lang, default_speed=tts_speed)
        st.session_state['tts_lang'] = tts_lang
        st.session_state['tts_speed'] = tts_speed
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown('<style>div.stButton > button {background-color: #1976d2; color: white;}</style>', unsafe_allow_html=True)
            if st.button("⬅️ Back to Scene Editor", key="back_to_scene_btn"):
                st.session_state['current_step'] = 2
                print("[DIAG] Going back to Scene Editor section")
                st.rerun()
        with col2:
            st.markdown('<style>div.stButton > button {background-color: #43a047; color: white;}</style>', unsafe_allow_html=True)
            if st.button("💾 Save Voice Settings", key="save_voice_btn"):
                st.success("Voice settings saved!")
        with col3:
            st.markdown('<style>div.stButton > button {background-color: #8bc34a; color: black;}</style>', unsafe_allow_html=True)
            if st.button("➡️ Continue to Video Generation", key="continue_to_video_btn"):
                st.session_state['current_step'] = 4
                print("[DIAG] Advancing to Video Generation step")
                st.rerun()

    # --- Step 4: Video Generation ---
    elif st.session_state['current_step'] == 4:
        st.markdown('<h2 class="section-header">Video Generation</h2>', unsafe_allow_html=True)
        st.info(f"Current number of scenes: {len(st.session_state['scenes'])}")
        style_config = st.session_state.get('style_config', None)
        style_config = style_selector(prepopulate=style_config) if 'style_selector' in globals() else None
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown('<style>div.stButton > button {background-color: #1976d2; color: white;}</style>', unsafe_allow_html=True)
            if st.button("⬅️ Back to Voice Over", key="back_to_voiceover_btn"):
                st.session_state['current_step'] = 3
                print("[DIAG] Going back to Voice Over section")
                st.rerun()
        with col2:
            st.markdown('<style>div.stButton > button {background-color: #43a047; color: white;}</style>', unsafe_allow_html=True)
            if st.button("💾 Save Style", key="save_style_btn"):
                st.session_state['style_config'] = style_config
                st.success("Style saved!")
        with col3:
            st.markdown('<style>div.stButton > button {background-color: #8bc34a; color: black;}</style>', unsafe_allow_html=True)
            if st.button("🎬 Generate Video", key="final_generate_video_btn"):
                print("[DIAG] About to generate video")
                import time
                progress_placeholder = st.empty()
                for percent_complete in range(0, 101, 5):
                    progress_placeholder.progress(percent_complete / 100, text=f"Generating Video... {percent_complete}%")
                    time.sleep(0.05)
                progress_placeholder.progress(1.0, text="Video Generation Complete! 100%")
                st.success("Video generation started!")
                output_path = process_video_generation(
                    scenes=st.session_state['scenes'],
                    video_processor=video_processor,
                    video_logic_handler=video_logic_handler,
                    style_config=style_config
                )
                if output_path:
                    st.session_state['generated_video_path'] = output_path
        video_path = st.session_state.get('generated_video_path')
        import os
        if video_path and os.path.exists(video_path):
            st.success(f"\U0001F389 Your video has been successfully generated!\n\nSaved at: {video_path}")
            st.video(video_path)
            with open(video_path, "rb") as file:
                st.download_button(
                    label="Download Video",
                    data=file,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4"
                )
        else:
            st.info("No video has been generated yet. Please click 'Generate Video' above.")

if __name__ == "__main__":
    main()
