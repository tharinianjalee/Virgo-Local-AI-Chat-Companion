# director.py
import json
import ollama
from config import DIRECTOR_MODEL


DIRECTOR_PROMPT = """You are a voice director for a text-to-speech system.
Your job: split the assistant's reply into segments and label each with a tone.

Rules:
- Split at natural sentence boundaries.
- Do NOT split into individual words.
- Each segment must contain only the words to be spoken (no stage directions, no [ACTION: ...] tags).
- Combine multiple sentences into one segment if they share the same tone.
- Choose exactly ONE tone per segment from this list:
  neutral, warm, happy, excited, playful, tender, murmur, whisper, shy,
  seductive, sad, serious, laugh, sigh, shout
- If the segment is a brief narration like "I murmur" or "she whispers", 
  fold its tone into the surrounding dialogue segment.
- Output ONLY JSON, no explanation.

Output schema:
{"segments": [{"text": "...", "tone": "warm"}, {"text": "...", "tone": "excited"}]}

Example input:
"[ACTION: smile] Hey there! I'm so happy to see you. [Internal thought: she looks tired.] How was your day?"

Example output:
{"segments": [
  {"text": "Hey there!", "tone": "excited"},
  {"text": "I'm so happy to see you.", "tone": "warm"},
  {"text": "I've just been relaxing at home.", "tone": "neutral"},
  {"text": "How was your day?", "tone": "tender"}
]}
"""
def merge_segments(segments):
    """Merge consecutive segments with the same tone into one."""
    if not segments:
        return segments

    merged = [segments[0].copy()]
    for seg in segments[1:]:
        text = seg.get("text", "").strip()
        tone = seg.get("tone", "neutral")
        if not text:
            continue

        last = merged[-1]
        if last["tone"] == tone:
            # Join with proper spacing — avoid gluing punctuation
            joiner = "" if last["text"].endswith((" ", "-", "—")) else " "
            last["text"] = last["text"].rstrip() + joiner + text
        else:
            merged.append({"text": text, "tone": tone})

    return merged

class Director:
    """A small LLM that annotates voice segments with tone labels."""

    def __init__(self, model=DIRECTOR_MODEL):
        self.model = model
        print(f"[OK] Director model: {model}")


    def direct(self, text: str):
        """
        Return a list of {'text': str, 'tone': str} segments.
        Falls back to a single neutral segment on any error.
        """
        if not text.strip():
            return [{"text": text, "tone": "neutral"}]

        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": DIRECTOR_PROMPT},
                    {"role": "user", "content": text},
                ],
                format="json",              # force JSON output
                options={"temperature": 0.3, "num_predict": 1024, "num_ctx": 4096,},
            )
            content = response["message"]["content"]
            data = json.loads(content)
            segments = data.get("segments", [])
            if not segments:
                raise ValueError("No segments returned")
            # Validate shape
            clean = []
            for s in segments:
                t = (s.get("text") or "").strip()
                tone = (s.get("tone") or "neutral").lower().strip()
                if t:
                    clean.append({"text": t, "tone": tone})
            clean = merge_segments(clean)                    
            return clean or [{"text": text, "tone": "neutral"}]

        except Exception as e:
            print(f"[WARN] Director failed ({e}); using single neutral segment")
            return [{"text": text, "tone": "neutral"}]