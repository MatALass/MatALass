"""SVG rendering: header (pit wall), project cards, language share.

All images are rendered by GitHub through <img>, which means an SVG cannot load
web fonts or external files. Fonts therefore use system stacks, and the optional
logo is embedded as a base64 data URI.
"""

from __future__ import annotations

import base64
import textwrap
from html import escape

from .models import Activity, Header, Logo, RepoCard, Theme

MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

HEADER_W, HEADER_H = 880, 300
CARD_W, CARD_H = 440, 170
LANGS_W, LANGS_H = 880, 128

TIER_BAR = {0: 60, 1: 44, 2: 28}  # bar length by tier rank (first tier = longest)


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


def _mono(x: float, y: float, text: str, color: str, size: float = 11, anchor: str = "start", spacing: float = 2) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO}" font-size="{size}" letter-spacing="{spacing}" '
        f'text-anchor="{anchor}" fill="{color}">{escape(text)}</text>'
    )


def _logo_image(logo: Logo, x: float, y: float) -> str:
    mime = "image/svg+xml" if logo.path.suffix.lower() == ".svg" else "image/png"
    data = base64.b64encode(logo.path.read_bytes()).decode()
    return (
        f'<image x="{x}" y="{y}" width="{logo.width}" height="{logo.height}" '
        f'preserveAspectRatio="xMinYMid meet" href="data:{mime};base64,{data}"/>'
    )


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def render_header(header: Header, activity: Activity, theme: Theme) -> str:
    t = theme
    b: list[str] = []

    # Background grid (timing-screen feel)
    for x in range(40, HEADER_W, 40):
        b.append(f'<line x1="{x}" y1="12" x2="{x}" y2="{HEADER_H - 12}" stroke="{t.grid}"/>')
    b.append(f'<rect x="0" y="0" width="{HEADER_W}" height="4" rx="2" fill="{t.primary}"/>')
    b.append(f'<rect x="{HEADER_W * 0.62:.0f}" y="0" width="{HEADER_W * 0.38:.0f}" height="4" rx="2" fill="{t.secondary}"/>')

    # Identity block
    kicker_x = 32
    if header.logo:
        b.append(_logo_image(header.logo, 32, 46 - header.logo.height + 4))
        kicker_x = 32 + header.logo.width + 12
    b.append(_mono(kicker_x, 46, header.kicker.upper(), t.muted, size=12, spacing=3))
    b.append(
        f'<text x="30" y="94" font-family="{SANS}" font-size="42" font-weight="800" letter-spacing="1" '
        f'fill="{t.text}">{escape(header.name.upper())}</text>'
    )
    b.append(f'<text x="32" y="122" font-family="{SANS}" font-size="15" fill="{t.muted}">{escape(header.subtitle)}</text>')

    # mono 11.5px + 1px letter-spacing ≈ 8px per character, plus dot and padding
    chip_w = int(len(header.availability) * 8) + 40
    b.append(f'<rect x="32" y="138" width="{chip_w}" height="24" rx="4" fill="{t.panel}" stroke="{t.secondary}"/>')
    b.append(f'<circle cx="46" cy="150" r="4" fill="{t.secondary}"/>')
    b.append(_mono(58, 154, header.availability.upper(), t.secondary, size=11.5, spacing=1))

    # Timing tower (stack)
    tx, tw = 596, 252
    tier_names = list(t.tiers)
    b.append(_mono(tx, 40, "STACK", t.muted, size=11))
    lx = tx + tw
    for name in reversed(tier_names):
        label = name.upper()
        lw = len(label) * 6.6 + 18  # mono 9px + 1px spacing, square and gap
        lx -= lw
        b.append(f'<rect x="{lx:.1f}" y="32" width="8" height="8" fill="{t.tiers[name]}"/>')
        b.append(_mono(lx + 11, 40, label, t.muted, size=9, spacing=1))
    for i, item in enumerate(header.stack):
        y = 52 + i * 21
        color = t.tiers[item.tier]
        bar = TIER_BAR.get(tier_names.index(item.tier), 20)
        b.append(f'<rect x="{tx}" y="{y}" width="{tw}" height="18" fill="{t.panel}"/>')
        b.append(_mono(tx + 8, y + 13, f"{i + 1:02d}", t.muted, size=11, spacing=0))
        b.append(f'<rect x="{tx + 30}" y="{y + 3}" width="3" height="12" fill="{color}"/>')
        b.append(
            f'<text x="{tx + 40}" y="{y + 13}" font-family="{MONO}" font-size="12" font-weight="700" '
            f'fill="{t.text}">{escape(item.code.upper())}</text>'
        )
        b.append(f'<text x="{tx + 84}" y="{y + 13}" font-family="{SANS}" font-size="12" fill="{t.muted}">{escape(item.name)}</text>')
        b.append(f'<rect x="{tx + tw - 8 - bar}" y="{y + 5}" width="{bar}" height="8" fill="{color}"/>')

    # Telemetry trace: contributions per week
    x0, x1, base, height = 32, HEADER_W - 32, 282, 52
    weekly = activity.weekly or (0,)
    peak = max(weekly)
    n = len(weekly)
    step = (x1 - x0) / max(n - 1, 1)
    pts = [(x0 + i * step, base - (height * v / peak if peak else 0)) for i, v in enumerate(weekly)]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))

    b.append(_mono(32, 198, f"CONTRIBUTIONS / WEEK · LAST {n} WEEKS", t.muted, size=11))
    stats = (
        f"{activity.contributions} TOTAL · STREAK {activity.current_streak}D · "
        f"BEST {activity.longest_streak}D · {activity.public_repos} REPOS"
    )
    b.append(_mono(x1, 198, stats, t.text, size=11, anchor="end", spacing=1))
    b.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" stroke="{t.grid}"/>')
    b.append(
        '<defs><linearGradient id="trace" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t.primary}"/><stop offset="1" stop-color="{t.secondary}"/>'
        "</linearGradient></defs>"
    )
    b.append(f'<path d="{path} L{x1},{base} L{x0},{base} Z" fill="url(#trace)" opacity="0.14"/>')
    b.append(f'<path d="{path}" fill="none" stroke="url(#trace)" stroke-width="2" stroke-linejoin="round"/>')
    if peak:
        px, py = pts[weekly.index(peak)]
        anchor, dx = ("end", -8) if px > x1 - 80 else ("start", 8)
        b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{t.secondary}"/>')
        b.append(_mono(px + dx, py - 8, f"PEAK {peak}", t.text, size=11, anchor=anchor, spacing=1))

    label = f"{header.name}: {header.subtitle}. {header.availability}."
    return _svg(HEADER_W, HEADER_H, label, b, t)


# --------------------------------------------------------------------------- #
# Project card
# --------------------------------------------------------------------------- #
def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "…"
    return lines


def render_repo_card(card: RepoCard, position: int, theme: Theme) -> str:
    t = theme
    b: list[str] = [
        f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="12" fill="{t.panel}" stroke="{t.grid}"/>',
        f'<rect x="0" y="16" width="4" height="{CARD_H - 32}" rx="2" fill="{t.secondary}"/>',
        _mono(22, 30, f"P{position:02d} · {card.repo}", t.muted, size=10.5, spacing=1),
    ]
    meta = f"{(card.language or '').upper()}  ★ {card.stars}".strip()
    b.append(_mono(CARD_W - 18, 30, meta, t.muted, size=10.5, anchor="end", spacing=1))
    b.append(
        f'<text x="22" y="56" font-family="{SANS}" font-size="17" font-weight="700" fill="{t.text}">{escape(card.title)}</text>'
    )
    for i, line in enumerate(_wrap(card.description, width=62, max_lines=3)):
        b.append(f'<text x="22" y="{79 + i * 17}" font-family="{SANS}" font-size="12.5" fill="{t.muted}">{escape(line)}</text>')

    x = 22
    for tag in card.tags:
        w = int(len(tag) * 6.6) + 16
        if x + w > CARD_W - 18:
            break
        b.append(f'<rect x="{x}" y="136" width="{w}" height="20" rx="3" fill="none" stroke="{t.primary}"/>')
        b.append(_mono(x + w / 2, 150, tag.upper(), t.primary, size=10, anchor="middle", spacing=0.5))
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

    b: list[str] = [_mono(32, 34, "LANGUAGES · SHARE OF CODE", t.muted, size=11)]
    bar_x, bar_w, gap = 32, LANGS_W - 64, 2
    usable = bar_w - gap * max(len(top) - 1, 0)
    x = float(bar_x)
    for i, (_, size) in enumerate(top):
        w = max(usable * size / grand, 1.5)
        b.append(f'<rect x="{x:.1f}" y="46" width="{w:.1f}" height="14" fill="{t.ramp[i % len(t.ramp)]}"/>')
        x += w + gap

    per_row = 5
    col_w = bar_w / per_row
    for i, (lang, size) in enumerate(top):
        row, col = divmod(i, per_row)
        lx, ly = bar_x + col * col_w, 88 + row * 22
        b.append(f'<rect x="{lx:.1f}" y="{ly - 9}" width="9" height="9" fill="{t.ramp[i % len(t.ramp)]}"/>')
        b.append(
            f'<text x="{lx + 15:.1f}" y="{ly}" font-family="{SANS}" font-size="12.5" fill="{t.text}">{escape(lang)} '
            f'<tspan font-family="{MONO}" font-size="11" fill="{t.muted}">{100 * size / grand:.1f}%</tspan></text>'
        )
    height = LANGS_H if len(top) > per_row else LANGS_H - 22
    return _svg(LANGS_W, height, "Most used languages by share of code", b, t)
