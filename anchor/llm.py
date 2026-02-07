import requests
import json
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class LLMClient:
    def __init__(self, model="codellama"):
        self.model = model
        self.api_url = f"{OLLAMA_HOST}/api/generate"
        self.chat_url = f"{OLLAMA_HOST}/api/chat"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates a response from the local Ollama instance (legacy generate endpoint).
        """
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\nUser Task: {user_prompt}",
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temperature for more deterministic code
                "num_predict": 4096 # Higher limit for full file generation
            }
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            if response.status_code != 200:
                try:
                    error_msg = response.json().get("error", "Unknown error")
                except Exception:
                    error_msg = response.text
                
                hint = ""
                if "memory" in error_msg.lower():
                    hint = "\nHint: Your system may not have enough RAM for this model. Try a smaller model like 'deepseek-coder:1.3b'."
                
                raise RuntimeError(f"Ollama Error: {error_msg}{hint}")

            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to Ollama at {OLLAMA_HOST}. Is it running?") from e

    def chat(self, messages: list) -> str:
        """
        Sends a list of messages to the Ollama chat endpoint and returns the response.
        Messages should be a list of dictionaries with 'role' and 'content'.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7, # Slightly higher for discussion
                "num_predict": 2048
            }
        }

        try:
            response = requests.post(self.chat_url, json=payload)
            if response.status_code != 200:
                try:
                    error_msg = response.json().get("error", "Unknown error")
                except Exception:
                    error_msg = response.text
                
                hint = ""
                if "memory" in error_msg.lower():
                    hint = "\nHint: Your system may not have enough RAM for this model. Try a smaller model like 'deepseek-coder:1.3b'."
                
                raise RuntimeError(f"Ollama Error: {error_msg}{hint}")

            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to Ollama at {OLLAMA_HOST}. Is it running?") from e
