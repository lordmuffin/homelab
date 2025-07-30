# KASM SSL Troubleshooting - RESOLVED

## Issue Resolved: 2025-07-30

### Problem
KASM API was failing with SSL connection error:
```
server does not support SSL, but SSL was required
```

### Root Cause
1. PostgreSQL had SSL disabled (`ssl = off` in configuration)
2. SSL certificates were in wrong format (PKCS#8 instead of RSA format required by PostgreSQL)

### Solution Applied

#### 1. Updated PostgreSQL Configuration
- Modified `kasm-db-configmap` ConfigMap to enable SSL:
```yaml
postgresql.conf: |
  # ... existing config ...
  # SSL Configuration
  ssl = on
  ssl_cert_file = '/etc/ssl/certs/db_server.crt'
  ssl_key_file = '/etc/ssl/certs/db_server.key'
```

#### 2. Generated Proper SSL Certificates
- Created new self-signed certificates in RSA format (required by PostgreSQL)
- Updated `kasm-db-cert` secret with proper certificate format:
  - Certificate: X.509 format
  - Private Key: RSA format (-----BEGIN RSA PRIVATE KEY-----)

#### 3. Applied Changes
- Restarted PostgreSQL StatefulSet to apply configuration changes
- Restarted KASM API deployment to test SSL connection

### Verification
- ✅ PostgreSQL starts successfully with SSL enabled
- ✅ No more "server does not support SSL" errors in KASM API logs
- ✅ SSL connection established (API now shows authentication errors instead of SSL errors)

### Commands Used
```bash
# Enable SSL in PostgreSQL configuration
kubectl patch configmap kasm-db-configmap -n kasm --patch='...'

# Generate proper SSL certificates
openssl genrsa -out server_rsa.key 2048
openssl req -new -x509 -key server_rsa.key -out server.crt -days 365 -subj '/CN=db'
openssl rsa -in server_rsa.key -traditional -out server_rsa_traditional.key

# Update certificate secret
kubectl delete secret kasm-db-cert -n kasm
kubectl create secret generic kasm-db-cert -n kasm --from-file=tls.crt=server.crt --from-file=tls.key=server_rsa_traditional.key

# Restart services
kubectl rollout restart statefulset kasm-db-statefulset -n kasm
kubectl rollout restart deployment kasm-api-deployment-fixed -n kasm
```

### Next Steps
The SSL connectivity issue has been resolved. The remaining authentication error (`password authentication failed for user "kasmapp"`) is a separate database user configuration issue unrelated to SSL.

### Reference
This troubleshooting followed the procedures outlined in `/docs/backup-patterns/TROUBLESHOOTING.md` section "🔒 SSL Connection Issues".