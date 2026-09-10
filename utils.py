# utils.py
from config import SUMMARY_MAX_TOKENS, SUMMARY_TEMPERATURE


def count_tokens(text):
    """Rough token count: 1 token ≈ 4 characters."""
    return len(text) // 4


def summarize_conversation(messages, model):
    filtered = [m for m in messages if m["role"] != "system"]
    if not filtered:
        return None
    text = "\n".join([f"{m['role']}: {m['content']}" for m in filtered])
    
    # New prompt – extract facts, not dialogue
    prompt = f"""Extract the most important facts about the user from this conversation.
Write a short summary (2‑3 sentences) that captures:
- Their name, preferences, emotions, or any personal information they shared.
- Do NOT write a script or dialogue.

Conversation:
{text}

Summary of user facts:"""
    
    summary = model.generate(
        prompt,
        max_tokens=SUMMARY_MAX_TOKENS,
        temperature=SUMMARY_TEMPERATURE,
        top_p=1.0,
        repeat_penalty=1.0,
    )
    return summary