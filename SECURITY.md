# Security Analysis & Risk Assessment

## QR Code Student Attendance System

**Version:** 1.0  
**Last Updated:** 2025  
**Institution:** Batangas State University ARASOF-Nasugbu

---

## Executive Summary

This document provides a comprehensive security analysis of the QR Code Student Attendance System, identifying potential attack surfaces, associated risks, and implemented mitigation strategies. The assessment follows industry best practices and aligns with the CIA Triad (Confidentiality, Integrity, Availability) framework.

---

## 1. Identified Attack Surfaces and Risks

### 1.1 Brute-Force Login Attacks

**Risk Description:**  
Attackers may attempt to gain unauthorized access by systematically trying multiple username/password combinations against the `/login` endpoint. Successful brute-force attacks could lead to administrative compromise, data exfiltration, or system manipulation.

**Impact:** High  
**Likelihood:** Medium (without mitigation)

**Mitigation Strategies Implemented:**
- **Rate Limiting via Nginx:** The `/login` route is protected with rate limiting configured at 5 requests per minute per IP address with a burst allowance of 5 requests. Excessive attempts return HTTP 429 (Too Many Requests).
- **Password Hashing:** Admin passwords are stored as cryptographic hashes using `werkzeug.security.generate_password_hash()` and verified using `check_password_hash()`, preventing plaintext exposure even if configuration files are compromised.
- **JWT Token Expiration:** Authentication tokens expire after 24 hours, limiting the window of opportunity for token reuse attacks.

**Recommended Enhancements:**
- Implement account lockout after N failed attempts
- Add CAPTCHA verification after multiple failed logins
- Enable multi-factor authentication (MFA) for admin accounts

---

### 1.2 CSV Injection and Malicious File Upload

**Risk Description:**  
The `/upload-csv` endpoint accepts student data uploads. Attackers could exploit this by uploading malicious CSV files containing formula injection payloads (e.g., `=cmd|'/C calc'!A0`), oversized files causing denial-of-service, or files with disguised content types.

**Impact:** High  
**Likelihood:** Medium

**Mitigation Strategies Implemented:**
- **MIME Type Validation:** Files are validated using `python-magic` library to verify actual content type matches the expected `text/csv` MIME type, preventing extension spoofing attacks.
- **File Size Limit:** Uploads are restricted to a maximum of 2MB, preventing resource exhaustion from oversized files.
- **Row Count Limit:** CSV processing is limited to 200 students per upload to prevent denial-of-service through excessive database operations.
- **Field Sanitization:** All CSV fields undergo sanitization:
  - Email addresses are validated against RFC 5322 compliant regex patterns
  - Names are stripped of non-printable characters and leading/trailing whitespace
  - Special characters that could enable SQL injection are parameterized via prepared statements

**Recommended Enhancements:**
- Scan uploaded files with antivirus/malware detection
- Implement asynchronous processing for large uploads
- Add audit logging for all upload activities

---

### 1.3 Exposed Backend Port

**Risk Description:**  
Direct exposure of the Flask/Gunicorn backend on port 5000 bypasses security controls implemented at the reverse proxy layer (Nginx), including rate limiting, security headers, and access logging.

**Impact:** Medium  
**Likelihood:** Low (with proper configuration)

**Mitigation Strategies Implemented:**
- **Docker Network Isolation:** In production Docker Compose configuration, the backend service communicates only within the internal `attendance_network`. External access should be routed exclusively through Nginx on port 80.
- **Kubernetes Service Configuration:** Backend is exposed as a ClusterIP service accessible only within the cluster, with external traffic routed through Ingress controller.
- **Development vs. Production Separation:** Port 5000 mapping in docker-compose.yml is documented for development purposes only and should be removed in production deployments.

**Recommended Enhancements:**
- Remove port 5000 exposure entirely in production docker-compose.yml
- Implement network policies in Kubernetes to restrict pod-to-pod communication
- Use private subnets for backend services in cloud deployments

---

### 1.4 QR Code Spoofing

**Risk Description:**  
Attackers may attempt to forge QR codes to record fraudulent attendance by generating valid-looking QR data or replaying captured QR scans.

**Impact:** Medium  
**Likelihood:** Medium

**Mitigation Strategies Implemented:**
- **UUID-Based QR Data:** Each student QR code contains a cryptographically random UUID v4 identifier generated server-side, making prediction computationally infeasible.
- **Server-Side Validation:** QR data is validated against the database; only registered UUIDs are accepted for attendance recording.
- **Timestamp Tracking:** The system tracks time-in and time-out, enabling detection of anomalous scanning patterns.

**Recommended Enhancements:**
- Implement QR code rotation (time-based one-time tokens)
- Add device fingerprinting to detect unusual scanner behavior
- Enable geofencing to restrict attendance recording to physical classroom locations
- Implement scan rate limiting per student

---

### 1.5 Weak JWT Secret

**Risk Description:**  
Using default, predictable, or weak JWT secret keys enables attackers to forge authentication tokens, gaining unauthorized access to protected endpoints.

**Impact:** Critical  
**Likelihood:** High (if defaults are not changed)

**Mitigation Strategies Implemented:**
- **Environment Variable Enforcement:** JWT secret is loaded exclusively from environment variables (`.env` file or container secrets), never hardcoded.
- **Startup Validation:** Application validates that a strong, non-default secret is configured at startup.
- **Kubernetes Secrets:** In Kubernetes deployments, the JWT secret is stored as a Kubernetes Secret object with base64 encoding, separate from ConfigMaps.

**Recommended Enhancements:**
- Implement secret rotation mechanism
- Use dedicated secrets management (HashiCorp Vault, AWS Secrets Manager)
- Enforce minimum secret complexity (length, character diversity)

---

### 1.6 Plaintext Passwords in Environment Variables

**Risk Description:**  
Storing sensitive credentials (database passwords, API keys, admin passwords) as plaintext environment variables creates exposure risk through process inspection, log leakage, or configuration file access.

**Impact:** High  
**Likelihood:** Medium

**Mitigation Strategies Implemented:**
- **Docker Secrets Compatibility:** Architecture supports migration to Docker Swarm secrets for sensitive values.
- **Kubernetes Secrets:** Production Kubernetes manifests utilize Secret objects for all sensitive configuration, providing encryption-at-rest when etcd encryption is enabled.
- **Password Hashing:** Admin password is hashed at application startup using Werkzeug's secure hashing algorithm.

**Recommended Enhancements:**
- Migrate to external secrets management (Vault, AWS Secrets Manager, Azure Key Vault)
- Enable encryption for environment variable storage in container orchestration
- Implement secret scanning in CI/CD pipelines to prevent accidental commits

---

## 2. CIA Triad Mapping

### 2.1 Confidentiality

**Definition:** Ensuring that information is accessible only to authorized individuals.

**Implementation in This System:**

| Control | Implementation |
|---------|----------------|
| Authentication | JWT-based authentication with 24-hour expiration |
| Password Security | Cryptographic hashing using Werkzeug (PBKDF2-SHA256) |
| Access Control | Token-required decorators protect all API endpoints except login |
| Session Management | Secure session cookies with server-side token validation |
| Data Protection | Sensitive credentials stored in Kubernetes Secrets / Docker environment files |
| Network Security | Backend isolated behind Nginx reverse proxy; direct access restricted |

**Gaps Addressed:**
- Plaintext password comparison replaced with hashed verification
- Environment variables externalized from codebase
- Database credentials separated from application logic

---

### 2.2 Integrity

**Definition:** Maintaining accuracy and completeness of data throughout its lifecycle.

**Implementation in This System:**

| Control | Implementation |
|---------|----------------|
| Input Validation | Email format validation, name sanitization, UUID generation |
| SQL Injection Prevention | Parameterized queries using PyMySQL placeholders (%s) |
| File Upload Security | MIME type verification, size limits, row count restrictions |
| Data Validation | Foreign key constraints between students, courses, and attendance tables |
| Audit Trail | Timestamps on all records (created_at, attendance time-in/out) |
| QR Code Uniqueness | UUID v4 ensures globally unique, unpredictable identifiers |

**Gaps Addressed:**
- CSV field sanitization prevents injection attacks
- File upload hardening prevents malicious content
- Prepared statements eliminate SQL injection vectors

---

### 2.3 Availability

**Definition:** Ensuring reliable access to information and systems when needed.

**Implementation in This System:**

| Control | Implementation |
|---------|----------------|
| Container Orchestration | Docker Compose with health checks and restart policies |
| Database Health Checks | MariaDB health monitoring with automatic recovery |
| Horizontal Scaling | Kubernetes HPA configured for 70% CPU threshold (2-10 replicas) |
| Resource Limits | CPU/memory requests and limits prevent resource starvation |
| Persistent Storage | PVC for database ensures data survives pod restarts |
| Load Balancing | Kubernetes Services distribute traffic across backend pods |
| Reverse Proxy | Nginx provides connection pooling and request buffering |

**Gaps Addressed:**
- Kubernetes manifests enable auto-scaling under load
- Health probes enable automatic pod replacement
- Persistent volumes protect against data loss

---

## 3. Security Headers Implementation

The Nginx reverse proxy implements the following security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Frame-Options | SAMEORIGIN | Prevents clickjacking by restricting iframe embedding |
| X-Content-Type-Options | nosniff | Prevents MIME-type sniffing attacks |
| X-XSS-Protection | 1; mode=block | Enables browser XSS filtering |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | Enforces HTTPS connections |
| Content-Security-Policy | Restrictive policy | Limits resource loading to trusted sources |
| Referrer-Policy | strict-origin-when-cross-origin | Controls referrer information leakage |

---

## 4. Production Hardening Checklist

### Immediate Actions (Before Deployment)

- [ ] Change all default passwords in `.env` file
- [ ] Generate strong, random JWT secret (minimum 32 characters)
- [ ] Remove port 5000 exposure from docker-compose.yml
- [ ] Obtain and configure SSL certificates (Let's Encrypt recommended)
- [ ] Enable HTTPS redirect in Nginx configuration
- [ ] Review and restrict CORS policies if applicable

### Short-Term Enhancements (Within 1 Month)

- [ ] Implement account lockout after 5 failed login attempts
- [ ] Add CAPTCHA to login form
- [ ] Enable audit logging for all administrative actions
- [ ] Configure log aggregation and alerting
- [ ] Implement database backup strategy with encryption
- [ ] Set up monitoring dashboards (Prometheus + Grafana recommended)

### Long-Term Improvements (Within 3 Months)

- [ ] Migrate to external secrets management solution
- [ ] Implement multi-factor authentication for admin accounts
- [ ] Deploy Web Application Firewall (WAF) in front of ingress
- [ ] Conduct penetration testing by third-party security firm
- [ ] Implement CI/CD security scanning (SAST/DAST)
- [ ] Develop incident response plan and runbook

---

## 5. Compliance Considerations

### Data Privacy (Philippines Data Privacy Act of 2012)

This system processes personal information (student names, email addresses, attendance records). Compliance requirements include:

- **Purpose Limitation:** Data collected solely for attendance tracking
- **Data Minimization:** Only necessary fields stored (name, email, course affiliation)
- **Retention:** Define and implement data retention policy
- **Access Rights:** Implement mechanisms for data subject access requests
- **Breach Notification:** Establish procedure for notifying affected parties

### Educational Records (FERPA Considerations)

If deployed in institutions receiving U.S. federal funding:

- Attendance records constitute education records requiring protection
- Access logs should track who views or modifies student data
- Parent/guardian consent may be required for certain data processing

---

## 6. Incident Response Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| System Administrator | [To be assigned] | Initial triage and containment |
| Database Administrator | [To be assigned] | Database integrity verification |
| Security Officer | [To be assigned] | Breach assessment and notification |
| Course Instructor | Mr. Calvin John V. Placio | Academic oversight |

---

## 7. Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025 | Development Team | Initial security analysis document |

---

## 8. References

- OWASP Top 10 Web Application Security Risks
- NIST Cybersecurity Framework
- Philippines Data Privacy Act of 2012 (Republic Act No. 10173)
- Docker Security Best Practices
- Kubernetes Security Guidelines

---

**Disclaimer:** This security analysis represents the current understanding of system risks at the time of writing. Security is an ongoing process requiring regular review, updates, and adaptation to emerging threats. Organizations should conduct their own risk assessments and consult with security professionals before production deployment.
