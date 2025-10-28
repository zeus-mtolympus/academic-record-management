import sqlite3

# Database path
DB_PATH = "college.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Enable foreign key constraint
cur.execute("PRAGMA foreign_keys = ON;")

# ---------- CREATE DEPARTMENTS TABLE ----------
cur.execute("""
CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT PRIMARY KEY,
    department_name TEXT NOT NULL
);
""")

# Insert departments
departments = [
    ("CSE", "Computer Science and Engineering"),
    ("ECE", "Electronics and Communication Engineering"),
    ("EEE", "Electrical and Electronics Engineering")
]

cur.executemany("INSERT OR IGNORE INTO departments (department_id, department_name) VALUES (?, ?)", departments)

conn.commit()
conn.close()

print("✅ Departments, Students, and Faculty tables created successfully with foreign key relations.")
