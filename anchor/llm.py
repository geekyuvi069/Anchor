import requests
import json
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class LLMClient:
    def __init__(self, model="codellama"):
        self.model = model
        self.api_url = f"{OLLAMA_HOST}/api/generate"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates a response from the local Ollama instance.
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
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to Ollama at {OLLAMA_HOST}. Is it running?") from e
