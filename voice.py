# voice.py
import os
import wave
import tempfile
from config import VOICE_MODEL_PATH , WHISPER_MODEL_SIZE
import re

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