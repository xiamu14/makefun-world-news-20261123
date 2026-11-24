# The World in One Day — Monday, 23 November 2026

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/xiamu14/makefun-world-news-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/xiamu14/makefun-world-news-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

Editorial flat-vector world news infographic for `news-image-20261123` on [make.fun](https://make.fun/bounty/news-image-20261123).

## Structure
- `edition-data.json`: 33 SIFT-verified news stories from Monday, 23 November 2026 across all 7 continents + Global, plus `DATE CHECK` exclusions.
- `build_html.py`: Generates `index.html` with warm newsprint broadsheet styling, `better-colors` OKLCH palette (no pure black), `unslop` spacing/typography, 13 bespoke flat-vector SVG illustrations, and a 191-country Natural Earth 110m SVG world map.
- `entry.png`: Deterministic `1024×1024` PNG compressed with `oxipng`.
- `main.ts`: Copies `entry.png` to `MAKEFUN_OUTPUT_DIR` (or `/output`).

## Run
```bash
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```
