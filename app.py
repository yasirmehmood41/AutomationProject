print("[DIAG] app.py loaded")

import time
import os
import threading
import json
import tempfile
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
from Media_Handler.video_processor import VideoProcessor
from Media_Handler.video_logic import VideoLogic
import logging
from pathlib import Path
from utils.config_loader import load_config
import sys
from utils.trending_apis import get_google_trends, get_youtube_trends, get_twitter_trends
from utils.api_key_manager import get_api_key, save_api_key
from utils.music_apis import search_pixabay_music, fetch_youtube_audio_library_trending, epidemic_sound_note

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

# --- Scene Editor Helper ---
def scene_editor(scenes):
    """UI for editing scenes. Returns the edited scenes list."""
    edited_scenes = []
    for i, scene in enumerate(scenes):
        st.subheader(f"Scene {i+1}")
        edited = {}
        # --- Use session_state to persist values ---
        scene_num_key = f"scene_number_{i}"
        script_key = f"scene_script_{i}"
        bg_key = f"scene_bg_{i}"
        subtitle_pos_key = f"scene_subtitle_position_{i}"
        # Restore from session_state if present
        if scene_num_key in st.session_state:
            scene_number = st.session_state[scene_num_key]
        else:
            scene_number = scene.get('scene_number', i+1)
        if script_key in st.session_state:
            script_val = st.session_state[script_key]
        else:
            script_val = scene.get('script', '')
        if bg_key in st.session_state:
            bg_val = st.session_state[bg_key]
        else:
            bg_val = scene.get('background', '')
        # Defensive: ensure background is always a dict for downstream usage
        if not isinstance(bg_val, dict):
            bg_val = {}
        if subtitle_pos_key in st.session_state:
            subtitle_pos = st.session_state[subtitle_pos_key]
        else:
            subtitle_pos = "(use global)"
        edited['scene_number'] = st.number_input(f"Scene Number", value=scene_number, key=scene_num_key)
        edited['script'] = st.text_area(f"Script", value=script_val, key=script_key)
        edited['background'] = st.text_input(f"Background", value=bg_val, key=bg_key)
        edited['subtitle_position'] = st.selectbox(
            "Subtitle Position (Override, optional)",
            options=["(use global)", "bottom", "center"],
            index=["(use global)", "bottom", "center"].index(subtitle_pos) if subtitle_pos in ["(use global)", "bottom", "center"] else 0,
            key=subtitle_pos_key,
            help="Override global subtitle position for this scene."
        )
        # Add more editable fields as needed
        edited_scenes.append(edited)
    return edited_scenes

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
                        st.session_state['api_script_text'] = script_text
                        script_text = st.text_area("Edit Script", value=st.session_state.get('api_script_text', ''), key="api_script_text")
                        st.session_state['script_metadata'] = metadata
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

            script_text = st.text_area("Paste your script JSON here", height=300, key="script_json_input", value="")
            if st.button("Validate & Continue", key="validate_script_btn"):
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
                    st.success("Script validated! Proceed to Music selection.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")
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
            edited_scenes[i]['sound_effects'] = st.text_input("Sound Effects (comma separated)", value=scene.get('sound_effects', ''), key=f"scene_sound_effects_{i}")
            edited_scenes[i]['subtitle_style'] = st.selectbox("Subtitle Style", ["default", "bold", "large", "italic", "highlight"], index=["default", "bold", "large", "italic", "highlight"].index(scene.get('subtitle_style', 'default')), key=f"scene_subtitle_style_{i}")
            edited_scenes[i]['voice_style'] = st.selectbox("Voice Style", ["male", "female", "child", "robotic", "narrator"], index=["male", "female", "child", "robotic", "narrator"].index(scene.get('voice_style', 'male')), key=f"scene_voice_style_{i}")
            edited_scenes[i]['notes'] = st.text_area("Internal Notes", value=scene.get('notes', ''), key=f"scene_notes_{i}")
            # Add per-scene subtitle position override
            edited_scenes[i]['subtitle_position'] = st.selectbox(
                "Subtitle Position (Override, optional)",
                options=["(use global)", "bottom", "center"],
                index=0,
                key=f"scene_subtitle_position_{i}",
                help="Override global subtitle position for this scene."
            )
    
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
    script_text = st.text_area("Paste your script JSON here", height=300, key="script_json_input", value="")
    if st.button("Save Script", key="save_script_btn"):
        try:
            parsed = json.loads(script_text)
            # Accept either a list (legacy) or an object with 'scenes' (modern)
            if isinstance(parsed, list):
                st.session_state['script_text'] = script_text
                st.session_state['script_metadata'] = {"scenes": parsed}
                st.success("Script saved and metadata auto-filled!")
            elif isinstance(parsed, dict) and 'scenes' in parsed and isinstance(parsed['scenes'], list):
                st.session_state['script_text'] = script_text
                st.session_state['script_metadata'] = {"scenes": parsed['scenes']}
                # Auto-fill metadata fields
                for k in ['title','description','author','category','language','tags','slogan','overlay_color','animate']:
                    if k in parsed:
                        st.session_state[f'meta_{k}'] = parsed[k]
                st.success("Script saved and metadata auto-filled!")
            else:
                st.error("Script must be a JSON array of scenes or an object with a 'scenes' array.")
        except Exception as e:
            st.error(f"Script is not valid JSON: {e}")
    if st.button("Validate & Continue", key="validate_script_btn"):
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
            st.success("Script validated! Proceed to Music selection.")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    return st.session_state.get('script_data')

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
    tts_lang = st.text_input('TTS Language Code', value=def_lang, help='e.g. en, ur, fr, etc.', key='tts_lang')
    tts_speed = st.slider('TTS Speed', min_value=0.5, max_value=2.0, value=def_speed, step=0.1, help='1.0 = normal, other values set slow mode', key='tts_speed')
    st.info(f'Current config: language = {tts_lang}, speed = {tts_speed}')
    if tts_lang != def_lang or tts_speed != def_speed:
        config['tts'] = {'language': tts_lang, 'speed': tts_speed}
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        st.success('TTS config updated!')
    # Style selection (reuse your style_selector logic here if needed)
    return tts_lang, tts_speed

def style_selector(prepopulate=None, return_name=False) -> dict:
    """Enhanced video style selector with preview and customization."""
    styles = {
        "modern": {"description": "Clean, minimalist design with smooth transitions", "color_scheme": "blue-white", "transitions": ["fade", "dissolve"], "preview_image": "templates/style_previews/modern.jpg"},
        "corporate": {"description": "Professional and polished look", "color_scheme": "navy-gray", "transitions": ["fade", "wipe"], "preview_image": "templates/style_previews/corporate.jpg"},
        "creative": {"description": "Dynamic and artistic elements", "color_scheme": "purple-orange", "transitions": ["zoom", "slide"], "preview_image": "templates/style_previews/creative.jpg"},
        "tech": {"description": "High-tech, digital aesthetic", "color_scheme": "black-green", "transitions": ["glitch", "fade"], "preview_image": "templates/style_previews/tech.jpg"},
        "casual": {"description": "Friendly and approachable style", "color_scheme": "yellow-blue", "transitions": ["slide", "wipe"], "preview_image": "templates/style_previews/casual.jpg"}
    }
    style_names = list(styles.keys())
    style_key = 'selected_style'
    # Fix: Always define default_idx
    if style_key in st.session_state and st.session_state[style_key] in style_names:
        default_idx = style_names.index(st.session_state[style_key])
    else:
        default_idx = 0
    selected_style = st.selectbox("Select Video Style", style_names, index=default_idx, key=style_key)
    style_details = styles.get(selected_style, {})
    st.markdown(f"**Selected Style:** {selected_style.title()}")
    st.markdown(f"*{style_details.get('description','')}*")
    # Customization options (add more as needed)
    # Restore original video quality selector
    quality_options = [
        ("HD (1280x720)", "HD"),
        ("Full HD (1920x1080)", "FHD"),
        ("4K (3840x2160)", "4K")
    ]
    quality_labels = [q[0] for q in quality_options]
    quality_keys = [q[1] for q in quality_options]
    quality_key = 'selected_quality_label'
    if quality_key in st.session_state and st.session_state[quality_key] in quality_labels:
        default_quality_idx = quality_labels.index(st.session_state[quality_key])
    else:
        default_quality_idx = 1
    selected_quality_label = st.selectbox(
        "Video Quality (Resolution)",
        options=quality_labels,
        index=default_quality_idx,
        key=quality_key
    )
    selected_quality = quality_keys[quality_labels.index(selected_quality_label)]
    # Color scheme with session persistence
    color_scheme_key = 'selected_color_scheme'
    # Gather all available color schemes from all styles
    all_color_schemes = list({v['color_scheme'] for v in styles.values()})
    color_scheme_val = st.session_state.get(color_scheme_key, style_details.get('color_scheme', 'default'))
    color_scheme = st.selectbox("Color Scheme", all_color_schemes, index=all_color_schemes.index(color_scheme_val) if color_scheme_val in all_color_schemes else 0, key=color_scheme_key)
    # Transition with session persistence
    transition_key = 'selected_transition'
    transition_val = st.session_state.get(transition_key, style_details.get('transitions', ['fade'])[0])
    transition = st.selectbox("Transition", style_details.get('transitions', ['fade']), index=0, key=transition_key)
    config = {
        "base_style": selected_style,
        "color_scheme": color_scheme,
        "transition": transition,
        "video_quality": selected_quality
    }
    if return_name:
        return selected_style, config
    return config

def music_selection_ui(prefix: str) -> dict:
    music_volume_key = f'music_volume_{prefix}'
    music_option_key = f'music_option_{prefix}'
    music_upload_key = f'music_upload_{prefix}'
    music_url_key = f'music_url_{prefix}'
    # Restore from session_state if present
    music_volume = st.session_state.get(music_volume_key, 0.1)
    music_option = st.session_state.get(music_option_key, 'None')
    music_file = st.session_state.get(music_upload_key, None)
    music_url = st.session_state.get(music_url_key, None)
    music_volume = st.slider(f'Music Volume (relative to voice) ({prefix})', min_value=0.0, max_value=1.0, value=music_volume, step=0.01, key=music_volume_key)
    music_option = st.radio(f'Choose music source ({prefix}):', ['None', 'Manual Upload', 'Pixabay Music (Free)', 'YouTube Audio Library (Trending)', 'Epidemic Sound (Paid)'], key=music_option_key, index=['None', 'Manual Upload', 'Pixabay Music (Free)', 'YouTube Audio Library (Trending)', 'Epidemic Sound (Paid)'].index(music_option) if music_option in ['None', 'Manual Upload', 'Pixabay Music (Free)', 'YouTube Audio Library (Trending)', 'Epidemic Sound (Paid)'] else 0)
    if music_option == 'Manual Upload':
        music_file = st.file_uploader(f'Upload your own music/SFX ({prefix}) (mp3, wav)', type=['mp3', 'wav'], key=music_upload_key)
        if music_file:
            st.audio(music_file)
    elif music_option == 'Pixabay Music (Free)':
        pixabay_key = st.text_input(f'Pixabay API Key ({prefix}):', value=get_api_key('pixabay_music'), type='password', key=f'pixabay_music_key_{prefix}')
        if st.button(f'Save Pixabay API Key ({prefix})'):
            save_api_key('pixabay_music', pixabay_key)
            st.success(f'Pixabay API Key saved!')
        query = st.text_input(f'Search Pixabay Music ({prefix}):', value='trending', key=f'pixabay_music_query_{prefix}')
        if st.button(f'Search Pixabay Music ({prefix})'):
            music_results = search_pixabay_music(pixabay_key, query)
            st.session_state['api_music_results'] = music_results
            music_results = st.session_state.get('api_music_results', [])
        if music_results:
            for idx, m in enumerate(music_results):
                st.markdown(f"**{m['title']}** by {m['user']} [{m['duration']}s]")
                st.audio(m['url'])
                if st.button(f"Select: {m['title']} ({prefix})", key=f"select_pixabay_{idx}_{prefix}"):
                    music_url = m['url']
                    st.session_state['api_music_url'] = music_url
                    music_url = st.text_input("Edit Music URL", value=st.session_state.get('api_music_url', ''), key="api_music_url")
    elif music_option == 'YouTube Audio Library (Trending)':
        yt_trending = fetch_youtube_audio_library_trending()
        st.session_state['api_yt_trending'] = yt_trending
        yt_trending = st.session_state.get('api_yt_trending', [])
        for idx, m in enumerate(yt_trending):
            st.markdown(f"**{m['title']}** [YouTube Audio Library]")
            st.markdown(f"[Download Link]({m['url']})")
            if st.button(f"Select: {m['title']} ({prefix})", key=f"select_ytlib_{idx}_{prefix}"):
                music_url = m['url']
                st.session_state['api_music_url'] = music_url
                music_url = st.text_input("Edit Music URL", value=st.session_state.get('api_music_url', ''), key="api_music_url")
    elif music_option == 'Epidemic Sound (Paid)':
        st.warning(epidemic_sound_note())
        music_file = st.file_uploader(f'Upload Epidemic Sound music ({prefix}) (after download)', type=['mp3', 'wav'], key=f'epidemic_upload_{prefix}')
        if music_file:
            st.audio(music_file)
    else:
        st.info(f'No background music will be added ({prefix}).')
    selected_music_url = st.session_state.get('api_music_url', None)
    if selected_music_url:
        st.markdown(f"**Current Selected Background Music:**")
        st.write(f"type(selected_music_url): {type(selected_music_url)}")
        if isinstance(selected_music_url, (str, bytes, bytearray)):
            st.audio(selected_music_url)
        else:
            st.write("[Audio not played: selected_music_url is not valid audio data]")
        if isinstance(selected_music_url, (bytes, bytearray)):
            st.write(f"[Binary data of length {len(selected_music_url)} bytes not shown]")
        else:
            st.write(str(selected_music_url))
    return {'mode': music_option, 'file': music_file, 'url': music_url, 'volume': music_volume}

def process_video_generation(
    scenes: List[Dict], 
    video_processor: VideoProcessor,
    video_logic_handler: VideoLogic,
    style_config: Dict = None,
    background_music_path: Optional[str] = None
) -> None:
    # Avoid printing raw bytes in scenes
    def summarize_scene(scene):
        scene_copy = dict(scene)
        for key in list(scene_copy.keys()):
            if isinstance(scene_copy[key], (bytes, bytearray)):
                scene_copy[key] = f"<bytes, length={len(scene_copy[key])}>"
        return scene_copy

    # print(f"[DIAG] scenes: {[summarize_scene(s) for s in scenes]}")  # COMMENTED OUT: Prevent binary or large data output
    # print(f"[DIAG] video_processor: {video_processor}")
    # print(f"[DIAG] video_logic_handler: {video_logic_handler}")
    # print(f"[DIAG] style_config: {style_config}")
    if not scenes:
        # print("[DIAG] No scenes available for processing. Returning None.")
        st.error("No scenes available for processing.")
        return
        
    # Create a placeholder for progress bar
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    
    # Create status text
    status_text = st.empty()
    
    try:
        with st.spinner("Generating your video. This may take a minute..."):
            print("[DIAG] Spinner shown. Entering export block.")
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
            
            music_info = st.session_state.get('music_for_video', None)
            music_arg = None
            music_volume = 0.1
            if music_info:
                music_volume = music_info.get('volume', 0.1)
                if music_info['mode'] in ['manual', 'epidemic'] and music_info.get('file'):
                    music_arg = music_info['file']
                elif music_info['mode'] in ['pixabay', 'ytlib'] and music_info.get('url'):
                    music_arg = music_info['url']
            music_arg = st.session_state.get('api_music_url', None)
            if music_arg:
                # Use this music_arg as the background music in video generation logic
                pass  # (existing logic should already use this variable)
            
            # Ensure additional_settings is always defined before use
            additional_settings = {}
            if background_music_path:
                additional_settings['background_music_path'] = background_music_path
                print(f"[DIAG] FINAL additional_settings includes background_music_path: {background_music_path}")
            # Merge style_settings and any previously set keys (like background_music_path)
            style_settings = {
                "base_style": style_config.get("base_style", "modern"),
                "font": style_config.get("font", "Arial"),
                "font_size": style_config.get("font_size", 36),
                "color": style_config.get("color", "#FFFFFF"),
                "background_color": style_config.get("background_color", "#000000"),
                "aspect_ratio": style_config.get("aspect_ratio", "16:9"),
                "resolution": style_config.get("resolution", (1920, 1080)),
                "fps": style_config.get("fps", 30),
                "bitrate": style_config.get("bitrate", "8M"),
                "use_intro": style_config.get("use_intro", False),
                "use_outro": style_config.get("use_outro", False),
                "use_logo": style_config.get("use_logo", False),
                "color_scheme": style_config.get("color_scheme", "blue-white"),
                "transition": style_config.get("transition", "fade"),
                "video_quality": style_config.get("video_quality", "FHD")
            }
            additional_settings = {**style_settings, **additional_settings}
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
            progress_bar_type = st.radio("Progress Bar Type", ["Line", "Circle"], horizontal=True, key="progress_bar_type")

            # --- CREATE A SINGLE DICT WITH EVERYTHING ---
            # Convert style_config to a proper style dictionary with all settings
            style_settings = {
                "base_style": style_config.get("base_style", "modern"),
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
                "use_logo": st.checkbox("Include Logo Overlay (if available)", value=False),
                "color_scheme": style_config.get("color_scheme", "blue-white"),
                "transition": style_config.get("transition", "fade"),
                "video_quality": style_config.get("video_quality", "FHD")
            }
            # Merge style_settings and any previously set keys (like background_music_path)
            additional_settings = {**style_settings, **additional_settings}
            # Force set the streamlit logger
            if progress_bar_type == "Circle":
                import streamlit.components.v1 as components
                circle_html = '''
                <div id="circle-progress-bar" style="width: 100px; height: 100px;">
                  <svg viewBox="0 0 36 36" style="width:100px;height:100px;">
                    <path
                      stroke="#eee"
                      stroke-width="3.8"
                      fill="none"
                      d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      id="circle-bar"
                      stroke="#00aaff"
                      stroke-width="3.8"
                      stroke-dasharray="0, 100"
                      fill="none"
                      d="M18 2.0845
                        a 15.9155 15.9155 0 0 1 0 31.831
                        a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div id="circle-label" style="position:absolute;top:35px;left:32px;font-size:1.2em;">0%</div>
                </div>
                <script>
                window.setCircleProgress = function(percent) {
                  var bar = document.getElementById('circle-bar');
                  var label = document.getElementById('circle-label');
                  if(bar && label) {
                    bar.setAttribute('stroke-dasharray', (percent*100).toFixed(1)+', 100');
                    label.innerText = Math.round(percent*100) + '%';
                  }
                };
                </script>
                '''
                components.html(circle_html, height=120)
                def set_circle_progress(percent, text=None):
                    st.experimental_js("setCircleProgress", percent)
                additional_settings["streamlit_logger"] = set_circle_progress
            else:
                video_progress_bar = st.progress(0.0)
                additional_settings["streamlit_logger"] = video_progress_bar
            
            print("[DIAG] FINAL additional_settings before compile_video:", additional_settings, flush=True)
            
            # Run video export synchronously with live progress bar
            logger = StreamlitProglogLogger(progress_key='video_progress')
            output_file = video_processor.compile_video(
                processed_scenes,
                None,
                style_config.get('base_style', 'video'),
                additional_settings,  # Pass the combined dict with streamlit_logger
                None,
                logger=logger
            )
            progress_placeholder.empty()
            st.session_state['last_generated_video'] = output_file
            print(f"[DIAG] Export complete. output_file={output_file}")
            # Display completion message and video
            if output_file and os.path.exists(output_file):
                print(f"[DIAG] Video file exists. Displaying preview and download. Path: {output_file}")
                st.success(f"\U0001F389 Your video has been successfully generated!\n\nSaved at: {output_file}")
                st.video(output_file, format="video/mp4", start_time=0)
                with open(output_file, "rb") as file:
                    st.download_button(
                        label="Download Video",
                        data=file,
                        file_name=os.path.basename(output_file),
                        mime="video/mp4"
                    )
            else:
                print(f"[DIAG] Video generation completed, but the output file was not found: {output_file}")
                st.error("Video generation completed, but the output file was not found.")
                
    except Exception as e:
        # print(f"[DIAG] Exception in process_video_generation: {e}")
        logger.error(f"Error generating video: {str(e)}")
        st.error(f"Error generating video: {str(e)}")
        
    finally:
        # Always clear the progress bar and status text
        progress_placeholder.empty()
        status_text.empty()

# --- Add StreamlitProglogLogger for real-time progress ---
from proglog import ProgressBarLogger
import threading
import time

class StreamlitProglogLogger(ProgressBarLogger):
    def __init__(self, progress_key='video_progress'):
        super().__init__()
        self.progress_key = progress_key
    def callback(self, **changes):
        if 'progress' in changes:
            import streamlit as st
            st.session_state[self.progress_key] = changes['progress']
    
    # Add standard logging methods
    def warning(self, msg):
        print(f"[STREAMLIT LOGGER] WARNING: {msg}")
    
    def error(self, msg):
        print(f"[STREAMLIT LOGGER] ERROR: {msg}")
    
    def info(self, msg):
        print(f"[STREAMLIT LOGGER] INFO: {msg}")
    
    def debug(self, msg):
        print(f"[STREAMLIT LOGGER] DEBUG: {msg}")

# --- Video export with real progress bar ---
def run_export(video_processor, processed_scenes, style_config, additional_settings, output_file, progress_key):
    logger = StreamlitProglogLogger(progress_key=progress_key)
    # Call your actual MoviePy export here, passing logger
    video_processor.compile_video(
        processed_scenes,
        None,
        style_config.get('base_style', 'video'),
        additional_settings,  # Pass the combined dict with streamlit_logger
        output_file,
        logger=logger
    )

# --- In your main Streamlit UI logic, before export ---
def main() -> None:
    """Main application function."""
    st.title("🎬 Multi-Niche Video Generator")
    # Stepper logic
    if 'current_step' not in st.session_state:
        st.session_state['current_step'] = 1
    # Always get the latest step value right before step logic
    step = st.session_state['current_step']

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    steps = [
        (1, "Script Input"),
        (2, "Scene Editing"),
        (3, "Voice & Music"),
        (4, "Video Generation")
    ]
    for idx, label in steps:
        if st.sidebar.button(label, key=f"sidebar_nav_{idx}"):
            st.session_state['current_step'] = idx
            st.rerun()
    st.sidebar.markdown(f"**Current Step:** {steps[st.session_state['current_step']-1][1]}")

    # Step 1: Script Input
    if step == 1:
        # --- Choose Script Input Mode: Manual or API ---
        script_input_mode = st.radio(
            "How do you want to provide your script?",
            ["Manual Entry (Paste/Write)", "Fetch from API (Auto)"]
        )
        if script_input_mode == "Manual Entry (Paste/Write)":
            # --- Sample Script Section (show at the top for easy copy) ---
            st.markdown("""
            **Sample Script Format (Copy & Edit):**
            ```json
            {
              "title": "Sample Video Title",
              "description": "A quick video about sample scenes.",
              "author": "Your Name",
              "category": "Education",
              "language": "en",
              "tags": ["sample", "education", "demo"],
              "scenes": [
                {
                  "scene_number": 1,
                  "title": "Introduction",
                  "background": {"type": "color", "value": "#222244"},
                  "script": "Welcome! This is the intro scene.",
                  "duration": 5
                },
                {
                  "scene_number": 2,
                  "title": "Main Content",
                  "background": {"type": "api", "value": "office"},
                  "script": "Here we show the main content.",
                  "duration": 6
                }
              ]
            }
            ```
            - Paste your script below or edit the sample. Fields can be in JSON, YAML, or label:value format.
            - Only `scene_number`, `title`, `script`, and `background` are required per scene initially.
            """)
            # --- Paste or Write Script Window (move to the top, before metadata fields) ---
            # Always keep script input in session state to survive reruns and step changes
            if 'script_text' not in st.session_state:
                st.session_state['script_text'] = ''
            full_script = st.text_area('Paste or Write Your Script Here', value=st.session_state['script_text'], height=250, key='script_input')
            st.session_state['script_text'] = full_script
            if st.button("Save Script", key="save_script_btn"):
                try:
                    parsed = json.loads(full_script)
                    # Accept either a list (legacy) or an object with 'scenes' (modern)
                    if isinstance(parsed, list):
                        st.session_state['script_text'] = full_script
                        st.session_state['script_metadata'] = {"scenes": parsed}
                        st.success("Script saved and metadata auto-filled!")
                    elif isinstance(parsed, dict) and 'scenes' in parsed and isinstance(parsed['scenes'], list):
                        st.session_state['script_text'] = full_script
                        st.session_state['script_metadata'] = {"scenes": parsed['scenes']}
                        # Auto-fill metadata fields
                        for k in ['title','description','author','category','language','tags','slogan','overlay_color','animate']:
                            if k in parsed:
                                st.session_state[f'meta_{k}'] = parsed[k]
                        st.success("Script saved and metadata auto-filled!")
                    else:
                        st.error("Script must be a JSON array of scenes or an object with a 'scenes' array.")
                except Exception as e:
                    st.error(f"Script is not valid JSON: {e}")
            # --- Metadata Fields (move inside script section) ---
            _tags_val = st.session_state.get('meta_tags', [])
            if isinstance(_tags_val, str):
                _tags_val = [t.strip() for t in _tags_val.split(',') if t.strip()]
            meta_title = st.text_input('Video Title', value=st.session_state.get('meta_title', ''), key='meta_title_main_script')
            meta_desc = st.text_area('Description', value=st.session_state.get('meta_desc', ''), key='meta_desc_main_script')
            meta_author = st.text_input('Author', value=st.session_state.get('meta_author', ''), key='meta_author_main_script')
            meta_category = st.text_input('Category', value=st.session_state.get('meta_category', ''), key='meta_category_main_script')
            meta_language = st.text_input('Language', value=st.session_state.get('meta_language', ''), key='meta_language_main_script')
            meta_tags = st.text_input('Tags (comma separated)', value=','.join(_tags_val), key='meta_tags_main_script')
            meta_logo = st.file_uploader('Upload Logo (PNG/JPG, transparent preferred)', type=['png', 'jpg', 'jpeg'], key='meta_logo_main_script')
            if meta_logo:
                st.session_state['meta_logo_bytes'] = meta_logo.read()
            meta_watermark = st.file_uploader('Upload Watermark (PNG/JPG, semi-transparent recommended)', type=['png', 'jpg', 'jpeg'], key='meta_watermark_main_script')
            if meta_watermark:
                st.session_state['meta_watermark_bytes'] = meta_watermark.read()
            meta_slogan = st.text_input('Slogan (optional)', value=st.session_state.get('meta_slogan', ''), key='meta_slogan_main_script')
            st.caption('💡 You can paste JSON, YAML, or label:value lines. Metadata will be auto-filled if fields are left empty.')
            st.session_state['script_data'] = {
                **st.session_state.get('script_data', {}),
                'title': meta_title,
                'description': meta_desc,
                'author': meta_author,
                'category': meta_category,
                'language': meta_language,
                'tags': [t.strip() for t in meta_tags.split(',') if t.strip()],
                'slogan': meta_slogan,
                'overlay_color': st.session_state.get('meta_overlay_color', '#222244'),
                'animate': st.session_state.get('meta_animate', False),
                'script': full_script,
                'scenes': st.session_state.get('script_data', {}).get('scenes', [])
            }
            # Only render button if not already rendered in this rerun
            if 'meta_fields_btn_rendered' not in st.session_state or not st.session_state['meta_fields_btn_rendered']:
                if st.button("Save All Fields", key="save_all_fields_btn_script_section"):
                    st.session_state['script_text'] = full_script
                    st.session_state['meta_title'] = meta_title
                    st.session_state['meta_desc'] = meta_desc
                    st.session_state['meta_author'] = meta_author
                    st.session_state['meta_category'] = meta_category
                    st.session_state['meta_language'] = meta_language
                    st.session_state['meta_tags'] = [t.strip() for t in meta_tags.split(',') if t.strip()]
                    st.session_state['meta_slogan'] = meta_slogan
                    st.session_state['meta_overlay_color'] = st.session_state.get('meta_overlay_color', '#222244')
                    st.session_state['meta_animate'] = st.session_state.get('meta_animate', False)
                    st.success("All script and metadata fields saved!")
                if st.button("Continue to Scene Section", key="continue_to_scene_btn_script_section_1"):
                    st.session_state['current_step'] = 2
                    st.rerun()
                st.session_state['meta_fields_btn_rendered'] = True
        else:
            st.markdown('**Fetch Script from API**')
            api_url = st.text_input('API Endpoint URL', key='script_api_url')
            api_key = st.text_input('API Key (optional)', key='script_api_key', type='password')
            fetch_btn = st.button('Fetch Script', key='fetch_script_btn')
            script_data = st.session_state.get('script_data', {})
            scenes = st.session_state.get('scenes', [])
            if fetch_btn and api_url:
                import requests
                headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
                try:
                    resp = requests.get(api_url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    fetched = resp.text
                    st.success('Script fetched from API!')
                    st.session_state['api_script_text'] = fetched
                    full_script = st.text_area("Edit Script", value=st.session_state.get('api_script_text', ''), key="api_script_text")
                    st.session_state['script_data'] = {**script_data, 'script': fetched}
                except Exception as e:
                    st.error(f'Failed to fetch script: {e}')
        # (metadata fields now come after script input)
        # REMOVE second rendering of metadata fields here
        # meta_title = st.text_input('Video Title', value=st.session_state.get('meta_title', ''), key='meta_title_main_main')
        # meta_desc = st.text_area('Description', value=st.session_state.get('meta_desc', ''), key='meta_desc_main_main')
        # meta_author = st.text_input('Author', value=st.session_state.get('meta_author', ''), key='meta_author_main_main')
        # meta_category = st.text_input('Category', value=st.session_state.get('meta_category', ''), key='meta_category_main_main')
        # meta_language = st.text_input('Language', value=st.session_state.get('meta_language', ''), key='meta_language_main_main')
        # meta_tags = st.text_input('Tags (comma separated)', value=','.join(_tags_val), key='meta_tags_main_main')
        # meta_slogan = st.text_input('Slogan (optional)', value=st.session_state.get('meta_slogan', ''), key='meta_slogan_main_main')
        # st.caption('💡 You can paste JSON, YAML, or label:value lines. Metadata will be auto-filled if fields are left empty.')
        # Store script and (possibly updated) meta in session state
        # st.session_state['script_data'] = {
        #     **st.session_state.get('script_data', {}),
        #     'title': meta_title,
        #     'description': meta_desc,
        #     'author': meta_author,
        #     'category': meta_category,
        #     'language': meta_language,
        #     'tags': [t.strip() for t in meta_tags.split(',') if t.strip()],
        #     'slogan': meta_slogan,
        #     'overlay_color': st.session_state.get('meta_overlay_color', '#222244'),
        #     'animate': st.session_state.get('meta_animate', False),
        #     'script': full_script,
        #     'scenes': st.session_state.get('script_data', {}).get('scenes', [])
        # }
        if st.button("Save All Fields", key="save_all_fields_btn_main_section"):
            st.session_state['script_text'] = full_script
            st.session_state['meta_title'] = meta_title
            st.session_state['meta_desc'] = meta_desc
            st.session_state['meta_author'] = meta_author
            st.session_state['meta_category'] = meta_category
            st.session_state['meta_language'] = meta_language
            st.session_state['meta_tags'] = [t.strip() for t in meta_tags.split(',') if t.strip()]
            st.session_state['meta_slogan'] = meta_slogan
            st.session_state['meta_overlay_color'] = st.session_state.get('meta_overlay_color', '#222244')
            st.session_state['meta_animate'] = st.session_state.get('meta_animate', False)
            st.success("All script and metadata fields saved!")
        if st.button("Continue to Scene Section", key="continue_to_scene_btn_script_section_2"):
            st.session_state['current_step'] = 2
            st.rerun()
        return
    # Step 2: Scene Editing
    elif step == 2:
        st.header("Step 2: Scene Editing")
        # Always get scenes from the latest script_metadata if available
        scenes = st.session_state.get('scenes')
        if not scenes:
            # Try to pull from script_metadata (which is set on Save Script)
            script_metadata = st.session_state.get('script_metadata', {})
            if isinstance(script_metadata, dict) and 'scenes' in script_metadata:
                scenes = script_metadata['scenes']
                st.session_state['scenes'] = scenes
            else:
                st.warning('No scenes found. Please go back and save your script first.')
                return
        edited_scenes = scene_editor(scenes)
        if st.button("Save Scene Edits", key="save_scene_edits"):
            st.session_state['scenes'] = edited_scenes
            st.success("Scenes saved!")
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Back to Script Input", key="back_to_script_input"):
                st.session_state['current_step'] = 1
                st.rerun()
        with col2:
            if st.button("Continue to Voice & Music", key="to_voice_music"):
                st.session_state['current_step'] = 3
                st.rerun()

    # Step 3: Voice & Music
    elif step == 3:
        st.header("Step 3: Voice Over & Music")
        tts_lang, tts_speed = voice_and_style_selector_tts()
        music_config = music_selection_ui("global")
        print(f"[DIAG] music_config returned: {music_config}")
        # Save uploaded music file to disk and store path in session
        if music_config and music_config.get('file') is not None:
            uploaded_music_file = music_config['file']
            music_save_path = None
            if uploaded_music_file:
                music_save_path = os.path.join(tempfile.gettempdir(), f"uploaded_bg_music_{int(time.time())}.mp3")
                with open(music_save_path, "wb") as f:
                    f.write(uploaded_music_file.read())
                print(f"[DIAG] Saved uploaded background music to: {music_save_path}")
                st.session_state['background_music_path'] = music_save_path
            else:
                print(f"[DIAG] No uploaded music file to save.")
        else:
            print(f"[DIAG] No music file in music_config.")
        if st.button("Save Voice & Music Config", key="save_voice_music"):
            st.session_state['music_config'] = music_config
            st.success("Voice & Music settings saved!")
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Back to Scene Editing", key="back_to_scene_editing"):
                st.session_state['current_step'] = 2
                st.rerun()
        with col2:
            if st.button("Continue to Video Generation", key="to_video_generation"):
                st.session_state['current_step'] = 4
                st.rerun()

    # Step 4: Video Generation
    elif step == 4:
        st.header("Step 4: Video Generation")
        st.subheader("Step 4: Video Generation")
        # Optional: Start Over button
        if st.button("Start Over"):
            st.session_state.clear()
            st.experimental_rerun()
        style_name, style_config = style_selector(return_name=True)
        st.session_state['selected_style_name'] = style_name
        st.session_state['selected_style_config'] = style_config
        script_data = st.session_state.get('script_data', {})
        scenes = st.session_state.get('scenes', [])
        video_processor = VideoProcessor()
        video_logic_handler = VideoLogic()
        # --- Subtitle position selection UI (moved outside button block for visibility) ---
        subtitle_position = st.selectbox(
            "Subtitle Position",
            options=["bottom", "center"],
            index=0,
            help="Choose where subtitles appear in the video."
        )
        # ---
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("Back to Voice & Music", key="back_to_voice_music"):
                st.session_state['current_step'] = 3
                st.rerun()
        with col2:
            if st.button("Generate Video", key="generate_video_btn_final"):
                print("[DIAG] Generate Video button clicked")
                print(f"[DIAG] Additional settings at button click: {style_config}")
                # --- Prepare additional_settings for video export ---
                additional_settings = dict(style_config)
                # Attach background music path if available
                bg_music_path = st.session_state.get('background_music_path', None)
                if bg_music_path:
                    additional_settings['background_music_path'] = bg_music_path
                    print(f"[DIAG] Passing background_music_path to export: {bg_music_path}")
                else:
                    print(f"[DIAG] No background_music_path in session_state at export.")
                # --- Progress spinner for export ---
                with st.spinner("Generating your video. This may take a minute..."):
                    print("[DIAG] Spinner shown. Entering export block.")
                    logger = StreamlitProglogLogger(progress_key='video_progress')
                    output_file = video_processor.compile_video(
                        scenes,
                        None,
                        style_config.get('base_style', 'video'),
                        additional_settings,  # Pass the combined dict with streamlit_logger
                        None,
                        logger=logger
                    )
                    print(f"[DIAG] Export complete in spinner. output_file={output_file}")
                st.session_state['last_generated_video'] = output_file
                print(f"[DIAG] Export complete. output_file={output_file}")
                # Display completion message and video
                if output_file and os.path.exists(output_file):
                    print(f"[DIAG] Video file exists. Displaying preview and download. Path: {output_file}")
                    st.success(f"\U0001F389 Your video has been successfully generated!\n\nSaved at: {output_file}")
                    st.video(output_file, format="video/mp4", start_time=0)
                    with open(output_file, "rb") as file:
                        st.download_button(
                            label="Download Video",
                            data=file,
                            file_name=os.path.basename(output_file),
                            mime="video/mp4"
                        )
                else:
                    print(f"[DIAG] Video generation completed, but the output file was not found: {output_file}")
                    st.error("Video generation completed, but the output file was not found.")
                
if __name__ == "__main__":
    def sanitize_scene(scene):
        scene_copy = dict(scene)
        for k, v in scene_copy.items():
            if isinstance(v, (bytes, bytearray)):
                scene_copy[k] = f"<bytes, length={len(v)}>"
        return scene_copy

    # Sanitize scenes before storing in session state
    if 'script_json_input' in st.session_state:
        script_text = st.session_state['script_json_input']
        try:
            data = json.loads(script_text)
            if 'scenes' in data:
                st.session_state['scenes'] = [sanitize_scene(s) for s in data['scenes']]
            else:
                st.session_state['scenes'] = data['scenes']
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    main()
