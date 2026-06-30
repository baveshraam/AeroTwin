"""L1 — Digital-twin dashboard (FastAPI wrapper).

The HTML/SVG view lives in src/l1_twin/view.py (no framework dependency) so it can
also be dumped to a static file without installing anything. This module just serves
it over HTTP.

Run:  uvicorn src.l1_twin.app:app --port 8000   ->   http://127.0.0.1:8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.l1_twin.view import render_home

app = FastAPI(title="AeroTwin-Edge - Structural Twin")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return render_home()
