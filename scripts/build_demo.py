#!/usr/bin/env python3
"""Build the static demo site: inject curated data into the template.

Usage: python scripts/build_demo.py [output_dir]   (default: _site)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "verifact" / "data"
SITE = ROOT / "site"


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "_site")
    out.mkdir(parents=True, exist_ok=True)

    lists = json.loads((DATA / "source_reputation.json").read_text())
    lists = {k: v for k, v in lists.items() if not k.startswith("_")}
    terms = [
        ln.strip().lower()
        for ln in (DATA / "sensational_terms.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")
    ]

    template = (SITE / "index.template.html").read_text()
    html = template.replace("__SOURCE_LISTS__", json.dumps(lists)).replace(
        "__SENSATIONAL_TERMS__", json.dumps(terms)
    )
    (out / "index.html").write_text(html)
    for extra in SITE.glob("*.png"):
        shutil.copy(extra, out / extra.name)
    print(f"demo built → {out / 'index.html'} ({len(html) // 1024} KiB)")


if __name__ == "__main__":
    main()
