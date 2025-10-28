import sqlite3
import random
from datetime import date, timedelta

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Helper: Generate all weekdays between two dates
def generate_weekdays(start_date, end_date):
    days = []
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday–Friday
            days.append(current)
        current += timedelta(days=1)
    return days

# Define months for semesters
SEMESTER_MONTHS = {
    "Odd":  (8, 9),  # August–September
    "Even": (1, 2)   # January–February
}

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

# Build mapping: (course_id, academic_year) → [roll_no]
# Only include students enrolled specifically in that academic_year for the course
enrollment_map = {}
for course_id, inst_id, roll_no, enrollment_year in enrollments:
    key = (course_id, enrollment_year)
    if key not in enrollment_map:
        enrollment_map[key] = []
    enrollment_map[key].append(roll_no)

# Generate attendance tables year by year
for course_id, semester, course_year, dept in courses:
    for academic_year in range(2020, 2025):
        # Skip if course didn’t exist yet (e.g., 2024 students in 1st year can't have 4th-year courses)
        if academic_year - course_year < 2019:  # ensures valid mapping
            continue

        # Build table name
        table_name = f"attendance_{course_id}_{academic_year}"

        # Drop and recreate table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                roll_no TEXT NOT NULL,
                date TEXT NOT NULL,
                status TEXT CHECK(status IN ('Present', 'Absent')),
                FOREIGN KEY (roll_no) REFERENCES students(roll_no)
            )
        """)

        # Determine date range for this semester/year
        start_month, end_month = SEMESTER_MONTHS[semester]
        start_date = date(academic_year, start_month, 1)
        end_date = date(academic_year, end_month, 28 if end_month == 2 else 30)
        class_days = generate_weekdays(start_date, end_date)

        # Get enrolled students (only those registered in this specific academic_year)
        students = enrollment_map.get((course_id, academic_year), [])
        if not students:
            continue

        # Generate attendance records
        records = []
        for roll_no in students:
            for day in class_days:
                status = "Absent" if random.random() < 0.1 else "Present"
                records.append((roll_no, str(day), status))

        # Insert into table
        cursor.executemany(
            f"INSERT INTO {table_name} (roll_no, date, status) VALUES (?, ?, ?)", 
            records
        )

        total_tables += 1
        total_records += len(records)
        print(f"✅ Created {table_name} with {len(records)} records.")

conn.commit()
conn.close()

print(f"\n🎯 Done! Generated {total_tables} attendance tables with {total_records} total records.")