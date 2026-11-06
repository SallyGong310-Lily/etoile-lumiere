# Contributing

Thanks for considering a contribution.

## Before you start

- Open an issue for anything larger than a typo or a small fix.
- Do not include scraped videos, captions, comments, account cookies or personal
  data in issues, pull requests or test fixtures.
- Keep the tools research-oriented. PRs that add evasion, account rotation or
  bulk-harvesting features will be declined.

## Development setup

```bash
git clone https://github.com/<your-account>/etoile-lumiere.git
cd etoile-lumiere
./scripts/install.sh
.venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login
```

## Checks

```bash
make test          # python -m compileall -q src
```

There is no network test suite: the tools depend on a live TikTok session and a
real browser, so tests are manual. A useful manual check is:

1. run Étoile with `--count 5 --delay 8` on a small hashtag;
2. run Lumière on one public TikTok URL with `--no-mp4`;
3. confirm the XLSX and MD files open and contain the expected rows.

## Style

- Python: 4 spaces, type hints where they already exist, no new dependencies
  without a reason.
- Shell: `zsh`, quote paths, keep the portable `ETOILE_HOME` / `LUMIERE_HOME`
  fallbacks.
- Commits: imperative subject, explain the why in the body.

## Pull requests

- One topic per PR.
- Describe how you tested it (macOS version, Python version, command used).
- Update `CHANGELOG.md` for user-visible changes.
