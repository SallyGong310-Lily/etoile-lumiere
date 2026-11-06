# Étoile & Lumière

**Two small macOS apps for studying Gen Z TikTok trends in France and the UK.**

[中文说明](README.zh-CN.md) · [Setup](docs/setup.md) · [Legal & ethics](docs/legal.md)

> **Research tooling, not a data vendor.** Étoile and Lumière drive a logged-in
> TikTok session through [PyTok](https://github.com/MEOMcGill/pytok). TikTok's
> Terms of Service prohibit unauthorised scraping, and PyTok itself is licensed
> **PolyForm Noncommercial 1.0.0**. Read [docs/legal.md](docs/legal.md) before
> using this project, and do not publish scraped videos, captions or comments.

---

## What the two apps do

| | **Étoile** | **Lumière** |
|---|---|---|
| Job | Sample hashtags and keep the creators/videos that match a market | Take selected video URLs and produce a structural + cultural analysis package |
| Input | Market (`FR` / `UK` / `ALL`), one or more hashtags, sample size | One URL, or a pair of URLs to compare |
| Output | JSON + CSV + styled XLSX (one row per video) | MP4, auto-captions, top comments, shot-cut stats, 5-frame storyboard, 8-dimension XLSX + Markdown |
| Best for | Building a candidate pool from scratch | Deep-reading a shortlist |

The intended workflow is **Étoile → shortlist → Lumière**: sample broadly with
Étoile, pick representative videos, then let Lumière extract the evidence you
need for a content/structure/audience analysis.

```
 hashtags ──► Étoile ──► JSON / CSV / XLSX ──► shortlist ──► Lumière ──► MP4 + storyboard
                │                                              │            + comments
                └─ market filter (FR / UK / ALL)               └─ 8-dimension report
```

## Features

### Étoile — creator & video sampler

- Scrapes a hashtag through a real browser session (Camoufox via PyTok), so it
  can survive the challenges that block plain HTTP scrapers.
- Filters by market using **two signals**: caption language (`langdetect`) and
  creator-level heuristics (flags, cities, currency, domains, bio language).
- Supports `FR`, `UK` and `ALL`, multiple hashtags per run, and a configurable
  request delay.
- Writes JSON, CSV and a Morandi-palette XLSX with clickable video links and a
  language/region evidence column.

### Lumière — structure & culture studio

- Fetches full metadata, the MP4, auto-caption tracks (when present) and the top
  comments for each TikTok URL.
- Runs OpenCV/FFmpeg analysis: duration, FPS, resolution, brightness, contrast,
  saturation, scene cuts, average shot length, and a 5-frame storyboard
  (Hook / 25% / 50% / 75% / CTA).
- Produces an eight-dimension report:
  1. Content Style
  2. Video Structure
  3. Audience Targeting
  4. Tone and Language
  5. Visual Presentation
  6. Engagement Strategy
  7. Cultural Characteristics
  8. Overall Trend Representation
- Accepts non-TikTok URLs through a yt-dlp fallback (metadata is thinner there:
  no TikTok comments or caption tracks).

## Requirements

- macOS 12 or newer (the launchers use `osascript` dialogs and `open`)
- Python 3.10–3.12
- A TikTok account you are willing to use for research. **Use a dedicated
  account**, not your personal one.
- ~2 GB of disk for the Python environment and the Camoufox browser.

## Quick start

```bash
git clone https://github.com/SallyGong310-Lily/etoile-lumiere.git
cd etoile-lumiere

# 1) Create .venv, install dependencies, download Camoufox
./scripts/install.sh

# 2) Log in once (a browser window opens; the session is stored locally by PyTok)
.venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login

# 3) Launch either app
./scripts/etoile_launcher.sh
./scripts/lumiere_launcher.sh
```

The account label is local only. It is never sent anywhere by this project and
never stored in the repository.

## CLI usage

Étoile:

```bash
.venv/bin/python src/scrape_french_creators.py \
  --market FR \
  --hashtag "blocus, rentree, octobrerose" \
  --count 80 \
  --delay 4 \
  --output-json out/Etoile_FR_blocus.json \
  --output-csv  out/Etoile_FR_blocus.csv
```

Lumière:

```bash
.venv/bin/python src/lumiere_analyzer.py \
  --urls "https://www.tiktok.com/@user/video/1234567890" \
  --out-dir "$HOME/TikTokResearch/Lumière_视频深析" \
  --comments 20
```

Compare two videos (the launcher uses the same `V1:` / `V2:` prefixes):

```bash
.venv/bin/python src/lumiere_analyzer.py \
  --urls "V1:https://www.tiktok.com/@a/video/111 V2:https://www.tiktok.com/@b/video/222"
```

## Build the macOS apps

```bash
./scripts/build_app.sh
open dist/Étoile.app
open dist/Lumière.app
```

The generated bundles are thin wrappers: they locate the repository and run the
same launchers. If you move the `.app` outside the repository, set
`ETOILE_HOME` / `LUMIERE_HOME` to the repository path.

## Outputs

| App | Files |
|---|---|
| Étoile | `Etoile_<MARKET>_<tags>.json`, `.csv`, `.xlsx` in `$ETOILE_OUTPUT_DIR` (default `~/TikTokResearch/Étoile`) |
| Lumière | `Lumière_Task1_视频深度分析报表_<timestamp>.xlsx`, `Lumière_Task1_AI深析档案_<timestamp>.md`, `Storyboard_<id>.png`, and `<creator>_<id>/<id>.mp4` in `$LUMIERE_OUTPUT_DIR` (default `~/TikTokResearch/Lumière_视频深析`) |

## Project layout

```
.
├── src/
│   ├── scrape_french_creators.py   # Étoile CLI
│   ├── lumiere_analyzer.py         # Lumière CLI
│   └── excel_exporter.py           # Morandi XLSX writer for Étoile
├── scripts/
│   ├── install.sh                  # venv + deps + camoufox
│   ├── etoile_launcher.sh          # native dialogs → scraper
│   ├── lumiere_launcher.sh         # native dialogs → analyzer
│   └── build_app.sh                # build dist/*.app
├── docs/                           # setup, usage, architecture, legal
├── assets/                         # app icons
└── examples/                       # example hashtag/URL lists
```

## Known limitations

- **Market detection is heuristic.** Language detection and bio keywords can
  misclassify diaspora creators, bilingual accounts and creators who do not fill
  in a location. Every row keeps the evidence used, so you can audit it.
- **Lumière's narrative templates are tuned for a fashion case study.** The
  generated "insights" in `build_dimension_insights` reference Victoria's Secret,
  haul culture and 18–28-year-old women. For other genres, edit the prompt
  strings in `src/lumiere_analyzer.py`; the measured metrics (cuts, ASL,
  brightness, engagement rates) are genre-neutral.
- **The eight-dimension text is a first draft, not a verdict.** Treat it as
  structured evidence to review, not as an automatically correct analysis.
- **APIs and selectors change.** PyTok is pinned to `v0.3.0` in `requirements.txt`; if the upstream API moves, pin a tested commit.
- **Rate limits and account risk are real.** Keep `--delay` at 4 seconds or
  higher, run small batches, and expect occasional challenges.

## Legal, ethics and privacy

This project is for **non-commercial academic research**. Before you publish
anything based on it:

- Read and comply with TikTok's Terms of Service and your institution's ethics
  policy.
- Do not redistribute scraped videos, captions, comments or creator profiles.
- Treat "public" data as personal data: GDPR and equivalent regimes still apply.
- Do not use the tools for harassment, mass profiling, or bypassing access
  controls.
- PyTok is PolyForm Noncommercial 1.0.0 — see [NOTICE](NOTICE) and
  [docs/legal.md](docs/legal.md).

## License

The code in this repository is MIT-licensed (see [LICENSE](LICENSE)).
Third-party dependencies keep their own licenses; in particular **PyTok is
noncommercial**. If you need a commercial license, replace the PyTok layer or
obtain permission from its authors.

## Acknowledgements

- [PyTok](https://github.com/MEOMcGill/pytok) by Ben Steel and contributors —
  the browser-backed TikTok client this project is built on.
- [Camoufox](https://github.com/daijro/camoufox) and
  [Playwright](https://playwright.dev/python/) for the browser automation layer.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the non-TikTok fallback.
- The Morandi colour system used in the reports.
