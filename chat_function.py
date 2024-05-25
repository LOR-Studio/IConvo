# IConvo/chat_function.py

import openai
import yaml
import os
import logging

def configure_openai(api_key):
    return openai.OpenAI(api_key=api_key)

def get_chat_response(client, messages, model, max_response_tokens):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_response_tokens
        )
        return response
    except openai.error.InvalidRequestError as e:
        logging.error(f"Invalid request: {e}")
        return None
    except openai.error.AuthenticationError as e:
        logging.error(f"Authentication error: {e}")
        return None
    except openai.error.RateLimitError as e:
        logging.error(f"Rate limit exceeded: {e}")
        return None
    except openai.error.APIConnectionError as e:
        logging.error(f"API connection error: {e}")
        return None
    except openai.error.APIError as e:
        logging.error(f"API error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None

def load_config(config_file="config.yaml"):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"The configuration file '{config_file}' does not exist.")
    with open(config_file, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config

def setup_logging(log_file):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def trim_history(messages, max_length):
    if len(messages) > max_length:
        messages = messages[:1] + messages[-(max_length-1):]
    return messages

def get_num_tokens(text):
    # Rough estimate of the number of tokens in a text string
    words = text.split()
    return len(words)