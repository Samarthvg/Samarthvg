"""Render the profile's SVG assets: the banner, section headings, link pills
and the footer, each in a dark and a light variant.

GitHub serves SVGs through <img>, which cannot load web fonts, so every piece
of text is shaped with HarfBuzz and written out as outlines. The result looks
the same on every machine and needs nothing at view time.

    pip install fonttools uharfbuzz
    python tools/build.py

Fonts live in tools/fonts: Instrument Serif and JetBrains Mono, both under
the SIL Open Font License (texts alongside them).

The live activity card is drawn by stats.py, which a daily workflow runs.

Colours match samarthvg.github.io (src/index.css in that repo).
"""

import random
import re
from pathlib import Path

from svgkit import (
    MONO, MONO_MED, OUT, PALETTES, SERIF, SERIF_IT, card, num, ridge, ridge_path, svg, text,
)


def banner(theme):
    p = PALETTES[theme]
    W, H = 1280, 420
    pad = 64
    parts = []

    parts.append(
        "<defs>"
        f'<radialGradient id="glow" cx="0.82" cy="0.18" r="0.7">'
        f'<stop offset="0" stop-color="{p["accent"]}" stop-opacity="{0.14 if theme == "dark" else 0.16}"/>'
        f'<stop offset="1" stop-color="{p["accent"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="fade" x1="0" x2="1" y1="0" y2="0">'
        f'<stop offset="0" stop-color="{p["ink"]}" stop-opacity="1"/>'
        f'<stop offset="0.42" stop-color="{p["ink"]}" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
        "</defs>"
    )
    parts.append('<g clip-path="url(#card)">')
    parts.append(f'<rect width="{W}" height="{H}" fill="{p["ink"]}"/>')
    parts.append(f'<rect width="{W}" height="{H}" fill="url(#glow)"/>')

    # Three ridges, far to near. Each nearer one is darker and lower, the way
    # haze works over real hills; they are drawn in the accent pigments rather
    # than grey so they stay part of the same warm picture.
    layers = [
        (7, H - 120, 120, p["accent2"], 0.10 if theme == "dark" else 0.13),
        (3, H - 70, 110, p["accent"], 0.13 if theme == "dark" else 0.16),
        (11, H - 22, 90, p["bone"], 0.07 if theme == "dark" else 0.08),
    ]
    for i, (seed, base, amp, colour, op) in enumerate(layers):
        pts = ridge(seed, 0, W + 40, base, amp)
        drift = ("ridge-far", "ridge-mid", "ridge-near")[i]
        parts.append(
            f'<path class="{drift}" d="{ridge_path(pts, H + 4)}" fill="{colour}" fill-opacity="{op}"/>'
        )
    # Let the hills dissolve before they reach the text column.
    parts.append(f'<rect width="{W}" height="{H}" fill="url(#fade)"/>')

    # Motes drifting up off the hills.
    rnd = random.Random(42)
    for i in range(14):
        x = rnd.uniform(620, W - 40)
        y = rnd.uniform(H - 150, H - 30)
        r = rnd.uniform(1.2, 2.6)
        dur = rnd.uniform(9, 16)
        delay = -rnd.uniform(0, dur)
        colour = p["accent2"] if i % 3 else p["accent"]
        parts.append(
            f'<circle class="mote" cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="{colour}" '
            f'style="animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s"/>'
        )

    # Top row.
    d, _ = MONO.path("SOFTWARE ENGINEER  ·  ML / GEN AI", 17, pad, 78, tracking=0.22)
    parts.append(f'<path d="{d}" fill="{p["muted"]}"/>')
    d, _ = MONO.path("BOSTON, MA", 17, W - pad, 78, tracking=0.22, anchor="end")
    parts.append(f'<path d="{d}" fill="{p["muted"]}"/>')

    # Name.
    size = 132
    d1, w1 = SERIF.path("Samarth", size, pad - 4, 222)
    gap = size * 0.24
    d2, _ = SERIF_IT.path("Galchar", size, pad - 4 + w1 + gap, 222)
    parts.append(f'<path d="{d1}" fill="{p["bone"]}"/>')
    parts.append(f'<path d="{d2}" fill="{p["accent"]}"/>')

    # Tagline.
    d, _ = SERIF_IT.path(
        "Full-stack products and applied machine learning,", 32, pad, 284
    )
    parts.append(f'<path d="{d}" fill="{p["muted"]}"/>')
    d, _ = SERIF_IT.path("and most of what I build sits between the two.", 32, pad, 324)
    parts.append(f'<path d="{d}" fill="{p["muted"]}"/>')

    # Status line with a breathing dot.
    sy = 372
    parts.append(f'<circle cx="{pad + 5}" cy="{sy - 5}" r="9" fill="{p["accent"]}" class="halo"/>')
    parts.append(f'<circle cx="{pad + 5}" cy="{sy - 5}" r="5" fill="{p["accent"]}"/>')
    d, w = MONO_MED.path("OPEN TO FULL-TIME ROLES", 16, pad + 24, sy, tracking=0.2)
    parts.append(f'<path d="{d}" fill="{p["bone"]}"/>')
    d, _ = MONO.path("·  M.S. CS, NORTHEASTERN '26", 16, pad + 24 + w + 18, sy, tracking=0.2)
    parts.append(f'<path d="{d}" fill="{p["muted"]}"/>')

    parts.append("</g>")
    parts.append(
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="17.5" fill="none" '
        f'stroke="{p["line"]}" stroke-opacity="{p["line_op"]}"/>'
    )

    style = (
        ".mote{animation:rise linear infinite;transform-box:fill-box}"
        "@keyframes rise{0%{transform:translateY(0);opacity:0}15%{opacity:.9}"
        "85%{opacity:.6}100%{transform:translateY(-150px);opacity:0}}"
        ".halo{animation:breathe 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
        "@keyframes breathe{0%,100%{opacity:.08;transform:scale(.7)}50%{opacity:.3;transform:scale(1.25)}}"
        ".ridge-far{animation:sway 26s ease-in-out infinite alternate}"
        ".ridge-mid{animation:sway 20s ease-in-out infinite alternate-reverse}"
        "@keyframes sway{to{transform:translateX(-18px)}}"
    )
    return svg(W, H, "".join(parts), "Samarth Galchar, software engineer, ML and generative AI", style)


def heading(theme, index, title):
    p = PALETTES[theme]
    # 840 wide is roughly GitHub's README column, so on desktop the heading
    # draws near 1:1, and on a phone it shrinks far less than a 1280 one would.
    W, H = 840, 66
    base = 46
    parts = []
    d, wi = MONO_MED.path(index, 15, 0, base - 3, tracking=0.12)
    parts.append(f'<path d="{d}" fill="{p["head_accent"]}"/>')
    d, wt = SERIF.path(title, 40, 42, base)
    parts.append(f'<path d="{d}" fill="{p["head_text"]}"/>')
    x = 42 + wt + 24
    parts.append(
        f'<line x1="{num(x)}" y1="{base - 11}" x2="{W}" y2="{base - 11}" '
        f'stroke="{p["head_text"]}" stroke-opacity="{0.22 if theme == "dark" else 0.25}" stroke-width="1.5"/>'
    )
    parts.append(f'<circle cx="{num(x)}" cy="{base - 11}" r="3" fill="{p["head_accent"]}"/>')
    return svg(W, H, "".join(parts), title)


def pill(theme, label):
    p = PALETTES[theme]
    size, track = 15, 0.18
    text_w = MONO_MED.measure(label, size, track)
    arrow = 16
    W = int(text_w + arrow + 14 + 2 * 26)
    H = 48
    parts = [
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="{(H - 1.5) / 2}" '
        f'fill="{p["ink"]}" stroke="{p["accent"]}" stroke-opacity="0.55" stroke-width="1.5"/>'
    ]
    d, _ = MONO_MED.path(label, size, 26, 29.5, tracking=track)
    parts.append(f'<path d="{d}" fill="{p["bone"]}"/>')
    ax = 26 + text_w + 14
    parts.append(
        f'<path d="M{num(ax)} {H / 2 + 6}L{num(ax + 11)} {H / 2 - 5}M{num(ax + 2)} {H / 2 - 5}H{num(ax + 11)}V{H / 2 + 4}" '
        f'fill="none" stroke="{p["accent"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return svg(W, H, "".join(parts), label)


def footer(theme):
    p = PALETTES[theme]
    W, H = 1280, 120
    # Fade both ends so the strip reads as a horizon, not a pasted block.
    parts = [
        '<defs><linearGradient id="edge" x1="0" x2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.25" stop-color="#fff"/><stop offset="0.75" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#edge)"/></mask></defs>'
        '<g mask="url(#m)">'
    ]
    for seed, base, amp, colour, op in (
        (5, 96, 70, p["head_accent"], 0.2),
        (9, 120, 45, p["head_text"], 0.1),
    ):
        parts.append(
            f'<path d="{ridge_path(ridge(seed, 0, W, base, amp), H)}" fill="{colour}" fill-opacity="{op}"/>'
        )
    parts.append("</g>")
    return svg(W, H, "".join(parts), "")


# Logos are Simple Icons (CC0), saved in tools/icons. Order is roughly how
# much of the work above each one carries.
STACK = [
    ("python", "Python"), ("typescript", "TypeScript"), ("javascript", "JavaScript"),
    ("react", "React"), ("nodedotjs", "Node.js"), ("fastapi", "FastAPI"),
    ("pytorch", "PyTorch"), ("tensorflow", "TensorFlow"), ("langchain", "LangChain"),
    ("postgresql", "PostgreSQL"), ("mongodb", "MongoDB"), ("docker", "Docker"),
    ("googlecloud", "Google Cloud"), ("amazonwebservices", "AWS"), ("cloudflare", "Cloudflare"),
    ("git", "Git"),
]
ICONS = Path(__file__).resolve().parent / "icons"


def stack(theme):
    p = PALETTES[theme]
    W, H, pad, icon = 840, 76, 30, 26
    cell = (W - 2 * pad) / len(STACK)
    parts = [card(p, W, H, radius=14)]
    for i, (slug, _) in enumerate(STACK):
        d = re.search(r' d="([^"]+)"', (ICONS / f"{slug}.svg").read_text(encoding="utf-8")).group(1)
        x = pad + i * cell + (cell - icon) / 2
        y = (H - icon) / 2
        parts.append(
            f'<path transform="translate({num(x)} {num(y)}) scale({icon / 24})" d="{d}" '
            f'fill="{p["accent"] if i < 3 else p["bone"]}" fill-opacity="{1 if i < 3 else 0.8}"/>'
        )
    return svg(W, H, "".join(parts), "Stack: " + ", ".join(n for _, n in STACK))


TIMELINE = [
    ("2020", "Charotar Univ.", "ML RESEARCH INTERN"),
    ("2022–23", "Simform", "FULL STACK DEVELOPER"),
    ("2025–26", "Cognitus", "FULL STACK INTERN"),
    ("2026", "Northeastern", "M.S. COMPUTER SCIENCE"),
]


def timeline(theme):
    p = PALETTES[theme]
    W, H = 840, 150
    line_y, step = 52, 210
    ink, accent = p["head_text"], p["head_accent"]
    parts = [
        f'<line x1="6" y1="{line_y}" x2="{3 * step + 6}" y2="{line_y}" stroke="{ink}" stroke-opacity="0.3" stroke-width="1.5"/>',
        # What comes next: the line keeps going, dashed.
        f'<line x1="{3 * step + 6}" y1="{line_y}" x2="{W}" y2="{line_y}" stroke="{accent}" stroke-opacity="0.7" '
        f'stroke-width="1.5" stroke-dasharray="2 7" stroke-linecap="round"/>',
    ]
    for i, (when, where, what) in enumerate(TIMELINE):
        x = i * step + 6
        last = i == len(TIMELINE) - 1
        parts.append(text(MONO_MED, when, 14, x - 6, line_y - 20, accent, tracking=0.1))
        if last:
            parts.append(f'<circle cx="{x}" cy="{line_y}" r="11" fill="{accent}" fill-opacity="0.2" class="halo"/>')
        parts.append(
            f'<circle cx="{x}" cy="{line_y}" r="5.5" fill="{accent if last else PALETTES[theme]["head_text"]}" '
            f'fill-opacity="{1 if last else 0.85}"/>'
        )
        parts.append(text(SERIF, where, 30, x - 6, line_y + 50, ink))
        parts.append(text(MONO, what, 12, x - 6, line_y + 74, ink, tracking=0.1, opacity=0.7))
    style = (
        ".halo{animation:breathe 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
        "@keyframes breathe{0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1.3)}}"
    )
    title = "Timeline: " + "; ".join(f"{a} {b}, {c.lower()}" for a, b, c in TIMELINE)
    return svg(W, H, "".join(parts), title, style)


SECTIONS = [
    ("work", "01", "Selected work"),
    ("experience", "02", "Path so far"),
    ("activity", "03", "On GitHub"),
]

PILLS = [("portfolio", "PORTFOLIO"), ("linkedin", "LINKEDIN"), ("resume", "RÉSUMÉ")]


def main():
    for old in OUT.glob("h-*.svg"):
        old.unlink()
    for theme in PALETTES:
        files = {
            f"banner-{theme}.svg": banner(theme),
            f"footer-{theme}.svg": footer(theme),
            f"timeline-{theme}.svg": timeline(theme),
            f"stack-{theme}.svg": stack(theme),
        }
        for slug, idx, title in SECTIONS:
            files[f"h-{slug}-{theme}.svg"] = heading(theme, idx, title)
        for slug, label in PILLS:
            files[f"pill-{slug}-{theme}.svg"] = pill(theme, label)
        for name, body in files.items():
            (OUT / name).write_text(body, encoding="utf-8")
    print("wrote", len(list(OUT.glob("*.svg"))), "svgs")


if __name__ == "__main__":
    main()
