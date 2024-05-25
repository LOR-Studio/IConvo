# IConvo/main.py

from openai import OpenAI
from chat_function import get_chat_response, load_config, setup_logging, trim_history
from speech_to_text import transcribe_audio
from video_processing import process_video
from text_to_voice import text_to_speech
import logging
from termcolor import colored
import keyboard
import os
import pyaudio
import wave
import base64
import time
import tkinter as tk
from tkinter import simpledialog
from PIL import Image, ImageDraw, ImageOps
import pyautogui
import pygame
import threading

def create_directory(directory):
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

def create_default_image(image_path):
    if not os.path.exists(image_path):
        img = Image.new('RGB', (100, 100), color='blue')
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Default Image", fill=(255, 255, 0))
        img.save(image_path)
        print(f"Created default image at {image_path}")

def record_audio(audio_path, key, fs=44100, channels=1):
    print("Press and hold the push-to-talk key to record...")
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=channels, rate=fs, input=True, frames_per_buffer=1024)
    frames = []

    while keyboard.is_pressed(key):
        data = stream.read(1024)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    audio.terminate()

    wf = wave.open(audio_path, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

    print("Recording completed.")

def encode_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def capture_screen(image_path, max_size, quality):
    try:
        # Ensure the directory exists
        directory = os.path.dirname(image_path)
        create_directory(directory)
        print(f"Directory ensured: {directory}")
        
        # Capture the screenshot
        screen = pyautogui.screenshot()
        screen = ImageOps.exif_transpose(screen)  # Correct orientation if needed
        
        # Debugging statements
        print(f"Captured screenshot: {screen.size}")
        
        # Resize the screenshot if max_size is specified
        if max_size:
            screen.thumbnail(max_size, Image.LANCZOS)
            print(f"Resized screenshot to: {screen.size}")
        
        # Save the screenshot
        screen.save(image_path, "JPEG", quality=quality)
        print(f"Screen captured and saved to {image_path}")
    except Exception as e:
        print(f"Error capturing or saving screenshot: {e}")

def get_text_input():
    class TextDialog(simpledialog.Dialog):
        def __init__(self, parent, title=None):
            self.user_input = None
            super().__init__(parent, title=title)

        def body(self, master):
            self.text = tk.Text(master, wrap='word', width=60, height=20)
            self.text.pack(padx=5, pady=5)
            return self.text

        def apply(self):
            self.user_input = self.text.get("1.0", tk.END).strip()

    root = tk.Tk()
    root.withdraw()  # Hide the main window
    dialog = TextDialog(root, title="Input")
    root.destroy()  # Close the tkinter window
    return dialog.user_input

def play_audio(file_path, interrupt_flag):
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if interrupt_flag.is_set():
                pygame.mixer.music.stop()
                break
            time.sleep(0.1)
    finally:
        pygame.mixer.quit()
        try:
            os.remove(file_path)
        except PermissionError:
            pass

def main():
    config = load_config()

    api_key = config["api_key"]
    model = config["model"]
    system_prompt = config["system_prompt"]
    user_name = config["user_name"]
    assistant_name = config["assistant_name"]
    user_color = config["user_color"]
    assistant_color = config["assistant_color"]
    log_file = config["log_file"]
    max_history_length = config["max_history_length"]
    max_response_tokens = config["max_response_tokens"]
    push_to_talk_key = config["push_to_talk_key"]
    image_path = config["image_path"]
    audio_path = config["audio_path"]
    image_max_size = tuple(config["image_max_size"])  # Read and convert to tuple
    image_quality = config["image_quality"]
    tts_model = config["tts_model"]
    tts_voice = config["tts_voice"]
    commands = config["commands"]

    create_directory(os.path.dirname(log_file))
    create_directory(os.path.dirname(image_path))
    create_directory(os.path.dirname(audio_path))

    # Create a default image if the specified image file does not exist
    create_default_image(image_path)

    setup_logging(log_file)
    client = OpenAI(api_key=api_key)

    messages = [{"role": "system", "content": system_prompt}]

    print("Chat session started. Type 'exit' to end the chat.")

    audio_playing = False
    interrupt_flag = threading.Event()

    try:
        while True:
            if keyboard.is_pressed(push_to_talk_key):
                if audio_playing:
                    interrupt_flag.set()
                    audio_playing = False
                    time.sleep(0.5)  # Small delay to ensure the playback stops

                record_audio(audio_path, push_to_talk_key)
                transcribed_text = transcribe_audio(audio_path, client)
                if transcribed_text:
                    print(colored(f"{user_name}: {transcribed_text}", user_color))
                    messages.append({"role": "user", "content": transcribed_text})
                    logging.info(f"{user_name}: Transcribed audio - {transcribed_text}")

                    # Check for commands in the transcribed text
                    for command, keywords in commands.items():
                        if any(keyword in transcribed_text.lower() for keyword in keywords):
                            if command == "image":
                                try:
                                    capture_screen(image_path, image_max_size, image_quality)
                                    base64_image = encode_image(image_path)
                                    messages.append({"role": "user", "content": [
                                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                                    ]})
                                    logging.info(f"{user_name}: Uploaded screen capture from {image_path}")
                                except FileNotFoundError as e:
                                    print(e)
                            elif command == "video":
                                video_path = input("Enter the video file path: ")
                                base64_frames, audio_path = process_video(video_path)
                                transcribed_text = transcribe_audio(audio_path, client)
                                messages.append({"role": "user", "content": [
                                    "These are the frames from the video.",
                                    *map(lambda x: {"type": "image_url", "image_url": {"url": f'data:image/jpg;base64,{x}', "detail": "low"}}, base64_frames),
                                    {"type": "text", "text": f"The audio transcription is: {transcribed_text}"}
                                ]})
                                logging.info(f"{user_name}: Processed video from {video_path}")
                            elif command == "text":
                                user_input = get_text_input()
                                if user_input:
                                    messages.append({"role": "user", "content": user_input})
                                    logging.info(f"{user_name}: {user_input}")

                    messages = trim_history(messages, max_history_length)
                    response = get_chat_response(client, messages, model, max_response_tokens)
                    if response:
                        assistant_response = response.choices[0].message.content
                        print(colored(f"{assistant_name}: {assistant_response}", assistant_color))
                        messages.append({"role": "assistant", "content": assistant_response})
                        logging.info(f"{assistant_name}: {assistant_response}")
                        logging.info(f"Tokens - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")

                        # Convert assistant response to speech and play it
                        audio_output_dir = os.path.join("data", "audio")
                        audio_file_path = text_to_speech(api_key, tts_model, tts_voice, assistant_response, audio_output_dir)
                        interrupt_flag.clear()
                        audio_thread = threading.Thread(target=play_audio, args=(audio_file_path, interrupt_flag))
                        audio_thread.start()

                        audio_playing = True

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Shutting down...")
        interrupt_flag.set()
        if audio_playing:
            audio_thread.join()  # Ensure playback thread completes

if __name__ == "__main__":
    main() 
