"""Load and validate ``profile.config.json``.

Validation is strict on purpose: a typo in the config should fail the workflow
with a clear message, not publish a half-broken header.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .models import Config, FeaturedRepo, Header, Logo, StackItem, Theme

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_STACK_ROWS = 6


class ConfigError(ValueError):
    """Raised when the configuration file is invalid."""


def _require(data: dict, key: str, where: str):
    if key not in data:
        raise ConfigError(f"missing '{key}' in {where}")
    return data[key]


def _color(value: str, where: str) -> str:
    if not isinstance(value, str) or not HEX.match(value):
        raise ConfigError(f"{where} must be a #RRGGBB color, got {value!r}")
    return value


def _theme(data: dict) -> Theme:
    names = ("bg", "panel", "grid", "text", "muted", "primary", "secondary")
    colors = {n: _color(_require(data, n, "theme"), f"theme.{n}") for n in names}
    tiers = {k: _color(v, f"theme.tiers.{k}") for k, v in _require(data, "tiers", "theme").items()}
    ramp = tuple(_color(c, "theme.ramp[]") for c in _require(data, "ramp", "theme"))
    if not tiers:
        raise ConfigError("theme.tiers must define at least one tier")
    if not ramp:
        raise ConfigError("theme.ramp must contain at least one color")
    return Theme(**colors, tiers=tiers, ramp=ramp)


def _header(data: dict, theme: Theme, base_dir: Path) -> Header:
    stack = []
    for i, item in enumerate(_require(data, "stack", "header")):
        where = f"header.stack[{i}]"
        code = str(_require(item, "code", where))
        tier = str(_require(item, "tier", where))
        if len(code) > 4:
            raise ConfigError(f"{where}.code must be at most 4 characters, got {code!r}")
        if tier not in theme.tiers:
            raise ConfigError(f"{where}.tier {tier!r} is not one of {sorted(theme.tiers)}")
        stack.append(StackItem(code=code, name=str(_require(item, "name", where)), tier=tier))
    if not 1 <= len(stack) <= MAX_STACK_ROWS:
        raise ConfigError(f"header.stack must have 1 to {MAX_STACK_ROWS} rows, got {len(stack)}")

    logo = None
    raw_logo = data.get("logo")
    if raw_logo:
        path = base_dir / str(_require(raw_logo, "path", "header.logo"))
        if not path.is_file():
            raise ConfigError(f"header.logo.path points to a missing file: {path}")
        if path.suffix.lower() not in {".svg", ".png"}:
            raise ConfigError("header.logo.path must be a .svg or .png file")
        logo = Logo(
            path=path,
            width=int(_require(raw_logo, "width", "header.logo")),
            height=int(raw_logo.get("height", 18)),
        )

    return Header(
        name=str(_require(data, "name", "header")),
        kicker=str(_require(data, "kicker", "header")),
        subtitle=str(_require(data, "subtitle", "header")),
        availability=str(_require(data, "availability", "header")),
        stack=tuple(stack),
        logo=logo,
    )


def load_config(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    theme = _theme(_require(data, "theme", "config"))
    header = _header(_require(data, "header", "config"), theme, path.parent)

    featured = []
    for i, item in enumerate(_require(data, "featured", "config")):
        where = f"featured[{i}]"
        featured.append(
            FeaturedRepo(
                repo=str(_require(item, "repo", where)),
                title=str(_require(item, "title", where)),
                description=str(_require(item, "description", where)),
                tags=tuple(str(t) for t in item.get("tags", [])),
            )
        )

    return Config(
        user=str(_require(data, "user", "config")),
        header=header,
        theme=theme,
        featured=tuple(featured),
        max_languages=int(data.get("max_languages", 8)),
        exclude_languages=frozenset(data.get("exclude_languages", [])),
    )
