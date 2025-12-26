# src/audio/speech_to_text.py
"""
Speech-to-Text Module
Converts spoken commands to text using OpenAI Whisper
"""

import whisper
import sounddevice as sd
import numpy as np
import yaml
import tempfile
import os
from scipy.io import wavfile


class SpeechToText:
    """Convert speech to text using Whisper"""
    
    def __init__(self, config_path="config/settings.yaml"):
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.cfg = config.get('speech_to_text', {})
        
        # Configuration
        self.model_size = self.cfg.get('model_size', 'base')  # tiny, base, small, medium, large
        self.language = self.cfg.get('language', 'en')
        self.sample_rate = self.cfg.get('sample_rate', 16000)
        self.record_duration = self.cfg.get('command_duration', 5)
        
        # Load Whisper model
        print(f"Loading Whisper model ({self.model_size})...")
        print("(First time will download the model - might take a minute)")
        
        try:
            self.model = whisper.load_model(self.model_size)
            print(f"✓ Whisper model loaded")
            print(f"  Model: {self.model_size}")
            print(f"  Language: {self.language}")
            print()
        except Exception as e:
            print(f"❌ Error loading Whisper: {e}")
            raise
    
    def record_command(self, duration=None):
        """Record audio command from microphone"""
        duration = duration or self.record_duration
        
        print(f"🎤 Listening for {duration} seconds... Speak now!")
        
        # Record audio
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        
        print("✓ Recording complete")
        
        return audio.flatten()
    
    def transcribe_audio(self, audio):
        """Transcribe audio to text"""
        print("🔄 Transcribing...")
        
        try:
            # Whisper expects audio in specific format
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_path = temp_audio.name
                
                # Convert float32 to int16
                audio_int16 = (audio * 32767).astype(np.int16)
                
                # Save as WAV
                wavfile.write(temp_path, self.sample_rate, audio_int16)
            
            # Transcribe
            result = self.model.transcribe(
                temp_path,
                language=self.language,
                fp16=False  # Use fp32 for better compatibility
            )
            
            # Clean up temp file
            os.unlink(temp_path)
            
            text = result['text'].strip()
            
            if text:
                print(f"✓ Transcription: \"{text}\"")
            else:
                print("⚠️  No speech detected")
            
            return text
        
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return ""
    
    def listen_for_command(self, duration=None):
        """Record and transcribe command in one go"""
        audio = self.record_command(duration)
        text = self.transcribe_audio(audio)
        return text
    
    def test(self):
        """Test the speech-to-text system"""
        print("\n" + "="*60)
        print("SPEECH-TO-TEXT TEST")
        print("="*60)
        print("Say something after the beep...\n")
        
        command = self.listen_for_command()
        
        if command:
            print(f"\n✓ Successfully transcribed: \"{command}\"")
        else:
            print("\n❌ No speech detected or transcription failed")
        
        print("="*60 + "\n")
        
        return command


def main():
    """Test speech-to-text standalone"""
    stt = SpeechToText()
    
    while True:
        print("\nOptions:")
        print("1. Test Speech-to-Text")
        print("2. Exit")
        
        choice = input("\nSelect (1-2): ").strip()
        
        if choice == "1":
            stt.test()
        elif choice == "2":
            print("\nGoodbye!\n")
            break
        else:
            print("\n❌ Invalid option")


if __name__ == "__main__":
    main()