# main.py
"""
JARVIS Personal Assistant
Integrated: Wake Word + Voice Authentication + Speech-to-Text
"""

from src.audio.voice_auth import VoiceAuth
from src.audio.wake_word import WakeWordDetector
from src.audio.speech_to_text import SpeechToText
from src.ui.animation import AnimationController
import sys
import time
import sounddevice as sd


class Jarvis:
    """Main JARVIS assistant orchestrator"""
    
    def __init__(self):
        print("\n" + "="*60)
        print("JARVIS PERSONAL ASSISTANT")
        print("="*60 + "\n")
        
        # IMPORTANT: Initialize animation controller FIRST on main thread
        self.animation = AnimationController()
        
        # Initialize other components
        print("Initializing components...")
        self.voice_auth = VoiceAuth()
        self.stt = SpeechToText()
        self.wake_word = None
        
        # Check if voice is enrolled
        if not self.voice_auth.enrolled_embeddings:
            print("\n⚠️  Voice not enrolled!")
            print("Please enroll your voice first.\n")
            self.enroll_voice()
    
    def enroll_voice(self):
        """Enroll user's voice"""
        self.voice_auth.enroll()
    
    def on_wake_word_detected(self):
        """Callback when wake word is detected"""
        # Mic is already released by wake word detector
        
        print("\n" + "="*60)
        print("🎤 JARVIS ACTIVATED")
        print("="*60)
        
        # Verify voice
        print("\nVerifying your voice...")
        is_authenticated = self.voice_auth.verify()
        
        if is_authenticated:
            print("\n✓ Authentication successful!")
            print("\nListening for your command...")
            
            # Listen for command
            command = self.stt.listen_for_command()
            
            if command:
                print(f"\n📝 Command received: \"{command}\"")
                self.process_command(command)
            else:
                print("\n⚠️  No command detected")
        else:
            print("\n❌ Voice not recognized. Access denied.")
        
        print("\n" + "="*60)
        print("Restarting wake word detection...\n")
        
        # Create NEW wake word detector instance
        self.wake_word = WakeWordDetector()
        self.wake_word.start(callback=self.on_wake_word_detected)
    
    def process_command(self, command):
        """Process the transcribed command"""
        print("\n" + "-"*60)
        print("PROCESSING COMMAND")
        print("-"*60)
        
        # TODO: Next step - actually execute commands
        # For now, just echo what was said
        print(f"You said: \"{command}\"")
        print("\n(Command execution coming in next update)")
        print("-"*60)
    
    def run_continuous(self):
        """Run JARVIS in continuous listening mode"""
        if not self.voice_auth.enrolled_embeddings:
            print("❌ Please enroll your voice first (option 1 in menu)")
            return
        
        print("\n" + "="*60)
        print("🚀 STARTING CONTINUOUS MODE")
        print("="*60)
        
        # Initialize wake word detector
        self.wake_word = WakeWordDetector()
        
        try:
            # Start listening (will call on_wake_word_detected when activated)
            self.wake_word.start(callback=self.on_wake_word_detected)
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            if self.wake_word:
                self.wake_word.cleanup()


def main():
    """Main entry point with menu"""
    jarvis = Jarvis()
    
    while True:
        print("\n" + "="*60)
        print("JARVIS CONTROL PANEL")
        print("="*60)
        print("1. Enroll Voice (Required for first time)")
        print("2. Test Voice Authentication")
        print("3. Test Wake Word Detection")
        print("4. Test Speech-to-Text")
        print("5. 🚀 Run JARVIS (Full System)")
        print("6. Exit")
        print("="*60)
        
        choice = input("\nSelect (1-6): ").strip()
        
        if choice == "1":
            jarvis.enroll_voice()
        
        elif choice == "2":
            if not jarvis.voice_auth.enrolled_embeddings:
                print("\n❌ Please enroll first (option 1)\n")
            else:
                print("\nTesting voice authentication...")
                jarvis.voice_auth.verify()
        
        elif choice == "3":
            print("\nTesting wake word detection...")
            print("Say 'Jarvis' to test (Ctrl+C to stop)\n")
            detector = WakeWordDetector()
            try:
                detector.start()
            except KeyboardInterrupt:
                print("\n")
            finally:
                detector.cleanup()
        
        elif choice == "4":
            print("\nTesting speech-to-text...")
            jarvis.stt.test()
        
        elif choice == "5":
            # Main continuous mode
            jarvis.run_continuous()
        
        elif choice == "6":
            print("\nGoodbye! 👋\n")
            sys.exit(0)
        
        else:
            print("\n❌ Invalid option\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutdown complete. Goodbye! 👋\n")
        sys.exit(0)