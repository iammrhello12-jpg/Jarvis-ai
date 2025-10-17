from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .llm import LocalLLM, Message
from .memory import TfidfMemory
from .tools import Tools, ToolResult


SYSTEM_PROMPT = (
    "You are a local AI agent with tools. "
    "Use concise reasoning. Think step-by-step in brief. "
    "When using tools, reflect on results and continue."
)


def build_prompt(user_input: str, memory_snippets: List[str]) -> List[Message]:
    context = "\n\n".join(f"MEMORY: {m}" for m in memory_snippets)
    messages = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"{user_input}\n\n{context}" if context else user_input),
    ]
    return messages


@dataclass
class AgentResponse:
    text: str
    used_tool: Optional[str] = None
    tool_output: Optional[str] = None


class Agent:
    def __init__(self, llm: LocalLLM, memory: TfidfMemory, tools: Tools):
        self.llm = llm
        self.memory = memory
        self.tools = tools

    def retrieve_memory(self, query: str, k: int = 5) -> List[str]:
        results = self.memory.search(query, k=k)
        return [text for _score, text, _meta in results if text]

    def think(self, user_input: str, max_tokens: int = 512) -> AgentResponse:
        memory_snippets = self.retrieve_memory(user_input)
        messages = build_prompt(user_input, memory_snippets)
        reply = self.llm.chat(messages, max_tokens=max_tokens, temperature=0.3)
        return AgentResponse(text=str(reply))

    def act(self, intent: str) -> ToolResult:
        # Very simple routing: detect commands like `shell: ...`, `read: path`, `write: path\n<content>` or `open: url`
        intent = intent.strip()
        if intent.startswith("shell:"):
            return self.tools.run_shell(intent[len("shell:"):].strip())
        if intent.startswith("read:"):
            return self.tools.read_file(intent[len("read:"):].strip())
        if intent.startswith("write:"):
            try:
                header, content = intent[len("write:"):].split("\n", 1)
            except ValueError:
                return ToolResult(False, "Write format: write: <path>\\n<content>")
            return self.tools.write_file(header.strip(), content)
        if intent.startswith("open:"):
            return self.tools.open_url(intent[len("open:"):].strip())
        return ToolResult(False, "Unknown intent. Prefix with shell:/read:/write:/open:")
