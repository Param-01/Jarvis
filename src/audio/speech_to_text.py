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
    
    def record_command(self, duration=None, audio_callback=None, event_pump=None):
        """Record audio command from microphone.

        audio_callback(level, freq) — called per chunk with amplitude and dominant freq
        event_pump()               — called per chunk to keep UI alive (e.g. Qt processEvents)
        """
        duration = duration or self.record_duration

        print(f"🎤 Listening for {duration} seconds... Speak now!")

        frames = []

        def _on_audio(indata, frame_count, time_info, status):
            chunk = indata[:, 0].copy()
            frames.append(chunk)

            if audio_callback:
                # Amplitude (RMS, scaled to ~0-1 for normal speech)
                level = float(np.sqrt(np.mean(chunk ** 2))) * 8
                level = min(level, 1.0)

                # Dominant frequency via FFT (voice range 80–1000 Hz)
                fft_mag = np.abs(np.fft.rfft(chunk))
                freqs = np.fft.rfftfreq(len(chunk), 1.0 / self.sample_rate)
                voice_mask = (freqs >= 80) & (freqs <= 1000)
                if voice_mask.any() and fft_mag[voice_mask].max() > 0.001:
                    dominant_freq = float(freqs[voice_mask][np.argmax(fft_mag[voice_mask])])
                else:
                    dominant_freq = 0.0

                audio_callback(level, dominant_freq)

        import time
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=_on_audio,
            blocksize=1024
        ):
            end_time = time.time() + duration
            while time.time() < end_time:
                if event_pump:
                    event_pump()
                time.sleep(0.03)

        print("✓ Recording complete")

        if frames:
            return np.concatenate(frames)
        return np.array([], dtype=np.float32)
    
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
    
    def listen_for_command(self, duration=None, audio_callback=None, event_pump=None):
        """Record and transcribe command in one go"""
        audio = self.record_command(duration, audio_callback=audio_callback, event_pump=event_pump)
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