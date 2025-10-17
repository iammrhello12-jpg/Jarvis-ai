from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .agent import Agent
from .config import AgentConfig
from .llm import LocalLLM, Message
from .memory import TfidfMemory
from .tools import Tools


@dataclass
class RunContext:
    agent: Agent


def build_agent(cfg: AgentConfig) -> RunContext:
    llm = LocalLLM(cfg.model_path, n_ctx=cfg.n_ctx, n_threads=cfg.n_threads)
    memory = TfidfMemory(cfg.memory_dir)
    tools = Tools(allow_destructive=cfg.allow_destructive_tools)
    agent = Agent(llm=llm, memory=memory, tools=tools)
    return RunContext(agent=agent)
