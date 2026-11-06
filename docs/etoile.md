# Étoile — creator & video sampler

`src/scrape_french_creators.py` samples one or more TikTok hashtags and keeps the
videos that match a target market.

## CLI

```bash
.venv/bin/python src/scrape_french_creators.py \
  --market FR \
  --hashtag "blocus, rentree" \
  --count 80 \
  --delay 4 \
  --output-json out/Etoile_FR.json \
  --output-csv  out/Etoile_FR.csv
```

| Flag | Default | Meaning |
|---|---|---|
| `--market` | `FR` | `FR`, `UK`, `ALL` (case-insensitive) |
| `--hashtag` | `fyp` | one or more tags, separated by commas or spaces; `#` optional |
| `--count` | `100` | maximum videos to scan per hashtag |
| `--delay` | `4` | seconds between requests; raise it if you see challenges |
| `--username` | auto | pick a specific account from the local PyTok pool |
| `--headless` | `false` | `false` / `true` / `virtual` (virtual display) |
| `--min-lang-prob` | `0.65` | minimum language probability for a caption to count |
| `--output-json` | `french_creators.json` | JSON output |
| `--output-csv` | `french_creators.csv` | CSV output |

## How the market filter works

A video is kept when **both** the caption language and the creator heuristics
agree with the target market.

**France (`FR`)**
- caption detected as French above `--min-lang-prob`;
- creator bio/name contains French signals: `🇫🇷`, French cities, `.fr`, French
  words, or a French-language bio.

**United Kingdom (`UK`)**
- caption detected as English above the threshold;
- creator contains UK signals: `🇬🇧` / England / Scotland / Wales flags, `£`,
  UK cities, `.co.uk`, UK clothing sizes, or a UK-language bio.

**Global (`ALL`)**
- no language or region filter; everything under the hashtag is exported.

The heuristics are deliberately visible: the output contains
`creator_match_reasons`, `lang_confidence` and `lang_summary` so you can audit
every row instead of trusting a black box.

## Output columns

`market`, `source_hashtag`, `uniqueId`, `nickname`, `user_id`, `verified`,
`signature`, `follower_count`, `following_count`, `creator_heart_count`,
`creator_video_count`, `video_id`, `video_url`, `duration_sec`, `create_time`,
`desc`, `lang_confidence`, `lang_summary`, `creator_match_reasons`,
`play_count`, `digg_count`, `comment_count`, `share_count`, `collect_count`,
`hashtags`.

The XLSX is a styled version of the same table with clickable links and
Morandi-palette section headers.

## Practical guidance

- **Start small.** `--count 40 --delay 6` for a first run; scale up once you
  know the account is not being challenged.
- **One topic per run.** A run with 5 unrelated hashtags produces a mixed pool
  that is hard to analyse; run them separately and merge later.
- **Respect the platform.** This is a research tool. Do not run it continuously,
  do not rotate accounts to evade limits, and do not collect more than you need.
- **Expect noise.** `langdetect` is unreliable on very short captions; the
  creator heuristics can mistake diaspora accounts for local ones. Keep the
  evidence columns and review a sample by hand.

## The XLSX report

`src/excel_exporter.py` writes the Morandi-styled workbook: a highlighted
clickable link column, interaction metrics, creator identity columns, bio and
follower stats, and the region/language evidence block. It has no hidden state
and no network access.
