# IConvo/interface.py

import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, BooleanVar, StringVar, filedialog
import yaml
import openai
from chat_function import get_chat_response, trim_history
from main import capture_screen, encode_image
from speech_to_text import transcribe_audio
from text_to_voice import text_to_speech
from video_processing import process_video
import threading
import pyaudio
import wave
import numpy as np
import re
import audioop
import keyboard
import os
import time
import queue
import nltk
import pygame
import shutil
import atexit
from datetime import datetime
from pygments import lex
from pygments.lexers import YamlLexer
from pygments.token import Token
nltk.download('punkt')

# Function to get the current timestamp
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Function to play audio and handle interruptions
def play_audio(file_path, interrupt_flag):
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print(f"{get_timestamp()} - Playing audio file: {file_path}")  # Debug print
        while pygame.mixer.music.get_busy():
            if interrupt_flag.is_set():
                pygame.mixer.music.stop()
                print(f"{get_timestamp()} - Playback interrupted: {file_path}")  # Debug print
                break
            time.sleep(0.1)
    except pygame.error as e:
        print(f"{get_timestamp()} - Error loading audio file: {e}")
    finally:
        pygame.mixer.quit()

def is_audio_file_too_short(file_path, min_duration=0.75):
    try:
        with wave.open(file_path, 'r') as audio_file:
            frames = audio_file.getnframes()
            rate = audio_file.getframerate()
            duration = frames / float(rate)
            return duration < min_duration
    except Exception as e:
        print(f"{get_timestamp()} - Error checking audio file duration: {e}")
        return True

# Create a custom logging filter to ignore specific messages
class IgnoreHttpRequestsFilter(logging.Filter):
    def filter(self, record):
        return "POST https://api.openai.com/v1/" not in record.getMessage()

# Suppress HTTP request logging at the logger level
logging.getLogger("http.client").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

LIGHT_MODE = {
    "bg": "white",
    "fg": "black",
    "input_bg": "white",
    "input_fg": "black",
    "output_bg": "white",
    "output_fg": "black",
}

DARK_MODE = {
    "bg": "#2b2b2b",
    "fg": "black",
    "input_bg": "#212121",
    "input_fg": "black",
    "output_bg": "#212121",
    "output_fg": "white",
}

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IConvo")
        self.geometry("800x600")
        self.config = self.load_config()
        self.audio_queue = queue.Queue()
        self.recording = False
        self.audio_playing = False
        self.interrupt_flag = threading.Event()
        self.audio_thread = None
        self.current_audio_file = None
        self.temp_audio_file = None
        self.messages = [{"role": "system", "content": self.config["system_prompt"]}]

        self.colors = LIGHT_MODE
        self.create_widgets()
        self.configure_theme()
        self.setup_logging()
        self.setup_keyboard_listener()
        self.create_temp_folder()
        self.clean_temp_folder()
        # Register the cleanup method to be called on exit
        atexit.register(self.cleanup_on_exit)

    def create_temp_folder(self):
        self.temp_folder = os.path.join("data", "temp")
        os.makedirs(self.temp_folder, exist_ok=True)
        print(f"{get_timestamp()} - Temporary folder created: {self.temp_folder}")

    def clean_temp_folder(self):
        for filename in os.listdir(self.temp_folder):
            file_path = os.path.join(self.temp_folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"{get_timestamp()} - Deleted file: {file_path}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"{get_timestamp()} - Deleted directory: {file_path}")
            except Exception as e:
                print(f"{get_timestamp()} - Failed to delete {file_path}. Reason: {e}")

    def cleanup_on_exit(self):
        print(f"{get_timestamp()} - Cleaning up before exit...")
        self.clean_temp_folder()
        print(f"{get_timestamp()} - Cleanup completed.")

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True)
        self.theme_var = tk.BooleanVar(value=False)
        self.light_bulb_icon = tk.PhotoImage(file="light_bulb.png")
        self.dark_bulb_icon = tk.PhotoImage(file="dark_bulb.png")
        self.theme_button = tk.Button(self, image=self.light_bulb_icon, bd=0, highlightthickness=0, command=self.toggle_theme)
        self.theme_button.place(relx=1.0, rely=0.0, anchor='ne')
        self.create_console_tab()
        self.create_config_tab()
        self.create_about_tab()
        # Add Save Audio button
        self.save_audio_button = ttk.Button(self.input_frame, text="Save Audio", command=self.save_last_audio)
        self.save_audio_button.pack(side='right', padx=5, pady=5)

    def toggle_theme(self):
        self.theme_var.set(not self.theme_var.get())
        if self.theme_var.get():
            self.colors = DARK_MODE
        else:
            self.colors = LIGHT_MODE
        self.configure_theme()

    def configure_theme(self):
        style = ttk.Style()
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TButton", background=self.colors["bg"], foreground=self.colors["fg"])
        style.configure("TEntry", fieldbackground=self.colors["input_bg"], foreground=self.colors["input_fg"])
        style.configure("TNotebook", background=self.colors["bg"])
        style.configure("TNotebook.Tab", background=self.colors["bg"], foreground=self.colors["fg"])
        self.configure(bg=self.colors["bg"])
        self.console_output.configure(bg=self.colors["output_bg"], fg=self.colors["output_fg"])
        self.input_frame.configure(style="TFrame")
        self.theme_button.configure(image=self.dark_bulb_icon if self.theme_var.get() else self.light_bulb_icon)

    def create_console_tab(self):
        console_frame = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(console_frame, text="Console")

        self.console_output = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, state='disabled', bg=self.colors["output_bg"], fg=self.colors["output_fg"])
        self.console_output.pack(fill='both', expand=True, padx=5, pady=5)

        self.input_frame = ttk.Frame(console_frame, style="TFrame")
        self.input_frame.pack(fill='x', padx=5, pady=5)

        self.toggle_button_var = BooleanVar(value=False)
        self.toggle_button = tk.Button(self.input_frame, text="●", bg="green", command=self.toggle_recording)
        self.toggle_button.pack(side='left', padx=5, pady=5)

        self.input_box = ttk.Entry(self.input_frame, style="TEntry")
        self.input_box.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.input_box.bind("<Return>", self.on_enter)

        self.send_button = ttk.Button(self.input_frame, text="Send", style="TButton", command=self.on_enter)
        self.send_button.pack(side='right', padx=5, pady=5)

    def create_config_tab(self):
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Configuration")

        # Create a custom text editor widget
        self.config_text = scrolledtext.ScrolledText(config_frame, wrap=tk.NONE, font=("Courier New", 10), bg="lightgray")
        self.config_text.pack(fill=tk.BOTH, expand=True)

        # Load the configuration into the text editor
        with open('config.yaml', 'r', encoding='utf-8') as file:
            config_data = file.read()
            self.config_text.insert(tk.END, config_data)

        # Apply syntax highlighting
        self.highlight_syntax()

        # Configure tags for syntax highlighting
        self.config_text.tag_configure("Token.Keyword", foreground="blue")
        self.config_text.tag_configure("Token.Literal.Scalar", foreground="black")
        self.config_text.tag_configure("Token.Literal.String", foreground="green")
        self.config_text.tag_configure("Token.Literal.Number", foreground="purple")
        self.config_text.tag_configure("Token.Comment", foreground="gray")

        self.save_button = ttk.Button(config_frame, text="Save Config", command=self.save_config)
        self.save_button.pack(padx=5, pady=5)

    def highlight_syntax(self):
        self.config_text.mark_set("range_start", "1.0")
        data = self.config_text.get("1.0", "end-1c")
        for token, content in lex(data, YamlLexer()):
            self.config_text.mark_set("range_end", "range_start + {}c".format(len(content)))
            self.config_text.tag_add(str(token), "range_start", "range_end")
            self.config_text.mark_set("range_start", "range_end")

    def save_config(self):
        # Get the modified configuration data from the text editor
        config_data = self.config_text.get("1.0", "end-1c")

        # Save the modified configuration data to the config.yaml file
        with open('config.yaml', 'w', encoding='utf-8') as file:
            file.write(config_data)

        messagebox.showinfo("Info", "Configuration saved successfully.")

    def create_about_tab(self):
        about_frame = ttk.Frame(self.notebook)
        self.notebook.add(about_frame, text="About")

        about_text = "IConvo v1 - An Interactive Conversational AI Application\n\n" \
                    "This application is currently in an experimental stage.\n\n" \
                    "Author: Legend of Ray\n"

        discord_link = "Discord Server"
        discord_url = "https://discord.gg/FPN7vx4eVY"

        self.about_label = ttk.Label(about_frame, text=about_text, justify=tk.LEFT)
        self.about_label.pack(padx=10, pady=10)
        discord_label = ttk.Label(about_frame, text=discord_link, foreground="blue", cursor="hand2")
        discord_label.pack(padx=10)
        discord_label.bind("<Button-1>", lambda e: self.open_url(discord_url))

    def open_url(self, url):
        import webbrowser
        webbrowser.open_new(url)

    def setup_logging(self):
        log_file = self.config["log_file"]  # Get the log file path from the config

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Create a file handler for logging to a file
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def write(self, message, color="black"):
        self.console_output.config(state='normal')
        self.console_output.insert(tk.END, message + '\n', color)
        self.console_output.tag_configure(color, foreground=color)
        self.console_output.config(state='disabled')
        self.console_output.see(tk.END)

    def on_enter(self, event=None):
        user_input = self.input_box.get()
        if user_input:
            self.input_box.delete(0, tk.END)
            self.process_input(user_input)

    def process_input(self, user_input):
        if self.audio_playing:
            self.interrupt_flag.set()
            self.audio_playing = False
            if self.audio_thread is not None:
                self.audio_thread.join(timeout=1.0)
                self.clear_current_audio_file()  # Clear only the current audio file
                time.sleep(0.5)  # Introduce a short delay to ensure the interruption is handled
        self.write(f"{self.config['user_name']}: {user_input}", self.config['user_color'])
        self.logger.info(f"{self.config['user_name']}: {user_input}")  # Log user input

        client = openai.OpenAI(api_key=self.config["api_key"])

        self.messages.append({"role": "user", "content": user_input})

        model = self.config["model"]
        max_response_tokens = int(self.config["max_response_tokens"])

        self.messages = trim_history(self.messages, int(self.config["max_history_length"]))

        def process_response():
            response = get_chat_response(client, self.messages, model, max_response_tokens)
            
            if response:
                assistant_response = response.choices[0].message.content
                self.after(0, self.write, f"{self.config['assistant_name']}: {assistant_response}", self.config['assistant_color'])
                self.logger.info(f"{self.config['assistant_name']}: {assistant_response}")  # Log assistant response
                self.messages.append({"role": "assistant", "content": assistant_response})

                audio_output_dir = os.path.join("data", "audio")
                
                start_time = time.time()  # Start the timer
                audio_file_path = text_to_speech(self.config["api_key"], self.config["tts_model"], self.config["tts_voice"], assistant_response, audio_output_dir)
                tts_time = time.time() - start_time  # Calculate the text-to-speech time
                print(f"{get_timestamp()} - Text-to-speech time: {tts_time:.2f} seconds")
                print(f"{get_timestamp()} - Audio saved to {audio_file_path}")  # Debug print

                self.after(0, self.play_and_delete_audio, audio_file_path)

        # Run the response processing on a separate thread
        threading.Thread(target=process_response).start()

    def play_and_delete_audio(self, file_path):
        self.audio_playing = True
        self.current_audio_file = file_path
        self.temp_audio_file = os.path.join(self.temp_folder, os.path.basename(file_path))
        shutil.copy2(file_path, self.temp_audio_file)
        self.interrupt_flag.clear()

        def audio_player():
            try:
                play_audio(file_path, self.interrupt_flag)
                print(f"{get_timestamp()} - Completed playing audio file: {file_path}")
            finally:
                self.audio_playing = False
                time.sleep(0.5)
                self.clear_current_audio_file()

        self.audio_thread = threading.Thread(target=audio_player)
        self.audio_thread.start()

    def clear_current_audio_file(self):
        if self.current_audio_file and os.path.isfile(self.current_audio_file):
            try:
                os.remove(self.current_audio_file)
                print(f"{get_timestamp()} - Deleted audio file: {self.current_audio_file}")
            except Exception as e:
                print(f"{get_timestamp()} - Failed to delete {self.current_audio_file}. Reason: {e}")
            finally:
                self.current_audio_file = None

    def save_last_audio(self):
        if self.temp_audio_file and os.path.isfile(self.temp_audio_file):
            save_path = filedialog.asksaveasfilename(
                defaultextension=".mp3",
                filetypes=[("MP3 files", "*.mp3")],
                title="Save Last Audio Response"
            )
            if save_path:
                shutil.copy2(self.temp_audio_file, save_path)
                messagebox.showinfo("Success", f"Audio saved to {save_path}")
        else:
            messagebox.showwarning("Warning", "No audio file available to save.")

    def clear_audio_directory(self):
        audio_output_dir = os.path.join("data", "audio")
        for filename in os.listdir(audio_output_dir):
            file_path = os.path.join(audio_output_dir, filename)
            if file_path != self.current_audio_file:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"{get_timestamp()} - Deleted audio file: {file_path}")
                except Exception as e:
                    print(f"{get_timestamp()} - Failed to delete {file_path}. Reason: {e}")
        
        # Clear temp folder except for the most recent file
        temp_files = os.listdir(self.temp_folder)
        if temp_files:
            most_recent = max(temp_files, key=lambda f: os.path.getmtime(os.path.join(self.temp_folder, f)))
            for filename in temp_files:
                if filename != most_recent:
                    file_path = os.path.join(self.temp_folder, filename)
                    try:
                        os.remove(file_path)
                        print(f"{get_timestamp()} - Deleted temp audio file: {file_path}")
                    except Exception as e:
                        print(f"{get_timestamp()} - Failed to delete {file_path}. Reason: {e}")

    def get_text_input(self):
        text_window = tk.Toplevel(self)
        text_window.title("Enter Text")
        text_window.geometry("600x600")

        text_frame = ttk.Frame(text_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_box = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        text_box.pack(fill=tk.BOTH, expand=True)

        result = None  # Initialize the result variable

        def confirm_text():
            nonlocal result  # Use nonlocal to access the result variable
            result = text_box.get("1.0", tk.END).strip()
            text_window.destroy()

        confirm_button = ttk.Button(text_window, text="Confirm", command=confirm_text)
        confirm_button.pack(pady=10)

        self.wait_window(text_window)
        return result

    def handle_commands(self, text):
        for command, keywords in self.config["commands"].items():
            if any(str(keyword).lower() in text.lower() for keyword in keywords):
                if command == "image":
                    try:
                        print(f"{get_timestamp()} - Executing image capture command...")
                        capture_screen(self.config["image_path"], self.config["image_max_size"], int(self.config["image_quality"]))
                        base64_image = encode_image(self.config["image_path"])
                        self.write(f"Image captured and saved to {self.config['image_path']}")
                        self.messages.append({"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]})
                        self.process_input("")  # Trigger response processing with an empty input
                        return True  # Command found and processed
                    except Exception as e:
                        print(f"{get_timestamp()} - Error capturing or encoding image: {e}")
                        self.write(f"Error capturing or encoding image: {e}")
                elif command == "video":
                    video_path = input("Enter the video file path: ")
                    base64_frames, audio_path = process_video(video_path)
                    transcribed_text = transcribe_audio(audio_path, openai.OpenAI(api_key=self.config["api_key"]))
                    self.write("These are the frames from the video.")
                    for frame in base64_frames:
                        self.write(f'<img src="data:image/jpg;base64,{frame}" style="detail: low" />')
                    self.write(f"The audio transcription is: {transcribed_text}")
                    return True  # Command found and processed
                elif command == "text":
                    additional_text = self.get_text_input()
                    if additional_text:
                        combined_text = text + "\n" + additional_text
                        self.write(f"{self.config['user_name']}: {combined_text}", self.config['user_color'])
                        self.messages.append({"role": "user", "content": combined_text})
                        self.process_input("")  # Trigger response processing with an empty input
                    return True  # Command found and processed

    def toggle_recording(self):
        self.recording = not self.recording
        self.toggle_button.config(bg="red" if self.recording else "green")
        if self.recording:
            self.start_listening()
        else:
            self.interrupt_flag.set()
            self.clear_audio_directory()

    def start_listening(self):
        self.interrupt_flag.clear()
        threading.Thread(target=self.listen_for_audio).start()

    def listen_for_audio(self):
        audio_path = self.config["audio_path"]
        fs = 44100
        channels = 1
        threshold = 500  # Adjust threshold as needed
        min_silence_duration = 2  # Minimum duration of silence before stopping the recording
        min_recording_duration = 3  # Minimum recording duration in seconds

        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=channels, rate=fs, input=True, frames_per_buffer=1024)

        recording_frames = []
        recording = False
        silence_counter = 0
        recording_start_time = None

        while self.recording:
            data = stream.read(1024)
            rms = audioop.rms(data, 2)

            if rms > threshold:
                if not recording:
                    recording_start_time = time.time()
                    recording = True

                recording_frames.append(data)
                silence_counter = 0
            elif recording:
                silence_counter += 1
                current_recording_duration = time.time() - recording_start_time
                if silence_counter > (fs / 1024 * min_silence_duration) or (current_recording_duration >= min_recording_duration and current_recording_duration < min_recording_duration):
                    recording = False

                    wf = wave.open(audio_path, 'wb')
                    wf.setnchannels(channels)
                    wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(fs)
                    wf.writeframes(b''.join(recording_frames))
                    wf.close()
                    print(f"{get_timestamp()} - Audio saved to {audio_path}")  # Debug print

                    if current_recording_duration >= min_recording_duration and not is_audio_file_too_short(audio_path):
                        self.after(0, self.process_transcription, audio_path)

                    recording_frames = []

        stream.stop_stream()
        stream.close()
        audio.terminate()

    def process_transcription(self, audio_path):
        transcribed_text = transcribe_audio(audio_path, openai.OpenAI(api_key=self.config["api_key"]))
        if transcribed_text and self.is_valid_transcription(transcribed_text):
            if self.audio_playing:
                self.interrupt_flag.set()
                self.audio_playing = False
                if self.audio_thread is not None:
                    self.audio_thread.join()
                    self.clear_current_audio_file()  # Clear only the current audio file
                    time.sleep(0.5)  # Introduce a short delay to ensure the interruption is handled
            if self.handle_commands(transcribed_text):
                return  # Exit the method if a command is found and processed
            self.process_input(transcribed_text)

    def is_valid_transcription(self, text):
        if len(text.strip()) < 3:
            return False
        if re.match(r'^[^a-zA-Z0-9]*$', text):
            return False
        return True             

    def setup_keyboard_listener(self):
        push_to_talk_key = self.config["push_to_talk_key"]

        def on_press(event):
            if event.name == push_to_talk_key:
                self.toggle_recording()

        keyboard.on_press(on_press)

    def load_config(self):
        with open('config.yaml', 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            
            # Convert image_max_size to a tuple of integers
            config['image_max_size'] = tuple(map(int, config['image_max_size'].strip('()').split(',')))
            
            return config

    def save_config(self):
        # Get the modified configuration data from the text editor
        config_data = self.config_text.get("1.0", "end-1c")

        # Save the modified configuration data to the config.yaml file
        with open('config.yaml', 'w', encoding='utf-8') as file:
            file.write(config_data)

        messagebox.showinfo("Info", "Configuration saved successfully.")

if __name__ == "__main__":
    app = Application()
    app.mainloop()
