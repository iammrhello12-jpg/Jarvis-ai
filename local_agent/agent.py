from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .config import AgentConfig, ConfigManager
from .llm import LocalLLM
from .memory import MemoryStore
from .tools import ToolRegistry


TOOL_JSON_RE = re.compile(r"```json\s*(\{[\s\S]*?\})\s*```", re.IGNORECASE)


@dataclass
class AgentStepResult:
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    tool_result: Optional[Dict] = None


class Agent:
    def __init__(self, config: AgentConfig | None = None):
        self.config = config or ConfigManager.load()
        self.llm = LocalLLM(self.config)
        self.memory = MemoryStore(self.config)
        self.tools = ToolRegistry(self.config)

    def _build_system_prompt(self) -> str:
        tools_list = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools.list()])
        return (
            "You are a helpful local AI agent that can use tools to control the user's device.\n"
            "Follow these rules strictly:\n"
            "- Think step-by-step. If you need information or to act, call a tool.\n"
            "- To call a tool, output a JSON object inside a fenced code block with language 'json', EXACTLY like:\n"
            "```json\n{\n  \"tool\": \"tool_name\",\n  \"args\": { ... }\n}\n```\n"
            "- After you have enough information, answer the user directly without a tool.\n"
            "Available tools:\n" + tools_list + "\n"
            "IMPORTANT: Only one tool call per step."
        )

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        m = TOOL_JSON_RE.search(text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict) and "tool" in obj and "args" in obj:
                return obj
        except Exception:
            return None
        return None

    def chat(self, user_message: str, session_id: str = "default") -> AgentStepResult:
        # Retrieve memory for context
        memories = self.memory.search(user_message, top_k=5)
        mem_text = "\n".join([f"- {m.text}" for m in memories]) if memories else "(no relevant memory)"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"Context memory:\n{mem_text}\n\nUser: {user_message}"},
        ]

        tool_steps = 0
        last_tool_result = None
        while tool_steps <= self.config.agent.max_tool_steps:
            content = self.llm.chat(messages, max_tokens=512)
            tool_call = self._parse_tool_call(content)
            if tool_call is None:
                # Final answer
                self.memory.add([f"Q: {user_message}\nA: {content}"], [{"type": "dialog", "session": session_id}])
                return AgentStepResult(content=content, tool_result=last_tool_result)
            # Execute tool
            name = str(tool_call.get("tool"))
            args = dict(tool_call.get("args", {}))
            result = self.tools.execute(name, args)
            # Append tool result and continue
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "tool", "content": json.dumps({"tool": name, "result": result})})
            last_tool_result = result
            tool_steps += 1
        # Max steps reached, provide best effort answer
        fallback = (
            "I reached the maximum number of tool steps. Here is the latest tool result: "
            f"{json.dumps(last_tool_result) if last_tool_result else 'none'}."
        )
        self.memory.add([f"Q: {user_message}\nA: {fallback}"], [{"type": "dialog", "session": session_id}])
        return AgentStepResult(content=fallback, tool_result=last_tool_result)
