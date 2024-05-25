# IConvo - Interactive Conversational AI Application

IConvo is an interactive conversational AI application that allows users to engage in natural language conversations with an AI assistant. The application supports various features such as voice input, text-to-speech output, image and video processing, and customizable commands.

## Features

- Natural language conversation with an AI assistant powered by OpenAI's GPT models
- Voice input using push-to-talk functionality
- Text-to-speech output for assistant responses
- Image capturing and processing using screen capture
- Video processing and transcription
- Customizable commands for triggering specific actions
- Configurable settings through a YAML configuration file
- Light and dark theme options for the user interface
- Logging of conversations and interactions
- Cross-platform compatibility (Windows, macOS, Linux)

## Installation

1. Clone the repository:
git clone https://github.com/LOR-Studio/IConvo.git

2. Install the required dependencies:
pip install -r requirements.txt

3. Set up the configuration:
- Open `config.yaml` and provide your OpenAI API key and other desired settings.

4. Run the application:
- Run `interface.py` in VS code or locally with dependencies.

## Configuration

The application can be configured using the `config.yaml` file. Here are the available configuration options:

- `api_key`: Your OpenAI API key.
- `model`: The OpenAI model to use for conversation (e.g., "gpt-3.5-turbo").
- `system_prompt`: The initial prompt to set the behavior of the AI assistant.
- `user_name`: The name of the user in the conversation.
- `assistant_name`: The name of the AI assistant in the conversation.
- `user_color`: The color of the user's messages in the console.
- `assistant_color`: The color of the assistant's messages in the console.
- `log_file`: The path to the log file for storing conversation logs.
- `max_history_length`: The maximum number of conversation turns to keep in the context.
- `max_response_tokens`: The maximum number of tokens allowed in the assistant's response.
- `push_to_talk_key`: The key to press and hold for voice input.
- `image_path`: The path to save captured images.
- `audio_path`: The path to save recorded audio.
- `image_max_size`: The maximum size of captured images (width, height).
- `image_quality`: The quality of captured images (0-100).
- `tts_model`: The text-to-speech model to use for generating audio responses.
- `tts_voice`: The voice to use for text-to-speech output.
- `commands`: Customizable commands and their associated keywords for triggering specific actions.

## Usage

1. Launch the application by running `python interface.py`.
2. The main window will appear with a conversation console, configuration editor, and an about section.
3. Type your message in the input box and press Enter to send it to the AI assistant.
4. The assistant will generate a response, which will be displayed in the console and played back as audio.
5. To use voice input, press to toggle the configured push-to-talk key while speaking, and toggle it when done.
6. Customize the application settings by editing the `config.yaml` file or through the configuration editor in the application.
7. Use the defined commands (e.g., "screenshot", "process videoWIP", "transcription") to trigger specific actions.
8. The conversation logs will be stored in the specified log file for later reference.

## Dependencies

- OpenAI: For natural language processing and conversation generation.
- PyAudio: For audio input and output.
- PyAutoGUI: For screen capture functionality.
- MoviePy: For video processing and transcription.
- NLTK: For natural language processing tasks.
- Pygame: For audio playback.
- Tkinter: For building the graphical user interface.

For a complete list of dependencies, please refer to the `requirements.txt` file.

## Contributing

Contributions to IConvo are welcome! If you find any bugs, have feature requests, or want to contribute improvements, please open an issue or submit a pull request on the GitHub repository.