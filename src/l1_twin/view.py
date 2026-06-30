"""L1 — Dashboard rendering (no web-framework dependency).

Pure-Python HTML/SVG rendering of the per-tail twin so it can be served by FastAPI
(src/l1_twin/app.py) OR dumped to a static file (tools/render_dashboard.py) with no
install. Same view either way.
"""
from __future__ import annotations

from src.l1_twin import db
from src.l2_progress.paris import project_growth

GRADE_COLOR = {
    "minor": "#2e7d32",
    "major": "#f9a825",
    "critical": "#ef6c00",
    "beyond-limit": "#c62828",
    "unknown": "#607d8b",
}


def _limit_from_grade(row: dict) -> float | None:
    try:
        from src.l0_detect.grade import grade_defect
        return grade_defect(row["defect_type"], row["ata_zone"], row["size_mm"]).get("limit_mm")
    except Exception:
        return None


def _sparkline(points: list[tuple[int, float]], limit_mm: float | None, w: int = 240, h: int = 64) -> str:
    if not points:
        return ""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ymax = max(ys + ([limit_mm] if limit_mm else []) + [1.0]) * 1.1
    xmax = max(xs) or 1

    def sx(x): return 6 + (w - 12) * (x / xmax)
    def sy(y): return h - 6 - (h - 12) * (y / ymax)

    poly = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
    dots = "".join(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="2.5" fill="#0a2540"/>' for x, y in points)
    limit_line = ""
    if limit_mm:
        ly = sy(limit_mm)
        limit_line = (
            f'<line x1="6" y1="{ly:.1f}" x2="{w-6}" y2="{ly:.1f}" stroke="#c62828" '
            f'stroke-dasharray="4 3" stroke-width="1"/>'
            f'<text x="{w-4}" y="{ly-3:.1f}" font-size="9" fill="#c62828" text-anchor="end">SRM limit</text>'
        )
    return (
        f'<svg width="{w}" height="{h}" style="background:#fafafa;border:1px solid #eee;border-radius:6px">'
        f'{limit_line}<polyline points="{poly}" fill="none" stroke="#0a2540" stroke-width="2"/>{dots}</svg>'
    )


def render_home() -> str:
    db.init()
    rows = db.all_findings()
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["tail"], r["location"], r["defect_type"]), []).append(r)

    cards = []
    for (tail, location, defect), items in groups.items():
        items.sort(key=lambda x: x["cycles"] or 0)
        latest = items[-1]
        color = GRADE_COLOR.get(latest["grade"], "#607d8b")
        if len(items) >= 2:
            pts = project_growth(items[-2]["size_mm"], latest["size_mm"],
                                 (latest["cycles"] or 0) - (items[-2]["cycles"] or 0))
        else:
            pts = [(0, latest["size_mm"])]
        ctl = latest.get("cycles_to_limit")
        ctl_txt = f"~{ctl} cycles to limit" if ctl else "insufficient data"
        hist_rows = "".join(
            f'<tr><td>{it["scan_date"] or "-"}</td><td>{it["cycles"]}</td>'
            f'<td>{it["size_mm"]} mm</td><td>{it["grade"]}</td></tr>'
            for it in items
        )
        cards.append(f"""
        <div class="card">
          <div class="head" style="border-left:6px solid {color}">
            <div><div class="tail">{tail}</div>
                 <div class="loc">ATA {latest['ata_zone']} &middot; {location} &middot; {defect}</div></div>
            <div class="grade" style="background:{color}">{latest['grade'].upper()}</div>
          </div>
          <div class="body">
            <div class="metric"><b>{latest['size_mm']} mm</b><span>current size</span></div>
            <div class="metric"><b>{ctl_txt}</b><span>progression</span></div>
            {_sparkline(pts, _limit_from_grade(latest))}
          </div>
          <div class="air">{latest['airworthiness'] or ''}</div>
          <table class="hist"><tr><th>Scan</th><th>Cycles</th><th>Size</th><th>Grade</th></tr>{hist_rows}</table>
        </div>""")

    body = "".join(cards) or '<p class="empty">No findings yet. Run <code>py -m src.pipeline --seed</code>.</p>'
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>AeroTwin-Edge - Structural Twin</title>
<style>
  :root{{font-family:-apple-system,Segoe UI,Roboto,sans-serif}}
  body{{margin:0;background:#eef2f6;color:#0a2540}}
  header{{background:#0a2540;color:#fff;padding:18px 28px}}
  header h1{{margin:0;font-size:20px;letter-spacing:.3px}}
  header p{{margin:4px 0 0;opacity:.7;font-size:13px}}
  .wrap{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px;padding:24px 28px}}
  .card{{background:#fff;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
  .head{{display:flex;justify-content:space-between;align-items:center;padding:14px 16px}}
  .tail{{font-weight:700;font-size:17px}} .loc{{font-size:12px;color:#5a6b7b}}
  .grade{{color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px}}
  .body{{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:6px 16px 12px}}
  .metric{{display:flex;flex-direction:column}} .metric b{{font-size:16px}} .metric span{{font-size:11px;color:#5a6b7b}}
  .air{{padding:8px 16px;font-size:12px;color:#37474f;background:#f7f9fb}}
  table.hist{{width:100%;border-collapse:collapse;font-size:12px}}
  table.hist th,table.hist td{{border-top:1px solid #eee;padding:6px 16px;text-align:left}}
  .empty{{padding:40px;text-align:center;color:#5a6b7b}}
</style></head>
<body>
  <header><h1>AeroTwin-Edge &middot; Per-Tail Structural Twin</h1>
  <p>Offline edge inspection &middot; condition-based maintenance &middot; audit-ready</p></header>
  <div class="wrap">{body}</div>
</body></html>"""
