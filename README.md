# Jarvis-ai (Local, No API Keys)

A fully local AI agent with a "brain" (persistent memory), device control tools, and the ability to learn from your inputs and public data. Runs entirely on your machine using `llama.cpp` models (.gguf).

## Features
- Local LLM via `llama-cpp-python` (no API keys)
- Persistent memory: FAISS (if installed) or SQLite+NumPy fallback
- ReAct-style agent loop with safe tool calling
- Device control tools (opt-in): read/write files, list directories, run whitelisted shell, open URLs, HTTP GET and extract text
- Learn and recall: `teach` and `ingest` commands to expand memory

## Quickstart

1) Python 3.9+

2) Install system requirements for `llama-cpp-python` and optionally `faiss-cpu` (Linux):
- Ubuntu/Debian example:
```bash
sudo apt update
sudo apt install -y build-essential python3-dev
```

3) Install Python deps:
```bash
pip install -e .
# or
pip install -r requirements.txt
```

4) Initialize config and directories:
```bash
local-agent config-init
```
This creates `.agent/` in your current working directory with `config.yaml`, `models/`, and `memory/`.

5) Download a small instruct GGUF model (example Qwen 1.5B instruct Q4_K_M):
```bash
local-agent models-download \
  --repo-id Qwen/Qwen2.5-1.5B-Instruct-GGUF \
  --filename Qwen2.5-1.5B-Instruct-Q4_K_M.gguf
```
The agent will also auto-discover any `.gguf` in `.agent/models/` if `config.yaml` path is missing.

6) Chat:
```bash
local-agent chat
# or single-turn
local-agent chat --once
```

## Safety and Device Control
Device tools are restricted by config.
- `allow_shell` is OFF by default. When enabling, only whitelisted prefixes run (see `allowed_shell_prefixes`).
- File ops require paths to be under `safe_roots`.
- `open_url` uses the OS default opener.

Edit `.agent/config.yaml` to change settings.

## Memory and Learning
- `ingest <path|url>`: adds text chunks from files or a URL to memory.
- `teach "question" "answer"`: stores a Q/A pair for recall.
- During chat, top-k relevant memories are retrieved and included as context. Dialog pairs are auto-saved.

Backend options:
- If `faiss-cpu` is installed, vector search uses FAISS HNSW.
- Otherwise, agent stores normalized vectors in SQLite and performs NumPy brute-force similarity.

## Project Layout
- `local_agent/config.py`: defaults and config manager
- `local_agent/llm.py`: llama.cpp wrapper, auto-discovers `.gguf`
- `local_agent/embeddings.py`: FastEmbed (preferred) with sentence-transformers fallback
- `local_agent/memory.py`: SQLite store + FAISS or NumPy fallback
- `local_agent/tools.py`: device and web tools (safe by default)
- `local_agent/agent.py`: ReAct-style loop with JSON tool calls
- `local_agent/cli.py`: Typer CLI

## Notes
- For better performance, enable GPU layers in `config.yaml` if your build supports it (`n_gpu_layers > 0`).
- Use small models on CPU for responsiveness.
- No external API keys are required.
