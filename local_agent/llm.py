from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from .config import AgentConfig, ConfigManager, DEFAULT_MODELS_DIR


class LocalLLM:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or ConfigManager.load()
        self._llm = None

    def _load(self):
        if self._llm is not None:
            return self._llm
        # Lazy import to avoid heavy import during CLI help
        from llama_cpp import Llama

        model_path = Path(self.config.model.model_path)
        if not model_path.exists():
            # Try to auto-discover a GGUF model in DEFAULT_MODELS_DIR
            candidates = sorted(
                DEFAULT_MODELS_DIR.glob("*.gguf"), key=lambda p: p.stat().st_size, reverse=True
            )
            if candidates:
                model_path = candidates[0]
            else:
                raise FileNotFoundError(
                    f"Model not found at {model_path}. Download a GGUF via 'local-agent models-download' or place one in {DEFAULT_MODELS_DIR}."
                )
        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=self.config.model.context_window,
            n_gpu_layers=self.config.model.n_gpu_layers,
            logits_all=False,
            chat_format="chatml",
            verbose=False,
        )
        return self._llm

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> str:
        llm = self._load()
        # Prefer chat completion API if available
        if hasattr(llm, "create_chat_completion"):
            out = llm.create_chat_completion(
                messages=messages,
                temperature=self.config.model.temperature,
                top_p=self.config.model.top_p,
                max_tokens=max_tokens,
                stream=False,
            )
            return out["choices"][0]["message"]["content"].strip()
        # Fallback to completion with formatted prompt
        prompt = self._format_chatml(messages)
        out = llm(
            prompt,
            temperature=self.config.model.temperature,
            top_p=self.config.model.top_p,
            max_tokens=max_tokens,
            stop=["</s>", "</assistant>"]
        )
        return out["choices"][0]["text"].strip()

    @staticmethod
    def _format_chatml(messages: List[Dict[str, str]]) -> str:
        parts: List[str] = ["<|im_start|>system\nYou are a helpful local AI assistant.<|im_end|>"]
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)
