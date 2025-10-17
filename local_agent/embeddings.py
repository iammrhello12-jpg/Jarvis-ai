from __future__ import annotations

from typing import Iterable, List

import numpy as np


class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", normalize: bool = True):
        self.normalize = normalize
        # Try fastembed first (no heavy torch dependency)
        try:
            from fastembed import TextEmbedding

            self._backend = "fastembed"
            self._model = TextEmbedding(model_name)
        except Exception:
            # Fallback to sentence-transformers if available
            try:
                from sentence_transformers import SentenceTransformer

                self._backend = "sentence-transformers"
                self._model = SentenceTransformer(model_name)
            except Exception as e:
                raise RuntimeError(
                    "No embedding backend available. Install 'fastembed' or 'sentence-transformers'."
                ) from e

    def embed(self, texts: Iterable[str]) -> np.ndarray:
        if self._backend == "fastembed":
            vectors: List[List[float]] = []
            for vec in self._model.embed(texts):
                vectors.append(vec)
            arr = np.array(vectors, dtype=np.float32)
        else:
            # sentence-transformers
            arr = np.array(self._model.encode(list(texts), normalize_embeddings=False), dtype=np.float32)
        if self.normalize:
            norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
            arr = arr / norms
        return arr
