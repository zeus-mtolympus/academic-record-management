from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import bcrypt
import io
import csv
from datetime import datetime
import pandas as pd
from io import BytesIO
import csv

app = Flask(__name__)
app.secret_key = "supersecretkey"  # In production, use os.urandom(24) or env var

USERS_DB = "users.db"
COLLEGE_DB = "college.db"

def get_users_connection():
    """Connection for users.db (authentication and user management)."""
    conn = sqlite3.connect(USERS_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_college_connection():
    """Connection for college.db (academic data)."""
    conn = sqlite3.connect(COLLEGE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(username):
    """Fetch user record by username from users.db."""
    conn = get_users_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, password, type FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return user

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        user = get_user(username)
        if user:
            stored_password = user['password'].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), stored_password):
                session["username"] = user['username']
                session["type"] = user['type']
                flash(f"Welcome back, {user['username']} ({user['type']})!", "success")

                # Redirect based on user type
                if user['type'] == "Admin":
                    return redirect(url_for("admin_dashboard"))
                elif user['type'] == "Faculty":
                    return redirect(url_for("faculty_dashboard"))
                else:  # Assuming "Student"
                    return redirect(url_for("student_dashboard"))
            else:
                flash("Invalid password. Please try again.", "danger")
        else:
            flash("User not found. Please check your username.", "danger")

    return render_template("login.html")

@app.route("/admin")
def admin_dashboard():
    if "username" not in session or session["type"] != "Admin":
        flash("Unauthorized access! Please log in as an admin.", "danger")
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html", username=session["username"])

# Updated manage_users route - replace existing (add admin handling and fetch/display)
@app.route("/admin/users", methods=["GET", "POST"])
def manage_users():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    users_conn = get_users_connection()
    college_conn = get_college_connection()
    
    action = request.form.get("action") if request.method == "POST" else None
    user_type = request.form.get("user_type") if request.method == "POST" else None
    
    if request.method == "POST" and action:
        if action == "add":
            if user_type == "student":
                return redirect(url_for("add_student"))
            elif user_type == "faculty":
                return redirect(url_for("add_faculty"))
            elif user_type == "admin":
                return redirect(url_for("add_admin"))
        elif action == "update":
            if user_type == "student":
                return redirect(url_for("update_student_search"))
            elif user_type == "faculty":
                return redirect(url_for("update_faculty_search"))
    
    # Fetch admins from users.db
    cur_users = users_conn.cursor()
    cur_users.execute("SELECT username FROM users WHERE type = 'Admin'")
    admin_usernames = cur_users.fetchall()
    admins_list = [{'username': user['username']} for user in admin_usernames]
    
    # Fetch students (unchanged)
    cur_users.execute("SELECT username FROM users WHERE type = 'Student'")
    student_institutes = cur_users.fetchall()
    
    cur_college = college_conn.cursor()
    students = cur_college.execute("""
        SELECT institute_id, roll_no, fname, lname, batch, cgpa, status, personal_email 
        FROM students
    """).fetchall()
    
    student_dict = {}
    for student in students:
        full_name = f"{student['fname']} {student['lname']}"
        student_dict[student['institute_id']] = {'roll_no': student['roll_no'], 'name': full_name, 'batch': student['batch'], 'cgpa': student['cgpa'], 'status': student['status'], 'email': student['personal_email']}
    
    students_list = []
    for user in student_institutes:
        institute_id = user['username']
        details = student_dict.get(institute_id, {'roll_no': 'N/A', 'name': 'N/A', 'batch': 'N/A', 'cgpa': 'N/A', 'status': 'N/A', 'email': 'N/A'})
        students_list.append({'institute_id': institute_id, 'roll_no': details['roll_no'], 'name': details['name'], 'batch': details['batch'], 'cgpa': details['cgpa'], 'status': details['status'], 'email': details['email']})
    
    # Fetch faculty (unchanged)
    cur_users.execute("SELECT username FROM users WHERE type = 'Faculty'")
    faculty_institutes = cur_users.fetchall()
    
    faculty_members = cur_college.execute("SELECT institute_id, fname, lname, status FROM faculty").fetchall()
    
    faculty_dict = {}
    for fac in faculty_members:
        full_name = f"{fac['fname']} {fac['lname']}"
        faculty_dict[fac['institute_id']] = full_name
    
    faculty_list = []
    for user in faculty_institutes:
        institute_id = user['username']
        fac_member = next((f for f in faculty_members if f['institute_id'] == institute_id), None)
        name = faculty_dict.get(institute_id, 'N/A')
        status = fac_member['status'] if fac_member else 'N/A'
        faculty_list.append({'institute_id': institute_id, 'name': name, 'status': status})
    
    users_conn.close()
    college_conn.close()
    
    return render_template("admin_users.html", admins=admins_list, students=students_list, faculty=faculty_list)

# New route for adding admin - add this
@app.route("/admin/add_admin", methods=["GET", "POST"])
def add_admin():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    users_conn = get_users_connection()
    
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        
        if not all([username, password]):
            flash("Missing required fields for Admin.", "danger")
        else:
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            
            try:
                cur = users_conn.cursor()
                cur.execute("INSERT INTO users (username, password, type) VALUES (?, ?, ?)",
                            (username, hashed.decode("utf-8"), "Admin"))
                users_conn.commit()
                flash(f"Admin added successfully! Username: {username}", "success")
                return redirect(url_for("manage_users"))
            except sqlite3.IntegrityError:
                flash("Username already exists.", "danger")
        
        users_conn.close()
    
    return render_template("add_admin.html")

# Updated add_student route - replace existing (add new fields: personal_email, college_email, phone)
@app.route("/admin/add_student", methods=["GET", "POST"])
def add_student():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    users_conn = get_users_connection()
    
    departments = []
    if request.method == "GET":
        cur = college_conn.cursor()
        cur.execute("SELECT department_id, department_name FROM departments")  # Adjust 'name' if needed
        departments = cur.fetchall()
    
    if request.method == "POST":
        institute_id = request.form["institute_id"].strip()
        roll_no = request.form["roll_no"].strip()
        password = institute_id + "1234!"
        fname = request.form["fname"].strip()
        lname = request.form["lname"].strip()
        dob_str = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        department_id = request.form.get("department_id", "").strip()
        batch = request.form.get("batch", "").strip()
        status = request.form.get("status", "Active").strip()
        personal_email = request.form.get("personal_email", "").strip()
        college_email = request.form.get("college_email", "").strip()
        phone = request.form.get("phone", "").strip()
        house_no = request.form.get("house_no", "").strip()
        lane = request.form.get("lane", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        country = request.form.get("country", "").strip()
        pincode = request.form.get("pincode", "").strip()
        
        if not all([institute_id, roll_no, fname, lname, dob_str, gender, department_id, batch]):
            flash("Missing required fields for Student.", "danger")
        else:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid DOB format. Use YYYY-MM-DD.", "danger")
            else:
                hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
                
                cur_users = users_conn.cursor()
                cur_users.execute("INSERT INTO users (username, password, type) VALUES (?, ?, ?)",
                                  (institute_id, hashed.decode("utf-8"), "Student"))
                
                cur_college = college_conn.cursor()
                cur_college.execute("""
                    INSERT INTO students (institute_id, fname, lname, roll_no, dob, gender, department_id, batch, cgpa, status, 
                                          personal_email, college_email, phone, house_no, lane, city, state, country, pincode) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (institute_id, fname, lname, roll_no, dob, gender, department_id, batch, status, 
                      personal_email, college_email, phone, house_no, lane, city, state, country, pincode))
                
                users_conn.commit()
                college_conn.commit()
                flash(f"Student added successfully! Institute ID: {institute_id}, Roll No: {roll_no}, Password: {password}", "success")
                return redirect(url_for("manage_users"))
        
        college_conn.close()
        users_conn.close()
    
    college_conn.close()
    return render_template("add_student.html", departments=departments)

# Updated add_faculty route - replace existing (remove faculty_no)
@app.route("/admin/add_faculty", methods=["GET", "POST"])
def add_faculty():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    users_conn = get_users_connection()
    
    departments = []
    if request.method == "GET":
        cur = college_conn.cursor()
        cur.execute("SELECT department_id, department_name FROM departments")  # Adjust 'name' if needed
        departments = cur.fetchall()
    
    if request.method == "POST":
        institute_id = request.form["institute_id"].strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        dob_str = request.form.get("dob", "").strip()
        gender = request.form.get("gender", "").strip()
        department_id = request.form.get("department_id", "").strip()
        joining_year = request.form.get("joining_year", "").strip()
        leaving_year = request.form.get("leaving_year", "").strip()
        status = request.form.get("status", "Active").strip()
        personal_email = request.form.get("personal_email", "").strip()
        college_email = request.form.get("college_email", "").strip()
        phone = request.form.get("phone", "").strip()
        house_no = request.form.get("house_no", "").strip()
        lane = request.form.get("lane", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        country = request.form.get("country", "").strip()
        pincode = request.form.get("pincode", "").strip()
        
        if not all([institute_id, first_name, last_name, dob_str, gender, department_id, joining_year]):
            flash("Missing required fields for Faculty.", "danger")
        else:
            try:
                dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid DOB format. Use YYYY-MM-DD.", "danger")
            else:
                password = institute_id + "1234!"
                hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
                
                cur_users = users_conn.cursor()
                cur_users.execute("INSERT INTO users (username, password, type) VALUES (?, ?, ?)",
                                  (institute_id, hashed.decode("utf-8"), "Faculty"))
                
                cur_college = college_conn.cursor()
                cur_college.execute("""
                    INSERT INTO faculty (institute_id, first_name, last_name, dob, gender, department_id, 
                                         joining_year, leaving_year, status, personal_email, college_email, phone, 
                                         house_no, lane, city, state, country, pincode) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (institute_id, first_name, last_name, dob, gender, department_id, 
                      joining_year, leaving_year, status, personal_email, college_email, phone, 
                      house_no, lane, city, state, country, pincode))
                
                users_conn.commit()
                college_conn.commit()
                flash(f"Faculty added successfully! Institute ID: {institute_id}, Password: {password}", "success")
                return redirect(url_for("manage_users"))
        
        college_conn.close()
        users_conn.close()
    
    college_conn.close()
    return render_template("add_faculty.html", departments=departments)

# Updated update_faculty_search and update_faculty - replace existing (full new schema)
@app.route("/admin/update_faculty_search", methods=["GET", "POST"])
def update_faculty_search():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    departments = []
    faculty = None
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("SELECT department_id, department_name FROM departments")  # Adjust 'name' if needed
    departments = cur.fetchall()
    
    if request.method == "POST":
        institute_id = request.form["institute_id"].strip()
        faculty = cur.execute("SELECT * FROM faculty WHERE institute_id = ?", (institute_id,)).fetchone()
        
        if faculty:
            college_conn.close()
            return render_template("update_faculty.html", faculty=faculty, departments=departments)
        else:
            flash("Faculty not found.", "danger")
    
    college_conn.close()
    return render_template("update_faculty_search.html")

# Updated update_faculty POST route - replace existing (remove faculty_no)
@app.route("/admin/update_faculty", methods=["POST"])
def update_faculty():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    institute_id = request.form["institute_id"].strip()
    first_name = request.form["first_name"].strip()
    last_name = request.form["last_name"].strip()
    dob_str = request.form.get("dob", "").strip()
    gender = request.form.get("gender", "").strip()
    department_id = request.form.get("department_id", "").strip()
    joining_year = request.form.get("joining_year", "").strip()
    leaving_year = request.form.get("leaving_year", "").strip()
    status = request.form.get("status", "").strip()
    personal_email = request.form.get("personal_email", "").strip()
    college_email = request.form.get("college_email", "").strip()
    phone = request.form.get("phone", "").strip()
    house_no = request.form.get("house_no", "").strip()
    lane = request.form.get("lane", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    country = request.form.get("country", "").strip()
    pincode = request.form.get("pincode", "").strip()
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    # Update all fields (removed faculty_no)
    cur.execute("""
        UPDATE faculty SET first_name = ?, last_name = ?, gender = ?, department_id = ?, 
        joining_year = ?, leaving_year = ?, status = ?, personal_email = ?, college_email = ?, phone = ?, 
        house_no = ?, lane = ?, city = ?, state = ?, country = ?, pincode = ? WHERE institute_id = ?
    """, (first_name, last_name, gender, department_id, joining_year, leaving_year, status, 
          personal_email, college_email, phone, house_no, lane, city, state, country, pincode, institute_id))
    
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            cur.execute("UPDATE faculty SET dob = ? WHERE institute_id = ?", (dob, institute_id))
        except ValueError:
            flash("Invalid DOB format. Use YYYY-MM-DD.", "danger")
    
    college_conn.commit()
    college_conn.close()
    flash("Faculty updated successfully!", "success")
    return redirect(url_for("manage_users"))

# Updated update_student_search and update_student - replace existing (add new fields)
@app.route("/admin/update_student_search", methods=["GET", "POST"])
def update_student_search():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    departments = []
    student = None
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("SELECT department_id, department_name FROM departments")  # Adjust 'name' if needed
    departments = cur.fetchall()
    
    if request.method == "POST":
        institute_id = request.form["institute_id"].strip()
        student = cur.execute("SELECT * FROM students WHERE institute_id = ?", (institute_id,)).fetchone()
        
        if student:
            college_conn.close()
            return render_template("update_student.html", student=student, departments=departments)
        else:
            flash("Student not found.", "danger")
    
    college_conn.close()
    return render_template("update_student_search.html")

@app.route("/admin/update_student", methods=["POST"])
def update_student():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    institute_id = request.form["institute_id"].strip()
    fname = request.form["fname"].strip()
    lname = request.form["lname"].strip()
    roll_no = request.form["roll_no"].strip()
    dob_str = request.form.get("dob", "").strip()
    gender = request.form.get("gender", "").strip()
    department_id = request.form.get("department_id", "").strip()
    batch = request.form.get("batch", "").strip()
    status = request.form.get("status", "").strip()
    personal_email = request.form.get("personal_email", "").strip()
    college_email = request.form.get("college_email", "").strip()
    phone = request.form.get("phone", "").strip()
    house_no = request.form.get("house_no", "").strip()
    lane = request.form.get("lane", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    country = request.form.get("country", "").strip()
    pincode = request.form.get("pincode", "").strip()
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    # Update all fields including new ones
    cur.execute("""
        UPDATE students SET fname = ?, lname = ?, roll_no = ?, gender = ?, department_id = ?, batch = ?, status = ?,
        personal_email = ?, college_email = ?, phone = ?, house_no = ?, lane = ?, city = ?, state = ?, country = ?, pincode = ? 
        WHERE institute_id = ?
    """, (fname, lname, roll_no, gender, department_id, batch, status, personal_email, college_email, phone, 
          house_no, lane, city, state, country, pincode, institute_id))
    
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            cur.execute("UPDATE students SET dob = ? WHERE institute_id = ?", (dob, institute_id))
        except ValueError:
            flash("Invalid DOB format. Use YYYY-MM-DD.", "danger")
    
    college_conn.commit()
    college_conn.close()
    flash("Student updated successfully!", "success")
    return redirect(url_for("manage_users"))

# Updated manage_courses route - replace existing (no change needed for delete, but included for completeness)
@app.route("/admin/courses", methods=["GET", "POST"])
def manage_courses():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    
    action = request.form.get("action") if request.method == "POST" else None
    
    if request.method == "POST" and action:
        if action == "add":
            return redirect(url_for("add_course"))
        elif action == "update":
            return redirect(url_for("update_course_search"))
        elif action == "delete":
            return redirect(url_for("delete_course_search"))
    
    # Fetch courses for display
    cur = college_conn.cursor()
    cur.execute("""
        SELECT c.course_id, c.name, c.semester, c.year, c.department_id, c.credits, c.faculty_id,
               d.department_name as dept_name, f.fname || ' ' || f.lname as faculty_name
        FROM courses c
        LEFT JOIN departments d ON c.department_id = d.department_id
        LEFT JOIN faculty f ON c.faculty_id = f.institute_id
    """)
    courses = cur.fetchall()
    
    college_conn.close()
    
    return render_template("admin_courses.html", courses=courses)

# New route for searching/deleting course - add this
@app.route("/admin/delete_course_search", methods=["GET", "POST"])
def delete_course_search():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        course_id = request.form["course_id"].strip()
        college_conn = get_college_connection()
        cur = college_conn.cursor()
        course = cur.execute("SELECT course_id, name FROM courses WHERE course_id = ?", (course_id,)).fetchone()
        college_conn.close()
        
        if course:
            return render_template("delete_course.html", course=course)
        else:
            flash("Course not found.", "danger")
    
    return render_template("delete_course_search.html")

# New route for deleting course - add this
@app.route("/admin/delete_course", methods=["POST"])
def delete_course():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    course_id = request.form["course_id"].strip()
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    college_conn.commit()
    college_conn.close()
    flash(f"Course {course_id} deleted successfully!", "success")
    return redirect(url_for("manage_courses"))

# New route for adding course - add this
@app.route("/admin/add_course", methods=["GET", "POST"])
def add_course():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    
    departments = []
    faculty = []
    if request.method == "GET":
        cur = college_conn.cursor()
        cur.execute("SELECT department_id, department_name FROM departments")
        departments = cur.fetchall()
        cur.execute("SELECT institute_id as faculty_id, fname || ' ' || lname as name FROM faculty")
        faculty = cur.fetchall()
    
    if request.method == "POST":
        course_id = request.form["course_id"].strip()
        name = request.form["name"].strip()
        semester = request.form["semester"].strip()
        year = int(request.form["year"])
        department_id = request.form["department_id"].strip()
        credits = int(request.form.get("credits", 3))
        faculty_id = request.form.get("faculty_id", "").strip() or None
        
        if not all([course_id, name, semester, department_id]):
            flash("Missing required fields.", "danger")
        else:
            try:
                cur = college_conn.cursor()
                cur.execute("""
                    INSERT INTO courses (course_id, name, semester, year, department_id, credits, faculty_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (course_id, name, semester, year, department_id, credits, faculty_id))
                college_conn.commit()
                flash(f"Course {course_id} ({name}) added successfully!", "success")
                return redirect(url_for("manage_courses"))
            except sqlite3.IntegrityError:
                flash("Course ID already exists.", "danger")
        
        college_conn.close()
        return render_template("add_course.html", departments=departments, faculty=faculty)
    
    college_conn.close()
    return render_template("add_course.html", departments=departments, faculty=faculty)

@app.route("/admin/update_course_search", methods=["GET", "POST"])
def update_course_search():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    course_id = request.args.get("course_id") if request.method == "GET" else request.form.get("course_id")
    
    if course_id:
        college_conn = get_college_connection()
        cur = college_conn.cursor()
        course = cur.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
        
        # Fetch related data for form
        cur.execute("SELECT department_id, name FROM departments")
        departments = cur.fetchall()
        cur.execute("SELECT institute_id as faculty_id, first_name || ' ' || last_name as name FROM faculty")
        faculty = cur.fetchall()
        
        college_conn.close()
        
        if course:
            return render_template("update_course.html", course=course, departments=departments, faculty=faculty)
        else:
            flash("Course not found.", "danger")
    
    return render_template("update_course_search.html")

# New route for updating course - add this
@app.route("/admin/update_course", methods=["POST"])
def update_course():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    course_id = request.form["course_id"].strip()
    name = request.form["name"].strip()
    semester = request.form["semester"].strip()
    year = int(request.form["year"])
    department_id = request.form["department_id"].strip()
    credits = int(request.form.get("credits", 3))
    faculty_id = request.form.get("faculty_id", "").strip() or None
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        UPDATE courses SET name = ?, semester = ?, year = ?, department_id = ?, credits = ?, faculty_id = ? 
        WHERE course_id = ?
    """, (name, semester, year, department_id, credits, faculty_id, course_id))
    college_conn.commit()
    college_conn.close()
    flash(f"Course {course_id} ({name}) updated successfully!", "success")
    return redirect(url_for("manage_courses"))

# Updated manage_enrollments route - replace existing
@app.route("/admin/enroll", methods=["GET", "POST"])
def manage_enrollments():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    
    action = request.form.get("action") if request.method == "POST" else None
    
    if request.method == "POST" and action:
        if action == "add":
            return redirect(url_for("add_enrollment"))
        elif action == "delete":
            return redirect(url_for("delete_enrollment_search"))
    
    # Fetch sample data for potential list (students and courses)
    cur = college_conn.cursor()
    cur.execute("SELECT institute_id, roll_no, fname || ' ' || lname AS name FROM students")
    students = cur.fetchall()
    
    cur.execute("SELECT course_id, name FROM courses")
    courses_list = cur.fetchall()
    
    # Fetch enrollments for list (adjusted for institute_id only)
    cur.execute("""
        SELECT e.course_id, e.institute_id, e.semester, e.year, e.status,
               s.roll_no, s.fname || ' ' || s.lname AS student_name,
               c.name AS course_name
        FROM enrollments e
        LEFT JOIN students s ON e.institute_id = s.institute_id
        LEFT JOIN courses c ON e.course_id = c.course_id
    """)
    enrollments = cur.fetchall()
    
    college_conn.close()
    
    return render_template("admin_enroll.html", students=students, courses=courses_list, enrollments=enrollments)

# Updated add_enrollment route - replace existing (use institute_ids directly)
@app.route("/admin/add_enrollment", methods=["GET", "POST"])
def add_enrollment():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    
    courses = []
    if request.method == "GET":
        cur = college_conn.cursor()
        cur.execute("SELECT course_id, name FROM courses")
        courses = cur.fetchall()
    
    if request.method == "POST":
        institute_ids_str = request.form.get("institute_ids", "").strip()
        selected_courses = request.form.getlist("course_ids")  # Multi-select
        semester = request.form.get("semester", "").strip()
        year = int(request.form.get("year", 1))
        status = request.form.get("status", "Completed").strip()
        
        if not all([institute_ids_str, selected_courses, semester]):
            flash("Missing required fields.", "danger")
        else:
            institute_ids = [iid.strip() for iid in institute_ids_str.split(',')]
            errors = []
            success_count = 0
            
            cur = college_conn.cursor()
            for institute_id in institute_ids:
                # Check if institute_id exists in students
                student = cur.execute("SELECT institute_id FROM students WHERE institute_id = ?", (institute_id,)).fetchone()
                if not student:
                    errors.append(f"Invalid institute_id: {institute_id}")
                    continue
                
                for course_id in selected_courses:
                    try:
                        cur.execute("""
                            INSERT INTO enrollments (course_id, institute_id, semester, year, status) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (course_id, institute_id, semester, year, status))
                        success_count += 1
                    except sqlite3.IntegrityError:
                        errors.append(f"Duplicate enrollment for {institute_id} in {course_id}")
            
            college_conn.commit()
            college_conn.close()
            
            if errors:
                flash(f"Errors (skipped invalid/duplicates): {', '.join(errors)}", "danger")
            if success_count > 0:
                flash(f"Successfully added {success_count} enrollments!", "success")
            return redirect(url_for("manage_enrollments"))
        
        college_conn.close()
        return render_template("add_enrollment.html", courses=courses)
    
    college_conn.close()
    return render_template("add_enrollment.html", courses=courses)

# Updated delete_enrollment_search route - replace existing (search by institute_id)
@app.route("/admin/delete_enrollment_search", methods=["GET", "POST"])
def delete_enrollment_search():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    enrollments_to_delete = []
    
    if request.method == "POST":
        institute_id = request.form.get("institute_id", "").strip()
        if institute_id:
            college_conn = get_college_connection()
            cur = college_conn.cursor()
            enrollments_to_delete = cur.execute("""
                SELECT e.course_id, e.institute_id, e.semester, e.year, e.status,
                       c.name AS course_name,
                       s.roll_no
                FROM enrollments e
                LEFT JOIN courses c ON e.course_id = c.course_id
                LEFT JOIN students s ON e.institute_id = s.institute_id
                WHERE e.institute_id = ?
            """, (institute_id,)).fetchall()
            college_conn.close()
            
            if not enrollments_to_delete:
                flash("No enrollments found for this institute_id.", "danger")
    
    return render_template("delete_enrollment_search.html", enrollments=enrollments_to_delete)

# Updated delete_enrollment route - replace existing (DELETE by course_id and institute_id)
@app.route("/admin/delete_enrollment", methods=["POST"])
def delete_enrollment():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    selected_enrollments = request.form.getlist("enrollments")  # List of 'course_id|institute_id'
    
    if selected_enrollments:
        college_conn = get_college_connection()
        cur = college_conn.cursor()
        deleted_count = 0
        for sel in selected_enrollments:
            course_id, institute_id = sel.split('|')
            cur.execute("DELETE FROM enrollments WHERE course_id = ? AND institute_id = ?", 
                        (course_id, institute_id))
            deleted_count += cur.rowcount
        college_conn.commit()
        college_conn.close()
        flash(f"Deleted {deleted_count} enrollments successfully!", "success")
    
    return redirect(url_for("manage_enrollments"))

@app.route("/admin/reports", methods=["GET", "POST"])
def admin_reports():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    df = pd.DataFrame()  # Initialize empty DataFrame
    filename = "report.csv"
    
    if request.method == "POST":
        report_type = request.form.get("report_type")
        if report_type:
            college_conn = get_college_connection()
            cur = college_conn.cursor()
            
            if report_type == "semester":
                year = request.form.get("year-sem")
                semester = request.form.get("semester-sem")
                if year and semester:
                    table_name = f"{semester}_{year}_report"
                    cur.execute(f"""
                        SELECT year, semester, semester_number, institute_id, roll_no, course_id, grade, total_marks, status, credits_earned
                        FROM {table_name} 
                        WHERE year = ? AND semester = ?
                    """, (year, semester))
                    data = cur.fetchall()
                    filename = f"{semester}_{year}_report.csv"
                    df = pd.DataFrame(data, columns=['year', 'semester', 'semester_number', 'institute_id', 'roll_no', 'course_id', 'grade', 'total_marks', 'status', 'credits_earned'])
                    
            elif report_type == "attendance":
                course_id = request.form.get("course_id-att")
                year = request.form.get("year-att")
                if course_id and year:
                    table_name = f"attendance_{course_id}_{year}"
                    cur.execute(f"""
                        SELECT roll_no, date, status
                        FROM {table_name}
                    """)
                    data = cur.fetchall()
                    temp_df = pd.DataFrame(data, columns=['roll_no', 'date', 'status'])
                    
                    # Calculate percentage per student
                    if not temp_df.empty:
                        temp_df['date'] = pd.to_datetime(temp_df['date'])
                        temp_df['present'] = temp_df['status'].apply(lambda x: 1 if str(x).lower() == 'present' else 0)
                        percentage = temp_df.groupby(['roll_no'])['present'].agg(['count', 'sum']).reset_index()
                        percentage['percentage'] = (percentage['sum'] / percentage['count'] * 100).round(2)
                        df = percentage[['roll_no', 'percentage']]
                    else:
                        df = pd.DataFrame()
                    
                    filename = f"attendance_{course_id}_{year}.csv"
            elif report_type == "marks":
                course_id = request.form.get("course_id-marks")
                year = request.form.get("year-marks")
                semester = request.form.get("semester-marks")
                if course_id and year and semester:
                    table_name = f"marks_{course_id}_{year}_{semester}"
                    cur.execute(f"""
                        SELECT roll_no, institute_id, internal_marks, external_marks, grade
                        FROM {table_name}
                    """)
                    data = cur.fetchall()
                    filename = f"marks_{course_id}_{year}.csv"
                    df = pd.DataFrame(data, columns=['roll_no', 'institute_id', 'internal_marks', 'external_marks', 'grade'])
            
            elif report_type == "sgpa":
                # Consolidated, no params needed, fetch all
                table_name = "sgpa_report"
                cur.execute(f"""
                    SELECT year, semester, institute_id, roll_no, sgpa, credits
                    FROM {table_name}
                """)
                data = cur.fetchall()
                filename = "sgpa_report.csv"
                df = pd.DataFrame(data, columns=['year', 'semester', 'institute_id', 'roll_no', 'sgpa', 'credits'])
            
            college_conn.close()
            
            if not df.empty:
                output = BytesIO()
                df.to_csv(output, index=False, quoting=csv.QUOTE_ALL)
                output.seek(0)
                return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)
            else:
                flash("No data found for the selected criteria.", "info")
        
        return redirect(url_for("admin_reports"))
    
    return render_template("admin_reports.html")

# New route for changing password - add this after the manage_users route
@app.route("/admin/change_password", methods=["GET", "POST"])
def change_password():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    users_conn = get_users_connection()
    
    if request.method == "POST":
        user_type = request.form.get("user_type", "").strip()
        username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "").strip()
        
        if not all([user_type, username, new_password]):
            flash("Missing required fields.", "danger")
        else:
            # Verify user exists and matches type (optional, but good for security)
            cur = users_conn.cursor()
            cur.execute("SELECT type FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            if user and user['type'] == user_type:
                hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
                cur.execute("UPDATE users SET password = ? WHERE username = ?",
                            (hashed.decode("utf-8"), username))
                users_conn.commit()
                flash(f"Password updated successfully for {username} ({user_type})!", "success")
            else:
                flash("User not found or type mismatch.", "danger")
        
        users_conn.close()
        return redirect(url_for("change_password"))
    
    users_conn.close()
    return render_template("change_password.html")

@app.route("/admin/backup", methods=["GET", "POST"])
def admin_backup():
    if "username" not in session or session["type"] != "Admin":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    if request.method == "POST":
        selected_tables = request.form.getlist("tables")  # Get list of selected table names
        
        if not selected_tables:
            flash("Please select at least one table to backup.", "danger")
            # Fetch tables for re-render
            cur.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            all_tables = [row['name'] for row in cur.fetchall()]
            # Categorize for template
            attendance_tables = [t for t in all_tables if 'attendance' in t.lower()]
            marks_tables = [t for t in all_tables if 'marks' in t.lower()]
            reports_tables = [t for t in all_tables if 'reports' in t.lower() or 'report' in t.lower()]
            other_tables = [t for t in all_tables if t not in attendance_tables + marks_tables + reports_tables]
            college_conn.close()
            return render_template("admin_backup.html", tables=all_tables, attendance_tables=attendance_tables, marks_tables=marks_tables, reports_tables=reports_tables, other_tables=other_tables)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        for table_name in selected_tables:
            # Add section header
            writer.writerow([f"--- {table_name.capitalize()} ---"])
            
            # Export table data
            # For each table export (in the POST handler and if you add any in GET for previews)
            try:
                cur.execute(f"SELECT * FROM {table_name}")
                if cur.description:
                    writer.writerow([desc[0] for desc in cur.description])
                writer.writerows([list(row) for row in cur.fetchall()])  # <-- This line fixed
            except sqlite3.Error as e:
                writer.writerow([f"Error exporting {table_name}: {str(e)}"])
                
        college_conn.close()
        
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        return send_file(
            io.BytesIO(csv_content.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='college_backup.csv'
        )
    
    # GET: Fetch all table names
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    all_tables = [row['name'] for row in cur.fetchall()]
    
    # Categorize tables (case-insensitive matching; adjust patterns if needed)
    attendance_tables = [t for t in all_tables if 'attendance' in t.lower()]
    marks_tables = [t for t in all_tables if 'marks' in t.lower()]
    reports_tables = [t for t in all_tables if 'reports' in t.lower() or 'report' in t.lower()]
    other_tables = [t for t in all_tables if t not in attendance_tables + marks_tables + reports_tables]
    
    college_conn.close()
    return render_template("admin_backup.html", tables=all_tables, attendance_tables=attendance_tables, marks_tables=marks_tables, reports_tables=reports_tables, other_tables=other_tables)

@app.route("/faculty")
def faculty_dashboard():
    if "username" not in session or session["type"] != "Faculty":
        flash("Unauthorized access! Please log in as faculty.", "danger")
        return redirect(url_for("login"))
    return render_template("faculty_dashboard.html", username=session["username"])

@app.route("/student")
def student_dashboard():
    if "username" not in session or session["type"] != "Student":
        flash("Unauthorized access! Please log in as a student.", "danger")
        return redirect(url_for("login"))
    return render_template("student_dashboard.html", username=session["username"])

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)