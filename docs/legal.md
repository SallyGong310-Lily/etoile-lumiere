# Legal, ethics and privacy

This is not legal advice. It is a checklist for a researcher who wants to use
the tools responsibly.

## 1. Platform terms

TikTok's Terms of Service prohibit unauthorised scraping, automated access and
collection of personal data. Using this project may breach those terms and can
lead to account restrictions. You are responsible for your own use. If your
institution requires it, seek approval from your ethics board before collecting.

## 2. PyTok's licence

PyTok is licensed under **PolyForm Noncommercial 1.0.0**. It is not MIT and it is
not OSI-approved. In practice:

- you may use, modify and share it for **non-commercial** purposes;
- you may not use it for commercial purposes;
- if you distribute a work that includes PyTok, you must pass on its licence and
  the required notice.

This repository does not vendor PyTok, but it installs it. If your use is
commercial, replace the client layer or obtain a licence from PyTok's authors.
See [NOTICE](../NOTICE).

## 3. Personal data

TikTok profiles, captions, comments and faces are personal data under GDPR and
similar regimes, even when they are public. For research:

- collect the minimum you need;
- do not publish identifiable creator or commenter data;
- store raw data on an encrypted disk, not in a public repository;
- delete raw media when the analysis is done, or keep it under your
  institution's retention policy;
- aggregate before you publish (e.g. report rates, not individual handles).

The `.gitignore` excludes the usual output patterns, but it is not a substitute
for checking `git status` before every push.

## 4. Research ethics

- Do not use the tools to harass, dox, mass-profile or monitor individuals.
- Do not scrape private, deleted or access-restricted content.
- Do not use multiple accounts to evade rate limits or bans.
- If you study minors, follow your institution's additional safeguards.
- Cite the platform and the collection date; report the limitations of the
  sample (hashtag-based, non-random, time-bound).

## 5. No warranty

The software is provided "as is". The authors are not responsible for account
bans, data loss, legal claims or errors in the generated analysis.
