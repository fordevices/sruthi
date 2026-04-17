"""
Sruthi — multi-model documentation and architecture review tool
Copyright (c) 2026 Sruthi Contributors (https://github.com/fordevices/sruthi)

Sends key project files to multiple AI providers (Anthropic Claude, OpenAI GPT-4o,
Google Gemini) and collects structured feedback on UX/documentation quality and
architecture/code design. All enabled providers run concurrently.

Usage:
  python3 review_docs.py               # both UX and architecture reviews
  python3 review_docs.py --ux          # documentation review only
  python3 review_docs.py --arch        # architecture review only
  python3 review_docs.py --save        # also write results to DOCS/ai/

API keys (set as env vars or in .env — same file the pipeline uses):
  ANTHROPIC_API_KEY  — Claude (claude-sonnet-4-6)
  OPENAI_API_KEY     — GPT-4o
  GEMINI_API_KEY     — Gemini 1.5 Pro

Packages for OpenAI and Gemini are optional — install only what you need:
  pip install openai
  pip install google-generativeai
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# Load .env — search from the script's directory upward, then from cwd upward.
# This finds a shared .env in a parent project folder (e.g. kirahi/aidev/.env)
# without requiring a copy in every sub-project.
def _load_env_file() -> None:
    """Walk upward from the script directory and load every .env found.
    setdefault means the innermost (closest) file wins for duplicate keys."""
    seen: set[Path] = set()
    p = Path(__file__).parent.resolve()
    while True:
        ep = p / ".env"
        if ep not in seen and ep.exists():
            seen.add(ep)
            for line in ep.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
        parent = p.parent
        if parent == p:
            break
        p = parent

_load_env_file()


# ---------------------------------------------------------------------------
# Files reviewed per mode
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent

UX_FILES = [
    ROOT / "README.md",
    ROOT / "DOCS/guide/USER_GUIDE.md",
]

ARCH_FILES = [
    ROOT / "DOCS/engineering/ARCHITECTURE.md",
    ROOT / "DOCS/guide/USER_GUIDE.md",
    ROOT / "main.py",
    ROOT / "pipeline/config.py",
    ROOT / "pipeline/db.py",
    ROOT / "pipeline/runner.py",
]


# ---------------------------------------------------------------------------
# Review prompts
# ---------------------------------------------------------------------------

_PROJECT_CONTEXT = """
Sruthi is a local Python CLI tool that identifies MP3 files using audio
fingerprinting (Shazam, ACRCloud), writes correct ID3 tags, and organises a
music library into Music/<Language>/<Year>/<Album>/. The target user is a
non-developer, computer-savvy music lover with a large Tamil/Hindi collection
from the pre-streaming era. It has no web server — entirely local.
"""

UX_PROMPT = f"""\
{_PROJECT_CONTEXT}

You are reviewing the UX and documentation of this tool. Read the files provided
and give honest, specific feedback.

Review questions:
1. Is README.md immediately clear to someone who has never heard of this tool?
   Does it answer "what does this do, why would I want it, how do I start"?
2. Is USER_GUIDE.md usable by the target audience (non-developer, computer-savvy)?
   Where might they get confused or lost?
3. Are there gaps — things a first-time user would need to know that are not covered?
4. Is the command reference easy to scan? Are commands explained in plain language?
5. Any jargon, developer-speak, or unstated assumptions the target audience would
   stumble on?

Be direct and specific. Point to exact sections or headings where issues exist.
Rate each document out of 10. Under 600 words total.
"""

ARCH_PROMPT = f"""\
{_PROJECT_CONTEXT}

You are doing an independent architecture review. Read the files provided and give
honest, specific technical feedback.

Review questions:
1. Does ARCHITECTURE.md accurately reflect what the code actually does?
   Call out any discrepancies.
2. Are there structural weaknesses in the pipeline design that would cause problems
   at scale or during error recovery?
3. Is the DB layer (db.py) well-designed? Any concerns about schema, migration
   approach, or concurrency?
4. Does main.py handle the CLI surface cleanly, or is it growing unwieldy?
5. What is the single biggest technical debt risk as the project grows?

Be direct and specific. Reference file names and line numbers where relevant.
Rate the overall architecture out of 10. Under 600 words total.
"""


# ---------------------------------------------------------------------------
# File loader
# ---------------------------------------------------------------------------

def _load_files(paths: list[Path]) -> str:
    parts = []
    for p in paths:
        rel = p.relative_to(ROOT)
        if p.exists():
            parts.append(f"=== {rel} ===\n{p.read_text()}")
        else:
            parts.append(f"=== {rel} === [FILE NOT FOUND]")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Provider callables
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, content: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "[SKIP] ANTHROPIC_API_KEY not set"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"{prompt}\n\n{content}"}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        return f"[ERROR] {e}"


def _call_openai(prompt: str, content: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return "[SKIP] OPENAI_API_KEY not set"
    try:
        import openai
    except ImportError:
        return "[SKIP] openai package not installed — run: pip install openai"
    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1500,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": content},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR] {e}"


def _call_gemini(prompt: str, content: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "[SKIP] GEMINI_API_KEY not set"
    try:
        import google.generativeai as genai
    except ImportError:
        return "[SKIP] google-generativeai package not installed — run: pip install google-generativeai"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        resp = model.generate_content(f"{prompt}\n\n{content}")
        return resp.text.strip()
    except Exception as e:
        return f"[ERROR] {e}"


PROVIDERS = [
    ("Claude (claude-sonnet-4-6)", _call_claude),
    ("GPT-4o",                     _call_openai),
    ("Gemini 1.5 Pro",             _call_gemini),
]


# ---------------------------------------------------------------------------
# Review runner
# ---------------------------------------------------------------------------

_DIVIDER = "═" * 70
_SUB     = "─" * 70


def _run_providers(prompt: str, content: str) -> list[tuple[str, str]]:
    """Call all providers concurrently. Returns [(name, response), ...] in order."""
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as ex:
        futures = {ex.submit(fn, prompt, content): name for name, fn in PROVIDERS}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = f"[ERROR] {e}"
    return [(name, results[name]) for name, _ in PROVIDERS]


def _format_section(title: str, results: list[tuple[str, str]]) -> str:
    lines = [f"\n{_DIVIDER}", f"  {title}", _DIVIDER]
    for model_name, response in results:
        pad = _SUB[len(model_name) + 4:]
        lines.append(f"\n── {model_name} {pad}\n")
        lines.append(response)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-model AI review of Sruthi docs and architecture.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--ux",   action="store_true",
                        help="Review README.md and USER_GUIDE.md")
    parser.add_argument("--arch", action="store_true",
                        help="Review ARCHITECTURE.md and key pipeline code")
    parser.add_argument("--save", action="store_true",
                        help="Save results to DOCS/ai/review_<timestamp>.md")
    args = parser.parse_args()

    # Default: both if neither flag given
    run_ux   = args.ux   or not (args.ux or args.arch)
    run_arch = args.arch or not (args.ux or args.arch)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    save_parts = [f"# Sruthi Review — {timestamp} UTC\n"]

    if run_ux:
        print("\nLoading UX files...")
        content = _load_files(UX_FILES)
        print(f"Sending to {len(PROVIDERS)} providers (concurrent)...")
        results = _run_providers(UX_PROMPT, content)
        section = _format_section("UX & DOCUMENTATION REVIEW", results)
        print(section)
        save_parts.append(f"\n## UX & Documentation\n{section}")

    if run_arch:
        print("\nLoading architecture files...")
        content = _load_files(ARCH_FILES)
        print(f"Sending to {len(PROVIDERS)} providers (concurrent)...")
        results = _run_providers(ARCH_PROMPT, content)
        section = _format_section("ARCHITECTURE & CODE REVIEW", results)
        print(section)
        save_parts.append(f"\n## Architecture & Code\n{section}")

    if args.save:
        out_dir = ROOT / "DOCS" / "ai"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"review_{timestamp}.md"
        out_path.write_text("\n".join(save_parts))
        print(f"\n✓ Saved → {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
