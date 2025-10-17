from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
try:
    import faiss  # type: ignore
    HAVE_FAISS = True
except Exception:  # pragma: no cover - optional dependency
    faiss = None  # type: ignore
    HAVE_FAISS = False

from .config import AgentConfig, ConfigManager
from .embeddings import Embedder


@dataclass
class MemoryHit:
    id: int
    text: str
    score: float
    metadata: Dict


class MemoryStore:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or ConfigManager.load()
        self.persist_dir = Path(self.config.memory.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.persist_dir / f"{self.config.memory.index_name}.sqlite3"
        self.index_path = self.persist_dir / f"{self.config.memory.index_name}.faiss"
        self.embedder = Embedder(
            model_name=self.config.embeddings.model_name,
            normalize=self.config.embeddings.normalize,
        )
        self.index = None  # FAISS index when available
        self._init_db()
        self._load_index()

    # --- SQLite storage ---
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            # Optional vectors table for FAISS-less brute force fallback
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    id INTEGER PRIMARY KEY,
                    vector BLOB NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _load_index(self):
        if not HAVE_FAISS:
            self.index = None
            return
        # Determine embedding dimension lazily
        if self.index_path.exists():
            idx = faiss.read_index(str(self.index_path)).to_cpu()
            if not isinstance(idx, faiss.IndexIDMap2):
                idx = faiss.IndexIDMap2(idx)
            self.index = idx
            return
        # Create a new index with dimension inferred from a dummy embedding
        dim = self.embedder.embed(["dimension probe"]).shape[1]
        base = faiss.IndexHNSWFlat(dim, 32, faiss.METRIC_INNER_PRODUCT)
        self.index = faiss.IndexIDMap2(base)
        self._persist_index()

    def _persist_index(self):
        if not HAVE_FAISS or self.index is None:
            return
        faiss.write_index(self.index, str(self.index_path))

    # --- Public API ---
    def add(self, texts: Iterable[str], metadatas: Optional[Iterable[Dict]] = None) -> List[int]:
        texts_list = list(texts)
        metas_list = list(metadatas or [{} for _ in texts_list])
        if len(metas_list) != len(texts_list):
            raise ValueError("texts and metadatas lengths differ")
        vectors = self.embedder.embed(texts_list)
        ids: List[int] = []
        conn = sqlite3.connect(self.db_path)
        try:
            for text, meta, vec in zip(texts_list, metas_list, vectors):
                cur = conn.execute(
                    "INSERT INTO memories(text, metadata, created_at) VALUES (?, ?, ?)",
                    (text, json.dumps(meta), datetime.utcnow().isoformat()),
                )
                row_id = int(cur.lastrowid)
                ids.append(row_id)
                if HAVE_FAISS and self.index is not None:
                    vec_np = np.array([vec], dtype=np.float32)
                    self.index.add_with_ids(vec_np, np.array([row_id], dtype=np.int64))
                else:
                    # Persist vector bytes for brute-force search
                    conn.execute(
                        "INSERT OR REPLACE INTO vectors(id, vector) VALUES (?, ?)",
                        (row_id, np.asarray(vec, dtype=np.float32).tobytes()),
                    )
            conn.commit()
        finally:
            conn.close()
        self._persist_index()
        return ids

    def search(self, query: str, top_k: Optional[int] = None) -> List[MemoryHit]:
        topk = top_k or self.config.memory.top_k
        q = self.embedder.embed([query])  # shape (1, dim)
        hits: List[MemoryHit] = []

        if HAVE_FAISS and self.index is not None:
            scores, ids = self.index.search(q, topk)
            id_list = [int(i) for i in ids[0] if i != -1]
            if not id_list:
                return []
            placeholders = ",".join(["?"] * len(id_list))
            conn = sqlite3.connect(self.db_path)
            try:
                cur = conn.execute(
                    f"SELECT id, text, metadata FROM memories WHERE id IN ({placeholders})",
                    id_list,
                )
                rows = {int(r[0]): (r[1], r[2]) for r in cur.fetchall()}
            finally:
                conn.close()
            for i, s in zip(id_list, scores[0][: len(id_list)]):
                text, meta_json = rows.get(int(i), ("", "{}"))
                hits.append(MemoryHit(id=int(i), text=text, score=float(s), metadata=json.loads(meta_json)))
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits

        # Brute-force fallback: cosine similarity via dot product (vectors already normalized)
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute("SELECT id, vector FROM vectors")
            rows = cur.fetchall()
        finally:
            conn.close()
        if not rows:
            return []
        ids = np.array([int(r[0]) for r in rows], dtype=np.int64)
        vec_list = [np.frombuffer(r[1], dtype=np.float32) for r in rows]
        # Ensure all vectors same dim
        dim = vec_list[0].shape[0]
        vecs = np.vstack([v.reshape(1, dim) for v in vec_list])  # (N, dim)
        sims = (vecs @ q[0].reshape(dim, 1)).reshape(-1)
        topk = min(topk, sims.shape[0])
        top_idx = np.argpartition(-sims, topk - 1)[:topk]
        top_sorted = top_idx[np.argsort(-sims[top_idx])]
        top_ids = ids[top_sorted].tolist()
        top_scores = sims[top_sorted].tolist()

        placeholders = ",".join(["?"] * len(top_ids))
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                f"SELECT id, text, metadata FROM memories WHERE id IN ({placeholders})",
                top_ids,
            )
            row_map = {int(r[0]): (r[1], r[2]) for r in cur.fetchall()}
        finally:
            conn.close()
        for i, s in zip(top_ids, top_scores):
            text, meta_json = row_map.get(int(i), ("", "{}"))
            hits.append(MemoryHit(id=int(i), text=text, score=float(s), metadata=json.loads(meta_json)))
        return hits
