"""Profile header drawn as a Power BI model view: a star schema of the profile.

A central fact table (``fact_profile``) is linked to five dimension tables
(experience, education, stack, projects, interests) with one-to-many
relationships. Everything shown comes from the ``model`` block of the config.

Two palettes are rendered (dark and light) so the README can follow the
GitHub theme with a <picture> element. Animations are SMIL, which GitHub plays
inside <img>: relationships draw in on load, then small dots travel along
them. Every element has a complete static state.
"""

from __future__ import annotations

from html import escape

from .models import ModelHeader

W, H = 900, 440
SANS = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

PALETTES = {
    "dark": {"bg": "#0D1117", "dots": "#1B2129", "card": "#161B22", "line": "#30363D", "text": "#E6EDF3",
             "muted": "#8B949E", "fact": "#F2C811", "fact_ink": "#0D1117", "fact_title": "#F2C811",
             "dim": "#3FB6A8", "rel": "#57606A"},
    "light": {"bg": "#F6F8FA", "dots": "#DDE2E8", "card": "#FFFFFF", "line": "#D0D7DE", "text": "#1F2328",
              "muted": "#59636E", "fact": "#F2C811", "fact_ink": "#1F2328", "fact_title": "#8A6D00",
              "dim": "#0F766E", "rel": "#8C959F"},
}

DIM_W, FACT_W = 252, 196
FACT_X = (W - FACT_W) / 2
HEADER_H, ROW_H = 30, 21
# (x, y, side) for the five dimensions, in config order
SLOTS = ((24, 104, "left"), (24, 262, "left"), (W - 24 - DIM_W, 104, "right"), (W - 24 - DIM_W, 262, "right"), (FACT_X - 16, 300, "bottom"))


def _t(x, y, s, *, size=12.0, fill="#fff", weight=400, family=SANS, anchor="start", spacing=0.0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.1f}" font-weight="{weight}" '
            f'letter-spacing="{spacing}" text-anchor="{anchor}" fill="{fill}">{escape(str(s))}</text>')


def _fit(text: str, width: float, size: float = 12.5) -> float:
    """Font size that keeps ``text`` inside ``width`` (average sans glyph ~0.53 em)."""
    return min(size, width / max(len(text) * 0.5, 1))


def _height(rows: int) -> float:
    return HEADER_H + ROW_H * rows + 8


def _table(x, y, w, name, rows, color, title_color, p, keys=False):
    h = _height(len(rows))
    # one font size per table, the largest that fits its longest line
    size = min((_fit(r, w - 28) for r in rows), default=12.5)
    out = [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h:.1f}" rx="6" fill="{p["card"]}" stroke="{p["line"]}"/>',
        f'<path d="M{x:.1f},{y + 6:.1f} a6,6 0 0 1 6,-6 h{w - 12} a6,6 0 0 1 6,6 v{HEADER_H - 6} h-{w} z" fill="{color}" fill-opacity="0.16"/>',
        f'<rect x="{x:.1f}" y="{y + HEADER_H - 2:.1f}" width="{w}" height="2" fill="{color}"/>',
        _t(x + 12, y + 20, name, size=12, fill=title_color, weight=700, family=MONO, spacing=0.3),
    ]
    for i, row in enumerate(rows):
        ry = y + HEADER_H + 16 + i * ROW_H
        if keys:
            out.append(f'<circle cx="{x + 16:.1f}" cy="{ry - 4:.1f}" r="3" fill="none" stroke="{color}" stroke-width="1.5"/>'
                       f'<line x1="{x + 19:.1f}" y1="{ry - 4:.1f}" x2="{x + 25:.1f}" y2="{ry - 4:.1f}" stroke="{color}" stroke-width="1.5"/>')
            out.append(_t(x + 32, ry, row, size=11.5, fill=p["muted"], family=MONO))
        else:
            out.append(_t(x + 14, ry, row, size=size, fill=p["text"]))
    return "".join(out)


def _relation(d: str, p: dict, delay: float) -> str:
    """Relationship path drawn in on load, then a dot travelling along it."""
    return (
        f'<path d="{d}" fill="none" stroke="{p["rel"]}" stroke-width="1.6" stroke-dasharray="420" stroke-dashoffset="0">'
        f'<animate attributeName="stroke-dashoffset" from="420" to="0" dur="1.1s" begin="{delay:.1f}s" fill="freeze"/></path>'
        f'<circle r="3" fill="{p["fact"]}" opacity="0"><set attributeName="opacity" to="0.9" begin="{delay + 1.1:.1f}s"/>'
        f'<animateMotion dur="3.4s" begin="{delay + 1.1:.1f}s" repeatCount="indefinite" path="{d}"/></circle>'
    )


def _mark(x, y, s, p, anchor="start"):
    return _t(x, y, s, size=11, fill=p["muted"], family=MONO, anchor=anchor)


def render_model_header(model: ModelHeader, theme: str = "dark") -> str:
    p = PALETTES[theme]
    body = [f'<rect width="{W}" height="{H}" fill="url(#dots-{theme})"/>']

    # title and availability badge
    badge_w = len(model.badge) * 7.0 + 30
    body += [
        _t(26, 46, model.name, size=26, fill=p["text"], weight=700),
        _t(26, 70, model.subtitle, size=_fit(model.subtitle, W - badge_w - 80, 13.5), fill=p["muted"]),
        f'<rect x="{W - 26 - badge_w:.1f}" y="28" width="{badge_w:.1f}" height="28" rx="14" fill="{p["fact"]}"/>',
        _t(W - 26 - badge_w / 2, 47, model.badge, size=12, fill="#0D1117", weight=700, anchor="middle"),
        _t(W - 26, 76, model.caption, size=11, fill=p["muted"], family=MONO, anchor="end"),
    ]

    # fact table: one key per dimension, named after it
    keys = [f"{d.name.removeprefix('dim_').removesuffix('s')}_id" for d in model.dimensions]
    fy = 112
    fh = _height(len(keys))
    key_y = [fy + HEADER_H + 12 + i * ROW_H for i in range(len(keys))]
    fact = _table(FACT_X, fy, FACT_W, model.fact, keys, p["fact"], p["fact_title"], p, keys=True)

    tables, links, marks = [], [], []
    for i, (dim, (x, y, side)) in enumerate(zip(model.dimensions, SLOTS, strict=True)):
        width = FACT_W + 32 if side == "bottom" else DIM_W
        tables.append(_table(x, y, width, dim.name, dim.rows, p["dim"], p["dim"], p))
        h = _height(len(dim.rows))
        delay = 0.2 + i * 0.2
        if side == "bottom":
            cx = FACT_X + FACT_W / 2
            links.append(_relation(f"M{cx:.1f},{fy + fh:.1f} L{cx:.1f},{y:.1f}", p, delay))
            marks += [_mark(cx + 8, fy + fh + 14, "*", p), _mark(cx + 8, y - 6, "1", p)]
            continue
        dy = y + h / 2
        x1, x2 = (x + DIM_W, FACT_X) if side == "left" else (x, FACT_X + FACT_W)
        mid = (x1 + x2) / 2
        links.append(_relation(f"M{x1:.1f},{dy:.1f} C{mid:.1f},{dy:.1f} {mid:.1f},{key_y[i]:.1f} {x2:.1f},{key_y[i]:.1f}", p, delay))
        if side == "left":
            marks += [_mark(x1 + 6, dy - 6, "1", p), _mark(x2 - 6, key_y[i] - 6, "*", p, "end")]
        else:
            marks += [_mark(x1 - 6, dy - 6, "1", p, "end"), _mark(x2 + 6, key_y[i] - 6, "*", p)]

    body += links + tables + [fact] + marks
    label = f"{model.name}. {model.subtitle}. {model.badge}."
    inner = "\n    ".join(body)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}">
  <title>{escape(label)}</title>
  <defs>
    <pattern id="dots-{theme}" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="{p["dots"]}"/></pattern>
    <clipPath id="frame-{theme}"><rect width="{W}" height="{H}" rx="14"/></clipPath>
  </defs>
  <g clip-path="url(#frame-{theme})">
    <rect width="{W}" height="{H}" fill="{p["bg"]}"/>
    {inner}
  </g>
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="none" stroke="{p["line"]}" stroke-width="1.5"/>
</svg>
"""
