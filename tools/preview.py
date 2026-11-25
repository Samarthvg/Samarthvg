"""Render README.md through GitHub's own Markdown API into preview.html, so the
page can be checked locally (python -m http.server, then open preview.html)
before anything is pushed. Needs an authenticated `gh`.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

md = (ROOT / "README.md").read_text(encoding="utf-8")
html = subprocess.run(
    ["gh", "api", "markdown", "--input", "-"],
    input=json.dumps({"text": md, "mode": "gfm", "context": "Samarthvg/Samarthvg"}).encode(),
    capture_output=True,
    check=True,
).stdout.decode()

page = f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown.css">
<style>
body{{margin:0;background:#fff}}
@media (prefers-color-scheme:dark){{body{{background:#0d1117}}}}
.markdown-body{{box-sizing:border-box;max-width:838px;margin:24px auto;padding:32px;border:1px solid #8884;border-radius:6px}}
@media (max-width:600px){{.markdown-body{{margin:0;padding:16px;border:0}}}}
</style>
<article class="markdown-body">{html}</article>
"""
(ROOT / "preview.html").write_text(page, encoding="utf-8")
print("wrote preview.html")
