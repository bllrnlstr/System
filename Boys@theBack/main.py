from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from datetime import datetime
import secrets

class RecordManagementSystem:
    def __init__(self, name):
        self.app = Flask(name)
        self.setup_config()
        self.setup_routes()
        self.mysql = MySQL(self.app)

    def setup_config(self):
        self.app.config['MYSQL_HOST'] = "localhost"
        self.app.config['MYSQL_USER'] = "root"
        self.app.config['MYSQL_PASSWORD'] = ""
        self.app.config['MYSQL_DB'] = "rec_man_sys"
        self.app.secret_key = secrets.token_hex(16)

    def validate_user(self, username, password, role):
        with self.mysql.connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username=%s AND role=%s", (username, role))
            user = cursor.fetchone()
            if user and user[4] == password: 
                return user
        return None

    def insert_user(self, user_data):
        with self.mysql.connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (role, username, email, password) VALUES (%s, %s, %s, %s)",
                           (user_data['role'], user_data['username'], user_data['email'], user_data['password']))
            self.mysql.connection.commit()

    def insert_teacher_info(self, teacher_data):
        with self.mysql.connection.cursor() as cursor:
            cursor.execute("INSERT INTO teacher_info (name, sections) VALUES (%s, %s)", 
                           (teacher_data['name'], teacher_data['sections']))
            self.mysql.connection.commit()

    def setup_routes(self):
        @self.app.route("/")
        def home():
            return render_template("index.html")

        @self.app.route("/login", methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                user_type = request.form['user_type']
                username = request.form['username']
                password = request.form['password']

                user = self.validate_user(username, password, user_type)
                if user:
                    session['username'] = username
                    session['role'] = user_type
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for(f'{user_type}_dashboard'))
                else:
                    flash('Invalid username, password, or role', 'danger')

            return render_template('login.html')

        @self.app.route("/signup", methods=['GET', 'POST'])
        def signup():
            if request.method == 'POST':
                role = request.form['user_type']
                username = request.form['username']
                teacher_name = request.form['teacher_name']
                email = request.form['email']
                subjects = request.form['subject']
                sections = request.form['sections']
                password = request.form['password']
                confirm_password = request.form['confirm_password']

                if password != confirm_password:
                    flash('Passwords do not match', 'danger')
                    return redirect(url_for('signup'))

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        flash('Username already exists', 'danger')
                        return redirect(url_for('signup'))

                user_data = {
                    'role': role,
                    'username': username,
                    'email': email,
                    'password': password,
                }
                self.insert_user(user_data)

                teacher_data = {
                    'name': teacher_name,
                    'sections': sections,
                }
                self.insert_teacher_info(teacher_data)

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("SELECT teacher_id FROM teacher_info WHERE name = %s", (teacher_name,))
                    teacher_id = cursor.fetchone()
                    if teacher_id:
                        teacher_id = teacher_id[0] 
                        if subjects:
                            cursor.execute("INSERT INTO subjects (subject_name, teacher_id) VALUES (%s, %s)", (subjects, teacher_id))
                            self.mysql.connection.commit()
                flash('Account created successfully!', 'success')
                return redirect(url_for('login'))

            return render_template('signup.html')

        @self.app.route("/create_account", methods=["GET", "POST"])
        def create_account():
            if 'username' in session and session['role'] == 'admin':
                if request.method == 'POST':
                    username = request.form.get('username')
                    password = request.form.get('password')

                    with self.mysql.connection.cursor() as cursor:
                        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                        existing_user = cursor.fetchone()

                        if existing_user:
                            flash('Username already taken. Please choose another one.', 'warning')
                            return redirect(url_for('create_account'))
                        
                        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, 'student'))
                        self.mysql.connection.commit()
                        
                    flash('Account created successfully!', 'success')
                    return redirect(url_for('admin_dashboard'))
                return render_template("admin_dashboard.html")
            else:
                flash('Access denied', 'danger')
                return redirect(url_for('login'))

        @self.app.route("/teacher_dashboard")
        def teacher_dashboard():
            if 'username' in session and session['role'] == 'teacher':
                now = datetime.now()
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M:%S")

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM student_info")
                    total_students = cursor.fetchone()[0 ]

                    cursor.execute("SELECT * FROM lesson_plans WHERE teacher_id = %s", (session['username'],))
                    lesson_plans = cursor.fetchall()

                    cursor.execute("SELECT * FROM announcements WHERE teacher_id = %s", (session['username'],))
                    announcements = cursor.fetchall()

                    cursor.execute("SELECT * FROM deadlines WHERE teacher_id = %s", (session['username'],))
                    upcoming_deadlines = cursor.fetchall()

                    cursor.execute("SELECT * FROM events WHERE teacher_id = %s", (session['username'],))
                    upcoming_events = cursor.fetchall()

                return render_template(
                    'teacher_dashboard.html',
                    date=date,
                    time=time,
                    total_students=total_students,
                    lesson_plans=lesson_plans,
                    announcements=announcements,
                    upcoming_deadlines=upcoming_deadlines,
                    upcoming_events=upcoming_events
                )
            else:
                flash('Access denied', 'danger')
                return redirect(url_for('login'))

        @self.app.route("/student_dashboard")
        def student_dashboard():
            if 'username' in session and session['role'] == 'student':
                now = datetime.now()
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M:%S")

                section_id = session.get('section_id')
                if section_id is None:
                    flash('Section ID not found in session', 'danger')
                    return redirect(url_for('login'))

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("SELECT title, date, message FROM announcements")
                    announcements = cursor.fetchall()

                    cursor.execute("SELECT title, date FROM deadlines WHERE section_id = %s", (section_id,))
                    upcoming_deadlines = cursor.fetchall()

                    cursor.execute("SELECT title, date FROM events WHERE section_id = %s", (section_id,))
                    upcoming_events = cursor.fetchall()

                return render_template(
                    'student_dashboard.html',
                    date=date,
                    time=time,
                    announcements=announcements,
                    upcoming_deadlines=upcoming_deadlines,
                    upcoming_events=upcoming_events
                )
            else:
                flash('Access denied', 'danger')
                return redirect(url_for('login'))

        @self.app.route("/admin_dashboard")
        def admin_dashboard():
            if 'username' in session and session['role'] == 'admin':
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("SELECT * FROM users")
                    users = cursor.fetchall()

                    cursor.execute("SELECT stud_id, f_name, m_name, l_name, year_lvl, sections   FROM student_info")
                    students = cursor.fetchall()

                    cursor.execute("""
                        SELECT student_info.stud_id, student_info.f_name, student_info.m_name, student_info.l_name
                        FROM student_info WHERE student_info.user_id = 0  -- Select students with no accounts yet (user_id = 0)
                    """)
                    students_without_accounts = cursor.fetchall()

                    cursor.execute("SELECT * FROM teacher_info")
                    teachers = cursor.fetchall()

                    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'teacher'")
                    teacher_count = cursor.fetchone()[0]

                    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
                    student_count = cursor.fetchone()[0]

                    cursor.execute("SELECT * FROM sections")
                    all_sections = cursor.fetchall()

                    students_without_accounts = cursor.execute( "SELECT * FROM student_info WHERE user_id IS NULL")
                    students_without_accounts = cursor.fetchall() 

                return render_template(
                    'admin_dashboard.html',
                    users=users,
                    teacher_count=teacher_count,
                    student_count=student_count,
                    teachers=teachers,
                    all_sections=all_sections,
                    students=students, 
                    students_without_accounts=students_without_accounts  
                )
            else:
                 flash('Access denied', 'danger')
            return redirect(url_for('login'))

        @self.app.route("/students")
        def view_students():
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM student_info")
                students = cursor.fetchall()
            selected_section = request.args.get(' section')
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM student_info")
                students = cursor.fetchall ()
            students_by_section = {}
            for student in students:
                section = student[2]
                if section not in students_by_section:
                    students_by_section[section] = []
                students_by_section[section].append(student)

            return render_template('view_students.html', students=students, students_by_section=students_by_section)

        @self.app.route("/add-student", methods=['GET', 'POST'])
        def add_student():
            if request.method == 'POST':
                student_data = {
                    
                    'lrn_number ': request.form['lrn_number'],
                    'section': request.form['section'],
                    'first_name': request .form['f_name'],
                    'middle_name': request.form['m_name'],
                    'last_name': request.form['l_name'],
                    'suffix': request.form['suffix'],
                    'year_level': request.form['year_lvl'],
                    'course': request.form['course'],
                    'address': request.form['address'],
                    'age': request.form['age'],
                    ' emerg_name': request.form['emerg_name'],
                    'emerg_num': request.form['emerg_num'],
                    'emerg_address': request.form['emerg_address']
                }

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO student_info ( lrn_num, section, f_name, m_name, l_name, suffix, year_lvl, course, address, age, emerg_name, emerg_num, emerg_address) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        tuple(student_data.values())
                    )
                    self.mysql.connection.commit()

                flash('Student added successfully!', 'success')
                return redirect(url_for('view_students'))

            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")
            return render_template('add_student.html', date=date, time=time)

        @self.app.route('/view-grades')
        def view_grades():
            if 'username' in session and session['role'] == 'teacher':
                grades= []
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("""
    SELECT student_info.f_name, student_info.m_name, student_info.l_name, 
           student_scores.quiz_score, student_scores.attendance_score,
           student_scores.participation_score, student_scores.exam_score, 
           student_scores.total_score
    FROM student_info
    JOIN student_scores ON student_info.stud_id = student_scores.stud_id
""")
                    grades = cursor.fetchall()
                return render_template('view_grades.html', students=grades)
            else:
                 flash('Access denied', 'danger')
            return redirect(url_for('login'))

        @self.app.route("/edit-student/<int:id>", methods=['GET', 'POST'])
        def edit_student(id):
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM student_info WHERE stud_id = %s", (id,))
                student = cursor.fetchone()

                if request.method == 'POST':
                    student_data = {
                        'first_name': request.form['newf_name'],
                        'middle_name': request.form['newm_name'],
                        'last_name': request.form['new_lname'],
                        'suffix': request.form['new_suffix'],
                        'year_level': request.form['new_lvl'],
                        'course': request.form['new_course'],
                        'address': request.form['new_address'],
                        'age': request.form ['new_age'],
                        'emerg_name': request.form['new_emerg_name'],
                        'emerg_num': request.form['new_emerg_num'],
                        'emerg_address': request.form['new_emerg_address'],
                        'id': id
                    }

                    cursor.execute(
                        "UPDATE student_info SET f_name = %s, m_name = %s, l_name = %s, suffix = %s, year_lvl = %s, course = %s, address = %s, age = %s, emerg_name = %s, emerg_num = %s, emerg_address = %s WHERE stud_id = %s",
                        tuple(student_data.values())
                    )
                    self.mysql.connection.commit()

                    flash('Student updated successfully!', 'success')
                    return redirect(url_for('view_students'))

                now = datetime.now()
                date = now.strftime("%Y-%m-%d")
                time = now.strftime("%H:%M:%S")
                return render_template('edit.html', student=student, date=date, time=time)

        @self.app.route('/add_section', methods=['POST'])
        def add_section():
            new_section = request.form.get('new_section')
            if new_section:
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute('INSERT INTO sections (section_name) VALUES (%s)', (new_section,))
                    self.mysql.connection.commit()
                flash('New section added successfully!', 'success')
            else:
                flash('Section name cannot be empty!', 'danger')
            return redirect(url_for('input_student_scores'))

        @self.app.route("/delete-student/<int:id>", methods=['POST'])
        def delete_student(id):
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("DELETE FROM student_info WHERE stud_id = %s", (id,))
                self.mysql.connection.commit()

            flash('Student deleted successfully!', 'success')
            return redirect(url_for('view_students'))

        @self.app.route("/add-announcement", methods=['GET', 'POST'])
        def add_announcement():
            if request .method == 'POST':
                title = request.form['title']
                message = request.form['message']
                date = datetime.now().strftime("%Y-%m-%d")
                section_id = request.form['section_id']

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO announcements (title, message, date, teacher_id, section_id) VALUES (%s, %s, %s, %s, %s)",
                        (title, message, date, session['username'], section_id)
                    )
                    self.mysql.connection.commit()

                flash('Announcement added successfully!', 'success')
                return redirect(url_for('teacher_dashboard'))
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT sections FROM teacher_info")
                sections = cursor.fetchall()
            return render_template('add_announcement.html', sections=sections)

        @self.app.route("/add-event", methods=['GET', 'POST'])
        def add_event():
            if request.method == 'POST':
                title = request.form['title']
                event_date = request.form['event_date']

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO events (title, date, teacher_id) VALUES (%s, %s, %s)",
                        (title, event_date, session['username '])
                    )
                    self.mysql.connection.commit()

                flash('Event added successfully!', 'success')
                return redirect(url_for('teacher_dashboard'))
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT sections FROM teacher_info")
                sections = cursor.fetchall()
            return render_template('add_event.html', sections=sections)

        @self.app.route("/add-deadline", methods=['GET', 'POST'])
        def add_deadline():
            if request.method == 'POST':
                title = request.form['title']
                deadline_date = request.form['deadline_date']

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO deadlines (title, date, teacher_id) VALUES (%s, %s, %s)",
                        (title, deadline_date, session['username'])
                    )
                    self.mysql.connection.commit()

                flash('Deadline added successfully!', 'success')
                return redirect(url_for('teacher_dashboard'))
            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT sections FROM teacher_info")
                sections = cursor.fetchall()
            return render_template('add_deadline.html', sections=sections)

        @self.app.route("/add-lesson-plan", methods=['GET', 'POST'])
        def add_lesson_plan():
            if request.method == 'POST':
                title = request.form['title']
                details = request.form['details']

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO lesson_plans (title, details, teacher_id) VALUES (%s, %s, %s)",
                        (title, details, session['username'])
                    )
                    self.mysql.connection.commit()

                flash('Lesson plan added successfully!', 'success')
                return redirect(url_for('teacher_dashboard'))
            return render_template('add_lesson_plan.html')

        @self.app.route("/input_student_scores", methods=['GET', 'POST'])
        def input_student_scores():
            if request.method == 'POST':
                quiz_score = float(request.form['quiz_score'])
                attendance_behavior_score = float(request.form['attendance_score'])
                class_participation_score = float(request.form['participation_score'])
                exam_score = float(request.form['exam_score'])
                student_id = request.form['student_id']  # Get the student ID from the form

                total_score = (
                    (quiz_score / 20 * 0.25) +
                    (attendance_behavior_score / 30 * 0.10) +
                    (class_participation_score / 50 * 0.15) +
                    (exam_score / 60 * 0.50)
                ) * 100

                # Insert the scores into the student_scores table
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO student_scores (stud_id, quiz_score, attendance_score, participation_score, exam_score, total_score)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (student_id, quiz_score, attendance_behavior_score, class_participation_score, exam_score, total_score)
                    )
                    self.mysql.connection.commit()

                # Insert or update the enrollment in the enrolled_students table
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO enrolled_students (stud_id, subject_name, section_name)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE subject_name = %s, section_name = %s
                        """,
                        (student_id, request.form['subject_name'], request.form['section_name'], request.form['subject_name'], request.form['section_name'])
                    )
                    self.mysql.connection.commit()

                flash('Scores entered and enrollment updated successfully!', 'success')
                return redirect(url_for('input_student_scores'))

            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT * FROM student_info")
                students = cursor.fetchall()

            selected_section = request.args.get('section')
            selected_subject = request.args.get('subject')

            if selected_section and selected_subject:
                with self.mysql.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT si.*
                        FROM student_info si
                        INNER JOIN subjects s ON si.section = %s AND s.subject_name = %s
                        WHERE si.section = %s AND s.subject_name = %s
                        """,
                        (selected_section, selected_subject, selected_section, selected_subject)
                    )
                    students = cursor.fetchall()

            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT sections FROM student_info")
                sections = cursor.fetchall()

            with self.mysql.connection.cursor() as cursor:
                cursor.execute("SELECT DISTINCT subject_name FROM subjects")
                subjects = cursor.fetchall()

            return render_template('input_student_scores.html', sections=sections, students=students, subjects=subjects, selected_section=selected_section, selected_subject=selected_subject)

        @self.app.route("/add-subject", methods=['GET', 'POST'])
        def add_subject():
            if request.method == 'POST':
                subject_name = request.form['subject_name']
                section_id = request.form['section_id']

                with self.mysql.connection.cursor() as cursor:
                    cursor.execute("INSERT INTO subjects (subject_name, section_id) VALUES (%s, %s)", (subject_name, section_id))
                    self.mysql.connection.commit()

                flash('Subject added successfully!', 'success')
                return redirect(url_for('add_subject'))

            with self.mysql.connection.cursor() as cursor :
                cursor.execute("SELECT * FROM sections")
                sections = cursor.fetchall()

            return render_template('add_subject.html', sections=sections)

        @self.app.route("/logout")
        def logout():
            session.pop('username', None)
            session.pop('role', None)
            flash('Logged out successfully!', 'success')
            return redirect(url_for('login'))

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)

if __name__ == "__main__":
    app = RecordManagementSystem(__name__)
    app.run(debug=True)