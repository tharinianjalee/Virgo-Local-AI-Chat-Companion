# voice.py
# voice.py
import os
import re
import wave
import tempfile
from pydub import AudioSegment

from config import (
    VOICE_MODEL_PATH,
    WHISPER_MODEL_SIZE,
    XTTS_ENABLED,
    XTTS_REFERENCE_DIR,
    XTTS_LANGUAGE,
)


# ─────────────────────────────────────────────────────────────
# Emoji / markdown cleaner
# ─────────────────────────────────────────────────────────────
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "\U0001F1E0-\U0001F1FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U000024C2-\U0001F251"
    "\U0001F000-\U0001F02F"
    "\U0001F0A0-\U0001F0FF"
    "]+",
    flags=re.UNICODE,
)

THOUGHT_PATTERN = re.compile(
    r"[\[\(]?\s*(?:internal\s+thought|thinking|thought)\s*[:\-]\s*[^\]\)]+?[\]\)]?",
    re.IGNORECASE,
)


def clean_text_for_tts(text: str) -> str:
    """Strip emojis, action tags, thoughts, markdown, and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"\[ACTION:\s*\w+\]\s*", "", text)
    text = THOUGHT_PATTERN.sub("", text)
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r"[*_`~#>]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────────────────────────────────────────
# Tone → XTTS reference clip
# ─────────────────────────────────────────────────────────────
def _xtts_ref(tone: str) -> str:
    """Return path to the reference clip for a tone, with fallbacks."""
    candidates = [
        f"virgo_{tone}.wav",
        f"virgo_{tone}.mp3",
        "virgo_neutral.wav",
        "virgo_reference.wav",
    ]
    for name in candidates:
        path = os.path.join(XTTS_REFERENCE_DIR, name)
        if os.path.exists(path):
            return path
    return ""


# ─────────────────────────────────────────────────────────────
# XTTS Engine
# ─────────────────────────────────────────────────────────────
class XTTSEngine:
    """Coqui XTTS v2 wrapper with per-tone reference clips."""

    def __init__(self):
        self.tts = None
        if not XTTS_ENABLED:
            print("[INFO] XTTS disabled in config")
            return
        try:
            from TTS.api import TTS
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[INFO] Loading XTTS v2 on {device} … (first run downloads ~1.8 GB)")

            self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            print("[OK] XTTS v2 loaded")
        except Exception as e:
            print(f"[WARN] XTTS unavailable: {e}")
            self.tts = None

    def is_ready(self) -> bool:
        return self.tts is not None

    def synthesize_segment(self, text: str, tone: str) -> str | None:
        """Synthesize one segment with the tone-appropriate reference. Returns WAV path."""
        if not self.is_ready() or not text.strip():
            return None

        ref = _xtts_ref(tone)
        if not ref:
            print(f"[WARN] No reference clip found for tone '{tone}' — using default")
            # Try to fall back to any voice in the folder
            for f in os.listdir(XTTS_REFERENCE_DIR):
                if f.lower().endswith((".wav", ".mp3")):
                    ref = os.path.join(XTTS_REFERENCE_DIR, f)
                    break
            if not ref:
                return None

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False,
                                          dir=tempfile.gettempdir())
        tmp.close()

        try:
            self.tts.tts_to_file(
                text=text,
                file_path=tmp.name,
                speaker_wav=ref,
                language=XTTS_LANGUAGE,
            )
            if os.path.getsize(tmp.name) < 1000:
                os.remove(tmp.name)
                return None
            return tmp.name
        except Exception as e:
            print(f"[WARN] XTTS synthesis failed: {e}")
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            return None


# ─────────────────────────────────────────────────────────────
# Piper Engine (fallback)
# ─────────────────────────────────────────────────────────────
TONE_PROFILES = {
    "neutral":   {"length_scale": 1.00, "noise_scale": 0.667, "noise_w": 0.80, "volume_db": 0},
    "warm":      {"length_scale": 1.00, "noise_scale": 0.65,  "noise_w": 0.80, "volume_db": -1},
    "happy":     {"length_scale": 0.95, "noise_scale": 0.75,  "noise_w": 0.95, "volume_db": 1},
    "excited":   {"length_scale": 0.92, "noise_scale": 0.85,  "noise_w": 1.00, "volume_db": 2},
    "playful":   {"length_scale": 0.95, "noise_scale": 0.80,  "noise_w": 0.95, "volume_db": 0},
    "tender":    {"length_scale": 1.10, "noise_scale": 0.60,  "noise_w": 0.75, "volume_db": -3},
    "murmur":    {"length_scale": 1.20, "noise_scale": 0.55,  "noise_w": 0.60, "volume_db": -10},
    "whisper":   {"length_scale": 1.30, "noise_scale": 0.45,  "noise_w": 0.50, "volume_db": -15},
    "shy":       {"length_scale": 1.15, "noise_scale": 0.60,  "noise_w": 0.70, "volume_db": -6},
    "seductive": {"length_scale": 1.20, "noise_scale": 0.55,  "noise_w": 0.65, "volume_db": -8},
    "sad":       {"length_scale": 1.25, "noise_scale": 0.50,  "noise_w": 0.60, "volume_db": -5},
    "serious":   {"length_scale": 1.05, "noise_scale": 0.55,  "noise_w": 0.70, "volume_db": 0},
    "laugh":     {"length_scale": 0.95, "noise_scale": 0.90,  "noise_w": 1.00, "volume_db": 0},
    "sigh":      {"length_scale": 1.35, "noise_scale": 0.40,  "noise_w": 0.50, "volume_db": -4},
    "shout":     {"length_scale": 0.88, "noise_scale": 0.90,  "noise_w": 1.05, "volume_db": 5},
}


class PiperEngine:
    """Piper-based fallback synthesis engine."""

    def __init__(self, model_path=VOICE_MODEL_PATH):
        self.voice = None
        if not os.path.exists(model_path):
            print(f"[WARN] Piper model not found: {model_path}")
            return
        try:
            from piper import PiperVoice
            self.voice = PiperVoice.load(model_path, config_path=model_path + ".json")
            print(f"[OK] Piper loaded: {model_path}")
        except Exception as e:
            print(f"[WARN] Failed to load Piper: {e}")
            self.voice = None

    def is_ready(self) -> bool:
        return self.voice is not None

    def synthesize_segment(self, text: str, tone: str) -> str | None:
        if not self.is_ready() or not text.strip():
            return None

        from piper import SynthesisConfig
        profile = TONE_PROFILES.get(tone, TONE_PROFILES["neutral"])
        cfg = SynthesisConfig(
            length_scale=profile["length_scale"],
            noise_scale=profile["noise_scale"],
            noise_w_scale=profile["noise_w"],
        )

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False,
                                          dir=tempfile.gettempdir())
        tmp.close()

        try:
            with wave.open(tmp.name, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file, syn_config=cfg)
            if os.path.getsize(tmp.name) < 1000:
                os.remove(tmp.name)
                return None
            # Apply volume via pydub
            seg_audio = AudioSegment.from_wav(tmp.name).apply_gain(profile["volume_db"])
            seg_audio.export(tmp.name, format="wav")
            return tmp.name
        except Exception as e:
            print(f"[WARN] Piper synthesis failed: {e}")
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            return None


# ─────────────────────────────────────────────────────────────
# Unified Voice (XTTS preferred, Piper fallback)
# ─────────────────────────────────────────────────────────────
SEGMENT_PAUSE_MS = 150


class Voice:
    """High-level voice pipeline: segments → stitched WAV."""

    def __init__(self):
        self.xtts = XTTSEngine()
        self.piper = PiperEngine()

        if self.xtts.is_ready():
            print("[OK] Voice engine: XTTS v2")
        elif self.piper.is_ready():
            print("[OK] Voice engine: Piper (fallback)")
        else:
            print("[WARN] No voice engine available — voice disabled")

    def is_ready(self) -> bool:
        return self.xtts.is_ready() or self.piper.is_ready()

    def _engine(self):
        return self.xtts if self.xtts.is_ready() else self.piper

    def synthesize_to_wav(self, text: str, action: str = "neutral") -> str | None:
        """Single-shot synthesis (no director)."""
        return self.synthesize_segments_to_wav(
            [{"text": text, "tone": "neutral"}]
        )

    def synthesize_segments_to_wav(self, segments, action: str = "neutral") -> str | None:
        """Synthesize each {text, tone} segment and stitch with pydub."""
        if not self.is_ready() or not segments:
            return None

        engine = self._engine()
        combined: AudioSegment | None = None

        for seg in segments:
            raw_text = seg.get("text", "")
            tone = (seg.get("tone") or "neutral").lower()
            text = clean_text_for_tts(raw_text)
            if not text:
                continue

            print(f"[VOICE] tone={tone:10s} | {text[:60]}")
            path = engine.synthesize_segment(text, tone)
            if not path:
                continue

            try:
                seg_audio = AudioSegment.from_wav(path)
                pause = AudioSegment.silent(duration=SEGMENT_PAUSE_MS)
                combined = seg_audio if combined is None else combined + pause + seg_audio
            finally:
                if os.path.exists(path):
                    os.remove(path)

        if combined is None:
            return None

        out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False,
                                          dir=tempfile.gettempdir())
        out.close()
        combined.export(out.name, format="wav")
        print(f"[DEBUG] Stitched WAV: {out.name} ({os.path.getsize(out.name)} bytes)")
        return out.name


# ─────────────────────────────────────────────────────────────
# Listener (Whisper STT) — unchanged
# ─────────────────────────────────────────────────────────────
class Listener:
    def __init__(self, model_size=WHISPER_MODEL_SIZE):
        self.model = None
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"[OK] Whisper loaded: {model_size}")
        except Exception as e:
            print(f"[WARN] Whisper unavailable: {e}")
            self.model = None

    def is_ready(self) -> bool:
        return self.model is not None

    def transcribe(self, audio_path: str) -> str:
        if not self.is_ready() or not audio_path or not os.path.exists(audio_path):
            return ""
        try:
            segments, _ = self.model.transcribe(
                audio_path, beam_size=5, language="en", vad_filter=True
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            print(f"[DEBUG] Transcribed: {text!r}")
            return text
        except Exception as e:
            print(f"[WARN] Transcription failed: {e}")
            return ""

'''
import os
import wave
import tempfile
from config import VOICE_MODEL_PATH , WHISPER_MODEL_SIZE
import re
from pydub import AudioSegment
from piper import SynthesisConfig

# Matches emojis, pictographs, dingbats, symbols, and other non-speech glyphs
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # geometric shapes extended
    "\U0001F800-\U0001F8FF"  # supplemental arrows-C
    "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
    "\U00002700-\U000027BF"  # dingbats
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U0001F000-\U0001F02F"  # mahjong
    "\U0001F0A0-\U0001F0FF"  # playing cards
    "]+",
    flags=re.UNICODE,
)

# ---------- Tone → Piper prosody + volume ----------
TONE_PROFILES = {
    "neutral":   {"length_scale": 1.00, "noise_scale": 0.667, "noise_w": 0.80, "volume_db": 0},
    "warm":      {"length_scale": 1.00, "noise_scale": 0.65,  "noise_w": 0.80, "volume_db": -1},
    "happy":     {"length_scale": 0.95, "noise_scale": 0.75,  "noise_w": 0.95, "volume_db": 1},
    "excited":   {"length_scale": 0.92, "noise_scale": 0.85,  "noise_w": 1.00, "volume_db": 2},
    "playful":   {"length_scale": 0.95, "noise_scale": 0.80,  "noise_w": 0.95, "volume_db": 0},
    "tender":    {"length_scale": 1.10, "noise_scale": 0.60,  "noise_w": 0.75, "volume_db": -3},
    "murmur":    {"length_scale": 1.20, "noise_scale": 0.55,  "noise_w": 0.60, "volume_db": -10},
    "whisper":   {"length_scale": 1.30, "noise_scale": 0.45,  "noise_w": 0.50, "volume_db": -15},
    "shy":       {"length_scale": 1.15, "noise_scale": 0.60,  "noise_w": 0.70, "volume_db": -6},
    "seductive": {"length_scale": 1.20, "noise_scale": 0.55,  "noise_w": 0.65, "volume_db": -8},
    "sad":       {"length_scale": 1.25, "noise_scale": 0.50,  "noise_w": 0.60, "volume_db": -5},
    "serious":   {"length_scale": 1.05, "noise_scale": 0.55,  "noise_w": 0.70, "volume_db": 0},
    "laugh":     {"length_scale": 0.95, "noise_scale": 0.90,  "noise_w": 1.00, "volume_db": 0},
    "sigh":      {"length_scale": 1.35, "noise_scale": 0.40,  "noise_w": 0.50, "volume_db": -4},
    "shout":     {"length_scale": 0.88, "noise_scale": 0.90,  "noise_w": 1.05, "volume_db": 5},
}

# Pause between segments (ms)
SEGMENT_PAUSE_MS = 130

def clean_text_for_tts(text: str) -> str:
    """Strip emojis, markdown, action tags, and extra whitespace for TTS."""
    if not text:
        return ""

    # Remove any leftover [ACTION: ...] tags (safety net)
    text = re.sub(r"\[ACTION:\s*\w+\]\s*", "", text)

    # Remove emojis
    text = EMOJI_PATTERN.sub("", text)

    # Remove markdown emphasis symbols and other punctuation noise
    text = re.sub(r"[*_`~#>]+", "", text)

    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()

    return text


class Voice:
    """Piper‑based text‑to‑speech wrapper."""

    def __init__(self, model_path=VOICE_MODEL_PATH):
        self.model_path = model_path
        self.voice = None
        if os.path.exists(model_path):
            try:
                from piper import PiperVoice
                self.voice = PiperVoice.load(
                    model_path,
                    config_path=model_path + ".json",
                )
                print(f"[OK] Loaded voice model: {model_path}")
            except Exception as e:
                print(f"[WARN] Failed to load Piper voice: {e}")
                self.voice = None
        else:
            print(f"[WARN] Voice model not found at {model_path}")

    def synthesize_segments_to_wav(self, segments, action: str = "neutral") -> str | None:
        """Takes a list of {'text': str, 'tone': str} and returns stitched WAV path."""
        if not self.is_ready() or not segments:
            return None

        combined: AudioSegment | None = None

        for seg in segments:
            text = clean_text_for_tts(seg.get("text", ""))
            tone = (seg.get("tone") or "neutral").lower()
            if not text:
                continue

            profile = TONE_PROFILES.get(tone, TONE_PROFILES["neutral"])
            cfg = SynthesisConfig(
                length_scale=profile["length_scale"],
                noise_scale=profile["noise_scale"],
                noise_w=profile["noise_w"],
            )

            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=tempfile.gettempdir()
            )
            tmp.close()

            try:
                with wave.open(tmp.name, "wb") as wav_file:
                    self.voice.synthesize_wav(text, wav_file, syn_config=cfg)

                if os.path.getsize(tmp.name) < 1000:
                    os.remove(tmp.name)
                    continue

                seg_audio = AudioSegment.from_wav(tmp.name).apply_gain(profile["volume_db"])
                pause = AudioSegment.silent(duration=SEGMENT_PAUSE_MS)

                combined = seg_audio if combined is None else combined + pause + seg_audio
                os.remove(tmp.name)

            except Exception as e:
                print(f"[WARN] Segment synthesis failed for '{text[:30]}…': {e}")
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
                continue

        if combined is None:
            return None

        out = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, dir=tempfile.gettempdir()
        )
        out.close()
        combined.export(out.name, format="wav")
        print(f"[DEBUG] Stitched WAV: {out.name} ({os.path.getsize(out.name)} bytes)")
        return out.name
    
    def is_ready(self) -> bool:
        return self.voice is not None

    def synthesize_to_wav(self, text: str) -> str | None:
        """Generate a WAV file for the given text. Returns the file path."""
        if not self.is_ready():
            return None
        # ⬇️ THIS LINE IS MISSING IN YOUR FILE
        clean = clean_text_for_tts(text)
        if not clean:
            return None
        
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, dir=tempfile.gettempdir()
        )
        tmp.close()

        try:
            # piper-tts 1.x: synthesize_wav() writes the complete WAV file
            if hasattr(self.voice, "synthesize_wav"):
                with wave.open(tmp.name, "wb") as wav_file:
                    self.voice.synthesize_wav(clean, wav_file)
            else:
                # Fallback for very old versions (< 1.0)
                with wave.open(tmp.name, "wb") as wav_file:
                    self.voice.synthesize(clean, wav_file)

            size = os.path.getsize(tmp.name)
            print(f"[DEBUG] WAV generated: {tmp.name} ({size} bytes)")

            if size < 1000:
                print("[WARN] WAV file is too small – synthesis may have failed")
                return None

            return tmp.name

        except Exception as e:
            print(f"[WARN] TTS failed: {e}")
            return None

# voice.py (append this class)

class Listener:
    """Speech-to-text using faster-whisper."""

    def __init__(self, model_size=WHISPER_MODEL_SIZE):
        self.model = None
        try:
            from faster_whisper import WhisperModel
            # device="cpu" works everywhere; use "cuda" if you have a GPU
            # compute_type="int8" is fast on CPU and uses less RAM
            self.model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
            )
            print(f"[OK] Loaded Whisper model: {model_size}")
        except Exception as e:
            print(f"[WARN] Failed to load Whisper: {e}")
            self.model = None

    def is_ready(self) -> bool:
        return self.model is not None

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file. Returns the text."""
        if not self.is_ready() or not audio_path:
            return ""
        if not os.path.exists(audio_path):
            print(f"[WARN] Audio file not found: {audio_path}")
            return ""
        try:
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language="en",           # force English (remove for auto-detect)
                vad_filter=True,         # skip silence
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            print(f"[DEBUG] Transcribed: {text!r}")
            return text
        except Exception as e:
            print(f"[WARN] Transcription failed: {e}")
            return ""

'''