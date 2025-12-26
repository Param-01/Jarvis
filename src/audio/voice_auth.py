"""
Voice Authentication Module
Only recognizes enrolled user's voice
"""

import torch
import sounddevice as sd
import numpy as np
from speechbrain.pretrained import EncoderClassifier
import pickle
from pathlib import Path
import yaml


class VoiceAuth:
    """Simple voice authentication system"""
    
    def __init__(self, config_path="config/settings.yaml"):
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.cfg = config['voice_auth']
        
        # Setup paths
        self.profile_path = Path("data/voice_profiles/user_profile.pkl")
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load model
        print("Loading voice recognition model...")
        self.model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="models/voice_auth"
        )
        
        self.enrolled_embeddings = []
        self.load_profile()
    
    def record(self, duration=None):
        """Record audio from microphone"""
        duration = duration or self.cfg['record_duration']
        sr = self.cfg['sample_rate']
        
        print(f"🎤 Recording for {duration} seconds...")
        audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype='float32')
        sd.wait()
        print("✓ Recording complete")
        
        return audio.flatten()
    
    def get_embedding(self, audio):
        """Extract voice embedding from audio"""
        audio_tensor = torch.tensor(audio).unsqueeze(0)
        with torch.no_grad():
            embedding = self.model.encode_batch(audio_tensor)
        return embedding.squeeze().cpu().numpy()
    
    def enroll(self):
        """Enroll user's voice"""
        num_samples = self.cfg['enrollment_samples']
        print(f"\n{'='*50}")
        print("VOICE ENROLLMENT")
        print(f"{'='*50}")
        print(f"Recording {num_samples} voice samples...")
        print("Tip: Say different phrases each time\n")
        
        embeddings = []
        for i in range(num_samples):
            input(f"Press Enter for sample {i+1}/{num_samples}...")
            audio = self.record()
            embedding = self.get_embedding(audio)
            embeddings.append(embedding)
            print(f"✓ Sample {i+1} processed\n")
        
        self.enrolled_embeddings = embeddings
        self.save_profile()
        
        print("✓ Voice profile saved!")
        print(f"{'='*50}\n")
    
    def verify(self, audio=None):
        """Verify if voice matches enrolled profile"""
        if not self.enrolled_embeddings:
            print("❌ No voice profile found. Run enrollment first.")
            return False
        
        # Record if no audio provided
        if audio is None:
            audio = self.record(duration=3)
        
        # Get embedding
        test_embedding = self.get_embedding(audio)
        
        # Compare with enrolled embeddings
        similarities = [
            np.dot(test_embedding, enrolled) / 
            (np.linalg.norm(test_embedding) * np.linalg.norm(enrolled))
            for enrolled in self.enrolled_embeddings
        ]
        
        max_similarity = np.max(similarities)
        distance = 1 - max_similarity
        
        is_match = distance < self.cfg['threshold']
        
        print(f"\nSimilarity: {max_similarity:.3f} | Threshold: {self.cfg['threshold']}")
        
        if is_match:
            print("✓ AUTHENTICATED - Voice recognized!")
        else:
            print("❌ REJECTED - Voice not recognized!")
        
        return is_match
    
    def save_profile(self):
        """Save voice profile to disk"""
        with open(self.profile_path, 'wb') as f:
            pickle.dump(self.enrolled_embeddings, f)
    
    def load_profile(self):
        """Load voice profile from disk"""
        if self.profile_path.exists():
            with open(self.profile_path, 'rb') as f:
                self.enrolled_embeddings = pickle.load(f)
            print("✓ Voice profile loaded\n")
            return True
        return False