# Copyright 2025 Baduge Tharini Anjalee Fernando
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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