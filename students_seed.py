import sqlite3
import random
from faker import Faker

fake = Faker("en_IN")
Faker.seed(0)

# Connect to SQLite database
conn = sqlite3.connect("college.db")
cursor = conn.cursor()

# Drop old tables
cursor.execute("DROP TABLE IF EXISTS student_guardian")
cursor.execute("DROP TABLE IF EXISTS students")

# Create simplified tables
cursor.execute("""
CREATE TABLE students (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    institute_id TEXT UNIQUE,
    fname TEXT,
    lname TEXT,
    roll_no TEXT UNIQUE,
    dob DATE,
    gender TEXT,
    department_id TEXT,
    batch INTEGER,
    cgpa REAL,
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

cursor.execute("""
CREATE TABLE student_guardian (
    guardian_id INTEGER PRIMARY KEY AUTOINCREMENT,
    institute_id TEXT,
    name TEXT,
    gender TEXT,
    relation TEXT,
    occupation TEXT,
    email TEXT,
    phone TEXT,
    house_no TEXT,
    lane TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    pincode TEXT,
    FOREIGN KEY(institute_id) REFERENCES students(institute_id)
);
""")

# --- Helper Data ---
branches = ["CSE", "ECE", "EEE"]

# --- Insert Dummy Data ---
student_count = 0
for batch in range(2020, 2025):
    for dept in branches:
        for i in range(30):
            student_count += 1
            institute_id = f"ID{batch}{student_count:03d}"
            fname = fake.first_name()
            lname = fake.last_name()
            gender = random.choice(["Male", "Female"])
            roll_no = f"{dept}{batch}{i+1:03d}"
            dob = fake.date_of_birth(minimum_age=18, maximum_age=23).strftime("%Y-%m-%d")
            cgpa = round(random.uniform(6.0, 9.8), 2)
            status = "Graduated" if batch == 2020 else "Studying"
            house_no = str(random.randint(1, 300))
            lane = fake.street_name()
            city = fake.city()
            state = fake.state()
            country = "India"
            pincode = fake.postcode()

            # Emails & phone
            personal_email = fake.email()
            college_email = f"{institute_id.lower()}_{fname.lower()}@college.ac.in"
            phone = fake.phone_number()

            # Insert student
            cursor.execute("""
                INSERT INTO students (
                    institute_id, fname, lname, roll_no, dob, gender,
                    department_id, batch, cgpa, status,
                    personal_email, college_email, phone,
                    house_no, lane, city, state, country, pincode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                institute_id, fname, lname, roll_no, dob, gender,
                dept, batch, cgpa, status,
                personal_email, college_email, phone,
                house_no, lane, city, state, country, pincode
            ))

            # Guardian info
            guardian_name = fake.name()
            guardian_gender = random.choice(["Male", "Female"])
            relation = random.choice(["Father", "Mother", "Brother", "Sister"])
            occupation = random.choice(["Teacher", "Engineer", "Doctor", "Business", "Farmer", "Clerk", "Police"])
            g_email = fake.email()
            g_phone = fake.phone_number()
            g_house_no = str(random.randint(1, 300))
            g_lane = fake.street_name()
            g_city = fake.city()
            g_state = fake.state()
            g_country = "India"
            g_pincode = fake.postcode()

            cursor.execute("""
                INSERT INTO student_guardian (
                    institute_id, name, gender, relation, occupation,
                    email, phone, house_no, lane, city, state, country, pincode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                institute_id, guardian_name, guardian_gender, relation, occupation,
                g_email, g_phone, g_house_no, g_lane, g_city, g_state, g_country, g_pincode
            ))

conn.commit()
conn.close()

print(f"Database created successfully with {student_count} students!")
