"""Command line entry point: ``python -m profile_assets --config profile.config.json --out dist``."""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .github import GitHub, GitHubError, fetch_activity, fetch_languages, fetch_repo_cards
from .models import Activity, Config, RepoCard
from .header import render_header
from .render import render_languages, render_repo_card


def demo_data(config: Config) -> tuple[list[RepoCard], dict[str, int], Activity]:
    """Deterministic fake data for offline previews and tests."""
    cards = [
        RepoCard(repo=f.repo, title=f.title, description=f.description, tags=f.tags, language="Python", stars=i % 3)
        for i, f in enumerate(config.featured)
    ]
    langs = {"Python": 620_000, "JavaScript": 140_000, "Java": 60_000, "Vue": 30_000, "PLpgSQL": 9_000, "Shell": 4_000}
    weekly = tuple(max(0, round(8 + 7 * math.sin(i / 4.5) + (10 if 30 < i < 40 else 0))) for i in range(52))
    return cards, langs, Activity(weekly=weekly, contributions=sum(weekly), current_streak=5, longest_streak=19, public_repos=42)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="profile_assets", description="Build the SVG assets of the GitHub profile README.")
    parser.add_argument("--config", type=Path, default=Path("profile.config.json"))
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--demo", action="store_true", help="fake data, no network (local preview)")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    if args.demo:
        cards, langs, activity = demo_data(config)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN is not set (use --demo for an offline preview).", file=sys.stderr)
            return 1
        gh = GitHub(token)
        try:
            cards = fetch_repo_cards(gh, config.user, config.featured)
            langs = fetch_languages(gh, config.user, config.exclude_languages)
            activity = fetch_activity(gh, config.user)
        except GitHubError as exc:
            print(f"GitHub API error: {exc}", file=sys.stderr)
            return 1

    write(args.out / "header.svg", render_header(config.header, activity, config.theme))
    for position, card in enumerate(cards, start=1):
        write(args.out / "cards" / f"{card.repo}.svg", render_repo_card(card, position, config.theme))
    write(args.out / "languages.svg", render_languages(langs, config.theme, config.max_languages))

    print(f"Wrote header, {len(cards)} project cards and languages to {args.out}/")
    return 0
