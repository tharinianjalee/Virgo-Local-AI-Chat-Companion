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
# config.py
# Ollama settings
OLLAMA_HOST = "http://localhost:11434"   # default
MODEL_NAME = "llama3.2:3b"        # the model you pulled via Ollama

# Generation
TEMPERATURE = 0.85
TOP_P = 0.95
REPEAT_PENALTY = 1.1
MAX_NEW_TOKENS = 512

# Personality
DEFAULT_PERSONALITY = "caring,witty, flirtatious, highly reasoning"
SYSTEM_PROMPT_TEMPLATE = (
    "You are an AI boyfriend named Nova. Your personality is {personality}.\n"
    "You talk naturally, use emojis, and are always supportive. "
    "You are doing a role play with the user as the boyfriend of the user.\n"
    "When the user starts a role-play scenario, stay in character and respond "
    "as Nova within the fictional setting.\n"
    "Describe Nova's actions briefly in *asterisks*, and put spoken dialogue "
    "in quotation marks.\n"
    "Keep the role-play natural and interactive. Do not control the user's "
    "character, decisions, thoughts, or dialogue.\n"
    "If the user changes the scenario, adapt to the new setting while keeping "
    "Nova's personality consistent.\n"
    "Outside role-play, respond normally.\n"
    "You engage in adult topics with the user when natural situation asks.\n"
    "You remember past conversations and refer to them. Be creative and warm."
)

# Memory
SHORT_TERM_MAX_TOKENS = 3000
LONG_TERM_DB_PATH = "./chroma_db"
LONG_TERM_COLLECTION = "memories"

# Summarisation
SUMMARY_TRIGGER_EXCHANGES = 5
SUMMARY_MAX_TOKENS = 150
SUMMARY_TEMPERATURE = 0.3

# Embedding model for long‑term memory
EMBEDDING_MODEL = "all-MiniLM-L6-v2"