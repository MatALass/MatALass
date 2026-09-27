#!/usr/bin/env python3
"""Generate self-hosted SVG cards for the GitHub profile README.

Why: third-party card services (github-readme-stats & co.) are rate-limited
and regularly go down, which leaves broken images on the profile. This script
builds the same cards from the GitHub API and the workflow commits them to the
``output`` branch, so the README only points at files we own.

Outputs (inside --out, default ``dist/``):
    cards/<repo>-light.svg, cards/<repo>-dark.svg   one card per featured repo
    langs-light.svg,        langs-dark.svg          most used languages
    kpis-light.svg,         kpis-dark.svg           activity KPIs (12 months)

Standard library only. Needs ``GITHUB_TOKEN`` unless ``--demo`` is passed.

Usage:
    python scripts/generate_cards.py --config scripts/cards.config.json --out dist
    python scripts/generate_cards.py --config scripts/cards.config.json --out dist --demo

Every repo listed under "featured" in the config must be public, otherwise the
API returns 404 and the run fails (on purpose: better a red workflow than a
silently missing card).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from pathlib import Path

API = "https://api.github.com"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "title": "#38bdf8",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "chip_bg": "#0c4a6e",
        "chip_text": "#e0f2fe",
        "tile_bg": "#161b22",
        "accent_from": "#1e3a8a",
        "accent_to": "#06b6d4",
    },
    "light": {
        "bg": "#f8fafc",
        "border": "#e2e8f0",
        "title": "#0369a1",
        "text": "#334155",
        "muted": "#64748b",
        "chip_bg": "#e0f2fe",
        "chip_text": "#075985",
        "tile_bg": "#ffffff",
        "accent_from": "#1e3a8a",
        "accent_to": "#06b6d4",
    },
}

# Linguist colors for the languages likely to show up; unknown ones fall back to grey.
LANG_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "Jupyter Notebook": "#DA5B0B",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Java": "#b07219",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Vue": "#41b883",
    "Game Maker Language": "#71b417",
    "PLpgSQL": "#336790",
    "TSQL": "#e38c00",
    "Shell": "#89e051",
    "PowerShell": "#012456",
    "C": "#555555",
    "C++": "#f34b7d",
    "Dockerfile": "#384d54",
}
DEFAULT_LANG_COLOR = "#8b949e"

# Octicon "star-16" (MIT licensed, github/octicons).
STAR_PATH = (
    "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279"
    "l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75"
    " 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327"
    ".668A.75.75 0 0 1 8 .25Z"
)

CARD_W, CARD_H = 440, 170


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RepoCard:
    repo: str
    title: str
    description: str
    tags: tuple[str, ...]
    language: str | None
    stars: int


@dataclass(frozen=True)
class Kpis:
    contributions: int
    current_streak: int
    longest_streak: int
    public_repos: int


# --------------------------------------------------------------------------- #
# GitHub client
# --------------------------------------------------------------------------- #
class GitHub:
    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-cards-generator",
        }

    def _request(self, method: str, url: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise RuntimeError(f"GitHub API {method} {url} -> {exc.code}: {detail}") from exc

    def rest(self, path: str):
        return self._request("GET", f"{API}{path}")

    def paginate(self, path: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        sep = "&" if "?" in path else "?"
        while True:
            batch = self.rest(f"{path}{sep}per_page=100&page={page}")
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1

    def graphql(self, query: str, variables: dict) -> dict:
        payload = self._request("POST", f"{API}/graphql", {"query": query, "variables": variables})
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL errors: {payload['errors']}")
        return payload["data"]


KPI_QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) { totalCount }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_repo_cards(gh: GitHub, user: str, featured: list[dict]) -> list[RepoCard]:
    cards = []
    for item in featured:
        meta = gh.rest(f"/repos/{user}/{item['repo']}")
        cards.append(
            RepoCard(
                repo=item["repo"],
                title=item.get("title") or meta["name"],
                description=item.get("description") or meta.get("description") or "",
                tags=tuple(item.get("tags", [])),
                language=meta.get("language"),
                stars=int(meta.get("stargazers_count", 0)),
            )
        )
    return cards


def fetch_languages(gh: GitHub, user: str, exclude: set[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in gh.paginate(f"/users/{user}/repos?type=owner"):
        if repo.get("fork") or repo.get("archived") or repo["name"] == user:
            continue
        for lang, size in gh.rest(f"/repos/{user}/{repo['name']}/languages").items():
            if lang not in exclude:
                totals[lang] = totals.get(lang, 0) + int(size)
    return totals


def compute_streaks(days: list[tuple[date, int]], today: date) -> tuple[int, int]:
    """Return (current, longest) streaks of consecutive days with contributions.

    The current streak tolerates an empty *today* (the day is not over yet).
    """
    counts = {d: c for d, c in days}

    longest = run = 0
    for d, c in sorted(days):
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    current = 0
    cursor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def fetch_kpis(gh: GitHub, user: str) -> Kpis:
    data = gh.graphql(KPI_QUERY, {"login": user})["user"]
    calendar = data["contributionsCollection"]["contributionCalendar"]
    days = [
        (date.fromisoformat(day["date"]), int(day["contributionCount"]))
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]
    current, longest = compute_streaks(days, date.today())
    return Kpis(
        contributions=int(calendar["totalContributions"]),
        current_streak=current,
        longest_streak=longest,
        public_repos=int(data["repositories"]["totalCount"]),
    )


# --------------------------------------------------------------------------- #
# SVG rendering
# --------------------------------------------------------------------------- #
def _frame(theme: dict[str, str], label: str, body: str, width: int = CARD_W, height: int = CARD_H) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{theme['accent_from']}"/>
      <stop offset="1" stop-color="{theme['accent_to']}"/>
    </linearGradient>
    <clipPath id="card"><rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10"/></clipPath>
  </defs>
  <g font-family="{FONT}">
    <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{theme['bg']}" stroke="{theme['border']}"/>
    <rect x="0" y="0" width="6" height="{height}" fill="url(#accent)" clip-path="url(#card)"/>
{body}
  </g>
</svg>
"""


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return lines


def render_repo_card(card: RepoCard, theme: dict[str, str]) -> str:
    parts = [
        f'    <text x="24" y="36" font-size="17" font-weight="700" fill="{theme["title"]}">{escape(card.title)}</text>'
    ]
    for i, line in enumerate(_wrap(card.description, width=60, max_lines=3)):
        parts.append(f'    <text x="24" y="{60 + i * 18}" font-size="12.5" fill="{theme["text"]}">{escape(line)}</text>')

    # Tag chips
    x = 24
    for tag in card.tags:
        w = int(len(tag) * 6.4) + 16
        if x + w > CARD_W - 20:
            break
        parts.append(
            f'    <rect x="{x}" y="116" width="{w}" height="20" rx="10" fill="{theme["chip_bg"]}"/>'
            f'<text x="{x + w / 2}" y="130" font-size="11" font-weight="600" text-anchor="middle" fill="{theme["chip_text"]}">{escape(tag)}</text>'
        )
        x += w + 6

    # Footer: language + stars
    fx = 24
    if card.language:
        color = LANG_COLORS.get(card.language, DEFAULT_LANG_COLOR)
        parts.append(f'    <circle cx="{fx + 5}" cy="153" r="5" fill="{color}"/>')
        parts.append(f'    <text x="{fx + 15}" y="157" font-size="12" fill="{theme["muted"]}">{escape(card.language)}</text>')
        fx += 15 + int(len(card.language) * 6.6) + 16
    parts.append(
        f'    <g transform="translate({fx},145)"><path d="{STAR_PATH}" fill="{theme["muted"]}"/></g>'
        f'<text x="{fx + 21}" y="157" font-size="12" fill="{theme["muted"]}">{card.stars}</text>'
    )
    return _frame(theme, f"{card.title}: {card.description}", "\n".join(parts))


def render_languages(totals: dict[str, int], theme: dict[str, str], max_langs: int) -> str:
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:max_langs]
    other = sum(v for _, v in ranked[max_langs:])
    if other:
        top.append(("Other", other))

    parts = [f'    <text x="24" y="36" font-size="17" font-weight="700" fill="{theme["title"]}">Most used languages</text>']

    bar_x, bar_w = 24, CARD_W - 48
    parts.append(f'    <clipPath id="bar"><rect x="{bar_x}" y="52" width="{bar_w}" height="10" rx="5"/></clipPath>')
    parts.append(f'    <g clip-path="url(#bar)">')
    x = float(bar_x)
    for lang, size in top:
        w = bar_w * size / grand
        color = LANG_COLORS.get(lang, DEFAULT_LANG_COLOR)
        parts.append(f'      <rect x="{x:.2f}" y="52" width="{w + 0.5:.2f}" height="10" fill="{color}"/>')
        x += w
    parts.append("    </g>")

    col_w = bar_w / 2
    for i, (lang, size) in enumerate(top):
        col, row = divmod(i, 5)
        lx = bar_x + col * col_w
        ly = 86 + row * 17
        color = LANG_COLORS.get(lang, DEFAULT_LANG_COLOR)
        pct = 100 * size / grand
        parts.append(f'    <circle cx="{lx + 5:.1f}" cy="{ly - 4}" r="5" fill="{color}"/>')
        parts.append(
            f'    <text x="{lx + 16:.1f}" y="{ly}" font-size="12" fill="{theme["text"]}">{escape(lang)} '
            f'<tspan fill="{theme["muted"]}">{pct:.1f}%</tspan></text>'
        )
    return _frame(theme, "Most used languages", "\n".join(parts))


def render_kpis(kpis: Kpis, theme: dict[str, str]) -> str:
    tiles = [
        (f"{kpis.contributions:,}".replace(",", " "), "contributions"),
        (str(kpis.current_streak), "current streak"),
        (str(kpis.longest_streak), "longest streak"),
        (str(kpis.public_repos), "public repos"),
    ]
    parts = [
        f'    <text x="24" y="36" font-size="17" font-weight="700" fill="{theme["title"]}">GitHub activity</text>',
        f'    <text x="{CARD_W - 20}" y="36" font-size="11" text-anchor="end" fill="{theme["muted"]}">last 12 months</text>',
    ]
    gap, left, right = 10, 24, 20
    tile_w = (CARD_W - left - right - gap * (len(tiles) - 1)) / len(tiles)
    for i, (value, label) in enumerate(tiles):
        tx = left + i * (tile_w + gap)
        cx = tx + tile_w / 2
        parts.append(
            f'    <rect x="{tx:.1f}" y="56" width="{tile_w:.1f}" height="92" rx="8" fill="{theme["tile_bg"]}" stroke="{theme["border"]}"/>'
        )
        parts.append(
            f'    <text x="{cx:.1f}" y="106" font-size="26" font-weight="700" text-anchor="middle" fill="{theme["title"]}">{escape(value)}</text>'
        )
        parts.append(
            f'    <text x="{cx:.1f}" y="130" font-size="11" text-anchor="middle" fill="{theme["muted"]}">{escape(label)}</text>'
        )
    return _frame(theme, "GitHub activity over the last 12 months", "\n".join(parts))


# --------------------------------------------------------------------------- #
# Demo data (offline preview)
# --------------------------------------------------------------------------- #
def demo_data(featured: list[dict]) -> tuple[list[RepoCard], dict[str, int], Kpis]:
    cards = [
        RepoCard(
            repo=f["repo"],
            title=f.get("title") or f["repo"],
            description=f.get("description", ""),
            tags=tuple(f.get("tags", [])),
            language="Python",
            stars=i % 3,
        )
        for i, f in enumerate(featured)
    ]
    langs = {"Python": 620_000, "JavaScript": 140_000, "Java": 60_000, "Vue": 30_000, "Game Maker Language": 20_000, "PLpgSQL": 5_000}
    return cards, langs, Kpis(contributions=742, current_streak=5, longest_streak=19, public_repos=42)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=Path("scripts/cards.config.json"))
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--demo", action="store_true", help="use fake data, no network (local preview)")
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    user = config["user"]
    featured = config["featured"]

    if args.demo:
        cards, langs, kpis = demo_data(featured)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN is not set (use --demo for an offline preview).", file=sys.stderr)
            return 1
        gh = GitHub(token)
        cards = fetch_repo_cards(gh, user, featured)
        langs = fetch_languages(gh, user, set(config.get("exclude_languages", [])))
        kpis = fetch_kpis(gh, user)

    for mode, theme in THEMES.items():
        for card in cards:
            write(args.out / "cards" / f"{card.repo}-{mode}.svg", render_repo_card(card, theme))
        write(args.out / f"langs-{mode}.svg", render_languages(langs, theme, config.get("max_languages", 8)))
        write(args.out / f"kpis-{mode}.svg", render_kpis(kpis, theme))

    print(f"Generated {len(cards)} repo cards + languages + KPIs in {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
