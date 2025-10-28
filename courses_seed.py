import sqlite3
import random

# Connect to your existing database (students, faculty, etc.)
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Create courses table
cursor.execute("""
DROP TABLE IF EXISTS courses
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS courses (
    course_id TEXT PRIMARY KEY,
    course_code TEXT NOT NULL,
    name TEXT NOT NULL,
    year INTEGER NOT NULL,
    semester TEXT CHECK(semester IN ('Odd', 'Even')),
    department_id TEXT NOT NULL,
    credits INTEGER NOT NULL,
    faculty_id TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(institute_id)
)
""")

# Department details
departments = {
    "CSE": "Computer Science and Engineering",
    "ECE": "Electronics and Communication Engineering",
    "EEE": "Electrical and Electronics Engineering"
}

# Example course names (you can customize)
course_names = {
    "CSE":[
    'Introduction to Programming',
    'Discrete Mathematics',
    'Calculus I',
    'Object-Oriented Programming',
    'Data Structures and Algorithms',
    'Computer Architecture & Organization',
    'Database Management Systems (DBMS)',
    'Software Engineering Principles',
    'Operating Systems',
    'Computer Networks',
    'Theory of Computation',
    'Web Development',
    'Artificial Intelligence',
    'Machine Learning',
    'Cybersecurity',
    'Computer Graphics'],
    "ECE":[
    # --- Year 1: Foundational Engineering ---
    'Engineering Mathematics I & II',
    'Basic Electrical Engineering',
    'Engineering Physics',
    'Programming for Problem Solving',
    
    # --- Year 2: Core Electronics ---
    'Analog Electronic Circuits',
    'Digital System Design',
    'Signals and Systems',
    'Network Theory',
    
    # --- Year 3: Communication & Systems ---
    'Microprocessors & Microcontrollers',
    'Analog and Digital Communication',
    'Control Systems',
    'VLSI Design',
    
    # --- Year 4: Specialization & Electives ---
    'Digital Signal Processing (DSP)',
    'Embedded Systems',
    'Wireless & Mobile Communication',
    'Robotics and Automation'
],
"EEE":[
    # --- Year 1: Foundational Engineering ---
    'Engineering Mathematics I & II',
    'Engineering Physics',
    'Basic Electrical Engineering',
    'Programming Fundamentals',
    
    # --- Year 2: Core Electrical & Electronics ---
    'Circuit Theory / Network Analysis',
    'Analog Electronic Circuits',
    'Digital Logic Design',
    'Electrical Machines I (DC Machines & Transformers)',
    
    # --- Year 3: Power Systems & Control ---
    'Electrical Machines II (AC Machines)',
    'Power Systems I (Generation & Transmission)',
    'Electromagnetic Fields',
    'Control Systems',
    
    # --- Year 4: Specialization & Electives ---
    'Power Electronics',
    'Power Systems II (Distribution & Protection)',
    'Digital Signal Processing (DSP)',
    'Renewable Energy Systems'
]}

# Fetch faculty IDs for each department
faculty_per_dept = {}
for dept in departments.keys():
    cursor.execute("SELECT institute_id FROM faculty WHERE department_id = ?", (dept,))
    faculty_ids = [f[0] for f in cursor.fetchall()]
    faculty_per_dept[dept] = faculty_ids

# Generate courses
courses = []
for dept in departments.keys():
    for i, name in enumerate(course_names[dept]):
        year = (i // 4) + 1  # 4 courses per year
        semester = "Odd" if i % 2 == 0 else "Even"
        course_code = f"{dept}{100 + i}"
        credits = random.randint(2, 5)
        faculty_id = random.choice(faculty_per_dept[dept])
        course_id = f"{course_code}_{year}_{semester}"

        courses.append((course_id, course_code, name, year, semester, dept, credits, faculty_id))

# Insert into table
cursor.executemany("""
INSERT INTO courses (course_id, course_code, name, year, semester, department_id, credits, faculty_id)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", courses)

conn.commit()
print(f"✅ Inserted {len(courses)} courses successfully!")
conn.close()
