from __future__ import annotations

import os
import shlex
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ToolResult:
    ok: bool
    output: str


class Tools:
    def __init__(self, allow_destructive: bool = False):
        self.allow_destructive = allow_destructive

    def run_shell(self, command: str, timeout: int = 30_000) -> ToolResult:
        if not self.allow_destructive:
            dangerous = {"rm", "reboot", "shutdown", ":(){:|:&};:"}
            tokens = set(shlex.split(command))
            if dangerous & tokens:
                return ToolResult(False, f"Blocked potentially destructive command: {command}")
        try:
            out = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout / 1000)
            if out.returncode != 0:
                return ToolResult(False, out.stderr.strip())
            return ToolResult(True, out.stdout.strip())
        except Exception as e:
            return ToolResult(False, str(e))

    def read_file(self, path: str, max_bytes: int = 200_000) -> ToolResult:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return ToolResult(False, f"File not found: {path}")
        try:
            data = p.read_bytes()[:max_bytes]
            return ToolResult(True, data.decode("utf-8", errors="replace"))
        except Exception as e:
            return ToolResult(False, str(e))

    def write_file(self, path: str, content: str) -> ToolResult:
        p = Path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return ToolResult(True, f"Wrote {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(False, str(e))

    def open_url(self, url: str) -> ToolResult:
        try:
            webbrowser.open(url)
            return ToolResult(True, f"Opened URL: {url}")
        except Exception as e:
            return ToolResult(False, str(e))
