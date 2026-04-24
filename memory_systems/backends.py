from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover
    faiss = None


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _normalized_hash_embedding(text: str, dim: int) -> np.ndarray:
    vector = np.zeros(dim, dtype=np.float32)
    tokens = _word_tokens(text)

    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector /= norm
    return vector


@dataclass
class SlidingWindowMemory:
    max_messages: int = 12
    _messages: list[dict[str, str]] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]

    def get_recent(self) -> list[dict[str, str]]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()


@dataclass
class JsonProfileStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def load_profile(self) -> dict[str, str]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save_profile(self, profile: dict[str, str]) -> None:
        self.path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert_fact(self, key: str, value: str) -> None:
        profile = self.load_profile()
        profile[key] = value
        self.save_profile(profile)


@dataclass
class JsonEpisodicStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def load_episodes(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def append_episode(self, episode: dict[str, Any]) -> None:
        episodes = self.load_episodes()
        episodes.append(episode)
        self.path.write_text(
            json.dumps(episodes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def recent(self, limit: int = 3) -> list[dict[str, Any]]:
        episodes = self.load_episodes()
        if limit <= 0:
            return []
        return episodes[-limit:]


@dataclass
class SemanticFaissStore:
    index_path: Path
    docs_path: Path
    dim: int = 256
    _docs: list[dict[str, Any]] = field(default_factory=list)
    _matrix: np.ndarray | None = None
    _index: Any = None

    def __post_init__(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.docs_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_docs()
        self._init_index()

    @property
    def backend_name(self) -> str:
        return "faiss" if faiss is not None else "numpy-fallback"

    def _load_docs(self) -> None:
        if self.docs_path.exists():
            self._docs = json.loads(self.docs_path.read_text(encoding="utf-8"))
        else:
            self._docs = []
            self.docs_path.write_text("[]", encoding="utf-8")

    def _save_docs(self) -> None:
        self.docs_path.write_text(
            json.dumps(self._docs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _init_index(self) -> None:
        if faiss is not None:
            if self.index_path.exists():
                self._index = faiss.read_index(str(self.index_path))
            else:
                self._index = faiss.IndexFlatIP(self.dim)
                self._rebuild_index()
        else:
            self._rebuild_numpy_matrix()

    def _rebuild_index(self) -> None:
        if faiss is None:
            return
        self._index = faiss.IndexFlatIP(self.dim)
        if not self._docs:
            faiss.write_index(self._index, str(self.index_path))
            return

        vectors = np.array(
            [_normalized_hash_embedding(doc["text"], self.dim) for doc in self._docs],
            dtype=np.float32,
        )
        self._index.add(vectors)
        faiss.write_index(self._index, str(self.index_path))

    def _rebuild_numpy_matrix(self) -> None:
        if not self._docs:
            self._matrix = np.zeros((0, self.dim), dtype=np.float32)
            return
        self._matrix = np.array(
            [_normalized_hash_embedding(doc["text"], self.dim) for doc in self._docs],
            dtype=np.float32,
        )

    def add_documents(self, texts: list[str], metadata: list[dict[str, Any]] | None = None) -> None:
        if metadata is None:
            metadata = [{} for _ in texts]
        if len(metadata) != len(texts):
            raise ValueError("metadata length must match texts length")

        for text, meta in zip(texts, metadata):
            self._docs.append({"text": text, "metadata": meta})
        self._save_docs()

        vectors = np.array(
            [_normalized_hash_embedding(text, self.dim) for text in texts],
            dtype=np.float32,
        )

        if faiss is not None:
            if self._index is None:
                self._index = faiss.IndexFlatIP(self.dim)
            self._index.add(vectors)
            faiss.write_index(self._index, str(self.index_path))
        else:
            if self._matrix is None or self._matrix.size == 0:
                self._matrix = vectors
            else:
                self._matrix = np.vstack([self._matrix, vectors])

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if not self._docs:
            return []

        k = max(1, min(top_k, len(self._docs)))
        query_vector = _normalized_hash_embedding(query, self.dim).reshape(1, -1).astype(np.float32)

        if faiss is not None and self._index is not None:
            scores, indices = self._index.search(query_vector, k)
            result: list[dict[str, Any]] = []
            for score, doc_idx in zip(scores[0], indices[0]):
                if doc_idx < 0:
                    continue
                doc = self._docs[int(doc_idx)]
                result.append(
                    {
                        "text": doc["text"],
                        "metadata": doc.get("metadata", {}),
                        "score": float(score),
                    }
                )
            return result

        if self._matrix is None:
            self._rebuild_numpy_matrix()
        if self._matrix is None or self._matrix.shape[0] == 0:
            return []

        sims = self._matrix @ query_vector[0]
        top_idx = np.argsort(-sims)[:k]
        result = []
        for idx in top_idx:
            doc = self._docs[int(idx)]
            result.append(
                {
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(sims[idx]),
                }
            )
        return result
