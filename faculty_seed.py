import sqlite3
import random
from faker import Faker

fake = Faker("en_IN")
Faker.seed(1)

# Connect to SQLite database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Drop old table if exists
cursor.execute("DROP TABLE IF EXISTS faculty")

# Create simplified faculty table
cursor.execute("""
CREATE TABLE faculty (
    faculty_no INTEGER PRIMARY KEY AUTOINCREMENT,
    institute_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    dob DATE,
    gender TEXT,
    department_id TEXT,
    joining_year INTEGER,
    leaving_year INTEGER,
    status TEXT,
    personal_email TEXT,
    college_email TEXT,
    phone TEXT,
    house_no TEXT,
    lane TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    pincode TEXT,
    FOREIGN KEY(department_id) REFERENCES departments(department_id)
);
""")

# --- Helper Data ---
branches = ["CSE", "ECE", "EEE"]
statuses = ["Active", "Retired", "On Leave"]

# --- Insert Dummy Data ---
faculty_count = 0
for dept in branches:
    for i in range(10):  # 10 faculty per branch
        faculty_count += 1
        fname = fake.first_name()
        lname = fake.last_name()
        gender = random.choice(["Male", "Female"])
        dob = fake.date_of_birth(minimum_age=28, maximum_age=60).strftime("%Y-%m-%d")
        joining_year = random.randint(2005, 2022)
        leaving_year = None if random.random() < 0.7 else random.randint(joining_year + 3, 2025)
        status = "Active" if leaving_year is None else random.choice(statuses)
        house_no = str(random.randint(1, 500))
        lane = fake.street_name()
        city = fake.city()
        state = fake.state()
        country = "India"
        pincode = fake.postcode()
        institute_id = f"ID{joining_year}{dept}{i+1:03d}"

        # Emails & phone
        personal_email = fake.email()
        college_email = f"{institute_id.lower()}_{fname.lower()}@college.ac.in"
        phone = fake.phone_number()

        # Insert faculty record
        cursor.execute("""
            INSERT INTO faculty (
                institute_id, first_name, last_name, dob, gender, department_id,
                joining_year, leaving_year, status,
                personal_email, college_email, phone,
                house_no, lane, city, state, country, pincode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            institute_id, fname, lname, dob, gender, dept,
            joining_year, leaving_year, status,
            personal_email, college_email, phone,
            house_no, lane, city, state, country, pincode
        ))

conn.commit()
conn.close()

print(f"Faculty database created successfully with {faculty_count} faculty members!")
