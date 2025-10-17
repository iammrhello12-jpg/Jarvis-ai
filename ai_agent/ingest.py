from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

import requests
from bs4 import BeautifulSoup

from .memory import TfidfMemory, MemoryEntry


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_chars, n)
        chunks.append(text[i:end])
        i = end - overlap
        if i < 0:
            i = 0
    return chunks


def ingest_files(memory: TfidfMemory, paths: Iterable[str]) -> int:
    entries: List[MemoryEntry] = []
    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        txt = path.read_text(encoding="utf-8", errors="ignore")
        for c in chunk_text(txt):
            entries.append(MemoryEntry(text=c, meta={"source": str(path), "text": c}))
    return memory.add(entries)


def ingest_url(memory: TfidfMemory, url: str) -> int:
    try:
        r = requests.get(url, timeout=20)
    except Exception:
        return 0
    if r.status_code != 200:
        return 0
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = "\n".join(t.strip() for t in soup.stripped_strings)
    entries = [MemoryEntry(text=c, meta={"source": url, "text": c}) for c in chunk_text(text)]
    return memory.add(entries)


def save_training_example(path: str, prompt: str, response: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"prompt": prompt, "response": response}, ensure_ascii=False) + "\n")
