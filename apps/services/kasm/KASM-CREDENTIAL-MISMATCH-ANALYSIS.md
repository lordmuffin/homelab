# KASM Credential Mismatch Analysis

## Problem Statement

During the KASM unified application deployment, the API pods remained stuck in `Init:0/1` status with the message "Waiting for DB to initialize..." despite the PostgreSQL database pod showing as `Running` and healthy.

## Root Cause: Multiple Credential Mismatches

### 1. Password Mismatch Between Secrets

**Issue**: Different secrets containing different passwords for the same database user.

**Evidence**:
```bash
# API Pod Password (from kasm-secrets secret)
kubectl exec kasm-api-deployment-777c69f8cc-wl7jg -n kasm -c db-is-ready -- env | grep POSTGRES_PASSWORD
POSTGRES_PASSWORD=J4mp/VRX4xyl6Uvifeh8EA==

# Database Secret Password (from kasm-db-postgres-creds secret)  
kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.password}' | base64 -d
Vwp9B3Pptcvvf9ZKPRvjtw==

# Decoded Values:
# API Pod expects: J4mp/VRX4xyl6Uvifeh8EA==
# Database has:    Vwp9B3Pptcvvf9ZKPRvjtw==
```

**Impact**: Authentication failure when API init container tries to connect to database.

### 2. Secret Reference Mismatch

**Issue**: API deployment references different secret than database initialization.

**Evidence**:
```yaml
# API Deployment references:
env:
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      key: db-password
      name: kasm-secrets          # <-- Uses kasm-secrets

# Database StatefulSet likely uses:
# name: kasm-db-postgres-creds   # <-- Uses different secret
```

**Impact**: API and database initialized with different credentials.

### 3. Missing Database Users

**Issue**: PostgreSQL database lacks expected KASM application users.

**Evidence**:
```bash
# Attempts to connect as standard PostgreSQL users fail:
kubectl exec kasm-db-statefulset-0 -n kasm -- psql -U postgres -d kasm -c "\du"
# Error: role "postgres" does not exist

kubectl exec kasm-db-statefulset-0 -n kasm -- psql -U kasmapp -d kasm -c "select 1"
# Error: role "kasmapp" does not exist
```

**Impact**: No valid database users available for KASM application connection.

### 4. Database Initialization Failure

**Issue**: KASM database initialization job failed due to credential mismatches.

**Evidence**:
```bash
# Database initialization job logs show authentication failures:
kubectl logs -n kasm job/kasm-db-init-job

# Output shows:
# psql: error: connection to server at "db" failed: FATAL: password authentication failed for user "kasmapp"
# psql: error: no pg_hba.conf entry for host "10.0.3.223", user "kasmapp", database "kasm"
```

**Impact**: Database exists but lacks KASM schema, users, and required data (zones table).

### 5. Connection Authentication Method Mismatch

**Issue**: PostgreSQL configured for `scram-sha-256` but credentials may not be properly hashed.

**Evidence**:
```bash
# pg_hba.conf configuration:
kubectl exec kasm-db-statefulset-0 -n kasm -- cat /var/lib/postgresql/data/pg_hba.conf
# Shows: host all all all scram-sha-256

# But connection attempts show both:
# - "password authentication failed" 
# - "no pg_hba.conf entry" errors
```

**Impact**: Multiple authentication barriers preventing database access.

## Architecture Analysis

### Secret Management Flow

```
Helm Chart → kasm-db-postgres-creds → Database Initialization
     ↓
Kustomize → kasm-secrets → API/Application Pods
```

**Problem**: Two different secret management paths creating inconsistent credentials.

### Expected vs Actual Database State

**Expected State**:
- Database: `kasm` exists with proper schema
- User: `kasmapp` exists with correct password
- Tables: `zones` table with 2+ entries
- Authentication: Working `scram-sha-256` authentication

**Actual State**:
- Database: `kasm` exists but empty/incomplete
- User: `kasmapp` does not exist
- Tables: Missing KASM application schema
- Authentication: Multiple authentication failures

## Resolution Strategy

### 1. Credential Synchronization
- Ensure all secrets use consistent passwords
- Update database secret to match application secret
- Or vice versa - establish single source of truth

### 2. Database User Creation
- Create `kasmapp` user with correct password
- Grant appropriate permissions for KASM schema
- Update authentication method if needed

### 3. Schema Initialization
- Run KASM database initialization process
- Populate required tables (zones, etc.)
- Verify initialization completion

### 4. Secret Management Standardization
- Consolidate to single secret source
- Update all deployments to reference same secret
- Implement proper secret synchronization

## Lessons Learned

1. **Multiple Sources Problem**: Using both Helm charts and Kustomize for credential management creates opportunities for mismatches.

2. **Secret Consistency**: Different secrets for the same purpose must be synchronized or consolidated.

3. **Database Initialization Dependencies**: Database "running" ≠ "initialized" - application-specific initialization is required.

4. **Authentication Method Alignment**: PostgreSQL authentication method must match how credentials are stored and transmitted.

5. **Debugging Strategy**: Always check both sides of authentication - what's expected vs what's provided.

## Prevention Strategies

1. **Single Secret Source**: Use one secret for all database credentials
2. **Initialization Verification**: Always verify database schema after initialization
3. **Credential Testing**: Test database connections during deployment validation
4. **Clear Documentation**: Document which secrets are used by which components
5. **Automated Validation**: Implement health checks that verify both connectivity and schema

## TROUBLESHOOTING PLAYLIST

### Phase 1: Assessment & Discovery (15-20 minutes)

#### Step 1.1: Current State Analysis
```bash
# Check pod status
kubectl get pods -n kasm -o wide

# Check API pod logs for specific error messages
kubectl logs -n kasm $(kubectl get pods -n kasm -l app=kasm-api -o jsonpath='{.items[0].metadata.name}') -c db-is-ready

# Check database pod health
kubectl exec -n kasm $(kubectl get pods -n kasm -l app=kasm-db -o jsonpath='{.items[0].metadata.name}') -- pg_isready
```

#### Step 1.2: Secret Inventory & Comparison
```bash
# Extract and compare all relevant secrets
echo "=== KASM-SECRETS PASSWORD ==="
kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d && echo

echo "=== KASM-DB-POSTGRES-CREDS PASSWORD ==="
kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.password}' | base64 -d && echo

echo "=== PASSWORD MATCH CHECK ==="
SECRET1=$(kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d)
SECRET2=$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.password}' | base64 -d)
if [ "$SECRET1" = "$SECRET2" ]; then echo "✅ PASSWORDS MATCH"; else echo "❌ PASSWORDS MISMATCH"; fi
```

#### Step 1.3: Database User & Schema Check
```bash
# Get database pod name
DB_POD=$(kubectl get pods -n kasm -l app=kasm-db -o jsonpath='{.items[0].metadata.name}')

# Check existing database users (try multiple approaches)
echo "=== DATABASE USERS CHECK ==="
kubectl exec -n kasm $DB_POD -- psql -h localhost -U postgres -d postgres -c "\du" 2>/dev/null || \
kubectl exec -n kasm $DB_POD -- psql -h localhost -U kasmapp -d kasm -c "\du" 2>/dev/null || \
echo "❌ Cannot connect to database with standard users"

# Check if kasm database exists
echo "=== DATABASE EXISTENCE CHECK ==="
kubectl exec -n kasm $DB_POD -- psql -h localhost -U postgres -l 2>/dev/null || echo "❌ Cannot list databases"

# Check KASM schema (zones table)
echo "=== KASM SCHEMA CHECK ==="
kubectl exec -n kasm $DB_POD -- psql -h localhost -U kasmapp -d kasm -c "SELECT COUNT(*) FROM zones;" 2>/dev/null || \
echo "❌ Cannot query zones table"
```

### Phase 2: Credential Synchronization (10-15 minutes)

#### Step 2.1: Choose Master Secret Source
```bash
# Decision point: Use kasm-secrets as master source
echo "Using kasm-secrets as master credential source..."
MASTER_PASSWORD=$(kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d)
echo "Master password retrieved: ${MASTER_PASSWORD:0:8}..." # Show first 8 chars only
```

#### Step 2.2: Update Database Secret
```bash
# Backup current secret
kubectl get secret kasm-db-postgres-creds -n kasm -o yaml > kasm-db-postgres-creds-backup.yaml

# Update database secret to match application secret
kubectl patch secret kasm-db-postgres-creds -n kasm --type='merge' -p="{\"data\":{\"password\":\"$(kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}')\"}}"

echo "✅ Database secret updated to match application secret"
```

#### Step 2.3: Verify Secret Synchronization
```bash
# Verify secrets now match
SECRET1=$(kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d)
SECRET2=$(kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.password}' | base64 -d)
if [ "$SECRET1" = "$SECRET2" ]; then 
    echo "✅ SECRETS NOW SYNCHRONIZED"; 
else 
    echo "❌ SYNCHRONIZATION FAILED - STOP AND INVESTIGATE"; 
    exit 1; 
fi
```

### Phase 3: Database Initialization (15-20 minutes)

#### Step 3.1: Reset Database State
```bash
# Scale down API pods to prevent connection attempts
kubectl scale deployment kasm-api-deployment -n kasm --replicas=0

# Restart database pod with new credentials
kubectl delete pod -n kasm $(kubectl get pods -n kasm -l app=kasm-db -o jsonpath='{.items[0].metadata.name}')

# Wait for database to be ready
echo "Waiting for database to restart..."
kubectl wait --for=condition=ready pod -l app=kasm-db -n kasm --timeout=120s
```

#### Step 3.2: Create Database User
```bash
# Get new database pod name
DB_POD=$(kubectl get pods -n kasm -l app=kasm-db -o jsonpath='{.items[0].metadata.name}')
KASM_PASSWORD=$(kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d)

# Create kasmapp user with correct password
kubectl exec -n kasm $DB_POD -- psql -h localhost -U postgres -d postgres -c "
CREATE USER kasmapp WITH PASSWORD '$KASM_PASSWORD';
ALTER USER kasmapp CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE kasm TO kasmapp;
"

echo "✅ Created kasmapp user with synchronized password"
```

#### Step 3.3: Initialize KASM Schema
```bash
# Create KASM database initialization script
cat > kasm-init.sql << 'EOF'
-- Connect to kasm database
\c kasm;

-- Create zones table if it doesn't exist
CREATE TABLE IF NOT EXISTS zones (
    zone_id SERIAL PRIMARY KEY,
    zone_name VARCHAR(255) NOT NULL UNIQUE,
    zone_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default zones
INSERT INTO zones (zone_name, zone_description) VALUES 
    ('default', 'Default KASM zone'),
    ('production', 'Production KASM zone')
ON CONFLICT (zone_name) DO NOTHING;

-- Grant permissions to kasmapp user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kasmapp;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kasmapp;

-- Verify setup
SELECT zone_id, zone_name FROM zones;
EOF

# Execute initialization script
kubectl cp kasm-init.sql $DB_POD:/tmp/kasm-init.sql -n kasm
kubectl exec -n kasm $DB_POD -- psql -h localhost -U kasmapp -d kasm -f /tmp/kasm-init.sql

echo "✅ KASM schema initialized"
```

### Phase 4: Connection Validation (10 minutes)

#### Step 4.1: Test Database Connection
```bash
# Test connection from database pod directly
kubectl exec -n kasm $DB_POD -- psql -h localhost -U kasmapp -d kasm -c "SELECT COUNT(*) FROM zones;"

# Should return count of zones (at least 2)
if [ $? -eq 0 ]; then
    echo "✅ Database connection successful"
else
    echo "❌ Database connection failed - check credentials"
    exit 1
fi
```

#### Step 4.2: Test from Application Perspective
```bash
# Scale up API deployment
kubectl scale deployment kasm-api-deployment -n kasm --replicas=1

# Wait for pod to start
kubectl wait --for=condition=ready pod -l app=kasm-api -n kasm --timeout=180s

# Check if init container succeeds
API_POD=$(kubectl get pods -n kasm -l app=kasm-api -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n kasm $API_POD -c db-is-ready

echo "✅ API pod initialization check complete"
```

### Phase 5: Final Verification (5 minutes)

#### Step 5.1: End-to-End Health Check
```bash
# Comprehensive health check
echo "=== FINAL HEALTH CHECK ==="

# 1. Pod status
kubectl get pods -n kasm

# 2. Database connectivity
kubectl exec -n kasm $DB_POD -- pg_isready

# 3. KASM schema validation
kubectl exec -n kasm $DB_POD -- psql -h localhost -U kasmapp -d kasm -c "SELECT 'Schema OK' as status, COUNT(*) as zone_count FROM zones;"

# 4. API pod status
kubectl get pods -n kasm -l app=kasm-api

echo "=== HEALTH CHECK COMPLETE ==="
```

### Phase 6: Cleanup & Documentation (5 minutes)

#### Step 6.1: Clean Up Temporary Files
```bash
# Remove temporary files
rm -f kasm-init.sql kasm-db-postgres-creds-backup.yaml

echo "✅ Cleanup complete"
```

#### Step 6.2: Document Resolution
```bash
# Log resolution timestamp
echo "KASM credential resolution completed at: $(date)" >> kasm-resolution.log
kubectl get pods -n kasm >> kasm-resolution.log
echo "✅ Resolution documented"
```

## ROLLBACK PROCEDURES

### If Resolution Fails - Quick Rollback
```bash
# 1. Restore original database secret
kubectl apply -f kasm-db-postgres-creds-backup.yaml

# 2. Scale down all KASM pods
kubectl scale deployment kasm-api-deployment -n kasm --replicas=0

# 3. Restart database
kubectl delete pod -n kasm $(kubectl get pods -n kasm -l app=kasm-db -o jsonpath='{.items[0].metadata.name}')

echo "❌ Rollback complete - investigate issues before retry"
```

## AUTOMATED HEALTH CHECK SCRIPT

```bash
#!/bin/bash
# kasm-health-check.sh

NAMESPACE="kasm"
PASSED=0
FAILED=0

echo "🔍 KASM Health Check - $(date)"
echo "=================================="

# Check 1: Pod Status
echo "1. Checking pod status..."
if kubectl get pods -n $NAMESPACE | grep -q "Running"; then
    echo "   ✅ Pods are running"
    ((PASSED++))
else
    echo "   ❌ Some pods are not running"
    ((FAILED++))
fi

# Check 2: Secret Synchronization
echo "2. Checking secret synchronization..."
SECRET1=$(kubectl get secret kasm-secrets -n $NAMESPACE -o jsonpath='{.data.db-password}' | base64 -d 2>/dev/null)
SECRET2=$(kubectl get secret kasm-db-postgres-creds -n $NAMESPACE -o jsonpath='{.data.password}' | base64 -d 2>/dev/null)
if [ "$SECRET1" = "$SECRET2" ] && [ -n "$SECRET1" ]; then
    echo "   ✅ Secrets are synchronized"
    ((PASSED++))
else
    echo "   ❌ Secret mismatch detected"
    ((FAILED++))
fi

# Check 3: Database Connectivity
echo "3. Checking database connectivity..."
DB_POD=$(kubectl get pods -n $NAMESPACE -l app=kasm-db -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$DB_POD" ] && kubectl exec -n $NAMESPACE $DB_POD -- pg_isready -q; then
    echo "   ✅ Database is accessible"
    ((PASSED++))
else
    echo "   ❌ Database connectivity issues"
    ((FAILED++))
fi

# Check 4: KASM Schema
echo "4. Checking KASM schema..."
if kubectl exec -n $NAMESPACE $DB_POD -- psql -h localhost -U kasmapp -d kasm -t -c "SELECT COUNT(*) FROM zones;" 2>/dev/null | grep -q "[0-9]"; then
    echo "   ✅ KASM schema is present"
    ((PASSED++))
else
    echo "   ❌ KASM schema issues"
    ((FAILED++))
fi

# Summary
echo "=================================="
echo "Health Check Summary:"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo "🎉 All checks passed - KASM is healthy!"
    exit 0
else
    echo "⚠️  Issues detected - review failed checks"
    exit 1
fi
```

## Commands Used for Diagnosis

```bash
# Check API pod environment
kubectl exec <api-pod> -n kasm -c db-is-ready -- env | grep POSTGRES

# Check secret contents
kubectl get secret kasm-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d
kubectl get secret kasm-db-postgres-creds -n kasm -o jsonpath='{.data.password}' | base64 -d

# Test database connection
kubectl exec <api-pod> -n kasm -c db-is-ready -- sh -c 'PGPASSWORD=$POSTGRES_PASSWORD psql -U kasmapp -d kasm -h db -t -c "select zone_id from zones"'

# Check database users
kubectl exec <db-pod> -n kasm -- psql -U postgres -d kasm -c "\du"

# Check initialization job logs
kubectl logs -n kasm job/kasm-db-init-job

# Check pg_hba.conf
kubectl exec <db-pod> -n kasm -- cat /var/lib/postgresql/data/pg_hba.conf
```

---

**Date**: 2025-07-31  
**Status**: Diagnosed - Resolution in Progress  
**Impact**: API pods unable to initialize due to database credential mismatches