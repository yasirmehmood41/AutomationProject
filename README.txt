AutomationProject
Overview
This project automates content creation using AI-powered tools. It includes:

Content Engine (AI-assisted script processing and scene generation)
Media Handler (Optimized video/audio asset management)
Manual Interface (Real-time preview and quick editing)
Output Manager (Quality control and batch processing)
Folder Structure

AutomationProject/
│── content_engine/       # AI processing for scripts and scenes
│── media_handler/        # Handles assets and optimizes media
│── manual_interface/     # User interaction and real-time preview
│── output_manager/       # Exports, quality checks, and batch processing
│── requirements.txt      # Dependencies for the project
│── README.md             # Documentation
│── main.py               # Entry point of the project
└── .venv/                # Virtual environment (if applicable)

# Video Generation Automation Project

A powerful tool for automating video creation with script processing, voice-over generation, and dynamic video editing.

## Features

1. **Script Processing**:
   - Manual script input
   - Script pasting
   - API-based script generation
   - Scene parsing and formatting

2. **Voice Generation**:
   - Local TTS voices (Windows)
   - ElevenLabs integration
   - Multiple voice options
   - Optional advanced features (Google Cloud, AWS Polly)

3. **Video Processing**:
   - Dynamic scene generation
   - Text-to-speech synchronization
   - Background color management
   - Word highlighting effects

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AutomationProject.git
   cd AutomationProject
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your API keys:
     ```
     ELEVENLABS_API_KEY=your_key_here
     OPENAI_API_KEY=your_key_here
     ```

## Usage

1. Run the main script:
   ```bash
   python main.py
   ```

2. Follow the interactive prompts to:
   - Input or generate script
   - Select voice type
   - Generate video

## Project Structure

```
AutomationProject/
├── Content_Engine/        # Script and content generation
│   ├── api_generator.py   # API-based script generation
│   ├── script_processor.py# Script parsing and processing
│   └── template_manager.py# Template management
├── Media_Handler/         # Audio and video processing
│   ├── voice_system.py   # Voice generation system
│   └── video_processor.py# Video creation and effects
├── Output_Manager/        # Export and quality control
│   └── export_manager.py # Video export handling
├── main.py               # Main entry point
└── requirements.txt      # Project dependencies
```

## Advanced Features

Optional advanced features require additional dependencies:
```bash
pip install google-cloud-texttospeech boto3
```

This enables:
- Google Cloud TTS
- AWS Polly
- Voice cloning
- Batch processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.