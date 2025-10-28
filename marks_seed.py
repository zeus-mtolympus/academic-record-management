import sqlite3
import random
from datetime import date, timedelta

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

total_records = 0
total_tables = 0

# Fetch all course details
cursor.execute("SELECT course_id, semester, year, department_id FROM courses")
courses = cursor.fetchall()

# Fetch enrollments once (to map students to courses)
cursor.execute("""
SELECT e.course_id, e.institute_id, s.roll_no, e.year
FROM enrollments e
JOIN students s ON e.institute_id = s.institute_id
""")
enrollments = cursor.fetchall()

# Build mapping: (course_id, academic_year) → [(roll_no, institute_id)]
enrollment_map = {}
for course_id, inst_id, roll_no, enrollment_year in enrollments:
    key = (course_id, enrollment_year)
    if key not in enrollment_map:
        enrollment_map[key] = []
    enrollment_map[key].append((roll_no, inst_id))

# Function to assign grade based on total marks
def assign_grade(total):
    if total >= 90:
        return 'A'
    elif total >= 80:
        return 'B'
    elif total >= 70:
        return 'C'
    elif total >= 60:
        return 'D'
    else:
        return 'F'

# Generate marks tables year by year
for course_id, semester, course_year, dept in courses:
    for academic_year in range(2020, 2025):
        # Skip if course didn’t exist yet (e.g., 2024 students in 1st year can't have 4th-year courses)
        if academic_year - course_year < 2019:  # ensures valid mapping
            continue

        # Build table name
        table_name = f"marks_{course_id}_{academic_year}_{semester}"

        # Drop and recreate table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                roll_no TEXT NOT NULL,
                institute_id TEXT NOT NULL,
                internal_marks INTEGER CHECK(internal_marks >= 0 AND internal_marks <= 30),
                external_marks INTEGER CHECK(external_marks >= 0 AND external_marks <= 70),
                grade TEXT CHECK(grade IN ('A', 'B', 'C', 'D', 'F')),
                FOREIGN KEY (roll_no) REFERENCES students(roll_no)
            )
        """)

        # Get enrolled students (only those registered in this specific academic_year)
        enrolled = enrollment_map.get((course_id, academic_year), [])
        if not enrolled:
            continue

        # Generate marks records
        records = []
        for roll_no, inst_id in enrolled:
            internal_float = random.triangular(0, 30, 25)
            external_float = random.triangular(0, 70, 50)

            # triangular() returns a float, so just round it to get an integer
            internal = int(round(internal_float))
            external = int(round(external_float))
            total = internal + external
            grade = assign_grade(total)
            records.append((roll_no, inst_id, internal, external, grade))

        # Insert into table
        cursor.executemany(
            f"INSERT INTO {table_name} (roll_no, institute_id, internal_marks, external_marks, grade) VALUES (?, ?, ?, ?, ?)", 
            records
        )

        total_tables += 1
        total_records += len(records)
        print(f"✅ Created {table_name} with {len(records)} records.")

conn.commit()
conn.close()

print(f"\n🎯 Done! Generated {total_tables} marks tables with {total_records} total records.")