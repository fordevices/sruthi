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

# -- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎵 Sruthi")
    st.markdown("### ஸ்ருதி")
    st.caption("Your music library, searchable in plain English.")
    st.markdown("---")

    st.markdown("**Standard reports**")
    _keys = list(CANNED.keys())
    if "report_idx" not in st.session_state:
        st.session_state.report_idx = 0
    report_choice = st.selectbox("report", _keys, index=st.session_state.report_idx, label_visibility="collapsed")
    st.session_state.report_idx = _keys.index(report_choice)
    if report_choice and CANNED.get(report_choice):
        if st.button("✕ Clear report", use_container_width=True):
            st.session_state.report_idx = 0
            st.rerun()

    st.markdown("---")
    st.markdown("[GitHub project](https://github.com/fordevices/mp3-organizer-pipeline)")

# -- Resolve report rows (needed to decide search mode) ----------------------
report_rows: list[dict] = []
report_sql = ""
report_err = None
report_active = bool(report_choice and CANNED.get(report_choice))

if report_active:
    report_sql = CANNED[report_choice]
    report_rows, report_err = run_sql(report_sql)

# -- Search bar (single row) -------------------------------------------------
report_mode = report_active and not report_err and report_rows
placeholder = "Filter results..." if report_mode else "show me all Tamil songs from 1981"

with st.form(key="search_form", clear_on_submit=False):
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input("search", placeholder=placeholder, label_visibility="collapsed")
    with col2:
        submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

# -- Main area ---------------------------------------------------------------
if report_active:
    st.subheader(report_choice)
    if report_err:
        st.error(f"Query error: {report_err}")
    else:
        rows = report_rows
        # Filter within report if query entered
        if submitted and query.strip():
            needle = query.strip().lower()
            rows = [r for r in rows if any(needle in str(v).lower() for v in r.values())]
            st.caption(f'{len(rows)} of {len(report_rows)} row(s) matching "{query}"')
        show_results(rows, report_sql)

elif submitted and query.strip():
    with st.spinner("Thinking..."):
        sql, err = nl_to_sql(query.strip())
    if err:
        st.error(err)
    elif sql:
        rows, err2 = run_sql(sql)
        if err2:
            st.error(f"Query error: {err2}")
            st.code(sql, language="sql")
        else:
            show_results(rows, sql)

# -- About (bottom) ----------------------------------------------------------
st.markdown("---")
with st.expander("ℹ️  About Sruthi", expanded=False):
    st.markdown("""
**Sruthi** was built for a specific problem: a large collection of Tamil, Hindi, and English
MP3s from the pre-streaming era — ripped from CDs, filed in folders named by guesswork,
with garbled filenames and wrong or missing ID3 tags. Standard tools (beets, MusicBrainz
Picard, AcoustID) have poor coverage of Indian film music pre-2000, especially Tamil.

The pipeline behind this page uses ShazamIO to identify songs by audio fingerprint.
Shazam's database has excellent Indian music coverage because millions of Indian users have
been Shazaming those songs for years. After a 5,550-file batch run the library went from
a pile of mystery files to a clean, tagged, organised collection — 68% matched automatically,
the rest reviewed by hand.

Sruthi is the read-only inspection layer on top of that pipeline. It exists so you can ask
questions about your library in plain English instead of writing SQL — and because in the AI
age, you should be able to describe the report you need rather than define it in a query
language. Standard reports are always available in the sidebar. If none fit, just ask.

This tool is **read-only** — it never writes to the database or touches your files.
To fix issues, use the CLI commands shown in the fix hints below each flagged result.

Named after *sruthi* (ஸ்ருதி) — the foundational note in Indian classical music,
the reference pitch everything else is tuned to.
""")
