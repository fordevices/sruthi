"""
mp3-organizer-pipeline — Read-only query GUI
Natural language → SQL over music.db via Claude API.
Run with: streamlit run gui.py
"""

import os
import re
import sqlite3

import anthropic
import streamlit as st

from pipeline import config

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Sruthi",
    page_icon="🎵",
    layout="wide",
)

# ---------------------------------------------------------------------------
# DB connection (read-only)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_db():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_sql(sql: str) -> tuple[list[dict], str | None]:
    """Execute a SELECT query. Returns (rows, error_message)."""
    try:
        conn = get_db()
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
        return rows, None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------------------
# Claude NL → SQL
# ---------------------------------------------------------------------------

SCHEMA = """
Table: songs
Columns:
  song_id TEXT, file_path TEXT, language TEXT, status TEXT,
  shazam_title TEXT, shazam_artist TEXT, shazam_album TEXT, shazam_year TEXT,
  shazam_genre TEXT, shazam_cover_url TEXT,
  final_title TEXT, final_artist TEXT, final_album TEXT, final_year TEXT,
  final_genre TEXT, final_path TEXT,
  override_used INTEGER, error_msg TEXT,
  duplicate_count INTEGER, id_source TEXT,
  created_at TEXT, updated_at TEXT

Table: artist_transliterations
Columns: roman_name TEXT, language TEXT, native_name TEXT, created_at TEXT

Status values: 'done', 'no_match', 'error', 'pending', 'identified', 'tagged'
Language values: 'Tamil', 'Hindi', 'English', 'Other'

Notes:
- final_* columns hold user-overridden values; shazam_* hold Shazam's values
- Use COALESCE(NULLIF(final_title,''), shazam_title) to get the effective title
- error_msg LIKE 'REVIEW:%' means the song is flagged for manual review
- final_path is the current location of the file on disk
"""

EXAMPLES = """
Q: show me all Tamil songs from 1981
A: SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, COALESCE(NULLIF(final_artist,''),shazam_artist) AS artist, shazam_year AS year, final_path FROM songs WHERE language='Tamil' AND shazam_year='1981' AND status='done'

Q: how many Hindi songs do I have
A: SELECT COUNT(*) AS total FROM songs WHERE language='Hindi' AND status='done'

Q: show flagged songs
A: SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, language, error_msg, final_path FROM songs WHERE error_msg LIKE 'REVIEW:%'

Q: find all Ilaiyaraaja songs
A: SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, COALESCE(NULLIF(final_album,''),shazam_album) AS album, shazam_year AS year, final_path FROM songs WHERE (shazam_artist LIKE '%Ilaiyaraaja%' OR final_artist LIKE '%Ilaiyaraaja%') AND status='done'

Q: show songs with unknown album
A: SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, language, shazam_year AS year, final_path FROM songs WHERE status='done' AND (shazam_album='' OR shazam_album IS NULL) AND (final_album='' OR final_album IS NULL)

Q: language breakdown
A: SELECT language, COUNT(*) AS total FROM songs WHERE status='done' GROUP BY language ORDER BY total DESC
"""

SYSTEM_PROMPT = f"""You convert plain English questions about a music library into SQLite SELECT queries.

Schema:
{SCHEMA}

Example question/answer pairs:
{EXAMPLES}

Rules:
- Output ONLY a raw SQL SELECT statement — no explanation, no markdown, no code fences
- Never use DROP, INSERT, UPDATE, DELETE, CREATE, ALTER, or any non-SELECT statement
- Use LIKE for partial text matches
- Year columns are stored as TEXT
- Prefer COALESCE(NULLIF(final_title,''), shazam_title) over shazam_title alone
"""

@st.cache_resource
def get_claude():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def nl_to_sql(question: str) -> tuple[str | None, str | None]:
    """Convert natural language to SQL. Returns (sql, error)."""
    client = get_claude()
    if client is None:
        return None, "ANTHROPIC_API_KEY is not set. Export it before launching the GUI."

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    sql = msg.content[0].text.strip()

    # Safety guard — reject anything that isn't a SELECT
    if not re.match(r"^\s*SELECT\b", sql, re.IGNORECASE):
        return None, f"Rejected non-SELECT query: {sql[:120]}"

    return sql, None


# ---------------------------------------------------------------------------
# Canned reports
# ---------------------------------------------------------------------------

CANNED = {
    "— choose a report —": None,
    "Flagged for review": (
        "SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, "
        "language, error_msg, final_path FROM songs WHERE error_msg LIKE 'REVIEW:%' ORDER BY language"
    ),
    "No-match songs by language": (
        "SELECT language, COUNT(*) AS no_match_count FROM songs "
        "WHERE status='no_match' GROUP BY language ORDER BY no_match_count DESC"
    ),
    "Unknown Year queue": (
        "SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, "
        "COALESCE(NULLIF(final_artist,''),shazam_artist) AS artist, language, final_path "
        "FROM songs WHERE status='done' AND final_path LIKE '%Unknown Year%' ORDER BY language"
    ),
    "Unknown Album queue": (
        "SELECT song_id, COALESCE(NULLIF(final_title,''),shazam_title) AS title, "
        "COALESCE(NULLIF(final_artist,''),shazam_artist) AS artist, language, shazam_year AS year, final_path "
        "FROM songs WHERE status='done' AND final_path LIKE '%Unknown Album%' ORDER BY language"
    ),
    "Language breakdown": (
        "SELECT language, status, COUNT(*) AS count FROM songs "
        "GROUP BY language, status ORDER BY language, count DESC"
    ),
    "Transliteration cache": (
        "SELECT roman_name, language, native_name, created_at "
        "FROM artist_transliterations ORDER BY language, roman_name"
    ),
    "Errors": (
        "SELECT song_id, file_path, language, error_msg FROM songs "
        "WHERE status='error' ORDER BY language"
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def show_results(rows: list[dict], sql: str):
    if not rows:
        st.info("No results.")
        return

    st.caption(f"{len(rows)} row(s) — `{sql}`")
    st.dataframe(rows, use_container_width=True)

    # If results contain final_path and error_msg, show CLI hints for flagged songs
    if rows and "error_msg" in rows[0] and "final_path" in rows[0]:
        flagged = [r for r in rows if r.get("error_msg", "").startswith("REVIEW:")]
        if flagged:
            st.markdown("---")
            st.markdown("**CLI fix hints for flagged songs:**")
            for r in flagged:
                path = r.get("final_path", "")
                folder = "/".join(path.split("/")[:-1]) if path else ""
                st.code(
                    f"# {r.get('error_msg','')}\n"
                    f"python3 main.py --review --folder \"{folder}\"",
                    language="bash",
                )


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🎵 Sruthi")
st.caption("Your music library, searchable in plain English.")

st.markdown("---")

# -- NL query (top) ----------------------------------------------------------
st.subheader("Ask a question")
st.caption("Examples: *show me all Tamil songs from 1981* · *find everything by Ilaiyaraaja* · *how many Hindi songs do I have*")

question = st.text_input("Your question", placeholder="show me all Tamil songs from 1981")
if st.button("Search", type="primary") and question.strip():
    with st.spinner("Thinking..."):
        sql, err = nl_to_sql(question.strip())
    if err:
        st.error(err)
    elif sql:
        rows, err2 = run_sql(sql)
        if err2:
            st.error(f"Query error: {err2}")
            st.code(sql, language="sql")
        else:
            show_results(rows, sql)

st.markdown("---")

# -- Canned reports (main area results) --------------------------------------
main_area = st.container()

# -- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.header("📋 Standard reports")
    report_choice = st.selectbox("Choose a report", list(CANNED.keys()), label_visibility="collapsed")

if report_choice and CANNED[report_choice]:
    sql = CANNED[report_choice]
    rows, err = run_sql(sql)
    with main_area:
        st.subheader(report_choice)
        if err:
            st.error(f"Query error: {err}")
        else:
            show_results(rows, sql)

# -- About (bottom) ----------------------------------------------------------
st.markdown("---")
with st.expander("ℹ️  Who this is for", expanded=False):
    st.markdown("""
**Not for everyone — and that's intentional.**

If you want your music organised without any of this, just use iTunes. It does the job
beautifully for most people and you will never need this tool.

This pipeline exists for a specific problem: large collections of Tamil and Hindi MP3s
from the pre-streaming era with garbled filenames, wrong tags, and no consistent structure.

The query tool above works like a report menu. Standard reports are always available in
the sidebar. If none of them fit, describe what you want in plain English — *"show me all
Tamil songs where the album is unknown"* — and it generates the report on the fly.

**You do not need to know SQL.** In the AI age, you describe the report you need and it
gets built for you instantly. That is the only shift from the old Crystal Reports / Power BI
way of working.

This tool is **read-only** — it never writes to the database or touches your files.
To fix issues, use the CLI commands shown in the fix hints below each flagged result.
""")
