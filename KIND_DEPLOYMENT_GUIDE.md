# Step-by-Step Guide: Running QR Attendance System on Kubernetes (Kind) with Docker

This guide walks you through deploying the QR Code Student Attendance System to a local Kubernetes cluster using **Kind (Kubernetes in Docker)**. This setup runs entirely within Docker on your machine.

## Prerequisites

Ensure you have the following installed:
- **Docker** (Desktop or Engine) - Running and accessible
- **Kind** - `kind version` should work
- **kubectl** - Kubernetes command-line tool
- **Git** - To clone/access the project

Verify installations:
```bash
docker --version
kind version
kubectl version --client
```

---

## Step 1: Create the Kind Cluster

Create a Kubernetes cluster inside Docker containers:

```bash
kind create cluster --name attendance-cluster --config=- <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
```

**What this does:**
- Creates a cluster named `attendance-cluster`
- Maps ports 80 and 443 from your host to the cluster (so you can access via localhost)

Verify cluster is running:
```bash
kubectl cluster-info --context kind-attendance-cluster
```

---

## Step 2: Install Nginx Ingress Controller

The Ingress Controller routes external traffic to your services:

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

Wait for it to be ready:
```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

Verify:
```bash
kubectl get pods -n ingress-nginx
```

---

## Step 3: Prepare Environment Variables

### 3.1 Generate Admin Password Hash

The system uses hashed passwords. Generate one:

```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
```

Copy the output (starts with `scrypt:` or `pbkdf2:`).

### 3.2 Update the Secret File

Edit `/workspace/k8s/secret.yaml` and replace the placeholder with your generated hash:

```bash
# Example: Replace the ADMIN_PASSWORD_HASH value
# The file uses base64 encoding, so encode your hash:
echo -n 'your_generated_hash_here' | base64
```

Update the secret.yaml with the base64-encoded values:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: attendance-secret
  namespace: attendance-system
type: Opaque
data:
  MYSQL_ROOT_PASSWORD: cm9vdHBhc3N3b3JkMTIz  # base64 of 'rootpassword123'
  MYSQL_DATABASE: YXR0ZW5kYW5jZV9kYg==      # base64 of 'attendance_db'
  MYSQL_USER: YXR0ZW5kYW5jZV91c2Vy         # base64 of 'attendance_user'
  MYSQL_PASSWORD: dXNlcnBhc3N3b3JkMTIz       # base64 of 'userpassword123'
  JWT_SECRET_KEY: eW91cl9zdXBlcl9zZWNyZXRfa2V5X2hlcmU=  # base64 of your secret
  ADMIN_USERNAME: YWRtaW4=                    # base64 of 'admin'
  ADMIN_PASSWORD_HASH: <YOUR_BASE64_HASH_HERE>
  MAIL_USERNAME: eG94QGdtYWlsLmNvbQ==         # base64 of your email
  MAIL_PASSWORD: eW91cl9hcHBfcGFzc3dvcmQ=     # base64 of app password
```

**Quick one-liner to update secret.yaml with a password hash:**
```bash
HASH=$(python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))")
HASH_B64=$(echo -n "$HASH" | base64 -w0)
sed -i "s/ADMIN_PASSWORD_HASH:.*/ADMIN_PASSWORD_HASH: $HASH_B64/" /workspace/k8s/secret.yaml
```

---

## Step 4: Deploy to Kubernetes

Apply all manifests in order:

### 4.1 Create Namespace
```bash
kubectl apply -f /workspace/k8s/namespace.yaml
```

### 4.2 Create ConfigMap and Secret
```bash
kubectl apply -f /workspace/k8s/configmap.yaml
kubectl apply -f /workspace/k8s/secret.yaml
```

### 4.3 Create Persistent Volume Claim (for Database)
```bash
kubectl apply -f /workspace/k8s/pvc.yaml
```

### 4.4 Deploy Database
```bash
kubectl apply -f /workspace/k8s/db-deployment.yaml
kubectl apply -f /workspace/k8s/db-service.yaml
```

Wait for DB to be ready:
```bash
kubectl wait --for=condition=ready pod -l app=mariadb -n attendance-system --timeout=120s
```

### 4.5 Deploy Backend
```bash
kubectl apply -f /workspace/k8s/backend-deployment.yaml
kubectl apply -f /workspace/k8s/backend-service.yaml
```

### 4.6 Deploy Horizontal Pod Autoscaler
```bash
kubectl apply -f /workspace/k8s/hpa.yaml
```

### 4.7 Deploy Ingress
```bash
kubectl apply -f /workspace/k8s/ingress.yaml
```

---

## Step 5: Verify Deployment

Check all resources:
```bash
kubectl get all -n attendance-system
```

Expected output:
```
NAME                                  READY   STATUS    RESTARTS   AGE
pod/attendance-backend-xxxxx-abcde    1/1     Running   0          2m
pod/attendance-backend-xxxxx-fghij    1/1     Running   0          2m
pod/mariadb-xxxxx-klmno               1/1     Running   0          3m

NAME                       TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)    AGE
service/attendance-backend ClusterIP   10.96.xxx.xxx    <none>        5000/TCP   2m
service/mariadb            ClusterIP   10.96.yyy.yyy    <none>        3306/TCP   3m

NAME                                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/attendance-backend       2/2     2            2           2m
deployment.apps/mariadb                  1/1     1            1           3m

NAME                                                DESIRED   CURRENT   READY   AGE
horizontalpodautoscaler.autoscaling/attendance-hpa  2         2         2       2m
```

Check Ingress:
```bash
kubectl get ingress -n attendance-system
```

---

## Step 6: Access the Application

Since we mapped port 80 in Step 1, access directly:

**Open browser:** `http://localhost`

Or use curl:
```bash
curl -I http://localhost
```

You should see security headers in response:
```
HTTP/1.1 200 OK
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

**Default Login:**
- Username: `admin`
- Password: `admin123` (or whatever you set)

---

## Step 7: Test Features

### 7.1 Test Auto-Scaling
Generate load to trigger HPA:
```bash
# Watch HPA status
kubectl get hpa -n attendance-system -w

# In another terminal, generate load
for i in {1..100}; do curl http://localhost & done
```

You should see replica count increase when CPU > 70%.

### 7.2 Test Rate Limiting
Try rapid login attempts:
```bash
for i in {1..20}; do curl -X POST http://localhost/login -d "username=test&password=test" & done
```

After 5-10 requests, you should get `429 Too Many Requests`.

### 7.3 Test CSV Upload
1. Login to the web interface
2. Navigate to upload section
3. Try uploading a CSV file
4. Files > 2MB or non-CSV will be rejected

---

## Step 8: Monitor and Debug

### View Logs
```bash
# Backend logs
kubectl logs -n attendance-system -l app=backend -f

# Database logs
kubectl logs -n attendance-system -l app=mariadb -f

# Ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller -f
```

### Check Events
```bash
kubectl get events -n attendance-system --sort-by='.lastTimestamp'
```

### Exec into Container
```bash
kubectl exec -it -n attendance-system $(kubectl get pod -n attendance-system -l app=backend -o jsonpath='{.items[0].metadata.name}') -- /bin/bash
```

---

## Step 9: Cleanup (When Done)

Delete the entire cluster:
```bash
kind delete cluster --name attendance-cluster
```

Or delete just the namespace:
```bash
kubectl delete namespace attendance-system
```

---

## Troubleshooting

### Issue: Ingress shows `<pending>` or no external IP
**Solution:** Kind doesn't assign external IPs. Use port mapping (Step 1) or port-forward:
```bash
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 80:80
```

### Issue: Pods stuck in `Pending`
**Solution:** Check resources:
```bash
kubectl describe pod <pod-name> -n attendance-system
```

### Issue: Database connection failed
**Solution:** Ensure DB is ready before backend starts:
```bash
kubectl rollout restart deployment/attendance-backend -n attendance-system
```

### Issue: Security headers missing
**Solution:** Verify nginx.conf is mounted correctly:
```bash
kubectl exec -n attendance-system $(kubectl get pod -n attendance-system -l app=backend -o jsonpath='{.items[0].metadata.name}') -- cat /etc/nginx/conf.d/default.conf
```

---

## Architecture Overview

```
┌─────────────┐
│   Browser   │
│ localhost:80│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Kind Kubernetes Cluster     │
│  ┌───────────────────────────────┐  │
│  │   Nginx Ingress Controller    │  │
│  │   (routes to backend)         │  │
│  └──────────────┬────────────────┘  │
│                 │                   │
│                 ▼                   │
│  ┌───────────────────────────────┐  │
│  │   attendance-backend (2x)     │  │
│  │   Flask + Gunicorn            │  │
│  │   - Security Headers          │  │
│  │   - Rate Limiting             │  │
│  │   - JWT Auth                  │  │
│  │   - CSV Validation            │  │
│  └──────────────┬────────────────┘  │
│                 │                   │
│                 ▼                   │
│  ┌───────────────────────────────┐  │
│  │   mariadb                     │  │
│  │   Persistent Volume           │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## Next Steps

1. **Enable HTTPS**: Add TLS certificates via cert-manager
2. **Persistent Storage**: Configure dynamic PV provisioning for cloud
3. **Monitoring**: Install Prometheus + Grafana
4. **CI/CD**: Set up GitHub Actions to auto-deploy on push
5. **Cloud Migration**: Use same manifests on GKE/EKS with minor changes

Your system is now running with:
✅ Containerization (Docker)
✅ Orchestration (Kubernetes via Kind)
✅ Auto-scaling (HPA)
✅ Security Headers & Rate Limiting
✅ Password Hashing
✅ CSV Hardening
✅ Isolated Namespace

Ready for demonstration! 🎉
