# Sruthi Review — 2026-04-17_22-57-02 UTC


## UX & Documentation

══════════════════════════════════════════════════════════════════════
  UX & DOCUMENTATION REVIEW
══════════════════════════════════════════════════════════════════════

── Claude (claude-sonnet-4-6) ────────────────────────────────────────

## Review: Sruthi README.md and USER_GUIDE.md

---

### README.md — 8/10

**What works well:** The opening paragraph is excellent — concrete, specific, and speaks directly to the target user's pain. The folder-tree example immediately answers "what does this do." The "For music lovers / For developers" split is smart information architecture.

**Specific problems:**

**Documentation table is broken.** The table at the bottom links to `DOCS/guide/USER_GUIDE.md` but the body links to `DOCS/USER_GUIDE.md`. One of these is wrong. A first-time user clicking "Read the User Guide" from two different places may hit a 404.

**"What other AI agents think of this" section** has no business being in a README aimed at a non-developer user. It reads as self-congratulatory and adds noise before the user has even installed anything. Move it to a separate file or the developer section.

**"How AI is used"** is three paragraphs long and interrupts the flow between setup and docs. The target user does not need this to get started. It belongs in an FAQ or footer.

**ACRCloud is undersold.** README says it's for "older Indian film music" but the User Guide's match-rate table shows it dramatically improves even 1990s Tamil music. The README should say "free account required" upfront — users will discover this mid-run otherwise.

---

### USER_GUIDE.md — 8/10

**What works well:** The step-by-step first-run flow is genuinely good. The decision tree for unmatched songs is the best section in the document — scannable, logical, and written for humans. Troubleshooting answers real questions. Match-rate table is useful and honest.

**Specific problems:**

**`git clone` in the install instructions.** The target user — a "computer-savvy non-developer" — likely does not have Git installed and may not know what cloning means. This is the single biggest drop-off risk. Add a fallback: "No Git? Download the ZIP from GitHub (Code → Download ZIP), unzip it, and open that folder in your terminal."

**`venv` is unexplained.** `python3 -m venv venv` and `source venv/bin/activate` appear with no explanation. The user will ask: "what is this, do I need to do it every time?" Add a one-sentence explanation and note that they must re-run `source venv/bin/activate` each new terminal session. This catches people repeatedly.

**`--stage 1` in the command reference has no explanation.** What are stages 2 and 3? What would I use this for? This is the only command in the table that a non-developer cannot infer.

**`--zeroise` is alarming with no context.** A destructive command appears in the reference table with a one-liner description and no warning callout. It should have a ⚠️ and a note about when you would ever want to use it.

**"Songs moved to Music/Unknown Year/" troubleshooting entry** references `--folder "Unknown Year"` — a flag that appears nowhere else in the guide. Is that a real flag? If so, document it. If not, fix the troubleshooting entry.

**Windows audio gap.** The guide mentions `--review` audio doesn't work on Windows and says "open in VLC." But the `--review` workflow requires listening to identify the song. This is a significant UX hole for Windows users — not just a footnote.

---

### Cross-cutting gaps

**No screenshot or gif.** The target user has never seen this tool run. One 30-second terminal recording would eliminate a lot of anxiety about whether the install worked.

**`export` syntax is shown but never explained.** The user needs to set environment variables for ACRCloud, Sarvam, and Anthropic. There is no explanation that these disappear when the terminal closes, nor any guidance for making them permanent on Windows (where `export` does not work at all — it's `set` in CMD or `$env:` in PowerShell).

**What does `--check` printing "DB OK" actually mean?** The guide says "you are ready to go" but doesn't say what a failed check looks like or what to do if it fails.

── GPT-4o ────────────────────────────────────────────────────────────

### README.md Review

1. **Clarity and Introduction**: The README is clear, detailing what the tool does, why it is useful, and how it can be started, fulfilling its role effectively for both music lovers and developers. Rating: 9/10

2. **User Guide Usability**: It is quite detailed and mostly understandable for a computer-savvy non-developer. However, the detailed setup instructions and environment variables might overwhelm users without some explanation or a step-by-step walkthrough, especially in the **Installation** section. Rating: 8/10

3. **Gaps**: The README does not mention prerequisites like checking `git` installation, which might confuse users if cloning the repository fails. Similarly, a brief on Python environments could be useful for users unfamiliar with `venv`. Another gap is in clarifying `Music/Other/`. It should explicitly mention for languages the tool might not recognize. Incorporating a troubleshooting link in the document could pre-emptively guide users. Rating: 7/10

4. **Command Reference**: The command reference is exhaustive and easy to scan, with plain language explanations, making it approachable for the target audience. Rating: 9/10

5. **Jargon and Assumptions**: Some assumptions are unstated, like prior knowledge of how to set environment variables, what '`export`' means, or how a CLI works. The term "resume-safety" may be unclear without explicit context. Overall, the tool assumes some familiarity with development setups which might not be accurate for all users in the target demographic. Rating: 7/10

**Overall Ratings**:
- **README.md**: 8/10
- **USER_GUIDE.md**: 8/10

Additional suggestion: Incorporate a "Getting Started" section in the README to guide complete novices step-by-step from downloading to running their first sort. This might ease any early confusion for first-time users.

── Gemini 2.5 Pro ────────────────────────────────────────────────────

Excellent work on the documentation. It's clear, comprehensive, and well-structured. Here is my specific feedback.

### README.md Review

**Rating: 9/10**

This is a strong README. It’s concise, well-targeted, and immediately communicates the tool's value.

**1. Is it immediately clear? (what, why, how)**
Yes.
*   **What:** "Sruthi takes a folder of MP3 files... and turns them into a clean, properly labelled music library". This is perfect. The file structure diagram is extremely effective.
*   **Why:** "Built for large Tamil and Hindi collections where standard tools fall short" speaks directly to the target user and their pain point.
*   **How:** The big link "→ [Read the User Guide]" is a clear and effective call to action.

The separation between "For music lovers" and "For developers" is outstanding. It allows each audience to get what they need without being distracted by irrelevant details.

**5. Jargon, developer-speak, or unstated assumptions?**
The "For music lovers" section is almost perfect. The sections on AI usage are clear, but "What other AI agents think of this" feels a bit like inside baseball; a non-developer may not care and might find it slightly confusing. This is a very minor point in an otherwise excellent document.

### USER_GUIDE.md Review

**Rating: 7/10**

The guide is comprehensive and logically structured, but the installation section makes assumptions that will be a significant hurdle for the target audience.

**2. Is it usable by the target audience? Where might they get confused?**
The workflow sections ("Your first run", "What to do with unmatched songs") are excellent. They are step-by-step, use clear examples, and anticipate user questions.

The main point of failure will be the **Installation** section.
*   **macOS:** It assumes the user has [Homebrew](https://brew.sh/) installed (`brew install python`). This is a third-party package manager most non-developers have never heard of.
*   **All OSes:** It assumes `git` is installed and the user is comfortable with `git clone`. For a non-developer, downloading a ZIP file from the GitHub repository is a much more familiar and less intimidating workflow.
*   **Setting API Keys:** The instruction "add to `~/.bashrc` to make permanent" is developer-speak. A non-developer won't know what `~/.bashrc` is, where to find it, or how to edit it. This needs a simpler explanation or a link to a beginner-friendly tutorial.

**3. Are there gaps — things a first-time user would need to know?**
*   **Installation Prerequisites:** As noted above, the guide needs to explicitly state that Homebrew (for macOS) and Git are required, with links on how to install them. A "Download ZIP" alternative would be better.
*   **Updating the Tool:** How does a user get new features or bug fixes? There are no instructions on how to update Sruthi to a newer version.

**4. Is the command reference easy to scan?**
Yes, the **Full command reference** table is excellent. It is easy to scan, and the "What it does" column uses clear, non-technical language.

**5. Jargon, developer-speak, or unstated assumptions?**
*   **`python3 -m venv venv` / `source venv/bin/activate`:** While the commands are provided, the user has no idea what a "virtual environment" is. A single sentence explaining it helps build confidence (e.g., "This creates a clean, private workspace for Sruthi so its dependencies don’t interfere with other apps on your computer.").
*   **`pip install -r requirements.txt`:** The term "dependencies" is not explained. Again, a simple clarification would help.
*   **Troubleshooting > "database is locked"**: This is great, but a user might not know *what* a database is in this context. Simply rephrasing to "You ran two Sruthi commands at once..." is slightly clearer.

## Architecture & Code

══════════════════════════════════════════════════════════════════════
  ARCHITECTURE & CODE REVIEW
══════════════════════════════════════════════════════════════════════

── Claude (claude-sonnet-4-6) ────────────────────────────────────────

## Architecture Review: Sruthi

### 1. ARCHITECTURE.md vs. Actual Code

The doc is largely accurate but has meaningful gaps:

- **`--retry-no-match` is absent from the module map and status flow.** It resets `no_match → pending` and re-runs Stage 1, but the status diagram doesn't show this path.
- **ANSI constants claim.** ARCHITECTURE.md states "nothing else imports from `runner.py` except ANSI colour constants," but `runner.py` imports all four stage modules at the top level (`identify`, `organizer`, `review`, `tagger`). The claim about import directionality is fine, but it's oddly phrased — the *rule* is that stages don't import runner, not the reverse.
- **`--metadata-search --all` flag.** The `run_filename_pass` call in `main.py` passes `all_songs=args.review_all`, but `args.review_all` is bound to `--all` which is documented as a `--review` modifier. A user running `--metadata-search --all` is reusing a flag that's semantically tied to `--review`. This shared flag is a latent confusion not mentioned in the architecture docs.
- **`gui.py` mention.** Listed in the module map but gets zero architectural explanation — no data flow, no note about what DB queries it runs.

### 2. Structural Pipeline Weaknesses

**The open-connection-per-call pattern is the biggest operational risk.** Every function in `db.py` calls `get_connection()`, which calls `CREATE TABLE IF NOT EXISTS` and runs the migration check on *every single invocation*. For a 5,000-song collection, `generate_song_id()` alone triggers schema setup on every insert. At scale this is measurably slow and means the migration code runs thousands of times per run.

**`generate_song_id()` is a race condition.** It opens a connection, reads `MAX(song_id)`, closes it, then a second call to `insert_song()` opens another connection and inserts. Two concurrent calls (e.g., future async Shazam) would generate the same ID. The UNIQUE constraint would catch it, but silently crash the insert rather than handling it gracefully.

**`--retry-no-match` runs raw SQL in `main.py`** (line ~190: `conn.execute("UPDATE songs SET status='pending'...")`). This violates the documented rule that `db.py` is the only file that runs SQL. Same issue with `cmd_check()` and `cmd_zeroise()` in `main.py` — multiple raw SQL queries scattered through the CLI entry point.

**Stage 1 dry-run is a no-op.** The comment says "identification writes to DB and is not preview-safe" — this is a design cop-out. Users running `--dry-run` on a fresh collection get no preview of Stage 1 whatsoever.

### 3. DB Layer Assessment

**Schema concerns:**
- `shazam_*` column naming is leaky abstraction. When ACRCloud or metadata-search identifies a song, the result still lands in `shazam_title`, `shazam_artist` etc. The column names are wrong for ~30% of use cases.
- `final_year` stored as `TEXT` makes range queries and sorting unreliable. The `--review --flagged` feature does year sanity checks — this would be cleaner as `INTEGER`.
- No index on `status` or `file_hash`. For 10,000+ songs, `get_songs_by_status('identified')` does a full table scan on every stage transition.

**Migration approach:** `PRAGMA table_info` + `ALTER TABLE` in `get_connection()` works for additive changes but gives no version tracking. There's no way to know which migrations have run without re-checking every column name. A `schema_version` table with monotonic integers is the standard fix.

**Concurrency:** WAL mode is correctly enabled, but each function opens and closes its own connection. A pipeline run makes hundreds of short-lived connections rather than one long-lived transaction. Stages 3→4 could be wrapped in a single connection with a transaction for atomicity.

### 4. main.py CLI Surface

At ~220 lines, `main.py` is already overloaded. Three specific problems:

- `cmd_check()`, `cmd_zeroise()`, `cmd_stats()` contain direct SQL — they belong in `db.py` or a `commands.py` module.
- `cmd_stats()` is 100 lines of formatting logic including disk-walk calls, reconciliation arithmetic, and backlog analysis. This is business logic masquerading as CLI code.
- The `--mark-removed` handler (lines ~185-195) iterates rows and calls `update_song()` in a loop inside `main.py` — again, business logic that belongs in a pipeline module.

The `args.review_all` / `--all` flag serving double duty for both `--review` and `--metadata-search` will cause bugs if someone adds a third pass that needs similar semantics.

### 5. Biggest Technical Debt Risk

**The `shazam_*` column naming locked to one identification source.** As ACRCloud and metadata-search become primary paths for the target user's pre-2000 Indian music, storing all metadata in `shazam_title` / `shazam_artist` columns becomes increasingly wrong. Fixing this requires a schema migration touching every stage, every query in `db.py`, and every reference in `tagger.py` and `organizer.py`. The longer this ships, the more expensive the rename becomes. The correct design is a single `raw_title` / `raw_artist` / `raw_album` set of columns populated by whichever source matched, with `id_source` recording which one.

---

### Overall Rating: **6/10**

The architecture doc, status machine, and resume-safety model are genuinely well thought out for the target use case. The DB-as-sole-SQL-owner rule is the right instinct. But the implementation leaks SQL into `main.py`, has a per-call connection overhead that will hurt at scale, carries a column naming mistake that will compound, and lacks indexes that are already needed. Nothing here is unfixable, but several items need attention before this handles a 10,000-song collection reliably.

── GPT-4o ────────────────────────────────────────────────────────────

### Architecture Review for Sruthi

1. **Architecture Document Discrepancy**:
   The `ARCHITECTURE.md` mostly aligns with the implementation, but there are slight discrepancies. For example, the document states that `multi-probe` uses four positions (15/35/55/75%), which aligns with the purpose in `multiprobe_pass.py`. However, the mention of `--review manual entry` influencing status transition appears supported by `main.py`, which clearly handles interactive reviews. Thus, no major discrepancies are evident.

2. **Pipeline Structural Weaknesses**:
   The sequential processing stages are well-defined, but there could be an issue with error recovery. For instance, if an error occurs mid-stage, the entire operation halts unless re-run. Automatic retries for some errors (set in Stage 1) are good, but finer error granularity may be necessary for robust recovery mechanisms. Also, as the scale grows, SQLite's limitations might surface because it is not ideal for concurrent write-heavy operations.

3. **Database Layer Design Concerns**:
   - **Schema/Concurrent Access**: SQLite is adequate for lightweight applications but may struggle with concurrency as usage scales, especially in multi-write scenarios. The `WAL` mode improves concurrent reads but not writes.
   - **Automatic Schema Migration**: Using `PRAGMA` for migrations is simple but lacks formal migration tracking. Consider adopting a tool like Alembic for more controlled migrations.
   - **Scalability**: The schema is flat, with no optimization for read-heavy operations across a large dataset, like indices on frequently queried columns (e.g., `status`, `language`).

4. **CLI Surface Management**:
   - The `main.py` handles CLI arguments but grows complex with numerous flags, risking user overwhelm. Grouping related commands or documentation-enhanced options could improve usability. Despite having many flags, it avoids deep business logic, adhering to architectural guidelines.

5. **Biggest Technical Debt**:
   The largest risk is the reliance on SQLite for data persistence without addressing its scaling limitations for concurrent writes. Moving to a more robust RDBMS like PostgreSQL or embedding lightweight distributed storage (for larger volumes) would mitigate this.

Overall, the current architecture is well-organized for the targeted scope. Still, there are structural concerns as it scales, primarily around database management and the extensibility of the CLI surface. A rating of **7.5/10** acknowledges the solid groundwork while noting the need for enhancements to sustain future growth.

── Gemini 2.5 Pro ────────────────────────────────────────────────────

Here is an independent architecture review of Sruthi.

### 1. Does ARCHITECTURE.md accurately reflect the code?

Mostly, yes. The four-stage pipeline, status flow, and module map are well-documented and reflect the project's intent. However, there are two key discrepancies:

1.  **Business logic in `main.py`:** The doc claims `main.py` contains "no business logic," but it handles several non-trivial operations directly. The `cmd_stats` function (main.py:100-247) contains complex SQLite queries and display logic. The `--mark-removed` (main.py:408-419) and `--retry-no-match` (main.py:421-436) flags also implement business logic with direct database writes, rather than dispatching to a pipeline module.
2.  **Error state recovery:** The architecture diagram states that an `error` status is "auto-retried on next run." The code provided does not show this mechanism. `runner.py` does not appear to query for songs in `error` state to reset them to `pending` at the start of a run.

### 2. Are there structural weaknesses in the pipeline design?

The primary weakness is the user-facing workflow for optional passes. The user must run an identification pass (e.g., `--acrcloud`) and then a separate `--move` command. This two-step process is slightly clunky and error-prone; a user could easily forget the second step. A more integrated flow, such as an `--and-move` flag, would provide a better user experience.

The separation of the main pipeline (invoked with `Input/`) from the optional passes (`--acrcloud`, `--multiprobe`) is logical but creates this operational overhead. While safe, it’s not as seamless as it could be.

### 3. Is the DB layer (db.py) well-designed?

The DB layer has a solid foundation but significant concerns.

**Good:**
*   The schema is sensible, with a stable `song_id` and audit-friendly `meta_before`/`meta_after` columns.
*   Centralising all SQL in `db.py` is an excellent design choice.

**Concerns:**
1.  **Connection Management:** Every function (`update_song`, `insert_song`, etc.) opens and closes its own connection. This is inefficient and the direct cause of the `"database is locked"` errors mentioned in the user guide. A better pattern would be to use a context manager or pass a single connection object for the duration of a logical operation, allowing for proper transaction control.
2.  **Migration Strategy:** The automatic migration via `PRAGMA table_info` (db.py:107-117) is brittle. It only handles adding new columns. It will fail if a column needs to be renamed, altered, or dropped, requiring manual intervention. A simple version-based migration script would be more robust.

### 4. Does main.py handle the CLI surface cleanly?

No, it is growing unwieldy. The single, flat namespace of arguments (main.py:270-341) mixes core pipeline commands, optional passes, and utility functions. The large `if/elif` block for dispatching commands (main.py:346-463) is a sign of this strain.

As the tool grows, this will become harder to manage. Migrating to `argparse` sub-commands (e.g., `sruthi process Input/`, `sruthi identify --acrcloud`, `sruthi db stats`) would create a much cleaner, more scalable, and more discoverable CLI.

### 5. What is the single biggest technical debt risk as the project grows?

The single biggest risk is the **database connection management in `db.py`**. The practice of opening a new connection for every single query is not scalable. It directly causes the concurrency issues ("database is locked") that force the "one command at a time" user constraint. This limitation will become more painful as new features are added, and it prevents any future work on parallel processing or background tasks. Fixing this would require refactoring every function that touches the database to accept a connection or cursor object.

---
**Overall Architecture Rating: 7/10**

The project has excellent documentation, a clear purpose, and a sensible modular structure. The core design is sound, but it is undermined by specific, fixable implementation weaknesses in the database and CLI layers that will cause growing pains.