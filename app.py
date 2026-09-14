from flask import Flask, render_template_string, request, redirect, url_for, session, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# PRODUCTION SECURITY: Fetch secret key and mail credentials from environment variables
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_a_very_secure_random_key_in_production")

DB_NAME = "school_database.db"

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

SCHOOL_NAME = "Top Spot Academy"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Enable WAL mode for better concurrency handling in SQLite
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT UNIQUE,
                reset_code TEXT,
                reset_code_time TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                dob TEXT,
                guardian_email TEXT,
                phone TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS billing (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                fee_type TEXT,
                description TEXT,
                amount_due REAL,
                amount_paid REAL DEFAULT 0.0,
                balance REAL,
                status TEXT DEFAULT 'Unpaid',
                due_date TEXT,
                UNIQUE(student_id, fee_type)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'Income' or 'Expense'
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                recorded_by TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                date TEXT,
                status TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timetables (
                timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
                grade_level TEXT,
                day_of_week TEXT,
                period_number INTEGER,
                subject TEXT,
                teacher TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS newsletters (
                newsletter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                target_audience TEXT,
                date_published TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                teacher_name TEXT,
                term TEXT,
                performance_summary TEXT,
                grades TEXT,
                date_uploaded TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elearning (
                resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                filename TEXT NOT NULL,
                uploaded_by TEXT,
                date_uploaded TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_incidents (
                incident_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                reported_by TEXT,
                incident_type TEXT,
                description TEXT,
                date_recorded TEXT
            )
        ''')
        
        # Seed Admin: Mr. Nyereyemhuka
        cursor.execute("SELECT * FROM users WHERE username = 'Mr. Nyereyemhuka'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('password123')
            cursor.execute("INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)", 
                           ('Mr. Nyereyemhuka', hashed_pw, 'Admin', 'admin@topspot.ac.zw'))

        # Seed Finance User: Ms. Rutendo
        cursor.execute("SELECT * FROM users WHERE username = 'Ms. Rutendo'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('password123')
            cursor.execute("INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)", 
                           ('Ms. Rutendo', hashed_pw, 'Finance', 'rutendo@topspot.ac.zw'))

        conn.commit()

init_db()

def seed_olevel_timetables():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        comprehensive_schedule = [
            # --- FORM 1 ---
            ("Form 1", "Monday", 1, "Mathematics (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 1", "Monday", 2, "English Language (08:25 - 09:20)", "Mrs. Chikunda"),
            ("Form 1", "Monday", 3, "Combined Science (09:20 - 10:15)", "Mr. Nyereyemhuka"),
            ("Form 1", "Monday", 4, "Geography (10:50 - 11:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Monday", 5, "ICT (11:45 - 12:45)", "Mrs. Nyereyemhuka"),
            ("Form 1", "Monday", 6, "Shona (12:45 - 13:45)", "Mrs. Chikunda"),
            
            ("Form 1", "Tuesday", 1, "Business Studies (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 1", "Tuesday", 2, "Principles of Accounting (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 1", "Tuesday", 3, "Heritage Studies (09:20 - 10:15)", "Mrs. Chikunda"),
            ("Form 1", "Tuesday", 4, "Mathematics (10:50 - 11:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Tuesday", 5, "English Language (11:45 - 12:45)", "Mrs. Chikunda"),
            ("Form 1", "Tuesday", 6, "Technical Graphics (12:45 - 13:45)", "Mrs. Nyereyemhuka"),

            ("Form 1", "Wednesday", 1, "Combined Science (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 1", "Wednesday", 2, "Geography (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 1", "Wednesday", 3, "Shona (09:20 - 10:15)", "Mrs. Chikunda"),
            ("Form 1", "Wednesday", 4, "ICT (10:50 - 11:45)", "Mrs. Nyereyemhuka"),
            ("Form 1", "Wednesday", 5, "Business Studies (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Wednesday", 6, "Mathematics (12:45 - 13:45)", "Mr. Nyereyemhuka"),

            ("Form 1", "Thursday", 1, "Principles of Accounting (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 1", "Thursday", 2, "Heritage Studies (08:25 - 09:20)", "Mrs. Chikunda"),
            ("Form 1", "Thursday", 3, "Technical Graphics (09:20 - 10:15)", "Mrs. Nyereyemhuka"),
            ("Form 1", "Thursday", 4, "English Language (10:50 - 11:45)", "Mrs. Chikunda"),
            ("Form 1", "Thursday", 5, "Combined Science (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Thursday", 6, "Geography (12:45 - 13:45)", "Mr. Nyereyemhuka"),

            ("Form 1", "Friday", 1, "Mathematics (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 1", "Friday", 2, "ICT (08:25 - 09:20)", "Mrs. Nyereyemhuka"),
            ("Form 1", "Friday", 3, "Shona (09:20 - 10:15)", "Mrs. Chikunda"),
            ("Form 1", "Friday", 4, "Business Studies (10:50 - 11:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Friday", 5, "Principles of Accounting (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 1", "Friday", 6, "Heritage Studies (12:45 - 13:45)", "Mrs. Chikunda"),

            # --- FORM 2 ---
            ("Form 2", "Monday", 1, "English Language (07:30 - 08:25)", "Mrs. Chikunda"),
            ("Form 2", "Monday", 2, "Mathematics (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 2", "Monday", 3, "Geography (09:20 - 10:15)", "Mr. Nyereyemhuka"),
            ("Form 2", "Monday", 4, "Combined Science (10:50 - 11:45)", "Mr. Nyereyemhuka"),
            ("Form 2", "Monday", 5, "Shona (11:45 - 12:45)", "Mrs. Chikunda"),
            ("Form 2", "Monday", 6, "ICT (12:45 - 13:45)", "Mrs. Nyereyemhuka"),

            ("Form 2", "Tuesday", 1, "Principles of Accounting (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 2", "Tuesday", 2, "Business Studies (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 2", "Tuesday", 3, "Technical Graphics (09:20 - 10:15)", "Mrs. Nyereyemhuka"),
            ("Form 2", "Tuesday", 4, "Heritage Studies (10:50 - 11:45)", "Mrs. Chikunda"),
            ("Form 2", "Tuesday", 5, "Mathematics (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 2", "Tuesday", 6, "English Language (12:45 - 13:45)", "Mrs. Chikunda"),

            ("Form 2", "Wednesday", 1, "Geography (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 2", "Wednesday", 2, "Combined Science (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 2", "Wednesday", 3, "Mathematics (09:20 - 10:15)", "Mr. Nyereyemhuka"),
            ("Form 2", "Wednesday", 4, "Business Studies (10:50 - 11:45)", "Mr. Nyereyemhuka"),
            ("Form 2", "Wednesday", 5, "ICT (11:45 - 12:45)", "Mrs. Nyereyemhuka"),
            ("Form 2", "Wednesday", 6, "Shona (12:45 - 13:45)", "Mrs. Chikunda"),

            ("Form 2", "Thursday", 1, "Heritage Studies (07:30 - 08:25)", "Mrs. Chikunda"),
            ("Form 2", "Thursday", 2, "Principles of Accounting (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 2", "Thursday", 3, "English Language (09:20 - 10:15)", "Mrs. Chikunda"),
            ("Form 2", "Thursday", 4, "Technical Graphics (10:50 - 11:45)", "Mrs. Nyereyemhuka"),
            ("Form 2", "Thursday", 5, "Geography (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 2", "Thursday", 6, "Combined Science (12:45 - 13:45)", "Mr. Nyereyemhuka"),

            ("Form 2", "Friday", 1, "ICT (07:30 - 08:25)", "Mrs. Nyereyemhuka"),
            ("Form 2", "Friday", 2, "Mathematics (08:25 - 09:20)", "Mr. Nyereyemhuka"),
            ("Form 2", "Friday", 3, "Business Studies (09:20 - 10:15)", "Mr. Nyereyemhuka"),
            ("Form 2", "Friday", 4, "Shona (10:50 - 11:45)", "Mrs. Chikunda"),
            ("Form 2", "Friday", 5, "Principles of Accounting (11:45 - 12:45)", "Mr. Nyereyemhuka"),
            ("Form 2", "Friday", 6, "Heritage Studies (12:45 - 13:45)", "Mrs. Chikunda"),

            # --- FORM 3 & 4 ---
            ("Form 3", "Monday", 1, "Mathematics (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 3", "Monday", 2, "English Language (08:25 - 09:20)", "Sir Nyereyemhuka"),
            ("Form 3", "Monday", 3, "Combined Science (09:20 - 10:15)", "Sir Nyereyemhuka"),
            ("Form 3", "Monday", 4, "Geography (10:50 - 11:45)", "Sir Nyereyemhuka"),
            ("Form 3", "Monday", 5, "ICT (11:45 - 12:45)", "Mrs. Nyereyemhuka"),
            ("Form 3", "Monday", 6, "Shona (12:45 - 13:45)", "Mr. Nyereyemhuka"),

            ("Form 4", "Monday", 1, "Mathematics (07:30 - 08:25)", "Mr. Nyereyemhuka"),
            ("Form 4", "Monday", 2, "English Language (08:25 - 09:20)", "Sir Nyereyemhuka"),
            ("Form 4", "Monday", 3, "Combined Science (09:20 - 10:15)", "Sir Nyereyemhuka"),
            ("Form 4", "Monday", 4, "Geography (10:50 - 11:45)", "Sir Nyereyemhuka"),
            ("Form 4", "Monday", 5, "ICT (11:45 - 12:45)", "Mrs. Nyereyemhuka"),
            ("Form 4", "Monday", 6, "Shona (12:45 - 13:45)", "Mr. Nyereyemhuka"),
        ]
        
        for slot in comprehensive_schedule:
            cursor.execute('''
                SELECT * FROM timetables WHERE grade_level = ? AND day_of_week = ? AND period_number = ?
            ''', (slot[0], slot[1], slot[2]))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO timetables (grade_level, day_of_week, period_number, subject, teacher)
                    VALUES (?, ?, ?, ?, ?)
                ''', slot)
        conn.commit()

seed_olevel_timetables()

def is_teacher_or_admin():
    return session.get('role') == 'Teacher' or session.get('user') == 'Mr. Nyereyemhuka'

def send_email_notification(recipient_email, subject, body):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.example.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    sender_email = os.environ.get("SMTP_USER", "notifications@topspot.ac.zw")
    sender_password = os.environ.get("SMTP_PASSWORD", "secret_password")

    if smtp_server == "smtp.example.com":
        print(f"[SIMULATED SMTP EMAIL] To: {recipient_email} | Subject: {subject} | Body: {body}")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email delivery failed: {e}")
        return False

def render_page(body_content, **kwargs):
    logged_in = 'user' in session
    username = session.get('user', '')
    role = session.get('role', '')
    is_admin_teacher = is_teacher_or_admin()

    rendered_body = render_template_string(body_content, school_name=SCHOOL_NAME, logged_in=logged_in, username=username, role=role, is_admin_teacher=is_admin_teacher, **kwargs)

    base_template = '''
    <!doctype html>
    <html lang="en">
    <head>
        <title>{{ school_name }} - Management System</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --sidebar-bg: #f8f9fa;
                --sidebar-border: #e2e8f0;
                --text-main: #2d3748;
                --text-muted: #718096;
                --primary: #3182ce;
                --bg-main: #f4f6f9;
            }
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: var(--bg-main); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
            
            aside { width: 270px; background: var(--sidebar-bg); border-right: 1px solid var(--sidebar-border); display: flex; flex-direction: column; height: 100vh; overflow-y: auto; }
            .brand { padding: 20px; font-size: 18px; font-weight: bold; color: #1a202c; border-bottom: 1px solid var(--sidebar-border); display: flex; align-items: center; background: white; }
            .sidebar-menu { padding: 15px 10px; display: flex; flex-direction: column; gap: 5px; flex: 1; }
            .menu-section-title { font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: bold; margin: 15px 10px 5px 10px; letter-spacing: 0.5px; }
            aside a { padding: 10px 12px; color: #4a5568; text-decoration: none; font-size: 14px; border-radius: 6px; display: flex; align-items: center; gap: 10px; font-weight: 500; transition: background 0.2s; }
            aside a:hover { background: #edf2f7; color: var(--primary); }
            
            .main-wrapper { flex: 1; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
            header { background: white; border-bottom: 1px solid var(--sidebar-border); padding: 15px 30px; display: flex; justify-content: flex-end; align-items: center; gap: 20px; }
            .user-badge { font-size: 14px; color: var(--text-muted); background: #edf2f7; padding: 6px 12px; border-radius: 20px; }
            .logout-btn { color: #e53e3e; text-decoration: none; font-weight: 600; font-size: 14px; }
            
            .content-container { padding: 30px; overflow-y: auto; flex: 1; }
            
            h1 { font-size: 22px; color: #1a202c; margin-top: 0; }
            h2 { font-size: 18px; color: #2d3748; margin-top: 25px; }
            form { background: white; padding: 25px; border-radius: 8px; border: 1px solid var(--sidebar-border); margin-bottom: 25px; max-width: 650px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            input, select, textarea { display: block; margin-bottom: 15px; padding: 10px; width: 100%; box-sizing: border-box; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 14px; }
            button { background: var(--primary); color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; }
            button:hover { background: #2b6cb0; }
            table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; border: 1px solid var(--sidebar-border); margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #edf2f7; font-size: 14px; }
            th { background: #f7fafc; color: #4a5568; font-weight: 600; }
            .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 25px; }
            .dashboard-card { background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--sidebar-border); box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 25px; }
            .chart-container { background: white; padding: 20px; border-radius: 8px; border: 1px solid var(--sidebar-border); height: 280px; position: relative; }
            
            /* Print Optimization */
            @media print {
                aside, header, .logout-btn, form, button, a, .hide-on-print {
                    display: none !important;
                }
                body, .main-wrapper, .content-container {
                    background: white !important;
                    padding: 0 !important;
                    margin: 0 !important;
                    display: block !important;
                    height: auto !important;
                    overflow: visible !important;
                }
                .content-container {
                    padding: 0 !important;
                }
            }

            @media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } body { flex-direction: column; height: auto; overflow: auto; } aside { width: 100%; height: auto; } .main-wrapper { height: auto; overflow: visible; } }
        </style>
        <script>
            function togglePassword(id) {
                const input = document.getElementById(id);
                if (input.type === "password") {
                    input.type = "text";
                } else {
                    input.type = "password";
                }
            }
        </script>
    </head>
    <body>
        <aside>
            <div class="brand">
                <span>{{ school_name }}</span>
            </div>
            <div class="sidebar-menu">
                {% if logged_in %}
                    <div class="menu-section-title">Main Navigation</div>
                    {% if role == 'Teacher' and username != 'Mr. Nyereyemhuka' %}
                        <a href="/teacher-dashboard">📊 Dashboard</a>
                        <a href="/teacher-students">👥 Manage Students</a>
                        <a href="/teacher-reports">📝 Upload Reports</a>
                        <a href="/attendance">📋 Attendance Register</a>
                        <a href="/behavior">⚠️ Behavior Tracking</a>
                        <a href="/timetable">📅 Timetable</a>
                        <a href="/elearning">📚 E-Learning & Textbooks</a>
                        <a href="/change-password">🔑 Change Password</a>
                    {% elif role == 'Parent' %}
                        <a href="/parent-dashboard">📂 My Children's Reports</a>
                        <a href="/behavior">⚠️ Behavior Tracking</a>
                        <a href="/timetable">📅 Timetable</a>
                        <a href="/elearning">📚 E-Learning & Textbooks</a>
                    {% elif role == 'Student' %}
                        <a href="/student-dashboard">🎓 Student Dashboard</a>
                        <a href="/behavior">⚠️ Behavior Tracking</a>
                        <a href="/timetable">📅 Timetable</a>
                        <a href="/elearning">📚 E-Learning & Textbooks</a>
                        <a href="/change-password">🔑 Change Password</a>
                    {% elif role == 'Finance' %}
                        <a href="/finance">💳 Finance & Billing</a>
                        <a href="/elearning">📚 E-Learning & Textbooks</a>
                    {% else %}
                        <!-- Admin / Mr. Nyereyemhuka -->
                        <a href="/teacher-dashboard">📊 Teacher Dashboard</a>
                        <a href="/teacher-students">👥 Manage Students & Directory</a>
                        <a href="/teacher-reports">📝 Upload Reports</a>
                        <a href="/finance">💳 Finance & Billing</a>
                        <a href="/attendance">📋 Attendance Register</a>
                        <a href="/behavior">⚠️ Behavior Tracking</a>
                        <a href="/timetable">📅 Timetable</a>
                        <a href="/newsletters">📢 Newsletters & Notices</a>
                        <a href="/elearning">📚 E-Learning & Textbooks</a>
                        <a href="/change-password">🔑 Change Password</a>
                    {% endif %}
                {% else %}
                    <div class="menu-section-title">Access Portal</div>
                    <a href="/login">🔐 Login</a>
                    <a href="/register-teacher">👩‍🏫 Teacher Registration</a>
                    <a href="/register-parent">👪 Parent Portal Registration</a>
                    <a href="/register-student">🎓 Student Portal Registration</a>
                    <a href="/forgot-password">❓ Forgot Password</a>
                {% endif %}
            </div>
        </aside>

        <div class="main-wrapper">
            <header>
                {% if logged_in %}
                    <span class="user-badge">👤 {{ username }} ({{ role }})</span>
                    <a href="/logout" class="logout-btn">Logout</a>
                {% endif %}
            </header>
            <div class="content-container">
                {{ body_content | safe }}
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(base_template, school_name=SCHOOL_NAME, 
                                  logged_in=logged_in, username=username, role=role, body_content=rendered_body)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
        
        if user and check_password_hash(user[2], password):
            session['user'] = user[1]
            session['role'] = user[3]
            if session['role'] == 'Teacher':
                return redirect(url_for('teacher_dashboard'))
            elif session['role'] == 'Parent':
                return redirect(url_for('parent_dashboard'))
            elif session['role'] == 'Student':
                return redirect(url_for('student_dashboard'))
            elif session['role'] == 'Finance':
                return redirect(url_for('finance'))
            return redirect(url_for('index'))
        else:
            error = "Invalid username or password."
            
    content = '''
    <h1>Portal Login</h1>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    <form method="POST">
        <input type="text" name="username" placeholder="Username / Email" required>
        <input type="password" name="password" id="login_password" placeholder="Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('login_password')" style="margin: 0; width: auto;"> Show Password
        </label>
        <button type="submit">Login to Dashboard</button>
    </form>
    <p>Forgot your password? <a href="/forgot-password">Reset via Email Code</a></p>
    <p>New Teacher? <a href="/register-teacher">Register as a Teacher</a></p>
    <p>New Parent? <a href="/register-parent">Register for Parent Portal</a></p>
    <p>New Student? <a href="/register-student">Register for Student Portal</a></p>
    '''
    return render_page(content, error=error)

@app.route('/register-teacher', methods=['GET', 'POST'])
def register_teacher():
    error = None
    success = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not username or not email or not password:
            error = "All fields are required."
        else:
            hashed_pw = generate_password_hash(password)
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)", 
                                   (username, hashed_pw, 'Teacher', email))
                    conn.commit()
                success = "Teacher account successfully created!"
            except sqlite3.IntegrityError:
                error = "Username or email already exists. Please pick a different name."
                
    content = '''
    <h1>Teacher Account Registration</h1>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if success %}<p style="color: #38a169;">{{ success }} <a href="/login">Login here</a></p>{% endif %}
    <form method="POST">
        <input type="text" name="username" placeholder="Full Name / Username (e.g. Mr. Moyo)" required>
        <input type="email" name="email" placeholder="Teacher Email Address (e.g. moyo@topspot.ac.zw)" required>
        <input type="password" name="password" id="reg_teacher_pw" placeholder="Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('reg_teacher_pw')" style="margin: 0; width: auto;"> Show Password
        </label>
        <button type="submit">Create Teacher Account</button>
    </form>
    '''
    return render_page(content, error=error, success=success)

@app.route('/register-parent', methods=['GET', 'POST'])
def register_parent():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email or not password:
            error = "All fields are required."
        else:
            hashed_pw = generate_password_hash(password)
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)", 
                                   (email, hashed_pw, 'Parent', email))
                    conn.commit()
                success = "Parent account created! Use your guardian email to log in."
            except sqlite3.IntegrityError:
                error = "An account with this email already exists."
                
    content = '''
    <h1>Parent Portal Registration</h1>
    <p style="color: var(--text-muted);">Register using your guardian email address provided during student enrollment to view your children's reports.</p>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if success %}<p style="color: #38a169;">{{ success }} <a href="/login">Login here</a></p>{% endif %}
    <form method="POST">
        <input type="email" name="email" placeholder="Guardian Email (e.g. parent@gmail.com)" required>
        <input type="password" name="password" id="reg_parent_pw" placeholder="Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('reg_parent_pw')" style="margin: 0; width: auto;"> Show Password
        </label>
        <button type="submit">Create Parent Account</button>
    </form>
    '''
    return render_page(content, error=error, success=success)

@app.route('/register-student', methods=['GET', 'POST'])
def register_student():
    error = None
    success = None
    if request.method == 'POST':
        name = request.form['name']
        admission_number = request.form['admission_number'].strip().upper()
        password = request.form['password']
        
        if not name or not admission_number or not password:
            error = "All fields including Admission Number are required."
        else:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT student_id, name FROM students WHERE admission_number = ?", (admission_number,))
                student = cursor.fetchone()
                
            if not student:
                error = "Student record not found. Please verify your exact Admission Number with administration."
            elif student[1].strip().lower() != name.strip().lower():
                error = "The provided name does not match our records for this admission number."
            else:
                hashed_pw = generate_password_hash(password)
                try:
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)", 
                                       (name, hashed_pw, 'Student', f"{admission_number.lower()}@student.topspot.ac.zw"))
                        conn.commit()
                    success = "Student portal account created successfully! You can now log in using your exact full name."
                except sqlite3.IntegrityError:
                    error = "An account already exists for this student profile."
                    
    content = '''
    <h1>Student Portal Registration</h1>
    <p style="color: var(--text-muted);">Register using your official student name and unique Admission Number.</p>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if success %}<p style="color: #38a169;">{{ success }} <a href="/login">Login here</a></p>{% endif %}
    <form method="POST">
        <input type="text" name="name" placeholder="Exact Full Name (e.g. John Doe)" required>
        <input type="text" name="admission_number" placeholder="Unique Admission Number (e.g. TS2026-001)" required>
        <input type="password" name="password" id="reg_student_pw" placeholder="Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('reg_student_pw')" style="margin: 0; width: auto;"> Show Password
        </label>
        <button type="submit">Create Student Account</button>
    </form>
    '''
    return render_page(content, error=error, success=success)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    info = None
    if request.method == 'POST':
        email = request.form['email']
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
        if user:
            code = str(random.randint(1000, 9999))
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET reset_code = ? WHERE email = ?", (code, email))
                conn.commit()
            
            email_subject = "Password Reset Code - Top Spot Academy"
            email_body = f"<p>Hello,</p><p>Your 4-digit code to reset your Top Spot Academy portal password is: <b>{code}</b></p>"
            send_email_notification(email, email_subject, email_body)

            info = f"A 4-digit security code has been successfully dispatched via email to <b>{email}</b>."
        else:
            error = "No user account is associated with this email address."
            
    content = '''
    <h1>Password Recovery</h1>
    <p style="color: var(--text-muted);">Enter your registered email address to receive a verification code.</p>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if info %}
        <div style="background: #ebf8ff; border: 1px solid #3182ce; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
            <p style="margin: 0; color: #2b6cb0;">{{ info | safe }}</p>
        </div>
        <p><a href="/verify-reset" style="font-weight: bold; color: var(--primary);">Proceed to enter 4-digit code &rsaquo;</a></p>
    {% else %}
        <form method="POST">
            <input type="email" name="email" placeholder="Your Registered Email" required>
            <button type="submit">Send 4-Digit Reset Code</button>
        </form>
    {% endif %}
    <p><a href="/login">Back to Login</a></p>
    '''
    return render_page(content, error=error, info=info)

@app.route('/verify-reset', methods=['GET', 'POST'])
def verify_reset():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form['email']
        code = request.form['code']
        new_password = request.form['new_password']
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT reset_code FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            
        if row and row[0] == code:
            hashed_pw = generate_password_hash(new_password)
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = ?, reset_code = NULL WHERE email = ?", (hashed_pw, email))
                conn.commit()
            success = "Your password has been successfully reset! You can now log in with your new password."
        else:
            error = "Invalid email or incorrect 4-digit verification code."
            
    content = '''
    <h1>Reset Password with Code</h1>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if success %}<p style="color: #38a169;">{{ success }} <a href="/login">Login here</a></p>{% endif %}
    <form method="POST">
        <input type="email" name="email" placeholder="Your Registered Email" required>
        <input type="text" name="code" placeholder="Enter 4-Digit Code" maxlength="4" required>
        <input type="password" name="new_password" id="reset_new_pw" placeholder="Enter New Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('reset_new_pw')" style="margin: 0; width: auto;"> Show Password
        </label>
        <button type="submit">Update Password</button>
    </form>
    <p><a href="/login">Back to Login</a></p>
    '''
    return render_page(content, error=error, success=success)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user' not in session or session.get('role') not in ['Teacher', 'Student'] and session.get('user') != 'Mr. Nyereyemhuka':
        return redirect(url_for('login'))
        
    username = session['user']
    error = None
    success = None
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
        if row and check_password_hash(row[0], current_password):
            hashed_pw = generate_password_hash(new_password)
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_pw, username))
                conn.commit()
            success = "Your password has been changed successfully!"
        else:
            error = "Incorrect current password provided."
            
    content = '''
    <h1>Change Password</h1>
    <p style="color: var(--text-muted);">Update your account security by providing your current password and choosing a new one.</p>
    {% if error %}<p style="color: #e53e3e;">{{ error }}</p>{% endif %}
    {% if success %}<p style="color: #38a169;">{{ success }}</p>{% endif %}
    <form method="POST">
        <input type="password" name="current_password" id="change_curr_pw" placeholder="Current Password" required>
        <input type="password" name="new_password" id="change_new_pw" placeholder="New Password" required>
        <label style="font-size: 13px; color: var(--text-muted); margin-bottom: 15px; display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="checkbox" onclick="togglePassword('change_curr_pw'); togglePassword('change_new_pw');" style="margin: 0; width: auto;"> Show Passwords
        </label>
        <button type="submit">Change Password</button>
    </form>
    '''
    return render_page(content, error=error, success=success)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/student-dashboard')
def student_dashboard():
    if 'user' not in session or session.get('role') != 'Student':
        return redirect(url_for('login'))
        
    student_name = session['user']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, admission_number, name, grade_level FROM students WHERE name = ?", (student_name,))
        student_record = cursor.fetchone()
        
    if not student_record:
        return "<h1>Student Profile Error</h1><p>No matching student record found for this username. <a href='/logout'>Logout</a></p>"
        
    student_id, admission_number, name, grade_level = student_record
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT teacher_name, term, performance_summary, grades, date_uploaded FROM reports WHERE student_id = ?", (student_id,))
        reports = cursor.fetchall()
        
        cursor.execute("SELECT day_of_week, period_number, subject, teacher FROM timetables WHERE grade_level = ? ORDER BY day_of_week, period_number", (grade_level,))
        timetable_slots = cursor.fetchall()
        
        subjects = sorted(list(set([slot[2] for slot in timetable_slots])))
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'Present'", (student_id,))
        days_present = cursor.fetchone()[0]

    content = f'''
    <h1>Student Dashboard - Welcome, {name}</h1>
    <p style="color: var(--text-muted);">Admission No: <b>{admission_number}</b> | Grade / Class: <b>{grade_level}</b> | Days Present: <b style="color: #38a169;">{days_present}</b></p>

    <div class="card-grid">
        <div class="dashboard-card">
            <h3>Attendance Status</h3>
            <p style="font-size: 26px; font-weight: bold; color: #38a169; margin: 5px 0;">{days_present} Days</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Marked present in register</p>
        </div>
        <div class="dashboard-card">
            <h3>Enrolled Subjects</h3>
            <p style="font-size: 26px; font-weight: bold; color: var(--primary); margin: 5px 0;">{len(subjects)} Subjects</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Active timetable modules</p>
        </div>
    </div>

    <h2>My Subjects</h2>
    <ul>
        {{% if subjects %}}
            {{% for sub in subjects %}}
            <li><b>{{{{sub}}}}</b></li>
            {{% endfor %}}
        {{% else %}}
            <p style="color: var(--text-muted);">No subjects scheduled for your grade level yet.</p>
        {{% endif %}}
    </ul>

    <h2>My Academic Results & Reports</h2>
    <table>
        <tr><th>Term</th><th>Teacher</th><th>Grades</th><th>Performance Summary</th><th>Date</th></tr>
        {{% if reports %}}
            {{% for r in reports %}}
            <tr>
                <td><b>{{{{r[1]}}}}</b></td>
                <td>{{{{r[0]}}}}</td>
                <td>{{{{r[3]}}}}</td>
                <td>{{{{r[2]}}}}</td>
                <td>{{{{r[4]}}}}</td>
            </tr>
            {{% endfor %}}
        {{% else %}}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No reports uploaded yet.</td></tr>
        {{% endif %}}
    </table>

    <h2 style="margin-top: 30px;">My Grade Timetable</h2>
    <table>
        <tr><th>Day</th><th>Period</th><th>Subject</th><th>Teacher</th></tr>
        {{% if timetable_slots %}}
            {{% for t in timetable_slots %}}
            <tr>
                <td><b>{{{{t[0]}}}}</b></td>
                <td>Period {{{{t[1]}}}}</td>
                <td>{{{{t[2]}}}}</td>
                <td>{{{{t[3]}}}}</td>
            </tr>
            {{% endfor %}}
        {{% else %}}
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No timetable assigned for your grade level yet.</td></tr>
        {{% endif %}}
    </table>

    <div style="margin-top: 25px;">
        <a href="/change-password" style="background: var(--primary); color: white; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">🔑 Change Password</a>
    </div>
    '''
    return render_page(content, reports=reports, timetable_slots=timetable_slots, subjects=subjects, days_present=days_present)

@app.route('/teacher-dashboard')
def teacher_dashboard():
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
    
    teacher_name = session['user']
    if session.get('role') == 'Admin':
        teacher_name = 'Mr. Nyereyemhuka'
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT timetable_id, grade_level, day_of_week, period_number, subject FROM timetables WHERE teacher = ? OR teacher = 'Sir Nyereyemhuka'", (teacher_name,))
        my_schedule = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM attendance GROUP BY status")
        att_counts = dict(cursor.fetchall())
        present_count = att_counts.get('Present', 0)
        absent_count = att_counts.get('Absent', 0)
        late_count = att_counts.get('Late', 0)

        cursor.execute("SELECT date, COUNT(*) FROM attendance GROUP BY date ORDER BY date LIMIT 7")
        trend_data = cursor.fetchall()
        trend_dates = [row[0] for row in trend_data]
        trend_counts = [row[1] for row in trend_data]

    if not trend_dates:
        trend_dates = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        trend_counts = [12, 19, 15, 22, 25]

    content = f'''
    <h1>Teacher & Admin Dashboard - Welcome, {session.get("user")}</h1>
    <p style="color: var(--text-muted);">Monitor class activities, schedules, and attendance metrics.</p>

    <div class="card-grid">
        <div class="dashboard-card">
            <h3>Enrolled Students</h3>
            <p style="font-size: 26px; font-weight: bold; color: var(--primary); margin: 5px 0;">{total_students}</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Total student body records</p>
        </div>
        <div class="dashboard-card">
            <h3>Portal Session</h3>
            <p style="color: #38a169; font-weight: bold; margin: 5px 0;">Active Connection</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Teacher / Admin Clearance Verified</p>
        </div>
    </div>

    <div class="charts-row">
        <div class="chart-container">
            <h3>Daily Engagement Trend</h3>
            <canvas id="progressLineChart"></canvas>
        </div>
        <div class="chart-container">
            <h3>Attendance Breakdown</h3>
            <canvas id="statusPieChart"></canvas>
        </div>
    </div>

    <h2>My Assigned Timetable Schedule</h2>
    <table>
        <tr><th>ID</th><th>Grade Level</th><th>Day</th><th>Period</th><th>Subject</th></tr>
        {{% if my_schedule %}}
            {{% for t in my_schedule %}}
            <tr><td>{{{{t[0]}}}}</td><td>{{{{t[1]}}}}</td><td>{{{{t[2]}}}}</td><td>{{{{t[3]}}}}</td><td>{{{{t[4]}}}}</td></tr>
            {{% endfor %}}
        {{% else %}}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No schedule slots assigned to you yet.</td></tr>
        {{% endif %}}
    </table>

    <script>
        const ctxLine = document.getElementById('progressLineChart').getContext('2d');
        new Chart(ctxLine, {{
            type: 'line',
            data: {{
                labels: {trend_dates},
                datasets: [{{
                    label: 'Logs Recorded',
                    data: {trend_counts},
                    borderColor: '#3182ce',
                    backgroundColor: 'rgba(49, 130, 206, 0.1)',
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true }} }} }}
        }});

        const ctxPie = document.getElementById('statusPieChart').getContext('2d');
        new Chart(ctxPie, {{
            type: 'doughnut',
            data: {{
                labels: ['Present', 'Absent', 'Late'],
                datasets: [{{
                    data: [{present_count}, {absent_count}, {late_count}],
                    backgroundColor: ['#38a169', '#e53e3e', '#d69e2e']
                }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
    </script>
    '''
    return render_page(content, my_schedule=my_schedule)

@app.route('/teacher-students')
def teacher_students():
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
        
    content = '''
    <h1>Manage Students</h1>
    <h2>Register New Student Record</h2>
    <form action="/teacher-add-student" method="POST">
        <input type="text" name="admission_number" placeholder="Admission Number (e.g. TS2026-001)" required>
        <input type="text" name="name" placeholder="Full Name" required>
        <input type="text" name="grade_level" placeholder="Grade Level / Class (e.g. Form 3)" required>
        <input type="date" name="dob" required>
        <input type="email" name="guardian_email" placeholder="Guardian Email" required>
        <input type="text" name="phone" placeholder="Phone Number" required>
        <button type="submit">Add Student Record</button>
    </form>

    <h2>Student Directory</h2>
    <table>
        <tr><th>ID</th><th>Admission No</th><th>Name</th><th>Grade/Class</th><th>DOB</th><th>Guardian Email</th><th>Phone</th><th>Actions</th></tr>
        {% for s in students %}
        <tr>
            <td>{{s[0]}}</td>
            <td><b>{{s[1]}}</b></td>
            <td>{{s[2]}}</td>
            <td>{{s[3]}}</td>
            <td>{{s[4]}}</td>
            <td>{{s[5]}}</td>
            <td>{{s[6]}}</td>
            <td>
                <a href="/edit-student/{{s[0]}}" style="color: var(--primary); text-decoration: none; font-weight: 600; margin-right: 10px;">✏️ Edit</a>
                <a href="/delete-student/{{s[0]}}" onclick="return confirm('Are you sure you want to delete this mistaken student record?');" style="color: #e53e3e; text-decoration: none; font-weight: 600;">🗑️ Delete</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, students=students)

@app.route('/teacher-add-student', methods=['POST'])
def teacher_add_student():
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
    
    admission_number = request.form['admission_number'].strip().upper()
    name = request.form['name']
    grade_level = request.form['grade_level']
    dob = request.form['dob']
    guardian_email = request.form['guardian_email']
    phone = request.form['phone']

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO students (admission_number, name, grade_level, dob, guardian_email, phone) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (admission_number, name, grade_level, dob, guardian_email, phone))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    return redirect(url_for('teacher_students'))

@app.route('/edit-student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if request.method == 'POST':
            admission_number = request.form['admission_number'].strip().upper()
            name = request.form['name']
            grade_level = request.form['grade_level']
            dob = request.form['dob']
            guardian_email = request.form['guardian_email']
            phone = request.form['phone']
            
            cursor.execute('''
                UPDATE students 
                SET admission_number = ?, name = ?, grade_level = ?, dob = ?, guardian_email = ?, phone = ?
                WHERE student_id = ?
            ''', (admission_number, name, grade_level, dob, guardian_email, phone, student_id))
            conn.commit()
            return redirect(url_for('teacher_students'))
            
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
    if not student:
        return "<h1>Student record not found</h1><p><a href='/teacher-students'>Back to students</a></p>"

    content = f'''
    <h1>Edit Student Record</h1>
    <form method="POST">
        <label>Admission Number:</label>
        <input type="text" name="admission_number" value="{student[1]}" required>
        <label>Full Name:</label>
        <input type="text" name="name" value="{student[2]}" required>
        <label>Grade Level / Class:</label>
        <input type="text" name="grade_level" value="{student[3]}" required>
        <label>Date of Birth:</label>
        <input type="date" name="dob" value="{student[4]}" required>
        <label>Guardian Email:</label>
        <input type="email" name="guardian_email" value="{student[5]}" required>
        <label>Phone Number:</label>
        <input type="text" name="phone" value="{student[6]}" required>
        <button type="submit">Update Student Record</button>
    </form>
    <p><a href="/teacher-students">Cancel & Return</a></p>
    '''
    return render_page(content, student=student)

@app.route('/delete-student/<int:student_id>')
def delete_student(student_id):
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM billing WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM reports WHERE student_id = ?", (student_id,))
        cursor.execute("DELETE FROM behavior_incidents WHERE student_id = ?", (student_id,))
        conn.commit()
        
    return redirect(url_for('teacher_students'))

@app.route('/teacher-reports', methods=['GET', 'POST'])
def teacher_reports():
    if not is_teacher_or_admin() and session.get('role') != 'Teacher':
        return redirect(url_for('login'))
        
    teacher_name = session['user']
    if session.get('role') == 'Admin':
        teacher_name = 'Mr. Nyereyemhuka'
        
    message = None
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        term = request.form['term']
        performance_summary = request.form['performance_summary']
        grades = request.form['grades']
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reports (student_id, teacher_name, term, performance_summary, grades, date_uploaded)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, teacher_name, term, performance_summary, grades, today))
            conn.commit()
        message = "Student progress report uploaded successfully!"

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, grade_level FROM students")
        students = cursor.fetchall()
        
        cursor.execute('''
            SELECT r.report_id, s.name, r.teacher_name, r.term, r.performance_summary, r.grades, r.date_uploaded
            FROM reports r JOIN students s ON r.student_id = s.student_id
        ''')
        reports = cursor.fetchall()

    content = '''
    <h1>Upload Student Progress Reports</h1>
    {% if message %}<p style="color: #38a169;">{{ message }}</p>{% endif %}
    <form method="POST">
        <select name="student_id" required>
            <option value="">Select Student</option>
            {% for s in students %}
            <option value="{{s[0]}}">{{s[1]}} ({{s[2]}})</option>
            {% endfor %}
        </select>
        <input type="text" name="term" placeholder="Term / Period (e.g. Term 1 2026)" required>
        <input type="text" name="grades" placeholder="Subject Grades Summary (e.g. Math: A, Science: B+)" required>
        <textarea name="performance_summary" placeholder="Detailed teacher comments and progress feedback..." rows="4" required></textarea>
        <button type="submit">Upload Report Card</button>
    </form>

    <h2>All Uploaded Reports</h2>
    <table>
        <tr><th>Student Name</th><th>Teacher</th><th>Term</th><th>Grades</th><th>Summary</th><th>Date</th></tr>
        {% for r in reports %}
        <tr>
            <td><b>{{r[1]}}</b></td>
            <td>{{r[2]}}</td>
            <td>{{r[3]}}</td>
            <td>{{r[5]}}</td>
            <td>{{r[4]}}</td>
            <td>{{r[6]}}</td>
        </tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, students=students, reports=reports, message=message)

@app.route('/behavior', methods=['GET', 'POST'])
def behavior():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    role = session.get('role')
    username = session.get('user')
    message = None
    
    if request.method == 'POST' and (is_teacher_or_admin() or role == 'Teacher'):
        student_id = request.form['student_id']
        incident_type = request.form['incident_type']
        description = request.form['description']
        reported_by = username
        today = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO behavior_incidents (student_id, reported_by, incident_type, description, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, reported_by, incident_type, description, today))
            conn.commit()
        message = "Behavior record logged successfully!"

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, name, grade_level FROM students")
        students = cursor.fetchall()
        
        if role == 'Student':
            cursor.execute("SELECT student_id FROM students WHERE name = ?", (username,))
            s_rec = cursor.fetchone()
            s_id = s_rec[0] if s_rec else -1
            cursor.execute('''
                SELECT b.incident_id, s.name, b.reported_by, b.incident_type, b.description, b.date_recorded
                FROM behavior_incidents b JOIN students s ON b.student_id = s.student_id
                WHERE b.student_id = ?
            ''', (s_id,))
        elif role == 'Parent':
            cursor.execute('''
                SELECT b.incident_id, s.name, b.reported_by, b.incident_type, b.description, b.date_recorded
                FROM behavior_incidents b JOIN students s ON b.student_id = s.student_id
                WHERE s.guardian_email = ?
            ''', (username,))
        else:
            cursor.execute('''
                SELECT b.incident_id, s.name, b.reported_by, b.incident_type, b.description, b.date_recorded
                FROM behavior_incidents b JOIN students s ON b.student_id = s.student_id
            ''')
        incidents = cursor.fetchall()

    content = '''
    <h1>Student Behavior & Conduct Tracking</h1>
    <p style="color: var(--text-muted);">Monitor and record positive recognitions or behavioral infractions.</p>
    '''

    if is_teacher_or_admin() or role == 'Teacher':
        content += '''
        {% if message %}<p style="color: #38a169;">{{ message }}</p>{% endif %}
        <h2>Log Behavior Record</h2>
        <form method="POST">
            <select name="student_id" required>
                <option value="">Select Student</option>
                {% for s in students %}
                <option value="{{s[0]}}">{{s[1]}} ({{s[2]}})</option>
                {% endfor %}
            </select>
            <select name="incident_type" required>
                <option value="">Select Type</option>
                <option value="Positive Recognition (Commendation)">Positive Recognition (Commendation)</option>
                <option value="Minor Infraction (Late/Uniform)">Minor Infraction (Late/Uniform)</option>
                <option value="Academic Warning">Academic Warning</option>
                <option value="Disciplinary Action">Disciplinary Action</option>
            </select>
            <textarea name="description" placeholder="Provide details regarding the incident or commendation..." rows="3" required></textarea>
            <button type="submit">Save Incident Record</button>
        </form>
        '''

    content += '''
    <h2>Recorded Behavior Logs</h2>
    <table>
        <tr><th>Student Name</th><th>Reported By</th><th>Type</th><th>Description</th><th>Date</th></tr>
        {% if incidents %}
            {% for i in incidents %}
            <tr>
                <td><b>{{i[1]}}</b></td>
                <td>{{i[2]}}</td>
                <td><span style="background: #edf2f7; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{{i[3]}}</span></td>
                <td>{{i[4]}}</td>
                <td>{{i[5]}}</td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No behavior records found.</td></tr>
        {% endif %}
    </table>
    '''
    return render_page(content, students=students, incidents=incidents, message=message)

@app.route('/parent-dashboard')
def parent_dashboard():
    if 'user' not in session or session.get('role') != 'Parent':
        return redirect(url_for('login'))
        
    parent_email = session['user']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, admission_number, name, grade_level FROM students WHERE guardian_email = ?", (parent_email,))
        my_children = cursor.fetchall()
        
        child_ids = [c[0] for c in my_children]
        reports = []
        if child_ids:
            placeholders = ','.join(['?'] * len(child_ids))
            cursor.execute(f'''
                SELECT s.name, r.teacher_name, r.term, r.performance_summary, r.grades, r.date_uploaded
                FROM reports r JOIN students s ON r.student_id = s.student_id
                WHERE r.student_id IN ({placeholders})
            ''', child_ids)
            reports = cursor.fetchall()

    content = '''
    <h1>Parent Portal - Children's Academic Reports</h1>
    <p style="color: var(--text-muted);">Viewing records linked to guardian email: <b>''' + parent_email + '''</b></p>

    <h2>My Children</h2>
    <table>
        <tr><th>Admission No</th><th>Name</th><th>Grade Level</th></tr>
        {% if my_children %}
            {% for c in my_children %}
            <tr><td>{{c[1]}}</td><td><b>{{c[2]}}</b></td><td>{{c[3]}}</td></tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="3" style="color: var(--text-muted);">No student records linked to this email address.</td></tr>
        {% endif %}
    </table>

    <h2 style="margin-top: 30px;">Term Reports & Progress Feedback</h2>
    <table>
        <tr><th>Student Name</th><th>Teacher</th><th>Term</th><th>Grades</th><th>Performance Summary</th><th>Date Uploaded</th></tr>
        {% if reports %}
            {% for r in reports %}
            <tr>
                <td><b>{{r[0]}}</b></td>
                <td>{{r[1]}}</td>
                <td>{{r[2]}}</td>
                <td>{{r[4]}}</td>
                <td>{{r[3]}}</td>
                <td>{{r[5]}}</td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="6" style="color: var(--text-muted);">No report cards uploaded yet for your children.</td></tr>
        {% endif %}
    </table>
    '''
    return render_page(content, my_children=my_children, reports=reports)

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'Teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'Parent':
        return redirect(url_for('parent_dashboard'))
    elif role == 'Student':
        return redirect(url_for('student_dashboard'))
    elif role == 'Finance':
        return redirect(url_for('finance'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = cursor.fetchall()
    
    content = '''
    <h1>Student Management Records</h1>
    <h2>Register New Student</h2>
    <form action="/add_student" method="POST">
        <input type="text" name="admission_number" placeholder="Admission Number (e.g. TS2026-001)" required>
        <input type="text" name="name" placeholder="Full Name" required>
        <input type="text" name="grade_level" placeholder="Grade Level (e.g. Form 3 / Grade 10)" required>
        <input type="date" name="dob" required>
        <input type="email" name="guardian_email" placeholder="Guardian Email" required>
        <input type="text" name="phone" placeholder="Phone Number" required>
        <button type="submit">Add Student Record</button>
    </form>

    <h2>Enrolled Students Directory</h2>
    <table>
        <tr><th>ID</th><th>Admission No</th><th>Name</th><th>Grade</th><th>DOB</th><th>Guardian Email</th><th>Phone</th><th>Actions</th></tr>
        {% for s in students %}
        <tr>
            <td>{{s[0]}}</td>
            <td><b>{{s[1]}}</b></td>
            <td>{{s[2]}}</td>
            <td>{{s[3]}}</td>
            <td>{{s[4]}}</td>
            <td>{{s[5]}}</td>
            <td>{{s[6]}}</td>
            <td>
                <a href="/edit-student/{{s[0]}}" style="color: var(--primary); text-decoration: none; font-weight: 600; margin-right: 10px;">✏️ Edit</a>
                <a href="/delete-student/{{s[0]}}" onclick="return confirm('Are you sure you want to delete this mistaken student record?');" style="color: #e53e3e; text-decoration: none; font-weight: 600;">🗑️ Delete</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, students=students)

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user' not in session or (session.get('role') == 'Student'):
        return redirect(url_for('login'))
    
    admission_number = request.form['admission_number'].strip().upper()
    name = request.form['name']
    grade_level = request.form['grade_level']
    dob = request.form['dob']
    guardian_email = request.form['guardian_email']
    phone = request.form['phone']

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO students (admission_number, name, grade_level, dob, guardian_email, phone) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (admission_number, name, grade_level, dob, guardian_email, phone))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    return redirect(url_for('index'))

@app.route('/finance')
def finance():
    if 'user' not in session or session.get('role') in ['Teacher', 'Student'] and session.get('user') != 'Mr. Nyereyemhuka':
        return redirect(url_for('login'))
    
    role = session.get('role')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, admission_number, name FROM students")
        students = cursor.fetchall()
        
        cursor.execute('''
            SELECT b.bill_id, s.student_id, s.admission_number, s.name, b.fee_type, b.description, b.amount_due, b.amount_paid, b.balance, b.status, b.due_date 
            FROM billing b JOIN students s ON b.student_id = s.student_id
            ORDER BY s.name, b.bill_id
        ''')
        ledger = cursor.fetchall()
        
        cursor.execute("SELECT transaction_id, type, category, amount, description, date, recorded_by FROM transactions ORDER BY date DESC")
        transactions = cursor.fetchall()
        
        # Calculate totals
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Income'")
        total_other_income = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT SUM(amount_paid) FROM billing")
        total_fee_income = cursor.fetchone()[0] or 0.0
        
        total_income = total_other_income + total_fee_income
        
        cursor.execute("SELECT SUM(amount) FROM transactions WHERE type = 'Expense'")
        total_expense = cursor.fetchone()[0] or 0.0
        
        net_balance = total_income - total_expense

    content = '''
    <h1>Finance, Income & Expenditure Dashboard</h1>
    
    <div class="card-grid">
        <div class="dashboard-card">
            <h3>Total Income</h3>
            <p style="font-size: 24px; font-weight: bold; color: #38a169; margin: 5px 0;">${{ "%.2f"|format(total_income) }}</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Fees + Other Income</p>
        </div>
        <div class="dashboard-card">
            <h3>Total Expenditure</h3>
            <p style="font-size: 24px; font-weight: bold; color: #e53e3e; margin: 5px 0;">${{ "%.2f"|format(total_expense) }}</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Operating expenses outlays</p>
        </div>
        <div class="dashboard-card">
            <h3>Net Balance</h3>
            <p style="font-size: 24px; font-weight: bold; color: var(--primary); margin: 5px 0;">${{ "%.2f"|format(net_balance) }}</p>
            <p style="color: var(--text-muted); font-size: 13px; margin: 0;">Income minus Expenditure</p>
        </div>
    </div>
    '''

    if role in ['Admin', 'Finance'] or session.get('user') == 'Mr. Nyereyemhuka':
        content += '''
        <h2>Record Income / Expense Transaction</h2>
        <form action="/save_transaction" method="POST">
            <select name="type" required>
                <option value="">Select Transaction Type</option>
                <option value="Income">Income (e.g. Donations, Grants, Hall Rental)</option>
                <option value="Expense">Expense (e.g. Utilities, Salaries, Maintenance)</option>
            </select>
            <input type="text" name="category" placeholder="Category Name (e.g. Salaries, Electricity, Donations)" required>
            <input type="number" step="0.01" name="amount" placeholder="Amount ($)" required>
            <input type="text" name="description" placeholder="Description / Details">
            <input type="date" name="date" required>
            <button type="submit">Save Financial Transaction</button>
        </form>
        
        <h2>1. Add New Fee Category / Bill for Student</h2>
        <form action="/save_bill" method="POST">
            <select name="student_id" required>
                <option value="">Select Student</option>
                {% for s in students %}
                <option value="{{s[0]}}">[{{s[1]}}] {{s[2]}}</option>
                {% endfor %}
            </select>
            
            <select name="fee_type" required>
                <option value="">Select Fee Category</option>
                <option value="School fees">School fees</option>
                <option value="Boarding fee">Boarding fee</option>
                <option value="Uniform fee">Uniform fee</option>
                <option value="Stationery fee">Stationery fee</option>
                <option value="Transport fee">Transport fee</option>
                <option value="Levy / Extra">Levy / Extra</option>
            </select>

            <input type="text" name="description" placeholder="Description / Details (e.g. Term 1 Boarding)">
            <input type="number" step="0.01" name="amount_due" placeholder="Fee Amount ($)" required>
            <input type="date" name="due_date" required>
            <button type="submit">Add Fee Bill Entry</button>
        </form>
        '''

    content += '''
    <h2>Record Payment / Pay Specific Bill Category</h2>
    <form action="/make_payment" method="POST">
        <select name="bill_id" required>
            <option value="">Select Specific Student Bill Category</option>
            {% for row in ledger %}
            <option value="{{row[0]}}">[{{row[2]}}] {{row[3]}} — {{row[4]}} (Due: ${{row[6]}}, Balance: ${{row[8]}})</option>
            {% endfor %}
        </select>
        <input type="number" step="0.01" name="payment_amount" placeholder="Payment Amount ($)" required>
        <button type="submit">Process Payment for Selected Category</button>
    </form>

    <h2>Other Income & Expenditure Log</h2>
    <table>
        <tr><th>Type</th><th>Category</th><th>Amount</th><th>Description</th><th>Date</th><th>Recorded By</th></tr>
        {% if transactions %}
            {% for tx in transactions %}
            <tr>
                <td><b><span style="color: {% if tx[1] == 'Income' %}#38a169{% else %}#e53e3e{% endif %};">{{tx[1]}}</span></b></td>
                <td>{{tx[2]}}</td>
                <td><b>${{ "%.2f"|format(tx[3]) }}</b></td>
                <td>{{tx[4]}}</td>
                <td>{{tx[5]}}</td>
                <td>{{tx[6]}}</td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No independent transactions logged yet.</td></tr>
        {% endif %}
    </table>

    <h2>Student Fee Accounts Ledger (Multi-Category)</h2>
    <table>
        <tr><th>Admission No</th><th>Student Name</th><th>Fee Category</th><th>Description</th><th>Total Due</th><th>Paid</th><th>Balance</th><th>Status</th><th>Invoice Actions</th></tr>
        {% if ledger %}
            {% for row in ledger %}
            <tr>
                <td><b>{{row[2]}}</b></td>
                <td>{{row[3]}}</td>
                <td><span style="background: #edf2f7; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{{row[4]}}</span></td>
                <td>{{row[5]}}</td>
                <td>${{ "%.2f"|format(row[6]) }}</td>
                <td>${{ "%.2f"|format(row[7]) }}</td>
                <td><b>${{ "%.2f"|format(row[8]) }}</b></td>
                <td>{{row[9]}}</td>
                <td>
                    <a href="/invoice/{{row[1]}}" style="color: var(--primary); text-decoration: none; font-weight: 600;">View Invoices</a>
                </td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No fee records found. Use the form above to add bills.</td></tr>
        {% endif %}
    </table>
    '''
    return render_page(content, students=students, ledger=ledger, transactions=transactions, total_income=total_income, total_expense=total_expense, net_balance=net_balance)

@app.route('/save_transaction', methods=['POST'])
def save_transaction():
    if 'user' not in session or (session.get('role') not in ['Admin', 'Finance'] and session.get('user') != 'Mr. Nyereyemhuka'):
        return redirect(url_for('login'))
        
    t_type = request.form['type']
    category = request.form['category']
    amount = float(request.form['amount'])
    description = request.form['description']
    date = request.form['date']
    recorded_by = session['user']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (type, category, amount, description, date, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (t_type, category, amount, description, date, recorded_by))
        conn.commit()
        
    return redirect(url_for('finance'))

@app.route('/save_bill', methods=['POST'])
def save_bill():
    if 'user' not in session or (session.get('role') not in ['Admin', 'Finance'] and session.get('user') != 'Mr. Nyereyemhuka'):
        return redirect(url_for('login'))
    
    student_id = request.form['student_id']
    fee_type = request.form['fee_type']
    description = request.form['description']
    amount_due = float(request.form['amount_due'])
    due_date = request.form['due_date']
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO billing (student_id, fee_type, description, amount_due, amount_paid, balance, status, due_date) 
                VALUES (?, ?, ?, ?, 0.0, ?, 'Unpaid', ?)
            ''', (student_id, fee_type, description, amount_due, amount_due, due_date))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
    return redirect(url_for('finance'))

@app.route('/make_payment', methods=['POST'])
def make_payment():
    if 'user' not in session or (session.get('role') not in ['Admin', 'Finance'] and session.get('user') != 'Mr. Nyereyemhuka'):
        return redirect(url_for('login'))
        
    bill_id = request.form['bill_id']
    payment_amount = float(request.form['payment_amount'])
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT amount_due, amount_paid, balance FROM billing WHERE bill_id = ?", (bill_id,))
        bill = cursor.fetchone()
        
        if bill:
            amount_due, current_paid, current_balance = bill
            new_paid = current_paid + payment_amount
            new_balance = max(0.0, current_balance - payment_amount)
            
            if new_balance == 0:
                status = "Paid"
            elif new_paid > 0:
                status = "Partial"
            else:
                status = "Unpaid"
                
            cursor.execute('''
                UPDATE billing 
                SET amount_paid = ?, balance = ?, status = ? 
                WHERE bill_id = ?
            ''', (new_paid, new_balance, status, bill_id))
            conn.commit()
            
    return redirect(url_for('finance'))

@app.route('/invoice/<int:student_id>')
def view_invoice(student_id):
    if 'user' not in session or session.get('role') == 'Student':
        return redirect(url_for('login'))
        
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, admission_number, name, grade_level, guardian_email, phone FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
        cursor.execute("SELECT fee_type, description, amount_due, amount_paid, balance, status, due_date FROM billing WHERE student_id = ?", (student_id,))
        bills = cursor.fetchall()
        
    if not student:
        return "<h1>Student not found</h1><p><a href='/finance'>Return to Finance</a></p>"

    total_due_sum = sum([b[2] for b in bills])
    total_paid_sum = sum([b[3] for b in bills])
    total_balance_sum = sum([b[4] for b in bills])

    content = '''
    <div style="background: white; padding: 40px; border-radius: 8px; border: 1px solid var(--sidebar-border); max-width: 750px; margin: auto;">
        <h2>''' + SCHOOL_NAME + ''' - Comprehensive Fee Statement</h2>
        <p><b>Student Name:</b> ''' + student[2] + ''' (Admission No: ''' + str(student[1]) + ''')</p>
        <p><b>Grade Level:</b> ''' + student[3] + ''' <span class="hide-on-print">| <b>Guardian Email:</b> ''' + str(student[4]) + '''</span></p>
        
        <table>
            <tr><th>Fee Category</th><th>Description</th><th>Due Date</th><th>Due ($)</th><th>Paid ($)</th><th>Balance ($)</th><th>Status</th></tr>
            {% if bills %}
                {% for b in bills %}
                <tr>
                    <td><b>{{b[0]}}</b></td>
                    <td>{{b[1]}}</td>
                    <td>{{b[6]}}</td>
                    <td>${{ "%.2f"|format(b[2]) }}</td>
                    <td>${{ "%.2f"|format(b[3]) }}</td>
                    <td><b>${{ "%.2f"|format(b[4]) }}</b></td>
                    <td>{{b[5]}}</td>
                </tr>
                {% endfor %}
            {% else %}
                <tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No bills issued for this student yet.</td></tr>
            {% endif %}
        </table>
        
        <div style="margin-top: 20px; background: #f7fafc; padding: 15px; border-radius: 6px; border: 1px solid #edf2f7;">
            <p style="margin: 0; font-size: 15px;"><b>Total Across All Categories:</b> Due: ${{ "%.2f"|format(total_due_sum) }} | Paid: ${{ "%.2f"|format(total_paid_sum) }} | <b>Outstanding Balance: ${{ "%.2f"|format(total_balance_sum) }}</b></p>
        </div>
        
        <br>
        <div style="display: flex; gap: 10px;" class="hide-on-print">
            <button onclick="window.print()" style="background: #38a169; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600;">🖨️ Print Invoice</button>
            <a href="/finance" style="background: #4a5568; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block; line-height: normal;">Back to Finance</a>
        </div>
    </div>
    '''
    return render_page(content, student=student, bills=bills, total_due_sum=total_due_sum, total_paid_sum=total_paid_sum, total_balance_sum=total_balance_sum)

@app.route('/attendance')
def attendance():
    if 'user' not in session or session.get('role') == 'Student':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, admission_number, name FROM students")
        students = cursor.fetchall()
        cursor.execute('''
            SELECT a.attendance_id, s.admission_number, s.name, a.date, a.status 
            FROM attendance a JOIN students s ON a.student_id = s.student_id
        ''')
        records = cursor.fetchall()

    content = '''
    <h1>Daily Attendance Register</h1>
    <h2>Mark Attendance</h2>
    <form action="/add_attendance" method="POST">
        <select name="student_id" required>
            <option value="">Select Student</option>
            {% for s in students %}
            <option value="{{s[0]}}">[{{s[1]}}] {{s[2]}}</option>
            {% endfor %}
        </select>
        <select name="status" required>
            <option value="Present">Present</option>
            <option value="Absent">Absent</option>
            <option value="Late">Late</option>
        </select>
        <button type="submit">Submit Attendance</button>
    </form>

    <h2>Attendance Log Records</h2>
    <table>
        <tr><th>ID</th><th>Admission No</th><th>Student Name</th><th>Date</th><th>Status</th></tr>
        {% for r in records %}
        <tr><td>{{r[0]}}</td><td><b>{{r[1]}}</b></td><td>{{r[2]}}</td><td>{{r[3]}}</td><td>{{r[4]}}</td></tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, students=students, records=records)

@app.route('/add_attendance', methods=['POST'])
def add_attendance():
    if 'user' not in session or session.get('role') == 'Student':
        return redirect(url_for('login'))
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)',
                       (request.form['student_id'], today, request.form['status']))
        conn.commit()
    return redirect(url_for('attendance'))

@app.route('/timetable')
def timetable():
    if 'user' not in session:
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM timetables")
        slots = cursor.fetchall()

    content = '''
    <h1>Class Timetable Manager</h1>
    <p style="color: var(--text-muted);">Daily Schedule Structure: Period 1 (07:30-08:25), Period 2 (08:25-09:20), Period 3 (09:20-10:15) | <b>Break (10:15-10:50)</b> | Period 4 (10:50-11:45), Period 5 (11:45-12:45), Period 6 (12:45-13:45)</p>
    '''
    if session.get('role') != 'Student':
        content += '''
        <h2>Add Schedule Slot</h2>
        <form action="/add_timetable" method="POST">
            <input type="text" name="grade_level" placeholder="Grade Level (e.g. Form 1)" required>
            <select name="day_of_week" required>
                <option value="Monday">Monday</option>
                <option value="Tuesday">Tuesday</option>
                <option value="Wednesday">Wednesday</option>
                <option value="Thursday">Thursday</option>
                <option value="Friday">Friday</option>
            </select>
            <input type="number" name="period_number" placeholder="Period Number (1 to 6)" required>
            <input type="text" name="subject" placeholder="Subject Name with Time (e.g. Mathematics (07:30 - 08:25))" required>
            <input type="text" name="teacher" placeholder="Teacher Name" required>
            <button type="submit">Add Timetable Slot</button>
        </form>
        '''

    content += '''
    <h2>Active School Timetables</h2>
    <table>
        <tr><th>ID</th><th>Grade</th><th>Day</th><th>Period</th><th>Subject</th><th>Teacher</th></tr>
        {% for t in slots %}
        <tr><td>{{t[0]}}</td><td>{{t[1]}}</td><td>{{t[2]}}</td><td>Period {{t[3]}}</td><td>{{t[4]}}</td><td>{{t[5]}}</td></tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, slots=slots)

@app.route('/add_timetable', methods=['POST'])
def add_timetable():
    if 'user' not in session or session.get('role') == 'Student':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO timetables (grade_level, day_of_week, period_number, subject, teacher) VALUES (?, ?, ?, ?, ?)',
                       (request.form['grade_level'], request.form['day_of_week'], request.form['period_number'], request.form['subject'], request.form['teacher']))
        conn.commit()
    return redirect(url_for('timetable'))

@app.route('/newsletters')
def newsletters():
    if 'user' not in session or (session.get('role') in ['Teacher', 'Student'] and session.get('user') != 'Mr. Nyereyemhuka'):
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM newsletters")
        news = cursor.fetchall()

    content = '''
    <h1>Newsletters & Parent Announcements</h1>
    <h2>Publish Notice</h2>
    <form action="/add_newsletter" method="POST">
        <input type="text" name="title" placeholder="Notice Title" required>
        <textarea name="content" placeholder="Type your full announcement or newsletter details here..." rows="4" required></textarea>
        <input type="text" name="target_audience" placeholder="Target Audience (e.g. Form 4 Parents, All Staff)" required>
        <button type="submit">Publish Notice</button>
    </form>

    <h2>Published Circulars</h2>
    <table>
        <tr><th>ID</th><th>Title</th><th>Content</th><th>Audience</th><th>Date Published</th></tr>
        {% for n in news %}
        <tr><td>{{n[0]}}</td><td>{{n[1]}}</td><td>{{n[2]}}</td><td>{{n[3]}}</td><td>{{n[4]}}</td></tr>
        {% endfor %}
    </table>
    '''
    return render_page(content, news=news)

@app.route('/add_newsletter', methods=['POST'])
def add_newsletter():
    if 'user' not in session or (session.get('role') in ['Teacher', 'Student'] and session.get('user') != 'Mr. Nyereyemhuka'):
        return redirect(url_for('login'))
    today = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO newsletters (title, content, target_audience, date_published) VALUES (?, ?, ?, ?)',
                       (request.form['title'], request.form['content'], request.form['target_audience'], today))
        conn.commit()
    return redirect(url_for('newsletters'))

@app.route('/elearning')
def elearning():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT resource_id, title, subject, grade_level, filename, uploaded_by, date_uploaded FROM elearning")
        resources = cursor.fetchall()

    content = '''
    <h1>E-Learning & Textbook Library</h1>
    <p style="color: var(--text-muted);">Access study materials, course notes, and downloadable textbook PDFs.</p>
    '''

    if role in ['Teacher', 'Admin'] or is_teacher_or_admin():
        content += '''
        <h2>Upload Textbook or Study Material</h2>
        <form action="/upload_resource" method="POST" enctype="multipart/form-data">
            <input type="text" name="title" placeholder="Resource Title (e.g. Form 3 Mathematics Guide)" required>
            <input type="text" name="subject" placeholder="Subject (e.g. Mathematics)" required>
            <input type="text" name="grade_level" placeholder="Grade Level (e.g. Form 3)" required>
            <label style="font-size: 13px; color: var(--text-muted); display: block; margin-bottom: 5px;">Upload Document / PDF File:</label>
            <input type="file" name="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt" required>
            <button type="submit">Upload Resource</button>
        </form>
        '''

    content += '''
    <h2>Available Library Resources</h2>
    <table>
        <tr><th>Title</th><th>Subject</th><th>Grade</th><th>Uploaded By</th><th>Date</th><th>Action</th></tr>
        {% if resources %}
            {% for r in resources %}
            <tr>
                <td><b>{{r[1]}}</b></td>
                <td>{{r[2]}}</td>
                <td>{{r[3]}}</td>
                <td>{{r[5]}}</td>
                <td>{{r[6]}}</td>
                <td><a href="/download_resource/{{r[0]}}" style="color: var(--primary); text-decoration: none; font-weight: 600;">📥 Download File</a></td>
            </tr>
            {% endfor %}
        {% else %}
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No e-learning materials uploaded yet.</td></tr>
        {% endif %}
    </table>
    '''
    return render_page(content, resources=resources)

@app.route('/upload_resource', methods=['POST'])
def upload_resource():
    if 'user' not in session or session.get('role') == 'Student':
        return redirect(url_for('login'))
        
    title = request.form['title']
    subject = request.form['subject']
    grade_level = request.form['grade_level']
    uploaded_by = session['user']
    today = datetime.now().strftime("%Y-%m-%d")
    
    file = request.files.get('file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file_path_save = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path_save)
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO elearning (title, subject, grade_level, filename, uploaded_by, date_uploaded)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, subject, grade_level, filename, uploaded_by, today))
            conn.commit()
            
    return redirect(url_for('elearning'))

@app.route('/download_resource/<int:resource_id>')
def download_resource(resource_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    with sqlite3.connect(DB_NAME) as cnt:
        cursor = cnt.cursor()
        cursor.execute("SELECT filename FROM elearning WHERE resource_id = ?", (resource_id,))
        record = cursor.fetchone()
        
    if record:
        filename = record[0]
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)

