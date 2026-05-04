import os
import csv
import uuid
import jwt
import datetime
import qrcode
from functools import wraps
from flask import Flask, request, jsonify, redirect, session, send_from_directory
from flask_mail import Mail, Message
import pymysql
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('JWT_SECRET', 'default-secret-key')

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')

mail = Mail(app)

db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'attendance_db'),
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(' ')[1]
        if not token and 'token' in session:
            token = session.get('token')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, os.getenv('JWT_SECRET', 'default-secret-key'), algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        if username == admin_username and password == admin_password:
            token = jwt.encode({
                'username': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, os.getenv('JWT_SECRET', 'default-secret-key'), algorithm='HS256')
            
            session['token'] = token
            session['username'] = username
            
            return jsonify({'token': token, 'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
def index():
    if 'token' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM students')
        total_students = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM courses')
        total_courses = cursor.fetchone()['count']
        
        today = datetime.date.today()
        cursor.execute('SELECT COUNT(DISTINCT student_id) as count FROM attendance WHERE date = %s AND status = "present"', (today,))
        present_today = cursor.fetchone()['count']
        
        cursor.execute('''
            SELECT COUNT(DISTINCT s.id) as count 
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id AND a.date = %s
            WHERE a.id IS NULL
        ''', (today,))
        absent_today = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_students': total_students,
            'total_courses': total_courses,
            'present_today': present_today,
            'absent_today': absent_today
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/students', methods=['GET'])
@token_required
def get_students(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.email, s.qr_data, s.qr_image_path, s.created_at, c.name as course_name
            FROM students s
            LEFT JOIN courses c ON s.course_id = c.id
            ORDER BY s.created_at DESC
        ''')
        
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(students), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/students', methods=['POST'])
@token_required
def create_student(current_user):
    try:
        data = request.get_json()
        name = data.get('name', '')
        email = data.get('email', '')
        course_id = data.get('course_id')
        
        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400
        
        qr_data = str(uuid.uuid4())
        qr_filename = f"{qr_data}.png"
        qr_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'static', 'images', 'qrcodes')
        qr_filepath = os.path.join(qr_folder, qr_filename)
        
        os.makedirs(qr_folder, exist_ok=True)
        
        img = qrcode.make(qr_data)
        img.save(qr_filepath)
        
        qr_image_path = f"/static/images/qrcodes/{qr_filename}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO students (name, email, course_id, qr_data, qr_image_path)
            VALUES (%s, %s, %s, %s, %s)
        ''', (name, email, course_id, qr_data, qr_image_path))
        
        conn.commit()
        student_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return jsonify({'id': student_id, 'name': name, 'email': email, 'course_id': course_id, 'qr_data': qr_data, 'qr_image_path': qr_image_path}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/students/<int:id>', methods=['PUT'])
@token_required
def update_student(current_user, id):
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        course_id = data.get('course_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students WHERE id = %s', (id,))
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        update_fields = []
        values = []
        
        if name is not None:
            update_fields.append('name = %s')
            values.append(name)
        if email is not None:
            update_fields.append('email = %s')
            values.append(email)
        if course_id is not None:
            update_fields.append('course_id = %s')
            values.append(course_id)
        
        if update_fields:
            values.append(id)
            query = f"UPDATE students SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, values)
            conn.commit()
        
        cursor.execute('SELECT * FROM students WHERE id = %s', (id,))
        updated_student = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify(updated_student), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/students/<int:id>', methods=['DELETE'])
@token_required
def delete_student(current_user, id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT qr_image_path FROM students WHERE id = %s', (id,))
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        qr_image_path = student['qr_image_path']
        if qr_image_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            full_path = os.path.join(base_dir, qr_image_path.lstrip('/'))
            if os.path.exists(full_path):
                os.remove(full_path)
        
        cursor.execute('DELETE FROM students WHERE id = %s', (id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Student deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/courses', methods=['GET'])
@token_required
def get_courses(current_user):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.name, c.section, c.schedule, c.created_at, t.name as teacher_name,
                   (SELECT COUNT(*) FROM students WHERE course_id = c.id) as student_count
            FROM courses c
            LEFT JOIN teachers t ON c.teacher_id = t.id
            ORDER BY c.created_at DESC
        ''')
        
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify(courses), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/courses', methods=['POST'])
@token_required
def create_course(current_user):
    try:
        data = request.get_json()
        name = data.get('name', '')
        section = data.get('section', '')
        schedule = data.get('schedule', '')
        teacher_id = data.get('teacher_id')
        
        if not name:
            return jsonify({'error': 'Course name is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO courses (name, section, schedule, teacher_id)
            VALUES (%s, %s, %s, %s)
        ''', (name, section, schedule, teacher_id))
        
        conn.commit()
        course_id = cursor.lastrowid
        
        cursor.execute('SELECT * FROM courses WHERE id = %s', (course_id,))
        new_course = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify(new_course), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/courses/<int:id>', methods=['PUT'])
@token_required
def update_course(current_user, id):
    try:
        data = request.get_json()
        name = data.get('name')
        section = data.get('section')
        schedule = data.get('schedule')
        teacher_id = data.get('teacher_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM courses WHERE id = %s', (id,))
        course = cursor.fetchone()
        
        if not course:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Course not found'}), 404
        
        update_fields = []
        values = []
        
        if name is not None:
            update_fields.append('name = %s')
            values.append(name)
        if section is not None:
            update_fields.append('section = %s')
            values.append(section)
        if schedule is not None:
            update_fields.append('schedule = %s')
            values.append(schedule)
        if teacher_id is not None:
            update_fields.append('teacher_id = %s')
            values.append(teacher_id)
        
        if update_fields:
            values.append(id)
            query = f"UPDATE courses SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, values)
            conn.commit()
        
        cursor.execute('SELECT * FROM courses WHERE id = %s', (id,))
        updated_course = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify(updated_course), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/courses/<int:id>', methods=['DELETE'])
@token_required
def delete_course(current_user, id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM students WHERE course_id = %s', (id,))
        student_count = cursor.fetchone()['count']
        
        if student_count > 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Cannot delete course with enrolled students'}), 400
        
        cursor.execute('DELETE FROM courses WHERE id = %s', (id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'message': 'Course deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/scan', methods=['POST'])
@token_required
def scan_qr(current_user):
    try:
        data = request.get_json()
        qr_data = data.get('qr_data', '')
        
        if not qr_data:
            return jsonify({'error': 'QR data is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.name, s.course_id, c.name as course_name
            FROM students s
            LEFT JOIN courses c ON s.course_id = c.id
            WHERE s.qr_data = %s
        ''', (qr_data,))
        
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Student not found'}), 404
        
        today = datetime.date.today()
        now = datetime.datetime.now().time()
        
        cursor.execute('''
            SELECT * FROM attendance 
            WHERE student_id = %s AND date = %s
        ''', (student['id'], today))
        
        existing_record = cursor.fetchone()
        
        if existing_record:
            if existing_record['time_in'] and not existing_record['time_out']:
                cursor.execute('''
                    UPDATE attendance 
                    SET time_out = %s, status = "present"
                    WHERE id = %s
                ''', (now, existing_record['id']))
                conn.commit()
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'student_name': student['name'],
                    'course_name': student['course_name'],
                    'status': 'time_out_recorded',
                    'message': 'Time out recorded successfully'
                }), 200
            else:
                cursor.close()
                conn.close()
                return jsonify({
                    'student_name': student['name'],
                    'course_name': student['course_name'],
                    'status': 'already_complete',
                    'message': 'Attendance already recorded for today'
                }), 200
        else:
            cursor.execute('''
                INSERT INTO attendance (student_id, course_id, date, time_in, status)
                VALUES (%s, %s, %s, %s, "present")
            ''', (student['id'], student['course_id'], today, now))
            
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'student_name': student['name'],
                'course_name': student['course_name'],
                'status': 'time_in_recorded',
                'message': 'Time in recorded successfully'
            }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-csv', methods=['POST'])
@token_required
def upload_csv(current_user):
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400
        
        import io
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        created_students = []
        failed_students = []
        
        qr_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'static', 'images', 'qrcodes')
        os.makedirs(qr_folder, exist_ok=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for row in csv_reader:
            try:
                name = row.get('name', '').strip()
                email = row.get('email', '').strip()
                course_id = row.get('course_id', '').strip()
                
                if not name or not email:
                    failed_students.append({'data': row, 'error': 'Missing name or email'})
                    continue
                
                if course_id:
                    course_id = int(course_id)
                else:
                    course_id = None
                
                qr_data = str(uuid.uuid4())
                qr_filename = f"{qr_data}.png"
                qr_filepath = os.path.join(qr_folder, qr_filename)
                
                img = qrcode.make(qr_data)
                img.save(qr_filepath)
                
                qr_image_path = f"/static/images/qrcodes/{qr_filename}"
                
                cursor.execute('''
                    INSERT INTO students (name, email, course_id, qr_data, qr_image_path)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (name, email, course_id, qr_data, qr_image_path))
                
                conn.commit()
                
                student_id = cursor.lastrowid
                
                created_students.append({
                    'id': student_id,
                    'name': name,
                    'email': email,
                    'course_id': course_id,
                    'qr_data': qr_data,
                    'qr_image_path': qr_image_path
                })
                
                if app.config['MAIL_USERNAME'] and email:
                    try:
                        msg = Message(
                            subject='Your QR Code for Attendance System',
                            recipients=[email],
                            body=f'Hello {name},\n\nYour QR code has been generated for the attendance system. Please find it attached.',
                            sender=app.config['MAIL_USERNAME']
                        )
                        
                        with open(qr_filepath, 'rb') as f:
                            msg.attach(qr_filename, 'image/png', f.read())
                        
                        mail.send(msg)
                    except Exception as e:
                        failed_students.append({'data': row, 'error': f'Email failed: {str(e)}'})
                
            except Exception as e:
                failed_students.append({'data': row, 'error': str(e)})
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'created': created_students,
            'failed': failed_students,
            'message': f'Successfully created {len(created_students)} students, {len(failed_students)} failed'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
