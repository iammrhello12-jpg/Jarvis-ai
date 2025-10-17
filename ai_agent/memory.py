from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class MemoryEntry:
    text: str
    meta: dict


class TfidfMemory:
    """Simple persistent vector store over TF-IDF."""

    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.memory_dir / "index.joblib"
        self.meta_path = self.memory_dir / "meta.json"
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: np.ndarray | None = None
        self.meta: List[dict] = []
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            data = joblib.load(self.index_path)
            self.vectorizer = data["vectorizer"]
            self.matrix = data["matrix"]
        if self.meta_path.exists():
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        if self.vectorizer is not None and self.matrix is not None:
            joblib.dump({"vectorizer": self.vectorizer, "matrix": self.matrix}, self.index_path)
        self.meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, entries: Iterable[MemoryEntry]) -> int:
        texts = [e.text for e in entries]
        metas = [e.meta for e in entries]
        if not texts:
            return 0
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self.matrix = self.vectorizer.fit_transform(texts)
            self.meta = metas
        else:
            assert self.matrix is not None
            new_vecs = self.vectorizer.transform(texts)
            from scipy.sparse import vstack

            self.matrix = vstack([self.matrix, new_vecs])
            self.meta.extend(metas)
        self._save()
        return len(texts)

    def search(self, query: str, k: int = 5) -> List[Tuple[float, str, dict]]:
        if self.vectorizer is None or self.matrix is None:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        top_idx = np.argsort(-sims)[:k]
        results: List[Tuple[float, str, dict]] = []
        for i in top_idx:
            score = float(sims[i])
            text = self._get_text_by_index(i)
            meta = self.meta[i] if i < len(self.meta) else {}
            results.append((score, text, meta))
        return results

    def _get_text_by_index(self, idx: int) -> str:
        # For simplicity we don't store raw texts separately; meta should include text when ingesting
        # but we will store text redundantly in meta["text"] to fetch here.
        meta = self.meta[idx]
        return meta.get("text", "")
