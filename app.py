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

import os
import yaml
import json
import time
from typing import Dict, List, Optional, Tuple
from Content_Engine.api_generator import ScriptGenerator
from Content_Engine.scene_generator import generate_scene_metadata
from Media_Handler.voice_system import VoiceSystem
from Media_Handler.video_processor import VideoProcessor
from Media_Handler.video_logic import VideoLogic
import logging
from pathlib import Path

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
        st.error(f"Error loading config: {e}")
        return {}

def load_project(project_path: str) -> dict:
    """Load a saved project from JSON file."""
    try:
        with open(project_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        st.error(f"Error loading project: {e}")
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
        st.error(f"Error saving project: {e}")
        return ""

def generate_script(script_generator: ScriptGenerator, generation_method: str) -> Tuple[str, Dict]:
    """Generate script based on selected method."""
    script_text = ""
    metadata = {}
    
    if generation_method == "AI Generation":
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # AI Provider selection
            ai_provider = st.selectbox(
                "Select AI Provider:",
                options=["OpenAI", "Anthropic", "Llama", "Custom"],
                index=0
            )
            
            # Topic input
            topic = st.text_input("Enter your video topic:", placeholder="e.g., Benefits of meditation")
            
            # Target audience
            audience = st.text_input("Target audience:", placeholder="e.g., Beginners interested in mindfulness")
            
            # Tone selection
            tone = st.selectbox(
                "Select tone:",
                options=["Informative", "Casual", "Professional", "Entertaining", "Educational"],
                index=0
            )
            
            # Length selection
            length = st.select_slider(
                "Script length:",
                options=["Very Short", "Short", "Medium", "Long", "Very Long"],
                value="Medium"
            )
            
            # Additional instructions
            additional_instructions = st.text_area(
                "Additional instructions (optional):",
                placeholder="Any specific points to include or exclude..."
            )
            
            # API key input (with secure input)
            api_key = st.text_input(f"{ai_provider} API Key:", type="password")
            
            # Save API key option
            save_api_key = st.checkbox("Save API key for future use")
            
            prompt = f"Create a {length.lower()} video script about '{topic}' in a {tone.lower()} tone for {audience}."
            if additional_instructions:
                prompt += f" Additional instructions: {additional_instructions}"
            
            metadata = {
                "generation_method": "ai",
                "ai_provider": ai_provider,
                "topic": topic,
                "audience": audience,
                "tone": tone,
                "length": length
            }
            
            if st.button("Generate Script", key="generate_ai_script"):
                if not api_key:
                    st.error("Please provide an API key to use AI generation.")
                    return script_text, metadata
                
                with st.spinner(f"Generating script using {ai_provider}..."):
                    try:
                        # Set the API key for the generator
                        script_generator.set_api_key(ai_provider.lower(), api_key)
                        
                        # Save API key if requested
                        if save_api_key:
                            # We'd implement proper secure storage here
                            st.success(f"{ai_provider} API key saved for future use.")
                        
                        # Generate the script
                        script_text = script_generator.generate_with_ai(
                            prompt=prompt,
                            provider=ai_provider.lower()
                        )
                        st.session_state.script_text = script_text
                        st.session_state.script_metadata = metadata
                        st.success("Script generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating script: {e}")
        
        with col2:
            st.markdown("### AI Generation Tips")
            st.markdown("- Be specific about your topic")
            st.markdown("- Define your audience clearly")
            st.markdown("- Choose the right tone for your content")
            st.markdown("- Specify any important details")
    else:  # Manual input
        col1, col2 = st.columns([2, 1])
        with col1:
            script_text = st.text_area("Enter your script:", height=300)
            if script_text and st.button("Save Script", key="save_manual_script"):
                st.session_state.script_text = script_text
                metadata = {"manual_input": True}
                st.session_state.script_metadata = metadata
                st.success("Script saved successfully!")
        
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
    
    return script_text, metadata

def scene_editor(scenes: List[Dict]) -> List[Dict]:
    """Interactive scene editor for modifying scene metadata."""
    edited_scenes = scenes.copy()
    
    st.markdown("### Scene Editor")
    st.info("Edit each scene to customize your video. You can modify text, duration, and visual elements.")
    
    for i, scene in enumerate(edited_scenes):
        with st.expander(f"Scene {i+1}: {scene.get('title', 'Untitled')}"):
            edited_scenes[i]['text'] = st.text_area(
                "Scene Text", 
                scene.get('text', ''), 
                key=f"scene_text_{i}"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                edited_scenes[i]['duration'] = st.slider(
                    "Duration (seconds)", 
                    min_value=1.0, 
                    max_value=20.0, 
                    value=float(scene.get('duration', 5.0)),
                    step=0.5,
                    key=f"scene_duration_{i}"
                )
            
            with col2:
                edited_scenes[i]['transition'] = st.selectbox(
                    "Transition",
                    options=["cut", "fade", "dissolve", "wipe", "slide"],
                    index=["cut", "fade", "dissolve", "wipe", "slide"].index(scene.get('transition', 'fade')),
                    key=f"scene_transition_{i}"
                )
            
            edited_scenes[i]['visual_prompt'] = st.text_area(
                "Visual Description/Prompt",
                scene.get('visual_prompt', ''),
                key=f"scene_visual_{i}"
            )
    
    return edited_scenes

def voice_selector(voice_system: VoiceSystem) -> str:
    """Enhanced voice selection interface."""
    voices = voice_system.list_available_voices()
    provider_voices = {k: v for k, v in voices.items()}
    voice_id = None
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Female Voices")
        female_voices = {
            voice_id: voice for voice_id, voice in provider_voices.items()
            if voice.gender and voice.gender.lower() == 'female'
        }
        if not female_voices:
            st.info("No female voices available")
        for vid, voice in female_voices.items():
            if st.button(f"{voice.name} ({voice.language})", key=f"voice_{vid}"):
                st.session_state.selected_voice_id = vid
                st.rerun()
                return vid
    with col2:
        st.markdown("#### Male Voices")
        male_voices = {
            voice_id: voice for voice_id, voice in provider_voices.items()
            if voice.gender and voice.gender.lower() == 'male'
        }
        if not male_voices:
            st.info("No male voices available")
        for vid, voice in male_voices.items():
            if st.button(f"{voice.name} ({voice.language})", key=f"voice_{vid}"):
                st.session_state.selected_voice_id = vid
                st.rerun()
                return vid
    st.markdown("#### Other Voices")
    other_voices = {
        voice_id: voice for voice_id, voice in provider_voices.items()
        if not voice.gender or voice.gender.lower() not in ['male', 'female']
    }
    if not other_voices:
        st.info("No other voices available")
    for vid, voice in other_voices.items():
        if st.button(f"{voice.name} ({voice.language})", key=f"voice_other_{vid}"):
            st.session_state.selected_voice_id = vid
            st.rerun()
            return vid
    if 'selected_voice_id' in st.session_state:
        voice_id = st.session_state.selected_voice_id
        voice = voices.get(voice_id)
        if voice:
            st.success(f"**Selected Voice:** {voice.name} ({voice.gender or 'Unknown gender'}, {voice.language})")
            if st.button("Play Sample"):
                sample_text = "This is a sample of my voice. I hope you like how it sounds."
                sample_file = voice_system.backend.generate_voice(sample_text, voice_id)
                if sample_file:
                    st.audio(sample_file)
    return voice_id

def style_selector() -> dict:
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
    voice_system: VoiceSystem, 
    video_processor: VideoProcessor,
    video_logic_handler: VideoLogic,
    voice_id: str,
    style_config: Dict = None
) -> None:
    import time  # Ensure time is imported at the top of the function
    """Process video generation."""
    if not scenes:
        st.error("No scenes available for processing.")
        return
        
    if not voice_id:
        st.error("Please select a voice first.")
        return
        
    if not style_config:
        style_config = {"base_style": "modern"}
        
    # Create a placeholder for progress bar
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    
    # Create status text
    status_text = st.empty()
    
    try:
        with st.spinner("Generating your video..."):
            # Phase 1: Voice Generation
            status_text.markdown("**Generating voice-overs...**")
            audio_files = []
            
            for i, scene in enumerate(scenes):
                if 'text' in scene:
                    audio_file = voice_system.backend.generate_voice(scene['text'], voice_id)
                    if audio_file:
                        audio_files.append(audio_file)
                    progress_bar.progress((i + 1) / (len(scenes) * 3))  # First third of progress
            
            status_text.markdown("✅ Voice generation complete!")
            
            # Phase 2: Scene Processing
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
                scene_audio = audio_files[i] if i < len(audio_files) else None
                processed = video_logic_handler.process_scene(
                    scene, 
                    style_dict,
                    scene_audio
                )
                if processed:
                    processed_scenes.append(processed)
                progress_bar.progress((len(scenes) + i + 1) / (len(scenes) * 3))  # Second third
            
            status_text.markdown("✅ Scene processing complete!")
            
            # Phase 3: Video Compilation
            status_text.markdown("**Compiling final video...**")
            
            output_file = video_processor.compile_video(
                scenes=processed_scenes,
                output_name=f"{style_config.get('base_style', 'video')}_{int(time.time())}.mp4",
                audio_files=audio_files,
                additional_settings=style_dict
            )
            
            for i in range(len(scenes)):
                progress_bar.progress((2 * len(scenes) + i + 1) / (len(scenes) * 3))  # Final third
                time.sleep(0.1)  # Simulate processing time
                
            status_text.markdown("✅ Video compilation complete!")
            progress_bar.progress(1.0)
            
            # Display completion message and video
            import time
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
        st.error(f"Error generating video: {str(e)}")
        logger.error(f"Video generation error: {str(e)}", exc_info=True)
        
    finally:
        # Always clear the progress bar and status text
        progress_placeholder.empty()
        status_text.empty()

def init_session_state():
    """Initialize session state variables."""
    if 'project_data' not in st.session_state:
        st.session_state.project_data = {}
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'scenes' not in st.session_state:
        st.session_state.scenes = []
    if 'selected_tab' not in st.session_state:
        st.session_state.selected_tab = 0
    if 'script_text' not in st.session_state:
        st.session_state.script_text = ""
    if 'selected_voice_id' not in st.session_state:
        st.session_state.selected_voice_id = ""
    if 'selected_style' not in st.session_state:
        st.session_state.selected_style = "modern"

def main() -> None:
    """Main application function."""
    init_session_state()
    
    # Display header with logo
    st.markdown('<h1 class="main-header">🎬 Multi-Niche Video Generation System</h1>', unsafe_allow_html=True)
    
    # Initialize components
    config = load_config()
    script_generator = ScriptGenerator()
    voice_system = VoiceSystem()
    video_processor = VideoProcessor()
    video_logic_handler = VideoLogic(config.get('video', {}))
    
    # Sidebar for project management
    with st.sidebar:
        st.markdown("### Project Management")
        
        # Project operations
        project_action = st.radio(
            "Project Action:",
            options=["New Project", "Load Project", "Save Project"]
        )
        
        if project_action == "New Project":
            if st.button("Start New Project"):
                st.session_state.project_data = {}
                st.session_state.current_step = 1
                st.session_state.selected_tab = 0
                st.session_state.scenes = []
                st.session_state.script_text = ""
                st.success("New project started!")
                st.rerun()
                
        elif project_action == "Load Project":
            # List available projects
            projects_dir = Path("projects")
            if projects_dir.exists():
                project_files = list(projects_dir.glob("*.json"))
                if project_files:
                    project_options = [p.stem for p in project_files]
                    selected_project = st.selectbox("Select Project:", options=project_options)
                    
                    if st.button("Load Project"):
                        project_data = load_project(f"projects/{selected_project}.json")
                        if project_data:
                            st.session_state.project_data = project_data
                            st.session_state.current_step = 1
                            st.session_state.selected_tab = 0
                            # Load saved project data into session
                            if "niche" in project_data:
                                st.session_state.selected_niche = project_data["niche"]
                            if "script" in project_data:
                                st.session_state.script_text = project_data["script"]
                            if "scenes" in project_data:
                                st.session_state.scenes = project_data["scenes"]
                            if "voice_id" in project_data:
                                st.session_state.selected_voice_id = project_data["voice_id"]
                            if "style" in project_data:
                                st.session_state.selected_style = project_data["style"]
                            st.success(f"Project '{selected_project}' loaded!")
                            st.rerun()
                else:
                    st.info("No saved projects found.")
            else:
                st.info("No projects directory found.")
                
        elif project_action == "Save Project":
            project_name = st.text_input("Project Name:")
            
            if project_name and st.button("Save Project"):
                # Collect current project data
                project_data = {
                    "name": project_name,
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "niche": st.session_state.get("selected_niche", ""),
                    "script": st.session_state.get("script_text", ""),
                    "scenes": st.session_state.get("scenes", []),
                    "voice_id": st.session_state.get("selected_voice_id", ""),
                    "style": st.session_state.get("selected_style", "modern")
                }
                
                project_path = save_project(project_data, project_name)
                if project_path:
                    st.success(f"Project saved to {project_path}")
        
        # System settings
        st.markdown("### System Settings")
        debug_mode = st.checkbox("Debug Mode", value=config.get("debug_mode", False))
        advanced_mode = st.checkbox("Advanced Mode", value=False)
        
        if debug_mode:
            st.info("Debug mode enabled. Logs will be more verbose.")
        
        # Help section
        with st.expander("Help & Documentation"):
            st.markdown("""
            #### Quick Help
            - Start by selecting a content niche
            - Generate or input your script
            - Edit scenes as needed
            - Select voice and style
            - Generate your video
            
            Need more help? Check the [documentation](https://example.com/docs).
            """)
    
    # Main workflow with wizard-style navigation (no st.tabs)
    section_titles = [
        "Script Generation",
        "Scene Editing",
        "Voice & Style",
        "Generate Video"
    ]
    current_tab = st.session_state.selected_tab
    st.markdown(f'<h2 class="section-header">{section_titles[current_tab]}</h2>', unsafe_allow_html=True)

    if current_tab == 0:
        # --- Script Generation Section ---
        st.markdown("### Script Generation")
        niches = script_generator.get_available_niches() + ["islamic"]
        selected_niche = st.selectbox("Select Content Niche", [n.title() for n in niches], key="niche_select")
        st.session_state.selected_niche = selected_niche.lower()
        generation_method = st.radio(
            "Choose script generation method:",
            options=["Manual input", "AI Generation"],
            index=0
        )
        script_text = st.session_state.get('script_text', '')
        script_metadata = st.session_state.get('script_metadata', {})
        manual_script_saved = st.session_state.get('manual_script_saved', False)
        if generation_method == "AI Generation":
            script_text, script_metadata = generate_script(script_generator, "AI Generation")
            st.session_state.manual_script_saved = True  # Always allow continue after AI
        else:
            col1, col2 = st.columns([2, 1])
            with col1:
                script_text = st.text_area("Paste your script below (scenes separated as instructed):", script_text, height=250, key="script_input")
                if script_text and st.button("Save Script", key="save_manual_script"):
                    st.session_state.script_text = script_text
                    st.session_state.script_metadata = {"manual_input": True}
                    st.session_state.manual_script_saved = True
                    st.success("Script saved successfully!")
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
        if st.button("Save and Continue", key="continue_to_scene_editing"):
            if generation_method == "Manual input" and not st.session_state.get('manual_script_saved', False):
                st.error("Please save your manually entered script before continuing.")
            elif not script_text:
                st.error("Please enter or generate a script before continuing.")
            else:
                st.session_state.script_text = script_text
                script_generator.switch_niche(selected_niche.lower())
                try:
                    scenes = generate_scene_metadata(script_text)
                    if not scenes:
                        st.error("Could not split script into scenes. Please check the script content format.")
                    else:
                        st.session_state.scenes = scenes
                        st.session_state.current_step = 2
                        st.session_state.selected_tab = 1
                        st.session_state.manual_script_saved = False  # Reset for next time
                        st.rerun()
                except Exception as e:
                    st.error(f"Error generating scene metadata: {e}")

    elif current_tab == 1:
        # --- Scene Editing Section ---
        st.markdown("### Scene Editor")
        if 'scenes' not in st.session_state or not st.session_state.scenes:
            st.warning("Please provide a script and generate scenes in the previous step first.")
            if st.button("Back to Script Generation", key="back_to_script"):
                st.session_state.selected_tab = 0
                st.rerun()
        else:
            # Always initialize scene_editor_state from script scenes if not present or different length
            if ('scene_editor_state' not in st.session_state or
                not st.session_state.scene_editor_state.get("scenes") or
                len(st.session_state.scene_editor_state["scenes"]) != len(st.session_state.scenes)):
                st.session_state.scene_editor_state = {"scenes": [scene.copy() for scene in st.session_state.scenes]}
            scenes_state = st.session_state.scene_editor_state["scenes"]
            st.info("Edit, add, or remove scenes. You can modify text, duration, and visual elements.")
            remove_indices = []
            for i, scene in enumerate(scenes_state):
                with st.expander(f"Scene {i+1}: {scene.get('title', 'Untitled')}"):
                    scenes_state[i]['text'] = st.text_area(
                        "Scene Text", 
                        scene.get('text', ''), 
                        key=f"scene_text_{i}"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        scenes_state[i]['duration'] = st.slider(
                            "Duration (seconds)", 
                            min_value=1.0, 
                            max_value=20.0, 
                            value=float(scene.get('duration', 5.0)),
                            step=0.5,
                            key=f"scene_duration_{i}"
                        )
                    with col2:
                        scenes_state[i]['transition'] = st.selectbox(
                            "Transition",
                            options=["cut", "fade", "dissolve", "wipe", "slide"],
                            index=["cut", "fade", "dissolve", "wipe", "slide"].index(scene.get('transition', 'fade')),
                            key=f"scene_transition_{i}"
                        )
                    scenes_state[i]['visual_prompt'] = st.text_area(
                        "Visual Description/Prompt",
                        scene.get('visual_prompt', ''),
                        key=f"scene_visual_{i}"
                    )
                    if st.button(f"Remove Scene {i+1}", key=f"remove_scene_{i}"):
                        remove_indices.append(i)
            for idx in sorted(remove_indices, reverse=True):
                del scenes_state[idx]
            if st.button("Add Scene", key="add_scene"):
                scenes_state.append({
                    "text": "",
                    "duration": 5.0,
                    "transition": "fade",
                    "visual_prompt": "",
                    "title": f"Scene {len(scenes_state)+1}"
                })
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button("Back", key="scene_edit_back"):
                    st.session_state.selected_tab = 0
                    st.rerun()
            with nav_cols[2]:
                if st.button("Save and Continue", key="continue_to_voice_style"):
                    st.session_state.scenes = scenes_state.copy()
                    st.session_state.current_step = 3
                    st.session_state.selected_tab = 2
                    st.rerun()

    elif current_tab == 2:
        # --- Voice & Style Selection Section ---
        st.markdown('<h2 class="section-header">Voice & Style Selection</h2>', unsafe_allow_html=True)
        if 'scenes' not in st.session_state or not st.session_state.scenes:
            st.warning("Please complete the previous steps first.")
            if st.button("Back to Scene Editing", key="back_to_scene"):
                st.session_state.selected_tab = 1
                st.rerun()
        else:
            voice_style_cols = st.columns(2)
            with voice_style_cols[0]:
                voice_id = voice_selector(voice_system)
            with voice_style_cols[1]:
                style_config = style_selector()
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button("Back", key="voice_style_back"):
                    st.session_state.selected_tab = 1
                    st.rerun()
            with nav_cols[2]:
                if st.button("Save and Continue", key="continue_to_video_gen"):
                    if ('selected_voice_id' in st.session_state and st.session_state.selected_voice_id and 
                        'selected_style' in st.session_state and st.session_state.selected_style):
                        st.session_state.current_step = 4
                        st.session_state.selected_tab = 3
                        st.rerun()

    elif current_tab == 3:
        # --- Generate Video Section ---
        st.markdown('<h2 class="section-header">Generate Video</h2>', unsafe_allow_html=True)
        if ('scenes' not in st.session_state or not st.session_state.scenes or
            'selected_voice_id' not in st.session_state or not st.session_state.selected_voice_id or
            'selected_style' not in st.session_state or not st.session_state.selected_style):
            st.warning("Please complete all previous steps before generating video.")
            if st.button("Back to Voice & Style", key="back_to_voice"):
                st.session_state.selected_tab = 2
                st.rerun()
        else:
            # Display summary of selections
            st.markdown("### Project Summary")
            summary_cols = st.columns(3)
            with summary_cols[0]:
                st.markdown(f"**Content Niche:** {st.session_state.selected_niche.title()}")
                st.markdown(f"**Script Length:** {len(st.session_state.script_text)} characters")
            with summary_cols[1]:
                st.markdown(f"**Number of Scenes:** {len(st.session_state.scenes)}")
                voice = voice_system.list_available_voices().get(st.session_state.selected_voice_id)
                if voice:
                    st.markdown(f"**Voice:** {voice.name} ({voice.gender or 'Unknown'})")
            with summary_cols[2]:
                st.markdown(f"**Style:** {st.session_state.selected_style.title()}")
                est_duration = sum(float(scene.get('duration', 5.0)) for scene in st.session_state.scenes)
                st.markdown(f"**Estimated Duration:** {est_duration:.1f} seconds")
            # --- Video Settings UI ---
            st.markdown("#### Video Settings")
            # Aspect Ratio
            aspect_ratios = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:5": (4, 5)}
            aspect_label = st.selectbox("Aspect Ratio", list(aspect_ratios.keys()), index=0)
            aspect = aspect_ratios[aspect_label]
            # Resolution presets
            res_presets = ["HD (1280x720)", "Full HD (1920x1080)", "4K (3840x2160)", "Custom"]
            res_choice = st.selectbox("Resolution", res_presets, index=1)
            if res_choice == "Custom":
                width = st.number_input("Width (px)", min_value=320, max_value=4096, value=1920)
                height = st.number_input("Height (px)", min_value=320, max_value=4096, value=1080)
            else:
                preset_map = {"HD (1280x720)": (1280, 720), "Full HD (1920x1080)": (1920, 1080), "4K (3840x2160)": (3840, 2160)}
                width, height = preset_map[res_choice]
            # Adjust for aspect ratio
            aspect_w, aspect_h = aspect
            if width / aspect_w * aspect_h != height:
                # Snap height to match aspect ratio
                height = int(width / aspect_w * aspect_h)
            # Frame rate
            fps = st.number_input("Frame Rate (fps)", min_value=15, max_value=60, value=30)
            # Bitrate (optional, advanced)
            bitrate = st.text_input("Bitrate (e.g. 4M, 8M, 16M)", value="8M")
            if st.button("Generate Video", key="final_generate"):
                style_config = {
                    "base_style": st.session_state.selected_style,
                    "video_quality": st.session_state.get("selected_quality", "FHD"),
                    "aspect_ratio": aspect_label,
                    "resolution": (width, height),
                    "fps": fps,
                    "bitrate": bitrate
                }
                process_video_generation(
                    st.session_state.scenes,
                    voice_system,
                    video_processor,
                    video_logic_handler,
                    st.session_state.selected_voice_id,
                    style_config
                )

if __name__ == "__main__":
    main()
