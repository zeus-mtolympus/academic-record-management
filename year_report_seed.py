import sqlite3

# Connect to your database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

total_records = 0
total_tables = 0

# Fetch all course details including credits (assuming 'credits' column exists in courses table)
cursor.execute("SELECT course_id, semester, year, department_id, credits FROM courses")
courses = cursor.fetchall()

# Fetch student admission years from students table
cursor.execute("SELECT institute_id, roll_no, batch FROM students")
student_years = cursor.fetchall()

# Build admission map: (institute_id, roll_no) -> admission_year
admission_map = {(inst_id, roll_no): year for inst_id, roll_no, year in student_years}

# Generate report tables year by year and semester by semester
for academic_year in range(2020, 2025):
    for semester in ["Odd", "Even"]:
        # Build table name
        table_name = f"{semester}_{academic_year}_report"

        # Drop and recreate table
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"""
            CREATE TABLE {table_name} (
                year INTEGER NOT NULL,
                semester TEXT NOT NULL,
                semester_number INTEGER NOT NULL,
                institute_id TEXT NOT NULL,
                roll_no TEXT NOT NULL,
                course_id TEXT NOT NULL,
                grade TEXT,
                total_marks INTEGER,
                status TEXT,
                credits_earned INTEGER,
                FOREIGN KEY (roll_no) REFERENCES students(roll_no)
            )
        """)

        # Find relevant courses for this semester
        relevant_courses = [course for course in courses if course[1] == semester]

        # Collect records
        records = []
        for course in relevant_courses:
            course_id, _, _, _, credits = course
            marks_table = f"marks_{course_id}_{academic_year}_{semester}"

            try:
                cursor.execute(f"""
                    SELECT roll_no, institute_id, internal_marks, external_marks, grade 
                    FROM {marks_table}
                """)
                rows = cursor.fetchall()
                for roll_no, inst_id, internal, external, grade in rows:
                    key = (inst_id, roll_no)
                    admit_year = admission_map.get(key, academic_year)  # fallback to current if not found
                    year_diff = academic_year - admit_year
                    semester_number = (year_diff * 2) + (1 if semester == "Odd" else 2)
                    
                    total_marks = internal + external
                    status = "Pass" if grade != 'F' else "Fail"
                    credits_earned = credits if status == "Pass" else 0
                    
                    records.append((
                        academic_year, semester, semester_number, inst_id, roll_no, 
                        course_id, grade, total_marks, status, credits_earned
                    ))
            except sqlite3.OperationalError:
                # Table doesn't exist, skip
                continue

        # Insert records
        if records:
            cursor.executemany(
                f"INSERT INTO {table_name} (year, semester, semester_number, institute_id, roll_no, course_id, grade, total_marks, status, credits_earned) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                records
            )
            total_tables += 1
            total_records += len(records)
            print(f"✅ Created {table_name} with {len(records)} records.")

conn.commit()
conn.close()

print(f"\n🎯 Done! Generated {total_tables} report tables with {total_records} total records.")