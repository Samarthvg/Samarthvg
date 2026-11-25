"""Render the profile's SVG assets: the banner, section headings, link pills
and the footer, each in a dark and a light variant.

GitHub serves SVGs through <img>, which cannot load web fonts, so every piece
of text is shaped with HarfBuzz and written out as outlines. The result looks
the same on every machine and needs nothing at view time.

    pip install fonttools uharfbuzz
    python tools/build.py

Fonts are read from tools/fonts (git-ignored). They are OFL and come from
github.com/google/fonts: ofl/instrumentserif/InstrumentSerif-Regular.ttf,
ofl/instrumentserif/InstrumentSerif-Italic.ttf and
ofl/jetbrainsmono/JetBrainsMono[wght].ttf (saved as JetBrainsMono.ttf).

Colours match samarthvg.github.io (src/index.css in that repo).
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

PALETTES = {
    "dark": {
        "ink": "#141310",
        "panel": "#1B1915",
        "raised": "#23201B",
        "bone": "#DCD6C9",
        "muted": "#9B968D",
        "accent": "#BAA276",
        "accent2": "#8294AA",
        "line": "#DCD6C9",
        "line_op": 0.13,
        # Section headings sit on GitHub's own page, not on ours.
        "head_text": "#DCD6C9",
        "head_accent": "#BAA276",
    },
    "light": {
        "ink": "#E4DCCB",
        "panel": "#DDD4C1",
        "raised": "#D5CBB5",
        "bone": "#3C362E",
        "muted": "#524B40",
        "accent": "#6A511E",
        "accent2": "#42576E",
        "line": "#3C362E",
        "line_op": 0.15,
        "head_text": "#3C362E",
        "head_accent": "#6A511E",
    },
}


def num(v: float) -> str:
    s = f"{v:.1f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


class Face:
    def __init__(self, filename: str, wght: float | None = None):
        path = FONTS / filename
        self.tt = TTFont(path)
        self.upem = self.tt["head"].unitsPerEm
        self.hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        location = {}
        if wght is not None:
            self.hb_font.set_variations({"wght": wght})
            location = {"wght": wght}
        self.glyphs = self.tt.getGlyphSet(location=location or None)
        self.order = self.tt.getGlyphOrder()

    def measure(self, text: str, size: float, tracking: float = 0.0) -> float:
        return self._shape(text, size, tracking)[1]

    def _shape(self, text, size, tracking):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": True})
        scale = size / self.upem
        placed, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            placed.append((self.order[info.codepoint], x + pos.x_offset * scale, pos.y_offset * scale))
            x += pos.x_advance * scale + tracking * size
        width = x - (tracking * size if placed else 0)
        return placed, width, scale

    def path(self, text, size, x, y, tracking=0.0, anchor="start") -> tuple[str, float]:
        """Return (path data, advance width) for text whose baseline starts at (x, y)."""
        placed, width, scale = self._shape(text, size, tracking)
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        pen = SVGPathPen(self.glyphs, ntos=num)
        for name, gx, gy in placed:
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + gx, y - gy)))
        return pen.getCommands(), width


SERIF = Face("InstrumentSerif-Regular.ttf")
SERIF_IT = Face("InstrumentSerif-Italic.ttf")
MONO = Face("JetBrainsMono.ttf", wght=450)
MONO_MED = Face("JetBrainsMono.ttf", wght=550)

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def svg(w, h, body, title, style=""):
    style_block = f"<style>{style}{REDUCED_MOTION}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{title}"><title>{title}</title>{style_block}{body}</svg>\n'
    )


def ridge(seed, x0, x1, base, amp, step=5, octaves=((430, 1.0), (180, 0.42), (75, 0.1))):
    """A smooth mountain line from x0 to x1, built from a few sine octaves."""
    rnd = random.Random(seed)
    phases = [(wl, a, rnd.uniform(0, math.tau)) for wl, a in octaves]
    pts = []
    x = x0
    while x <= x1 + step:
        # The broadest octave is folded (1 - 2|sin|) so the hills come to
        # peaks instead of rolling like waves.
        y = 0.0
        for k, (wl, a, ph) in enumerate(phases):
            s = math.sin(x / wl * math.tau / (2 if k == 0 else 1) + ph)
            y += a * ((1 - 2 * abs(s)) if k == 0 else s)
        pts.append((x, base - amp * (0.5 + 0.5 * y / sum(a for _, a, _ in phases))))
        x += step
    return pts


def ridge_path(pts, floor):
    d = f"M{num(pts[0][0])} {num(floor)}L" + " ".join(f"{num(x)} {num(y)}" for x, y in pts)
    return d + f"L{num(pts[-1][0])} {num(floor)}Z"


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
    d, _ = MONO_MED.path("OPEN TO FULL-TIME ROLES", 16, pad + 24, sy, tracking=0.2)
    parts.append(f'<path d="{d}" fill="{p["bone"]}"/>')

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
    W, H = 840, 84
    base = 58
    parts = []
    d, wi = MONO_MED.path(index, 17, 0, base - 4, tracking=0.12)
    parts.append(f'<path d="{d}" fill="{p["head_accent"]}"/>')
    d, wt = SERIF.path(title, 50, 48, base)
    parts.append(f'<path d="{d}" fill="{p["head_text"]}"/>')
    x = 48 + wt + 28
    parts.append(
        f'<line x1="{num(x)}" y1="{base - 13}" x2="{W}" y2="{base - 13}" '
        f'stroke="{p["head_text"]}" stroke-opacity="{0.22 if theme == "dark" else 0.25}" stroke-width="1.5"/>'
    )
    parts.append(f'<circle cx="{num(x)}" cy="{base - 13}" r="3.5" fill="{p["head_accent"]}"/>')
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


SECTIONS = [
    ("now", "01", "Now building"),
    ("work", "02", "Selected work"),
    ("research", "03", "Research"),
    ("experience", "04", "Experience"),
    ("toolbox", "05", "Toolbox"),
    ("offclock", "06", "Off the clock"),
]

PILLS = [("portfolio", "PORTFOLIO"), ("linkedin", "LINKEDIN"), ("resume", "RÉSUMÉ")]


def main():
    for theme in PALETTES:
        files = {f"banner-{theme}.svg": banner(theme), f"footer-{theme}.svg": footer(theme)}
        for slug, idx, title in SECTIONS:
            files[f"h-{slug}-{theme}.svg"] = heading(theme, idx, title)
        for slug, label in PILLS:
            files[f"pill-{slug}-{theme}.svg"] = pill(theme, label)
        for name, body in files.items():
            (OUT / name).write_text(body, encoding="utf-8")
    print("wrote", len(list(OUT.glob("*.svg"))), "svgs")


if __name__ == "__main__":
    main()
