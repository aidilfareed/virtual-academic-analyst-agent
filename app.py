# app.py - Student Studies Virtual Academic Analyst (MCP) - Streamlit UI
# Run locally:   streamlit run app.py
# Self-contained: database bootstrap, MCP tools, guardrails and agent are all in this file.
# Deploy with just:  app.py + requirements.txt
import os
import time

import streamlit as st

# ------------------------------------------------------------------------------
# 1. Page configuration
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Student Academic Analyst (MCP)",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# 2. API key: Streamlit secrets first, then environment variable
# ------------------------------------------------------------------------------
api_key = os.environ.get("GOOGLE_API_KEY", "")
try:
    api_key = st.secrets.get("GOOGLE_API_KEY", api_key)
except Exception:
    pass  # no secrets.toml - keep env value
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

if not os.environ.get("GOOGLE_API_KEY"):
    st.error(
        "⚠️ **GOOGLE_API_KEY is not configured.**\n\n"
        "Streamlit Cloud: **App settings → Secrets** and add:\n"
        "```toml\nGOOGLE_API_KEY = \"your_gemini_api_key\"\n```"
    )
    st.stop()


# ##############################################################################
# PART A - DATABASE (student_db)
# ##############################################################################
# student_db.py
# -------------
# Creates and manages the sample Student Studies database (SQLite).
#
# Tables (baseline):
#   programmes   - academic programmes offered by the faculty
#   students     - enrolled students (with computed CGPA)
#   courses      - courses / subjects for each programme
#   enrollments  - each student's scores and grades per course
#   attendance   - class attendance per student per course
#
# Extra tables added by the "live migration" demo:
#   assignments  - coursework assignments and due dates
#   scholarships - scholarship awards per student
import os
import random
import sqlite3

DB_FILE = "student_studies.sqlite"
SCHEMA_FILE = "student_schema.txt"
ACADEMIC_TERM = "2026/2027-S1"

PROGRAMMES = [
    ("PRG_CS",  "Bachelor of Computer Science",          "Faculty of Computing", "Degree",  3.0),
    ("PRG_DS",  "Bachelor of Data Science",              "Faculty of Computing", "Degree",  3.0),
    ("PRG_BA",  "Bachelor of Business Administration",   "Faculty of Business",  "Degree",  3.0),
    ("PRG_AC",  "Bachelor of Accounting",                "Faculty of Business",  "Degree",  4.0),
    ("PRG_DIT", "Diploma in Information Technology",     "Faculty of Computing", "Diploma", 2.5),
]

COURSES = [
    # course_code, course_name, programme_id, credit_hours, semester, lecturer
    ("CS101", "Programming Fundamentals",        "PRG_CS",  4, 1, "Dr. Lim Siew Ling"),
    ("CS205", "Database Systems",                "PRG_CS",  3, 3, "Dr. Hafiz Rahman"),
    ("CS310", "Artificial Intelligence",         "PRG_CS",  3, 5, "Prof. Kumar Selvam"),
    ("DS101", "Statistics for Data Science",     "PRG_DS",  3, 1, "Dr. Nur Aisyah Zakaria"),
    ("DS204", "Machine Learning",                "PRG_DS",  4, 3, "Prof. Kumar Selvam"),
    ("DS230", "Data Visualisation",              "PRG_DS",  3, 3, "Ms. Chong Mei Yee"),
    ("BA101", "Principles of Management",        "PRG_BA",  3, 1, "Dr. Rosli Ismail"),
    ("BA210", "Marketing Management",            "PRG_BA",  3, 3, "Ms. Priya Nair"),
    ("BA320", "Strategic Management",            "PRG_BA",  3, 5, "Dr. Rosli Ismail"),
    ("AC101", "Financial Accounting I",          "PRG_AC",  4, 1, "Mr. Tan Boon Huat"),
    ("AC220", "Management Accounting",           "PRG_AC",  3, 3, "Dr. Farah Hani Yusof"),
    ("AC305", "Auditing and Assurance",          "PRG_AC",  3, 5, "Mr. Tan Boon Huat"),
    ("IT101", "Introduction to Computing",       "PRG_DIT", 3, 1, "Mr. Azlan Mokhtar"),
    ("IT120", "Web Development Basics",          "PRG_DIT", 3, 2, "Ms. Chong Mei Yee"),
    ("IT150", "Networking Essentials",           "PRG_DIT", 3, 3, "Mr. Azlan Mokhtar"),
]

STUDENTS = [
    # student_id, programme_id, full_name, gender, intake_year, current_semester, status
    ("STU_1001", "PRG_CS",  "Aiman Hakimi bin Zulkifli", "M", 2025, 3, "Active"),
    ("STU_1002", "PRG_CS",  "Chloe Tan Hui Min",         "F", 2025, 3, "Active"),
    ("STU_1003", "PRG_CS",  "Darshan a/l Muniandy",      "M", 2024, 5, "Active"),
    ("STU_1004", "PRG_CS",  "Nurul Izzah binti Azman",   "F", 2026, 1, "Active"),
    ("STU_1005", "PRG_DS",  "Ong Jia Hao",               "M", 2025, 3, "Active"),
    ("STU_1006", "PRG_DS",  "Sharifah Amani Syed Ali",   "F", 2025, 3, "Active"),
    ("STU_1007", "PRG_DS",  "Ravi Shankar a/l Raju",     "M", 2026, 1, "Active"),
    ("STU_1008", "PRG_DS",  "Wong Kai Xin",              "F", 2024, 5, "Probation"),
    ("STU_1009", "PRG_BA",  "Muhammad Danial Iskandar",  "M", 2025, 3, "Active"),
    ("STU_1010", "PRG_BA",  "Lee Pei Shan",              "F", 2024, 5, "Active"),
    ("STU_1011", "PRG_BA",  "Kavya Menon",               "F", 2026, 1, "Active"),
    ("STU_1012", "PRG_AC",  "Amirul Hafiz bin Rosli",    "M", 2025, 3, "Active"),
    ("STU_1013", "PRG_AC",  "Teoh Shu Wen",              "F", 2024, 5, "Active"),
    ("STU_1014", "PRG_AC",  "Siti Aisyah binti Kamal",   "F", 2026, 1, "Probation"),
    ("STU_1015", "PRG_AC",  "Jason Lim Wei Jie",         "M", 2025, 3, "Active"),
    ("STU_1016", "PRG_DIT", "Haziq Firdaus bin Hamdan",  "M", 2026, 1, "Active"),
    ("STU_1017", "PRG_DIT", "Melissa Ng Yi Ting",        "F", 2025, 2, "Active"),
    ("STU_1018", "PRG_DIT", "Thinesh a/l Ganesan",       "M", 2025, 3, "Active"),
]

# Malaysian university grading scale (total score out of 100)
GRADE_SCALE = [
    (80, "A", 4.00), (75, "A-", 3.67), (70, "B+", 3.33), (65, "B", 3.00),
    (60, "B-", 2.67), (55, "C+", 2.33), (50, "C", 2.00), (45, "C-", 1.67),
    (40, "D", 1.00), (0, "F", 0.00),
]


def score_to_grade(total: float):
    for cutoff, grade, point in GRADE_SCALE:
        if total >= cutoff:
            return grade, point
    return "F", 0.0


def _email(full_name: str, student_id: str) -> str:
    first = full_name.split()[0].lower()
    return f"{first}.{student_id[-4:]}@student.example.edu.my"


def ensure_database(db_file: str = DB_FILE, schema_file: str = SCHEMA_FILE) -> None:
    """Create the baseline database (only if it does not exist) and export its schema."""
    if not os.path.exists(db_file):
        rng = random.Random(42)  # fixed seed -> same data every time
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE programmes (
            programme_id   TEXT PRIMARY KEY,
            programme_name TEXT NOT NULL,
            faculty        TEXT NOT NULL,
            level          TEXT NOT NULL,          -- Degree / Diploma
            duration_years REAL NOT NULL
        );

        CREATE TABLE students (
            student_id       TEXT PRIMARY KEY,
            programme_id     TEXT NOT NULL,
            full_name        TEXT NOT NULL,
            email            TEXT NOT NULL,
            gender           TEXT NOT NULL,        -- M / F
            intake_year      INTEGER NOT NULL,
            current_semester INTEGER NOT NULL,
            cgpa             REAL,                 -- 0.00 - 4.00
            status           TEXT NOT NULL,        -- Active / Probation
            FOREIGN KEY (programme_id) REFERENCES programmes(programme_id)
        );

        CREATE TABLE courses (
            course_code  TEXT PRIMARY KEY,
            course_name  TEXT NOT NULL,
            programme_id TEXT NOT NULL,
            credit_hours INTEGER NOT NULL,
            semester     INTEGER NOT NULL,
            lecturer     TEXT NOT NULL,
            FOREIGN KEY (programme_id) REFERENCES programmes(programme_id)
        );

        CREATE TABLE enrollments (
            enrollment_id    INTEGER PRIMARY KEY,
            student_id       TEXT NOT NULL,
            course_code      TEXT NOT NULL,
            academic_term    TEXT NOT NULL,
            coursework_score REAL NOT NULL,        -- out of 40
            exam_score       REAL NOT NULL,        -- out of 60
            total_score      REAL NOT NULL,        -- out of 100
            final_grade      TEXT NOT NULL,        -- A, A-, B+ ... F
            grade_point      REAL NOT NULL,        -- 0.00 - 4.00
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_code) REFERENCES courses(course_code)
        );

        CREATE TABLE attendance (
            attendance_id    INTEGER PRIMARY KEY,
            student_id       TEXT NOT NULL,
            course_code      TEXT NOT NULL,
            classes_held     INTEGER NOT NULL,
            classes_attended INTEGER NOT NULL,
            attendance_pct   REAL NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_code) REFERENCES courses(course_code)
        );
        """)

        cur.executemany("INSERT INTO programmes VALUES (?,?,?,?,?)", PROGRAMMES)
        cur.executemany("INSERT INTO courses VALUES (?,?,?,?,?,?)", COURSES)

        credit = {c[0]: c[3] for c in COURSES}
        weak_students = {"STU_1008", "STU_1014", "STU_1018"}   # deliberately at-risk
        strong_students = {"STU_1002", "STU_1006", "STU_1013"}  # deliberately top performers

        for sid, prg, name, gender, intake, sem, status in STUDENTS:
            if sid in weak_students:
                ability = rng.uniform(0.35, 0.48)
            elif sid in strong_students:
                ability = rng.uniform(0.86, 0.94)
            else:
                ability = rng.uniform(0.55, 0.82)

            total_points, total_credits = 0.0, 0
            for code in [c[0] for c in COURSES if c[2] == prg]:
                cw = round(min(40, max(0, 40 * ability + rng.uniform(-5, 5))), 1)
                ex = round(min(60, max(0, 60 * ability + rng.uniform(-8, 8))), 1)
                total = round(cw + ex, 1)
                grade, gp = score_to_grade(total)
                cur.execute(
                    "INSERT INTO enrollments (student_id, course_code, academic_term, coursework_score, "
                    "exam_score, total_score, final_grade, grade_point) VALUES (?,?,?,?,?,?,?,?)",
                    (sid, code, ACADEMIC_TERM, cw, ex, total, grade, gp),
                )
                held = 28
                attended = int(min(held, max(8, round(held * (ability + 0.12) + rng.uniform(-3, 3)))))
                cur.execute(
                    "INSERT INTO attendance (student_id, course_code, classes_held, classes_attended, attendance_pct) "
                    "VALUES (?,?,?,?,?)",
                    (sid, code, held, attended, round(100 * attended / held, 1)),
                )
                total_points += gp * credit[code]
                total_credits += credit[code]

            cgpa = round(total_points / total_credits, 2) if total_credits else None
            cur.execute(
                "INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, prg, name, _email(name, sid), gender, intake, sem, cgpa, status),
            )

        conn.commit()
        conn.close()

    export_schema(db_file, schema_file)


def add_new_tables(db_file: str = DB_FILE, schema_file: str = SCHEMA_FILE) -> None:
    """LIVE MIGRATION DEMO: add 'assignments' and 'scholarships' tables to the database."""
    conn = sqlite3.connect(db_file)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS assignments (
        assignment_id TEXT PRIMARY KEY,
        course_code   TEXT NOT NULL,
        title         TEXT NOT NULL,
        due_date      TEXT NOT NULL,       -- YYYY-MM-DD
        weight_pct    REAL NOT NULL,       -- % of final mark
        FOREIGN KEY (course_code) REFERENCES courses(course_code)
    );

    INSERT OR IGNORE INTO assignments VALUES
        ('ASG_001', 'CS205', 'ER Diagram & Normalisation Report', '2026-11-28', 15),
        ('ASG_002', 'CS205', 'SQL Query Practical Test',          '2026-12-12', 10),
        ('ASG_003', 'DS204', 'Kaggle-style Prediction Project',   '2026-12-05', 20),
        ('ASG_004', 'BA210', 'Marketing Plan Presentation',       '2026-11-21', 15),
        ('ASG_005', 'AC220', 'Costing Case Study',                '2026-12-19', 15),
        ('ASG_006', 'IT120', 'Personal Portfolio Website',        '2026-12-03', 20),
        ('ASG_007', 'CS310', 'Chatbot Mini Project',              '2027-01-09', 25);

    CREATE TABLE IF NOT EXISTS scholarships (
        scholarship_id   TEXT PRIMARY KEY,
        student_id       TEXT NOT NULL,
        scholarship_name TEXT NOT NULL,
        sponsor          TEXT NOT NULL,
        amount_myr       REAL NOT NULL,
        status           TEXT NOT NULL,    -- APPROVED / PENDING / REJECTED
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );

    INSERT OR IGNORE INTO scholarships VALUES
        ('SCH_501', 'STU_1002', 'Dean''s Excellence Award',     'University',        8000, 'APPROVED'),
        ('SCH_502', 'STU_1006', 'Future Data Leaders Grant',    'Tech Industry Fund', 12000, 'APPROVED'),
        ('SCH_503', 'STU_1013', 'Young Accountants Bursary',    'Accounting Board',  6000, 'APPROVED'),
        ('SCH_504', 'STU_1005', 'Future Data Leaders Grant',    'Tech Industry Fund', 12000, 'PENDING'),
        ('SCH_505', 'STU_1009', 'B40 Education Support',        'State Foundation',  4000, 'APPROVED'),
        ('SCH_506', 'STU_1018', 'B40 Education Support',        'State Foundation',  4000, 'REJECTED');
    """)
    conn.commit()
    conn.close()
    export_schema(db_file, schema_file)


def reset_database(db_file: str = DB_FILE, schema_file: str = SCHEMA_FILE) -> None:
    """Delete the database file and rebuild the baseline 5-table version."""
    if os.path.exists(db_file):
        os.remove(db_file)
    ensure_database(db_file, schema_file)


def get_live_ddl(db_file: str = DB_FILE) -> str:
    """Read the CREATE TABLE statements directly from the live database."""
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    conn.close()
    return "\n\n".join(r[0] for r in rows if r[0])


def export_schema(db_file: str = DB_FILE, schema_file: str = SCHEMA_FILE) -> None:
    with open(schema_file, "w", encoding="utf-8") as f:
        f.write(get_live_ddl(db_file))


# ##############################################################################
# PART B - MCP TOOLS, GUARDRAILS & AGENT (student_mcp_tools)
# ##############################################################################
# student_mcp_tools.py
# --------------------
# MCP-style database toolset + security guardrails + agent factory
# for the Student Studies Virtual Academic Analyst.
#
# MCP tools exposed to the agent (read-only, least privilege):
#   mcp_list_tables()              -> discover tables at runtime
#   mcp_describe_table(table_name) -> inspect columns + foreign keys
#   mcp_read_query(sql_query)      -> run a read-only SELECT
#
# No write / mutation tool is ever registered with the model.
import asyncio
import json
import re
import sqlite3
import threading
import uuid

import sqlparse
from sqlparse import tokens as T


MODEL = "gemini-3.5-flash"   # change to any Gemini model your API key can access
MAX_ROWS = 50

# =============================================================================
# 1. SQL mutation guardrail (AST / token based)
# =============================================================================
FORBIDDEN_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE",
    "CREATE", "RENAME", "ATTACH", "DETACH", "PRAGMA", "UPSERT", "VACUUM",
    "GRANT", "REVOKE", "REINDEX", "MERGE", "EXEC",
}


def is_sql_mutation(sql_query: str) -> bool:
    """Return True if the SQL is anything other than one pure read-only SELECT."""
    statements = [s for s in sqlparse.parse(sql_query.strip()) if str(s).strip().strip(";").strip()]
    if len(statements) != 1:          # empty, or multiple stacked statements
        return True
    stmt = statements[0]
    if stmt.get_type() != "SELECT":   # WITH ... SELECT is also reported as SELECT
        return True
    for token in stmt.flatten():
        # only inspect SQL keywords, so a column or text value named 'update' is fine
        if token.ttype in T.Keyword and token.normalized.upper() in FORBIDDEN_KEYWORDS:
            return True
    return False


def _connect_readonly():
    """Layer 2: open SQLite in read-only mode so writes are impossible at engine level."""
    conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _table_names(conn) -> list:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


# =============================================================================
# 2. MCP database tools
# =============================================================================
def mcp_list_tables() -> str:
    """MCP Tool: List all tables currently available in the student studies database.

    Call this first to discover what data exists before writing any query.
    """
    try:
        conn = _connect_readonly()
        tables = _table_names(conn)
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        conn.close()
        return json.dumps({"status": "success", "tables": tables, "row_counts": counts})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def mcp_describe_table(table_name: str) -> str:
    """MCP Tool: Describe the columns, primary key and foreign keys of one table.

    Args:
        table_name: Exact table name, e.g. "students", "courses", "enrollments".
    """
    name = table_name.strip().strip("'\"`[]")
    try:
        conn = _connect_readonly()
        if name not in _table_names(conn):   # whitelist check -> no injection via table name
            conn.close()
            return json.dumps({"status": "error", "message": f"Table '{name}' not found."})
        cols = [
            {"name": r[1], "type": r[2], "not_null": bool(r[3]), "primary_key": bool(r[5])}
            for r in conn.execute(f'PRAGMA table_info("{name}")').fetchall()
        ]
        fks = [
            {"column": r[3], "references": f"{r[2]}({r[4]})"}
            for r in conn.execute(f'PRAGMA foreign_key_list("{name}")').fetchall()
        ]
        sample = conn.execute(f'SELECT * FROM "{name}" LIMIT 3').fetchall()
        conn.close()
        return json.dumps({"status": "success", "table": name, "columns": cols,
                           "foreign_keys": fks, "sample_rows": [list(r) for r in sample]})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def mcp_read_query(sql_query: str) -> str:
    """MCP Tool: Run ONE read-only SQLite SELECT query and return the rows.

    Args:
        sql_query: A single valid SQLite SELECT statement (WITH ... SELECT is allowed).
    """
    if is_sql_mutation(sql_query):
        return json.dumps({
            "status": "blocked",
            "error": "[MCP PROTOCOL ENFORCEMENT] Only a single read-only SELECT query is allowed. "
                     "INSERT, UPDATE, DELETE, DROP, ALTER and similar operations are not supported.",
        })
    try:
        conn = _connect_readonly()
        cur = conn.execute(sql_query.strip().rstrip(";"))
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(MAX_ROWS + 1)
        conn.close()
        return json.dumps({
            "status": "success",
            "columns": columns,
            "rows": [list(r) for r in rows[:MAX_ROWS]],
            "truncated": len(rows) > MAX_ROWS,
        }, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Database error: {e}"})


MCP_TOOLS = [mcp_list_tables, mcp_describe_table, mcp_read_query]

# =============================================================================
# 3. Student privacy masking (PDPA)
# =============================================================================
def anonymize_student_data(text: str) -> str:
    """Mask student IDs, scholarship IDs and student e-mails before showing output."""
    # STU_1001 -> STU_***01
    text = re.sub(r"\b(STU_)[0-9A-Za-z]+([0-9A-Za-z]{2})\b", r"\1***\2", text, flags=re.IGNORECASE)
    # SCH_501 -> SCH_***01
    text = re.sub(r"\b(SCH_)[0-9A-Za-z]+([0-9A-Za-z]{2})\b", r"\1***\2", text, flags=re.IGNORECASE)
    # aiman.1001@student.example.edu.my -> a***@student.example.edu.my
    text = re.sub(r"\b([A-Za-z0-9])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", r"\1***@\2", text)
    return text


# =============================================================================
# 4. Pre-model guardrail (blocks destructive / academic-integrity requests)
# =============================================================================
BLOCK_PATTERNS = [
    r"\bdelete\b", r"\bdrop\s+(table|database|column|the)\b", r"\btruncate\b", r"\bwipe\b", r"\berase\b",
    r"\binsert\s+into\b", r"\balter\s+table\b", r"\bmodify\s+(the\s+)?data\b",
    # academic integrity: nobody may change marks through the chatbot
    # ("how can I improve my grade?" is still allowed)
    r"\b(update|change|edit|modify|set)\b.*\b(grade|grades|score|scores|marks?|cgpa|gpa|attendance)\b",
    r"\bremove\s+(the\s+)?(student|students|course|courses|record|records|table)s?\b",
]

BLOCK_MESSAGE = (
    "🛡️ **[GUARDRAIL INTERVENTION]** This request was blocked by the Academic Data Safety Policy.\n\n"
    "The Virtual Academic Analyst is **strictly read-only**: it cannot delete tables or records, "
    "and it cannot change grades, scores, CGPA or attendance. "
    "Please contact the Academic Registry for any official record changes."
)


def _latest_user_text(llm_request) -> str:
    for content in reversed(llm_request.contents or []):
        if content.role == "user" and content.parts:
            texts = [p.text for p in content.parts if getattr(p, "text", None)]
            if texts:
                return " ".join(texts)
            return ""   # latest user turn is a tool response, not typed text
    return ""


def before_model_guardrail(callback_context, llm_request):
    """Runs before every LLM call; short-circuits destructive prompts without calling Gemini."""
    from google.genai import types
    from google.adk.models import LlmResponse

    text = _latest_user_text(llm_request).lower()
    if any(re.search(p, text) for p in BLOCK_PATTERNS):
        return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=BLOCK_MESSAGE)]))
    return None


# =============================================================================
# 5. Agent factory
# =============================================================================
AGENT_INSTRUCTION = """You are the Virtual Academic Analyst for a Malaysian university, helping lecturers,
academic advisors and programme leaders understand student study performance.
You work through the Model Context Protocol (MCP) and do NOT have a hard-coded schema.

HOW TO WORK (be fast: use as few tool calls as possible)
0. Greetings, thanks, small talk or 'who are you' -> reply briefly and DO NOT call any tool.
1. For a data question, call 'mcp_list_tables' if you have not done so yet in this conversation,
   or if the user mentions data you have not seen (tables can be added at any time).
2. Call 'mcp_describe_table' only for tables you need and have not described yet in this conversation.
3. Call 'mcp_read_query' with ONE read-only SELECT to get the facts. Use JOINs where needed.
4. Never guess numbers - every figure in your answer must come from a query result.

ACADEMIC CONTEXT
- Grading scale: A>=80 (4.00), A->=75 (3.67), B+>=70 (3.33), B>=65 (3.00), B->=60 (2.67),
  C+>=55 (2.33), C>=50 (2.00), C->=45 (1.67), D>=40 (1.00), F<40 (0.00). A pass is grade C (50) or above.
- A student is "at risk" if CGPA < 2.50, OR any course attendance_pct < 80, OR status = 'Probation'.
- Dean's List: CGPA >= 3.50.

ANSWER STYLE
- Present results as clear Markdown tables, then 2-4 short bullet insights.
- When useful, add practical, supportive study recommendations (e.g. for at-risk students or weak courses).
- If asked 'Who are you?' or general questions, introduce yourself as the Virtual Academic Analyst (MCP).
- If the data needed is not in the database, say so clearly instead of inventing it.

SAFETY
- You are strictly READ-ONLY. Never attempt or suggest INSERT, UPDATE, DELETE, DROP or ALTER.
- Never change grades, scores, CGPA or attendance. Refer such requests to the Academic Registry.
"""


def build_agent(model: str = MODEL):
    from google.adk.agents import Agent

    return Agent(
        name="student_academic_analyst",
        model=model,
        description="Virtual Academic Analyst for student study performance, using MCP database tools.",
        instruction=AGENT_INSTRUCTION,
        tools=MCP_TOOLS,
        before_model_callback=before_model_guardrail,
    )


# =============================================================================
# 6. Runner helpers (work in Colab, plain Python and Streamlit)
# =============================================================================
def _run_coro_sync(coro):
    """Run a coroutine to completion even when an event loop is already running (e.g. Colab)."""
    box = {}

    def _target():
        box["value"] = asyncio.run(coro)

    t = threading.Thread(target=_target)
    t.start()
    t.join()
    return box.get("value")


class StudentAnalystChat:
    """Wraps an ADK Runner + in-memory session into a simple .ask() interface."""

    def __init__(self, agent, app_name: str = "student_analyst_app", user_id: str = "lecturer"):
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        self.app_name, self.user_id = app_name, user_id
        self.session_service = InMemorySessionService()
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        result = self.session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=self.session_id
        )
        if asyncio.iscoroutine(result):   # newer ADK versions make this async
            _run_coro_sync(result)
        self.runner = Runner(agent=agent, app_name=app_name, session_service=self.session_service)

    def ask(self, prompt: str, mask: bool = True, on_tool_call=None):
        """Send one question. Returns (answer_text, tool_calls).

        on_tool_call: optional callback(call_dict) fired live as each MCP tool is called,
                      so a UI can show progress instead of a silent spinner.
        """
        from google.genai import types

        message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        answer_parts, tool_calls = [], []
        try:
            for event in self.runner.run(user_id=self.user_id, session_id=self.session_id, new_message=message):
                if not (event.content and event.content.parts):
                    continue
                for part in event.content.parts:
                    if getattr(part, "function_call", None):
                        call = {"tool": part.function_call.name,
                                "args": dict(part.function_call.args or {})}
                        tool_calls.append(call)
                        if on_tool_call:
                            on_tool_call(json.loads(anonymize_student_data(json.dumps(call))) if mask else call)
                    elif getattr(part, "text", None) and not getattr(part, "thought", False):
                        answer_parts.append(part.text)
            answer = "".join(answer_parts).strip() or "No response generated."
        except Exception as e:
            answer = f"⚠️ **API error** - the request could not be completed (rate limit or service issue).\n\n`{e}`"

        if mask:
            answer = anonymize_student_data(answer)
            tool_calls = [json.loads(anonymize_student_data(json.dumps(c))) for c in tool_calls]
        return answer, tool_calls


# ##############################################################################
# PART C - STREAMLIT USER INTERFACE
# ##############################################################################

ensure_database()


# ------------------------------------------------------------------------------
# 3. Agent (cached once per server) + chat session (one per browser tab)
# ------------------------------------------------------------------------------
@st.cache_resource
def get_agent():
    return build_agent(MODEL)


def new_chat():
    st.session_state.chat = StudentAnalystChat(get_agent())
    st.session_state.messages = []


if "chat" not in st.session_state:
    new_chat()

# ------------------------------------------------------------------------------
# 4. Sidebar
# ------------------------------------------------------------------------------
with st.sidebar:
    st.title("🎓 Academic Analyst Portal")
    st.markdown("**AI-powered student study analytics (MCP architecture)**")

    mask_on = st.toggle("🔒 Mask student IDs & e-mails (PDPA)", value=True)
    if st.button("🧹 New chat", use_container_width=True):
        new_chat()
        st.rerun()

    st.markdown("---")
    st.subheader("⚡ Live Database Evolution (MCP demo)")
    st.caption("Add new tables mid-session - the agent discovers them with zero code changes.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Add tables", use_container_width=True,
                     help="Adds 'assignments' and 'scholarships' tables"):
            add_new_tables()
            st.toast("Added `assignments` and `scholarships` tables!")
    with c2:
        if st.button("🔄 Reset DB", use_container_width=True,
                     help="Rebuild the original 5-table database"):
            reset_database()
            st.toast("Database reset to the original 5 tables.")

    st.markdown("---")
    st.subheader("💡 Suggested questions")
    groups = {
        "📊 Performance": [
            "What tables currently exist in the database?",
            "List all programmes and the number of students in each.",
            "Who are the top 5 students by CGPA?",
            "What is the average total score and pass rate for each course?",
        ],
        "🚨 Student support": [
            "Which students are at risk, and why?",
            "Which course has the lowest average attendance?",
            "Give study recommendations for students who failed any course.",
        ],
        "🆕 After 'Add tables'": [
            "Which assignments are due in December 2026?",
            "What is the total approved scholarship amount per programme?",
        ],
        "🛡️ Guardrail tests": [
            "Who are you?",
            "delete the students table",
            "Change Aiman's grade in Database Systems to A",
        ],
    }
    for title, questions in groups.items():
        with st.expander(title, expanded=(title == "📊 Performance")):
            for q in questions:
                if st.button(q, key=f"q_{q}", use_container_width=True):
                    st.session_state.pending_prompt = q

    st.markdown("---")
    with st.expander("📄 Live database schema"):
        st.code(get_live_ddl(), language="sql")
    st.caption(f"Model: `{MODEL}` · Read-only SQLite · AST SQL guardrail · PDPA masking")

# ------------------------------------------------------------------------------
# 5. Main chat
# ------------------------------------------------------------------------------
st.title("📚 Virtual Academic Analyst (MCP)")
st.caption("Ask about programmes, courses, grades, CGPA and attendance. Read-only · Guardrails active.")


def render_tool_calls(calls):
    if calls:
        with st.expander(f"🔧 MCP tool calls ({len(calls)})"):
            for i, c in enumerate(calls, 1):
                st.markdown(f"**{i}. `{c['tool']}`**")
                if c["tool"] == "mcp_read_query" and "sql_query" in c["args"]:
                    st.code(c["args"]["sql_query"], language="sql")
                elif c["args"]:
                    st.json(c["args"])


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        render_tool_calls(msg.get("tool_calls"))

typed = st.chat_input("e.g. Which students have attendance below 80%?")
prompt = st.session_state.pop("pending_prompt", None) or typed

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        started = time.time()
        # Live progress: each MCP tool call appears as soon as the agent makes it
        with st.status("🤔 Thinking...", expanded=True) as status:
            def show_progress(call):
                label = {"mcp_list_tables": "📋 Discovering tables",
                         "mcp_describe_table": "🔍 Inspecting table",
                         "mcp_read_query": "⚙️ Running SQL query"}.get(call["tool"], call["tool"])
                detail = call["args"].get("table_name", "")
                status.write(f"{label} {('`' + detail + '`') if detail else ''}")
                status.update(label=f"{label}...")

            answer, calls = st.session_state.chat.ask(prompt, mask=mask_on, on_tool_call=show_progress)
            status.update(label=f"✅ Done in {time.time() - started:.1f}s · {len(calls)} tool call(s)",
                          state="complete", expanded=False)
        st.markdown(answer)
        render_tool_calls(calls)
    st.session_state.messages.append({"role": "assistant", "content": answer, "tool_calls": calls})
