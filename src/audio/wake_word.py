# src/audio/wake_word.py
"""
Wake Word Detection Module
Continuously listens for wake word (e.g., "Hey Jarvis")
Uses Porcupine for efficient, always-on detection
"""

import os
import pvporcupine
import sounddevice as sd
import numpy as np
import yaml
from pathlib import Path
from dotenv import load_dotenv


class WakeWordDetector:
    """Detects wake word in audio stream"""
    
    # Available built-in keywords in Porcupine
    AVAILABLE_KEYWORDS = [
        "alexa",
        "americano",
        "blueberry",
        "bumblebee",
        "computer",
        "grapefruit",
        "grasshopper",
        "hey google",
        "hey siri",
        "jarvis",
        "ok google",
        "picovoice",
        "porcupine",
        "terminator"
    ]
    
    def __init__(self, config_path="config/settings.yaml"):

        load_dotenv()

        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.cfg = config['wake_word']
        
        self.keyword = self.cfg['keyword'].lower()
        self.sensitivity = self.cfg['sensitivity']
        self.access_key = os.getenv('wake_word_access_key', '').strip()
        
        # Check for access key
        if not self.access_key:
            print("\n❌ Porcupine access key required!")
            print("1. Go to https://console.picovoice.ai/")
            print("2. Sign up (free)")
            print("3. Copy your access key")
            print("4. Add it to config/settings.yaml under wake_word.access_key")
            raise ValueError("Missing Porcupine access key")
        
        # Validate keyword
        if self.keyword not in self.AVAILABLE_KEYWORDS:
            print(f"⚠️  '{self.keyword}' not available. Using 'jarvis' instead.")
            print(f"Available keywords: {', '.join(self.AVAILABLE_KEYWORDS)}")
            self.keyword = "jarvis"
        
        # Initialize Porcupine
        print(f"Initializing wake word detector for '{self.keyword}'...")
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=[self.keyword],
                sensitivities=[self.sensitivity]
            )
            print(f"✓ Wake word detector ready")
            print(f"  Keyword: '{self.keyword}'")
            print(f"  Sensitivity: {self.sensitivity}")
            print(f"  Sample rate: {self.porcupine.sample_rate} Hz")
            print(f"  Frame length: {self.porcupine.frame_length}\n")
        except Exception as e:
            print(f"❌ Error initializing Porcupine: {e}")
            raise
        
        self.is_listening = False
        self.audio_stream = None
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio stream - processes each audio frame"""
        if status:
            print(f"Audio callback status: {status}")
        
        # Convert audio to int16 (Porcupine expects this format)
        audio_frame = (indata[:, 0] * 32767).astype(np.int16)
        
        # Check if wake word is detected
        keyword_index = self.porcupine.process(audio_frame)
        
        if keyword_index >= 0:
            # Wake word detected!
            print(f"\n🎤 Wake word '{self.keyword}' detected!")
            # You can trigger a callback here in the future
            if hasattr(self, 'on_wake_word_detected'):
                self.on_wake_word_detected()
    
    def start(self, callback=None):
        """Start listening for wake word"""
        if self.is_listening:
            print("Already listening...")
            return
        
        # Store callback if provided
        if callback:
            self.on_wake_word_detected = callback
        
        print(f"\n{'='*50}")
        print(f"🎧 LISTENING FOR WAKE WORD: '{self.keyword.upper()}'")
        print(f"{'='*50}")
        print("Say the wake word to activate...")
        print("Press Ctrl+C to stop\n")
        
        self.is_listening = True
        
        try:
            # Open audio stream
            self.audio_stream = sd.InputStream(
                channels=1,
                samplerate=self.porcupine.sample_rate,
                blocksize=self.porcupine.frame_length,
                dtype=np.float32,
                callback=self._audio_callback
            )
            
            with self.audio_stream:
                # Keep stream open until interrupted
                while self.is_listening:
                    sd.sleep(100)  # Sleep in small intervals
        
        except KeyboardInterrupt:
            print("\n\n✓ Stopped listening")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop listening"""
        self.is_listening = False
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        if self.porcupine:
            self.porcupine.delete()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()


def test_wake_word():
    """Test the wake word detector standalone"""
    detector = WakeWordDetector()
    
    def on_detected():
        print("✓ Wake word callback triggered!")
        print("(In real app, this would activate voice auth)\n")
    
    try:
        detector.start(callback=on_detected)
    finally:
        detector.cleanup()


if __name__ == "__main__":
    test_wake_word()