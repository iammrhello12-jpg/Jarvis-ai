from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


DEFAULT_CONFIG_DIR = Path(os.getenv("LOCAL_AGENT_HOME", Path.cwd() / ".agent")).expanduser()
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_MODELS_DIR = DEFAULT_CONFIG_DIR / "models"
DEFAULT_MEMORY_DIR = DEFAULT_CONFIG_DIR / "memory"


class DeviceSettings(BaseModel):
    allow_shell: bool = False
    allowed_shell_prefixes: List[str] = Field(
        default_factory=lambda: [
            "ls", "cat", "echo", "python", "pip", "pwd", "whoami", "uptime",
            "df", "du", "free", "ps", "top", "head", "tail",
        ]
    )
    allow_open_url: bool = True
    safe_roots: List[str] = Field(
        default_factory=lambda: [str(Path.cwd()), str(Path.home())]
    )


class ModelSettings(BaseModel):
    model_path: str = str(DEFAULT_MODELS_DIR / "qwen2.5-1.5b-instruct-Q4_K_M.gguf")
    context_window: int = 4096
    n_gpu_layers: int = 0  # 0 for CPU-only
    temperature: float = 0.2
    top_p: float = 0.95


class EmbeddingSettings(BaseModel):
    # fastembed default; lightweight and no API key
    model_name: str = "BAAI/bge-small-en-v1.5"
    normalize: bool = True


class MemorySettings(BaseModel):
    persist_dir: str = str(DEFAULT_MEMORY_DIR)
    index_name: str = "default"
    top_k: int = 5


class AgentSettings(BaseModel):
    max_tool_steps: int = 5
    require_tool_approval: bool = True


class AgentConfig(BaseModel):
    device: DeviceSettings = DeviceSettings()
    model: ModelSettings = ModelSettings()
    embeddings: EmbeddingSettings = EmbeddingSettings()
    memory: MemorySettings = MemorySettings()
    agent: AgentSettings = AgentSettings()


class ConfigManager:
    @staticmethod
    def load(path: Optional[Path] = None) -> AgentConfig:
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return AgentConfig(**data)
        # Ensure directories exist
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        # Write default
        cfg = AgentConfig()
        ConfigManager.save(cfg, cfg_path)
        return cfg

    @staticmethod
    def save(config: AgentConfig, path: Optional[Path] = None) -> None:
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config.model_dump(mode="python"), f, sort_keys=False)
