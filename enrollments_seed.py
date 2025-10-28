import sqlite3
import random

# Connect to existing DB
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON;")

# Drop and recreate enrollments table cleanly
cursor.execute("DROP TABLE IF EXISTS enrollments;")
cursor.execute("""
CREATE TABLE enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    institute_id TEXT NOT NULL,
    semester TEXT CHECK(semester IN ('Odd', 'Even')),
    year INTEGER NOT NULL,
    status TEXT CHECK(status IN ('Enrolled', 'Completed', 'Backlog')) DEFAULT 'Enrolled',
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (institute_id) REFERENCES students(institute_id)
)
""")

# Fetch required data
cursor.execute("SELECT institute_id, department_id, batch FROM students")
students = cursor.fetchall()

cursor.execute("SELECT course_id, department_id, year, semester FROM courses")
courses = cursor.fetchall()

current_year = 2024
enrollments = []

for institute_id, dept_id, batch in students:
    for course_id, course_dept, course_year, semester in courses:
        if course_dept == dept_id:
            course_academic_year = batch + course_year - 1

            if course_academic_year > current_year:
                # Student hasn't reached this course yet
                continue

            elif course_academic_year < current_year:
                # Course from past year - completed or backlog
                status = random.choices(["Completed", "Backlog"], weights=[0.85, 0.15])[0]
            else:
                # Current year's courses
                status = "Enrolled"

            enrollments.append((course_id, institute_id, semester, course_academic_year, status))

# Bulk insert
cursor.executemany("""
INSERT INTO enrollments (course_id, institute_id, semester, year, status)
VALUES (?, ?, ?, ?, ?)
""", enrollments)

conn.commit()
print(f"✅ Successfully inserted {len(enrollments)} enrollment records.")
conn.close()
