from datetime import date, datetime, timedelta
from functools import wraps
import csv
import io
import os
import uuid
from io import BytesIO

import pymysql
import qrcode
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from flask_cors import CORS

from config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    FLASK_SECRET_KEY,
    MAIL_DEFAULT_SENDER,
    MAIL_PASSWORD,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_USE_SSL,
    MAIL_USE_TLS,
    MAIL_USERNAME,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_USER,
)

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.secret_key = FLASK_SECRET_KEY
app.config.update(
    MAIL_SERVER=MAIL_SERVER,
    MAIL_PORT=int(MAIL_PORT),
    MAIL_USE_TLS=str(MAIL_USE_TLS).lower() in ('true', '1', 'yes'),
    MAIL_USE_SSL=str(MAIL_USE_SSL).lower() in ('true', '1', 'yes'),
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER=MAIL_DEFAULT_SENDER,
)
mail = Mail(app)
CORS(app)


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_admin_teacher():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT IGNORE INTO teachers (username, password, email) VALUES (%s, %s, %s)',
                (ADMIN_USERNAME, ADMIN_PASSWORD, f'{ADMIN_USERNAME}@localhost'),
            )
            conn.commit()
    finally:
        conn.close()


def get_teacher_by_username(username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, username, password, email FROM teachers WHERE username = %s', (username,))
            return cursor.fetchone()
    finally:
        conn.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)

    return wrapper


def build_qr_image_bytes(qr_value):
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(qr_value)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def send_qr_email(student_name, course_name, qr_value, recipient_email):
    message = Message(
        subject=f'QR Attendance Card for {course_name}',
        recipients=[recipient_email],
    )
    message.body = (
        f'Hello {student_name},\n\n'
        f'Your QR attendance code for {course_name} is ready. Scan the attached QR code to track attendance in real time.\n\n'
        'Keep this QR safe and present it to your teacher when asked.\n'
    )
    qr_file = build_qr_image_bytes(qr_value)
    message.attach('qr-attendance.png', 'image/png', qr_file.read())
    mail.send(message)


def generate_qr_value():
    return f'QR-{uuid.uuid4().hex[:18].upper()}'


def get_teacher_courses(teacher_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, name, description FROM courses WHERE teacher_id = %s ORDER BY created_at DESC', (teacher_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def get_student_details(student_id, teacher_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT s.id, s.name, s.email, s.year_level, s.qr_data, c.id AS course_id, c.name AS course_name '
                'FROM students s '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE s.id = %s AND c.teacher_id = %s',
                (student_id, teacher_id),
            )
            return cursor.fetchone()
    finally:
        conn.close()


def fetch_active_teacher_id():
    return session.get('teacher_id')


@app.route('/')
def home():
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    teacher = get_teacher_by_username(username)
    if not teacher and username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        teacher = {'id': None, 'username': username, 'password': password, 'email': f'{username}@localhost'}
    if not teacher or teacher['password'] != password:
        return render_template('login.html', error='Invalid credentials', username=username)
    session['authenticated'] = True
    session['teacher_id'] = teacher['id']
    session['username'] = teacher['username']
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) AS total FROM courses WHERE teacher_id = %s', (teacher_id,))
            courses_count = cursor.fetchone()['total']
            cursor.execute(
                'SELECT COUNT(*) AS total FROM students s JOIN courses c ON s.course_id = c.id WHERE c.teacher_id = %s',
                (teacher_id,),
            )
            students_count = cursor.fetchone()['total']
            cursor.execute(
                'SELECT COUNT(*) AS total FROM attendance a '
                'JOIN students s ON a.student_id = s.id '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE c.teacher_id = %s',
                (teacher_id,),
            )
            attendance_count = cursor.fetchone()['total']
            cursor.execute(
                'SELECT a.id, s.name AS student_name, c.name AS course_name, a.time_in, a.time_out, a.date '
                'FROM attendance a '
                'JOIN students s ON a.student_id = s.id '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE c.teacher_id = %s '
                'ORDER BY a.id DESC LIMIT 8',
                (teacher_id,),
            )
            recent_records = cursor.fetchall()
    finally:
        conn.close()
    return render_template(
        'dashboard.html',
        courses_count=courses_count,
        students_count=students_count,
        attendance_count=attendance_count,
        recent_records=recent_records,
    )


@app.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    teacher_id = fetch_active_teacher_id()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if name:
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'INSERT INTO courses (teacher_id, name, description) VALUES (%s, %s, %s)',
                        (teacher_id, name, description),
                    )
                    conn.commit()
                flash('Course created successfully.')
            finally:
                conn.close()
        else:
            flash('Course name is required.')
        return redirect(url_for('courses'))
    course_list = get_teacher_courses(teacher_id)
    return render_template('courses.html', courses=course_list)


@app.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, name, description FROM courses WHERE id = %s AND teacher_id = %s', (course_id, teacher_id))
            course = cursor.fetchone()
            if not course:
                return redirect(url_for('courses'))
            if request.method == 'POST':
                name = request.form.get('name', '').strip()
                description = request.form.get('description', '').strip()
                if name:
                    cursor.execute('UPDATE courses SET name = %s, description = %s WHERE id = %s', (name, description, course_id))
                    conn.commit()
                    flash('Course updated successfully.')
                    return redirect(url_for('courses'))
                flash('Course name is required.')
    finally:
        conn.close()
    return render_template('course_edit.html', course=course)


@app.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM courses WHERE id = %s AND teacher_id = %s', (course_id, teacher_id))
            conn.commit()
    finally:
        conn.close()
    flash('Course deleted successfully.')
    return redirect(url_for('courses'))


@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        year_level = request.form.get('year_level', '').strip()
        course_id = request.form.get('course_id')
        if name and email and course_id:
            qr_value = generate_qr_value()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        'INSERT INTO students (course_id, name, email, year_level, qr_data) VALUES (%s, %s, %s, %s, %s)',
                        (course_id, name, email, year_level, qr_value),
                    )
                    conn.commit()
                    cursor.execute('SELECT c.name FROM courses c WHERE c.id = %s AND c.teacher_id = %s', (course_id, teacher_id))
                    course = cursor.fetchone()
                send_qr_email(name, course['name'], qr_value, email)
                flash('Student added and QR email sent.')
            except Exception:
                flash('Student added, but email delivery failed.')
        else:
            flash('Name, email, and course selection are required.')
        return redirect(url_for('students'))
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT s.id, s.name, s.email, s.year_level, s.qr_data, c.name AS course_name '
                'FROM students s JOIN courses c ON s.course_id = c.id '
                'WHERE c.teacher_id = %s ORDER BY s.id DESC',
                (teacher_id,),
            )
            student_list = cursor.fetchall()
            cursor.execute('SELECT id, name FROM courses WHERE teacher_id = %s', (teacher_id,))
            course_list = cursor.fetchall()
    finally:
        conn.close()
    return render_template('students.html', students=student_list, courses=course_list)


@app.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT s.id, s.name, s.email, s.year_level, s.qr_data, s.course_id, c.name AS course_name '
                'FROM students s JOIN courses c ON s.course_id = c.id '
                'WHERE s.id = %s AND c.teacher_id = %s',
                (student_id, teacher_id),
            )
            student = cursor.fetchone()
            if not student:
                return redirect(url_for('students'))
            if request.method == 'POST':
                name = request.form.get('name', '').strip()
                email = request.form.get('email', '').strip()
                year_level = request.form.get('year_level', '').strip()
                course_id = request.form.get('course_id')
                if name and email and course_id:
                    cursor.execute(
                        'UPDATE students SET name = %s, email = %s, year_level = %s, course_id = %s WHERE id = %s',
                        (name, email, year_level, course_id, student_id),
                    )
                    conn.commit()
                    flash('Student information updated.')
                    return redirect(url_for('students'))
                flash('Student name, email, and course are required.')
            cursor.execute('SELECT id, name FROM courses WHERE teacher_id = %s', (teacher_id,))
            course_list = cursor.fetchall()
    finally:
        conn.close()
    return render_template('student_edit.html', student=student, courses=course_list)


@app.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'DELETE s FROM students s '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE s.id = %s AND c.teacher_id = %s',
                (student_id, teacher_id),
            )
            conn.commit()
    finally:
        conn.close()
    flash('Student deleted successfully.')
    return redirect(url_for('students'))


@app.route('/students/upload-csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    teacher_id = fetch_active_teacher_id()
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        csv_file = request.files.get('csv_file')
        if course_id and csv_file:
            content = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            inserted = 0
            failed = 0
            conn = get_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT name FROM courses WHERE id = %s AND teacher_id = %s', (course_id, teacher_id))
                    course = cursor.fetchone()
                    if not course:
                        flash('Selected course is not available.')
                        return redirect(url_for('upload_csv'))
                    for row in reader:
                        name = (row.get('name') or '').strip()
                        email = (row.get('email') or '').strip()
                        year_level = (row.get('year_level') or '').strip()
                        if not name or not email:
                            failed += 1
                            continue
                        qr_value = generate_qr_value()
                        try:
                            cursor.execute(
                                'INSERT INTO students (course_id, name, email, year_level, qr_data) VALUES (%s, %s, %s, %s, %s)',
                                (course_id, name, email, year_level, qr_value),
                            )
                            conn.commit()
                            send_qr_email(name, course['name'], qr_value, email)
                            inserted += 1
                        except Exception:
                            failed += 1
            finally:
                conn.close()
            flash(f'CSV upload complete: {inserted} students added, {failed} failed.')
        else:
            flash('Course selection and CSV file are required.')
        return redirect(url_for('upload_csv'))
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, name FROM courses WHERE teacher_id = %s', (teacher_id,))
            course_list = cursor.fetchall()
    finally:
        conn.close()
    return render_template('upload_csv.html', courses=course_list)


@app.route('/attendance')
@login_required
def attendance():
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT a.id, s.name AS student_name, c.name AS course_name, a.date, a.time_in, a.time_out, a.status '
                'FROM attendance a '
                'JOIN students s ON a.student_id = s.id '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE c.teacher_id = %s ORDER BY a.date DESC, a.time_in DESC LIMIT 120',
                (teacher_id,),
            )
            attendance_records = cursor.fetchall()
    finally:
        conn.close()
    return render_template('attendance.html', attendance_records=attendance_records)


@app.route('/attendance/<int:attendance_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_attendance(attendance_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT a.id, a.time_in, a.time_out, a.status, s.name AS student_name, c.name AS course_name '
                'FROM attendance a '
                'JOIN students s ON a.student_id = s.id '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE a.id = %s AND c.teacher_id = %s',
                (attendance_id, teacher_id),
            )
            record = cursor.fetchone()
            if not record:
                return redirect(url_for('attendance'))
            if request.method == 'POST':
                time_out = request.form.get('time_out') or None
                status = request.form.get('status', 'present')
                cursor.execute('UPDATE attendance SET time_out = %s, status = %s WHERE id = %s', (time_out, status, attendance_id))
                conn.commit()
                flash('Attendance record updated.')
                return redirect(url_for('attendance'))
    finally:
        conn.close()
    return render_template('attendance_edit.html', record=record)


@app.route('/attendance/<int:attendance_id>/delete', methods=['POST'])
@login_required
def delete_attendance(attendance_id):
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'DELETE a FROM attendance a '
                'JOIN students s ON a.student_id = s.id '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE a.id = %s AND c.teacher_id = %s',
                (attendance_id, teacher_id),
            )
            conn.commit()
    finally:
        conn.close()
    flash('Attendance record deleted.')
    return redirect(url_for('attendance'))


@app.route('/scanner')
@login_required
def scanner_page():
    return render_template('scanner.html')


@app.route('/scan', methods=['POST'])
@login_required
def scan_qr():
    data = request.get_json(silent=True) or {}
    qr_data = data.get('qr_data', '').strip()
    if not qr_data:
        return jsonify({'error': 'QR data is required.'}), 400
    teacher_id = fetch_active_teacher_id()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT s.id, s.name, s.year_level, c.name AS course_name '
                'FROM students s '
                'JOIN courses c ON s.course_id = c.id '
                'WHERE s.qr_data = %s AND c.teacher_id = %s',
                (qr_data, teacher_id),
            )
            student = cursor.fetchone()
            if not student:
                return jsonify({'error': 'Student not found.'}), 404
            today = date.today()
            cursor.execute(
                'SELECT id, time_in, time_out, date, status '
                'FROM attendance WHERE student_id = %s AND date = %s ORDER BY id DESC LIMIT 1',
                (student['id'], today),
            )
            attendance_record = cursor.fetchone()
            if attendance_record:
                if attendance_record['time_out'] is None:
                    return jsonify(
                        {
                            'message': 'Attendance already recorded for today.',
                            'student': student,
                            'attendance': attendance_record,
                        }
                    ), 200
                return jsonify(
                    {
                        'message': 'Attendance has already been registered today.',
                        'student': student,
                        'attendance': attendance_record,
                    }
                ), 200
            now = datetime.utcnow()
            cursor.execute(
                'INSERT INTO attendance (student_id, time_in, date, status) VALUES (%s, %s, %s, %s)',
                (student['id'], now, today, 'present'),
            )
            conn.commit()
            attendance_id = cursor.lastrowid
            cursor.execute('SELECT id, time_in, time_out, date, status FROM attendance WHERE id = %s', (attendance_id,))
            attendance_record = cursor.fetchone()
    finally:
        conn.close()
    return jsonify({'message': 'Attendance recorded.', 'student': student, 'attendance': attendance_record}), 201


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    ensure_admin_teacher()
    app.run(host='0.0.0.0', port=5000)
