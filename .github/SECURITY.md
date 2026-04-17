# Security Policy

## Supported Versions

Only the current release is actively maintained. Security fixes are not back-ported to earlier versions.

| Version | Supported |
|---------|-----------|
| 1.3.x   | ✅        |
| < 1.3   | ❌        |

## Scope

Sruthi is a **local command-line tool** — it has no web server, no inbound network ports, and no multi-user access control. The realistic attack surface is:

| Area | Notes |
|------|-------|
| API credentials | ACRCloud, Sarvam AI, and Anthropic API keys stored in env vars or a local `.env` file |
| External network calls | ShazamIO (no key), ACRCloud, Sarvam AI, cover art URLs via `requests`, Anthropic API (GUI only) |
| Local SQLite database | `music.db` — stores file paths, music metadata, and MD5 hashes; no passwords or personal data |
| MP3 file handling | `mutagen` for ID3 tags, `pydub`/`ffmpeg` for audio slicing |

## Credential Handling

API keys are read exclusively from environment variables (or a `.env` file in the project root that is loaded at startup). Keys are never written to the database or logged.

**Never commit `.env` to version control.** Verify with `git check-ignore -v .env` before pushing.

Required secrets and where they are used:

| Variable | Service | Used by |
|---|---|---|
| `ACRCLOUD_HOST` | ACRCloud | `--acrcloud` pass |
| `ACRCLOUD_ACCESS_KEY` | ACRCloud | `--acrcloud` pass |
| `ACRCLOUD_ACCESS_SECRET` | ACRCloud | `--acrcloud` pass |
| `SARVAM_API_KEY` | Sarvam AI | `--transliterate` pass |
| `ANTHROPIC_API_KEY` | Anthropic | `gui.py` (optional NL query GUI) |

## Known Limitations

- **No input sanitisation on filenames** — Sruthi processes MP3s from a folder you control. Do not point it at untrusted third-party archives without inspecting the files first.
- **Cover art downloads** — `tagger.py` fetches JPEG data from Shazam CDN URLs and embeds them into ID3 tags. The URL comes from the Shazam API response; a compromised or spoofed response could supply a malicious URL (low practical risk for a local tool).
- **`music.db` is unencrypted** — it contains file paths and music metadata. If your machine is shared, ensure the database file has appropriate filesystem permissions.

## Reporting a Vulnerability

Open a **private** security advisory on GitHub:
**[github.com/fordevices/sruthi/security/advisories/new](https://github.com/fordevices/sruthi/security/advisories/new)**

Please include:
- A description of the vulnerability
- Steps to reproduce
- The version affected
- Any suggested fix if you have one

You can expect an initial response within 7 days. For low-severity issues (e.g. a dependency version bump), opening a regular issue is fine.
