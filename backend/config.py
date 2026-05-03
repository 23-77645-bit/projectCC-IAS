import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'attendance_db')

MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
MAIL_PORT = os.getenv('MAIL_PORT', '25')
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False')
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False')
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@attendance.local')

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'change-me')
