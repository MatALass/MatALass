"""Alternative profile headers, chosen with ``header.style`` in the config.

Each style is a sober, recruiter-friendly alternative to the "racing" scene of
``header.py``: no car, no synthwave, one dark palette and one accent per style.
They use the same data (name, role, rank, availability, stack, weekly
contributions) so switching style is a one-word change in the config.

Animations are SMIL, which GitHub plays inside <img>. Every animated element
also has a complete static state.
"""

from __future__ import annotations

from datetime import date
from html import escape

from .header import days_until
from .models import Activity, Header

W = 880
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"


def _mono_width(text: str, size: float, spacing: float = 0) -> float:
    return len(text) * (size * 0.6 + spacing)


def _text(x, y, s, *, size=11, fill="#fff", family=SANS, weight=400, anchor="start", spacing=0, extra=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'letter-spacing="{spacing}" text-anchor="{anchor}" fill="{fill}"{extra}>{escape(str(s))}</text>'
    )


def _label(header: Header, today: date) -> str:
    days = days_until(header.available_from, today)
    status = f"available in {days} days" if days > 0 else "available now"
    return f"{header.name}, {header.role}, {header.rank}, {status} ({header.available_from:%B %Y})."


def _availability(header: Header, today: date) -> tuple[str, str]:
    """(big value, caption) for the availability block."""
    days = days_until(header.available_from, today)
    month = header.available_from.strftime("%b %Y").upper()
    return (str(days), f"DAYS TO {month}") if days > 0 else ("NOW", f"AVAILABLE · {month}")


def _svg(height: int, label: str, bg: str, border: str, body: list[str], defs: str = "") -> str:
    inner = "\n    ".join(body)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <defs><clipPath id="frame"><rect width="{W}" height="{height}" rx="14"/></clipPath>{defs}</defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{height}" fill="{bg}"/>
    {inner}
  </g>
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{height - 1.5}" rx="14" fill="none" stroke="{border}" stroke-width="1.5"/>
</svg>
"""


def _trace(values: tuple[int, ...], x0: float, x1: float, y_base: float, h: float) -> list[tuple[float, float]]:
    values = values or (0,)
    peak = max(values) or 1
    step = (x1 - x0) / max(len(values) - 1, 1)
    return [(x0 + i * step, y_base - h * v / peak) for i, v in enumerate(values)]


def _path(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))


# --------------------------------------------------------------------------- #
# 1. timing: an F1 live-timing screen, no car
# --------------------------------------------------------------------------- #
TIMING = {"bg": "#0E1116", "panel": "#161B22", "line": "#262D36", "text": "#F2F4F7", "muted": "#8B95A3",
          "accent": "#E10600", "purple": "#B15CFF", "green": "#2BD67B", "yellow": "#F5C518"}
TIER_SECTOR = {"core": "purple", "strong": "green", "working": "yellow"}


def render_timing(header: Header, activity: Activity, today: date) -> str:
    c, H = TIMING, 320
    out = [
        f'<rect x="0" y="0" width="{W}" height="4" fill="{c["accent"]}"/>',
        _text(32, 44, "LIVE TIMING", size=10, fill=c["accent"], family=MONO, weight=700, spacing=3),
        _text(32, 84, header.name, size=34, fill=c["text"], weight=700),
        _text(32, 110, header.role, size=15, fill=c["muted"]),
        _text(32, 132, header.rank, size=13, fill=c["muted"]),
    ]
    # availability, as "lights out"
    value, caption = _availability(header, today)
    out += [
        f'<rect x="32" y="152" width="214" height="54" rx="6" fill="{c["panel"]}" stroke="{c["line"]}"/>',
        *[f'<circle cx="{50 + i * 15}" cy="179" r="5" fill="{c["accent"]}" opacity="{0.35 + i * 0.13:.2f}">'
          f'<animate attributeName="opacity" values="0.15;1;1;0.15" keyTimes="0;{0.1 + i * 0.1:.1f};0.85;1" dur="5s" repeatCount="indefinite"/></circle>'
          for i in range(5)],
        _text(135, 177, value, size=20, fill=c["text"], family=MONO, weight=700),
        _text(135, 194, caption, size=9, fill=c["muted"], family=MONO, spacing=1),
    ]
    # timing tower: one row per stack item, sector colours = tier
    x0, y0, row = 470, 26, 24
    out += [
        f'<rect x="{x0}" y="{y0}" width="378" height="{row * (len(header.stack) + 1) + 6}" rx="6" fill="{c["panel"]}" stroke="{c["line"]}"/>',
        _text(x0 + 16, y0 + 19, "POS", size=9, fill=c["muted"], family=MONO, spacing=1),
        _text(x0 + 56, y0 + 19, "STACK", size=9, fill=c["muted"], family=MONO, spacing=1),
        _text(x0 + 196, y0 + 19, "S1   S2   S3", size=9, fill=c["muted"], family=MONO, spacing=1),
    ]
    for i, item in enumerate(header.stack):
        y = y0 + row * (i + 1) + 4
        sector = c[TIER_SECTOR.get(item.tier, "yellow")]
        filled = {"core": 3, "strong": 2}.get(item.tier, 1)
        out.append(f'<line x1="{x0 + 10}" y1="{y}" x2="{x0 + 368}" y2="{y}" stroke="{c["line"]}"/>')
        out.append(_text(x0 + 22, y + 16, i + 1, size=12, fill=c["text"], family=MONO, weight=700, anchor="middle"))
        out.append(f'<rect x="{x0 + 44}" y="{y + 5}" width="3" height="14" fill="{sector}"/>')
        out.append(_text(x0 + 56, y + 16, item.name, size=13, fill=c["text"], weight=600))
        for s in range(3):
            fill = sector if s < filled else c["line"]
            out.append(f'<rect x="{x0 + 196 + s * 35}" y="{y + 7}" width="28" height="10" rx="2" fill="{fill}"/>')
        out.append(_text(x0 + 358, y + 16, item.tier.upper(), size=8.5, fill=c["muted"], family=MONO, anchor="end", spacing=1))
    # telemetry trace from weekly contributions, with a sweeping cursor
    tx0, tx1, base, th = 32, W - 32, H - 34, 48
    pts = _trace(activity.weekly, tx0, tx1, base, th)
    out += [
        f'<line x1="{tx0}" y1="{base}" x2="{tx1}" y2="{base}" stroke="{c["line"]}"/>',
        f'<path d="{_path(pts)}" fill="none" stroke="{c["green"]}" stroke-width="2" stroke-linejoin="round"/>',
        (
            f'<rect x="{tx0}" y="{base - th - 6}" width="1.5" height="{th + 6}" fill="{c["text"]}" opacity="0.6">'
            f'<animate attributeName="x" values="{tx0};{tx1};{tx0}" dur="14s" repeatCount="indefinite"/></rect>'
        ),
        _text(tx0, base + 18, f"TELEMETRY · COMMITS PER WEEK · LAST {len(activity.weekly)} WEEKS", size=9, fill=c["muted"], family=MONO, spacing=1),
        _text(tx1, base + 18, f"{activity.contributions} CONTRIBUTIONS · {activity.public_repos} REPOS", size=9, fill=c["muted"], family=MONO, anchor="end", spacing=1),
    ]
    return _svg(H, _label(header, today), c["bg"], c["line"], out)


# --------------------------------------------------------------------------- #
# 2. dashboard: the header is a small BI report
# --------------------------------------------------------------------------- #
DASH = {"bg": "#F7F6F2", "card": "#FFFFFF", "line": "#E2E0D8", "ink": "#1F2933", "muted": "#6B7280",
        "accent": "#0F766E", "accent2": "#F59E0B", "soft": "#CCE5E2"}


def render_dashboard(header: Header, activity: Activity, today: date) -> str:
    c, H = DASH, 330
    value, _ = _availability(header, today)
    out = [
        _text(32, 50, header.name, size=30, fill=c["ink"], weight=700),
        _text(32, 76, f"{header.role}  ·  {header.rank}", size=14, fill=c["muted"]),
        f'<rect x="{W - 232}" y="28" width="200" height="30" rx="15" fill="{c["accent"]}"/>',
        f'<circle cx="{W - 214}" cy="43" r="4.5" fill="#FFFFFF"><animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite"/></circle>',
        _text(W - 200, 48, f"Open to work · {header.available_from:%b %Y}", size=12.5, fill="#FFFFFF", weight=600),
    ]
    # KPI tiles
    tiles = [(f"{activity.contributions:,}", "Contributions, 52 weeks"), (str(activity.public_repos), "Public repositories"),
             (f"{activity.longest_streak} d", "Longest streak"), (value, f"Days to {header.available_from:%b %Y}" if value != "NOW" else "Available now")]
    tw, gap, ty = 196, 12, 98
    for i, (v, cap) in enumerate(tiles):
        x = 32 + i * (tw + gap)
        out += [
            f'<rect x="{x}" y="{ty}" width="{tw}" height="70" rx="8" fill="{c["card"]}" stroke="{c["line"]}"/>',
            _text(x + 16, ty + 36, v, size=24, fill=c["accent"] if i == 3 else c["ink"], weight=700),
            _text(x + 16, ty + 56, cap, size=11, fill=c["muted"]),
        ]
    # column chart of weekly contributions, growing once on load
    cx0, cx1, base, ch = 44, 600, H - 22, 82
    values = activity.weekly or (0,)
    peak = max(values) or 1
    bw = (cx1 - cx0) / len(values)
    out.append(f'<rect x="{cx0 - 12}" y="{base - ch - 24}" width="{cx1 - cx0 + 24}" height="{ch + 40}" rx="8" fill="{c["card"]}" stroke="{c["line"]}"/>')
    out.append(_text(cx0, base - ch - 8, "Commits per week", size=11, fill=c["muted"], weight=600))
    for i, v in enumerate(values):
        h = max(1.5, ch * 0.85 * v / peak)
        x = cx0 + i * bw + 1
        fill = c["accent2"] if v == peak else c["accent"]
        out.append(
            f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" rx="1.5" fill="{fill}">'
            f'<animate attributeName="height" from="0" to="{h:.1f}" dur="0.8s" begin="{i * 0.015:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="{base}" to="{base - h:.1f}" dur="0.8s" begin="{i * 0.015:.2f}s" fill="freeze"/></rect>'
        )
    mean = sum(values) / len(values)
    my = base - ch * 0.85 * mean / peak
    out.append(f'<line x1="{cx0}" y1="{my:.1f}" x2="{cx1}" y2="{my:.1f}" stroke="{c["ink"]}" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>')
    out.append(_text(cx1, my - 4, f"avg {mean:.1f}", size=9.5, fill=c["ink"], anchor="end"))
    # stack as a ranked bar list
    sx, sw = 624, W - 32 - 624
    out.append(f'<rect x="{sx}" y="{base - ch - 24}" width="{sw}" height="{ch + 40}" rx="8" fill="{c["card"]}" stroke="{c["line"]}"/>')
    out.append(_text(sx + 14, base - ch - 8, "Core stack", size=11, fill=c["muted"], weight=600))
    level = {"core": 1.0, "strong": 0.72, "working": 0.45}
    items = header.stack[:6]
    rh = (ch + 6) / max(len(items), 1)
    for i, item in enumerate(items):
        y = base - ch + 6 + i * rh
        bar = (sw - 120) * level.get(item.tier, 0.45)
        out.append(_text(sx + 14, y + 10, item.name, size=10.5, fill=c["ink"]))
        out.append(f'<rect x="{sx + 100}" y="{y + 2}" width="{sw - 120}" height="9" rx="4.5" fill="{c["soft"]}" opacity="0.5"/>')
        out.append(f'<rect x="{sx + 100}" y="{y + 2}" width="{bar:.1f}" height="9" rx="4.5" fill="{c["accent"]}">'
                   f'<animate attributeName="width" from="0" to="{bar:.1f}" dur="0.9s" fill="freeze"/></rect>')
    return _svg(H, _label(header, today), c["bg"], c["line"], out)


# --------------------------------------------------------------------------- #
# 3. circuit: minimal, a light dot lapping an abstract circuit
# --------------------------------------------------------------------------- #
CIRCUIT = {"bg": "#0B1020", "line": "#1E2742", "track": "#34406A", "text": "#EEF1F8", "muted": "#8A93AD",
           "accent": "#FF6B35", "accent2": "#2EC4B6"}
# An invented closed circuit (not a real track): straights, a hairpin and an esses section.
TRACK = ("M560,214 L800,214 C836,214 846,190 828,170 L790,128 C776,112 788,88 810,86 C836,84 846,60 822,46 "
         "L700,40 C676,39 664,58 676,76 C690,98 672,118 648,112 L600,98 C574,90 552,110 566,132 "
         "C578,150 560,168 538,160 L520,154 C496,146 480,170 498,188 C510,202 530,214 560,214 Z")
SECTORS = (("S1", 690, 236), ("S2", 762, 30), ("S3", 540, 96))


def render_circuit(header: Header, activity: Activity, today: date) -> str:
    c, H = CIRCUIT, 260
    value, caption = _availability(header, today)
    names = [s.name for s in header.stack[:3]]
    out = [
        _text(40, 74, header.name, size=34, fill=c["text"], weight=700),
        _text(40, 102, header.role, size=15, fill=c["muted"]),
        _text(40, 124, header.rank, size=13, fill=c["muted"]),
        f'<line x1="40" y1="146" x2="92" y2="146" stroke="{c["accent"]}" stroke-width="3" stroke-linecap="round"/>',
    ]
    stats = [(value, caption), (str(activity.contributions), "CONTRIBUTIONS"), (str(activity.public_repos), "PUBLIC REPOS")]
    for i, (v, cap) in enumerate(stats):
        x = 40 + i * 130
        out.append(_text(x, 192, v, size=24, fill=c["accent"] if i == 0 else c["text"], family=MONO, weight=700))
        out.append(_text(x, 212, cap, size=8.5, fill=c["muted"], family=MONO, spacing=1))
    out += [
        f'<path id="lap" d="{TRACK}" fill="none" stroke="{c["track"]}" stroke-width="9" stroke-linejoin="round"/>',
        f'<path d="{TRACK}" fill="none" stroke="{c["bg"]}" stroke-width="1" stroke-dasharray="6 8" opacity="0.8"/>',
        f'<rect x="556" y="206" width="5" height="16" fill="{c["text"]}"/>',
        # static renderers show the car-dot parked on the start line; animated ones hide it and run the lap
        f'<circle cx="560" cy="214" r="6" fill="{c["accent"]}"><set attributeName="opacity" to="0" begin="0s"/></circle>',
        (
            f'<g opacity="0"><set attributeName="opacity" to="1" begin="0s"/>'
            f'<circle r="11" fill="{c["accent"]}" opacity="0.25"/><circle r="6" fill="{c["accent"]}"/>'
            f'<animateMotion dur="9s" repeatCount="indefinite"><mpath href="#lap"/></animateMotion></g>'
        ),
    ]
    for (code, x, y), name in zip(SECTORS, names + [""] * 3, strict=False):
        out.append(_text(x, y, f"{code} {name.upper()}".strip(), size=9, fill=c["accent2"], family=MONO, anchor="middle", spacing=1))
    return _svg(H, _label(header, today), c["bg"], c["line"], out)


STYLES = {"timing": render_timing, "dashboard": render_dashboard, "circuit": render_circuit}
