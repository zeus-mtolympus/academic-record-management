import sqlite3

# Connect to the database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# List of unnecessary / deprecated tables to drop
unnecessary_tables = [
    "student_email",
    "student_phone",
    "student_guardian_email",
    "student_guardian_phone",
    "faculty_email",
    "faculty_phone"
]

# Drop each table if it exists
for table in unnecessary_tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"Dropped table: {table}")

# Commit and close
conn.commit()
conn.close()

print("\nCleanup complete — unnecessary tables removed successfully!")
