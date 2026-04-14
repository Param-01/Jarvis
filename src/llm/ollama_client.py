# src/llm/ollama_client.py
"""
Ollama HTTP client for local LLM inference
"""

import json
import yaml
import requests
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent.parent.parent / "config/settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('ollama', {})


class OllamaClient:
    def __init__(self):
        cfg = _load_config()
        self.base_url = cfg.get('base_url', 'http://localhost:11434')
        self.model = cfg.get('model', 'llama3.2')
        self.timeout = cfg.get('timeout', 30)
        self.temperature = cfg.get('temperature', 0.7)

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def chat(self, messages: list, system_prompt: str = None, temperature: float = None) -> str:
        """Send a chat request and return the response string."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature if temperature is not None else self.temperature}
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except requests.exceptions.Timeout:
            return "Sorry, the request timed out. Ollama may be overloaded."
        except Exception as e:
            return f"LLM error: {e}"

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        """Convenience wrapper: single-turn completion."""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, system_prompt=system_prompt)


if __name__ == "__main__":
    client = OllamaClient()
    print(f"Ollama available: {client.is_available()}")
    if client.is_available():
        response = client.complete("Say hello in one sentence.")
        print(f"Response: {response}")
