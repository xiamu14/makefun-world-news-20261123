#!/usr/bin/env python3
"""Build index.html for news-image-20261123 (Monday, 23 November 2026)."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "edition-data.json"
OUT_HTML = ROOT / "index.html"
WORLD_TOPO = Path("/tmp/countries-110m.json")

REGION_ORDER = [
    "N. AMERICA",
    "S. AMERICA",
    "EUROPE",
    "MIDDLE EAST",
    "AFRICA",
    "ASIA",
    "OCEANIA",
    "GLOBAL",
]

# Restrained, high-contrast region palette (used for map pins, region bar, and small numbered badges)
REGION_COLORS = {
    "N. AMERICA": "oklch(0.53 0.20 25)",   # Passionate Red
    "S. AMERICA": "oklch(0.60 0.17 48)",   # Warm Orange
    "AFRICA": "oklch(0.46 0.13 150)",      # Muted Forest Green
    "ASIA": "oklch(0.48 0.12 205)",        # Deep Teal
    "EUROPE": "oklch(0.45 0.15 255)",      # Slate Cobalt
    "MIDDLE EAST": "oklch(0.48 0.15 325)", # Plum
    "OCEANIA": "oklch(0.50 0.15 355)",     # Berry
    "GLOBAL": "oklch(0.32 0.010 60)",      # Charcoal Gray (no pure black)
}

STATUS_STYLES = {
    "CONFIRMED": ("oklch(0.36 0.08 150)", "oklch(0.94 0.015 150)"),
    "OFFICIAL": ("oklch(0.36 0.08 245)", "oklch(0.94 0.015 245)"),
    "CLAIM": ("oklch(0.44 0.11 48)", "oklch(0.95 0.025 55)"),
}


def audit_data(data: dict) -> dict[str, int]:
    leads = data["leads"]
    cards = data["cards"]
    briefs = data["briefs"]
    assert len(leads) == 3, f"Expected 3 leads, got {len(leads)}"
    assert len(cards) == 10, f"Expected 10 cards, got {len(cards)}"
    assert len(briefs) == 20, f"Expected 20 briefs, got {len(briefs)}"

    all_items = leads + cards + briefs
    ids = [item["id"] for item in all_items]
    assert ids == list(range(1, 34)), f"IDs not contiguous 1..33: {ids}"

    counts = {r: 0 for r in REGION_ORDER}
    for item in all_items:
        reg = item["region"]
        assert reg in counts, f"Unknown region {reg}"
        counts[reg] += 1
        lat, lon = item["lat"], item["lon"]
        assert -90 <= lat <= 90 and -180 <= lon <= 180, f"Bad coords on #{item['id']}"
        assert item.get("location") and (item.get("title") or item.get("text")), f"Empty fields on #{item['id']}"

    assert sum(counts.values()) == 33
    for r, c in counts.items():
        assert c > 0, f"Region {r} has 0 items"
    return counts


ROBINSON_TABLE = [
    (0, 1.0000, 0.0000),
    (5, 0.9986, 0.0620),
    (10, 0.9954, 0.1240),
    (15, 0.9900, 0.1860),
    (20, 0.9822, 0.2480),
    (25, 0.9730, 0.3100),
    (30, 0.9600, 0.3720),
    (35, 0.9427, 0.4340),
    (40, 0.9216, 0.4958),
    (45, 0.8962, 0.5571),
    (50, 0.8679, 0.6176),
    (55, 0.8350, 0.6769),
    (60, 0.7986, 0.7346),
    (65, 0.7597, 0.7903),
    (70, 0.7186, 0.8435),
    (75, 0.6732, 0.8936),
    (80, 0.6213, 0.9394),
    (85, 0.5722, 0.9761),
    (90, 0.5322, 1.0000),
]


def project_robinson(lon: float, lat: float, w: float = 364.0, h: float = 166.0) -> tuple[float, float]:
    alat = min(89.9, abs(lat))
    idx = int(alat // 5)
    frac = (alat - idx * 5) / 5.0
    _, px0, py0 = ROBINSON_TABLE[idx]
    _, px1, py1 = ROBINSON_TABLE[min(idx + 1, len(ROBINSON_TABLE) - 1)]
    px = px0 + (px1 - px0) * frac
    py = py0 + (py1 - py0) * frac
    if lat < 0:
        py = -py
    x = w * 0.5 + (lon / 180.0) * px * (w * 0.485)
    y = h * 0.55 - py * (h * 0.485)
    return round(x, 2), round(y, 2)


def decode_topojson_paths() -> list[str]:
    topo = json.loads(WORLD_TOPO.read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]

    decoded_arcs: list[list[tuple[float, float]]] = []
    for arc in topo["arcs"]:
        pts = []
        cx, cy = 0, 0
        for dx, dy in arc:
            cx += dx
            cy += dy
            pts.append((cx * sx + tx, cy * sy + ty))
        decoded_arcs.append(pts)

    def get_ring(arc_indices: list[int]) -> list[tuple[float, float]]:
        ring: list[tuple[float, float]] = []
        for idx in arc_indices:
            pts = decoded_arcs[~idx][::-1] if idx < 0 else decoded_arcs[idx]
            if ring and pts:
                pts = pts[1:]
            ring.extend(pts)
        return ring

    paths: list[str] = []
    geoms = topo["objects"]["countries"]["geometries"]
    for geom in geoms:
        if geom.get("id") == "010":
            continue
        gtype = geom["type"]
        rings = []
        if gtype == "Polygon":
            rings = geom["arcs"]
        elif gtype == "MultiPolygon":
            for poly in geom["arcs"]:
                rings.extend(poly)
        for arc_idx_list in rings:
            ring = get_ring(arc_idx_list)
            if len(ring) < 3:
                continue
            segments: list[list[tuple[float, float]]] = [[]]
            for i, (lon, lat) in enumerate(ring):
                if i > 0 and abs(lon - ring[i - 1][0]) > 180:
                    segments.append([])
                segments[-1].append((lon, lat))
            for seg in segments:
                if len(seg) < 3:
                    continue
                coords = [project_robinson(lon, lat) for lon, lat in seg]
                d = "M" + "L".join(f"{x},{y}" for x, y in coords) + "Z"
                paths.append(d)
    return paths


def render_world_map(all_items: list[dict]) -> str:
    land_paths = decode_topojson_paths()
    land_svg = "".join(
        f'<path d="{d}" fill="oklch(0.985 0.004 80)" stroke="oklch(0.75 0.008 70)" stroke-width="0.48"/>'
        for d in land_paths
    )
    eq_y = project_robinson(0, 0)[1]
    dots_svg = []
    for item in reversed(all_items):
        x, y = project_robinson(item["lon"], item["lat"])
        col = REGION_COLORS[item["region"]]
        if item["id"] <= 13:
            dots_svg.append(
                f'<g><circle cx="{x}" cy="{y}" r="6.2" fill="{col}" stroke="oklch(0.99 0.003 80)" stroke-width="1.2"/>'
                f'<text x="{x}" y="{y + 2.8}" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="800" fill="oklch(0.99 0.003 80)">{item["id"]}</text></g>'
            )
        else:
            dots_svg.append(
                f'<circle cx="{x}" cy="{y}" r="3.1" fill="{col}" stroke="oklch(0.99 0.003 80)" stroke-width="0.9"/>'
            )
    return (
        f'<svg viewBox="0 0 364 166" width="364" height="166" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="364" height="166" rx="4" fill="oklch(0.945 0.010 220)"/>'
        f'<line x1="6" y1="{eq_y}" x2="358" y2="{eq_y}" stroke="oklch(0.84 0.012 220)" stroke-width="0.5" stroke-dasharray="2,3"/>'
        f'{land_svg}{"".join(dots_svg)}</svg>'
    )


def lead_svg(lead_id: int) -> str:
    if lead_id == 1:
        # Detailed GPU silicon chip + Wall Street rebound chart
        return """<svg viewBox="0 0 318 108" width="318" height="108" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="318" height="108" fill="oklch(0.955 0.006 80)"/>
  <!-- Left: Detailed GPU / AI Chip Die -->
  <g transform="translate(12,12)">
    <rect x="0" y="0" width="84" height="84" rx="6" fill="oklch(0.32 0.012 60)" stroke="oklch(0.45 0.012 60)" stroke-width="1"/>
    <!-- Gold/Orange pins -->
    <g fill="oklch(0.68 0.14 55)">
      <rect x="12" y="-3" width="6" height="4"/><rect x="24" y="-3" width="6" height="4"/><rect x="36" y="-3" width="6" height="4"/><rect x="48" y="-3" width="6" height="4"/><rect x="60" y="-3" width="6" height="4"/>
      <rect x="12" y="83" width="6" height="4"/><rect x="24" y="83" width="6" height="4"/><rect x="36" y="83" width="6" height="4"/><rect x="48" y="83" width="6" height="4"/><rect x="60" y="83" width="6" height="4"/>
      <rect x="-3" y="12" width="4" height="6"/><rect x="-3" y="24" width="4" height="6"/><rect x="-3" y="36" width="4" height="6"/><rect x="-3" y="48" width="4" height="6"/><rect x="-3" y="60" width="4" height="6"/>
      <rect x="83" y="12" width="4" height="6"/><rect x="83" y="24" width="4" height="6"/><rect x="83" y="36" width="4" height="6"/><rect x="83" y="48" width="4" height="6"/><rect x="83" y="60" width="4" height="6"/>
    </g>
    <rect x="12" y="12" width="60" height="60" rx="3" fill="oklch(0.24 0.010 60)" stroke="oklch(0.60 0.17 48)" stroke-width="1.2"/>
    <g stroke="oklch(0.45 0.015 60)" stroke-width="0.7" fill="oklch(0.30 0.010 60)">
      <rect x="17" y="17" width="22" height="22" rx="1.5"/><rect x="45" y="17" width="22" height="22" rx="1.5"/>
      <rect x="17" y="45" width="22" height="22" rx="1.5"/><rect x="45" y="45" width="22" height="22" rx="1.5"/>
    </g>
    <text x="42" y="45" text-anchor="middle" font-family="Roboto,sans-serif" font-size="10" font-weight="900" fill="oklch(0.98 0.004 80)">NVDA</text>
  </g>
  <!-- Right: Market Rebound Area + Bar Chart -->
  <g transform="translate(108,10)">
    <rect x="0" y="0" width="198" height="88" rx="4" fill="oklch(0.985 0.004 80)" stroke="oklch(0.86 0.008 75)" stroke-width="1"/>
    <line x1="10" y1="66" x2="188" y2="66" stroke="oklch(0.82 0.008 75)" stroke-width="1"/>
    <line x1="10" y1="44" x2="188" y2="44" stroke="oklch(0.91 0.006 75)" stroke-width="0.8" stroke-dasharray="2,2"/>
    <line x1="10" y1="22" x2="188" y2="22" stroke="oklch(0.91 0.006 75)" stroke-width="0.8" stroke-dasharray="2,2"/>
    <!-- Last week plunge -> Monday surge -->
    <polygon points="14,34 36,56 58,62 82,20 82,66 14,66" fill="oklch(0.53 0.21 25 / 0.14)"/>
    <polyline points="14,34 36,56 58,62 82,20" fill="none" stroke="oklch(0.53 0.21 25)" stroke-width="2.2" stroke-linejoin="round"/>
    <circle cx="82" cy="20" r="3" fill="oklch(0.53 0.21 25)"/>
    <text x="48" y="16" font-family="Roboto,sans-serif" font-size="11.5" font-weight="900" fill="oklch(0.53 0.21 25)">+31.5%</text>
    <text x="48" y="79" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8" font-weight="700" fill="oklch(0.45 0.010 60)">7d slide → rebound</text>
    <!-- Index bars -->
    <rect x="102" y="28" width="22" height="38" rx="2" fill="oklch(0.60 0.17 48)"/>
    <text x="113" y="24" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8" font-weight="800" fill="oklch(0.32 0.010 60)">+6.5%</text>
    <text x="113" y="79" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.40 0.010 60)">NDQ</text>

    <rect x="132" y="38" width="22" height="28" rx="2" fill="oklch(0.52 0.012 60)"/>
    <text x="143" y="34" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8" font-weight="800" fill="oklch(0.32 0.010 60)">+4.7%</text>
    <text x="143" y="79" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.40 0.010 60)">S&amp;P</text>

    <rect x="162" y="48" width="22" height="18" rx="2" fill="oklch(0.68 0.010 60)"/>
    <text x="173" y="44" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8" font-weight="800" fill="oklch(0.32 0.010 60)">+3.0%</text>
    <text x="173" y="79" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.40 0.010 60)">DOW</text>
  </g>
</svg>"""
    if lead_id == 2:
        # Detailed EU-27 Sanctions + Kyiv/Refinery Strikes dual editorial scene
        return """<svg viewBox="0 0 318 108" width="318" height="108" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="318" height="108" fill="oklch(0.952 0.006 80)"/>
  <!-- Left: EU-27 Sanctions Card with bank/crypto/flag icons -->
  <rect x="10" y="9" width="144" height="90" rx="4" fill="oklch(0.985 0.004 80)" stroke="oklch(0.84 0.008 75)" stroke-width="1"/>
  <circle cx="24" cy="22" r="8" fill="oklch(0.45 0.15 255)"/>
  <circle cx="24" cy="22" r="5" fill="none" stroke="oklch(0.82 0.14 85)" stroke-width="1.2" stroke-dasharray="1.5,1.8"/>
  <text x="36" y="25" font-family="Roboto,sans-serif" font-size="9" font-weight="900" fill="oklch(0.30 0.010 60)">EU-27 SANCTIONS</text>
  <!-- 3 detailed target rows -->
  <g transform="translate(17,34)">
    <rect width="130" height="17" rx="2.5" fill="oklch(0.945 0.006 80)"/>
    <path d="M7,13 L17,13 M8,13 L8,8 M12,13 L12,8 M16,13 L16,8 M6,8 L18,8 L12,4 Z" fill="oklch(0.45 0.15 255)"/>
    <text x="24" y="11.5" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.28 0.010 60)">Dozens of Russian banks</text>
  </g>
  <g transform="translate(17,55)">
    <rect width="130" height="17" rx="2.5" fill="oklch(0.945 0.006 80)"/>
    <circle cx="12" cy="8.5" r="4.5" fill="none" stroke="oklch(0.60 0.17 48)" stroke-width="1.5"/>
    <path d="M10,8.5 L14,8.5 M12,6.5 L12,10.5" stroke="oklch(0.60 0.17 48)" stroke-width="1.3"/>
    <text x="24" y="11.5" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.28 0.010 60)">Crypto platforms</text>
  </g>
  <g transform="translate(17,76)">
    <rect width="130" height="17" rx="2.5" fill="oklch(0.945 0.006 80)"/>
    <path d="M8,13 L8,4 L16,6 L8,9" fill="oklch(0.53 0.20 25)"/>
    <line x1="6" y1="13" x2="17" y2="4" stroke="oklch(0.32 0.010 60)" stroke-width="1.2"/>
    <text x="24" y="11.5" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.28 0.010 60)">Sports flag bans</text>
  </g>

  <!-- Right: Kyiv Apartment Skyline + Refinery Strike -->
  <rect x="164" y="9" width="144" height="90" rx="4" fill="oklch(0.985 0.004 80)" stroke="oklch(0.84 0.008 75)" stroke-width="1"/>
  <!-- Building silhouette -->
  <g transform="translate(172,42)">
    <rect x="0" y="12" width="18" height="36" fill="oklch(0.42 0.010 60)"/>
    <rect x="22" y="2" width="24" height="46" fill="oklch(0.32 0.010 60)"/>
    <polygon points="34,2 46,2 46,16 38,12" fill="oklch(0.53 0.20 25)"/>
    <rect x="50" y="18" width="16" height="30" fill="oklch(0.48 0.010 60)"/>
    <!-- Windows -->
    <g fill="oklch(0.95 0.005 80)">
      <rect x="26" y="8" width="4" height="4"/><rect x="26" y="16" width="4" height="4"/><rect x="34" y="16" width="4" height="4"/>
      <rect x="26" y="24" width="4" height="4"/><rect x="34" y="24" width="4" height="4"/><rect x="26" y="32" width="4" height="4"/>
    </g>
  </g>
  <text x="244" y="33" font-family="Roboto,sans-serif" font-size="22" font-weight="900" fill="oklch(0.53 0.21 25)">15+</text>
  <text x="244" y="45" font-family="Roboto,sans-serif" font-size="8.5" font-weight="800" fill="oklch(0.30 0.010 60)">Kyiv dead</text>
  <line x1="244" y1="53" x2="298" y2="53" stroke="oklch(0.86 0.006 80)" stroke-width="1"/>
  <text x="244" y="66" font-family="Roboto,sans-serif" font-size="8" font-weight="700" fill="oklch(0.38 0.008 60)">Perm &amp; Rostov</text>
  <text x="244" y="76" font-family="Roboto,sans-serif" font-size="8" font-weight="700" fill="oklch(0.60 0.17 48)">refineries hit</text>
</svg>"""
    # Lead 3: Detailed Strait of Hormuz tactical map + tanker + drone silhouette
    return """<svg viewBox="0 0 318 108" width="318" height="108" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="318" height="108" fill="oklch(0.945 0.012 220)"/>
  <!-- Bathymetry rings -->
  <path d="M0,45 Q130,30 220,54 T318,48" fill="none" stroke="oklch(0.88 0.015 220)" stroke-width="6"/>
  <!-- Iran Coast (north) & Qeshm Island -->
  <path d="M0,0 L318,0 L318,34 Q245,44 190,26 Q115,12 0,32 Z" fill="oklch(0.88 0.018 75)" stroke="oklch(0.72 0.018 70)" stroke-width="0.8"/>
  <path d="M122,30 Q150,24 172,30 Q150,36 122,30 Z" fill="oklch(0.85 0.020 75)" stroke="oklch(0.70 0.018 70)" stroke-width="0.6"/>
  <!-- Musandam Peninsula (south) -->
  <path d="M108,108 L142,74 Q166,54 186,74 L218,108 Z" fill="oklch(0.86 0.020 75)" stroke="oklch(0.70 0.018 70)" stroke-width="0.8"/>
  <text x="16" y="18" font-family="Roboto,sans-serif" font-size="9" font-weight="900" fill="oklch(0.32 0.012 60)">IRAN</text>
  <text x="164" y="100" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8.5" font-weight="800" fill="oklch(0.34 0.012 60)">OMAN / HORMUZ</text>
  <!-- Shipping lane + Detailed Tanker Silhouette -->
  <path d="M10,66 Q140,42 308,64" fill="none" stroke="oklch(0.60 0.17 48)" stroke-width="1.6" stroke-dasharray="4,3"/>
  <g transform="translate(54,53)">
    <polygon points="0,6 34,6 38,2 4,2" fill="oklch(0.30 0.010 60)"/>
    <rect x="6" y="-2" width="8" height="4" fill="oklch(0.45 0.010 60)"/>
    <rect x="18" y="0" width="12" height="2" fill="oklch(0.60 0.17 48)"/>
  </g>
  <!-- Detailed Drone + Radar Target -->
  <g transform="translate(226,48)">
    <circle cx="0" cy="0" r="16" fill="oklch(0.53 0.21 25 / 0.12)" stroke="oklch(0.53 0.21 25)" stroke-width="1.2" stroke-dasharray="3,2"/>
    <path d="M-12,0 L12,0 M-3,-7 L0,7 L3,-7" fill="none" stroke="oklch(0.28 0.010 60)" stroke-width="1.6" stroke-linecap="round"/>
    <circle cx="0" cy="0" r="2.2" fill="oklch(0.53 0.21 25)"/>
  </g>
  <rect x="246" y="28" width="64" height="30" rx="3" fill="oklch(0.985 0.004 80)" stroke="oklch(0.53 0.21 25)" stroke-width="1"/>
  <text x="278" y="41" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8.5" font-weight="900" fill="oklch(0.53 0.21 25)">DRONE CLAIM</text>
  <text x="278" y="52" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.36 0.010 60)">+ US sanctions</text>
</svg>"""


def card_svg(card_id: int) -> str:
    # Full-bleed 190x72 (preserveAspectRatio="xMidYMid slice"), keeping y=0..24 clear for .mini-top overlay
    if card_id == 4:
        # Spain Supreme Court grants Puigdemont amnesty
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <g transform="translate(120,28)">
    <rect x="0" y="29" width="60" height="5" rx="1" fill="oklch(0.76 0.008 75)"/>
    <rect x="10" y="6" width="40" height="23" rx="2" fill="oklch(0.985 0.004 80)" stroke="oklch(0.45 0.15 255)" stroke-width="1.2"/>
    <line x1="16" y1="13" x2="44" y2="13" stroke="oklch(0.60 0.17 48)" stroke-width="1.8"/>
    <line x1="16" y1="20" x2="36" y2="20" stroke="oklch(0.72 0.008 75)" stroke-width="1.5"/>
  </g>
  <text x="8" y="44" font-family="Roboto,sans-serif" font-size="13" font-weight="900" fill="oklch(0.45 0.15 255)">AMNESTY</text>
  <text x="8" y="59" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.36 0.010 60)">2017 case closed</text>
</svg>"""
    if card_id == 5:
        # FIFA 2031 & 2035 Women's World Cup pitch + trophy
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <rect x="5" y="27" width="79" height="39" rx="3" fill="oklch(0.985 0.004 80)" stroke="oklch(0.82 0.008 75)" stroke-width="1"/>
  <rect x="5" y="27" width="79" height="4" rx="1" fill="oklch(0.60 0.17 48)"/>
  <text x="44.5" y="47" text-anchor="middle" font-family="Roboto,sans-serif" font-size="13" font-weight="900" fill="oklch(0.28 0.010 60)">2031</text>
  <text x="44.5" y="59" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.42 0.010 60)">US·MX·CR·JM</text>
  <path d="M90,34 L100,34 L98,44 L92,44 Z M95,44 L95,53 M91,53 L99,53" fill="oklch(0.60 0.17 48)" stroke="oklch(0.60 0.17 48)" stroke-width="1.2"/>
  <rect x="106" y="27" width="79" height="39" rx="3" fill="oklch(0.985 0.004 80)" stroke="oklch(0.82 0.008 75)" stroke-width="1"/>
  <rect x="106" y="27" width="79" height="4" rx="1" fill="oklch(0.45 0.15 255)"/>
  <text x="145.5" y="47" text-anchor="middle" font-family="Roboto,sans-serif" font-size="13" font-weight="900" fill="oklch(0.28 0.010 60)">2035</text>
  <text x="145.5" y="59" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.42 0.010 60)">UK 4-Nations</text>
</svg>"""
    if card_id == 6:
        # Himalayan mountains shifted right so $1.6B sits 100% on clean light-gray background
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <polygon points="104,63 130,32 156,63" fill="oklch(0.84 0.008 75)"/>
  <polygon points="138,63 166,27 190,63" fill="oklch(0.76 0.008 75)"/>
  <path d="M98,63 Q144,57 190,63 L190,72 L98,72 Z" fill="oklch(0.48 0.12 205 / 0.30)"/>
  <text x="8" y="48" font-family="Roboto,sans-serif" font-size="22" font-weight="900" fill="oklch(0.60 0.17 48)">$1.6B</text>
  <text x="8" y="61" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.32 0.010 60)">Nepal flood aid</text>
</svg>"""
    if card_id == 7:
        # Brazil economic target band & downward GDP step
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <rect x="82" y="28" width="102" height="36" rx="3" fill="oklch(0.985 0.004 80)" stroke="oklch(0.84 0.008 75)" stroke-width="0.8"/>
  <rect x="84" y="35" width="98" height="11" fill="oklch(0.60 0.17 48 / 0.15)"/>
  <polyline points="88,37 118,40 148,49 178,58" fill="none" stroke="oklch(0.53 0.21 25)" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="178" cy="58" r="3" fill="oklch(0.53 0.21 25)"/>
  <text x="6" y="48" font-family="Roboto,sans-serif" font-size="22" font-weight="900" fill="oklch(0.28 0.010 60)">1.8%</text>
  <text x="6" y="62" font-family="Roboto,sans-serif" font-size="8" font-weight="700" fill="oklch(0.42 0.010 60)">2027 GDP · CPI up</text>
</svg>"""
    if card_id == 8:
        # US-China rivalry diplomatic scales
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <line x1="95" y1="29" x2="95" y2="58" stroke="oklch(0.42 0.010 60)" stroke-width="2"/>
  <rect x="77" y="58" width="36" height="4" rx="1" fill="oklch(0.32 0.010 60)"/>
  <line x1="28" y1="42" x2="162" y2="35" stroke="oklch(0.32 0.010 60)" stroke-width="2"/>
  <circle cx="28" cy="48" r="11" fill="oklch(0.985 0.004 80)" stroke="oklch(0.45 0.15 255)" stroke-width="1.5"/>
  <text x="28" y="51" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8.5" font-weight="900" fill="oklch(0.45 0.15 255)">US</text>
  <circle cx="162" cy="41" r="11" fill="oklch(0.985 0.004 80)" stroke="oklch(0.53 0.21 25)" stroke-width="1.5"/>
  <text x="162" y="44" text-anchor="middle" font-family="Roboto,sans-serif" font-size="8.5" font-weight="900" fill="oklch(0.53 0.21 25)">CN</text>
  <text x="95" y="68" text-anchor="middle" font-family="Roboto,sans-serif" font-size="7.5" font-weight="700" fill="oklch(0.42 0.010 60)">Global rules strained</text>
</svg>"""
    if card_id == 9:
        # UN AI Safety Shield + 1 YR
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <path d="M138,27 L160,33 L160,47 C160,57 138,65 138,65 C138,65 116,57 116,47 L116,33 Z" fill="oklch(0.985 0.004 80)" stroke="oklch(0.32 0.010 60)" stroke-width="1.5"/>
  <circle cx="138" cy="45" r="5" fill="oklch(0.60 0.17 48)"/>
  <circle cx="127" cy="39" r="2" fill="oklch(0.42 0.010 60)"/><circle cx="149" cy="39" r="2" fill="oklch(0.42 0.010 60)"/>
  <line x1="127" y1="39" x2="138" y2="45" stroke="oklch(0.42 0.010 60)" stroke-width="1"/>
  <line x1="149" y1="39" x2="138" y2="45" stroke="oklch(0.42 0.010 60)" stroke-width="1"/>
  <text x="6" y="48" font-family="Roboto,sans-serif" font-size="22" font-weight="900" fill="oklch(0.28 0.010 60)">1 YR</text>
  <text x="6" y="62" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.42 0.010 60)">UN AI safety pact</text>
</svg>"""
    if card_id == 10:
        # Belgian Airport Strike: ATC Tower + Grounded Jet + 14h
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <rect x="160" y="34" width="6" height="28" fill="oklch(0.42 0.010 60)"/>
  <polygon points="153,28 173,28 169,35 157,35" fill="oklch(0.30 0.010 60)"/>
  <path d="M88,54 L140,54 L144,48 L134,51 L114,42 L109,42 L116,51 L94,51 L90,47 L87,47 Z" fill="oklch(0.32 0.010 60)"/>
  <rect x="0" y="60" width="190" height="4" fill="oklch(0.78 0.008 75)"/>
  <text x="6" y="48" font-family="Roboto,sans-serif" font-size="21" font-weight="900" fill="oklch(0.53 0.21 25)">14h</text>
  <text x="6" y="59" font-family="Roboto,sans-serif" font-size="8" font-weight="700" fill="oklch(0.36 0.010 60)">06–20Z grounded</text>
</svg>"""
    if card_id == 11:
        # Asian Stocks Candlestick Sell-off (raised so SEOUL · TOKYO SLIDE has clean margin)
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <g stroke="oklch(0.42 0.010 60)" stroke-width="1">
    <line x1="20" y1="26" x2="20" y2="37"/><rect x="14" y="28" width="12" height="6" fill="oklch(0.48 0.12 205)"/>
    <line x1="56" y1="29" x2="56" y2="41"/><rect x="50" y="31" width="12" height="7" fill="oklch(0.53 0.21 25)"/>
    <line x1="94" y1="33" x2="94" y2="46"/><rect x="88" y="35" width="12" height="8" fill="oklch(0.53 0.21 25)"/>
    <line x1="132" y1="36" x2="132" y2="50"/><rect x="126" y="38" width="12" height="9" fill="oklch(0.53 0.21 25)"/>
    <line x1="170" y1="40" x2="170" y2="54"/><rect x="164" y="42" width="12" height="9" fill="oklch(0.53 0.21 25)"/>
  </g>
  <text x="6" y="65" font-family="Roboto,sans-serif" font-size="8.5" font-weight="800" fill="oklch(0.36 0.010 60)">SEOUL · TOKYO SLIDE</text>
</svg>"""
    if card_id == 12:
        # DR Congo Ebola Clinic Tent + Perimeter
        return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <polygon points="8,60 8,40 30,31 52,40 52,60" fill="oklch(0.985 0.004 80)" stroke="oklch(0.46 0.13 150)" stroke-width="1.4"/>
  <path d="M30,41 L30,52 M24.5,46.5 L35.5,46.5" stroke="oklch(0.46 0.13 150)" stroke-width="2.4"/>
  <path d="M62,36 A18,18 0 0,1 62,56" fill="none" stroke="oklch(0.53 0.21 25)" stroke-width="1.6" stroke-dasharray="3,2"/>
  <text x="74" y="45" font-family="Roboto,sans-serif" font-size="11.5" font-weight="900" fill="oklch(0.53 0.21 25)">EBOLA ZONE</text>
  <text x="74" y="58" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.36 0.010 60)">WHO staff trapped</text>
</svg>"""
    # Card 13: Appeals court ruling (light warm-paper background, gavel & docket)
    return """<svg viewBox="0 0 190 72" width="190" height="72" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
  <rect width="190" height="72" fill="oklch(0.955 0.005 80)"/>
  <!-- Court pillars & gavel on light background -->
  <g transform="translate(116,28)">
    <rect x="0" y="28" width="64" height="6" rx="1" fill="oklch(0.76 0.008 75)"/>
    <rect x="8" y="8" width="8" height="20" fill="oklch(0.84 0.008 75)"/>
    <rect x="28" y="8" width="8" height="20" fill="oklch(0.84 0.008 75)"/>
    <rect x="48" y="8" width="8" height="20" fill="oklch(0.84 0.008 75)"/>
    <polygon points="0,8 64,8 32,-1" fill="oklch(0.60 0.17 48)"/>
  </g>
  <text x="8" y="45" font-family="Roboto,sans-serif" font-size="13" font-weight="900" fill="oklch(0.53 0.21 25)">APPEAL</text>
  <text x="8" y="59" font-family="Roboto,sans-serif" font-size="8.5" font-weight="700" fill="oklch(0.36 0.010 60)">NY hush-money ruling</text>
</svg>"""


def format_lead_title(title: str, highlight: str, tone: str) -> str:
    esc_title = html.escape(title)
    esc_hl = html.escape(highlight)
    if esc_hl and esc_hl in esc_title:
        return esc_title.replace(
            esc_hl, f'<mark class="hl hl-{tone}">{esc_hl}</mark>', 1
        )
    return esc_title


def build_html() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    counts = audit_data(data)
    all_items = data["leads"] + data["cards"] + data["briefs"]

    # KPIs: calm gray-white/charcoal, only the key figure in passionate red / warm orange
    kpis_html = "".join(
        f'<div class="kpi-item" style="border-left: 3px solid {REGION_COLORS[k["region"]]};">'
        f'<span class="kpi-val">{html.escape(k["value"])}</span>'
        f'<span class="kpi-lbl">{html.escape(k["label"])}</span>'
        f'</div>'
        for k in data["kpis"]
    )

    # Region distribution bar
    reg_bar_html = "".join(
        f'<div class="reg-seg" style="flex:{counts[r]} 0 auto; background:{REGION_COLORS[r]};">'
        f'{r} {counts[r]}</div>'
        for r in REGION_ORDER
    )

    # UTC timeline (5 nodes)
    utc_html = "".join(
        f'<div class="utc-node">'
        f'<div class="utc-dot"></div>'
        f'<span class="utc-time">{html.escape(u["time"])}</span> '
        f'<span class="utc-lbl">{html.escape(u["label"])}</span>'
        f'</div>'
        for u in data["utc_timeline"]
    )

    # 3 Leads
    leads_html = []
    for item in data["leads"]:
        col = REGION_COLORS[item["region"]]
        fg, bg = STATUS_STYLES[item["status"]]
        title_html = format_lead_title(
            item["title"], item.get("highlight", ""), item.get("highlight_tone", "orange")
        )
        leads_html.append(
            f'<article class="lead-col">'
            f'<div class="lead-art">{lead_svg(item["id"])}</div>'
            f'<div class="lead-meta">'
            f'<div class="meta-left">'
            f'<span class="num-badge" style="background:{col};">{item["id"]}</span>'
            f'<span class="loc-txt">{html.escape(item["location"])}</span>'
            f'</div>'
            f'<span class="status-pill" style="color:{fg}; background:{bg};">{item["status"]}</span>'
            f'</div>'
            f'<h2 class="lead-title">{title_html}</h2>'
            f'<p class="lead-sum">{html.escape(item["summary"])}</p>'
            f'</article>'
        )

    # 10 Cards
    cards_html = []
    for item in data["cards"]:
        col = REGION_COLORS[item["region"]]
        fg, bg = STATUS_STYLES[item["status"]]
        cards_html.append(
            f'<article class="mini-card">'
            f'<div class="mini-art">'
            f'{card_svg(item["id"])}'
            f'<div class="mini-top">'
            f'<div class="mini-top-l">'
            f'<span class="mini-num" style="background:{col};">{item["id"]}</span>'
            f'<span class="mini-loc">{html.escape(item["location"])}</span>'
            f'</div>'
            f'<span class="mini-status" style="color:{fg}; background:{bg};">{item["status"]}</span>'
            f'</div>'
            f'</div>'
            f'<h3 class="mini-title">{html.escape(item["title"])}</h3>'
            f'<p class="mini-sum">{html.escape(item["summary"])}</p>'
            f'</article>'
        )

    # 20 Briefs: calm charcoal text & location, small region-colored number dot only
    briefs_html = []
    for item in data["briefs"]:
        col = REGION_COLORS[item["region"]]
        briefs_html.append(
            f'<div class="brief-row">'
            f'<span class="brief-num" style="background:{col};">{item["id"]}</span>'
            f'<span class="brief-loc">{html.escape(item["location"])}:</span> '
            f'<span class="brief-txt">{html.escape(item["text"])}</span>'
            f'</div>'
        )

    map_svg = render_world_map(all_items)
    legend_html = "".join(
        f'<span class="leg-item"><i style="background:{REGION_COLORS[r]};"></i>{r} ({counts[r]})</span>'
        for r in REGION_ORDER
    )
    dc_items = " · ".join(
        f'<span class="dc-key">{html.escape(x.split(":")[0])}:</span> {html.escape(x.split(":", 1)[1].strip())}'
        if ":" in x else html.escape(x)
        for x in data["date_check_excluded"]
    )

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>The World in One Day — {html.escape(data["date_label"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700;900&family=Source+Serif+4:opsz,wght@8..60,700;8..60,800;8..60,900&display=swap" rel="stylesheet"/>
<style>
  :root {{
    /* Neutral gray-white & charcoal base (NO pure black) */
    --paper: oklch(0.985 0.004 80);
    --panel: oklch(0.952 0.005 80);
    --ink: oklch(0.24 0.008 60);
    --ink-2: oklch(0.38 0.008 60);
    --ink-muted: oklch(0.52 0.008 60);
    --rule: oklch(0.86 0.006 80);
    /* Focused theme & accent colors */
    --orange: oklch(0.60 0.17 48);
    --scarlet: oklch(0.53 0.21 25);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    width: 1024px;
    height: 1024px;
    overflow: hidden;
    background: var(--paper);
    color: var(--ink);
    font-family: "Roboto", -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
  }}
  .page {{
    width: 1024px;
    height: 1024px;
    padding: 4px 16px 4px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    gap: 4px;
  }}
  .eyebrow {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 700;
    color: var(--ink-muted);
    letter-spacing: 0.02em;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 2px;
  }}
  .eyebrow-tag {{
    color: var(--orange);
    font-weight: 900;
  }}
  .masthead-wrap {{
    border-bottom: 2px solid var(--ink);
    padding: 0 0 2px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }}
  h1.masthead {{
    font-family: "Source Serif 4", Georgia, serif;
    font-size: 40px;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.02em;
    color: var(--ink);
  }}
  h1.masthead .date-accent {{
    color: var(--scarlet);
  }}
  .kpi-strip {{
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 8px;
    padding: 1px 0;
  }}
  .kpi-item {{
    display: flex;
    flex-direction: column;
    gap: 1px;
    padding-left: 7px;
  }}
  .kpi-val {{
    font-size: 16px;
    font-weight: 900;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
    line-height: 1.05;
  }}
  .kpi-item:first-child .kpi-val,
  .kpi-item:nth-child(2) .kpi-val {{
    color: var(--scarlet);
  }}
  .kpi-lbl {{
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-muted);
    line-height: 1.1;
    white-space: nowrap;
  }}
  .reg-bar {{
    display: flex;
    gap: 2px;
    height: 18px;
    border-radius: 3px;
    overflow: hidden;
  }}
  .reg-seg {{
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: oklch(0.99 0.003 80);
    white-space: nowrap;
    padding: 0 3px;
    font-variant-numeric: tabular-nums;
  }}
  .utc-strip {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--panel);
    padding: 3px 8px;
    border-radius: 3px;
    border-left: 3px solid var(--orange);
  }}
  .utc-hd {{
    font-size: 12px;
    font-weight: 900;
    color: var(--ink);
    white-space: nowrap;
  }}
  .utc-track {{
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
  }}
  .utc-track::before {{
    content: "";
    position: absolute;
    left: 6px;
    right: 6px;
    top: 5px;
    height: 1.5px;
    background: var(--rule);
    z-index: 0;
  }}
  .utc-node {{
    position: relative;
    z-index: 1;
    font-size: 12px;
    color: var(--ink-2);
    white-space: nowrap;
    padding-top: 10px;
  }}
  .utc-dot {{
    position: absolute;
    top: 1px;
    left: 2px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--scarlet);
    border: 2px solid var(--paper);
    outline: 1.2px solid var(--ink-muted);
  }}
  .utc-time {{
    font-weight: 800;
    color: var(--scarlet);
    font-variant-numeric: tabular-nums;
  }}
  .leads {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 6px;
  }}
  .lead-col {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .lead-col + .lead-col {{
    border-left: 1px solid var(--rule);
    padding-left: 14px;
    margin-left: -7px;
  }}
  .lead-art {{
    width: 100%;
    height: 100px;
    border-radius: 3px;
    overflow: hidden;
    border: 1px solid var(--rule);
  }}
  .lead-art svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}
  .lead-meta {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
  }}
  .meta-left {{
    display: flex;
    align-items: center;
    gap: 5px;
  }}
  .num-badge {{
    width: 18px;
    height: 18px;
    border-radius: 50%;
    color: oklch(0.99 0.003 80);
    font-size: 12px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .loc-txt {{
    font-size: 12px;
    font-weight: 700;
    color: var(--ink-2);
    white-space: nowrap;
  }}
  .status-pill {{
    font-size: 12px;
    font-weight: 900;
    padding: 1px 5px;
    border-radius: 2px;
    letter-spacing: 0.01em;
  }}
  h2.lead-title {{
    font-family: "Source Serif 4", Georgia, serif;
    font-size: 19px;
    font-weight: 800;
    line-height: 1.08;
    color: var(--ink);
  }}
  mark.hl {{
    color: inherit;
    padding: 0 2px;
    border-radius: 2px;
  }}
  mark.hl-orange {{ background: oklch(0.89 0.09 52 / 0.72); }}
  mark.hl-red {{ background: oklch(0.90 0.07 26 / 0.72); }}
  mark.hl-amber {{ background: oklch(0.91 0.09 78 / 0.78); }}
  p.lead-sum {{
    font-size: 13px;
    line-height: 1.18;
    color: var(--ink-2);
  }}
  .cards {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 5px 10px;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 6px;
  }}
  .mini-card {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .mini-art {{
    position: relative;
    width: 100%;
    height: 70px;
    border-radius: 3px;
    overflow: hidden;
    border: 1px solid var(--rule);
  }}
  .mini-art svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}
  .mini-top {{
    position: absolute;
    top: 3px;
    left: 4px;
    right: 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2px;
  }}
  .mini-top-l {{
    display: flex;
    align-items: center;
    gap: 3px;
    min-width: 0;
  }}
  .mini-num {{
    width: 17px;
    height: 17px;
    border-radius: 50%;
    color: oklch(0.99 0.003 80);
    font-size: 12px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}
  .mini-loc {{
    font-size: 12px;
    font-weight: 700;
    color: var(--ink);
    background: oklch(0.99 0.003 80 / 0.88);
    padding: 0 3px;
    border-radius: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .mini-status {{
    font-size: 12px;
    font-weight: 900;
    padding: 0 3px;
    border-radius: 2px;
    flex-shrink: 0;
  }}
  h3.mini-title {{
    font-family: "Source Serif 4", Georgia, serif;
    font-size: 14.5px;
    font-weight: 800;
    line-height: 1.08;
    color: var(--ink);
  }}
  p.mini-sum {{
    font-size: 12px;
    line-height: 1.15;
    color: var(--ink-2);
  }}
  .bottom {{
    display: grid;
    grid-template-columns: 364px 1fr;
    gap: 12px;
    flex: 1;
    min-height: 0;
  }}
  .sec-hd {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 3px;
  }}
  .sec-title {{
    background: var(--panel);
    border-left: 3px solid var(--orange);
    padding: 1px 6px;
    font-size: 12px;
    font-weight: 900;
    color: var(--ink);
    white-space: nowrap;
  }}
  .sec-sub {{
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-muted);
  }}
  .map-box {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}
  .map-frame {{
    width: 364px;
    height: 166px;
    border: 1px solid var(--rule);
    border-radius: 4px;
    overflow: hidden;
  }}
  .map-frame svg {{
    width: 100%;
    height: 100%;
    display: block;
  }}
  .map-legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 2px 7px;
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-2);
    line-height: 1.12;
  }}
  .leg-item {{
    display: inline-flex;
    align-items: center;
    gap: 3px;
    white-space: nowrap;
  }}
  .leg-item i {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
  }}
  .date-check {{
    border: 1.8px solid var(--scarlet);
    padding: 3px 6px;
    font-size: 12px;
    line-height: 1.14;
    color: var(--ink-2);
    background: var(--panel);
    border-radius: 2px;
  }}
  .dc-key {{
    font-weight: 700;
    color: var(--scarlet);
  }}
  .briefs-wrap {{
    display: flex;
    flex-direction: column;
  }}
  .briefs-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0 12px;
  }}
  .brief-row {{
    font-size: 12px;
    line-height: 1.15;
    padding: 4.5px 0;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
    overflow: hidden;
    color: var(--ink-2);
  }}
  .brief-num {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 17px;
    height: 17px;
    border-radius: 50%;
    color: oklch(0.99 0.003 80);
    font-size: 12px;
    font-weight: 700;
    margin-right: 3px;
    vertical-align: middle;
  }}
  .brief-loc {{
    font-weight: 700;
    color: var(--ink);
  }}
  .footer {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 600;
    color: var(--ink-muted);
    padding-top: 1px;
  }}
  .ft-legend {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .ft-pill {{
    font-size: 12px;
    font-weight: 900;
    padding: 0 4px;
    border-radius: 2px;
  }}
  .ft-right {{
    color: var(--scarlet);
    font-weight: 800;
  }}
</style>
</head>
<body>
<div class="page">
  <div class="eyebrow">
    <span>{html.escape(data["edition_eyebrow"])}</span>
    <span class="eyebrow-tag">SIFT VERIFIED</span>
  </div>
  <div class="masthead-wrap">
    <h1 class="masthead">THE WORLD IN ONE DAY <span class="date-accent">· {html.escape(data["date_label"])}</span></h1>
  </div>
  <div class="kpi-strip">{kpis_html}</div>
  <div class="reg-bar">{reg_bar_html}</div>
  <div class="utc-strip">
    <span class="utc-hd">THE DAY IN UTC</span>
    <div class="utc-track">{utc_html}</div>
  </div>
  <section class="leads">{"".join(leads_html)}</section>
  <section class="cards">{"".join(cards_html)}</section>
  <section class="bottom">
    <div class="map-box">
      <div class="sec-hd">
        <span class="sec-title">WHERE IT HAPPENED</span>
        <span class="sec-sub">Natural Earth 110m · 191 countries · Pins 1–13, Dots 14–33</span>
      </div>
      <div class="map-frame">{map_svg}</div>
      <div class="map-legend">{legend_html}</div>
      <div class="date-check"><span class="dc-key">DATE CHECK:</span> {dc_items}</div>
    </div>
    <div class="briefs-wrap">
      <div class="sec-hd">
        <span class="sec-title">WORLD IN BRIEF (14–33)</span>
        <span class="sec-sub">20 verified dispatches · 23 Nov 2026</span>
      </div>
      <div class="briefs-grid">{"".join(briefs_html)}</div>
    </div>
  </section>
  <footer class="footer">
    <div class="ft-legend">
      <span><span class="ft-pill" style="color:oklch(0.36 0.08 150);background:oklch(0.94 0.015 150);">CONFIRMED</span> Multi-src</span>
      <span><span class="ft-pill" style="color:oklch(0.36 0.08 245);background:oklch(0.94 0.015 245);">OFFICIAL</span> Gov/UN</span>
      <span><span class="ft-pill" style="color:oklch(0.44 0.11 48);background:oklch(0.95 0.025 55);">CLAIM</span> Unilateral</span>
      <span>AP, AJ, Guardian, France24, UN, ABC, MercoPress</span>
    </div>
    <span class="ft-right">{html.escape(data["date_label"])} · 33 stories · 7 regions</span>
  </footer>
</div>
</body>
</html>
"""
    OUT_HTML.write_text(page_html, encoding="utf-8")
    print(f"Audit passed: 33 stories across 8 region buckets {counts}. Wrote {OUT_HTML}")


if __name__ == "__main__":
    build_html()
