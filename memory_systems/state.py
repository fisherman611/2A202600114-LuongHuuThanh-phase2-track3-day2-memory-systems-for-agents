from __future__ import annotations

from typing import Any, TypedDict


class MemoryState(TypedDict):
    messages: list[dict[str, str]]
    user_profile: dict[str, str]
    episodes: list[dict[str, Any]]
    semantic_hits: list[str]
    memory_budget: int
