# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python3 main.py

# Test individual modules standalone
python3 src/audio/speech_to_text.py
python3 src/ui/animation.py
```

## Environment

Create a `.env` file in the project root with:
```
wake_word_access_key=<Picovoice Porcupine API key>
```

The Porcupine key is required — startup will raise `ValueError` without it.

## Architecture

JARVIS is a voice-activated personal assistant with a thread-safe activation pipeline:

```
[WakeWordDetector thread] --sets--> threading.Event
         |
[Main thread] --waits on event--> handle_activation()
         |
   VoiceAuth.verify()  -->  SpeechToText.listen_for_command()  -->  process_command()
```

**Key design constraint**: The audio callback in `WakeWordDetector` only sets a `threading.Event` — it never does heavy work. All processing (voice auth, STT, command handling) happens on the main thread after the event is received.

**Modules:**
- `main.py` — `Jarvis` class orchestrates all components; entry point with enrollment/run menu
- `src/audio/wake_word.py` — Porcupine-based wake word detection via continuous `sounddevice` stream
- `src/audio/voice_auth.py` — Speaker verification using SpeechBrain's ECAPA-VOXCELEB model; stores embeddings in `data/voice_profiles/user_profile.pkl`; cosine similarity against enrolled samples
- `src/audio/speech_to_text.py` — OpenAI Whisper transcription; records audio to a temp WAV then transcribes
- `src/ui/animation.py` — PyQt5 transparent overlay with pulsing orb animation; `AnimationController` is thread-safe via pending flags, Qt events must be pumped from main thread via `process_events()`

**Config:** All tuneable parameters live in `config/settings.yaml` (thresholds, model sizes, sample rates, sensitivity). Loaded at module init time.

**Persisted state:**
- Voice profile: `data/voice_profiles/user_profile.pkl` (created on first enrollment)
- Downloaded models: `models/voice_auth/` (SpeechBrain ECAPA model, auto-downloaded on first run)
- Whisper model cached by the `whisper` library (downloaded on first run per model size)
