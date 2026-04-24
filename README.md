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

## Notes

- Semantic memory uses FAISS when installed (`faiss-cpu` in `requirements.txt`).
- If FAISS import fails, code still runs with a deterministic cosine-search fallback so local development is not blocked.
