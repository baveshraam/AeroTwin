"""Dump the twin dashboard to a static HTML file — no FastAPI/uvicorn needed.

    py -m src.pipeline --seed          # populate the twin first
    py tools/render_dashboard.py       # writes data/dashboard_preview.html

Then just double-click data/dashboard_preview.html. Great for a quick screenshot for
the deck before you install the web stack.
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Allow running as a plain script (`py tools/render_dashboard.py`): put the repo
# root on sys.path so the `src` package imports the same as `py -m`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.l1_twin.view import render_home

OUT = Path("data/dashboard_preview.html")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_home(), encoding="utf-8")
    print(f"Wrote {OUT.resolve()}")
    try:
        webbrowser.open(OUT.resolve().as_uri())
    except Exception:
        pass


if __name__ == "__main__":
    main()
