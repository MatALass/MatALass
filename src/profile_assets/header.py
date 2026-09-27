"""Animated "mini game" header: a racing scene rendered with shooter-style HUD overlays.

Layers, back to front:
    sky + stars  →  sun  →  skyline built from real weekly contributions (peak = checkered flag)
    →  perspective floor grid  →  scrolling track with kerbs  →  race car
    →  HUD: player card, loadout (stack), countdown to availability, kill feed, live overlay

Everything is original artwork (no third-party logos or characters). Animations
are SMIL, which GitHub plays inside <img>; every element also has a sensible
static state, so a non-animating renderer still shows a complete frame.
"""

from __future__ import annotations

from datetime import date
from html import escape

from .models import Activity, Header, Theme

W, H = 880, 340
HORIZON = 222
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"


def _mono_width(text: str, size: float, spacing: float = 0) -> float:
    return len(text) * (size * 0.6 + spacing)


def _text(x, y, s, *, size=11, fill="#fff", family=MONO, weight=400, anchor="start", spacing=0, extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'letter-spacing="{spacing}" text-anchor="{anchor}" fill="{fill}"{extra}>{escape(str(s))}</text>'
    )


def days_until(target: date, today: date) -> int:
    return (target - today).days


# --------------------------------------------------------------------------- #
# Scene
# --------------------------------------------------------------------------- #
def _defs(t: Theme) -> str:
    return f"""<defs>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t.sky[0]}"/><stop offset="1" stop-color="{t.sky[1]}"/>
    </linearGradient>
    <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t.sun[0]}"/><stop offset="0.55" stop-color="{t.sun[1]}"/><stop offset="1" stop-color="{t.sun[2]}"/>
    </linearGradient>
    <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t.sky[1]}"/><stop offset="1" stop-color="{t.bg}"/>
    </linearGradient>
    <linearGradient id="ridge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{t.accents[4 % len(t.accents)]}"/><stop offset="0.5" stop-color="{t.accents[2 % len(t.accents)]}"/><stop offset="1" stop-color="{t.accents[0]}"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity="0.28"/></pattern>
  </defs>"""


def _stars(t: Theme) -> list[str]:
    out, seed = [], 1234567
    for _ in range(46):
        seed = (seed * 1103515245 + 12345) % 2**31
        x = seed % W
        seed = (seed * 1103515245 + 12345) % 2**31
        y = 8 + seed % (HORIZON - 70)
        r = 0.6 + (seed % 3) * 0.35
        out.append(f'<circle cx="{x}" cy="{y}" r="{r:.2f}" fill="{t.text}" opacity="{0.25 + (seed % 5) * 0.12:.2f}"/>')
    return out


def _sun(t: Theme) -> list[str]:
    cx, r = 612, 104
    out = [f'<circle cx="{cx}" cy="{HORIZON}" r="{r}" fill="url(#sun)" filter="url(#glow)"/>']
    # synthwave cut lines, thicker towards the horizon
    y, gap = HORIZON - 42, 2.0
    while y < HORIZON:
        out.append(f'<rect x="{cx - r - 2}" y="{y:.1f}" width="{2 * r + 4}" height="{gap:.1f}" fill="{t.sky[1]}"/>')
        y += 9
        gap += 1.1
    return out


def _skyline(weekly: tuple[int, ...], t: Theme) -> list[str]:
    x0, x1, max_h = 0, W, 58
    values = weekly or (0,)
    peak = max(values)
    n = len(values)
    step = (x1 - x0) / max(n - 1, 1)
    pts = [(x0 + i * step, HORIZON - 6 - (max_h * v / peak if peak else 0)) for i, v in enumerate(values)]
    ridge = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    out = [
        f'<path d="{ridge} L{x1},{HORIZON} L{x0},{HORIZON} Z" fill="{t.panel}" fill-opacity="0.9"/>',
        f'<path d="{ridge}" fill="none" stroke="url(#ridge)" stroke-width="2.2" stroke-linejoin="round" filter="url(#glow)"/>',
    ]
    if peak:
        px, py = pts[values.index(peak)]
        top = py - 26
        out.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{top:.1f}" stroke="{t.text}" stroke-width="1.5"/>')
        cell = 3.5
        for row in range(3):
            for col in range(5):
                fill = "#FFFFFF" if (row + col) % 2 == 0 else "#111111"
                out.append(
                    f'<rect x="{px + 0.75 + col * cell:.1f}" y="{top + row * cell:.1f}" width="{cell}" height="{cell}" fill="{fill}"/>'
                )
        label = f"PEAK {peak}/WK"
        right = px + 24 + _mono_width(label, 10, 1) > W - 12
        lx = px - 6 if right else px + 24
        lw = _mono_width(label, 10, 1) + 10
        bx = lx - lw + 5 if right else lx - 5
        out.append(f'<rect x="{bx:.1f}" y="{top - 3:.1f}" width="{lw:.1f}" height="16" rx="3" fill="{t.bg}" fill-opacity="0.85"/>')
        out.append(_text(lx, top + 9, label, size=10, fill=t.accents[1 % len(t.accents)], weight=700, spacing=1, anchor="end" if right else "start"))
    out.append(_text(16, HORIZON - 10, f"COMMITS / WEEK · LAST {n} WEEKS", size=9, fill=t.muted, spacing=1.5))
    return out


def _floor(t: Theme) -> list[str]:
    out = [f'<rect x="0" y="{HORIZON}" width="{W}" height="{H - HORIZON}" fill="url(#floor)"/>']
    vx = W / 2
    grid = t.accents[0]
    for k in range(-14, 15):
        out.append(
            f'<line x1="{vx + k * 7:.1f}" y1="{HORIZON}" x2="{vx + k * 90:.1f}" y2="{H}" stroke="{grid}" stroke-width="1" opacity="0.28"/>'
        )
    for d in (3, 8, 15, 25, 38, 55, 78, 108):
        out.append(f'<line x1="0" y1="{HORIZON + d}" x2="{W}" y2="{HORIZON + d}" stroke="{grid}" stroke-width="1" opacity="0.3"/>')
    out.append(f'<line x1="0" y1="{HORIZON}" x2="{W}" y2="{HORIZON}" stroke="{t.accents[0]}" stroke-width="1.5" filter="url(#glow)"/>')
    return out


def _track(t: Theme) -> list[str]:
    top, bottom = 280, 318
    red, white = t.accents[3 % len(t.accents)], "#F5F3FF"
    out = [f'<rect x="0" y="{top}" width="{W}" height="{bottom - top}" fill="#120824"/>']

    def kerb(y: float) -> str:
        blocks = "".join(
            f'<rect x="{x}" y="{y}" width="20" height="6" fill="{red if (x // 20) % 2 == 0 else white}"/>' for x in range(0, W + 40, 20)
        )
        return (
            f'<g>{blocks}<animateTransform attributeName="transform" type="translate" '
            f'values="0,0; -40,0" dur="0.35s" repeatCount="indefinite"/></g>'
        )

    out.append(kerb(top - 6))
    out.append(kerb(bottom))
    dashes = "".join(f'<rect x="{x}" y="{(top + bottom) / 2 - 1.5}" width="26" height="3" fill="{t.accents[1 % len(t.accents)]}" opacity="0.8"/>' for x in range(0, W + 60, 60))
    out.append(f'<g>{dashes}<animateTransform attributeName="transform" type="translate" values="0,0; -60,0" dur="0.35s" repeatCount="indefinite"/></g>')
    # speed streaks
    for i, (y, w) in enumerate(((288, 70), (296, 110), (305, 55))):
        out.append(
            f'<rect x="0" y="{y}" width="{w}" height="1.5" fill="{t.text}" opacity="0.35">'
            f'<animate attributeName="x" values="{W};-{w}" dur="{0.55 + i * 0.15:.2f}s" repeatCount="indefinite"/></rect>'
        )
    return out


def _wheel(cx: float, cy: float, r: float, rim: str) -> str:
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy - r * 0.55:.1f}" x2="{cx}" y2="{cy + r * 0.55:.1f}" stroke="{rim}" stroke-width="1.6" transform="rotate({a} {cx} {cy})"/>'
        for a in (0, 60, 120)
    )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#0A0A0F" stroke="#2B2B3A" stroke-width="1.5"/>'
        f'<g>{spokes}<animateTransform attributeName="transform" type="rotate" values="0 {cx} {cy}; 360 {cx} {cy}" dur="0.3s" repeatCount="indefinite"/></g>'
        f'<circle cx="{cx}" cy="{cy}" r="{r * 0.22:.1f}" fill="{rim}"/>'
    )


def _car(t: Theme, x: float, y: float) -> str:
    """Generic open-wheel race car, side view, facing right. (x, y) = rear wheel ground contact."""
    body, stripe, wing, helmet, rim = t.accents[0], t.accents[1 % len(t.accents)], t.accents[3 % len(t.accents)], t.accents[1 % len(t.accents)], t.accents[4 % len(t.accents)]
    parts = [
        # exhaust flame
        f'<polygon points="-4,-15 -22,-12 -4,-9" fill="{t.accents[1 % len(t.accents)]}"><animate attributeName="opacity" values="1;0.3;1" dur="0.18s" repeatCount="indefinite"/></polygon>',
        f'<polygon points="-4,-14 -13,-12 -4,-10" fill="{t.accents[3 % len(t.accents)]}"/>',
        # rear wing
        f'<rect x="-2" y="-36" width="20" height="5" rx="1" fill="{wing}"/>',
        f'<rect x="7" y="-31" width="3" height="18" fill="#1B1B25"/>',
        # chassis
        f'<path d="M4,-10 L12,-21 L50,-23 L58,-29 L74,-29 L80,-21 L126,-15 L138,-10 L138,-6 L4,-6 Z" fill="{body}"/>',
        f'<path d="M30,-19 L96,-17 L104,-11 L30,-11 Z" fill="{stripe}"/>',
        f'<path d="M58,-29 Q68,-40 82,-27" fill="none" stroke="#1B1B25" stroke-width="3"/>',
        f'<circle cx="67" cy="-30" r="5.5" fill="{helmet}"/>',
        f'<rect x="64" y="-32" width="7" height="2.5" fill="#1B1B25"/>',
        # front wing
        f'<rect x="120" y="-6" width="30" height="4" rx="1" fill="{wing}"/>',
        f'<rect x="146" y="-13" width="4" height="11" fill="{wing}"/>',
        _wheel(22, -11, 11, rim),
        _wheel(114, -10, 10, rim),
    ]
    return (
        f'<g transform="translate({x},{y})"><g>{"".join(parts)}'
        '<animateTransform attributeName="transform" type="translate" values="0,0; 0,-1.2; 0,0" dur="0.25s" repeatCount="indefinite"/></g></g>'
    )


# --------------------------------------------------------------------------- #
# HUD
# --------------------------------------------------------------------------- #
def _panel(x, y, w, h, t: Theme, stroke: str | None = None) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{t.panel}" fill-opacity="0.88" stroke="{stroke or t.grid}" stroke-width="1.2"/>'


def _player_card(header: Header, t: Theme) -> list[str]:
    x, y, w, h = 18, 16, 318, 96
    pink, yellow = t.accents[0], t.accents[1 % len(t.accents)]
    out = [
        _panel(x, y, w, h, t),
        f'<rect x="{x}" y="{y + 12}" width="4" height="{h - 24}" rx="2" fill="{pink}"/>',
        _text(x + 16, y + 20, "PLAYER 1", size=9, fill=t.muted, spacing=2),
        _text(x + 15, y + 48, header.name.upper(), size=25, fill=t.text, family=SANS, weight=800, spacing=0.5),
        _text(x + 16, y + 67, header.role, size=12.5, fill=t.muted, family=SANS),
    ]
    label = "RANK"
    out.append(f'<rect x="{x + 16}" y="{y + 74}" width="{_mono_width(label, 9, 1) + 12:.0f}" height="15" rx="3" fill="{yellow}"/>')
    out.append(_text(x + 22, y + 85, label, size=9, fill=t.bg, weight=700, spacing=1))
    out.append(_text(x + 28 + _mono_width(label, 9, 1) + 4, y + 85, header.rank.upper(), size=9.5, fill=yellow, weight=700, spacing=1))
    return out


def _loadout(header: Header, t: Theme) -> list[str]:
    x, y, size, gap = 18, 120, 44, 6.8
    out = []
    for i, item in enumerate(header.stack):
        sx = x + i * (size + gap)
        color = t.tiers[item.tier]
        out.append(_panel(sx, y, size, size, t, stroke=color))
        out.append(_text(sx + 5, y + 11, str(i + 1), size=8.5, fill=t.muted))
        out.append(_text(sx + size / 2, y + 29, item.code.upper(), size=12.5, fill=color, weight=800, anchor="middle"))
        out.append(f'<rect x="{sx + 8}" y="{y + size - 7}" width="{size - 16}" height="2.5" rx="1" fill="{color}" opacity="0.8"/>')
    lx = x + len(header.stack) * (size + gap) + 4
    for j, (name, color) in enumerate(t.tiers.items()):
        out.append(f'<rect x="{lx}" y="{y + 6 + j * 13}" width="7" height="7" fill="{color}"/>')
        out.append(_text(lx + 11, y + 13 + j * 13, name.upper(), size=8, fill=t.muted, spacing=1))
    return out


def _countdown(header: Header, today: date, t: Theme) -> list[str]:
    x, y, w, h = W / 2 - 68, 16, 136, 72
    yellow, pink = t.accents[1 % len(t.accents)], t.accents[0]
    days = days_until(header.available_from, today)
    out = [_panel(x, y, w, h, t, stroke=yellow)]
    if days > 0:
        out.append(_text(W / 2, y + 36, days, size=30, fill=yellow, weight=800, anchor="middle", extra=' filter="url(#glow)"'))
        out.append(_text(W / 2, y + 52, "DAYS UNTIL AVAILABLE", size=8.5, fill=t.muted, anchor="middle", spacing=0.5))
    else:
        out.append(_text(W / 2, y + 38, "NOW", size=28, fill=yellow, weight=800, anchor="middle", extra=' filter="url(#glow)"'))
        out.append(_text(W / 2, y + 52, "AVAILABLE", size=9, fill=t.muted, anchor="middle", spacing=1))
    out.append(_text(W / 2, y + 65, header.available_from.strftime("%b %Y").upper(), size=9.5, fill=pink, weight=700, anchor="middle", spacing=1.5))
    return out


def _kill_feed(header: Header, t: Theme) -> list[str]:
    right, y0, row_h = W - 18, 16, 26
    player, victim = t.accents[4 % len(t.accents)], t.accents[3 % len(t.accents)]
    out = []
    for i, entry in enumerate(header.kill_feed):
        y = y0 + i * (row_h + 5)
        chip_color = t.accents[(i * 2 + 1) % len(t.accents)]
        name, tool, target = "MATHIEU", entry.tool.upper(), entry.target
        w_name, w_tool, w_target = _mono_width(name, 10.5, 0.5), _mono_width(tool, 9.5, 0.5) + 12, _mono_width(target, 10.5)
        total = 10 + w_name + 8 + w_tool + 8 + w_target + 10
        x = right - total
        cx = x + 10
        row = [
            _panel(x, y, total, row_h, t),
            _text(cx, y + 17, name, size=10.5, fill=player, weight=700, spacing=0.5),
        ]
        cx += w_name + 8
        row.append(f'<rect x="{cx:.1f}" y="{y + 5}" width="{w_tool:.1f}" height="16" rx="3" fill="{chip_color}"/>')
        row.append(_text(cx + w_tool / 2, y + 17, tool, size=9.5, fill=t.bg, weight=800, anchor="middle", spacing=0.5))
        cx += w_tool + 8
        row.append(_text(cx, y + 17, target, size=10.5, fill=victim))
        row.append(f'<line x1="{cx:.1f}" y1="{y + 13.5}" x2="{cx + w_target:.1f}" y2="{y + 13.5}" stroke="{victim}" stroke-width="1.3"/>')
        begin = f"{i * 0.5:.1f}s"
        out.append(
            f'<g>{"".join(row)}<animate attributeName="opacity" values="0;1;1;1" keyTimes="0;0.06;0.9;1" dur="6s" begin="{begin}" repeatCount="indefinite"/></g>'
        )
    return out


def _live(activity: Activity, t: Theme) -> list[str]:
    red = t.accents[3 % len(t.accents)]
    stats = f"{activity.contributions} CONTRIBUTIONS · {activity.public_repos} PUBLIC REPOS · STREAK {activity.current_streak}D"
    w_stats = _mono_width(stats, 9.5, 0.5)
    pill_w = 52
    total = 10 + pill_w + 10 + w_stats + 12
    x, y, h = 18, 174, 26
    return [
        _panel(x, y, total, h, t, stroke=t.accents[2 % len(t.accents)]),
        f'<rect x="{x + 10}" y="{y + 5}" width="{pill_w}" height="16" rx="3" fill="{red}"/>',
        f'<circle cx="{x + 20}" cy="{y + 13}" r="3.5" fill="#FFFFFF"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/></circle>',
        _text(x + 28, y + 17, "LIVE", size=9.5, fill="#FFFFFF", weight=800, spacing=1),
        _text(x + 10 + pill_w + 10, y + 17, stats, size=9.5, fill=t.text, spacing=0.5),
    ]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def render_header(header: Header, activity: Activity, theme: Theme, today: date | None = None) -> str:
    t, today = theme, today or date.today()
    days = days_until(header.available_from, today)
    status = f"available in {days} days" if days > 0 else "available now"
    label = f"{header.name}, {header.role}, {header.rank}, {status} ({header.available_from:%B %Y})."

    scene = [
        f'<rect width="{W}" height="{H}" fill="url(#sky)"/>',
        *_stars(t),
        *_sun(t),
        *_skyline(activity.weekly, t),
        *_floor(t),
        *_track(t),
        _car(t, 150, 312),
        *_player_card(header, t),
        *_loadout(header, t),
        *_countdown(header, today, t),
        *_kill_feed(header, t),
        *_live(activity, t),
        f'<rect width="{W}" height="{H}" fill="url(#scan)" opacity="0.35"/>',
    ]
    body = "\n    ".join(scene)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  {_defs(t)}
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{t.bg}"/>
    {body}
  </g>
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="none" stroke="{t.grid}" stroke-width="1.5"/>
</svg>
"""
