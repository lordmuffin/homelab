# KASM Login Fix - Complete Solution

## 🎯 Problem Summary

The KASM deployment had multiple authentication issues preventing successful login:

1. **Admin Account Locked**: Account locked due to failed login attempts
2. **Wrong Password Hash**: Database password hash didn't match the provided password  
3. **Database User Confusion**: Mixed usage of `kasm` and `kasmapp` database users
4. **Secret Inconsistency**: Different secrets used by different components

## ✅ Solutions Implemented

### 1. Database User Standardization

**Files Updated:**
- `manager-container-patch.yaml`: Added `DATABASE_USER=kasm` and `POSTGRES_USER=kasm`
- `kasm-db-user-setup-job.yaml`: Removed `kasmapp` user creation, standardized on `kasm`
- `kasm-db-permissions-job.yaml`: Updated to grant permissions only to `kasm` user
- `kasm-db-complete-init-job.yaml`: Updated validation to check only `kasm` user

**Changes:**
- All KASM components (API and Manager) now use the single `kasm` database user
- Eliminated confusion between `kasm` and `kasmapp` users
- Simplified permission management

### 2. Secret Synchronization

**New File:**
- `kasm-secrets-sync-job.yaml`: Ensures `kasm-secrets` matches `kasm-all-in-one-secrets`

**Purpose:**
- Synchronizes password between different secret objects
- Runs early in deployment (sync-wave: 2)
- Prevents password mismatches between components

### 3. Admin Password Hash Correction  

**New File:**
- `kasm-admin-password-fix-job.yaml`: Corrects admin password hash and unlocks account

**Features:**
- Retrieves existing salt from database
- Generates correct SHA256 hash using `password + salt`
- Unlocks admin account and resets failed login attempts
- Runs after all other database setup (sync-wave: 8)

### 4. Manager Container Configuration

**Updated:**
- `manager-container-patch.yaml`: Updated sync-wave to 7 (after database jobs)
- Added proper environment variables for database user
- Uses consistent `kasm-all-in-one-secrets` secret

### 5. Deployment Orchestration

**Updated:**
- `kustomization.yaml`: Added new jobs to resources list
- Proper ArgoCD sync-wave ordering ensures correct execution sequence

## 🔄 Execution Flow

The fixed deployment follows this sequence:

1. **Wave 1**: Database initialization (`kasm-db-init-job`)
2. **Wave 2**: Secret synchronization (`kasm-secrets-sync-job`)  
3. **Wave 4**: Database user setup (`kasm-db-user-setup-job`)
4. **Wave 5**: Database permissions (`kasm-db-permissions-job`)
5. **Wave 6**: Complete database validation (`kasm-db-complete-init-job`)
6. **Wave 7**: Manager deployment (`manager-container-patch`)
7. **Wave 8**: Admin password fix (`kasm-admin-password-fix-job`)

## 🔑 Login Credentials

After applying these fixes:

- **URL**: https://kasm.lab.apj.dev
- **Username**: `admin@kasm.local`  
- **Password**: Retrieved from `kasm-admin-creds` secret (`AzAujN4Z7SamVNvM76nS1Q==`)

## 🛠️ Manual Application (If Needed)

If you need to apply these fixes manually:

```bash
# Apply the updated kustomization
kubectl apply -k /path/to/kasm/

# Or apply individual jobs
kubectl apply -f kasm-secrets-sync-job.yaml
kubectl apply -f kasm-admin-password-fix-job.yaml

# Check job completion
kubectl get jobs -n kasm
```

## 🔍 Verification

To verify the fix is working:

```bash
# Test API login
curl -k -X POST https://kasm.lab.apj.dev/api/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@kasm.local", "password":"AzAujN4Z7SamVNvM76nS1Q=="}' 

# Should return HTTP 200 with JWT token

# Check admin account status
kubectl exec kasm-database-1 -n kasm -c postgres -- \
  env PGPASSWORD='Vwp9B3Pptcvvf9ZKPRvjtw==' \
  psql -U postgres -d kasm \
  -c "SELECT username, locked, disabled, failed_pw_attempts FROM users WHERE username = 'admin@kasm.local';"

# Should show: locked=f, disabled=f, failed_pw_attempts=0
```

## 📝 Key Technical Details

### Password Hashing Algorithm
- KASM uses salted SHA256: `SHA256(password + salt)`
- Salt is generated during user creation and stored in database
- Hash must be exactly 64 characters (SHA256 hex output)

### Database Authentication
- All components use single `kasm` user with unified password
- Password stored in `kasm-all-in-one-secrets.db-password`
- No more `kasmapp` user complexity

### ArgoCD Integration
- Jobs use proper sync-waves for ordered execution
- PostSync hooks ensure jobs run after main deployment
- TTL cleanup prevents job accumulation

## 🚨 Important Notes

1. **Fresh Deployments**: The database initialization already has correct password hashing logic
2. **Existing Deployments**: The password fix job corrects any existing hash mismatches  
3. **Account Locking**: The fix job automatically unlocks accounts and resets failed attempts
4. **Secret Consistency**: The sync job maintains password consistency across all secrets

## 🎯 Future Prevention

These fixes ensure:
- Consistent password handling across all components
- Proper salted hash generation during initialization
- Automatic account unlocking for existing deployments
- Single database user eliminates confusion
- Proper deployment orchestration prevents race conditions

The login issue should not reoccur with this comprehensive solution in place.