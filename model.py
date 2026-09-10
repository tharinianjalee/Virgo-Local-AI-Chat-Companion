# model.py
import ollama
from config import OLLAMA_HOST, MODEL_NAME

# Optional: set the host if different from default
# ollama.Client(host=OLLAMA_HOST)

class LlamaModel:
    """Wrapper around Ollama's API for inference."""

    def __init__(self, model_name=MODEL_NAME):
        self.model_name = model_name
        # You can set client if needed:
        # self.client = ollama.Client(host=OLLAMA_HOST)

    def generate(self, prompt, max_tokens, temperature, top_p, repeat_penalty, echo=False):
        # Ollama's generate API
        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repeat_penalty": repeat_penalty,
                "num_ctx": 4096,
                "stop": ["[/INST]", "</s>", "User:", "Assistant:"],   # stop on any new turn
            }
        )
        return response["response"].strip()