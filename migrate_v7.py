import sqlite3
import os

# 1. Find the database file
db_paths = ["./agenteval.db", "/app/agenteval.db"]
db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if db_path is None:
    print("ERROR: Could not find agenteval.db in any expected location.")
    exit(1)

print(f"Found database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. Add columns to traces table
new_columns = [
    ("llm_score_overall", "REAL"),
    ("failure_category", "TEXT"),
    ("failure_detail", "TEXT"),
    ("score_task_completion", "REAL"),
    ("score_tool_selection", "REAL"),
    ("score_reasoning", "REAL"),
    ("score_policy_compliance", "REAL"),
    ("score_hallucination_risk", "REAL"),
    ("dim_notes", "TEXT"),
]

for col_name, col_type in new_columns:
    try:
        cursor.execute(f"ALTER TABLE traces ADD COLUMN {col_name} {col_type}")
        conn.commit()
        print(f"Added column {col_name} to traces")
    except sqlite3.OperationalError:
        print(f"Skipping {col_name} (already exists)")

# 3. Copy old data from llm_score if it exists
try:
    cursor.execute(
        "UPDATE traces SET llm_score_overall = llm_score "
        "WHERE llm_score IS NOT NULL AND llm_score_overall IS NULL"
    )
    conn.commit()
    print(f"Copied llm_score -> llm_score_overall ({cursor.rowcount} rows updated)")
except sqlite3.OperationalError:
    print("Skipping llm_score copy (column does not exist)")

# 4. Create reviewer_profiles table
cursor.execute("""
CREATE TABLE IF NOT EXISTS reviewer_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    domain_expertise TEXT NOT NULL,
    years_experience INTEGER,
    linkedin_url TEXT,
    hourly_rate_usd INTEGER,
    availability TEXT,
    bio TEXT,
    status TEXT DEFAULT 'PENDING',
    rating REAL,
    completed_reviews INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME,
    notes TEXT
)
""")
conn.commit()
print("reviewer_profiles table created")

conn.close()
print("Migration complete.")
