"""Shared pieces for the profile art: palettes, text, cards and the ridge
generator.

Text is real SVG <text> set in GitHub's own font stacks, so each visitor sees
the same system font the rest of GitHub uses (Segoe UI on Windows, San
Francisco on macOS and iOS, Noto Sans or similar on Linux and Android).

Layout sometimes needs to know how wide a run of text is, for example where
a heading's rule starts. Widths are measured against Segoe UI and Consolas
when they are installed, and otherwise estimated. System fonts differ by a
few percent, so everything placed after measured text leaves room for that.
"""

from __future__ import annotations

import math
import random
from functools import lru_cache
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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

# The same stacks github.com uses for its UI and for code.
SANS_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO_STACK = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


class Font:
    def __init__(self, family: str, weight: int, measure_file: str | None, fallback_em: float):
        self.family = family
        self.weight = weight
        self.measure_file = measure_file
        self.fallback_em = fallback_em

    def measure(self, s: str, size: float, tracking: float = 0.0) -> float:
        widths = _advances(self.measure_file)
        if widths is None:
            base = len(s) * self.fallback_em * size
        else:
            cmap, hmtx, upem = widths
            base = sum(hmtx.get(cmap.get(ord(c), ".notdef"), (upem * self.fallback_em,))[0] for c in s) * size / upem
        return base + tracking * size * max(len(s) - 1, 0)


@lru_cache(maxsize=None)
def _advances(filename: str | None):
    """Advance widths from a locally installed font, or None if unavailable."""
    if not filename:
        return None
    path = Path("C:/Windows/Fonts") / filename
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    if not path.exists():
        return None
    tt = TTFont(path, lazy=True)
    hmtx = {k: v for k, v in tt["hmtx"].metrics.items()}
    return tt.getBestCmap(), hmtx, tt["head"].unitsPerEm


SANS = Font(SANS_STACK, 400, "segoeui.ttf", 0.55)
SANS_LIGHT = Font(SANS_STACK, 300, "segoeuil.ttf", 0.53)
SANS_SEMI = Font(SANS_STACK, 600, "seguisb.ttf", 0.57)
# Monospace is estimated at 0.6em, the widest of the common system monos
# (SF Mono, Menlo), so nothing placed after it can collide on any platform.
MONO = Font(MONO_STACK, 400, None, 0.6)
MONO_MED = Font(MONO_STACK, 600, None, 0.6)

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def num(v: float) -> str:
    s = f"{v:.1f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def svg(w, h, body, title, style=""):
    style_block = f"<style>{style}{REDUCED_MOTION}</style>" if style else ""
    t = escape(title)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{t}"><title>{t}</title>{style_block}{body}</svg>\n'
    )


def text(font: Font, s, size, x, y, fill, tracking=0.0, anchor="start", opacity=None):
    attrs = [
        f'x="{num(x)}" y="{num(y)}"',
        f'font-family="{font.family}"',
        f'font-size="{num(size)}"',
        f'font-weight="{font.weight}"',
        f'fill="{fill}"',
    ]
    if tracking:
        attrs.append(f'letter-spacing="{num(tracking * size)}"')
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if opacity is not None:
        attrs.append(f'fill-opacity="{opacity}"')
    return f"<text {' '.join(attrs)}>{escape(s)}</text>"


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
