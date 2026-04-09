"""
Sruthi — CLI entry point
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Parses command-line arguments and dispatches to the appropriate pipeline pass
or standalone command. All user-facing flags are defined here; the actual work
lives in the pipeline/ package.

Docs:
  Full CLI reference      — DOCS/USER_GUIDE.md  (Quick command reference, Full CLI reference)
  Pipeline stage overview — DOCS/ARCHITECTURE.md
Issues:
  #13 — --metadata-search, --all, --folder flags
  #26 — --transliterate flag
"""

import argparse
import sqlite3

from pipeline.db import get_connection


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def cmd_check():
    """Verify DB tables exist and print row counts. Safe to run at any time."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables = [r[0] for r in rows]
        print("Tables:", tables)
        if "songs" in tables and "runs" in tables:
            print("DB OK")
        else:
            print("DB ERROR: missing tables")
            return
        total = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        print(f"Total songs: {total}")
        for row in conn.execute(
            "SELECT status, COUNT(*) n FROM songs GROUP BY status ORDER BY status"
        ):
            print(f"  {row[0]:<14} {row[1]}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# --zeroise
# ---------------------------------------------------------------------------

def cmd_zeroise():
    """Wipe all songs and runs from music.db after interactive confirmation."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        runs  = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        print(f"This will delete {total} song(s) and {runs} run(s) from the database.")
        answer = input("Type YES to confirm: ").strip()
        if answer != "YES":
            print("Aborted.")
            return
        conn.execute("DELETE FROM songs")
        conn.execute("DELETE FROM runs")
        conn.commit()
        print("Database cleared.")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# --stats
# ---------------------------------------------------------------------------

def cmd_stats():
    """Print a summary of music.db — status breakdown, language breakdown, top albums."""
    conn = get_connection()
    try:
        print("Status breakdown:")
        for row in conn.execute(
            "SELECT status, COUNT(*) n FROM songs GROUP BY status ORDER BY n DESC"
        ):
            print(f"  {row[0]:<14} {row[1]}")

        print()
        print("Language breakdown:")
        for row in conn.execute(
            "SELECT language, COUNT(*) n FROM songs GROUP BY language ORDER BY n DESC"
        ):
            print(f"  {row[0]:<14} {row[1]}")

        print()
        print("Top albums (by song count):")
        for row in conn.execute(
            """SELECT COALESCE(NULLIF(final_album,''), NULLIF(shazam_album,''), 'Unknown Album') AS album,
                      COUNT(*) AS n
               FROM songs GROUP BY album ORDER BY n DESC LIMIT 5"""
        ):
            print(f"  {row[0][:45]:<47} {row[1]}")

        no_match_count = conn.execute(
            "SELECT COUNT(*) FROM songs WHERE status='no_match'"
        ).fetchone()[0]
        if no_match_count:
            print()
            print(f"  {no_match_count} file(s) still need review — run: python3 main.py --review")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """
    Parse CLI arguments and dispatch to the appropriate command or pipeline pass.
    See DOCS/USER_GUIDE.md — Full CLI reference for the complete flag list.
    """
    parser = argparse.ArgumentParser(
        description="Music Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("source", nargs="?", help="File or folder to process")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4],
                        help="Run only a single stage (1–4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview actions without writing or moving files")
    parser.add_argument("--review-after", action="store_true",
                        help="Run interactive Stage 2 review after Stage 1")
    parser.add_argument("--review", action="store_true",
                        help="Interactive review of unmatched files (standalone)")
    parser.add_argument("--all", dest="review_all", action="store_true",
                        help="Review all identified + no_match songs")
    parser.add_argument("--flagged", action="store_true",
                        help="Review only songs with suspicious year (⚠)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max songs to review")
    parser.add_argument("--check", action="store_true",
                        help="Verify DB tables and print row counts")
    parser.add_argument("--stats", action="store_true",
                        help="Print DB summary by status and language")
    parser.add_argument("--zeroise", action="store_true",
                        help="Clear all songs and runs from the database (asks for confirmation)")
    parser.add_argument("--move", action="store_true",
                        help="Tag and move all identified songs to Music/ (stages 3+4, no source needed)")
    parser.add_argument("--metadata-search", action="store_true", dest="metadata_search",
                        help="Metadata search pass: query iTunes using ID3 tags and cleaned filename, review interactively")
    parser.add_argument("--folder", type=str, default=None,
                        help="Limit --metadata-search or --review to songs whose path contains this string")
    parser.add_argument("--acoustid", action="store_true",
                        help="AcoustID fallback pass: fingerprint no_match songs and review interactively")
    parser.add_argument("--transliterate", action="store_true",
                        help="Transliterate Artist ID3 tags to native script for Tamil/Hindi songs (requires SARVAM_API_KEY)")
    parser.add_argument("--retry-no-match", action="store_true", dest="retry_no_match",
                        help="Re-run Shazam on all no_match songs (resets them to pending, then runs Stage 1)")
    parser.add_argument("--multiprobe", action="store_true",
                        help="Multi-probe pass: re-attempt Shazam on no_match songs at 4 time positions (issue #32)")

    args = parser.parse_args()

    # ── Standalone commands ──────────────────────────────────────────────
    if args.check:
        cmd_check()
        return

    if args.zeroise:
        cmd_zeroise()
        return

    if args.move:
        from pipeline.runner import run_pipeline
        run_pipeline(source_path="(db-only)", stages=[3, 4], dry_run=args.dry_run)
        return

    if args.metadata_search:
        from pipeline.filename_pass import run_filename_pass
        run_filename_pass(folder=args.folder, all_songs=args.review_all)
        return
    if args.acoustid:
        from pipeline.acoustid_pass import run_acoustid_pass
        run_acoustid_pass()
        return

    if args.transliterate:
        from pipeline.transliterate import run_transliterate_pass
        run_transliterate_pass(dry_run=args.dry_run)
        return

    if args.multiprobe:
        from pipeline.multiprobe_pass import run_multiprobe_pass
        run_multiprobe_pass()
        return

    if args.retry_no_match:
        if not args.source:
            print("--retry-no-match requires a source path, e.g.: python3 main.py --retry-no-match Input/")
            return
        conn = get_connection()
        try:
            result = conn.execute(
                "UPDATE songs SET status='pending', error_msg=NULL WHERE status='no_match'"
            )
            conn.commit()
            count = result.rowcount
        finally:
            conn.close()
        print(f"Reset {count} no_match songs to pending — running Stage 1...")
        from pipeline.runner import run_pipeline
        run_pipeline(source_path=args.source, stages=[1], dry_run=args.dry_run)
        return

    if args.stats:
        cmd_stats()
        return

    if args.review:
        from pipeline.review import run_review
        if args.flagged:
            mode = "flagged"
        elif args.review_all:
            mode = "all"
        else:
            mode = "no_match"
        run_review(mode=mode, limit=args.limit)
        return

    # ── Pipeline commands (need source or stage-only) ────────────────────
    if args.stage in (3, 4) and not args.source:
        # Stage 3 and 4 read from DB — source not required
        from pipeline.runner import run_pipeline
        run_pipeline(
            source_path="(db-only)",
            stages=[args.stage],
            dry_run=args.dry_run,
        )
        return

    if not args.source:
        parser.print_help()
        return

    from pipeline.runner import run_pipeline

    stages = [args.stage] if args.stage else [1, 2, 3, 4]

    run_pipeline(
        source_path=args.source,
        stages=stages,
        dry_run=args.dry_run,
        review_after=args.review_after,
    )


if __name__ == "__main__":
    main()
