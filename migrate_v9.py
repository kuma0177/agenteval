import sqlite3
import os

# 1. Find the database
db_path = None
for candidate in ["./agenteval.db", "/app/agenteval.db"]:
    if os.path.exists(candidate):
        db_path = candidate
        break

if db_path is None:
    print("ERROR: Database not found at ./agenteval.db or /app/agenteval.db")
    exit(1)

print(f"Found database: {db_path}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()


def add_column_if_missing(table, column, col_type):
    cur.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"  Added {table}.{column}")
    else:
        print(f"  Skipped {table}.{column} (already exists)")


# 2. Add columns to traces table
print("\n[traces] Adding new columns...")
add_column_if_missing("traces", "score_task_performance", "REAL")
add_column_if_missing("traces", "score_reasoning_autonomy", "REAL")
add_column_if_missing("traces", "score_operational_reliability", "REAL")
add_column_if_missing("traces", "score_user_experience", "REAL")
add_column_if_missing("traces", "score_ethics_safety", "REAL")
add_column_if_missing("traces", "score_efficiency", "REAL")
add_column_if_missing("traces", "client_comment", "TEXT")
add_column_if_missing("traces", "client_flagged", "INTEGER DEFAULT 0")
conn.commit()
print("[traces] Done.")

# 3. Add columns to jobs table
print("\n[jobs] Adding new columns...")
add_column_if_missing("jobs", "client_password_hash", "TEXT")
add_column_if_missing("jobs", "last_viewed_at", "DATETIME")
conn.commit()
print("[jobs] Done.")

# 4. Add columns to reviewer_profiles table
print("\n[reviewer_profiles] Adding new columns...")
add_column_if_missing("reviewer_profiles", "domain_scores", "TEXT")
add_column_if_missing("reviewer_profiles", "quiz_token", "TEXT")
add_column_if_missing("reviewer_profiles", "quiz_score", "REAL")
add_column_if_missing("reviewer_profiles", "quiz_submitted_at", "DATETIME")
add_column_if_missing("reviewer_profiles", "trial_token", "TEXT")
add_column_if_missing("reviewer_profiles", "trial_agreement_rate", "REAL")
add_column_if_missing("reviewer_profiles", "nda_signed_at", "DATETIME")
add_column_if_missing("reviewer_profiles", "nda_ip_address", "TEXT")
add_column_if_missing("reviewer_profiles", "total_earnings_usd", "REAL DEFAULT 0")
add_column_if_missing("reviewer_profiles", "stripe_connect_id", "TEXT")
conn.commit()
print("[reviewer_profiles] Done.")

# 5. Create agent_profiles table
print("\n[agent_profiles] Creating table if not exists...")
cur.execute("""
CREATE TABLE IF NOT EXISTS agent_profiles (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_description TEXT,
    is_public INTEGER DEFAULT 0,
    overall_avg REAL,
    task_performance_avg REAL,
    reasoning_autonomy_avg REAL,
    operational_reliability_avg REAL,
    user_experience_avg REAL,
    ethics_safety_avg REAL,
    efficiency_avg REAL,
    audit_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
)
""")
conn.commit()
print("[agent_profiles] Done.")

# 6. Create email_log table
print("\n[email_log] Creating table if not exists...")
cur.execute("""
CREATE TABLE IF NOT EXISTS email_log (
    id TEXT PRIMARY KEY,
    recipient_email TEXT NOT NULL,
    email_type TEXT NOT NULL,
    job_id TEXT,
    reviewer_id TEXT,
    resend_message_id TEXT,
    status TEXT DEFAULT 'SENT',
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
)
""")
conn.commit()
print("[email_log] Done.")

# 7. Create reviewer_quizzes table
print("\n[reviewer_quizzes] Creating table if not exists...")
cur.execute("""
CREATE TABLE IF NOT EXISTS reviewer_quizzes (
    id TEXT PRIMARY KEY,
    reviewer_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    questions TEXT NOT NULL,
    answers TEXT,
    score REAL,
    status TEXT DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    submitted_at DATETIME
)
""")
conn.commit()
print("[reviewer_quizzes] Done.")

conn.close()
print("\nMigration complete.")
