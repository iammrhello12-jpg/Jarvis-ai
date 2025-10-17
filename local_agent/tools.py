from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from .config import AgentConfig


class ToolArgs(BaseModel):
    pass


@dataclass
class Tool:
    name: str
    description: str
    args_model: type[ToolArgs]
    func: Callable[[AgentConfig, ToolArgs], Dict[str, Any]]


class RunShellArgs(ToolArgs):
    command: str = Field(description="Shell command to execute. Must match allowed prefixes.")
    timeout: int = Field(default=20, description="Timeout seconds")


class OpenUrlArgs(ToolArgs):
    url: str


class ReadFileArgs(ToolArgs):
    path: str
    max_bytes: int = 200_000


class WriteFileArgs(ToolArgs):
    path: str
    content: str
    mode: str = "w"


class ListDirArgs(ToolArgs):
    path: str


class HttpGetArgs(ToolArgs):
    url: str
    timeout: int = 20


def _is_safe_path(path: str, safe_roots: List[str]) -> bool:
    try:
        p = Path(path).resolve()
        for root in safe_roots:
            if str(p).startswith(str(Path(root).resolve())):
                return True
        return False
    except Exception:
        return False


def run_shell(config: AgentConfig, args: RunShellArgs) -> Dict[str, Any]:
    if not config.device.allow_shell:
        return {"error": "Shell execution is disabled by config."}
    # Check whitelist
    parts = shlex.split(args.command)
    if not parts:
        return {"error": "Empty command"}
    allowed = any(args.command.strip().startswith(prefix + " ") or args.command.strip() == prefix for prefix in config.device.allowed_shell_prefixes)
    if not allowed:
        return {"error": f"Command not allowed. Allowed prefixes: {config.device.allowed_shell_prefixes}"}
    try:
        completed = subprocess.run(
            args.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
            text=True,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-10_000:],
            "stderr": completed.stderr[-10_000:],
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {args.timeout}s"}


def open_url(config: AgentConfig, args: OpenUrlArgs) -> Dict[str, Any]:
    if not config.device.allow_open_url:
        return {"error": "Opening URLs is disabled by config."}
    try:
        if os.name == "posix":
            subprocess.Popen(["xdg-open", args.url])
        elif os.name == "nt":
            os.startfile(args.url)  # type: ignore[attr-defined]
        else:
            return {"error": "Unsupported OS for open_url"}
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


def read_file(config: AgentConfig, args: ReadFileArgs) -> Dict[str, Any]:
    if not _is_safe_path(args.path, config.device.safe_roots):
        return {"error": "Path not in safe roots"}
    try:
        with open(args.path, "rb") as f:
            data = f.read(args.max_bytes)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="ignore")
        return {"content": text}
    except Exception as e:
        return {"error": str(e)}


def write_file(config: AgentConfig, args: WriteFileArgs) -> Dict[str, Any]:
    if not _is_safe_path(args.path, config.device.safe_roots):
        return {"error": "Path not in safe roots"}
    try:
        Path(args.path).parent.mkdir(parents=True, exist_ok=True)
        with open(args.path, args.mode, encoding="utf-8") as f:
            f.write(args.content)
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}


def list_dir(config: AgentConfig, args: ListDirArgs) -> Dict[str, Any]:
    if not _is_safe_path(args.path, config.device.safe_roots):
        return {"error": "Path not in safe roots"}
    try:
        entries = []
        p = Path(args.path)
        for child in p.iterdir():
            entries.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size,
            })
        return {"entries": entries}
    except Exception as e:
        return {"error": str(e)}


def http_get(config: AgentConfig, args: HttpGetArgs) -> Dict[str, Any]:
    try:
        resp = requests.get(args.url, timeout=args.timeout, headers={"User-Agent": "local-agent/0.1"})
        content = resp.text[:200_000]
        soup = BeautifulSoup(content, "html.parser")
        # crude text extraction
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        text = "\n".join(t.strip() for t in soup.get_text("\n").splitlines() if t.strip())
        return {"status": resp.status_code, "text": text[:200_000]}
    except Exception as e:
        return {"error": str(e)}


class ToolRegistry:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._tools: Dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(Tool(
            name="run_shell",
            description="Execute a whitelisted shell command on this device.",
            args_model=RunShellArgs,
            func=run_shell,
        ))
        self.register(Tool(
            name="open_url",
            description="Open a URL in the default browser.",
            args_model=OpenUrlArgs,
            func=open_url,
        ))
        self.register(Tool(
            name="read_file",
            description="Read a file (within safe roots).",
            args_model=ReadFileArgs,
            func=read_file,
        ))
        self.register(Tool(
            name="write_file",
            description="Write a file (within safe roots).",
            args_model=WriteFileArgs,
            func=write_file,
        ))
        self.register(Tool(
            name="list_dir",
            description="List directory entries (within safe roots).",
            args_model=ListDirArgs,
            func=list_dir,
        ))
        self.register(Tool(
            name="http_get",
            description="Fetch and extract text from a URL.",
            args_model=HttpGetArgs,
            func=http_get,
        ))

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def list(self) -> List[Dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        tool = self._tools[name]
        try:
            parsed = tool.args_model(**args)
        except Exception as e:
            return {"error": f"Invalid args for {name}: {e}"}
        return tool.func(self.config, parsed)
