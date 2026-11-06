# Lumière — structure & culture studio

`src/lumiere_analyzer.py` turns one or two video URLs into an evidence package:
metadata, MP4, captions, comments, shot statistics, a storyboard and an
eight-dimension report.

## CLI

```bash
.venv/bin/python src/lumiere_analyzer.py \
  --urls "https://www.tiktok.com/@user/video/1234567890" \
  --out-dir "$HOME/TikTokResearch/Lumière_视频深析" \
  --comments 20
```

| Flag | Default | Meaning |
|---|---|---|
| `--urls` | required | one or more URLs, separated by spaces/commas; optional `V1:`, `V2:`, `FR:`, `UK:` prefixes |
| `--out-dir` | `~/TikTokResearch/Lumière_视频深析` | output directory |
| `--comments` | `20` | number of top comments to fetch per TikTok video |
| `--no-mp4` | off | skip the MP4 download and the visual analysis |

## Pipeline

1. **Resolve the URL.** TikTok URLs go through PyTok for full metadata, comments
   and caption tracks. Everything else goes through yt-dlp with thinner metadata.
2. **Download the MP4** into `<creator>_<id>/<id>.mp4`.
3. **Extract captions** from the TikTok caption track when present (WebVTT).
4. **Fetch top comments** (TikTok only).
5. **Analyse the footage** with OpenCV: duration, FPS, resolution, brightness,
   contrast, saturation, scene cuts, average shot length, and five frames
   (Hook, 25%, 50%, 75%, CTA) composed into `Storyboard_<id>.png`.
6. **Write the report**: `Lumière_Task1_视频深度分析报表_<timestamp>.xlsx` and
   `Lumière_Task1_AI深析档案_<timestamp>.md`.

## The eight dimensions

1. **Content Style** — genre, format, aesthetic, production pattern.
2. **Video Structure** — hook, development, climax, CTA; cuts and ASL as evidence.
3. **Audience Targeting** — who the video is for, and the signals that address them.
4. **Tone and Language** — register, address, slang, captions, voice.
5. **Visual Presentation** — framing, light, colour, on-screen text, editing.
6. **Engagement Strategy** — the interaction design and the measured interaction
   rates (like / comment / share / save).
7. **Cultural Characteristics** — local codes, references, identities.
8. **Overall Trend Representation** — why this video stands for a wider pattern.

The report also includes a comparison sheet (when you pass two URLs) and a
comment-evidence sheet.

## Customising the narrative

The generated text lives in `build_dimension_insights` in
`src/lumiere_analyzer.py`. It was written for a fashion case study and mentions
Victoria's Secret, haul culture and 18–28-year-old women. Change those strings
for your own corpus; the measured metrics are independent of the template.

The Markdown file is deliberately structured so you can paste it into an LLM
together with the local MP4 to produce a final bilingual report.

## Supported URLs

- **TikTok** — full pipeline (metadata, comments, captions, MP4).
- **YouTube / Instagram / X / Bilibili / Xiaohongshu / etc.** — yt-dlp fallback:
  metadata and MP4 only; no TikTok comments or caption tracks.

## Limits

- Private, deleted or region-locked videos cannot be fetched.
- Comment sampling is the top N by relevance, not a random sample. It is
  evidence, not a representative survey.
- Scene-cut detection is threshold-based; fast motion can be read as a cut.
  Review the storyboard before quoting the ASL.
- The eight-dimension text is a first draft. Edit it.
