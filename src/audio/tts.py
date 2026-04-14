# src/audio/tts.py
"""
Text-to-Speech using macOS `say` command
"""

import subprocess
import yaml
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent.parent.parent / "config/settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f).get('tts', {})


class TTS:
    def __init__(self):
        cfg = _load_config()
        self.voice = cfg.get('voice', 'Alex')
        self.rate = cfg.get('rate', 200)
        self.enabled = cfg.get('enabled', True)

    def speak(self, text: str):
        """Speak text synchronously (blocks until done)."""
        if not self.enabled or not text:
            return
        subprocess.run(
            ['say', '-v', self.voice, '-r', str(self.rate), text],
            check=False
        )

    def speak_async(self, text: str):
        """Speak text asynchronously (returns immediately)."""
        if not self.enabled or not text:
            return
        subprocess.Popen(
            ['say', '-v', self.voice, '-r', str(self.rate), text]
        )


if __name__ == "__main__":
    tts = TTS()
    print("Testing TTS...")
    tts.speak("JARVIS online")
    print("TTS test complete.")
