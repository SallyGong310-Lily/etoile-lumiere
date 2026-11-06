# Architecture

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│ Étoile                       │        │ Lumière                      │
│ scripts/etoile_launcher.sh   │        │ scripts/lumiere_launcher.sh  │
│   └─ osascript dialogs       │        │   └─ osascript dialogs       │
│      └─ scrape_french_        │        │      └─ lumiere_analyzer.py  │
│         creators.py           │        │         ├─ pytok (metadata,  │
│         ├─ pytok (hashtag)    │        │         │   comments, captions)│
│         ├─ langdetect         │        │         ├─ yt-dlp (fallback)  │
│         └─ excel_exporter.py  │        │         ├─ OpenCV / FFmpeg    │
└──────────────┬───────────────┘        │         └─ openpyxl / Markdown│
               │                        └──────────────┬───────────────┘
               ▼                                       ▼
      JSON / CSV / XLSX                      MP4 + storyboard + XLSX + MD
```

## Modules

| Module | Responsibility |
|---|---|
| `src/scrape_french_creators.py` | Étoile CLI; hashtag walk; language + creator filtering; JSON/CSV export. |
| `src/excel_exporter.py` | Styled XLSX writer for Étoile; pure function, no network. |
| `src/lumiere_analyzer.py` | Lumière CLI; URL resolution; download; caption/comment capture; CV analysis; report generation. |
| `scripts/*_launcher.sh` | Native dialogs; account check; run the CLI in Terminal; open the result. |
| `scripts/install.sh` | venv + dependencies + Camoufox browser. |
| `scripts/build_app.sh` | Builds the two `.app` bundles. |

## Data flow

1. The launcher collects market, hashtags, sample size (Étoile) or URLs
   (Lumière).
2. The CLI uses PyTok's account pool (`~/.pytok`) to open a logged-in session.
3. Étoile walks the hashtag feed, applies the filters and appends rows.
4. Lumière resolves each URL, downloads media, and runs the analysis.
5. Both write to a user-chosen output directory; nothing is uploaded.

## What is deliberately not included

- No vendored PyTok copy. PyTok is installed from upstream because it is
  PolyForm Noncommercial and should be updated independently.
- No scraped datasets. The repository ships code and examples only.
- No credentials. The account pool lives in `~/.pytok` and is never read by the
  code that writes reports.
