import json
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from profile_assets.cli import demo_data, main
from profile_assets.config import ConfigError, load_config
from profile_assets.github import compute_streaks, weekly_totals
from profile_assets.header import days_until, render_header
from profile_assets.models import Activity, RepoCard
from profile_assets.render import render_languages, render_repo_card

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "profile.config.json"
TODAY = date(2026, 9, 27)


def _raw_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "profile.config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG)


# ------------------------------------------------------------------ metrics
def _days(counts):
    """counts[0] is today, counts[1] yesterday, ..."""
    return [(TODAY - timedelta(days=i), c) for i, c in enumerate(counts)]


def test_streak_ignores_empty_today():
    assert compute_streaks(_days([0, 2, 1, 3, 0, 1, 1, 1, 1, 0]), TODAY) == (3, 4)


def test_streak_counts_active_today():
    assert compute_streaks(_days([1, 0]), TODAY) == (1, 1)


def test_streak_zero_when_inactive():
    assert compute_streaks(_days([0, 0, 0]), TODAY) == (0, 0)


def test_weekly_totals_keeps_last_weeks_oldest_first():
    weeks = [[1] * 7 for _ in range(50)] + [[0, 1, 0, 0, 0, 0, 2], [3]]
    assert weekly_totals(weeks, n_weeks=3) == (7, 3, 3)


def test_days_until():
    assert days_until(date(2027, 9, 1), TODAY) == 339
    assert days_until(date(2027, 9, 1), date(2027, 9, 2)) == -1


# ------------------------------------------------------------------ config
def test_repo_config_loads(config):
    assert config.user == "MatALass"
    assert 1 <= len(config.header.stack) <= 6
    assert config.header.available_from == date(2027, 9, 1)
    assert config.featured


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["header"]["stack"][0].update(tier="legendary"), "tier"),
        (lambda d: d["theme"].update(bg="purple"), "theme.bg"),
        (lambda d: d["theme"].update(sun=["#FFFFFF"]), "exactly 3"),
        (lambda d: d["header"].update(available_from="next year"), "YYYY-MM-DD"),
        (lambda d: d["header"].update(kill_feed=[{"tool": "a", "target": "b"}] * 4), "at most 3"),
        (lambda d: d["header"].update(stack=[]), "1 to 6"),
    ],
)
def test_invalid_config_is_rejected(tmp_path, mutate, message):
    data = _raw_config()
    mutate(data)
    with pytest.raises(ConfigError, match=message):
        load_config(_write_config(tmp_path, data))


# ------------------------------------------------------------------ rendering
def test_all_renders_are_valid_xml(config):
    cards, langs, activity = demo_data(config)
    ET.fromstring(render_header(config.header, activity, config.theme, today=TODAY))
    ET.fromstring(render_languages(langs, config.theme, config.max_languages))
    for i, card in enumerate(cards, start=1):
        ET.fromstring(render_repo_card(card, i, config.theme))


def test_header_shows_countdown_then_available(config):
    _, _, activity = demo_data(config)
    before = render_header(config.header, activity, config.theme, today=TODAY)
    assert ">339<" in before and "DAYS UNTIL AVAILABLE" in before
    after = render_header(config.header, activity, config.theme, today=date(2027, 9, 1))
    assert ">NOW<" in after


def test_header_contains_real_stats_and_feed(config):
    _, _, activity = demo_data(config)
    svg = render_header(config.header, activity, config.theme, today=TODAY)
    assert f"{activity.public_repos} PUBLIC REPOS" in svg
    for entry in config.header.kill_feed:
        assert entry.target in svg


def test_header_survives_zero_activity(config):
    flat = Activity(weekly=(0,) * 52, contributions=0, current_streak=0, longest_streak=0, public_repos=0)
    svg = render_header(config.header, flat, config.theme, today=TODAY)
    ET.fromstring(svg)
    assert "PEAK" not in svg


def test_header_escapes_user_text(config):
    header = replace(config.header, name="A & <B>", role='"R&D"')
    _, _, activity = demo_data(config)
    svg = render_header(header, activity, config.theme, today=TODAY)
    ET.fromstring(svg)
    assert "A &amp; &lt;B&gt;" in svg


def test_card_escapes_and_truncates(config):
    card = RepoCard(repo="r", title="A & B <C>", description="word " * 200, tags=("R&D",), language=None, stars=0)
    svg = render_repo_card(card, 1, config.theme)
    ET.fromstring(svg)
    assert "A &amp; B &lt;C&gt;" in svg
    assert svg.count("…") == 1


def test_cli_demo_writes_all_files(tmp_path, config):
    assert main(["--config", str(CONFIG), "--out", str(tmp_path), "--demo"]) == 0
    assert (tmp_path / "header.svg").is_file()
    assert (tmp_path / "languages.svg").is_file()
    for repo in config.featured:
        assert (tmp_path / "cards" / f"{repo.repo}.svg").is_file()
