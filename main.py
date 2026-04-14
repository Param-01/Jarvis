"""
JARVIS Personal Assistant
Thread-safe wake word → activation pipeline
"""

import sys
import threading
import time

from src.audio.voice_auth import VoiceAuth
from src.audio.wake_word import WakeWordDetector
from src.audio.speech_to_text import SpeechToText
from src.audio.tts import TTS
from src.ui.animation import AnimationController
from src.commands.processor import CommandProcessor


class Jarvis:
    def __init__(self):
        print("=" * 60)
        print("JARVIS PERSONAL ASSISTANT")
        print("=" * 60)

        self.animation = AnimationController()
        self.voice_auth = VoiceAuth()
        self.stt = SpeechToText()
        self.tts = TTS()
        self.processor = CommandProcessor()

        self.wake_event = threading.Event()
        self.wake_word = WakeWordDetector(self.wake_event)

        if not self.processor.is_ready():
            print("⚠️  Ollama is not running. Start with: ollama serve")
            print("   Voice commands will return an error until Ollama is available.")

        if not self.voice_auth.enrolled_embeddings:
            print("\n⚠️  No voice profile found. You must enroll first.")
            self.enroll_voice()

    @property
    def is_enrolled(self) -> bool:
        return bool(self.voice_auth.enrolled_embeddings)

    def enroll_voice(self):
        self.voice_auth.enroll()

    def handle_activation(self):
        print("\n🎤 Wake word detected!")

        # Show animation immediately
        self.animation.show(duration_ms=0)
        self.animation.process_events()

        # Verify voice from buffered wake word audio
        wake_audio = self.wake_word.get_wake_audio()
        if wake_audio is None:
            print("❌ No audio captured")
            self.animation.hide()
            self.animation.process_events()
            return

        print("Verifying voice...")
        if not self.voice_auth.verify(audio=wake_audio):
            print("❌ Voice not recognized — ignoring")
            self.animation.hide()
            self.animation.process_events()
            return

        print("✓ Authenticated")
        self.tts.speak_async("Yes?")

        # Listen for command with audio-reactive animation
        def on_audio(level, freq):
            self.animation.set_audio_level(level, freq)

        print("Listening for command...")
        command = self.stt.listen_for_command(
            audio_callback=on_audio,
            event_pump=self.animation.process_events
        )

        if command:
            # Reset audio level while processing
            self.animation.set_audio_level(0.0, 0.0)
            self.animation.process_events()

            response = self.process_command(command)
            print(f"\n💬 {response}")
            self.tts.speak(response)

        self.animation.hide()
        self.animation.process_events()

    def process_command(self, command: str) -> str:
        print(f"\n📝 Command: {command}")
        if not self.processor.is_ready():
            return "Ollama is not running. Please start Ollama first."
        return self.processor.process(command)

    def run_continuous(self):
        print("\n🚀 Starting continuous mode")
        print("Say 'Jarvis' to activate\n")
        self.wake_word.start()

        try:
            while True:
                if self.wake_event.wait(timeout=0.05):
                    self.wake_event.clear()
                    self.handle_activation()
                self.animation.process_events()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.wake_word.cleanup()


def main():
    jarvis = Jarvis()

    while True:
        if not jarvis.is_enrolled:
            print("\n1. Enroll Voice")
            print("2. Exit")
            choice = input("> ").strip()
            if choice == "1":
                jarvis.enroll_voice()
            elif choice == "2":
                sys.exit(0)
            else:
                print("Invalid option")
        else:
            print("\n1. Run JARVIS")
            print("2. Exit")
            choice = input("> ").strip()
            if choice == "1":
                jarvis.run_continuous()
            elif choice == "2":
                sys.exit(0)
            else:
                print("Invalid option")


if __name__ == "__main__":
    main()
