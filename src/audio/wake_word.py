"""
Wake Word Detection Module
Realtime-safe: audio callback only signals an event
Keeps a rolling buffer of recent audio for voice verification
"""

import os
import pvporcupine
import sounddevice as sd
import numpy as np
import yaml
import threading
from collections import deque
from dotenv import load_dotenv


class WakeWordDetector:
    """Detects wake word in audio stream and buffers audio for voice auth"""

    AVAILABLE_KEYWORDS = [
        "alexa", "americano", "blueberry", "bumblebee", "computer",
        "grapefruit", "grasshopper", "hey google", "hey siri",
        "jarvis", "ok google", "picovoice", "porcupine", "terminator"
    ]

    # Buffer ~3 seconds of audio for voice verification
    BUFFER_SECONDS = 3

    def __init__(self, wake_event: threading.Event, config_path="config/settings.yaml"):
        load_dotenv()
        self.wake_event = wake_event

        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)["wake_word"]

        self.keyword = cfg["keyword"].lower()
        self.sensitivity = cfg["sensitivity"]
        self.access_key = os.getenv("wake_word_access_key", "").strip()

        if not self.access_key:
            raise ValueError("Missing Porcupine access key")

        if self.keyword not in self.AVAILABLE_KEYWORDS:
            self.keyword = "jarvis"

        self.porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=[self.keyword],
            sensitivities=[self.sensitivity],
        )

        # Rolling audio buffer (stores float32 frames)
        # Each callback delivers porcupine.frame_length samples
        num_frames_to_buffer = int(
            self.BUFFER_SECONDS * self.porcupine.sample_rate / self.porcupine.frame_length
        )
        self._audio_buffer = deque(maxlen=num_frames_to_buffer)
        self._buffer_lock = threading.Lock()
        self._wake_audio = None  # snapshot taken when wake word fires

        self.audio_stream = None
        self.running = False

        print(f"✓ Wake word detector ready ({self.keyword})")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            return  # never print from audio thread

        raw = indata[:, 0].copy()  # float32 copy

        # Store in rolling buffer
        with self._buffer_lock:
            self._audio_buffer.append(raw)

        # Feed int16 to Porcupine
        pcm = (raw * 32767).astype(np.int16)
        result = self.porcupine.process(pcm)

        if result >= 0:
            # Snapshot the buffer for voice auth
            with self._buffer_lock:
                self._wake_audio = np.concatenate(list(self._audio_buffer))
            self.wake_event.set()  # SIGNAL ONLY

    def get_wake_audio(self) -> np.ndarray | None:
        """Return the audio captured around the wake word trigger.
        Call this from the main thread after wake_event is set."""
        audio = self._wake_audio
        self._wake_audio = None
        return audio

    def start(self):
        if self.running:
            return

        self.running = True

        self.audio_stream = sd.InputStream(
            channels=1,
            samplerate=self.porcupine.sample_rate,
            blocksize=self.porcupine.frame_length,
            dtype=np.float32,
            callback=self._audio_callback,
        )

        self.audio_stream.start()
        print(f"🎧 Listening for wake word: {self.keyword.upper()}")

    def stop(self):
        self.running = False
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

    def cleanup(self):
        self.stop()
        self.porcupine.delete()
