# IConvo/speech_to_text.py

import openai
import logging

def transcribe_audio(audio_path, client):
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcription.text
    except openai.OpenAIError as e:
        logging.error(f"OpenAI API error during transcription: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error during transcription: {str(e)}")
        return None