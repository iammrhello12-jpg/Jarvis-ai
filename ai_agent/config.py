from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import yaml


@dataclass
class AgentConfig:
    model_path: str
    n_ctx: int = 4096
    n_threads: int = 4
    memory_dir: str = "data/memory"
    training_examples_path: str = "data/training/examples.jsonl"
    allow_destructive_tools: bool = False

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentConfig":
        return AgentConfig(
            model_path=data.get("model_path", "models/model.gguf"),
            n_ctx=int(data.get("n_ctx", 4096)),
            n_threads=int(data.get("n_threads", os.cpu_count() or 4)),
            memory_dir=data.get("memory_dir", "data/memory"),
            training_examples_path=data.get("training_examples_path", "data/training/examples.jsonl"),
            allow_destructive_tools=bool(data.get("allow_destructive_tools", False)),
        )


def load_config(path: str) -> AgentConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = AgentConfig.from_dict(raw)
    _ensure_dirs(cfg)
    return cfg


def _ensure_dirs(cfg: AgentConfig) -> None:
    os.makedirs(cfg.memory_dir, exist_ok=True)
    td = os.path.dirname(cfg.training_examples_path)
    if td:
        os.makedirs(td, exist_ok=True)
