# Contributing to Sruthi

> **First time here?** Read [README.md](README.md) first.
> **Using Claude CLI to implement an issue?** See [CLAUDE_CLI_WORKFLOW.md](CLAUDE_CLI_WORKFLOW.md).

This document covers two things:
1. The GitHub workflow for humans raising bugs and features
2. The Claude CLI workflow for implementing them — how to use Claude CLI
   as a disciplined contributor that reads the codebase before touching it

---

## For humans — raising an issue

Every change to this project starts as a GitHub issue. No exceptions.

### Bug report

Go to: https://github.com/fordevices/sruthi/issues/new

Use this template:

```
**Describe the bug**
One clear sentence describing what went wrong.

**Command you ran**
python3 main.py Input/Tamil/ --stage 1

**Expected behaviour**
What you expected to happen.

**Actual behaviour**
What actually happened. Paste the relevant lines from the terminal.

**Run log**
Paste the relevant section from runs/<timestamp>/run.log

**DB state at time of error**
python3 main.py --stats
(paste the output)

**Environment**
- OS: macOS 14 / Ubuntu 22.04 / Windows 11
- Python version: 3.11.2
- shazamio version: pip show shazamio | grep Version
```

Label it: `bug`

### Feature request

```
**What do you want to do that you cannot do now?**
One clear sentence.

**Why is this useful?**
Who benefits and how.

**What module would this touch?**
identify.py / review.py / tagger.py / organizer.py / runner.py / main.py / db.py
— see ARCHITECTURE.md for module responsibilities

**Acceptance criteria**
A bullet list of specific, testable things that must be true for this to be done.
Example:
- Running python3 main.py Input/ --format flac processes .flac files
- .flac files are tagged with the same ID3-equivalent tags as .mp3
- DB schema unchanged — no new columns needed
```

Label it: `enhancement`

---

## For Claude CLI — implementing an issue

The sections below are the workflow and prompt structure for using Claude CLI
to implement a GitHub issue. Read this entire file before starting any session.

### Core rule

**Claude CLI reads before it writes.**

Every session starts with Claude CLI reading:
1. This file (CONTRIBUTING.md)
2. ARCHITECTURE.md  — pipeline stages, modules, status flow, CLI surface
3. DATABASE.md      — full schema, field priority rule, status meanings
4. (if issue touches identification) DESIGN_DECISIONS.md — ShazamIO
   response structure, API trade-offs, fallback plan
5. README.md             — quick orientation only, not architecture
6. The specific module(s) the issue touches

Only after reading all of the above does it write any code.

### What Claude CLI must never do

- Modify `music.db` directly
- Change the DB schema without an explicit schema migration plan
- Add new CLI flags without updating README.md CLI reference table
- Change `resolve()` logic in tagger.py or organizer.py without updating both
- Add a new dependency without adding it to `requirements.txt`
- Commit code that does not pass its own verification commands
- Close an issue without a verification command whose output can be pasted

---

## The workflow — step by step

### Step 1 — Issue is raised on GitHub

Someone opens an issue. It gets triaged, labelled, and assigned.
The issue number is the anchor for everything that follows. e.g. `#7`

### Step 2 — Create a branch

```bash
git checkout -b issue-7-flac-support
```

Branch naming: `issue-<number>-<short-description>`
Always branch from `main`. Never work directly on `main`.

### Step 3 — Paste the Claude CLI session prompt

Use the prompt template in the next section. Fill in the issue number,
issue title, and issue body. Paste into Claude CLI from the project root.

### Step 4 — Claude CLI implements, you verify

Claude CLI will implement the change and end with a verification command.
Run the verification command. Paste the output back into Claude CLI if
anything needs fixing. Repeat until the verification passes cleanly.

### Step 5 — Commit

```bash
git add .
git commit -m "fix: <one line description> (closes #7)"
# or
git commit -m "feat: <one line description> (closes #7)"
```

Commit message format:
- `fix:` for bugs
- `feat:` for new features
- `docs:` for documentation only
- `refactor:` for internal changes with no behaviour change

Always include `(closes #<number>)` — GitHub will auto-close the issue on merge.

### Step 6 — Push the branch

```bash
git push -u origin issue-7-flac-support
```

### Step 7 — Open a pull request on GitHub

Title: same as the commit message
Body: paste the verification output that confirmed it worked
Link: mention the issue number in the PR body — `Closes #7`

### Step 8 — Merge and tag (if significant)

For bug fixes: merge directly, no new version tag needed.
For new features: merge, then tag a new minor version:

```bash
git checkout main
git pull
git tag -a v1.1.0 -m "v1.1.0 — <feature name>"
git push origin v1.1.0
```

Version numbering:
- `v1.0.x` — bug fixes
- `v1.x.0` — new features
- `v2.0.0` — breaking changes (schema change, CLI flag removed, behaviour change)

---

## Claude CLI session prompt template

Copy this entire block, fill in the placeholders marked with <ANGLE BRACKETS>,
and paste into Claude CLI from the project root directory.

```
You are implementing a GitHub issue for the Sruthi project.

Before writing any code, read these files in this order:
  1. CONTRIBUTING.md              — rules and constraints
  2. ARCHITECTURE.md         — pipeline stages, modules, status flow
  3. DATABASE.md             — schema, field priority, status meanings
  4. <MODULE_FILE(S)>             — the specific file(s) this issue touches
  5. README.md                    — skip unless issue is docs-only
  6. Run: python3 main.py --check — confirm DB is healthy before starting

Do not modify music.db. Do not change the DB schema unless the issue explicitly
requires it and you have described the migration plan first.
Do not add CLI flags without updating the README.md CLI reference table.
Do not add dependencies without adding them to requirements.txt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISSUE #<NUMBER> — <TITLE>
Label: <bug / enhancement>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<PASTE THE FULL ISSUE BODY HERE — description, steps to reproduce or
acceptance criteria, and any context from the comments>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files you are allowed to modify for this issue:
  <list the specific files — e.g. pipeline/identify.py, main.py, README.md>

Files you must NOT modify:
  music.db, Music/, Input/, runs/, ../guide/USER_GUIDE.md (unless issue is docs-only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before writing any code, describe in plain text:
  1. What function(s) you will add or change and why
  2. What the before/after behaviour looks like
  3. Whether any DB columns, CLI flags, or config constants are affected
  4. Whether requirements.txt needs updating

Wait for confirmation before writing the code if the approach is non-obvious.
For straightforward bugs, proceed directly to the implementation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

End the session with a specific, runnable verification command.
The output of that command must be pasteable as evidence the issue is fixed.

Good verification commands:
  python3 main.py Input/test_case/ --stage 1     (and paste the result line)
  python3 main.py --stats                        (and paste the breakdown)
  python3 -c "..."                               (targeted DB query)
  python3 -m pytest tests/test_<module>.py -v   (if tests exist)

Bad verification commands:
  "check that it works" — not runnable
  "review the code" — not measurable
  "it should be fine" — not verifiable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER IMPLEMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When the verification passes, Claude CLI must:
  1. Update README.md if any CLI flags, config constants, or behaviour changed
  2. Update ../guide/USER_GUIDE.md if the change affects how a user operates the tool
  3. Print the exact git commit message to use:
       fix: <description> (closes #<number>)
     or
       feat: <description> (closes #<number>)
```

---

## Filled-in example — bug fix

Here is a complete example using a real-world scenario so you can see
exactly how to fill in the template.

**The GitHub issue:**
> **#8 — Stage 1 crashes on .mp3 files with no ID3 header when checking duration**
> Label: bug
> When running Stage 1 on a raw MP3 with no existing tags, the short-file guard
> raises `mutagen.mp3.HeaderNotFoundError` and the entire run stops instead of
> logging the file as no_match and continuing.
> Command: `python3 main.py Input/Tamil/ --stage 1`
> Error: `HeaderNotFoundError: can't sync to MPEG frame`

**The filled-in prompt:**

```
You are implementing a GitHub issue for the Sruthi project.

Before writing any code, read these files in this order:
  1. CONTRIBUTING.md
  2. ARCHITECTURE.md
  3. DATABASE.md
  4. pipeline/identify.py
  5. README.md — skip unless needed

Do not modify music.db. Do not change the DB schema.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISSUE #8 — Stage 1 crashes on MP3s with no ID3 header
Label: bug
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When running Stage 1 on a raw MP3 with no existing tags, the short-file guard
raises HeaderNotFoundError and the entire run stops instead of logging the
file as no_match and continuing.

Command: python3 main.py Input/Tamil/ --stage 1
Error:   HeaderNotFoundError: can't sync to MPEG frame

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files allowed: pipeline/identify.py
Files not allowed: music.db, Music/, Input/, runs/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before writing code, describe the fix.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create a headerless MP3:
  ffmpeg -f lavfi -i "sine=frequency=440:duration=5" -f mp3 /tmp/noheader.mp3
  cp /tmp/noheader.mp3 Input/English/

Run: python3 main.py Input/English/noheader.mp3 --stage 1

Expected output line:
  [max-000027] ✗ no match  (1/1) English | noheader.mp3

Expected: run completes, no crash, status=no_match in DB.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER IMPLEMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Print the git commit message to use.
```

---

## Filled-in example — new feature

**The GitHub issue:**
> **#12 — Support .flac files in addition to .mp3**
> Label: enhancement
> Acceptance criteria:
> - Running python3 main.py Input/ processes .flac files alongside .mp3
> - .flac files are tagged using mutagen's FLAC/VorbisComment tags
> - .flac files are organised into the same Music/ structure as .mp3
> - SUPPORTED_EXTENSIONS in config.py is the single place to add .flac
> - DB schema unchanged

**The filled-in prompt:**

```
You are implementing a GitHub issue for the Sruthi project.

Before writing any code, read these files in this order:
  1. CONTRIBUTING.md
  2. ARCHITECTURE.md
  3. DATABASE.md
  4. pipeline/config.py
  5. pipeline/identify.py
  6. pipeline/tagger.py
  7. Run: python3 main.py --check

Do not modify music.db. Do not change the DB schema.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ISSUE #12 — Support .flac files
Label: enhancement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add .flac support. Acceptance criteria:
- python3 main.py Input/ processes .flac files alongside .mp3
- .flac files tagged using mutagen FLAC/VorbisComment (not ID3)
- .flac files organised into same Music/ structure
- SUPPORTED_EXTENSIONS in config.py is the single place to add .flac
- DB schema unchanged
- requirements.txt unchanged (mutagen already handles FLAC)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCOPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files allowed:
  pipeline/config.py, pipeline/identify.py, pipeline/tagger.py,
  pipeline/organizer.py, README.md, ../guide/USER_GUIDE.md

Files not allowed: music.db, Music/, Input/, runs/, db.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before writing code:
  1. Describe how tagger.py will branch on file extension to use FLAC vs ID3
  2. Confirm mutagen.flac.FLAC and mutagen.flac.FLACNoHeaderError equivalents
  3. Describe how the short-file guard in identify.py handles .flac duration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create a test .flac file:
  ffmpeg -f lavfi -i "sine=frequency=440:duration=10" /tmp/test.flac
  cp /tmp/test.flac Input/English/

Run full pipeline:
  python3 main.py Input/English/test.flac

Then inspect tags:
  python3 -c "
  from mutagen.flac import FLAC
  f = FLAC('Music/English/Unknown Year/Unknown Album/test.flac')
  print(f.tags.as_dict())
  "

Confirm: title, artist fields present (even if no_match → from override or empty).
Confirm: file moved to Music/ structure.
Confirm: status=done in DB.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AFTER IMPLEMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Update README.md: add .flac to SUPPORTED_EXTENSIONS row in config section.
Update ../guide/USER_GUIDE.md: add .flac to Requirements and What this does sections.
Print the git commit message to use.
```

---

## What good issues look like — quick reference

| Type | Good | Bad |
|---|---|---|
| Bug title | "Stage 3 silently skips files with status=identified when album contains /" | "it doesn't work" |
| Feature title | "Add --output-dir flag to set Music/ destination at runtime" | "make it better" |
| Acceptance criteria | Specific, runnable, pasteable output | "should work correctly" |
| Scope | Lists exact files to touch | "whatever needs changing" |
| Verification | One command, one expected output | "test it manually" |

---

## Things that are NOT issues

- ShazamIO breaking because Shazam changed their API — this is an upstream
  dependency. See README.md "Fallback plan" section. Not a bug in this project.
- A song not being identified — this is expected behaviour for ~10–25% of files.
  Use `python3 main.py --review` to handle them manually.
- Wanting to discuss an idea before writing it up — open a GitHub Discussion,
  not an issue. Issues are for things with clear acceptance criteria.
- Questions about how to use the tool — read ../guide/USER_GUIDE.md first.

---

## Session hygiene rules for Claude CLI

These apply to every session, regardless of issue type:

1. **Read before writing.** Always read CONTRIBUTING.md, README.md, and the
   relevant module(s) before touching any code. No exceptions.

2. **One issue per session.** Never implement two issues in one Claude CLI session.
   If the work reveals a second problem, note it and open a new issue for it.

3. **Smallest possible change.** Fix the exact problem described. Do not refactor
   adjacent code, rename things, or "improve" code that is not part of the issue.

4. **Verification must be runnable.** The verification command must produce
   output that can be pasted as evidence. "It looks correct" is not verification.

5. **Update docs when behaviour changes.** If a CLI flag changes, README.md
   CLI reference table is updated in the same commit. If a user-facing behaviour
   changes, ../guide/USER_GUIDE.md is updated in the same commit.

6. **Never touch music.db directly.** All DB changes go through db.py functions.
   Never run raw SQL UPDATE or DELETE against music.db from Claude CLI.

7. **Commit message closes the issue.** Always include `(closes #N)` so GitHub
   auto-closes the issue when the PR merges.

8. **Branch, never main.** All work happens on a feature branch. Claude CLI
   should remind you to create the branch before it writes any code.
