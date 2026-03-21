"""
Orchestrator — ties all pipeline stages together and writes run logs + summary.json.
"""

import json
import logging
import os
import sys
from datetime import datetime

# ANSI colour constants — disabled automatically when stdout is not a TTY
# (piped output, log files, CI). Import from here in other modules.
_C     = sys.stdout.isatty()
GREEN  = "\033[32m" if _C else ""
YELLOW = "\033[33m" if _C else ""
RED    = "\033[31m" if _C else ""
BOLD   = "\033[1m"  if _C else ""
RESET  = "\033[0m"  if _C else ""

from pipeline import config
from pipeline.db import create_run, finish_run
from pipeline.identify import run_identification
from pipeline.organizer import run_organization
from pipeline.review import run_review
from pipeline.tagger import run_tagging


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_run_logging(run_id: str) -> logging.Logger:
    """
    Create runs/{run_id}/ and configure the 'pipeline' logger with:
      - StreamHandler (stdout, INFO, clean format)
      - FileHandler (run.log, DEBUG, timestamped format)
    Guards against duplicate handlers if called more than once.
    """
    run_dir = os.path.join(config.RUNS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console)

        log_path = os.path.join(run_dir, "run.log")
        fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# Summary writer
# ---------------------------------------------------------------------------

def write_summary(run_id: str, summary: dict) -> None:
    """Write summary dict as pretty JSON to runs/{run_id}/summary.json."""
    path = os.path.join(config.RUNS_DIR, run_id, "summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(
    source_path: str,
    stages: list[int] = None,
    dry_run: bool = False,
    review_after: bool = False,
) -> None:
    if stages is None:
        stages = [1, 2, 3, 4]

    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    start_time = datetime.now()
    started_at = start_time.isoformat()

    logger = setup_run_logging(run_id)
    create_run(run_id, mode="folder", source_path=source_path)

    logger.info(f"{BOLD}=== Run {run_id} | source: {source_path} | stages: {stages} ==={RESET}")
    if dry_run:
        logger.info(f"{BOLD}[DRY RUN — no files will be written or moved]{RESET}")

    # Accumulated counters
    files_total = 0
    files_identified = 0
    files_no_match = 0
    files_already_done = 0
    files_tagged = 0
    files_moved = 0
    files_error = 0
    shazam_calls_made = 0

    # ── Stage 1 — Identification ──────────────────────────────────────────
    if 1 in stages:
        logger.info("── Stage 1: identification ──")
        result = run_identification(source_path, run_id)
        files_total        = result.get("total", 0)
        files_identified   = result.get("identified", 0)
        files_no_match     = result.get("no_match", 0)
        files_already_done = result.get("skipped", 0)
        files_error        += result.get("errors", 0)
        shazam_calls_made  = files_identified + files_no_match
        logger.info(
            f"Stage 1 done: {files_identified} identified, "
            f"{files_no_match} no_match, {files_already_done} skipped, "
            f"{result.get('errors', 0)} errors"
        )

    # ── Stage 2 — Review ─────────────────────────────────────────────────
    if 2 in stages:
        if review_after:
            logger.info("── Stage 2: manual review ──")
            run_review(mode="no_match")
        else:
            logger.info("Stage 2 — review skipped (use --review-after to enable)")

    # ── Stage 3 — Tagging ────────────────────────────────────────────────
    if 3 in stages:
        logger.info("── Stage 3: tagging ──")
        result = run_tagging(dry_run=dry_run)
        files_tagged  = result.get("tagged", 0)
        files_error  += result.get("errors", 0)
        logger.info(
            f"Stage 3 done: {files_tagged} tagged, {result.get('errors', 0)} errors"
        )

    # ── Stage 4 — Organization ───────────────────────────────────────────
    if 4 in stages:
        logger.info("── Stage 4: organization ──")
        result = run_organization(dry_run=dry_run)
        files_moved  = result.get("moved", 0)
        files_error += result.get("errors", 0)
        logger.info(
            f"Stage 4 done: {files_moved} moved, {result.get('errors', 0)} errors"
        )

    # ── Wrap up ──────────────────────────────────────────────────────────
    finish_time = datetime.now()
    finished_at = finish_time.isoformat()
    duration_sec = round((finish_time - start_time).total_seconds(), 1)

    summary = {
        "run_id":            run_id,
        "source_path":       source_path,
        "started_at":        started_at,
        "finished_at":       finished_at,
        "duration_sec":      duration_sec,
        "files_total":       files_total,
        "files_identified":  files_identified,
        "files_no_match":    files_no_match,
        "files_already_done": files_already_done,
        "files_tagged":      files_tagged,
        "files_moved":       files_moved,
        "files_error":       files_error,
        "shazam_calls_made": shazam_calls_made,
    }

    finish_run(
        run_id,
        files_total=files_total,
        files_done=files_moved,
        files_error=files_error,
        files_no_match=files_no_match,
    )
    write_summary(run_id, summary)

    one_liner = (
        f"{files_identified} identified, {files_tagged} tagged, "
        f"{files_moved} moved, {files_error} errors — {duration_sec}s"
    )
    logger.info(f"{BOLD}=== Run complete: {one_liner} ==={RESET}")
    logger.info(f"Log:     runs/{run_id}/run.log")
    logger.info(f"Summary: runs/{run_id}/summary.json")
