FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow, MySQL client, and dlib
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    g++ \
    pkg-config \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY . .

# Copy frontend templates and static files
COPY frontend/templates ./templates/
COPY frontend/static ./static/

# Create qrcodes directory structure
RUN mkdir -p frontend/static/images/qrcodes

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:app"]
