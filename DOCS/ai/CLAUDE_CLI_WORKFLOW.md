# Claude CLI — Project Onboarding Prompt

> **This file is for Claude CLI sessions only.**
> For the human PR workflow, see [CONTRIBUTING.md](../engineering/CONTRIBUTING.md).
> For project architecture, see [ARCHITECTURE.md](../engineering/ARCHITECTURE.md).

> Run this ONCE at the start of any new Claude CLI session before working on an issue.
> It teaches Claude CLI what the project is, how it works, and what the rules are.
> After running this, paste the issue prompt from CONTRIBUTING.md.

---

```
You are a disciplined contributor to the Sruthi project.
Your job is to implement GitHub issues — one at a time, surgically, with verification.

Before you do anything else, read and absorb the following files.
After reading each one, print a single line confirming what you read and the key
constraint or fact you need to remember from it. Do not summarise at length —
one line per file is enough.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — READ THE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read CONTRIBUTING.md in full.

Key things to extract and state:
  - What you must read before writing any code
  - What you must never modify
  - The branch naming convention
  - The commit message format
  - The verification requirement

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2a — READ THE ARCHITECTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read ../engineering/ARCHITECTURE.md in full.

Key things to extract and state:
  - The four pipeline stages and which module owns each one
  - The module responsibility of each of the 7 pipeline files
  - The output folder pattern: Music/<Language>/<Year>/<Album>/<Title>.mp3
  - The full CLI flag surface

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2b — READ THE DATABASE REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read ../engineering/DATABASE.md in full.

Key things to extract and state:
  - The status flow: pending → identified → no_match → tagged → done → error
  - The field priority rule: final_* beats shazam_* beats fallback
  - The song ID format: max-XXXXXX
  - What triggers each status transition

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2c — SKIM DESIGN DECISIONS (unless issue touches Stage 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read ../engineering/DESIGN_DECISIONS.md (skim unless issue touches Stage 1 / identify.py).

Key things to extract and state:
  - Why ShazamIO was chosen (one sentence)
  - The ShazamIO response parsing structure: subtitle is artist, sections.metadata
    holds album/year — this is a common source of bugs
  - The fallback plan if ShazamIO breaks

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — READ THE LIVE CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Read each of these files. For each, state the key function(s) it exports
and any gotcha or non-obvious behaviour worth knowing:

  pipeline/config.py
  pipeline/db.py
  pipeline/identify.py
  pipeline/review.py
  pipeline/tagger.py
  pipeline/organizer.py
  pipeline/runner.py
  main.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — INSPECT THE LIVE DATABASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run these commands and report the output:

  python3 main.py --check
  python3 main.py --stats

Also run:
  python3 -c "
  import sqlite3
  conn = sqlite3.connect('music.db')
  conn.row_factory = sqlite3.Row
  rows = conn.execute(
    'SELECT song_id, language, status, shazam_title, final_year, override_used '
    'FROM songs ORDER BY song_id LIMIT 10'
  ).fetchall()
  for r in rows: print(dict(r))
  "

State:
  - Total songs in DB and status breakdown
  - How many have override_used=1
  - The song_id of the highest-numbered row (so you know where the counter is)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — CONFIRM YOU ARE READY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After completing steps 1–4, print this checklist with ✓ or ✗ for each item:

  [ ] CONTRIBUTING.md read — rules understood
  [ ] ../engineering/ARCHITECTURE.md read — modules, stages, CLI surface understood
  [ ] ../engineering/DATABASE.md read — schema, status flow, field priority understood
  [ ] ../engineering/DESIGN_DECISIONS.md skimmed — ShazamIO parsing quirks noted
  [ ] All 7 pipeline modules read — functions and gotchas noted
  [ ] main.py read — full CLI surface known
  [ ] python3 main.py --check passed — DB is healthy
  [ ] python3 main.py --stats run — current state known
  [ ] Highest song_id noted — counter position known
  [ ] No code written yet — read-only phase complete

Once all items are ✓, print:
  "Ready. Paste the issue prompt from CONTRIBUTING.md."

If any item is ✗, explain why and what is needed to resolve it before continuing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STANDING RULES FOR THIS SESSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These apply for the entire session. You do not need to be reminded of them:

1. One issue per session. If you discover a second problem while implementing,
   note it and tell me to open a new GitHub issue. Do not fix it in this session.

2. Smallest possible change. Fix exactly what the issue describes.
   Do not refactor adjacent code, rename things, or improve code not in scope.

3. Never modify music.db directly. All DB writes go through db.py functions.

4. Never work on main. Remind me to create a branch before you write any code:
     git checkout -b issue-<N>-<short-description>

5. Every session ends with a runnable verification command and its expected output.
   You paste the command. I run it. I paste the result back. Only then is it done.

6. Update README.md and ../guide/USER_GUIDE.md in the same commit if any CLI flag,
   config constant, or user-facing behaviour changes.

7. Print the exact git commit message at the end:
     fix: <description> (closes #N)
     feat: <description> (closes #N)
```

---

## How to use this

### Starting a new Claude CLI session for an issue

1. Open Claude CLI in the project root directory
2. Paste the onboarding prompt above — Claude CLI reads the code and DB
3. Wait for the "Ready. Paste the issue prompt." confirmation
4. Copy the issue prompt template from CONTRIBUTING.md, fill it in, paste it
5. Claude CLI implements. You run the verification command. Paste the result.
6. Repeat until verification passes.
7. Use the commit message Claude CLI prints. Push. Open PR. Close issue.

### The two-prompt structure

Every session has exactly two prompts:

```
Prompt 1 (onboarding):   reads codebase, checks DB, confirms ready
                         — key sources: ../engineering/ARCHITECTURE.md + ../engineering/DATABASE.md
Prompt 2 (issue):        implements exactly one GitHub issue
```

Never skip Prompt 1. A Claude CLI session that starts directly with the issue
prompt — without reading the live code and DB state first — will make
assumptions about the code that may no longer be true.

### When to re-run the onboarding prompt

- Any time you start a new Claude CLI session (context is not preserved)
- Any time more than a few days have passed since the last session
- Any time a previous session changed code or the DB significantly

### Session length expectation

| Issue type | Expected session length |
|---|---|
| Simple bug (one function fix) | 10–20 minutes |
| Medium bug (two modules) | 20–40 minutes |
| Small feature (one new flag) | 20–40 minutes |
| Medium feature (new stage behaviour) | 40–90 minutes |
| Large feature (new module or DB migration) | Split into multiple issues |

If a session is taking longer than 90 minutes, the issue is probably too large.
Stop, close the partial work, and split the issue into two smaller ones on GitHub.
