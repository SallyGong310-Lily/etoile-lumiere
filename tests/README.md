# Tests

The project depends on a live TikTok session and a real browser, so there is no
offline integration suite. CI runs a syntax check only:

```bash
make test
```

Manual smoke test:

1. `./scripts/install.sh`
2. `.venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login`
3. `.venv/bin/python src/scrape_french_creators.py --market FR --hashtag fyp --count 5 --delay 8 --output-json /tmp/e.json --output-csv /tmp/e.csv`
4. `.venv/bin/python src/lumiere_analyzer.py --urls "<a public TikTok URL>" --no-mp4 --out-dir /tmp/lumiere`
5. Open `/tmp/e.csv` and `/tmp/lumiere/*.xlsx`.

Never commit the outputs.
