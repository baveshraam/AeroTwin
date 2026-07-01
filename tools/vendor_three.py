"""Vendor Three.js locally so the 3D twin runs OFFLINE (Pi in airplane mode, ITAR hangar).

Downloads the UMD build + OrbitControls into src/l1_twin/static/vendor/ once, while you
have a network. After that the dashboard needs no internet — the whole point of an edge
twin. Pinned to r128 (classic global-`THREE` UMD, works with plain <script> tags, no
build step).

    python tools/vendor_three.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / "src" / "l1_twin" / "static" / "vendor"
FILES = {
    "three.min.js": "https://unpkg.com/three@0.128.0/build/three.min.js",
    "OrbitControls.js": "https://unpkg.com/three@0.128.0/examples/js/controls/OrbitControls.js",
}


def main() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = VENDOR / name
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  ok (cached): {name}")
            continue
        try:
            print(f"  downloading {name} ...")
            with urllib.request.urlopen(url, timeout=30) as r:
                dest.write_bytes(r.read())
            print(f"  saved {name} ({dest.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  ! failed {name}: {e}\n    grab it manually from {url} -> {dest}")
            sys.exit(1)
    print(f"\nVendored into {VENDOR}. The 3D twin now runs offline.")


if __name__ == "__main__":
    main()
