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

# companion.py
from config import (
    DEFAULT_PERSONALITY,
    SYSTEM_PROMPT_TEMPLATE,
    TEMPERATURE,
    TOP_P,
    REPEAT_PENALTY,
    MAX_NEW_TOKENS,
    SUMMARY_TRIGGER_EXCHANGES,
)
from memory import ShortTermMemory, LongTermMemory
from model import LlamaModel
from utils import summarize_conversation


class ChatCompanion:
    """Main orchestrator – handles conversation, memory, and generation."""

    def __init__(self, model_path=None, personality=DEFAULT_PERSONALITY):
        self.model = LlamaModel(model_path=model_path) if model_path else LlamaModel()
        self.short_mem = ShortTermMemory()
        self.long_mem = LongTermMemory()
        self.personality = personality
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(personality=personality)
        self.short_mem.add("system", self.system_prompt)
        self.exchange_count = 0

    def chat(self, user_input):
        # 1. Retrieve relevant long‑term memories
        snippets = self.long_mem.retrieve(user_input, n_results=3)
        print(f"[DEBUG] Retrieved {len(snippets)} long-term memories for: {user_input}")

        # 2. Build prompt
        prompt = self._build_prompt(user_input, snippets)

        # 3. Generate reply
        reply = self.model.generate(
            prompt,
            max_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repeat_penalty=REPEAT_PENALTY,
        )

        # 4. Store in short‑term
        self.short_mem.add("user", user_input)
        self.short_mem.add("assistant", reply)
        self.exchange_count += 1

        # 5. Periodic long‑term storage (summary of recent conversation)
        if self.exchange_count % SUMMARY_TRIGGER_EXCHANGES == 0:
            recent = self.short_mem.messages[-6:] if len(self.short_mem.messages) > 6 else self.short_mem.messages
            summary = summarize_conversation(recent, self.model)
            if summary:
                self.long_mem.add_memory(summary)
                print(f"[DEBUG] Stored summary in long-term memory: {summary}")

        return reply

    def _build_prompt(self, user_input, snippets):
        prompt = f"<<SYS>>\n{self.system_prompt}\n<</SYS>>\n\n"
        if snippets:
            prompt += "Relevant past memories:\n"
            for s in snippets:
                prompt += f"- {s}\n"
            prompt += "\n"

        # Add short‑term history (skip system prompt)
        for msg in self.short_mem.messages[1:]:
            if msg["role"] == "user":
                prompt += f"[INST] {msg['content']} [/INST]"
            else:
                prompt += f" {msg['content']} </s>"
        prompt += f"[INST] {user_input} [/INST]"

        # DEBUG: Print the full prompt before returning
        print("\n" + "="*50)
        print("FINAL PROMPT SENT TO MODEL:")
        print("="*50)
        print(prompt)
        print("="*50 + "\n")

        return prompt