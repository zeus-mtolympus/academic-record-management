import sqlite3
import random

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

total_records = 0

# Fetch all course details including credits (assuming 'credits' column exists in courses table)
cursor.execute("SELECT course_id, semester, year, department_id, credits FROM courses")
courses = cursor.fetchall()

# Function to map grade to grade point
def grade_to_point(grade):
    mapping = {'A': 10, 'B': 9, 'C': 8, 'D': 7, 'F': 0}
    return mapping.get(grade, 0)

# Drop and create the unified sgpa_report table
cursor.execute("DROP TABLE IF EXISTS sgpa_report")
cursor.execute("""
    CREATE TABLE sgpa_report (
        year INTEGER NOT NULL,
        semester TEXT NOT NULL,
        institute_id TEXT NOT NULL,
        roll_no TEXT NOT NULL,
        sgpa REAL,
        credits INTEGER NOT NULL,
        FOREIGN KEY (roll_no) REFERENCES students(roll_no)
    )
""")

# Generate SGPA reports year by year and semester by semester
for academic_year in range(2020, 2025):
    for semester in ["Odd", "Even"]:
        # Find relevant courses for this semester
        relevant_courses = [course for course in courses if course[1] == semester]
        
        # Dictionary to accumulate weighted grades per student
        student_grades = {}  # key: (institute_id, roll_no) -> {'total_weighted': 0, 'total_credits': 0}
        
        for course in relevant_courses:
            course_id, _, _, _, credits = course
            table_name = f"marks_{course_id}_{academic_year}_{semester}"
            
            try:
                cursor.execute(f"SELECT roll_no, institute_id, grade FROM {table_name}")
                rows = cursor.fetchall()
                for roll_no, inst_id, grade in rows:
                    key = (inst_id, roll_no)
                    if key not in student_grades:
                        student_grades[key] = {'total_weighted': 0, 'total_credits': 0}
                    
                    # Skip if grade is 'F' (backlog, do not count credits)
                    if grade != 'F':
                        gp = grade_to_point(grade)
                        weighted = gp * credits
                        student_grades[key]['total_weighted'] += weighted
                        student_grades[key]['total_credits'] += credits
            except sqlite3.OperationalError:
                # Table doesn't exist for this course/year/semester, skip
                continue
        
        # Compute SGPA for each student and prepare records
        records = []
        for (inst_id, roll_no), data in student_grades.items():
            if data['total_credits'] > 0:
                sgpa = round(data['total_weighted'] / data['total_credits'], 2)
            else:
                sgpa = None
            records.append((academic_year, semester, inst_id, roll_no, sgpa, data['total_credits']))
        
        # Insert records
        if records:
            cursor.executemany(
                "INSERT INTO sgpa_report (year, semester, institute_id, roll_no, sgpa, credits) VALUES (?, ?, ?, ?, ?, ?)",
                records
            )
            total_records += len(records)
            print(f"✅ Added {len(records)} SGPA records for {academic_year} {semester}.")

conn.commit()
conn.close()

print(f"\n🎯 Done! Generated sgpa_report table with {total_records} total records.")