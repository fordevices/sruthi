# Sruthi — Release History

All work is tracked as GitHub issues:
https://github.com/fordevices/sruthi/issues

Bugs → label `bug` | Features → label `enhancement`

---

## v1.2.0 *(in development)*

- `--transliterate` pass — converts `Artist` ID3 tag to native script (Tamil/Devanagari) using Sarvam AI; each unique artist name cached in `music.db` after the first call
- Read-only GUI (`gui.py`) — natural language → SQL over `music.db` via Claude API; opens in browser at `http://localhost:8501`

Issues: #26 (transliteration), #27 (GUI)
Open: #25 (song-level language detection — future release)

---

## v1.1.0 — released April 3, 2026

- iTunes metadata search added to `--metadata-search` pass
- ID3 tag query: reads existing tags before falling back to cleaned filename
- `--all` flag: run `--metadata-search` across all songs, not just `no_match`
- `--folder` flag: scope any pass to a specific subfolder

Tested on 5,550 files: **68% automated match rate** (3,768 identified, 1,700 no_match, 4 errors).

Issues fixed: #7, #11, #13, #15, #16, #17, #18, #19, #22

---

## v1.0.0 — released March 2026

Initial release.

- ShazamIO fingerprint identification (Stage 1)
- Manual review CLI (Stage 2)
- Mutagen ID3 tag writer (Stage 3)
- File rename + move to `Music/<Language>/<Year>/<Album>/` (Stage 4)
- Resume-safe SQLite tracking (`music.db`)
- AcoustID fallback pass (`--acoustid`)
- `--dry-run`, `--stats`, `--check`, `--zeroise` utilities
