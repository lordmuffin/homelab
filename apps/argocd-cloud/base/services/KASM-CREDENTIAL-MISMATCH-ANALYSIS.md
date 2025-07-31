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