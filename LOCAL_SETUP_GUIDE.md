# Local Setup Guide: Docker & Kubernetes (Kind)

This guide walks you through running the QR Code Student Attendance System locally using Docker for containerization and Kind (Kubernetes in Docker) for orchestration.

## Prerequisites

Ensure you have the following installed:

- **Docker** (v20.10+) - [Install Docker](https://docs.docker.com/get-docker/)
- **kubectl** (Kubernetes CLI) - [Install kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- **Kind** (Kubernetes in Docker) - [Install Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- **Python 3.11+** (optional, for local development)
- **Git** (for cloning the repository)

Verify installations:
```bash
docker --version
kubectl version --client
kind version
```

---

## Option 1: Docker Compose (Simplest - Recommended for Development)

### Step 1: Create Environment File

Create a `.env` file in the project root with your configuration:

```bash
cat > .env << EOF
# Database Configuration
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=attendance_db
MYSQL_USER=attendance_user
MYSQL_PASSWORD=attendance_secure_password_2025

# JWT Configuration
JWT_SECRET=super_secure_jwt_secret_key_change_in_production_2025

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Email Configuration (Optional - for QR code email delivery)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Flask Environment
FLASK_ENV=production
EOF
```
### Required Create proxy 
mkdir -p apache
nano apache/proxy.conf

### Paset it inside proxy.conf
<VirtualHost *:80>

    ProxyPreserveHost On

    ProxyPass / http://backend:5000/
    ProxyPassReverse / http://backend:5000/

</VirtualHost>

### Step 2: Build and Start Containers

```bash
docker-compose up --build -d
```

This command:
- Builds the backend Flask application
- Starts MariaDB database
- Starts Nginx reverse proxy
- Creates necessary volumes for data persistence

### Step 3: Verify Services Are Running

```bash
docker-compose ps
```

You should see three containers:
- `attendance_db` - MariaDB database
- `attendance_backend` - Flask/Gunicorn application
- `attendance_nginx` - Nginx reverse proxy

### Step 4: Access the Application

Open your browser and navigate to:
- **Main Application**: http://localhost
- **Admin Login**: http://localhost/login

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

### Step 5: Test the System

1. **Login** with admin credentials
2. **View Dashboard** - See attendance statistics
3. **Upload CSV** - Import students via CSV file (max 2MB, 200 rows)
4. **Generate QR Codes** - Automatic QR generation for each student
5. **Mark Attendance** - Scan QR codes to mark attendance

### Step 6: View Logs (Troubleshooting)

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs backend
docker-compose logs db
docker-compose logs nginx
```

### Step 7: Stop the System

```bash
docker-compose down
```

To also remove volumes (delete all data):
```bash
docker-compose down -v
```

---

## Option 2: Kubernetes with Kind (Production-Like Environment)

### Step 1: Create Kind Cluster

Create a Kubernetes cluster with port mappings for external access:

```bash
kind create cluster --name attendance-cluster --config=- <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
```

### Step 2: Verify Cluster Is Running

```bash
kubectl cluster-info --context kind-attendance-cluster
kubectl get nodes
```

### Step 3: Install Nginx Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

Wait for the ingress controller to be ready:

```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

### Step 4: Generate Admin Password Hash

Generate a secure password hash for the admin user:

```bash
# Generate hash for password 'admin123'
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
```

Copy the output hash and update the secret:

```bash
# Replace <YOUR_HASH> with the generated hash
HASH="<YOUR_HASH>"
HASH_B64=$(echo -n "$HASH" | base64 -w0)

# Update the secret file
sed -i "s/ADMIN_PASSWORD_HASH:.*/ADMIN_PASSWORD_HASH: $HASH_B64/" k8s/secret.yaml
```

Or manually edit `k8s/secret.yaml` and replace the `ADMIN_PASSWORD_HASH` value with your base64-encoded hash.

### Step 5: Deploy All Kubernetes Resources

Apply all manifests in the correct order:

```bash
# Create namespace first
kubectl apply -f k8s/namespace.yaml

# Apply ConfigMap and Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy database with persistent storage
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/db-service.yaml

# Deploy backend application
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Configure autoscaling
kubectl apply -f k8s/hpa.yaml

# Setup ingress routing
kubectl apply -f k8s/ingress.yaml
```

Or apply all at once:
```bash
kubectl apply -f k8s/
```

### Step 6: Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n attendance-system

# Check services
kubectl get services -n attendance-system

# Check ingress
kubectl get ingress -n attendance-system

# Check horizontal pod autoscaler
kubectl get hpa -n attendance-system
```

Expected output:
```
NAME                                  READY   STATUS    RESTARTS   AGE
backend-deployment-xxxxxxxxxx-xxxxx   1/1     Running   0          2m
backend-deployment-xxxxxxxxxx-xxxxx   1/1     Running   0          2m
db-deployment-xxxxxxxxxx-xxxxx        1/1     Running   0          2m
```

### Step 7: Access the Application

#### Method A: Port Forwarding (Recommended for Local Testing)

```bash
# Forward ingress controller to localhost
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 80:80
```

Keep this terminal open and access:
- **Application**: http://localhost
- **Admin Panel**: http://localhost/admin

#### Method B: Direct Node Port Access

If you configured node ports, access via the node's IP and port.

### Step 8: Test Autoscaling

Monitor pod scaling based on CPU usage:

```bash
# Watch HPA status
kubectl get hpa -n attendance-system -w

# Simulate load (in another terminal)
while true; do curl http://localhost/dashboard; sleep 0.1; done
```

You should see replicas increase when CPU exceeds 70%.

### Step 9: View Logs

```bash
# View backend logs
kubectl logs -n attendance-system -l app=backend -f

# View database logs
kubectl logs -n attendance-system -l app=db -f

# View specific pod logs
kubectl logs -n attendance-system <pod-name>
```

### Step 10: Cleanup

When finished, delete the entire cluster:

```bash
kind delete cluster --name attendance-cluster
```

Or delete just the namespace:
```bash
kubectl delete namespace attendance-system
```

---

## Testing Security Features

### 1. Password Hashing Verification

The system uses Werkzeug's `generate_password_hash` and `check_password_hash`:

```bash
# Check that passwords are hashed in the code
grep -A 5 "check_password_hash" backend/app.py
```

### 2. Rate Limiting Test

Try multiple failed login attempts:

```bash
# Rapid login attempts (should get 429 after 5 requests)
for i in {1..10}; do
  curl -X POST http://localhost/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrong"}' \
    -w "\nAttempt $i: %{http_code}\n"
done
```

### 3. Security Headers Check

```bash
curl -I http://localhost
```

Look for headers:
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### 4. CSV Upload Validation

Test file upload restrictions:

```bash
# Try uploading a non-CSV file (should fail)
echo "malicious content" > test.txt
curl -X POST http://localhost/upload-csv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.txt"

# Try uploading oversized file (>2MB should fail)
dd if=/dev/zero of=large.csv bs=1M count=3
curl -X POST http://localhost/upload-csv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@large.csv"
```

---

## Troubleshooting

### Common Issues

#### 1. Backend Won't Connect to Database

**Symptom**: Backend logs show connection refused

**Solution**:
```bash
# Check if database is healthy
docker-compose ps db
# or
kubectl get pods -n attendance-system -l app=db

# Wait for database to be ready (health check passes)
docker-compose logs db | grep "ready for connections"
```

#### 2. Port 80 Already in Use

**Symptom**: Cannot start Nginx/Ingress

**Solution**:
```bash
# Find what's using port 80
sudo lsof -i :80

# Stop the conflicting service or use a different port
# For Kind, update extraPortMappings in cluster config
```

#### 3. Pods Stuck in Pending State

**Symptom**: `kubectl get pods` shows Pending

**Solution**:
```bash
# Check events for why pods are pending
kubectl describe pod <pod-name> -n attendance-system

# Usually resource constraints - ensure Docker has enough resources
# Increase Docker memory/CPU in Docker Desktop settings
```

#### 4. Ingress Not Working

**Symptom**: Cannot access via localhost

**Solution**:
```bash
# Verify ingress controller is running
kubectl get pods -n ingress-nginx

# Check ingress configuration
kubectl describe ingress attendance-ingress -n attendance-system

# Ensure port forwarding is active
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 80:80
```

#### 5. Password Hash Mismatch

**Symptom**: Cannot login with admin credentials

**Solution**:
```bash
# Regenerate password hash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"

# Update secret and redeploy
kubectl delete secret attendance-secret -n attendance-system
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment/backend-deployment -n attendance-system
```

### Debugging Commands

```bash
# Docker Compose debugging
docker-compose logs -f backend
docker exec -it attendance_db mysql -u attendance_user -pattendance_pass attendance_db

# Kubernetes debugging
kubectl describe pod <pod-name> -n attendance-system
kubectl exec -it <pod-name> -n attendance-system -- /bin/bash
kubectl top pods -n attendance-system  # Requires metrics-server
```

---

## Next Steps After Setup

1. **Add Students**: Upload a CSV file with student data
2. **Generate QR Codes**: Automatic on student creation
3. **Test Attendance Marking**: Use QR scanner or manual entry
4. **Configure Email**: Set up SMTP for QR code email delivery
5. **Enable HTTPS**: Uncomment HTTPS block in nginx.conf for production
6. **Deploy to Cloud**: Follow README.md guides for GKE/EKS deployment

---

## Architecture Overview

```
Browser → Nginx (port 80) → Gunicorn/Flask (port 5000) → MariaDB (port 3306)
                ↓
        Security Headers
        Rate Limiting
        SSL/TLS (optional)
```

**Kubernetes Layer:**
```
Ingress → Service (ClusterIP) → Pods (Backend × 2+) → PVC (Database)
                                    ↓
                              HPA (Auto-scaling)
```

---

## Security Checklist

✅ Password hashing with Werkzeug  
✅ JWT token authentication  
✅ Rate limiting on login (5 req/min)  
✅ Security headers (X-Frame-Options, CSP, HSTS)  
✅ CSV validation (MIME type, size limit, row limit)  
✅ Input sanitization (email regex, name stripping)  
✅ Container isolation (separate networks)  
✅ Resource limits (CPU/memory)  
✅ Horizontal pod autoscaling  
✅ Namespace isolation  

For detailed security analysis, see [SECURITY.md](SECURITY.md).

---

## Support

For issues or questions:
- Check logs: `docker-compose logs` or `kubectl logs`
- Review [README.md](README.md) for API documentation
- See [SECURITY.md](SECURITY.md) for security details
- Consult [KIND_DEPLOYMENT_GUIDE.md](KIND_DEPLOYMENT_GUIDE.md) for Kubernetes specifics
