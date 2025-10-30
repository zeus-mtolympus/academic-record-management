"""
generate_users_db.py

Creates users.db with:
 - username (institute_id)
 - password (bcrypt-hashed of institute_id + "1234!")
 - type ("Student" / "Faculty" / "Admin")

Reads data from:
 - college_students.db (table: students with 'institute_id')
 - faculty.db (table: faculty with 'institute_id')

Always adds one Admin user manually:
 - username: "ADMIN01"
 - password: "ADMIN011234!"
"""
import sqlite3
import bcrypt
import os

USERS_DB = "users.db"
STUDENTS_DB = "college.db"
FACULTY_DB = "college.db"

def hash_password(plaintext: str) -> str:
    """Return bcrypt hash as utf-8 string."""
    hashed = bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def create_users_table(conn):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS users;")
    cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            type TEXT NOT NULL
        );
    """)
    conn.commit()

def add_user(conn, username, hashed_password, utype):
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password, type) VALUES (?, ?, ?)",
                    (username, hashed_password, utype))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"[WARN] username '{username}' already exists — skipped")

def seed_from_students(conn_users):
    if not os.path.exists(STUDENTS_DB):
        print(f"[INFO] {STUDENTS_DB} not found — skipping student import.")
        return 0
    s_conn = sqlite3.connect(STUDENTS_DB)
    s_cur = s_conn.cursor()

    try:
        s_cur.execute("SELECT institute_id FROM students;")
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Failed reading students table: {e}")
        s_conn.close()
        return 0

    rows = s_cur.fetchall()
    count = 0
    for (institute_id,) in rows:
        if not institute_id:
            continue
        plain = f"{institute_id}1234!"
        hashed = hash_password(plain)
        add_user(conn_users, institute_id, hashed, "Student")
        count += 1
    s_conn.close()
    print(f"[INFO] Seeded {count} students into users.db")
    return count

def seed_from_faculty(conn_users):
    if not os.path.exists(FACULTY_DB):
        print(f"[INFO] {FACULTY_DB} not found — skipping faculty import.")
        return 0
    f_conn = sqlite3.connect(FACULTY_DB)
    f_cur = f_conn.cursor()

    try:
        f_cur.execute("SELECT institute_id FROM faculty;")
    except sqlite3.OperationalError as e:
        print(f"[ERROR] Failed reading faculty table: {e}")
        f_conn.close()
        return 0

    rows = f_cur.fetchall()
    count = 0
    for (institute_id,) in rows:
        if not institute_id:
            continue
        plain = f"{institute_id}1234!"
        hashed = hash_password(plain)
        add_user(conn_users, institute_id, hashed, "Faculty")
        count += 1
    f_conn.close()
    print(f"[INFO] Seeded {count} faculty into users.db")
    return count

def seed_admin(conn_users):
    usernames = ["ADMIN01", "DUMBLEDORE"]
    plains = [f"{username}1234!" for username in usernames]
    for username, plain in zip(usernames, plains):
        hashed = hash_password(plain)
        add_user(conn_users, username, hashed, "Admin")
        print(f"[INFO] Admin user added — username: {username}, password: {plain}")

def main():
    if os.path.exists(USERS_DB):
        print(f"[WARN] {USERS_DB} already exists and will be replaced.")
        os.remove(USERS_DB)

    conn_users = sqlite3.connect(USERS_DB)
    create_users_table(conn_users)

    # Seed admin, faculty, students
    seed_admin(conn_users)
    fcount = seed_from_faculty(conn_users)
    scount = seed_from_students(conn_users)

    total = 1 + fcount + scount
    print(f"[DONE] users.db created successfully with {total} users.")
    conn_users.close()

if __name__ == "__main__":
    main()
