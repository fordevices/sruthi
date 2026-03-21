import argparse
from datetime import datetime

from pipeline.db import get_connection


def cmd_check():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        tables = [r[0] for r in rows]
        print("Tables in music.db:", tables)
        if "songs" in tables and "runs" in tables:
            print("DB OK")
        else:
            print("DB ERROR: missing tables")
    finally:
        conn.close()


def cmd_stage1(source: str):
    from pipeline.identify import run_identification
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"Run ID: {run_id}")
    summary = run_identification(source, run_id)
    print()
    print("Summary:", summary)


def cmd_review(mode: str, limit: int):
    from pipeline.review import run_review
    run_review(mode=mode, limit=limit)


def main():
    parser = argparse.ArgumentParser(description="Music Pipeline")
    parser.add_argument("source", nargs="?", help="File or folder to process")
    parser.add_argument("--check", action="store_true", help="Verify DB and exit")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4], help="Run a single stage")
    parser.add_argument("--review", action="store_true", help="Interactive review of unmatched files")
    parser.add_argument("--all", dest="review_all", action="store_true",
                        help="Review all identified + no_match songs")
    parser.add_argument("--flagged", action="store_true",
                        help="Review only songs with suspicious year (⚠)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max number of songs to review")
    args = parser.parse_args()

    if args.check:
        cmd_check()
        return

    if args.review:
        if args.flagged:
            mode = "flagged"
        elif args.review_all:
            mode = "all"
        else:
            mode = "no_match"
        cmd_review(mode=mode, limit=args.limit)
        return

    if not args.source:
        parser.print_help()
        return

    if args.stage == 1:
        cmd_stage1(args.source)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
