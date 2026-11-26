"""Render the profile's SVG assets: the banner, section headings, link pills
and the footer, each in a dark and a light variant.

Text uses GitHub's own system font stacks (see svgkit.py), so the art reads
as part of the page rather than pasted onto it.

    python tools/build.py      # fontTools, if installed, sharpens measuring

The live activity card is drawn by stats.py, which a daily workflow runs.

Colours are GitHub's own Primer palette (see svgkit.py).
"""

import random
import re
from pathlib import Path

from svgkit import (
    MONO, MONO_MED, MONO_STACK, OUT, PALETTES, SANS, SANS_SEMI, SANS_STACK,
    card, num, ridge, ridge_path, svg, text,
)


def banner(theme):
    p = PALETTES[theme]
    W, H = 1280, 420
    # Text lines up with the page column, like the pills and strip below it.
    pad = 6
    parts = []

    # No panel of its own: the page's background shows through, so the banner
    # reads as part of the profile. The hills fade out towards the text column
    # and towards the bottom edge instead of being cut off by a frame.
    parts.append(
        "<defs>"
        '<linearGradient id="fade-x" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset="0.12" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="0.88" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="fade-y" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0.8" stop-color="#fff" stop-opacity="1"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<mask id="hills-x" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="url(#fade-x)"/></mask>'
        f'<mask id="hills-y" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="url(#fade-y)"/></mask>'
        "</defs>"
    )
    parts.append('<g mask="url(#hills-y)"><g mask="url(#hills-x)">')

    # Three ridges, far to near, each lower and denser, the way haze works over
    # real hills. The motes above them take the contribution-graph green.
    layers = [
        (7, H - 120, 120, p["accent"], 0.08 if theme == "dark" else 0.07),
        (3, H - 70, 110, p["accent"], 0.12 if theme == "dark" else 0.10),
        (11, H - 22, 90, p["bone"], 0.06 if theme == "dark" else 0.05),
    ]
    for i, (seed, base, amp, colour, op) in enumerate(layers):
        pts = ridge(seed, 0, W + 40, base, amp)
        drift = ("ridge-far", "ridge-mid", "ridge-near")[i]
        parts.append(
            f'<path class="{drift}" d="{ridge_path(pts, H + 4)}" fill="{colour}" fill-opacity="{op}"/>'
        )
    parts.append("</g></g>")

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
    parts.append(text(MONO, "SOFTWARE ENGINEER · ML / GEN AI", 16, pad, 78, p["muted"], tracking=0.16))
    parts.append(text(MONO, "BOSTON, MA", 16, W - pad, 78, p["muted"], tracking=0.16, anchor="end"))

    # Name: one run of text, so the gap between the words is the font's own
    # and nothing depends on knowing how wide "Samarth" is.
    parts.append(
        f'<text x="{pad - 4}" y="214" font-family="{SANS_STACK}" font-size="104" letter-spacing="-2.5">'
        f'<tspan font-weight="600" fill="{p["bone"]}">Samarth</tspan> '
        f'<tspan font-weight="300" fill="{p["accent"]}">Galchar</tspan></text>'
    )

    # Tagline.
    parts.append(text(SANS, "Full-stack products and applied machine learning,", 28, pad, 272, p["muted"]))
    parts.append(text(SANS, "and most of what I build sits between the two.", 28, pad, 310, p["muted"]))

    # Status line with a breathing dot.
    sy = 368
    parts.append(f'<circle cx="{pad + 5}" cy="{sy - 5}" r="9" fill="{p["accent"]}" class="halo"/>')
    parts.append(f'<circle cx="{pad + 5}" cy="{sy - 5}" r="5" fill="{p["accent"]}"/>')
    parts.append(
        f'<text x="{pad + 24}" y="{sy}" font-family="{MONO_STACK}" font-size="15" letter-spacing="2.4">'
        f'<tspan font-weight="600" fill="{p["bone"]}">OPEN TO FULL-TIME ROLES</tspan>'
        f'<tspan fill="{p["muted"]}"> · M.S. CS, NORTHEASTERN &#8217;26</tspan></text>'
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
    parts.append(text(MONO_MED, index, 14, 0, base - 2, p["head_accent"], tracking=0.1))
    parts.append(text(SANS_SEMI, title, 30, 36, base, p["head_text"]))
    # Measured against Segoe UI; the margin absorbs wider system fonts.
    x = 36 + SANS_SEMI.measure(title, 30) * 1.08 + 20
    parts.append(
        f'<line x1="{num(x)}" y1="{base - 10}" x2="{W}" y2="{base - 10}" '
        f'stroke="{p["head_text"]}" stroke-opacity="{0.22 if theme == "dark" else 0.25}" stroke-width="1.5"/>'
    )
    parts.append(f'<circle cx="{num(x)}" cy="{base - 10}" r="3" fill="{p["head_accent"]}"/>')
    return svg(W, H, "".join(parts), title)


def pill(theme, label):
    p = PALETTES[theme]
    size, track = 14, 0.14
    text_w = MONO_MED.measure(label, size, track)
    arrow = 16
    W = int(text_w + arrow + 14 + 2 * 26)
    H = 48
    parts = [
        f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="{(H - 1.5) / 2}" '
        f'fill="{p["ink"]}" stroke="{p["accent"]}" stroke-opacity="0.55" stroke-width="1.5"/>'
    ]
    parts.append(text(MONO_MED, label, size, 26, 29, p["bone"], tracking=track))
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
        parts.append(text(MONO_MED, when, 13, x - 6, line_y - 20, accent, tracking=0.1))
        if last:
            parts.append(f'<circle cx="{x}" cy="{line_y}" r="11" fill="{accent}" fill-opacity="0.2" class="halo"/>')
        parts.append(
            f'<circle cx="{x}" cy="{line_y}" r="5.5" fill="{accent if last else PALETTES[theme]["head_text"]}" '
            f'fill-opacity="{1 if last else 0.85}"/>'
        )
        parts.append(text(SANS_SEMI, where, 22, x - 6, line_y + 46, ink))
        parts.append(text(MONO, what, 11.5, x - 6, line_y + 70, ink, tracking=0.08, opacity=0.7))
    style = (
        ".halo{animation:breathe 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
        "@keyframes breathe{0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1.3)}}"
    )
    title = "Timeline: " + "; ".join(f"{a} {b}, {c.lower()}" for a, b, c in TIMELINE)
    return svg(W, H, "".join(parts), title, style)


SECTIONS = [
    ("experience", "01", "Path so far"),
    ("activity", "02", "On GitHub"),
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
