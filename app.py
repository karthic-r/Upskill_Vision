import matplotlib
matplotlib.use("Agg")  # Fixes Matplotlib GUI issue
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import io
import base64
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
import os
import sqlite3
import smtplib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import jsonify
import plotly.graph_objs as go
import plotly.io as pio
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = 'your_secret_key_here'

DATABASE = 'upskill_vision.db'

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '211422104211.cse@gmail.com'  # Change this
app.config['MAIL_PASSWORD'] = 'tbky gbsh tiks kkqr'  # Use an App Password
app.config['MAIL_DEFAULT_SENDER'] = '211422104211.cse@gmail.com'  # Change this

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# 🔒 Session Configuration
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Use only if HTTPS is enabled
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Session Timeout Configuration (15 minutes)
SESSION_TIMEOUT = 900  

# Account Lockout Configuration
MAX_FAILED_ATTEMPTS = 5  
LOCKOUT_DURATION = 600  # 10 minutes

# Dictionary to track failed login attempts
failed_attempts = {}


UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Function to validate password strength
def is_strong_password(password):
    if (len(password) < 8 or
        not re.search(r'[A-Z]', password) or
        not re.search(r'[a-z]', password) or
        not re.search(r'[0-9]', password) or
        not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
        return False
    return True

# Before request: Session Management
@app.before_request
def session_management():
    if 'user' in session:
        if 'last_activity' in session:
            elapsed_time = time.time() - session['last_activity']
            if elapsed_time > SESSION_TIMEOUT:
                session.clear()
                flash("Your session has expired due to inactivity. Please log in again.", "error")
                return redirect(url_for('login'))
        session['last_activity'] = time.time()

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Signup Page with Email Verification
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # role = request.form.get('role', 'user')  

        if not is_strong_password(password):
            flash("Error: Password must be strong (8+ chars, uppercase, lowercase, number, special char).", "error")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password, role, is_verified, approval_status) VALUES (?, ?, ?, ?, ?, ?)", 
                (name, email, hashed_password, 'user', 0, 'pending')
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Error: Email already exists!", "error")
            return redirect(url_for('signup'))
        finally:
            conn.close()

        # Generate email verification token
        token = serializer.dumps(email, salt='email-confirmation')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        subject = "Email Confirmation - Verify Your Account"
        message_body = f"Hi {name},\n\nPlease click the link below to verify your email:\n{confirm_url}\n\nThank you!"
        send_email(email, subject, message_body)

        flash("A confirmation email has been sent.", "success")
        return redirect(url_for('signup'))

    return render_template('signup.html')

# Function to send email
def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print("Email failed to send:", e)

# Confirm Email Route
@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirmation', max_age=3600)
    except:
        flash("The confirmation link is invalid or has expired.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

    flash("Email verified successfully! You can now log in.", "success")
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    global failed_attempts

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash("Error: No account found with this email.", "error")
            return redirect(url_for('login'))

        if not user['is_verified']:
            flash("Error: Please verify your email before logging in.", "error")
            return redirect(url_for('login'))

        if user['approval_status'] in ['pending', 'rejected']:
            flash("Error: Your account is not approved yet.", "error")
            return redirect(url_for('login'))

        # Lockout mechanism
        if email in failed_attempts and failed_attempts[email]['count'] >= MAX_FAILED_ATTEMPTS:
            lockout_time = time.time() - failed_attempts[email]['timestamp']
            if lockout_time < LOCKOUT_DURATION:
                flash("Too many failed attempts. Please try again later.", "error")
                return redirect(url_for('login'))
            else:
                del failed_attempts[email]  # Reset after lockout

        if check_password_hash(user['password'], password):
            session['user'] = user['name']
            session['role'] = user['role']
            session['last_activity'] = time.time()
            session['user_email'] = user['email']  # ✅ Fix: Store as user_email
            session['user_id'] = user['id']  # ✅ Store user ID for easier access
            session.modified = True

            # Regenerate session ID
            session.permanent = True

            if email in failed_attempts:
                del failed_attempts[email]  

            if user['role'] == 'user':
                return redirect(url_for('user_dashboard'))
            elif user['role'] == 'instructor':
                return redirect(url_for('instructor_dashboard'))

        # Failed login attempt tracking
        if email not in failed_attempts:
            failed_attempts[email] = {'count': 1, 'timestamp': time.time()}
        else:
            failed_attempts[email]['count'] += 1
            failed_attempts[email]['timestamp'] = time.time()

        flash("Invalid credentials. Try again!", "error")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))

# Forgot Password Page
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash("Error: Email not registered.", "error")
            return redirect(url_for('forgot_password'))

        token = serializer.dumps(email, salt='password-reset')

        reset_url = url_for('reset_password', token=token, _external=True)
        subject = "Password Reset Request"
        message_body = f"Hi,\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email."

        send_email(email, subject, message_body)

        flash("A password reset link has been sent to your email.", "success")
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except:
        flash("The password reset link is invalid or has expired.", "error")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("Error: Passwords do not match.", "error")
            return redirect(url_for('reset_password', token=token))

        if not is_strong_password(new_password):
            flash("Error: Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character.", "error")
            return redirect(url_for('reset_password', token=token))

        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
        conn.commit()
        conn.close()

        flash("Your password has been reset successfully. You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)
def get_user_data(user_id):
    conn = sqlite3.connect("upskill_vision.db")
    cursor = conn.cursor()
    
    # Fetch user's enrolled courses with progress and status
    cursor.execute("SELECT c.id, c.title, e.status, e.progress FROM enrollment e JOIN courses c ON e.course_id = c.id WHERE e.user_id = ?", (user_id,))
    courses = cursor.fetchall()

    conn.close()
    return courses

@app.route('/user_dashboard')
def user_dashboard():
    if 'user' in session and session.get('role') == 'user':
        user_id = session.get('user_id')
        courses = get_user_data(user_id)

        if not courses:
            return render_template("user_dashboard.html", name=session['user'], courses=[], graphJSON=None)

        # Extracting course details
        course_names = [course[1] for course in courses]
        progress = [course[3] for course in courses]  # Progress percentage
        statuses = [course[2] for course in courses]

        # Calculate completed vs in-progress courses
        completed_count = sum(1 for s in statuses if s == 'Completed')
        in_progress_count = sum(1 for s in statuses if s != 'Completed')

        # Create Pie Chart for Completion Breakdown
        pie_chart = go.Figure(data=[go.Pie(labels=["Completed", "In Progress"], values=[completed_count, in_progress_count], hole=0.3)])
        pie_chart.update_layout(title_text="Course Completion Breakdown", title_x=0.5)
        graphJSON = pio.to_json(pie_chart)

        return render_template("user_dashboard.html", name=session['user'], courses=courses, graphJSON=graphJSON)
    
    return redirect(url_for('login'))
@app.route('/user_courses')
def user_courses():
    if 'user_email' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    user_email = session.get('user_email')
    conn = get_db_connection()

    # Fetch user_id from users table
    user = conn.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
    
    if not user:
        conn.close()
        return "User not found. Please check if you're logged in with the correct email.", 404

    user_id = user["id"]

    # Fetch all courses with instructor name
    courses = conn.execute("""
        SELECT courses.*, users.name as instructor_name 
        FROM courses 
        JOIN users ON courses.instructor_id = users.id
    """).fetchall()

    # Fetch enrollments for the user
    enrollments = conn.execute("SELECT course_id, status FROM enrollment WHERE user_id = ?", (user_id,)).fetchall()

    # Fetch course ratings (average rating for each course)
    course_ratings = conn.execute("""
        SELECT course_id, ROUND(AVG(rate), 1) as avg_rating
        FROM feedback
        GROUP BY course_id
    """).fetchall()
    
    conn.close()

    # Convert course ratings into a dictionary for easy lookup
    course_ratings_dict = {row["course_id"]: row["avg_rating"] for row in course_ratings}
    enrolled_courses = {row['course_id']: row['status'].lower() for row in enrollments}

    courses_data = []
    for course in courses:
        status = "Not Enrolled"
        if course['id'] in enrolled_courses:
            status = "Completed" if enrolled_courses[course['id']] == "completed" else "Enrolled"
        
        image_path = course["image_path"] if course["image_path"] else "static/images/default.jpg"
        avg_rating = course_ratings_dict.get(course["id"], "No Ratings")
        
        if avg_rating != "No Ratings":
            stars = "⭐" * int(avg_rating) + "☆" * (5 - int(avg_rating))
            rating_display = f"{stars} ({avg_rating}/5)"
        else:
            rating_display = "No Ratings"

        courses_data.append({
            "id": course["id"],
            "title": course["title"],
            "description": course["description"],
            "duration": course["duration"],  # Added course duration
            "image": image_path,
            "status": status,
            "avg_rating": rating_display,
            "instructor": course["instructor_name"]
        })

    return render_template("user_courses.html", courses=courses_data)

# ✅ Route to Enroll in a Course
@app.route('/enroll/<int:course_id>')
def enroll_course(course_id):
    if 'user_email' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    user_email = session.get('user_email')
    conn = get_db_connection()
    
    # Get the user ID
    user = conn.execute("SELECT id FROM users WHERE email = ?", (user_email,)).fetchone()
    if not user:
        conn.close()
        return "User not found.", 404
    
    user_id = user["id"]

    # Check if already enrolled
    already_enrolled = conn.execute("SELECT * FROM enrollment WHERE user_id = ? AND course_id = ?", 
                                    (user_id, course_id)).fetchone()
    if already_enrolled:
        conn.close()
        return redirect(url_for('user_courses'))  # Already enrolled, return to courses page

    # Insert into enrollment table
    enrollment_date = datetime.now().strftime("%Y-%m-%d")
    conn.execute("INSERT INTO enrollment (user_id, course_id, status, progress, enrollment_date) VALUES (?, ?, ?, ?, ?)",
                 (user_id, course_id, "Enrolled", 0, enrollment_date))
    conn.commit()
    conn.close()
    
    return redirect(url_for('user_courses'))
@app.route('/view_course/<int:course_id>')
def view_course(course_id):
    if 'user_email' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Fetch course details including image_path and video_path
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return "Course not found", 404

    # Fetch modules and quizzes for the course
    modules = conn.execute("SELECT * FROM module WHERE course_id = ?", (course_id,)).fetchall()
    quizzes = conn.execute("SELECT * FROM quiz WHERE course_id = ?", (course_id,)).fetchall()

    # Fetch user_id based on session email
    user = conn.execute("SELECT id FROM users WHERE email = ?", (session['user_email'],)).fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    user_id = user['id']

    # Fetch enrollment details
    enrollment = conn.execute("SELECT status, progress FROM enrollment WHERE course_id = ? AND user_id = ?", 
                              (course_id, user_id)).fetchone()
    conn.close()

    # Default values if not enrolled
    status = "Not Enrolled"
    progress = 0
    course_completed = False

    if enrollment:
        status = enrollment['status']
        progress = enrollment['progress']
        course_completed = (status == 'Completed')

    # Extract module titles for 'What You Will Learn' section
    learning_outcomes = ", ".join([module['title'] for module in modules]) if modules else "No modules available."

    # Extract YouTube video ID from URL using corrected regex
    video_path = course['video_path'] if course['video_path'] else None
    youtube_id = None
    if video_path:
        match = re.search(r"(?:v=|youtu\.be/|embed/|v/|shorts/)([a-zA-Z0-9_-]{11})", video_path)
        if match:
            youtube_id = match.group(1)

    return render_template("user_modules.html", course=course, modules=modules, quizzes=quizzes, 
                           status=status, progress=progress, course_completed=course_completed, 
                           learning_outcomes=learning_outcomes, youtube_id=youtube_id)
@app.route('/certificate/<int:course_id>')
def certificate(course_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Fetch course title
    course = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        conn.close()
        return "Course not found", 404
    
    # Fetch user details
    user = conn.execute("SELECT id, name FROM users WHERE email = ?", (session['user_email'],)).fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    user_id, user_name = user['id'], user['name']

    # Check enrollment status
    enrollment = conn.execute("SELECT status FROM enrollment WHERE course_id = ? AND user_id = ?", 
                              (course_id, user_id)).fetchone()
    
    if not enrollment or enrollment['status'] != 'Completed':
        conn.close()
        return "You are not eligible to download the certificate.", 403

    # Check if certificate already exists
    certificate_data = conn.execute(
        "SELECT certificate_code, issue_date FROM certificate WHERE user_id = ? AND course_id = ?",
        (user_id, course_id)
    ).fetchone()

    if certificate_data:
        # Certificate already exists, fetch details
        certificate_code, issue_date = certificate_data['certificate_code'], certificate_data['issue_date']
    else:
        # Fetch the last certificate code and generate next one
        last_certificate = conn.execute("SELECT certificate_code FROM certificate ORDER BY id DESC LIMIT 1").fetchone()
        
        if last_certificate and last_certificate["certificate_code"].startswith("USV"):
            last_number = int(last_certificate["certificate_code"][3:])  # Extract number part
            next_number = last_number + 1  # Increment by 1
        else:
            next_number = 101  # Start from 101 if table is empty

        certificate_code = f"USV{next_number}"

        # Issue date (Dynamically fetch current date)
        from datetime import datetime
        issue_date = datetime.today().strftime('%Y-%m-%d')

        # Insert new certificate details
        conn.execute("INSERT INTO certificate (certificate_code, user_id, course_id, issue_date) VALUES (?, ?, ?, ?)",
                     (certificate_code, user_id, course_id, issue_date))
        conn.commit()

    conn.close()

    # Generate and return the certificate
    certificate_path = generate_certificate(user_name, course['title'], certificate_code, issue_date)
    return send_file(certificate_path, as_attachment=True)
def generate_certificate(user_name, course_title, certificate_code, issue_date):
    template_path = "static/certificate_template.png"
    font_path_bold = "static/fonts/ARLRDBD.ttf"
    font_path_regular = "static/fonts/arial.ttf"
    output_path = f"static/certificates/{user_name}_{course_title}.png"

    # Ensure font files exist
    try:
        font_name = ImageFont.truetype(font_path_bold, 40)  # Larger font for name
        font_course = ImageFont.truetype(font_path_regular, 25)  # Medium font for course title
        font_small = ImageFont.truetype(font_path_regular, 35)  # Smaller font for completion text
        font_code = ImageFont.truetype(font_path_regular, 25)  # Font for certificate code
    except OSError:
        print("Font file not found! Using default font.")
        font_name = font_course = font_small = font_code = ImageFont.load_default()

    # Open the certificate template
    img = Image.open(template_path).convert("RGB")  # Convert to RGB mode
    draw = ImageDraw.Draw(img)

    # Define positions
    name_position = (640, 480)  # Below 'proudly presented to'
    course_position = (630, 600)  # Below 'For completing the'
    code_position = (230, 23)  # Top-left corner for certificate code
    date_position = (580, 643)  # Issue date position

    # Center the text dynamically
    def draw_centered_text(draw, text, position, font, fill="black"):
        bbox = draw.textbbox((0, 0), text, font=font)  # Get bounding box
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        centered_position = (position[0] - text_width // 2, position[1])
        draw.text(centered_position, text, fill=fill, font=font)

    # Add text dynamically centered
    draw_centered_text(draw, user_name, name_position, font_name)
    draw_centered_text(draw, course_title, course_position, font_course)

    # Add certificate code and issue date
    draw.text(code_position, f" {certificate_code}", fill="black", font=font_code)
    draw.text(date_position, f" {issue_date}", fill="black", font=font_code)

    # Save the generated certificate
    os.makedirs("static/certificates", exist_ok=True)
    img.save(output_path)

    return output_path
@app.route('/quiz/<int:course_id>', methods=['GET', 'POST'])
def quiz(course_id):
    if 'user_email' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    user_id = session.get('user_id')  # Get logged-in user ID
    conn = get_db_connection()

    # Fetch course and quizzes
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    quizzes = conn.execute("SELECT * FROM quiz WHERE course_id = ?", (course_id,)).fetchall()

    if not course:
        conn.close()
        return "Course not found", 404

    score = None
    status = None

    if request.method == 'POST' and 'quiz_submission' in request.form:
        user_answers = request.form
        score = 0
        total_questions = len(quizzes)

        for quiz in quizzes:
            question_id = str(quiz["id"])
            correct_answer_key = quiz["correct_answer"].strip().upper()
            options = [opt.strip() for opt in quiz["options"].split(",")]
            answer_mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            correct_answer_text = options[answer_mapping[correct_answer_key]] if correct_answer_key in answer_mapping else None
            user_answer = user_answers.get(question_id, '').strip()

            if correct_answer_text and user_answer.lower() == correct_answer_text.lower():
                score += int(quiz["points"])

        passing_score = total_questions * 0.5
        status = "Passed" if score >= passing_score else "Failed"
        attempt_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert quiz attempt
        conn.execute("""
            INSERT INTO quiz_attempt (course_id, user_id, attempt_date, score, status)
            VALUES (?, ?, ?, ?, ?)
        """, (course_id, user_id, attempt_date, score, status))
        conn.commit()

        # Update progress after quiz attempt
        update_user_progress(user_id, course_id, conn)

        conn.close()
        return render_template("quiz.html", course=course, quizzes=quizzes, score=score, status=status)
    
    conn.close()
    return render_template("quiz.html", course=course, quizzes=quizzes, score=score, status=status)


def update_user_progress(user_id, course_id, conn):
    """
    Dynamically calculates the progress of a user in a course based on quiz attempts.
    Progress is calculated as (Best attempt score / Total possible score) * 100.
    """

    # Get total possible score for the course
    total_score_row = conn.execute("""
        SELECT COALESCE(SUM(q.points), 0) 
        FROM quiz q
        WHERE q.course_id = ?
    """, (course_id,)).fetchone()
    
    total_score = total_score_row[0]

    if total_score == 0:
        progress, status = 0, "Enrolled"
    else:
        # Get user's highest score for the course
        user_score_row = conn.execute("""
            SELECT COALESCE(MAX(qa.score), 0)
            FROM quiz_attempt qa
            WHERE qa.course_id = ? AND qa.user_id = ?
        """, (course_id, user_id)).fetchone()
        
        user_score = user_score_row[0]

        # Calculate progress percentage
        progress = round((user_score / total_score) * 100) if total_score else 0

        # Determine status based on progress
        if progress == 0:
            status = "Enrolled"
        elif progress >= 100:
            status = "Completed"
        else:
            status = "In Progress"

    # Debugging output
    print(f"User: {user_id}, Course: {course_id}, User Score: {user_score}, Total Score: {total_score}, Progress: {progress}, Status: {status}")

    # Update enrollment table
    conn.execute(
        "UPDATE enrollment SET progress = ?, status = ? WHERE user_id = ? AND course_id = ?",
        (progress, status, user_id, course_id)
    )
    conn.commit()
@app.route('/feedback/<int:course_id>', methods=['POST'])
def feedback(course_id):
    if 'user_email' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    rating = request.form.get("rating")
    
    if rating:
        feedback_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Add current timestamp
        conn = get_db_connection()
        
        conn.execute("""
            INSERT INTO feedback (course_id, user_id, feedback_date, rate)
            VALUES (?, ?, ?, ?)
        """, (course_id, user_id, feedback_date, rating))  # Include feedback_date in insertion
        
        conn.commit()
        conn.close()
        flash("Thank you for your feedback!", "success")
    else:
        flash("Please select a rating before submitting.", "danger")
    
    return redirect(url_for('view_course', course_id=course_id))

def get_instructor_data(instructor_id, course_filter=None, date_range=None, user_filter=None):
    conn = sqlite3.connect("upskill_vision.db")
    cursor = conn.cursor()

    query = """
        SELECT c.id, c.title, e.user_id, e.progress, e.status, 
               COALESCE(AVG(q.score), 0) AS avg_score
        FROM courses c
        LEFT JOIN enrollment e ON c.id = e.course_id
        LEFT JOIN quiz_attempt q ON e.user_id = q.user_id AND e.course_id = q.course_id
        WHERE c.instructor_id = ?
    """
    params = [instructor_id]

    if course_filter:
        query += " AND c.id = ?"
        params.append(course_filter)
    
    if user_filter:
        query += " AND e.user_id = ?"
        params.append(user_filter)

    if date_range:
        query += " AND q.attempt_date BETWEEN ? AND ?"
        params.extend(date_range)

    query += " GROUP BY c.id, c.title, e.user_id"  

    cursor.execute(query, tuple(params))
    data = cursor.fetchall()
    
    conn.close()
    return data

@app.route('/instructor_dashboard', methods=['GET', 'POST'])
def instructor_dashboard():
    if 'user' in session and session.get('role') == 'instructor':
        instructor_id = session.get('user_id')

        conn = sqlite3.connect("upskill_vision.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id, title FROM courses WHERE instructor_id = ?", (instructor_id,))
        courses_list = cursor.fetchall()

        cursor.execute("SELECT DISTINCT user_id FROM enrollment WHERE course_id IN (SELECT id FROM courses WHERE instructor_id = ?)", (instructor_id,))
        users_list = cursor.fetchall()

        conn.close()
        
        course_filter = request.form.get('course')
        user_filter = request.form.get('user')
        date_range = None
        if request.form.get('start_date') and request.form.get('end_date'):
            date_range = (request.form.get('start_date'), request.form.get('end_date'))

        data = get_instructor_data(instructor_id, course_filter, date_range, user_filter)

        if not data:
            return render_template("instructor_dashboard.html", name=session['user'], graphJSON_pie=None, graphJSON_bar=None,
                                   total_enrolled=0, active_users=0, completed_users=0, avg_quiz_score=0, overall_completion_rate=0,
                                   courses_list=courses_list, users_list=users_list)

        courses = []
        quiz_scores = []
        completed_count = 0
        in_progress_count = 0
        total_enrolled = 0
        total_quiz_score = 0
        num_quiz_attempts = 0

        for row in data:
            course_id, course_title, user_id, progress, status, avg_score = row
            if course_title not in courses:
                courses.append(course_title)
                quiz_scores.append(avg_score)

            total_enrolled += 1
            if status == 'Completed':
                completed_count += 1
            else:
                in_progress_count += 1

            if avg_score > 0:
                total_quiz_score += avg_score
                num_quiz_attempts += 1

        avg_quiz_score = round(total_quiz_score / num_quiz_attempts, 2) if num_quiz_attempts > 0 else 0
        overall_completion_rate = round((completed_count / total_enrolled) * 100, 2) if total_enrolled > 0 else 0

        pie_chart = go.Figure(data=[go.Pie(labels=["Completed", "In Progress", "Enrolled"], 
                                           values=[completed_count, in_progress_count, total_enrolled], hole=0.3)])
        pie_chart.update_layout(title_text="Course Completion Breakdown", title_x=0.5)

        bar_chart = go.Figure(data=[go.Bar(x=courses, y=quiz_scores, marker_color='blue')])
        bar_chart.update_layout(title_text="Average Quiz Scores per Course", xaxis_title="Courses", yaxis_title="Avg Quiz Score")

        graphJSON_pie = pio.to_json(pie_chart)
        graphJSON_bar = pio.to_json(bar_chart)

        return render_template("instructor_dashboard.html", name=session['user'], graphJSON_pie=graphJSON_pie, graphJSON_bar=graphJSON_bar,
                               total_enrolled=total_enrolled, active_users=in_progress_count, completed_users=completed_count, 
                               avg_quiz_score=avg_quiz_score, overall_completion_rate=overall_completion_rate,
                               courses_list=courses_list, users_list=users_list)

    return redirect(url_for('login'))

@app.route('/instructor_courses')
def instructor_courses():
    if 'user' in session and session.get('role') == 'instructor':
        instructor_id = session.get('user_id')
        conn = sqlite3.connect("upskill_vision.db")
        cursor = conn.cursor()

        # Fetch users enrolled in instructor's courses along with progress
        query = """
            SELECT u.name, u.email, c.title, e.status, e.progress
            FROM users u
            JOIN enrollment e ON u.id = e.user_id
            JOIN courses c ON e.course_id = c.id
            WHERE c.instructor_id = ?
        """
        cursor.execute(query, (instructor_id,))
        courses_data = cursor.fetchall()

        conn.close()
        return render_template("instructor_courses.html", courses=courses_data, name=session['user'])

    return redirect(url_for('login'))

@app.route('/export_instructor_data')
def export_instructor_data():
    if 'user' in session and session.get('role') == 'instructor':
        instructor_id = session.get('user_id')

        conn = sqlite3.connect("upskill_vision.db")
        cursor = conn.cursor()

        # Fetch instructor name
        cursor.execute("SELECT name FROM users WHERE id = ?", (instructor_id,))
        instructor_name = cursor.fetchone()[0]

        # Fetch summary statistics
        instructor_data = get_instructor_data(instructor_id)
        courses = []
        quiz_scores = []
        completed_count = 0
        in_progress_count = 0
        total_enrolled = 0
        total_quiz_score = 0
        num_quiz_attempts = 0

        for row in instructor_data:
            course_id, course_title, user_id, progress, status, avg_score = row
            if course_title not in courses:
                courses.append(course_title)
                quiz_scores.append(avg_score)

            total_enrolled += 1
            if status == 'Completed':
                completed_count += 1
            else:
                in_progress_count += 1

            if avg_score > 0:
                total_quiz_score += avg_score
                num_quiz_attempts += 1

        avg_quiz_score = round(total_quiz_score / num_quiz_attempts, 2) if num_quiz_attempts > 0 else 0
        overall_completion_rate = round((completed_count / total_enrolled) * 100, 2) if total_enrolled > 0 else 0

        # Fetch My Assigned Courses with Users
        cursor.execute("""
            SELECT u.name, u.email, c.title, e.status, e.progress
            FROM users u
            JOIN enrollment e ON u.id = e.user_id
            JOIN courses c ON e.course_id = c.id
            WHERE c.instructor_id = ?
        """, (instructor_id,))
        assigned_courses_data = cursor.fetchall()

        conn.close()

        # Create DataFrames for Excel Export
        summary_df = pd.DataFrame([{
            "Instructor Name": instructor_name,
            "Instructor ID": instructor_id,
            "Total Enrollments": total_enrolled,
            "Active Users": in_progress_count,
            "Completed Users": completed_count,
            "Avg Quiz Score": avg_quiz_score,
            "Completion Rate (%)": overall_completion_rate
        }])

        course_completion_df = pd.DataFrame([{
            "Completed (%)": round((completed_count / total_enrolled) * 100, 2) if total_enrolled > 0 else 0,
            "In Progress (%)": round((in_progress_count / total_enrolled) * 100, 2) if total_enrolled > 0 else 0,
            "Enrolled (%)": 100
        }])

        quiz_scores_df = pd.DataFrame({
            "Course Name": courses,
            "Average Quiz Score": quiz_scores
        })

        assigned_courses_df = pd.DataFrame(assigned_courses_data, columns=["User Name", "User Email", "Course Name", "Status", "Progress (%)"])

        # Save to Excel File
        excel_filename = f"instructor_{instructor_id}_report.xlsx"
        excel_path = f"./static/{excel_filename}"

        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
            course_completion_df.to_excel(writer, sheet_name="Course Completion Breakdown", index=False)
            quiz_scores_df.to_excel(writer, sheet_name="Quiz Scores Per Course", index=False)
            assigned_courses_df.to_excel(writer, sheet_name="My Assigned Courses", index=False)

        return send_file(excel_path, as_attachment=True, download_name=excel_filename)

    return redirect(url_for('login'))

@app.route('/instructor_logout')
def instructor_logout():
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('home'))

# User Dashboard
@app.route('/user')
def user_page():
    if 'user' in session:
        return render_template('user.html', name=session['user'])
    return redirect(url_for('login'))

## Logout
#@app.route('/logout')
#def logout():
#    session.pop('user', None)
#    return redirect(url_for('home'))

# Admin Login Page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Default admin credentials
        admin_email = "admin@admin.com"
        admin_password = "admin@123"

        if email == admin_email and password == admin_password:
            session['admin'] = email
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials!", "danger")

    return render_template('admin_login.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

   # Fetch user statistics
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_users,
            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) AS total_learners,
            SUM(CASE WHEN role = 'instructor' THEN 1 ELSE 0 END) AS total_instructors,
            SUM(CASE WHEN approval_status = 'approved' THEN 1 ELSE 0 END) AS approved_users,
            SUM(CASE WHEN approval_status = 'pending' THEN 1 ELSE 0 END) AS pending_users,
            SUM(CASE WHEN approval_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_users
        FROM users
    """)
    stats = cursor.fetchone()
    total_users, total_learners, total_instructors, approved_users, pending_users, rejected_users = stats

    # Fetch course and enrollment details dynamically
    cursor.execute("SELECT COUNT(*) FROM courses")
    total_courses = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM enrollment")
    total_enrollments = cursor.fetchone()[0]

    # Fetch courses and users for filtering
    cursor.execute("SELECT id, title FROM courses")
    courses = cursor.fetchall()

    cursor.execute("SELECT id, email FROM users WHERE role = 'user'")
    users = cursor.fetchall()

    # Fetch filter inputs
    selected_course = request.form.get('course')
    selected_user = request.form.get('user')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    filters = []
    conditions = []

    if selected_course:
        conditions.append("c.id = ?")
        filters.append(selected_course)

    if selected_user:
        conditions.append("e.user_id = ?")
        filters.append(selected_user)

    if start_date and end_date:
        conditions.append("e.enrollment_date BETWEEN ? AND ?")
        filters.append(start_date)
        filters.append(end_date)

    # Query for course completion data
    completion_query = """
        SELECT c.title, 
               COUNT(e.user_id) AS total_enrolled, 
               SUM(CASE WHEN e.progress = 100 THEN 1 ELSE 0 END) AS completed_users 
        FROM courses c
        LEFT JOIN enrollment e ON c.id = e.course_id
    """

    if conditions:
        completion_query += " WHERE " + " AND ".join(conditions)
    
    completion_query += " GROUP BY c.title"

    df_completion = pd.read_sql_query(completion_query, conn, params=filters)

    # Generate Course Completion Plot
    fig_completion = px.bar(df_completion, x="completed_users", y="title", color="title", orientation="h",
                            title="Course Completion Rates", labels={"completed_users": "Completed Users"})
    
    completion_plot = fig_completion.to_html(full_html=False)

    # Fetch filter inputs
    selected_course = request.form.get('course')

    # Dynamic query for top performers per course
    top_performers_query = """
        SELECT 
            u.id AS user_id, 
            u.name, 
            u.email, 
            COUNT(DISTINCT e.course_id) AS completed_courses,  
            ROUND(COALESCE(AVG(qa.score), 0), 2) AS avg_score
        FROM users u
        LEFT JOIN enrollment e ON u.id = e.user_id 
        LEFT JOIN quiz_attempt qa ON u.id = qa.user_id
    """

    # Apply course filtering if selected
    filters = []
    if selected_course:
        top_performers_query += " WHERE e.course_id = ? AND e.progress = 100"
        filters.append(selected_course)
    else:
        top_performers_query += " WHERE e.progress = 100"

    top_performers_query += " GROUP BY u.id ORDER BY avg_score DESC LIMIT 5"
    # Fetch data into DataFrame
    df_top_performers = pd.read_sql_query(top_performers_query, conn, params=filters)

    df_top_performers["Rank"] = range(1, len(df_top_performers) + 1)
    
    rank_colors = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32", 4: "#2196F3", 5: "#F44336"}
    df_top_performers["Color"] = df_top_performers["Rank"].map(rank_colors)

    fig_top_performers = go.Figure()

    for _, row in df_top_performers.iterrows():
        rank_label = "🥇" if row["Rank"] == 1 else "🥈" if row["Rank"] == 2 else "🥉" if row["Rank"] == 3 else "🏅"
        
        fig_top_performers.add_trace(go.Scatter(
            x=[0],
            y=[-row["Rank"]],
            mode="markers+text",
            text=f"<b>{rank_label} {row['name']}</b><br><sub>{row['completed_courses']} courses, {int(row['avg_score'])}% avg. score</sub>",
            textposition="middle left",
            textfont=dict(size=18, color="black", family="Arial Black"),
            marker=dict(size=50, color=row["Color"], line=dict(width=2, color="white")),
            showlegend=False,
            hoverinfo="text",
            hovertext=f"{row['name']}: {row['completed_courses']} courses, {row['avg_score']}% avg. score"
        ))

    fig_top_performers.update_layout(
        title=f"🏆 <b>Top Performers Leaderboard ({'All Courses' if not selected_course else 'Selected Course'})</b>",
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="white",
    )

    top_performers_plot = fig_top_performers.to_html(full_html=False)

    

    # Query for users needing additional training
    low_performers_query = """
        SELECT u.email, e.progress
        FROM users u
        JOIN enrollment e ON u.id = e.user_id
        WHERE e.progress < 50
        ORDER BY e.progress ASC LIMIT 10
    """
    df_low_performers = pd.read_sql_query(low_performers_query, conn)

    fig_low_performers = px.bar(df_low_performers, x="progress", y="email", orientation="h",
                                title="Training Recommended", labels={"progress": "Progress (%)"})
    
    low_performers_plot = fig_low_performers.to_html(full_html=False)

        
   # Query to get Top Courses based on average rating
    top_courses_query = """
        SELECT c.title, ROUND(AVG(f.rate), 2) AS avg_rating
        FROM courses c
        LEFT JOIN feedback f ON c.id = f.course_id
        GROUP BY c.id
        ORDER BY avg_rating DESC, c.id ASC
        LIMIT 5
    """

    df_top_courses = pd.read_sql_query(top_courses_query, conn)

    # Ensure ranking is correct (1st = highest avg rating)
    df_top_courses = df_top_courses.sort_values(by="avg_rating", ascending=False).reset_index(drop=True)
    df_top_courses["Rank"] = df_top_courses.index + 1  # Assign ranks dynamically

    # Define correct rank labels dynamically
    rank_labels = {
        1: "🥇 1st",
        2: "🥈 2nd",
        3: "🥉 3rd",
        4: "🏅 4th",
        5: "🏅 5th"
    }
    df_top_courses["Rank_Label"] = df_top_courses["Rank"].map(rank_labels)

    # Combine Rank_Label and Course Title
    df_top_courses["Display_Label"] = df_top_courses["Rank_Label"] + " " + df_top_courses["title"]

    # Color Mapping for Medals (Gold, Silver, Bronze) and additional ranks
    course_rank_colors = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32", 4: "#2196F3", 5: "#F44336"}
    df_top_courses["Color"] = df_top_courses["Rank"].map(course_rank_colors)

    # Generate the leaderboard using Plotly
    fig_top_courses = go.Figure()

    for _, row in df_top_courses.iterrows():
        fig_top_courses.add_trace(go.Bar(
            x=[row["avg_rating"]],
            y=[row["Display_Label"]],  # Show rank + course title
            text=f"⭐ Avg. Rating: {row['avg_rating']}",
            textposition="auto",
            marker=dict(color=row["Color"]),
            orientation="h",
            hoverinfo="text",
        ))

    # Update layout for correct ranking display
    fig_top_courses.update_layout(
        title="🏆 <b>Top Courses Leaderboard</b>",
        xaxis_title="Average Rating",
        yaxis=dict(
            categoryorder="array",
            categoryarray=df_top_courses["Display_Label"][::-1],  # Ensure highest-rated appears first
            automargin=True
        ),
        height=400,
        margin=dict(l=120, r=20, t=50, b=40),
        plot_bgcolor="white",
        showlegend=False  # Hide legend
    )

    # Convert to HTML for display in web apps
    top_courses_plot = fig_top_courses.to_html(full_html=False)

    conn.close()

    # Return updated leaderboard
    return render_template(
        'admin_dashboard.html',
        admin_email=session['admin'],
        total_users=total_users,
        total_learners=total_learners,
        total_instructors=total_instructors,
        approved_users=approved_users,
        pending_users=pending_users,
        rejected_users=rejected_users,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        courses=courses,
        users=users,
        completion_plot=completion_plot,
        top_performers_plot=top_performers_plot,
        low_performers_plot=low_performers_plot,
        top_courses_plot=top_courses_plot  # Updated Top Courses Leaderboard
    )

@app.route('/export_excel', methods=['GET'])
def export_excel():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()

    # Fetch user and system statistics
    user_stats_query = """
        SELECT 
            COUNT(*) AS total_users,
            SUM(CASE WHEN role = 'user' THEN 1 ELSE 0 END) AS total_learners,
            SUM(CASE WHEN role = 'instructor' THEN 1 ELSE 0 END) AS total_instructors,
            SUM(CASE WHEN approval_status = 'approved' THEN 1 ELSE 0 END) AS approved_users,
            SUM(CASE WHEN approval_status = 'pending' THEN 1 ELSE 0 END) AS pending_users,
            SUM(CASE WHEN approval_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_users
        FROM users
    """
    user_stats = pd.read_sql_query(user_stats_query, conn)

    # Fetch total courses
    total_courses_query = "SELECT COUNT(*) AS total_courses FROM courses"
    total_courses = pd.read_sql_query(total_courses_query, conn)

    # Fetch total enrollments
    total_enrollments_query = "SELECT COUNT(*) AS total_enrollments FROM enrollment"
    total_enrollments = pd.read_sql_query(total_enrollments_query, conn)

    # Merge statistics into one DataFrame
    user_stats['total_courses'] = total_courses['total_courses'].iloc[0]
    user_stats['total_enrollments'] = total_enrollments['total_enrollments'].iloc[0]

    # Fetch course completion data
    completion_query = """
        SELECT c.title AS course_title, 
               COUNT(e.user_id) AS total_enrolled, 
               SUM(CASE WHEN e.progress = 100 THEN 1 ELSE 0 END) AS completed_users 
        FROM courses c
        LEFT JOIN enrollment e ON c.id = e.course_id
        GROUP BY c.title
    """
    df_completion = pd.read_sql_query(completion_query, conn)

    # Fetch top performers
    top_performers_query = """
        SELECT u.name, u.email, COUNT(e.course_id) AS completed_courses, 
               ROUND(COALESCE(AVG(qa.score), 0), 2) AS avg_score
        FROM users u
        JOIN enrollment e ON u.id = e.user_id
        LEFT JOIN quiz_attempt qa ON u.id = qa.user_id
        WHERE e.progress = 100
        GROUP BY u.id
        ORDER BY completed_courses DESC, avg_score DESC
        LIMIT 5
    """
    df_top_performers = pd.read_sql_query(top_performers_query, conn)

    # Fetch users needing additional training
    low_performers_query = """
        SELECT u.email, e.progress
        FROM users u
        JOIN enrollment e ON u.id = e.user_id
        WHERE e.progress < 50
        ORDER BY e.progress ASC LIMIT 10
    """
    df_low_performers = pd.read_sql_query(low_performers_query, conn)

    # Fetch top-rated courses
    top_courses_query = """
        SELECT c.title, ROUND(AVG(f.rate), 2) AS avg_rating
        FROM courses c
        LEFT JOIN feedback f ON c.id = f.course_id
        GROUP BY c.id
        ORDER BY avg_rating DESC, c.id ASC
        LIMIT 5
    """
    df_top_courses = pd.read_sql_query(top_courses_query, conn)

    conn.close()

    # Create an Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        user_stats.to_excel(writer, sheet_name="User Stats", index=False)
        df_completion.to_excel(writer, sheet_name="Course Completion", index=False)
        df_top_performers.to_excel(writer, sheet_name="Top Performers", index=False)
        df_low_performers.to_excel(writer, sheet_name="Low Performers", index=False)
        df_top_courses.to_excel(writer, sheet_name="Top Courses", index=False)

    output.seek(0)

    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="admin_dashboard_data.xlsx")
    # Logout for admin
@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/admin_users', methods=['GET'])
def admin_users():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, approval_status FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_users.html', users=users)


def send_email(to, subject, body):
    try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
    except Exception as e:
        print("Email failed to send:", e)

# Function to approve user
@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if user:  # Ensure user exists before proceeding
        cursor.execute("UPDATE users SET approval_status='approved' WHERE id=?", (user_id,))
        conn.commit()
        
        send_email(user['email'], "Account Approved", "Your account has been approved! You can now log in.")

    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/reject_user/<int:user_id>')
def reject_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if user:  # Ensure user exists before proceeding
        cursor.execute("UPDATE users SET approval_status='rejected' WHERE id=?", (user_id,))
        conn.commit()
        
        send_email(user['email'], "Account Rejected", "Your account has been rejected. Contact support for more details.")

    conn.close()
    return redirect(url_for('admin_users'))


# Show all users in a table format
@app.route('/all_users')
def all_users():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role, is_verified, approval_status FROM users")
    users = cursor.fetchall()
    conn.close()

    return render_template('all_users.html', users=users)
@app.route('/change_role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    new_role = request.form['role']  # 'user' or 'instructor'

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        cursor.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
        conn.commit()
        
        # Send notification email
        send_email(user['email'], "Role Updated", f"Your role has been updated to: {new_role}")

    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/terms')
def terms():
    return render_template('terms.html')

# Function to send email notification
def send_email_notification(course_title, description, start_date, end_date):
    conn = sqlite3.connect('upskill_vision.db')
    cur = conn.cursor()

    # Fetch all users' emails (both instructors and users)
    cur.execute("SELECT email FROM users WHERE role IN ( 'user')")
    recipients = [row[0] for row in cur.fetchall()] 
    conn.close()

    if not recipients:
        print("No users found to send email notifications.")
        return

    subject = f"New Course: {course_title} - Enrollment Open!"
    body = f"""
    Dear Users,

    A new course has been added to the platform:

    📌 **Course Title:** {course_title}
    📖 **Description:** {description}
    📅 **Start Date:** {start_date}
    🎯 **End Date:** {end_date}

    Please log in to the portal to enroll in the course.

    Regards,  
    Admin Team
    """

    try:
        msg = Message(subject, recipients=recipients, body=body)
        mail.send(msg)
        print("Email notifications sent successfully to all users!")
    except Exception as e:
        print(f"Failed to send emails: {e}")

# Function to fetch instructors 
def get_instructors():
    conn = sqlite3.connect('upskill_vision.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE LOWER(role) = 'instructor'")
    instructors = cur.fetchall()
    conn.close()
    return instructors

# Route to display Add Course form
@app.route('/add_course', methods=['GET'])
def add_course_form():
    instructors = get_instructors()
    return render_template('add_course.html', instructors=instructors)

@app.route('/add_course', methods=['POST'])
def add_course():
    try:
        course_title = request.form['course_title']
        description = request.form['description']
        instructor_id = request.form['instructor_id']
        start_date = request.form['start_date']
        duration = int(request.form['duration'])
        video_path = request.form['video_path']  # New video link input

        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        projected_end_date = start_dt + timedelta(weeks=duration)

        # Handle image upload
        image_file = request.files.get('course_image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_path = image_path.replace('\\', '/')  # Normalize path
        else:
            image_path = None

        # Save course details in the database
        conn = sqlite3.connect('upskill_vision.db')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO courses (title, description, duration, instructor_id, start_date, end_date, image_path, video_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (course_title, description, duration, instructor_id, start_date, projected_end_date.strftime("%Y-%m-%d"), image_path, video_path))
        conn.commit()
        conn.close()

        # Send email notification to members
        send_email_notification(course_title, description, start_date, projected_end_date.strftime("%Y-%m-%d"))

        flash("Course added successfully! Notifications sent.", "success")
        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        flash(f"Error adding course: {e}", "danger")
        return redirect(url_for('add_course_form'))

def get_courses():
    conn = sqlite3.connect('upskill_vision.db')
    cur = conn.cursor()
    
    # Fetching image_path for background image
    cur.execute("""
        SELECT c.id, c.title, c.description, c.duration, u.name, c.image_path 
        FROM courses c 
        LEFT JOIN users u ON c.instructor_id = u.id
    """)
    
    courses = cur.fetchall()
    conn.close()
    return courses

@app.route('/courses')
def courses():
    search_query = request.args.get('search', '').strip()
    courses = get_courses()

    if search_query:
        courses = [course for course in courses if search_query.lower() in course[1].lower()]

    return render_template('courses.html', courses=courses, search_query=search_query)
# Render the Add Module page for a specific course
@app.route('/add_module/<int:course_id>')
def add_module_page(course_id):
    return render_template('add_module.html', course_id=course_id)

# Get all modules for a given course (to populate the dropdown)
@app.route('/get_modules/<int:course_id>')
def get_modules(course_id):
    conn = get_db_connection()
    modules = conn.execute("SELECT * FROM module WHERE course_id = ?", (course_id,)).fetchall()
    conn.close()
    return jsonify([dict(module) for module in modules])

# Get details for a specific module by its ID
@app.route('/get_module/<int:module_id>')
def get_module(module_id):
    conn = get_db_connection()
    module = conn.execute("SELECT * FROM module WHERE id = ?", (module_id,)).fetchone()
    conn.close()
    if module is None:
        return jsonify({"error": "Module not found"}), 404
    return jsonify(dict(module))

# Insert a new module
@app.route('/add_module', methods=['POST'])
def add_module():
    data = request.json
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO module (course_id, title, content, learning_points) VALUES (?, ?, ?, ?)",
        (data['course_id'], data['title'], data['content'], data['learning_points'])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Module added successfully!"})

# Update an existing module by its module_id
@app.route('/update_module', methods=['POST'])
def update_module():
    data = request.json
    conn = get_db_connection()
    conn.execute(
        "UPDATE module SET title = ?, content = ?, learning_points = ? WHERE id = ?",
        (data['title'], data['content'], data['learning_points'], data['module_id'])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Module updated successfully!"})

# Delete a module by its module_id
@app.route('/delete_module/<int:module_id>', methods=['POST'])
def delete_module(module_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM module WHERE id = ?", (module_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Module deleted successfully!"})
# Route to render add_quiz.html
@app.route('/add_quiz/<int:course_id>')
def add_quiz(course_id):
    return render_template('add_quiz.html', course_id=course_id)

# API to fetch quizzes for a course (only quiz IDs)
@app.route('/get_quiz/<int:course_id>')
def get_quiz(course_id):
    conn = sqlite3.connect('upskill_vision.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM quiz WHERE course_id = ?", (course_id,))
    quizzes = [{'id': row[0]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(quizzes)

# API to fetch a single quiz by its ID
@app.route('/get_single_quiz/<int:quiz_id>')
def get_single_quiz(quiz_id):
    conn = sqlite3.connect('upskill_vision.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'id': row[0], 
            'question_text': row[2], 
            'options': row[3], 
            'correct_answer': row[4],
            'points': row[5]  # Added points field
        })
    else:
        return jsonify({"message": "Quiz not found"}), 404

# API to add a new quiz
@app.route('/add_quiz', methods=['POST'])
def add_quiz_question():
    data = request.json
    conn = sqlite3.connect('upskill_vision.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO quiz (course_id, question_text, options, correct_answer, points) VALUES (?, ?, ?, ?, ?)",
                   (data['course_id'], data['question_text'], data['options'], data['correct_answer'], data['points']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Quiz added successfully"})

# API to update a quiz
@app.route('/update_quiz', methods=['POST'])
def update_quiz():
    data = request.json
    conn = sqlite3.connect('upskill_vision.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE quiz SET question_text = ?, options = ?, correct_answer = ?, points = ? WHERE id = ?",
                   (data['question_text'], data['options'], data['correct_answer'], data['points'], data['quiz_id']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Quiz updated successfully"})

# API to delete a quiz
@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    conn = sqlite3.connect('upskill_vision.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quiz WHERE id = ?", (quiz_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Quiz deleted successfully"})
@app.route('/edit_course/<int:course_id>')
def edit_course(course_id):
    conn = sqlite3.connect('upskill_vision.db')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, title, description, duration, instructor_id, start_date, end_date, image_path, video_path 
        FROM courses WHERE id = ?
    """, (course_id,))
    course = cur.fetchone()

    cur.execute("SELECT id, name FROM users WHERE LOWER(role) = 'instructor'")
    instructors = cur.fetchall()
    
    conn.close()

    if not course:
        flash("Course not found", "danger")
        return redirect(url_for('courses'))

    return render_template('edit_course.html', course=course, instructors=instructors)

@app.route('/update_course', methods=['POST'])
def update_course():
    try:
        course_id = request.form['course_id']
        course_title = request.form['course_title']
        description = request.form['description']
        instructor_id = request.form['instructor_id']
        start_date = request.form['start_date']
        duration = int(request.form['duration'])
        projected_end_date = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(weeks=duration)
        video_path = request.form['video_path']  # New YouTube Video Field

        image_file = request.files.get('course_image')
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_path = image_path.replace('\\', '/')  # Normalize path
        else:
            image_path = request.form.get('current_image')

        conn = sqlite3.connect('upskill_vision.db')
        cur = conn.cursor()
        cur.execute("""
            UPDATE courses 
            SET title = ?, description = ?, instructor_id = ?, start_date = ?, duration = ?, end_date = ?, image_path = ?, video_path = ?
            WHERE id = ?
        """, (course_title, description, instructor_id, start_date, duration, projected_end_date.strftime("%Y-%m-%d"), image_path, video_path, course_id))

        conn.commit()
        conn.close()

        flash("Course updated successfully!", "success")
        return redirect(url_for('courses'))

    except Exception as e:
        flash(f"Error updating course: {e}", "danger")
        return redirect(url_for('edit_course', course_id=course_id))

@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    conn = sqlite3.connect('upskill_vision.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
    
