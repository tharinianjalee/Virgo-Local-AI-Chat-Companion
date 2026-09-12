![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

## 📄 License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for the full text.

# Virgo-Local-AI-Chat-Companion

A fully offline, memory‑aware AI companion built in Python. Virgo holds natural conversations, remembers facts about you over time, and runs entirely on your machine using [Ollama](https://ollama.com) – no cloud APIs, no data leaving your device.

---

## ✨ Features

- 🧠 **Short‑term memory** – token‑aware sliding window keeps recent context coherent.
- 📚 **Long‑term memory** – semantic recall via ChromaDB + sentence‑transformers. Virgo remembers facts about you across sessions.
- 📝 **Automatic summarisation** – every few exchanges, the conversation is summarised and stored as a fact, so the companion builds an evolving understanding of the user.
- 🎭 **Customisable personality** – change the companion’s tone and style via a single system prompt.
- 🖥️ **Dual interface** – CLI for quick testing, Gradio web UI for a polished chat experience.
- 🔒 **100% local & private** – all inference runs locally through Ollama.
- 🧩 **Modular architecture** – clean separation of model, memory, config, and orchestration.

---

## 🏗️ Architecture

```text
main.py ──► companion.py ──► model.py (Ollama inference)
                         ├──► memory.py (short + long term)
                         ├──► utils.py (summarisation)
                         └──► config.py (constants / prompts)

app.py ──► Gradio web UI (wraps companion.py)
```

| File | Responsibility |
|------|----------------|
| `config.py` | Model name, generation params, system prompt, memory settings |
| `model.py` | Thin wrapper around Ollama for inference |
| `memory.py` | `ShortTermMemory` (sliding window) + `LongTermMemory` (vector DB) |
| `utils.py` | Token counting, conversation summarisation |
| `companion.py` | `ChatCompanion` – orchestrates memory, prompt building, generation |
| `app.py` | Gradio web interface |
| `main.py` | CLI / Gradio entry point |

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com/download)** installed and running
- A compatible model pulled locally (default: `llama3.2:3b`)

```bash
ollama pull llama3.2:3b
```

### 2. Clone the repository

```bash
git clone https://github.com/<your-username>/virgo-chat-companion.git
cd virgo-chat-companion
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

Edit `config.py` if needed:

```python
MODEL_NAME = "llama3.2:3b"       # any Ollama model
TEMPERATURE = 0.85
MAX_NEW_TOKENS = 512
DEFAULT_PERSONALITY = "friendly, witty, and slightly flirtatious"
```

### 5. Run

**CLI:**

```bash
python main.py
```

**Gradio web UI:**

```bash
python main.py gradio
# or
python app.py
```

Then open `http://127.0.0.1:7860` in your browser.

---

## 🧠 How Memory Works

### Short‑term memory

Recent messages are stored raw in a list. When the estimated token count exceeds `SHORT_TERM_MAX_TOKENS`, the oldest user/assistant pairs are pruned. This keeps the prompt within the model’s context window without losing the immediate flow.

### Long‑term memory

Every `SUMMARY_TRIGGER_EXCHANGES` turns, the recent conversation is summarised by the model into a plain factual statement (e.g., "The user's name is Taf and they prefer to be called sweetie."). This summary is embedded using sentence-transformers and stored in ChromaDB.

On each new user message, the top‑K most semantically similar memories are retrieved and injected into the prompt as context – giving the companion persistent recall.

---

## ⚙️ Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_NAME` | Ollama model name | `llama3.2:3b` |
| `TEMPERATURE` | Sampling temperature | `0.85` |
| `TOP_P` | Nucleus sampling | `0.95` |
| `REPEAT_PENALTY` | Repetition penalty | `1.1` |
| `MAX_NEW_TOKENS` | Max tokens per reply | `512` |
| `SHORT_TERM_MAX_TOKENS` | Sliding window size (approx) | `3000` |
| `SUMMARY_TRIGGER_EXCHANGES` | Turns between summaries | `5` |
| `EMBEDDING_MODEL` | Sentence‑transformers model | `all-MiniLM-L6-v2` |
| `LONG_TERM_DB_PATH` | ChromaDB persistence dir | `./chroma_db` |

---

## 🛠️ Tech Stack

- Python 3.10+
- Ollama – local LLM inference
- ChromaDB – vector store for long‑term memory
- sentence‑transformers – text embeddings
- Gradio – web UI
- llama3.2 – default model

---

## 🗺️ Roadmap

- [ ] Streaming responses (token‑by‑token in Gradio)
- [ ] Voice input/output (Whisper + TTS)
- [ ] Multi‑user session support
- [ ] Memory editing / deletion UI
- [ ] Sentiment‑aware personality adaptation
- [ ] Docker image for easy deployment

---

## ⚠️ Notes

This project stores conversation summaries locally in `chroma_db/`. Delete that folder to reset long‑term memory.

The companion is designed for personal, local use. If you expose it publicly, ensure appropriate safeguards.

Tested with `llama3.2:3b`. Larger models (e.g., `llama3.1:8b`, `dolphin-mistral`) will improve quality if your hardware allows.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT License – see `LICENSE` for details.

---

## 🙏 Acknowledgements

- Ollama for making local LLMs easy
- ChromaDB for the vector store
- Gradio for the UI framework

Built as a personal exploration of memory, personality, and local LLM orchestration.
Character is built from a custom prompt using chatgpt 4mini
the video of idle is generated by kapwingAI

