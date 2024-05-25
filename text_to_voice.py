# IConvo/text_to_voice.py
from openai import OpenAI
import os
import re
import time

def text_to_speech(api_key, model, voice, text, output_dir):
    client = OpenAI(api_key=api_key)
    
    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a unique file name using a timestamp
    timestamp = int(time.time() * 1000)
    file_name = f"response_{timestamp}.mp3"
    output_path = os.path.join(output_dir, file_name)
    
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text
    )
    
    with open(output_path, "wb") as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
    
    print(f"Audio saved to {output_path}")
    return output_path

if __name__ == "__main__":
    import yaml
    
    # Load config
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
    
    api_key = config["api_key"]
    tts_model = config["tts_model"]
    tts_voice = config["tts_voice"]
    
    sample_text = "This is a sample text to speech conversion."
    output_dir = os.path.join("data", "audio")
    
    # Convert text to speech
    text_to_speech(api_key, tts_model, tts_voice, sample_text, output_dir)