"""Draw assets/activity-{dark,light}.svg from live GitHub data.

Standard library only. Run daily by .github/workflows/stats.yml, which commits the result only when
it changes. Locally:

    GH_TOKEN=$(gh auth token) python tools/stats.py

With the workflow's own GITHUB_TOKEN only public repositories are visible. Set
a STATS_TOKEN secret (a fine-grained token with read-only Metadata on all of
your repositories) to count private repositories' languages too. Repository
names never appear in the output, only totals.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from collections import Counter

from svgkit import MONO, MONO_MED, OUT, PALETTES, SANS_LIGHT, card, num, svg, text

LOGIN = os.environ.get("STATS_LOGIN", "Samarthvg")
WEEKS = 16
TOP_LANGUAGES = 5
# A notebook is Python with its outputs saved alongside; counting it as its
# own language mostly measures how many plots were left in the cells.
MERGE = {"Jupyter Notebook": "Python"}

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
      totalRepositoriesWithContributedCommits
    }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes { languages(first: 20) { edges { size node { name color } } } }
    }
  }
}
"""


def graphql(token: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]["user"]


def fetch(token: str) -> dict:
    after, languages, colours, first = None, Counter(), {}, None
    while True:
        user = graphql(token, {"login": LOGIN, "after": after})
        first = first or user
        repos = user["repositories"]
        for repo in repos["nodes"]:
            for edge in repo["languages"]["edges"]:
                raw = edge["node"]["name"]
                name = MERGE.get(raw, raw)
                languages[name] += edge["size"]
                if name == raw and edge["node"]["color"]:
                    colours[name] = edge["node"]["color"]
        if not repos["pageInfo"]["hasNextPage"]:
            break
        after = repos["pageInfo"]["endCursor"]

    collection = first["contributionsCollection"]
    days = [d for w in collection["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in collection["contributionCalendar"]["weeks"]]
    total = sum(languages.values()) or 1
    return {
        "year": collection["contributionCalendar"]["totalContributions"],
        "best_week": max(weekly),
        "repos": collection["totalRepositoriesWithContributedCommits"],
        "weekly": weekly[-WEEKS:],
        # GitHub's own language colours, the ones on every repository page.
        "languages": [(n, s / total, colours.get(n)) for n, s in languages.most_common(TOP_LANGUAGES)],
        "as_of": days[-1]["date"],
    }


def activity(theme: str, s: dict) -> str:
    p = PALETTES[theme]
    W, H = 840, 330
    parts = [card(p, W, H)]
    split = 452
    parts.append(
        f'<line x1="{split}" y1="28" x2="{split}" y2="{H - 28}" stroke="{p["line"]}" stroke-opacity="{p["line_op"]}"/>'
    )

    # Left: three figures, then weekly bars.
    x0 = 32
    figures = [
        (f'{s["year"]:,}', "PAST YEAR"),
        (f'{s["best_week"]:,}', "BUSIEST WEEK"),
        (str(s["repos"]), "REPOS COMMITTED TO"),
    ]
    parts.append(text(MONO, "CONTRIBUTIONS", 12.5, x0, 52, p["muted"], tracking=0.14))
    col = (split - 2 * x0) / 3
    for i, (figure, label) in enumerate(figures):
        x = x0 + i * col
        parts.append(text(SANS_LIGHT, figure, 50, x - 2, 118, p["accent"]))
        parts.append(text(MONO, label, 11, x, 144, p["bone"], tracking=0.1))

    parts.append(text(MONO, f"WEEKLY, LAST {WEEKS} WEEKS", 12.5, x0, 196, p["muted"], tracking=0.14))
    bars_top, bars_bottom = 212, 292
    gap = 4
    bw = (split - 2 * x0 - gap * (WEEKS - 1)) / WEEKS
    peak = max(s["weekly"]) or 1
    graph = p["graph"]
    for i, v in enumerate(s["weekly"]):
        x = x0 + i * (bw + gap)
        if v == 0:
            parts.append(
                f'<rect x="{num(x)}" y="{bars_bottom - 3}" width="{num(bw)}" height="3" rx="1.5" fill="{p["graph_empty"]}"/>'
            )
            continue
        h = max(4, (bars_bottom - bars_top) * (v / peak) ** 0.7)
        level = graph[min(len(graph) - 1, int(len(graph) * v / peak - 1e-9))]
        parts.append(
            f'<rect x="{num(x)}" y="{num(bars_bottom - h)}" width="{num(bw)}" height="{num(h)}" rx="2" fill="{level}"/>'
        )

    # Right: languages by share of code.
    rx = split + 36
    rw = W - rx - 32
    parts.append(text(MONO, "LANGUAGES", 12.5, rx, 52, p["muted"], tracking=0.14))
    row = 46
    top_share = s["languages"][0][1] if s["languages"] else 1
    for i, (name, share, colour) in enumerate(s["languages"]):
        y = 96 + i * row
        parts.append(text(MONO_MED, name, 14, rx, y, p["bone"], tracking=0.02))
        parts.append(text(MONO, f"{share * 100:.0f}%", 14, rx + rw, y, p["muted"], anchor="end"))
        parts.append(
            f'<rect x="{rx}" y="{y + 10}" width="{num(rw)}" height="5" rx="2.5" fill="{p["bone"]}" fill-opacity="0.1"/>'
        )
        parts.append(
            f'<rect x="{rx}" y="{y + 10}" width="{num(max(5, rw * share / top_share))}" height="5" rx="2.5" '
            f'fill="{colour or p["accent"]}"/>'
        )

    stamp = dt.date.fromisoformat(s["as_of"]).strftime("UPDATED %d %b %Y").upper()
    parts.append(text(MONO, stamp, 10.5, W - 32, H - 22, p["muted"], tracking=0.14, anchor="end", opacity=0.8))

    langs = ", ".join(f"{n} {sh * 100:.0f}%" for n, sh, _ in s["languages"])
    title = (
        f'{s["year"]} contributions in the past year, {s["best_week"]} in the busiest week, '
        f'commits to {s["repos"]} repositories. Languages: {langs}.'
    )
    return svg(W, H, "".join(parts), title)


def main():
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    s = fetch(token)
    for theme in PALETTES:
        (OUT / f"activity-{theme}.svg").write_text(activity(theme, s), encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "weekly"}))


if __name__ == "__main__":
    main()
