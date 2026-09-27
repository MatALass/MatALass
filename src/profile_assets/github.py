"""Minimal GitHub REST + GraphQL client (standard library only) and the metrics built on it."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, timedelta

from .models import Activity, FeaturedRepo, RepoCard

API = "https://api.github.com"

ACTIVITY_QUERY = """
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


class GitHubError(RuntimeError):
    """Raised when the GitHub API answers with an error."""


class GitHub:
    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "profile-assets",
        }

    def _request(self, method: str, url: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise GitHubError(f"{method} {url} -> {exc.code}: {detail}") from exc

    def rest(self, path: str):
        return self._request("GET", f"{API}{path}")

    def paginate(self, path: str) -> list[dict]:
        items: list[dict] = []
        sep = "&" if "?" in path else "?"
        page = 1
        while True:
            batch = self.rest(f"{path}{sep}per_page=100&page={page}")
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1

    def graphql(self, query: str, variables: dict) -> dict:
        payload = self._request("POST", f"{API}/graphql", {"query": query, "variables": variables})
        if payload.get("errors"):
            raise GitHubError(f"GraphQL errors: {payload['errors']}")
        return payload["data"]


# --------------------------------------------------------------------------- #
# Pure metric helpers (unit-tested)
# --------------------------------------------------------------------------- #
def compute_streaks(days: list[tuple[date, int]], today: date) -> tuple[int, int]:
    """Return (current, longest) runs of consecutive days with contributions.

    An empty *today* does not break the current streak: the day is not over yet.
    """
    counts = dict(days)
    longest = run = 0
    for _, count in sorted(days):
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)

    current = 0
    cursor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def weekly_totals(weeks: list[list[int]], n_weeks: int = 52) -> tuple[int, ...]:
    """Sum each calendar week and keep the most recent ``n_weeks`` (oldest first)."""
    totals = [sum(week) for week in weeks]
    return tuple(totals[-n_weeks:])


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
def fetch_repo_cards(gh: GitHub, user: str, featured: tuple[FeaturedRepo, ...]) -> list[RepoCard]:
    cards = []
    for item in featured:
        meta = gh.rest(f"/repos/{user}/{item.repo}")
        cards.append(
            RepoCard(
                repo=item.repo,
                title=item.title,
                description=item.description,
                tags=item.tags,
                language=meta.get("language"),
                stars=int(meta.get("stargazers_count", 0)),
            )
        )
    return cards


def fetch_languages(gh: GitHub, user: str, exclude: frozenset[str]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in gh.paginate(f"/users/{user}/repos?type=owner"):
        if repo.get("fork") or repo.get("archived") or repo["name"].lower() == user.lower():
            continue
        for lang, size in gh.rest(f"/repos/{user}/{repo['name']}/languages").items():
            if lang not in exclude:
                totals[lang] = totals.get(lang, 0) + int(size)
    return totals


def fetch_activity(gh: GitHub, user: str, today: date | None = None) -> Activity:
    data = gh.graphql(ACTIVITY_QUERY, {"login": user})["user"]
    calendar = data["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    days = [
        (date.fromisoformat(d["date"]), int(d["contributionCount"]))
        for week in weeks
        for d in week["contributionDays"]
    ]
    current, longest = compute_streaks(days, today or date.today())
    return Activity(
        weekly=weekly_totals([[int(d["contributionCount"]) for d in w["contributionDays"]] for w in weeks]),
        contributions=int(calendar["totalContributions"]),
        current_streak=current,
        longest_streak=longest,
        public_repos=int(data["repositories"]["totalCount"]),
    )
