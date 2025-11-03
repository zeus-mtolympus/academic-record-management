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

# Updated add_student route - replace existing (add guardian insertion)
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
        personal_email = request.form.get("pemail", "").strip()
        college_email = institute_id.lower() + "_" + fname + "@college.ac.in"
        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender", "").strip()
        department_id = request.form.get("department_id", "").strip()
        batch = request.form.get("batch", "").strip()
        status = request.form.get("status", "Active").strip()
        house_no = request.form.get("house_no", "").strip()
        lane = request.form.get("lane", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        country = request.form.get("country", "").strip()
        pincode = request.form.get("pincode", "").strip()
        
        # Guardian fields (optional)
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_gender = request.form.get("guardian_gender", "").strip()
        guardian_relation = request.form.get("guardian_relation", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()
        guardian_phone = request.form.get("guardian_phone", "").strip()
        guardian_occupation = request.form.get("guardian_occupation", "").strip()
        guardian_house_no = request.form.get("guardian_house_no", "").strip()
        guardian_lane = request.form.get("guardian_lane", "").strip()
        guardian_city = request.form.get("guardian_city", "").strip()
        guardian_state = request.form.get("guardian_state", "").strip()
        guardian_country = request.form.get("guardian_country", "").strip()
        guardian_pincode = request.form.get("guardian_pincode", "").strip()
        
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
                    INSERT INTO students (institute_id, fname, lname, roll_no, dob, gender, personal_email, college_email, phone, department_id, batch, cgpa, status, house_no, lane, city, state, country, pincode) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (institute_id, fname, lname, roll_no, dob, gender, personal_email, college_email, phone, department_id, batch, 0.0, status, house_no, lane, city, state, country, pincode))
                
                # Add guardian if provided (assume enrollment_id = institute_id; adjust if needed)
                if guardian_name:
                    try:
                        # Assume enrollment_id is institute_id or fetch real enrollment.id after creating one
                      
                        cur_college.execute("""
                            INSERT INTO student_guardian (institute_id, name, gender, relation, email, phone, occupation, house_no, lane, city, state, country, pincode)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (institute_id, guardian_name, guardian_gender, guardian_relation, guardian_email, guardian_phone, guardian_occupation, guardian_house_no, guardian_lane, guardian_city, guardian_state, guardian_country, guardian_pincode))
                        
                        flash(f"Guardian added for {guardian_name}.", "success")
                    except sqlite3.IntegrityError as ge:
                        flash(f"Guardian add error: {str(ge)}", "warning")  # Non-fatal
                else:
                    flash("No guardian added (optional).", "info")
                
                users_conn.commit()
                college_conn.commit()
                flash(f"Student added successfully! Institute ID: {institute_id}, Roll No: {roll_no}, Password: {password}", "success")
                college_conn.close()
                users_conn.close()
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

# Updated update_student route - replace existing (add guardian add option)
@app.route("/admin/update_student", methods=["GET", "POST"])
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
    house_no = request.form.get("house_no", "").strip()
    lane = request.form.get("lane", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    country = request.form.get("country", "").strip()
    pincode = request.form.get("pincode", "").strip()
    
    # Guardian add fields (optional for new guardian)
    add_guardian = request.form.get("add_guardian", "").strip() == "yes"
    if add_guardian:
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_gender = request.form.get("guardian_gender", "").strip()
        guardian_relation = request.form.get("guardian_relation", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()
        guardian_phone = request.form.get("guardian_phone", "").strip()
        guardian_occupation = request.form.get("guardian_occupation", "").strip()
        guardian_house_no = request.form.get("guardian_house_no", "").strip()
        guardian_lane = request.form.get("guardian_lane", "").strip()
        guardian_city = request.form.get("guardian_city", "").strip()
        guardian_state = request.form.get("guardian_state", "").strip()
        guardian_country = request.form.get("guardian_country", "").strip()
        guardian_pincode = request.form.get("guardian_pincode", "").strip()
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    # Update student
    cur.execute("""
        UPDATE students SET fname = ?, lname = ?, roll_no = ?, gender = ?, department_id = ?, batch = ?, status = ?,
        house_no = ?, lane = ?, city = ?, state = ?, country = ?, pincode = ? WHERE institute_id = ?
    """, (fname, lname, roll_no, gender, department_id, batch, status, house_no, lane, city, state, country, pincode, institute_id))
    
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            cur.execute("UPDATE students SET dob = ? WHERE institute_id = ?", (dob, institute_id))
        except ValueError:
            flash("Invalid DOB format. Use YYYY-MM-DD.", "danger")
    
    # Add new guardian if requested
    if add_guardian and guardian_name:
        try:
            # Fetch or create enrollment_id (assume first enrollment or use institute_id as proxy; adjust)
            cur.execute("SELECT id FROM enrollments WHERE institute_id = ? LIMIT 1", (institute_id,))
            enrollment_row = cur.fetchone()
            enrollment_id = enrollment_row['id'] if enrollment_row else institute_id  # Fallback
            
            guardian_id = f"G_{institute_id}_{guardian_relation}"  # Auto-generate
            cur.execute("""
                INSERT INTO student_guardian (guardian_id, enrollment_id, name, gender, relation, email, phone, occupation, house_no, lane, city, state, country, pincode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (guardian_id, enrollment_id, guardian_name, guardian_gender, guardian_relation, guardian_email, guardian_phone, guardian_occupation, guardian_house_no, guardian_lane, guardian_city, guardian_state, guardian_country, guardian_pincode))
            
            flash(f"New guardian {guardian_name} added.", "success")
        except sqlite3.IntegrityError as ge:
            flash(f"Guardian add error: {str(ge)}", "warning")
    
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
        course_code = course_id[:6]
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
                    INSERT INTO courses (course_id, course_code, name, semester, year, department_id, credits, faculty_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (course_id, course_code, name, semester, year, department_id, credits, faculty_id))
                college_conn.commit()
                flash(f"Course {course_id} ({name}) added successfully!", "success")
                return redirect(url_for("manage_courses"))
            except sqlite3.IntegrityError as e:
                flash(f"Integrity Error: {str(e)}. Check for duplicates or invalid IDs.", "danger")
                # Optional: Print to console for dev
                print(f"DB Error Details: {e} | Values: course_id={course_id}, dept={department_id}, fac={faculty_id}")
            except ValueError as e:
                flash(f"Value Error (e.g., invalid year): {str(e)}", "danger")
            except Exception as e:
                flash(f"Unexpected Error: {str(e)}", "danger")
                print(f"Unexpected Error: {e}")  # Console log
        
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
        cur.execute("SELECT department_id, department_name FROM departments")
        departments = cur.fetchall()
        cur.execute("SELECT institute_id as faculty_id, fname || ' ' || lname as name FROM faculty")
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

# Updated faculty_dashboard route - replace existing
@app.route("/faculty")
def faculty_dashboard():
    if "username" not in session or session["type"] != "Faculty":
        flash("Unauthorized access! Please log in as faculty.", "danger")
        return redirect(url_for("login"))
    
    # Fetch faculty's assigned courses for display (optional preview)
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT c.course_id, c.name 
        FROM courses c 
        WHERE c.faculty_id = ?
    """, (session["username"],))
    assigned_courses = cur.fetchall()
    college_conn.close()
    
    return render_template("faculty_dashboard.html", username=session["username"], assigned_courses=assigned_courses)

# Updated faculty_manage_marks route - replace existing (add year selection)
@app.route("/faculty/manage_marks", methods=["GET", "POST"])
def faculty_manage_marks():
    if "username" not in session or session["type"] != "Faculty":
        return redirect(url_for("login"))
    
    current_year = datetime.now().year
    
    if request.method == "POST":
        course_id = request.form["course_id"]
        year = int(request.form["year"])
        semester = request.form["semester"]
        # Redirect to marks entry with selected year and semester
        return redirect(url_for("faculty_enter_marks", course_id=course_id, year=year, semester=semester))
    
    # GET: Fetch assigned courses
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT c.course_id, c.name 
        FROM courses c 
        WHERE c.faculty_id = ?
    """, (session["username"],))
    courses = cur.fetchall()
    college_conn.close()
    
    if not courses:
        flash("No courses assigned to you.", "warning")
    
    return render_template("faculty_select_marks.html", courses=courses, current_year=current_year)

# No changes to faculty_enter_marks (already uses passed year)

# # Updated faculty_enter_marks route - replace existing (only update existing records, skip new inserts)
@app.route("/faculty/enter_marks/<course_id>/<int:year>/<semester>", methods=["GET", "POST"])
def faculty_enter_marks(course_id, year, semester):
    if "username" not in session or session["type"] != "Faculty":
        return redirect(url_for("login"))
    
    # Verify faculty is assigned to this course
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("SELECT faculty_id FROM courses WHERE course_id = ?", (course_id,))
    course = cur.fetchone()
    if not course or course['faculty_id'] != session["username"]:
        flash("You are not assigned to this course.", "danger")
        college_conn.close()
        return redirect(url_for("faculty_dashboard"))
    
    marks_table = f"marks_{course_id}_{year}_{semester}"
    
    if request.method == "POST":
        # Group changes by roll_no to build full row
        student_updates = {}
        for key, value in request.form.items():
            if key.startswith("internal_marks_"):
                roll_no = key.split("_")[-1]
                student_updates.setdefault(roll_no, {})
                student_updates[roll_no]['internal_marks'] = float(value) if value else None
            elif key.startswith("external_marks_"):
                roll_no = key.split("_")[-1]
                student_updates.setdefault(roll_no, {})
                student_updates[roll_no]['external_marks'] = float(value) if value else None
            elif key.startswith("grade_"):
                roll_no = key.split("_")[-1]
                student_updates.setdefault(roll_no, {})
                student_updates[roll_no]['grade'] = value if value else None
        
        updated_count = 0
        # For each student, fetch existing row if any, merge changes, then UPDATE only if exists
        for roll_no, changes in student_updates.items():
            # Fetch existing
            try:
                cur.execute(f"SELECT * FROM {marks_table} WHERE roll_no = ?", (roll_no,))
                existing = cur.fetchone()
                if existing:
                    # Existing row found: Merge changes and UPDATE full row
                    for field in ['internal_marks', 'external_marks', 'grade']:
                        if field not in changes:
                            changes[field] = existing[field]
                    # Ensure institute_id is preserved
                    changes['institute_id'] = existing['institute_id']
                    
                    # UPDATE the existing row
                    cur.execute(f"""
                        UPDATE {marks_table} 
                        SET institute_id = ?, internal_marks = ?, external_marks = ?, grade = ? 
                        WHERE roll_no = ?
                    """, (changes['institute_id'], changes.get('internal_marks'), changes.get('external_marks'), changes.get('grade'), roll_no))
                    updated_count += 1
                else:
                    # No existing row: Skip (no new insert)
                    continue
            except sqlite3.OperationalError:
                # Table doesn't exist or no row: Skip
                continue
        
        if updated_count > 0:
            college_conn.commit()
            flash(f"Marks updated for {updated_count} existing records in {course_id} ({year} - {semester})!", "success")
        else:
            flash("No existing marks records found to update.", "info")
        college_conn.close()
        return redirect(url_for("faculty_dashboard"))
    
    # GET: Fetch enrolled students for this year, roll_no, and current marks from dynamic table
    cur.execute("""
        SELECT s.roll_no, s.institute_id, s.fname || ' ' || s.lname AS name
        FROM students s 
        LEFT JOIN enrollments e ON s.institute_id = e.institute_id AND e.year = ?
        WHERE e.course_id = ?
    """, (year, course_id))
    students_base = cur.fetchall()
    
    students = []
    for student in students_base:
        try:
            cur.execute(f"""
                SELECT internal_marks, external_marks, grade 
                FROM {marks_table} 
                WHERE roll_no = ?
            """, (student['roll_no'],))
            marks_row = cur.fetchone()
            students.append({
                'roll_no': student['roll_no'],
                'institute_id': student['institute_id'],
                'name': student['name'],
                'internal_marks': marks_row['internal_marks'] if marks_row else None,
                'external_marks': marks_row['external_marks'] if marks_row else None,
                'grade': marks_row['grade'] if marks_row else None
            })
        except sqlite3.OperationalError:
            # Table doesn't exist yet - no marks
            students.append({
                'roll_no': student['roll_no'],
                'institute_id': student['institute_id'],
                'name': student['name'],
                'internal_marks': None,
                'external_marks': None,
                'grade': None
            })
    
    # Fetch course name
    cur.execute("SELECT name FROM courses WHERE course_id = ?", (course_id,))
    course_result = cur.fetchone()
    course_name = course_result['name'] if course_result else "Unknown"
    
    college_conn.close()
    return render_template("faculty_marks.html", course_id=course_id, course_name=course_name, year=year, semester=semester, students=students)

# No changes needed for attendance (INSERT OR REPLACE is fine since only status per date/roll_no; no multiple fields to preserve)

# Updated faculty_mark_attendance route - replace existing (ensure year is passed and used)
@app.route("/faculty/mark_attendance", methods=["GET", "POST"])
def faculty_mark_attendance():
    if "username" not in session or session["type"] != "Faculty":
        return redirect(url_for("login"))
    
    current_year = datetime.now().year
    
    if request.method == "POST":
        course_id = request.form["course_id"]
        year = int(request.form["year"])
        date_str = request.form["date"]
        if not date_str:
            flash("Please select a date.", "danger")
        else:
            # Redirect to attendance marking with selected year
            return redirect(url_for("faculty_enter_attendance", course_id=course_id, year=year, date=date_str))
    
    # GET: Fetch assigned courses
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT c.course_id, c.name 
        FROM courses c 
        WHERE c.faculty_id = ?
    """, (session["username"],))
    courses = cur.fetchall()
    college_conn.close()
    
    if not courses:
        flash("No courses assigned to you.", "warning")
    
    return render_template("faculty_select_attendance.html", courses=courses, current_year=current_year)

# Updated faculty_enter_attendance route - replace existing (remove institute_id from attendance INSERT, assume schema has only roll_no, date, status)
@app.route("/faculty/enter_attendance/<course_id>/<int:year>/<date>", methods=["GET", "POST"])
def faculty_enter_attendance(course_id, year, date):
    if "username" not in session or session["type"] != "Faculty":
        return redirect(url_for("login"))
    
    # Verify faculty is assigned to this course
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("SELECT faculty_id FROM courses WHERE course_id = ?", (course_id,))
    course = cur.fetchone()
    if not course or course['faculty_id'] != session["username"]:
        flash("You are not assigned to this course.", "danger")
        college_conn.close()
        return redirect(url_for("faculty_dashboard"))
    
    attendance_table = f"attendance_{course_id}_{year}"
    
    if request.method == "POST":
        # Update attendance for each student (only status; updates if exists via OR REPLACE)
        for key, status in request.form.items():
            if key.startswith("attendance_"):
                roll_no = key.split("_")[-1]  # Last part is roll_no
                # Before the execute, check if row exists for this roll_no and date
                cur.execute(f"""
                    SELECT 1 FROM {attendance_table} WHERE roll_no = ? AND date = ?
                """, (roll_no, date))
                exists = cur.fetchone() is not None

                if exists:
                    # Update existing row
                    cur.execute(f"""
                        UPDATE {attendance_table} 
                        SET status = ? 
                        WHERE roll_no = ? AND date = ?
                    """, (status, roll_no, date))
                else:
                    # Insert new row
                    cur.execute(f"""
                        INSERT INTO {attendance_table} (roll_no, date, status) 
                        VALUES (?, ?, ?)
                    """, (roll_no, date, status))
        college_conn.commit()
        flash(f"Attendance updated for {course_id} ({year}) on {date} successfully!", "success")
        college_conn.close()
        return redirect(url_for("faculty_dashboard"))
    
    # GET: Fetch enrolled students for this year and current attendance from dynamic table (no institute_id fetch)
    cur.execute("""
        SELECT s.roll_no, s.fname || ' ' || s.lname AS name
        FROM students s 
        LEFT JOIN enrollments e ON s.institute_id = e.institute_id AND e.year = ?
        WHERE e.course_id = ?
    """, (year, course_id))
    students_base = cur.fetchall()
    
    students = []
    for student in students_base:
        try:
            cur.execute(f"""
                SELECT status 
                FROM {attendance_table} 
                WHERE roll_no = ? AND date = ?
            """, (student['roll_no'], date))
            att_row = cur.fetchone()
            students.append({
                'roll_no': student['roll_no'],
                'name': student['name'],
                'attendance_status': att_row['status'] if att_row else 'Not Marked'
            })
        except sqlite3.OperationalError:
            # Table doesn't exist yet - new entry
            students.append({
                'roll_no': student['roll_no'],
                'name': student['name'],
                'attendance_status': 'Not Marked'
            })
    
    # Fetch course name
    cur.execute("SELECT name FROM courses WHERE course_id = ?", (course_id,))
    course_result = cur.fetchone()
    course_name = course_result['name'] if course_result else "Unknown"
    
    college_conn.close()
    return render_template("faculty_attendance.html", course_id=course_id, course_name=course_name, year=year, date=date, students=students)

# New route for changing faculty password - add this (similar to student)
@app.route("/faculty/change_password", methods=["GET", "POST"])
def faculty_change_password():
    if "username" not in session or session["type"] != "Faculty":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        
        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return render_template("faculty_change_password.html")
        
        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return render_template("faculty_change_password.html")
        
        # Verify old password
        users_conn = get_users_connection()
        cur = users_conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (session["username"],))
        user = cur.fetchone()
        if not user or not bcrypt.checkpw(old_password.encode("utf-8"), user['password'].encode("utf-8")):
            flash("Old password is incorrect.", "danger")
            users_conn.close()
            return render_template("faculty_change_password.html")
        
        # Hash and update new password
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        cur.execute("UPDATE users SET password = ? WHERE username = ?", (hashed.decode("utf-8"), session["username"]))
        users_conn.commit()
        users_conn.close()
        
        flash("Password changed successfully!", "success")
        return redirect(url_for("faculty_dashboard"))
    
    return render_template("faculty_change_password.html")

# Updated student_dashboard route - replace existing (fetch enrolled courses for preview)
@app.route("/student")
def student_dashboard():
    if "username" not in session or session["type"] != "Student":
        flash("Unauthorized access! Please log in as a student.", "danger")
        return redirect(url_for("login"))
    
    # Fetch student's enrolled courses for display
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT c.course_id, c.name 
        FROM enrollments e 
        JOIN courses c ON e.course_id = c.course_id
        WHERE e.institute_id = ?
    """, (session["username"],))
    enrolled_courses = cur.fetchall()
    college_conn.close()
    
    return render_template("student_dashboard.html", username=session["username"], enrolled_courses=enrolled_courses)


@app.route("/student/view_marks", methods=["GET", "POST"])
def student_view_marks():
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    current_year = datetime.now().year
    
    if request.method == "POST":
        course_id = request.form["course_id"]
        year = int(request.form["year"])
        semester = request.form["semester"]
        return redirect(url_for("student_marks_detail", course_id=course_id, year=year, semester=semester))
    
    # Fetch enrolled courses
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT DISTINCT c.course_id, c.name 
        FROM enrollments e 
        JOIN courses c ON e.course_id = c.course_id
        WHERE e.institute_id = ?
    """, (session["username"],))
    courses = cur.fetchall()
    college_conn.close()
    
    if not courses:
        flash("No courses enrolled.", "warning")
    
    return render_template("student_select_marks.html", courses=courses, current_year=current_year)

# Updated student_marks_detail route - replace existing (dynamic table)
@app.route("/student/marks_detail/<course_id>/<int:year>/<semester>")
def student_marks_detail(course_id, year, semester):
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    marks_table = f"marks_{course_id}_{year}_{semester}"
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    # Fetch marks for this student from dynamic table
    try:
        cur.execute(f"""
            SELECT internal_marks, external_marks, grade 
            FROM {marks_table} 
            WHERE roll_no = (SELECT roll_no FROM students WHERE institute_id = ?) 
        """, (session["username"],))
        marks_row = cur.fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist
        marks_row = None
    
    # Fetch course name
    cur.execute("SELECT name FROM courses WHERE course_id = ?", (course_id,))
    course_result = cur.fetchone()
    course_name = course_result['name'] if course_result else "Unknown"
    
    college_conn.close()
    return render_template("student_marks.html", course_id=course_id, course_name=course_name, year=year, semester=semester, marks=marks_row)

# Updated student_view_attendance route - replace existing (add year selection)
@app.route("/student/view_attendance", methods=["GET", "POST"])
def student_view_attendance():
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    current_year = datetime.now().year
    
    if request.method == "POST":
        course_id = request.form["course_id"]
        year = int(request.form["year"])
        return redirect(url_for("student_attendance_detail", course_id=course_id, year=year))
    
    # Fetch enrolled courses
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT DISTINCT c.course_id, c.name 
        FROM enrollments e 
        JOIN courses c ON e.course_id = c.course_id
        WHERE e.institute_id = ?
    """, (session["username"],))
    courses = cur.fetchall()
    college_conn.close()
    
    if not courses:
        flash("No courses enrolled.", "warning")
    
    return render_template("student_select_attendance.html", courses=courses, current_year=current_year)

# Updated student_attendance_detail route - replace existing (pass present_days and total_days)
@app.route("/student/attendance_detail/<course_id>/<int:year>")
def student_attendance_detail(course_id, year):
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    attendance_table = f"attendance_{course_id}_{year}"
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    
    # Fetch roll_no for student
    cur.execute("SELECT roll_no FROM students WHERE institute_id = ?", (session["username"],))
    roll_no_row = cur.fetchone()
    roll_no = roll_no_row['roll_no'] if roll_no_row else None
    
    if not roll_no:
        flash("Student roll number not found.", "danger")
        college_conn.close()
        return redirect(url_for("student_view_attendance"))
    
    # Fetch attendance records for this student from dynamic table
    try:
        cur.execute(f"""
            SELECT date, status 
            FROM {attendance_table} 
            WHERE roll_no = ?
            ORDER BY date DESC
        """, (roll_no,))
        attendance_records = cur.fetchall()
    except sqlite3.OperationalError:
        # Table doesn't exist
        attendance_records = []
    
    # Fetch course name
    cur.execute("SELECT name FROM courses WHERE course_id = ?", (course_id,))
    course_result = cur.fetchone()
    course_name = course_result['name'] if course_result else "Unknown"
    
    # Calculate summary
    total_days = len(attendance_records)
    present_days = len([r for r in attendance_records if r['status'] == 'Present'])
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    college_conn.close()
    return render_template("student_attendance.html", course_id=course_id, course_name=course_name, year=year, records=attendance_records, percentage=attendance_percentage, present_days=present_days, total_days=total_days)

# New route for profile
# Updated student_profile route - replace existing (add guardian fetch)
@app.route("/student/profile")
def student_profile():
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    college_conn = get_college_connection()
    cur = college_conn.cursor()
    cur.execute("""
        SELECT * FROM students WHERE institute_id = ?
    """, (session["username"],))
    profile = cur.fetchone()
    
    # Fetch guardians (assume enrollments has 'id' as PRIMARY KEY; adjust join if schema differs)
    cur.execute("""
        SELECT sg.* FROM student_guardian sg
        JOIN students s ON sg.institute_id = s.institute_id
        WHERE s.institute_id = ?
    """, (session["username"],))
    guardians = cur.fetchall()
    
    college_conn.close()
    
    return render_template("student_profile.html", profile=profile, guardians=guardians)

# New route for changing student password - add this
@app.route("/student/change_password", methods=["GET", "POST"])
def student_change_password():
    if "username" not in session or session["type"] != "Student":
        return redirect(url_for("login"))
    
    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]
        
        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return render_template("student_change_password.html")
        
        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return render_template("student_change_password.html")
        
        # Verify old password
        users_conn = get_users_connection()
        cur = users_conn.cursor()
        cur.execute("SELECT password FROM users WHERE username = ?", (session["username"],))
        user = cur.fetchone()
        if not user or not bcrypt.checkpw(old_password.encode("utf-8"), user['password'].encode("utf-8")):
            flash("Old password is incorrect.", "danger")
            users_conn.close()
            return render_template("student_change_password.html")
        
        # Hash and update new password
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        cur.execute("UPDATE users SET password = ? WHERE username = ?", (hashed.decode("utf-8"), session["username"]))
        users_conn.commit()
        users_conn.close()
        
        flash("Password changed successfully!", "success")
        return redirect(url_for("student_dashboard"))
    
    return render_template("student_change_password.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)