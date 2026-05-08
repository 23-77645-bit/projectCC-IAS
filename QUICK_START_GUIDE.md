# 🚀 Quick Start Guide - QR Code Student Attendance System

Welcome! This guide will help you get the attendance system up and running on your device in minutes. Choose the method that works best for you.

---

## 📋 What You Need Before Starting

### Required Software (Choose Docker Compose Method)
- **Docker** and **Docker Compose** installed
  - Download from: https://docs.docker.com/get-docker/
  
### Verify Installation
```bash
docker --version
docker compose version
```

If both commands show version numbers, you're ready to go! ✅

---

## 🎯 Method 1: Docker Compose (EASIEST - Recommended for Beginners)

This is the simplest way to run the entire system with one command.

### Step 1: Create Configuration File

Open a terminal/command prompt and navigate to the project folder, then create a `.env` file:

**On Windows (PowerShell):**
```powershell
cd /workspace
@"
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=attendance_db
MYSQL_USER=attendance_user
MYSQL_PASSWORD=attendance_secure_password_2025
JWT_SECRET=super_secure_jwt_secret_key_change_in_production_2025
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
FLASK_ENV=production
"@ > .env
```

**On Mac/Linux:**
```bash
cd /workspace
cat > .env << EOF
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=attendance_db
MYSQL_USER=attendance_user
MYSQL_PASSWORD=attendance_secure_password_2025
JWT_SECRET=super_secure_jwt_secret_key_change_in_production_2025
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
FLASK_ENV=production
EOF
```

### Step 2: Start the Application

Run this single command to build and start everything:

```bash
docker-compose up --build -d
```

**What this does:**
- Builds the Flask backend application
- Starts MariaDB database
- Starts Nginx web server
- Sets up all necessary connections

### Step 3: Wait for Services to Start

Give it about 30-60 seconds to fully start up. You can check the status:

```bash
docker-compose ps
```

You should see 3 containers with "Up" status:
- `attendance_db` ✅
- `attendance_backend` ✅
- `attendance_nginx` ✅

### Step 4: Open Your Browser

Navigate to: **http://localhost**

### Step 5: Login

Use these default credentials:
- **Username:** `admin`
- **Password:** `admin123`

🎉 **Congratulations! The system is now running!**

---

## 🧪 Try It Out - Quick Demo

Once logged in, follow these steps to test the system:

### 1. Add a Course
- Click **"Courses"** in the sidebar
- Click **"Add Course"**
- Enter:
  - Course Name: `Mathematics 101`
  - Section: `A`
  - Schedule: `MWF 8:00-9:00 AM`
- Click **"Save"**

### 2. Add Students

**Option A - Manual Entry:**
- Click **"Students"** in the sidebar
- Click **"Add Student"**
- Enter:
  - Name: `John Doe`
  - Email: `john@example.com`
  - Select Course: `Mathematics 101`
- Click **"Save"**
- QR code is automatically generated! ✅

**Option B - Upload CSV:**
- Create a CSV file with columns: `name,email,course_id`
- Example:
  ```csv
  name,email,course_id
  Jane Smith,jane@example.com,1
  Bob Johnson,bob@example.com,1
  ```
- Click **"Upload CSV"** in Students page
- Select your file and upload

### 3. Test QR Scanner
- Click **"Scanner"** in the sidebar
- Allow camera access when prompted
- Hold a student's QR code in front of the camera
- Watch as attendance is automatically recorded! ✅

### 4. View Attendance Records
- Click **"Attendance"** in the sidebar
- See all recorded attendance with timestamps
- Use filters to search by date or course
- Click **"Export CSV"** to download records

---

## ⏹️ Stopping the Application

When you're done testing:

```bash
docker-compose down
```

To completely remove all data and start fresh:

```bash
docker-compose down -v
```

---

## 🔧 Troubleshooting Common Issues

### Issue: Port 80 Already in Use

**Error:** Cannot start nginx/container

**Solution:** Stop other services using port 80 (like Skype, IIS, or Apache), or change the port in `docker-compose.yml`.

### Issue: Containers Won't Start

**Check logs:**
```bash
docker-compose logs
```

**Look for errors** in the output to identify the problem.

### Issue: Can't Access http://localhost

**Verify containers are running:**
```bash
docker-compose ps
```

If any show "Exit" or error status, check logs:
```bash
docker-compose logs backend
docker-compose logs db
```

### Issue: Database Connection Failed

**Wait longer** - The database takes 30-60 seconds to initialize on first run. Check status:
```bash
docker-compose logs db | grep "ready for connections"
```

### Issue: QR Codes Not Generating

**Create the directory manually:**
```bash
mkdir -p frontend/static/images/qrcodes
chmod 755 frontend/static/images/qrcodes
```

Then restart:
```bash
docker-compose restart backend
```

---

## 📊 Viewing Logs (For Debugging)

### View All Logs
```bash
docker-compose logs -f
```

### View Specific Service Logs
```bash
# Backend application logs
docker-compose logs -f backend

# Database logs
docker-compose logs -f db

# Web server logs
docker-compose logs -f nginx
```

Press `Ctrl+C` to stop following logs.

---

## 🔐 Security Notes

⚠️ **IMPORTANT:** Before using in production:

1. **Change Default Passwords** in `.env`:
   - Change `ADMIN_PASSWORD`
   - Change `JWT_SECRET`
   - Change database passwords

2. **Enable HTTPS** for production use

3. **Update Email Settings** if using QR code email delivery

---

## 📁 Project Structure Overview

```
/workspace/
├── backend/           # Flask application
│   ├── app.py        # Main application
│   └── requirements.txt
├── frontend/          # Web interface
│   ├── templates/    # HTML pages
│   └── static/       # CSS, JS, images
├── k8s/              # Kubernetes configs (for advanced users)
├── docker-compose.yml # Docker orchestration
└── .env              # Your configuration (created in Step 1)
```

---

## 🆘 Need More Help?

### Additional Documentation
- **Detailed Setup Guide:** `LOCAL_SETUP_GUIDE.md`
- **Kubernetes Deployment:** `KIND_DEPLOYMENT_GUIDE.md`
- **Security Information:** `SECURITY.md`
- **API Documentation:** See `README.md`

### Quick Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up --build -d` | Start all services |
| `docker-compose down` | Stop all services |
| `docker-compose down -v` | Stop and delete all data |
| `docker-compose ps` | Check container status |
| `docker-compose logs -f` | View live logs |
| `docker-compose restart` | Restart all services |

---

## ✅ Success Checklist

Before you finish, make sure:

- [ ] Docker is installed and running
- [ ] `.env` file created with configuration
- [ ] All 3 containers show "Up" status
- [ ] Can access http://localhost in browser
- [ ] Can login with admin credentials
- [ ] Can add a course
- [ ] Can add students (manual or CSV)
- [ ] QR codes are generated
- [ ] Scanner can read QR codes
- [ ] Attendance records are saved

---

## 🎓 What You've Accomplished

You now have a fully functional QR Code Student Attendance System running locally with:

✅ Web-based admin dashboard  
✅ Student management with QR code generation  
✅ Live QR code scanner for attendance tracking  
✅ Course management  
✅ Attendance records with export capability  
✅ Secure authentication system  
✅ Database persistence  

**Happy testing! 🚀**
