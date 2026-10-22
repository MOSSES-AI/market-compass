#!/usr/bin/env python3
"""Package only public assets; never publish repository internals."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"
DEST.mkdir(exist_ok=True)
for filename in ("index.html", "live.css", "live.js", ".nojekyll"):
    shutil.copy2(ROOT / filename, DEST / filename)
(DEST / "data").mkdir(exist_ok=True)
shutil.copy2(ROOT / "data/live.json", DEST / "data/live.json")
print("Public dashboard built in _site/")
