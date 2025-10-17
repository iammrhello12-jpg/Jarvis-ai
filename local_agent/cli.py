from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import AgentConfig, ConfigManager, DEFAULT_MODELS_DIR

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Local AI agent (no API keys)")
console = Console()


@app.command()
def config_init():
    """Create a default config file in ./.agent/config.yaml"""
    cfg = ConfigManager.load()
    console.print(f"Config written to [bold]{cfg.model_dump()}[/bold]")


@app.command()
def tools_list():
    # Lazy import to avoid heavy startup cost
    from .tools import ToolRegistry
    cfg = ConfigManager.load()
    reg = ToolRegistry(cfg)
    table = Table(title="Available Tools")
    table.add_column("Name")
    table.add_column("Description")
    for t in reg.list():
        table.add_row(t["name"], t["description"])
    console.print(table)


@app.command()
def chat(once: bool = typer.Option(False, help="Run a single-turn chat and exit")):
    from .agent import Agent
    agent = Agent()
    console.print("[bold green]Local Agent[/bold green] - type 'exit' to quit.")
    if once:
        user = typer.prompt("You")
        res = agent.chat(user)
        console.print(f"[bold]Assistant:[/bold] {res.content}")
        raise typer.Exit(0)
    while True:
        user = typer.prompt("You")
        if user.strip().lower() in {"exit", "quit"}:
            break
        res = agent.chat(user)
        console.print(f"[bold]Assistant:[/bold] {res.content}")


@app.command()
def ingest(path_or_url: str = typer.Argument(..., help="File/dir path or URL to ingest")):
    from bs4 import BeautifulSoup
    import requests

    from .memory import MemoryStore
    store = MemoryStore()
    texts = []
    metas = []
    p = Path(path_or_url)
    if p.exists():
        files = []
        if p.is_dir():
            for root, _, filenames in os.walk(p):
                for fn in filenames:
                    fp = Path(root) / fn
                    if fp.suffix.lower() in {".txt", ".md", ".py", ".json", ".log"}:
                        files.append(fp)
        else:
            files = [p]
        for f in files:
            try:
                data = f.read_text(encoding="utf-8")
            except Exception:
                continue
            for chunk in _chunk_text(data):
                texts.append(chunk)
                metas.append({"source": str(f)})
    else:
        # Treat as URL
        try:
            resp = requests.get(path_or_url, timeout=20, headers={"User-Agent": "local-agent/0.1"})
            soup = BeautifulSoup(resp.text, "html.parser")
            for s in soup(["script", "style", "noscript"]):
                s.decompose()
            text = "\n".join(t.strip() for t in soup.get_text("\n").splitlines() if t.strip())
            for chunk in _chunk_text(text):
                texts.append(chunk)
                metas.append({"source": path_or_url})
        except Exception as e:
            console.print(f"[red]Failed to fetch URL:[/red] {e}")
            raise typer.Exit(1)
    if not texts:
        console.print("[yellow]Nothing to ingest[/yellow]")
        raise typer.Exit(0)
    ids = store.add(texts, metas)
    console.print(f"Ingested {len(ids)} chunks into memory.")


@app.command()
def teach(question: str = typer.Argument(...), answer: str = typer.Argument(...)):
    from .memory import MemoryStore
    store = MemoryStore()
    store.add([f"Q: {question}\nA: {answer}"], [{"type": "qa"}])
    console.print("Stored teaching example in memory.")


@app.command()
def models_download(
    repo_id: str = typer.Option(..., help="Hugging Face repo id for GGUF model"),
    filename: str = typer.Option(..., help="Model filename inside the repo (e.g., model.Q4_K_M.gguf)"),
):
    from huggingface_hub import hf_hub_download

    DEFAULT_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    console.print("Downloading model (this may take a while)...")
    path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=DEFAULT_MODELS_DIR)
    console.print(f"Downloaded to: [bold]{path}[/bold]")


def _chunk_text(text: str, max_len: int = 1200, overlap: int = 200):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_len)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def main():  # console script entry
    app()


if __name__ == "__main__":
    main()
