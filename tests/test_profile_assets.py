import json
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import pytest

from profile_assets.cli import demo_data, main
from profile_assets.config import ConfigError, load_config
from profile_assets.github import compute_streaks, weekly_totals
from profile_assets.models import RepoCard
from profile_assets.render import render_header, render_languages, render_repo_card

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "profile.config.json"


def _raw_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "profile.config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ------------------------------------------------------------------ metrics
TODAY = date(2026, 9, 27)


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
    totals = weekly_totals(weeks, n_weeks=3)
    assert totals == (7, 3, 3)


# ------------------------------------------------------------------ config
def test_repo_config_loads():
    config = load_config(CONFIG)
    assert config.user == "MatALass"
    assert 1 <= len(config.header.stack) <= 6
    assert config.featured


def test_unknown_tier_is_rejected(tmp_path):
    data = _raw_config()
    data["header"]["stack"][0]["tier"] = "legendary"
    with pytest.raises(ConfigError, match="tier"):
        load_config(_write_config(tmp_path, data))


def test_bad_color_is_rejected(tmp_path):
    data = _raw_config()
    data["theme"]["primary"] = "blue"
    with pytest.raises(ConfigError, match="theme.primary"):
        load_config(_write_config(tmp_path, data))


def test_missing_logo_file_is_rejected(tmp_path):
    data = _raw_config()
    data["header"]["logo"] = {"path": "assets/nope.svg", "width": 60}
    with pytest.raises(ConfigError, match="missing file"):
        load_config(_write_config(tmp_path, data))


def test_logo_is_embedded_as_data_uri(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    data = _raw_config()
    data["header"]["logo"] = {"path": "assets/logo.svg", "width": 60}
    config = load_config(_write_config(tmp_path, data))
    _, _, activity = demo_data(config)
    svg = render_header(config.header, activity, config.theme)
    assert 'href="data:image/svg+xml;base64,' in svg
    ET.fromstring(svg)


# ------------------------------------------------------------------ rendering
@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG)


def test_all_renders_are_valid_xml(config):
    cards, langs, activity = demo_data(config)
    ET.fromstring(render_header(config.header, activity, config.theme))
    ET.fromstring(render_languages(langs, config.theme, config.max_languages))
    for i, card in enumerate(cards, start=1):
        ET.fromstring(render_repo_card(card, i, config.theme))


def test_special_characters_are_escaped(config):
    card = RepoCard(repo="r", title="A & B <C>", description='"quotes" & <tags>', tags=("R&D",), language=None, stars=0)
    svg = render_repo_card(card, 1, config.theme)
    ET.fromstring(svg)
    assert "A &amp; B &lt;C&gt;" in svg


def test_long_description_is_truncated(config):
    card = RepoCard(repo="r", title="T", description="word " * 200, tags=(), language="Python", stars=0)
    svg = render_repo_card(card, 1, config.theme)
    assert svg.count("…") == 1


def test_header_survives_zero_activity(config):
    _, _, activity = demo_data(config)
    flat = activity.__class__(weekly=(0,) * 52, contributions=0, current_streak=0, longest_streak=0, public_repos=0)
    svg = render_header(config.header, flat, config.theme)
    ET.fromstring(svg)
    assert "PEAK" not in svg


def test_cli_demo_writes_all_files(tmp_path):
    assert main(["--config", str(CONFIG), "--out", str(tmp_path), "--demo"]) == 0
    config = load_config(CONFIG)
    assert (tmp_path / "header.svg").is_file()
    assert (tmp_path / "languages.svg").is_file()
    for repo in config.featured:
        assert (tmp_path / "cards" / f"{repo.repo}.svg").is_file()
