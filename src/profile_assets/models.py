"""Typed data structures shared by the loader, the GitHub client and the renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    bg: str
    panel: str
    grid: str
    text: str
    muted: str
    primary: str  # Alpine-inspired blue
    secondary: str  # Alpine-inspired pink
    tiers: dict[str, str]  # tier name -> color (e.g. core / strong / working)
    ramp: tuple[str, ...]  # categorical ramp for the language bar


@dataclass(frozen=True)
class StackItem:
    code: str  # 3-letter timing-tower code, e.g. "PYT"
    name: str
    tier: str


@dataclass(frozen=True)
class Logo:
    path: Path
    width: int
    height: int


@dataclass(frozen=True)
class Header:
    name: str
    kicker: str
    subtitle: str
    availability: str
    stack: tuple[StackItem, ...]
    logo: Logo | None


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
