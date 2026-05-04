# QR Code Student Identification and Attendance System

A comprehensive attendance management system for Batangas State University ARASOF-Nasugbu that leverages QR code technology for efficient student identification and real-time attendance tracking.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Flask (Python 3.11) |
| Database | MariaDB 11 |
| ORM/Database Driver | PyMySQL |
| Authentication | JWT (PyJWT) |
| Email Service | Flask-Mail |
| QR Code Generation | qrcode + Pillow |
| Frontend Templates | Jinja2 |
| CSS Framework | Bootstrap 5 (CDN) |
| JavaScript | Vanilla JS |
| QR Scanner | html5-qrcode (CDN) |
| Web Server | Gunicorn + Nginx |
| Containerization | Docker + Docker Compose |

## Folder Structure

```
/workspace/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── config.py              # Configuration loader
│   ├── requirements.txt       # Python dependencies
│   ├── schema.sql             # Database schema and seed data
│   ├── Dockerfile             # Backend container definition
│   ├── .env.example           # Environment variables template
│   └── utils/
│       ├── __init__.py
│       ├── qr_generator.py    # QR code generation utility
│       └── email_sender.py    # Email sending utility
├── frontend/
│   ├── templates/
│   │   ├── base.html          # Base template with navbar/sidebar
│   │   ├── login.html         # Login page
│   │   ├── dashboard.html     # Dashboard overview
│   │   ├── scanner.html       # Live QR scanner page
│   │   ├── students.html      # Student management
│   │   ├── courses.html       # Course management
│   │   └── attendance.html    # Attendance records
│   └── static/
│       ├── css/
│       │   └── style.css      # Custom minimalist styles
│       ├── js/
│       │   ├── scanner.js     # QR scanner logic
│       │   ├── students.js    # Student CRUD operations
│       │   ├── courses.js     # Course CRUD operations
│       │   └── attendance.js  # Attendance filtering/export
│       └── images/
│           └── qrcodes/       # Generated QR code images
├── docker-compose.yml         # Multi-container orchestration
├── nginx.conf                 # Nginx reverse proxy config
└── README.md                  # This file
```

## Setup Instructions

### Option 1: Local Development (Virtual Environment)

1. **Clone and navigate to project:**
   ```bash
   cd /workspace
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env  # Edit with your credentials
   ```

5. **Create database and load schema:**
   ```bash
   sudo mariadb -u root -p < backend/schema.sql
   ```

6. **Create QR codes directory:**
   ```bash
   mkdir -p frontend/static/images/qrcodes
   ```

7. **Run the application:**
   ```bash
   cd backend
   python app.py
   ```

8. **Access the application:**
   Open browser to `http://localhost:5000`

### Option 2: Docker Compose (Recommended for Production)

1. **Ensure Docker and Docker Compose are installed:**
   ```bash
   docker --version
   docker compose version
   ```

2. **Create environment file:**
   ```bash
   cp backend/.env.example backend/.env
   nano backend/.env  # Edit with your credentials
   ```

3. **Build and start all services:**
   ```bash
   docker compose up --build -d
   ```

4. **View logs:**
   ```bash
   docker compose logs -f
   ```

5. **Access the application:**
   - Via Nginx: `http://localhost:80`
   - Direct backend: `http://localhost:5000`

6. **Stop all services:**
   ```bash
   docker compose down
   ```

7. **Stop and remove volumes (clean slate):**
   ```bash
   docker compose down -v
   ```

## API Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| GET | `/login` | No | Render login page |
| POST | `/login` | No | Authenticate admin, return JWT token |
| GET | `/logout` | Yes | Clear session and redirect to login |
| GET | `/` | No | Redirect to dashboard or login |
| GET | `/dashboard` | Yes | Get attendance statistics summary |
| GET | `/students` | Yes | Get all students with course info |
| POST | `/students` | Yes | Create new student with QR code |
| PUT | `/students/<id>` | Yes | Update student information |
| DELETE | `/students/<id>` | Yes | Delete student and QR image |
| GET | `/courses` | Yes | Get all courses with teacher and student count |
| POST | `/courses` | Yes | Create new course |
| PUT | `/courses/<id>` | Yes | Update course information |
| DELETE | `/courses/<id>` | Yes | Delete course (if no students enrolled) |
| POST | `/scan` | Yes | Process QR scan and record attendance |
| POST | `/upload-csv` | Yes | Bulk import students from CSV file |
| GET | `/attendance` | Yes | Get attendance records with filters |
| GET | `/attendance/export` | Yes | Export attendance to CSV file |
| GET | `/scanner` | Yes | Render live QR scanner page |

## How to Run the Demo

### Step 1: Start the Application
```bash
cd /workspace
docker compose up --build -d
```

### Step 2: Access the Login Page
Open browser to `http://localhost:80` or `http://localhost:5000`

### Step 3: Login with Admin Credentials
- **Username:** `admin` (or value from `.env` ADMIN_USERNAME)
- **Password:** `admin123` (or value from `.env` ADMIN_PASSWORD)

### Step 4: Create a Course
1. Navigate to "Courses" in sidebar
2. Click "Add Course"
3. Enter course name, section, and schedule
4. Click "Save"

### Step 5: Add Students
**Option A - Manual Entry:**
1. Navigate to "Students"
2. Click "Add Student"
3. Enter name, email, and select course
4. Click "Save" (QR code auto-generated)

**Option B - CSV Upload:**
1. Prepare CSV with columns: `name,email,course_id`
2. Click "Upload CSV" in Students page
3. Select file and upload
4. QR codes generated and emails sent automatically

### Step 6: Test QR Scanner
1. Navigate to "Scanner"
2. Allow camera access when prompted
3. Hold student QR code in front of camera
4. System displays student info and records attendance
5. Scan again to record time-out

### Step 7: View Attendance Records
1. Navigate to "Attendance"
2. Use filters (date, course, status)
3. View summary statistics
4. Click "Export CSV" to download records

### Step 8: Stop the Application
```bash
docker compose down
```

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |

**Important:** Change these defaults in `.env` before production deployment.

## Seed Data

The database includes sample data for testing:
- **3 Teachers** with sample credentials
- **6 Courses** across different programs
- **18 Students** (3 per course) with pre-generated QR codes

## Troubleshooting

### Database Connection Issues
```bash
docker compose logs db
docker compose logs backend
```

### QR Code Generation Fails
Ensure directory exists and has write permissions:
```bash
mkdir -p frontend/static/images/qrcodes
chmod 755 frontend/static/images/qrcodes
```

### Email Not Sending
Verify SMTP credentials in `.env`:
- MAIL_SERVER (e.g., smtp.gmail.com)
- MAIL_PORT (587 for TLS, 465 for SSL)
- MAIL_USERNAME
- MAIL_PASSWORD (use app-specific password for Gmail)

## Team Members

**Course:** IT 323 / NTT 404 - Web Systems Technologies  
**Academic Year:** 2025-2026  
**Institution:** Batangas State University ARASOF-Nasugbu

**Approved by:**  
Mr. Calvin John V. Placio  
Course Instructor

---

© 2025 QR Code Student Identification and Attendance System  
Batangas State University ARASOF-Nasugbu
