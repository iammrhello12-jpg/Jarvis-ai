from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.panel import Panel

from .config import load_config, AgentConfig

app = typer.Typer(add_completion=False, help="Local AI agent CLI (no API keys)")


@app.callback()
def main(ctx: typer.Context, config: str = typer.Option("config.yaml", "--config", "-c", help="Path to config.yaml")):
    """Load configuration and attach to context."""
    try:
        cfg = load_config(config)
    except FileNotFoundError:
        rprint(f"[red]Config not found:[/red] {config}")
        raise typer.Exit(code=1)
    ctx.obj = cfg


@app.command("config-show")
def config_show(ctx: typer.Context):
    cfg: AgentConfig = ctx.obj
    rprint(Panel.fit(json.dumps(cfg.__dict__, indent=2), title="Agent Config"))


@app.command("chat")
def chat(ctx: typer.Context, message: Optional[str] = typer.Option(None, "--message", "-m", help="Single-turn message. If omitted, enter interactive chat.")):
    rprint("[yellow]Chat will be available after the agent is fully wired.[/yellow]")
    if message:
        rprint(f"You said: [bold]{message}[/bold]")


if __name__ == "__main__":
    app()
