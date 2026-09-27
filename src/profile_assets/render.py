"""SVG rendering for project cards and the language share bar.

GitHub displays these through <img>, so an SVG cannot load web fonts or external
files: fonts use system stacks and everything is self-contained.
The animated header lives in ``header.py``.
"""

from __future__ import annotations

import textwrap
from html import escape

from .models import RepoCard, Theme

MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

CARD_W, CARD_H = 440, 170
LANGS_W, LANGS_H = 880, 128


def _svg(width: int, height: int, label: str, body: list[str], theme: Theme) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">',
            f"  <title>{escape(label)}</title>",
            f'  <rect width="{width}" height="{height}" rx="12" fill="{theme.bg}"/>',
            *[f"  {line}" for line in body],
            "</svg>",
            "",
        ]
    )


def _mono(x: float, y: float, text: str, color: str, size: float = 11, anchor: str = "start", spacing: float = 2, weight: int = 400) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}" '
        f'text-anchor="{anchor}" fill="{color}">{escape(text)}</text>'
    )


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return lines


# --------------------------------------------------------------------------- #
# Project card
# --------------------------------------------------------------------------- #
def render_repo_card(card: RepoCard, position: int, theme: Theme) -> str:
    t = theme
    accent = t.accents[(position - 1) % len(t.accents)]
    b: list[str] = [
        f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="12" fill="{t.panel}" stroke="{accent}" stroke-opacity="0.55"/>',
        f'<rect x="0" y="16" width="5" height="{CARD_H - 32}" rx="2.5" fill="{accent}"/>',
        f'<rect x="22" y="18" width="34" height="17" rx="3" fill="{accent}"/>',
        _mono(39, 30.5, f"P{position:02d}", t.bg, size=10.5, anchor="middle", spacing=0.5, weight=800),
        _mono(64, 30.5, card.repo, t.muted, size=10.5, spacing=0.5),
    ]
    meta = f"{(card.language or '').upper()}  ★ {card.stars}".strip()
    b.append(_mono(CARD_W - 18, 30.5, meta, t.muted, size=10.5, anchor="end", spacing=1))
    b.append(
        f'<text x="22" y="60" font-family="{SANS}" font-size="17" font-weight="800" fill="{t.text}">{escape(card.title)}</text>'
    )
    for i, line in enumerate(_wrap(card.description, width=62, max_lines=3)):
        b.append(f'<text x="22" y="{82 + i * 17}" font-family="{SANS}" font-size="12.5" fill="{t.muted}">{escape(line)}</text>')

    x = 22
    for tag in card.tags:
        w = int(len(tag) * 6.6) + 16
        if x + w > CARD_W - 18:
            break
        b.append(f'<rect x="{x}" y="138" width="{w}" height="20" rx="3" fill="{accent}" fill-opacity="0.14" stroke="{accent}"/>')
        b.append(_mono(x + w / 2, 152, tag.upper(), accent, size=10, anchor="middle", spacing=0.5, weight=700))
        x += w + 6

    return _svg(CARD_W, CARD_H, f"{card.title}: {card.description}", b, t)


# --------------------------------------------------------------------------- #
# Language share
# --------------------------------------------------------------------------- #
def render_languages(totals: dict[str, int], theme: Theme, max_langs: int) -> str:
    t = theme
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:max_langs]
    rest = sum(v for _, v in ranked[max_langs:])
    if rest:
        top.append(("Other", rest))

    b: list[str] = [
        f'<rect x="0.5" y="0.5" width="{LANGS_W - 1}" height="{LANGS_H - 1}" rx="12" fill="{t.panel}" stroke="{t.grid}"/>',
        _mono(32, 34, "LANGUAGES · SHARE OF CODE", t.muted, size=11),
    ]
    bar_x, bar_w, gap = 32, LANGS_W - 64, 2
    usable = bar_w - gap * max(len(top) - 1, 0)
    x = float(bar_x)
    for i, (_, size) in enumerate(top):
        w = max(usable * size / grand, 1.5)
        b.append(f'<rect x="{x:.1f}" y="46" width="{w:.1f}" height="14" rx="2" fill="{t.ramp[i % len(t.ramp)]}"/>')
        x += w + gap

    per_row = 5
    col_w = bar_w / per_row
    for i, (lang, size) in enumerate(top):
        row, col = divmod(i, per_row)
        lx, ly = bar_x + col * col_w, 88 + row * 22
        b.append(f'<rect x="{lx:.1f}" y="{ly - 9}" width="9" height="9" rx="2" fill="{t.ramp[i % len(t.ramp)]}"/>')
        b.append(
            f'<text x="{lx + 15:.1f}" y="{ly}" font-family="{SANS}" font-size="12.5" fill="{t.text}">{escape(lang)} '
            f'<tspan font-family="{MONO}" font-size="11" fill="{t.muted}">{100 * size / grand:.1f}%</tspan></text>'
        )
    height = LANGS_H if len(top) > per_row else LANGS_H - 22
    body = [line.replace(f'height="{LANGS_H - 1}"', f'height="{height - 1}"') for line in b]
    return _svg(LANGS_W, height, "Most used languages by share of code", body, t)
