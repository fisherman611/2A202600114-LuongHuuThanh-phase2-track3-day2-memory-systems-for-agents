from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .backends import JsonEpisodicStore, JsonProfileStore, SemanticFaissStore, SlidingWindowMemory
from .state import MemoryState


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _trim_lines_to_budget(lines: list[str], budget_words: int) -> list[str]:
    if budget_words <= 0:
        return []
    output: list[str] = []
    used = 0
    for line in lines:
        line_words = count_words(line)
        if line_words == 0:
            continue
        if used + line_words > budget_words:
            break
        output.append(line)
        used += line_words
    return output


@dataclass
class MemoryStack:
    short_term: SlidingWindowMemory
    profile: JsonProfileStore
    episodic: JsonEpisodicStore
    semantic: SemanticFaissStore


def build_default_stack(data_dir: str | Path = "data") -> MemoryStack:
    root = Path(data_dir)
    return MemoryStack(
        short_term=SlidingWindowMemory(max_messages=12),
        profile=JsonProfileStore(root / "profile.json"),
        episodic=JsonEpisodicStore(root / "episodes.json"),
        semantic=SemanticFaissStore(root / "semantic.index", root / "semantic_docs.json"),
    )


def _normalize_fact_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,!?\n\t")


def extract_profile_updates(user_text: str) -> dict[str, str]:
    text = user_text.strip()
    updates: dict[str, str] = {}

    fact_patterns: list[tuple[str, str]] = [
        (r"(?:tên tôi là|tôi tên là)\s+([^\.,\n]+)", "name"),
        (r"tôi sống ở\s+([^\.,\n]+)", "location"),
        (r"tôi làm nghề\s+([^\.,\n]+)", "occupation"),
    ]

    for pattern, key in fact_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
        if match:
            updates[key] = _normalize_fact_value(match.group(1))

    allergy_match = re.search(
        r"tôi dị ứng\s+([^\.,\n]+?)(?:\s+chứ\s+không\s+phải|\s*(?:[,\.\n]|$))",
        text,
        flags=re.IGNORECASE | re.UNICODE,
    )
    if allergy_match:
        updates["allergy"] = _normalize_fact_value(allergy_match.group(1))

    return updates


def _extract_episode_outcome(assistant_text: str) -> str | None:
    if not assistant_text.strip():
        return None
    signal_words = [
        "đã xong",
        "hoàn tất",
        "kết quả",
        "done",
        "completed",
        "resolved",
        "fix",
    ]
    lower = assistant_text.lower()
    if any(keyword in lower for keyword in signal_words):
        return assistant_text.strip()
    return None


def save_memory_updates(
    stack: MemoryStack,
    user_text: str,
    assistant_text: str = "",
    task_name: str = "general",
) -> None:
    updates = extract_profile_updates(user_text)
    for key, value in updates.items():
        # Conflict handling: newest fact for the same key always overwrites old one.
        stack.profile.upsert_fact(key, value)

    outcome = _extract_episode_outcome(assistant_text)
    if outcome:
        episode = {
            "timestamp": _utc_now_iso(),
            "task": task_name,
            "user_input": user_text.strip(),
            "outcome": outcome,
        }
        stack.episodic.append_episode(episode)


def retrieve_memory(state: MemoryState, stack: MemoryStack) -> MemoryState:
    messages = state.get("messages", [])
    current_query = ""
    if messages:
        for message in reversed(messages):
            if message.get("role") == "user":
                current_query = message.get("content", "")
                break

    state["user_profile"] = stack.profile.load_profile()
    state["episodes"] = stack.episodic.recent(limit=4)
    semantic_hits = stack.semantic.search(current_query, top_k=4) if current_query else []
    state["semantic_hits"] = [hit["text"] for hit in semantic_hits]
    return state


def memory_router(state: MemoryState, stack: MemoryStack) -> MemoryState:
    state["messages"] = stack.short_term.get_recent()
    return retrieve_memory(state, stack)


def _format_profile(profile: dict[str, str]) -> list[str]:
    if not profile:
        return ["- (empty)"]
    return [f"- {key}: {value}" for key, value in profile.items()]


def _format_episodes(episodes: list[dict[str, Any]]) -> list[str]:
    if not episodes:
        return ["- (none)"]
    lines: list[str] = []
    for idx, episode in enumerate(episodes, start=1):
        lines.append(
            f"- {idx}. task={episode.get('task', 'general')}, outcome={episode.get('outcome', '').strip()}"
        )
    return lines


def _format_semantic_hits(hits: list[str]) -> list[str]:
    if not hits:
        return ["- (none)"]
    return [f"- {idx}. {value}" for idx, value in enumerate(hits, start=1)]


def _format_recent_messages(messages: list[dict[str, str]]) -> list[str]:
    if not messages:
        return ["- (none)"]
    return [f"- {m['role']}: {m['content']}" for m in messages]


def build_prompt(state: MemoryState, current_user_message: str) -> str:
    budget = max(40, state.get("memory_budget", 220))
    profile_budget = int(budget * 0.20)
    episodic_budget = int(budget * 0.25)
    semantic_budget = int(budget * 0.25)
    recent_budget = max(10, budget - (profile_budget + episodic_budget + semantic_budget))

    profile_lines = _trim_lines_to_budget(_format_profile(state.get("user_profile", {})), profile_budget)
    episode_lines = _trim_lines_to_budget(_format_episodes(state.get("episodes", [])), episodic_budget)
    semantic_lines = _trim_lines_to_budget(_format_semantic_hits(state.get("semantic_hits", [])), semantic_budget)
    recent_lines = _trim_lines_to_budget(_format_recent_messages(state.get("messages", [])), recent_budget)

    return "\n".join(
        [
            "You are a helpful assistant. Use memory carefully.",
            "",
            "[USER PROFILE]",
            *profile_lines,
            "",
            "[EPISODIC MEMORY]",
            *episode_lines,
            "",
            "[SEMANTIC MEMORY HITS]",
            *semantic_lines,
            "",
            "[RECENT CONVERSATION]",
            *recent_lines,
            "",
            "[CURRENT USER MESSAGE]",
            current_user_message,
        ]
    )


class MemoryGraphSkeleton:
    def __init__(self, stack: MemoryStack):
        self.stack = stack

    def invoke(self, user_message: str, memory_budget: int = 220) -> tuple[MemoryState, str]:
        self.stack.short_term.add_message("user", user_message)
        state: MemoryState = {
            "messages": self.stack.short_term.get_recent(),
            "user_profile": {},
            "episodes": [],
            "semantic_hits": [],
            "memory_budget": memory_budget,
        }
        state = memory_router(state, self.stack)
        prompt = build_prompt(state, user_message)
        return state, prompt
