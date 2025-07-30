# KASM Post-Deployment Manual Steps

This document outlines the manual steps that were required during troubleshooting and should be automated or documented for future deployments.

## Database User Creation and Permissions

After the database is initialized, the following steps are required:

### 1. Create kasmapp User
The manager pod connects as `kasmapp` user, but only the `kasm` user exists by default.

```bash
# Create kasmapp user with password from kasm-all-in-one-secrets
DB_PASSWORD=$(kubectl get secret kasm-all-in-one-secrets -n kasm -o jsonpath='{.data.db-password}' | base64 -d)
kubectl exec -it kasm-database-1 -n kasm -- env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' psql -U postgres -c "CREATE USER kasmapp WITH PASSWORD '$DB_PASSWORD';"
kubectl exec -it kasm-database-1 -n kasm -- env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE kasm TO kasmapp;"
```

### 2. Grant Database Permissions
Both `kasm` (API) and `kasmapp` (Manager) users need access to database tables:

```bash
# Grant permissions to kasm user (API)
kubectl exec -it kasm-database-1 -n kasm -- env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' psql -U postgres -d kasm -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kasm;"
kubectl exec -it kasm-database-1 -n kasm -- env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' psql -U postgres -d kasm -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kasm;"

# Grant kasm role to kasmapp user for table access
kubectl exec -it kasm-database-1 -n kasm -- env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' psql -U postgres -d kasm -c "GRANT kasm TO kasmapp;"
```

## Database Pod Labeling

The database service requires the database pod to have the `app.kubernetes.io/name=kasm-db` label:

```bash
# Add required label to database pod
kubectl label pod kasm-database-1 -n kasm app.kubernetes.io/name=kasm-db
```

## Troubleshooting Notes

### Issues Resolved During Deployment:

1. **Database Service Endpoints**: Service selector didn't match pod labels
2. **Database User Authentication**: Missing kasmapp user and incorrect passwords
3. **Database Initialization**: Empty database (no tables)
4. **Database Permissions**: Permission denied errors for both users
5. **Probe Timeouts**: Insufficient startup time for complex initialization
6. **Service Dependencies**: Manager waiting for API readiness

### Configuration Changes Made:

1. **Manager Deployment**: Increased probe delays to 120s
2. **API Deployment**: Increased readiness probe timeout to 30s
3. **Database**: Added service selector label
4. **Permissions**: Granted proper table access to both database users

### Future Improvements:

1. **Automate User Creation**: Add kasmapp user creation to database initialization
2. **Automate Permissions**: Include permission grants in database init scripts
3. **Automate Labeling**: Use init jobs or operators to ensure proper pod labeling
4. **Health Checks**: Implement better startup health checks with retries
5. **Documentation**: Document the complete startup sequence and dependencies

## Component Startup Order

The correct startup sequence is:
1. Database pod (with proper labels)
2. Database initialization job (creates tables and data)
3. API pod (depends on database)
4. Manager pod (depends on API)
5. Other components (depend on API/Manager)

## Monitoring

Monitor these key indicators:
- Database pod has `app.kubernetes.io/name=kasm-db` label
- Database service has endpoints
- API pod is ready (1/1)
- Manager pod progresses past init container
- All services have proper endpoints