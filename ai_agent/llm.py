from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator, List, Optional

from llama_cpp import Llama


@dataclass
class Message:
    role: str
    content: str


class LocalLLM:
    """Thin wrapper around llama-cpp-python for local inference."""

    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int = 4):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        # Use chat_format auto to support instruct/chat models
        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            chat_format="auto",
            verbose=False,
        )

    def chat(self, messages: List[Message], max_tokens: int = 512, temperature: float = 0.7, top_p: float = 0.95, stream: bool = False) -> Iterator[str] | str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        if stream:
            for tok in self.llm.create_chat_completion(
                messages=formatted,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=True,
            ):
                if token := tok.get("choices", [{}])[0].get("delta", {}).get("content"):
                    yield token
        else:
            out = self.llm.create_chat_completion(
                messages=formatted,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=False,
            )
            return out["choices"][0]["message"]["content"].strip()
