"""Shared pieces for the profile art: palettes, text-to-outline shaping and
the ridge generator. See build.py for why text is drawn as outlines."""

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
OUT.mkdir(exist_ok=True)

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


def card(p, w, h, radius=18):
    """Background and hairline for a self-coloured panel, like the banner's."""
    return (
        f'<rect width="{w}" height="{h}" rx="{radius}" fill="{p["ink"]}"/>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{radius - 0.5}" fill="none" '
        f'stroke="{p["line"]}" stroke-opacity="{p["line_op"]}"/>'
    )


def text(face, s, size, x, y, fill, tracking=0.0, anchor="start", opacity=None):
    d, _ = face.path(s, size, x, y, tracking=tracking, anchor=anchor)
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    return f'<path d="{d}" fill="{fill}"{op}/>'
