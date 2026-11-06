# Security policy

## What counts as a vulnerability

- Code that leaks the local TikTok session, cookies or account pool contents.
- Code that writes credentials or personal data into reports or logs.
- Command injection through hashtags, URLs or file names.
- Path traversal through `--out-dir` or creator names.

## Reporting

Please use GitHub's **Security → Report a vulnerability** flow (private
advisory), not a public issue. Include the version, macOS version and a minimal
reproduction. Do not attach real cookies or account data.

## Scope

The tools drive a browser and download media from third-party platforms. A
platform blocking, challenging or rate-limiting an account is not a security
vulnerability. A missing sanitisation step that lets a video title or creator
name escape into a shell command **is**.
