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

# memory.py
import uuid
import chromadb
from sentence_transformers import SentenceTransformer
from config import (
    LONG_TERM_DB_PATH,
    LONG_TERM_COLLECTION,
    EMBEDDING_MODEL,
    SHORT_TERM_MAX_TOKENS,
)


class ShortTermMemory:
    """Stores recent conversation turns with token‑based pruning."""

    def __init__(self, max_tokens=SHORT_TERM_MAX_TOKENS):
        self.messages = []
        self.max_tokens = max_tokens

    def add(self, role, content):
        self.messages.append({"role": role, "content": content})
        self._prune()

    def _prune(self):
        # Remove oldest user/assistant pairs until token count fits
        while self._count_tokens() > self.max_tokens and len(self.messages) > 2:
            # Keep system prompt if present at index 0
            if self.messages[0]["role"] == "system":
                del self.messages[1:3]  # remove first user+assistant
            else:
                del self.messages[:2]

    def _count_tokens(self):
        # Rough estimate: 1 token ≈ 4 chars
        return sum(len(m["content"]) // 4 for m in self.messages)

    def get_messages(self):
        return self.messages


class LongTermMemory:
    """Vector database for storing and retrieving past conversations."""

    def __init__(self, collection_name=LONG_TERM_COLLECTION):
        self.client = chromadb.PersistentClient(path=LONG_TERM_DB_PATH)
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

    def add_memory(self, text, metadata=None):
        # Ensure metadata is a non‑empty dict
        if metadata is None:
            metadata = {"timestamp": str(uuid.uuid4())}   # <-- always a non‑empty dict
        # If metadata is an empty dict, also replace it
        elif metadata == {}:
            metadata = {"timestamp": str(uuid.uuid4())}
            
        embedding = self.embedder.encode(text).tolist()
        self.collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
            ids=[str(uuid.uuid4())],
        )

    def retrieve(self, query, n_results=3):
        embedding = self.embedder.encode(query).tolist()
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
        return results["documents"][0] if results else []