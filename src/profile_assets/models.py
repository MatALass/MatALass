"""Typed data structures shared by the loader, the GitHub client and the renderers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Theme:
    bg: str
    panel: str
    grid: str
    text: str
    muted: str
    accents: tuple[str, ...]  # vivid colors cycled through cards, chips and HUD elements
    tiers: dict[str, str]  # tier name -> color (core / strong / working)
    ramp: tuple[str, ...]  # categorical ramp for the language bar
    sky: tuple[str, str]  # header sky gradient (top, horizon)
    sun: tuple[str, str, str]  # header sun gradient (top, middle, bottom)


@dataclass(frozen=True)
class StackItem:
    code: str  # short code shown in the loadout slot, e.g. "PYT"
    name: str
    tier: str


@dataclass(frozen=True)
class KillFeedEntry:
    tool: str  # e.g. "Python"
    target: str  # e.g. "messy_data.csv"


@dataclass(frozen=True)
class Header:
    name: str
    role: str
    rank: str
    available_from: date
    stack: tuple[StackItem, ...]
    kill_feed: tuple[KillFeedEntry, ...]


@dataclass(frozen=True)
class FeaturedRepo:
    repo: str
    title: str
    description: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    user: str
    header: Header
    theme: Theme
    featured: tuple[FeaturedRepo, ...]
    max_languages: int
    exclude_languages: frozenset[str]


@dataclass(frozen=True)
class RepoCard:
    repo: str
    title: str
    description: str
    tags: tuple[str, ...]
    language: str | None
    stars: int


@dataclass(frozen=True)
class Activity:
    weekly: tuple[int, ...]  # contributions per week, oldest first
    contributions: int
    current_streak: int
    longest_streak: int
    public_repos: int
