"""Load and validate ``profile.config.json``.

Validation is strict on purpose: a typo in the config should fail the workflow
with a clear message, not publish a half-broken header.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .models import Config, FeaturedRepo, Header, KillFeedEntry, ModelDimension, ModelHeader, StackItem, Theme

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_STACK_SLOTS = 6
MAX_KILL_FEED = 3
HEADER_STYLES = ("racing", "model")
MODEL_DIMENSIONS = 5
MODEL_ROWS = (1, 4)


class ConfigError(ValueError):
    """Raised when the configuration file is invalid."""


def _require(data: dict, key: str, where: str):
    if not isinstance(data, dict) or key not in data:
        raise ConfigError(f"missing '{key}' in {where}")
    return data[key]


def _color(value: str, where: str) -> str:
    if not isinstance(value, str) or not HEX.match(value):
        raise ConfigError(f"{where} must be a #RRGGBB color, got {value!r}")
    return value


def _colors(values, where: str, exact: int | None = None) -> tuple[str, ...]:
    if not isinstance(values, list) or not values:
        raise ConfigError(f"{where} must be a non-empty list of colors")
    if exact is not None and len(values) != exact:
        raise ConfigError(f"{where} must contain exactly {exact} colors")
    return tuple(_color(c, f"{where}[{i}]") for i, c in enumerate(values))


def _theme(data: dict) -> Theme:
    single = {n: _color(_require(data, n, "theme"), f"theme.{n}") for n in ("bg", "panel", "grid", "text", "muted")}
    tiers = {k: _color(v, f"theme.tiers.{k}") for k, v in _require(data, "tiers", "theme").items()}
    if not tiers:
        raise ConfigError("theme.tiers must define at least one tier")
    return Theme(
        **single,
        accents=_colors(_require(data, "accents", "theme"), "theme.accents"),
        tiers=tiers,
        ramp=_colors(_require(data, "ramp", "theme"), "theme.ramp"),
        sky=_colors(_require(data, "sky", "theme"), "theme.sky", exact=2),  # type: ignore[arg-type]
        sun=_colors(_require(data, "sun", "theme"), "theme.sun", exact=3),  # type: ignore[arg-type]
    )


def _header(data: dict, theme: Theme) -> Header:
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
    if not 1 <= len(stack) <= MAX_STACK_SLOTS:
        raise ConfigError(f"header.stack must have 1 to {MAX_STACK_SLOTS} items, got {len(stack)}")

    feed = [
        KillFeedEntry(tool=str(_require(e, "tool", f"header.kill_feed[{i}]")), target=str(_require(e, "target", f"header.kill_feed[{i}]")))
        for i, e in enumerate(data.get("kill_feed", []))
    ]
    if len(feed) > MAX_KILL_FEED:
        raise ConfigError(f"header.kill_feed must have at most {MAX_KILL_FEED} entries")

    raw_date = str(_require(data, "available_from", "header"))
    try:
        available_from = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ConfigError(f"header.available_from must be YYYY-MM-DD, got {raw_date!r}") from exc

    return Header(
        name=str(_require(data, "name", "header")),
        role=str(_require(data, "role", "header")),
        rank=str(_require(data, "rank", "header")),
        available_from=available_from,
        stack=tuple(stack),
        kill_feed=tuple(feed),
    )


def _model(data: dict) -> ModelHeader:
    dims = []
    raw_dims = _require(data, "dimensions", "model")
    if not isinstance(raw_dims, list) or len(raw_dims) != MODEL_DIMENSIONS:
        raise ConfigError(f"model.dimensions must have exactly {MODEL_DIMENSIONS} tables (left, left, right, right, bottom)")
    for i, item in enumerate(raw_dims):
        where = f"model.dimensions[{i}]"
        name = str(_require(item, "name", where))
        if not name.startswith("dim_"):
            raise ConfigError(f"{where}.name must start with 'dim_', got {name!r}")
        rows = _require(item, "rows", where)
        if not isinstance(rows, list) or not MODEL_ROWS[0] <= len(rows) <= MODEL_ROWS[1]:
            raise ConfigError(f"{where}.rows must have {MODEL_ROWS[0]} to {MODEL_ROWS[1]} lines")
        dims.append(ModelDimension(name=name, rows=tuple(str(r) for r in rows)))
    return ModelHeader(
        name=str(_require(data, "name", "model")),
        subtitle=str(_require(data, "subtitle", "model")),
        badge=str(_require(data, "badge", "model")),
        caption=str(data.get("caption", "profile.pbix · model view")),
        fact=str(data.get("fact", "fact_profile")),
        dimensions=tuple(dims),
    )


def load_config(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc

    theme = _theme(_require(data, "theme", "config"))
    header = _header(_require(data, "header", "config"), theme)

    featured = []
    for i, item in enumerate(_require(data, "featured", "config")):
        where = f"featured[{i}]"
        featured.append(
            FeaturedRepo(
                repo=str(_require(item, "repo", where)),
                title=str(_require(item, "title", where)),
                description=str(_require(item, "description", where)),
                tags=tuple(str(t) for t in item.get("tags", [])),
                tech=str(_require(item, "tech", where)),
            )
        )

    style = str(data.get("header_style", "racing"))
    if style not in HEADER_STYLES:
        raise ConfigError(f"header_style must be one of {list(HEADER_STYLES)}, got {style!r}")
    model = _model(data["model"]) if "model" in data else None
    if style == "model" and model is None:
        raise ConfigError("header_style 'model' needs a 'model' block")

    return Config(
        user=str(_require(data, "user", "config")),
        header=header,
        theme=theme,
        featured=tuple(featured),
        max_languages=int(data.get("max_languages", 8)),
        exclude_languages=frozenset(data.get("exclude_languages", [])),
        header_style=style,
        model=model,
    )
