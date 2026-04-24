# Multi-Memory Agent (Lab #17 Skeleton)

This repository implements the rubric requirements for:

1. Full memory stack
2. LangGraph-like state/router + prompt injection
3. Save/update memory + conflict handling
4. Benchmark with 10 multi-turn conversations
5. Privacy/limitations reflection

## Project Structure

- `memory_systems/backends.py`: 4 memory backends
  - short-term: sliding window
  - long-term profile: JSON key-value
  - episodic: JSON list
  - semantic: FAISS (with numpy fallback if FAISS is unavailable)
- `memory_systems/state.py`: `MemoryState` typed state
- `memory_systems/pipeline.py`: router, retrieval, prompt injection, update logic
- `memory_systems/demo.py`: end-to-end demo (memory + NVIDIA-NIM LLM response)
- `tests/test_memory_pipeline.py`: required behavior tests
- `BENCHMARK.md`: 10 multi-turn benchmark scenarios
- `REFLECTION.md`: privacy and technical limitations

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

## Configure NVIDIA-NIM

Create `.env` from `.env.example`:

```bash
NVIDIA_API_KEY=your_key_here
NVIDIA_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_TEMPERATURE=0.2
NVIDIA_TOP_P=0.7
NVIDIA_MAX_TOKENS=1024
```

Then run:

```bash
python -m memory_systems.demo
```

## Notes

- Semantic memory uses FAISS when installed (`faiss-cpu` in `requirements.txt`).
- If FAISS import fails, code still runs with a deterministic cosine-search fallback so local development is not blocked.
- If `NVIDIA_API_KEY` is missing, demo falls back to "prompt-only" mode (no LLM generation).
