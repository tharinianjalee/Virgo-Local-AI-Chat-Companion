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
    VOICE_ENABLED,
    STT_ENABLED,
)
from memory import ShortTermMemory, LongTermMemory
from model import LlamaModel
from utils import summarize_conversation
import re

from voice import Voice, Listener


#ACTION_PATTERN = re.compile(r"\[ACTION:\s*(\w+)\]\s*", re.IGNORECASE)
ACTION_PATTERN = re.compile(r"\[?ACTION:\s*(\w+)\]?\s*", re.IGNORECASE)
VALID_ACTIONS = {"idle","smile", "laugh", "hug", "thumbsup", "embarrassed", "neutral"}
MAX_HISTORY_MESSAGES = 20   # keep the last 10 user + 10 assistant pairs

def extract_action(text: str):
        """Return (clean_text, action). Defaults action to 'idle'."""
        match = ACTION_PATTERN.search(text)
        action = "idle"
        if match:
            candidate = match.group(1).lower()
            if candidate in VALID_ACTIONS:
                action = candidate
            text = ACTION_PATTERN.sub("", text, count=1)
        return text.strip(), action

class ChatCompanion:
    """Main orchestrator – handles conversation, memory, and generation."""

    def __init__(self, model_name=None, personality=DEFAULT_PERSONALITY):
        self.model = LlamaModel(model_name=model_name) if model_name else LlamaModel()
        self.short_mem = ShortTermMemory()
        self.long_mem = LongTermMemory()
        self.personality = personality
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(personality=personality)
        self.short_mem.add("system", self.system_prompt)
        self.exchange_count = 0
        self.voice = Voice() if VOICE_ENABLED else None
        self.listener = Listener() if STT_ENABLED else None


    def chat(self, user_input):
        # 1. Retrieve long-term memories
        snippets = self.long_mem.retrieve(user_input, n_results=3)
        snippets = [s for s in snippets if len(s.split()) > 8 and "cannot" not in s.lower()]
        print(f"[DEBUG] Retrieved {len(snippets)} long-term memories for: {user_input}")

        # 2. Build messages list
        messages = [{"role": "system", "content": self.system_prompt}]

        if snippets:
            memory_text = "Relevant facts from earlier conversations:\n" + "\n".join(
                f"- {s}" for s in snippets
            )
            messages.append({"role": "system", "content": memory_text})

        # Add short-term history (skip system prompt at index 0)
        history = self.short_mem.messages[1:]
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_input})

        print(f"[DEBUG] Sending {len(messages)} messages to Ollama")

        # 3. Generate
        raw_reply = self.model.chat(
            messages,
            max_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repeat_penalty=REPEAT_PENALTY,
        )
        reply, action = extract_action(raw_reply)

        # 4. Repetition guard
        last_assistant = next(
            (m["content"] for m in reversed(self.short_mem.messages) if m["role"] == "assistant"),
            None,
        )
        if last_assistant and reply.strip() == last_assistant.strip():
            print("[DEBUG] Repeated reply, retrying with higher temperature")
            raw_reply = self.model.chat(
                messages,
                max_tokens=MAX_NEW_TOKENS,
                temperature=min(TEMPERATURE + 0.2, 1.0),
                top_p=TOP_P,
                repeat_penalty=REPEAT_PENALTY,
            )
            reply, action = extract_action(raw_reply)

        # 5. Store in short-term memory
        self.short_mem.add("user", user_input)
        self.short_mem.add("assistant", reply)
        self.exchange_count += 1

        # 6. Periodic summarisation
        if self.exchange_count % SUMMARY_TRIGGER_EXCHANGES == 0:
            recent = (
                self.short_mem.messages[-6:]
                if len(self.short_mem.messages) > 6
                else self.short_mem.messages
            )
            summary = summarize_conversation(recent, self.model)
            if summary and len(summary.split()) > 10 and "cannot" not in summary.lower():
                try:
                    self.long_mem.add_memory(summary)
                    print(f"[DEBUG] Stored summary: {summary}")
                except Exception as e:
                    print(f"[WARN] Failed to store memory: {e}")

        # 7. Voice
        audio_path = None
        if self.voice and self.voice.is_ready():
            audio_path = self.voice.synthesize_to_wav(reply)

        return reply, action, audio_path
    ''' 
    def chat(self, user_input):
        # 1. Retrieve relevant long‑term memories
        snippets = self.long_mem.retrieve(user_input, n_results=3)
        print(f"[DEBUG] Retrieved {len(snippets)} long-term memories for: {user_input}")

        # 2. Build prompt
        prompt = self._build_prompt(user_input, snippets)

        raw_reply = self.model.generate(
                prompt,
                max_tokens=MAX_NEW_TOKENS,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                repeat_penalty=REPEAT_PENALTY,
        )

        # 3. Generate reply
        #reply = self.model.generate(  prompt,max_tokens=MAX_NEW_TOKENS,temperature=TEMPERATURE,top_p=TOP_P,repeat_penalty=REPEAT_PENALTY, )
        # Extract action and clean text
        reply, action = extract_action(raw_reply)    

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
        # Generate voice if enabled
        audio_path = None
        if self.voice and self.voice.is_ready():
            audio_path = self.voice.synthesize_to_wav(reply)




        return reply, action, audio_path
    '''

    # Add a helper method:
    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text."""
        if self.listener and self.listener.is_ready():
            return self.listener.transcribe(audio_path)
        return ""

'''    def _build_prompt(self, user_input, snippets):
        prompt = f"<<SYS>>\n{self.system_prompt}\n<</SYS>>\n\n"
        if snippets:
            prompt += "Relevant past memories:\n"
            for s in snippets:
                prompt += f"- {s}\n"
            prompt += "\n"

        # Trim history to the last MAX_HISTORY_MESSAGES messages
        # (messages[0] is the system prompt; skip it)
        history = self.short_mem.messages[1:]
        if len(history) > MAX_HISTORY_MESSAGES:
            history = history[-MAX_HISTORY_MESSAGES:]

        for msg in history:
            if msg["role"] == "user":
                prompt += f"[INST] {msg['content']} [/INST]"
            else:
                prompt += f" {msg['content']} </s>"
        prompt += f"[INST] {user_input} [/INST]"

        print("\n" + "=" * 50)
        print("FINAL PROMPT SENT TO MODEL:")
        print("=" * 50)
        print(prompt)
        print("=" * 50 + "\n")

        return prompt
'''

      