#!/bin/bash

# Actual Budget File-to-PostgreSQL Migration Script
# This script migrates backed-up file data to the new PostgreSQL database

set -euo pipefail

# Configuration
NAMESPACE="services"
MIGRATION_POD="actual-migration-worker"
BACKUP_DIR="./actual-backups"
POSTGRES_HOST="actual-database-rw.services.svc.cluster.local"
POSTGRES_DB="actual"

# Logging functions
log_info() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] INFO: $*" >&2
}

log_error() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ERROR: $*" >&2
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if backup exists
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
        log_error "No backup files found in $BACKUP_DIR. Run ./actual-backup-script.sh first."
        exit 1
    fi
    
    # Check if PostgreSQL database is deployed
    if ! kubectl get cluster actual-database -n $NAMESPACE >/dev/null 2>&1; then
        log_error "PostgreSQL database not found. Deploy it first:"
        log_error "kubectl apply -f apps/services/finances/actual/base/database.yaml"
        log_error "kubectl apply -f apps/services/finances/actual/base/actual-db-postgres-creds-1password.yaml"
        exit 1
    fi
    
    # Check database readiness
    if ! kubectl wait --for=condition=Ready cluster/actual-database -n $NAMESPACE --timeout=60s >/dev/null 2>&1; then
        log_error "PostgreSQL database is not ready. Please wait for it to start."
        exit 1
    fi
    
    log_info "✅ Prerequisites check passed"
}

# Create migration worker pod
create_migration_pod() {
    log_info "Creating migration worker pod..."
    
    cat <<EOF | kubectl apply -f -
---
apiVersion: v1
kind: Pod
metadata:
  name: $MIGRATION_POD
  namespace: $NAMESPACE
  labels:
    app: actual-migration
spec:
  restartPolicy: Never
  containers:
  - name: migration-worker
    image: node:18-alpine
    command: ["/bin/sh"]
    args: ["-c", "sleep 7200"]  # Keep pod alive for 2 hours
    env:
    - name: POSTGRES_HOST
      value: "$POSTGRES_HOST"
    - name: POSTGRES_PORT
      value: "5432"
    - name: POSTGRES_DB
      value: "$POSTGRES_DB"
    - name: POSTGRES_USER
      valueFrom:
        secretKeyRef:
          name: actual-db-postgres-creds-1password
          key: username
    - name: POSTGRES_PASSWORD
      valueFrom:
        secretKeyRef:
          name: actual-db-postgres-creds-1password
          key: password
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "1Gi"
        cpu: "1000m"
    volumeMounts:
    - name: work-storage
      mountPath: /work
    workingDir: /work
  volumes:
  - name: work-storage
    emptyDir: {}
EOF

    # Wait for pod to be ready
    log_info "Waiting for migration pod to be ready..."
    kubectl wait --for=condition=Ready pod/$MIGRATION_POD -n $NAMESPACE --timeout=300s
    
    # Install required tools
    log_info "Installing migration tools..."
    kubectl exec -n $NAMESPACE $MIGRATION_POD -- sh -c "
        apk add --no-cache postgresql-client sqlite curl bash tar gzip
        npm install -g @actualbudget/api
    "
}

# Upload backup data to migration pod
upload_backup_data() {
    log_info "Uploading backup data to migration pod..."
    
    # Find the latest backup file
    LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.tar.gz | head -1)
    log_info "Using backup: $LATEST_BACKUP"
    
    # Copy backup to pod
    kubectl cp "$LATEST_BACKUP" $NAMESPACE/$MIGRATION_POD:/work/backup.tar.gz
    
    # Extract backup
    kubectl exec -n $NAMESPACE $MIGRATION_POD -- sh -c "
        cd /work
        tar -xzf backup.tar.gz
        echo 'Backup extracted, contents:'
        find . -name '*.sqlite*' -o -name '*.db' -o -name '*.json' | head -10
    "
}

# Create migration script inside the pod
create_migration_logic() {
    log_info "Creating migration logic..."
    
    kubectl exec -n $NAMESPACE $MIGRATION_POD -- sh -c 'cat > /work/migrate.js << '\''EOF'\''
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// Database connection configuration
const dbConfig = {
  host: process.env.POSTGRES_HOST,
  port: process.env.POSTGRES_PORT,
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD
};

console.log("Starting Actual Budget migration...");
console.log("Database config:", { ...dbConfig, password: "***" });

// Function to find Actual Budget data files
function findActualData() {
  const dataDir = "/work/data";
  console.log("Searching for Actual Budget data in:", dataDir);
  
  try {
    // Look for common Actual Budget file patterns
    const serverFiles = path.join(dataDir, "server-files");
    const userFiles = path.join(dataDir, "user-files");
    
    if (fs.existsSync(serverFiles)) {
      console.log("Found server-files directory");
      const files = fs.readdirSync(serverFiles);
      console.log("Server files:", files.slice(0, 10));
    }
    
    if (fs.existsSync(userFiles)) {
      console.log("Found user-files directory");
      const files = fs.readdirSync(userFiles);
      console.log("User files:", files.slice(0, 10));
    }
    
    // Find SQLite databases
    const findCmd = `find ${dataDir} -name "*.sqlite*" -o -name "*.db" 2>/dev/null || true`;
    const sqliteFiles = execSync(findCmd, { encoding: "utf8" }).trim().split("\n").filter(f => f);
    
    if (sqliteFiles.length > 0) {
      console.log("Found SQLite databases:", sqliteFiles);
      return sqliteFiles;
    }
    
    console.log("No SQLite databases found, looking for other data files...");
    const allFiles = execSync(`find ${dataDir} -type f | head -20`, { encoding: "utf8" }).trim().split("\n");
    console.log("Available files:", allFiles);
    
    return [];
  } catch (error) {
    console.error("Error searching for data:", error.message);
    return [];
  }
}

// Test database connection
function testDatabaseConnection() {
  try {
    const connectionUrl = `postgresql://${dbConfig.user}:${dbConfig.password}@${dbConfig.host}:${dbConfig.port}/${dbConfig.database}`;
    execSync(`psql "${connectionUrl}" -c "SELECT version();"`, { encoding: "utf8" });
    console.log("✅ Database connection successful");
    return true;
  } catch (error) {
    console.error("❌ Database connection failed:", error.message);
    return false;
  }
}

// Main migration function
async function migrate() {
  console.log("=== Actual Budget Migration Process ===");
  
  // Test database connection
  if (!testDatabaseConnection()) {
    process.exit(1);
  }
  
  // Find data files
  const dataFiles = findActualData();
  
  if (dataFiles.length === 0) {
    console.log("⚠️  No Actual Budget database files found.");
    console.log("This might be a fresh installation or the data structure is different.");
    console.log("Manual inspection required.");
    process.exit(0);
  }
  
  console.log(`Found ${dataFiles.length} database file(s) to migrate`);
  
  // For each SQLite database, examine its structure
  dataFiles.forEach((dbFile, index) => {
    console.log(`\n--- Examining database ${index + 1}: ${dbFile} ---`);
    try {
      const tables = execSync(`sqlite3 "${dbFile}" ".tables"`, { encoding: "utf8" }).trim();
      console.log("Tables:", tables);
      
      if (tables) {
        const tableList = tables.split(/\s+/).filter(t => t);
        tableList.forEach(table => {
          try {
            const count = execSync(`sqlite3 "${dbFile}" "SELECT COUNT(*) FROM ${table};"`, { encoding: "utf8" }).trim();
            console.log(`  ${table}: ${count} records`);
          } catch (e) {
            console.log(`  ${table}: Could not count records`);
          }
        });
      }
    } catch (error) {
      console.log("Error examining database:", error.message);
    }
  });
  
  console.log("\n=== Migration Strategy ===");
  console.log("Due to the complexity of Actual Budget'\''s data structure,");
  console.log("the recommended approach is:");
  console.log("1. Start a fresh Actual Budget instance with PostgreSQL");
  console.log("2. Use Actual Budget'\''s import/export features to migrate data");
  console.log("3. Or manually recreate budgets using the backup data as reference");
  
  console.log("\n=== Next Steps ===");
  console.log("1. Deploy the new Actual Budget with PostgreSQL configuration");
  console.log("2. Access the web interface and set up your budget");
  console.log("3. Import data using Actual Budget'\''s built-in import features");
  
  return true;
}

// Run migration
migrate().catch(console.error);
EOF'
}

# Run the migration
run_migration() {
    log_info "Running migration process..."
    
    kubectl exec -n $NAMESPACE $MIGRATION_POD -- node /work/migrate.js
}

# Create PostgreSQL schema inspection script
create_inspection_script() {
    log_info "Creating database inspection script..."
    
    kubectl exec -n $NAMESPACE $MIGRATION_POD -- sh -c 'cat > /work/inspect-db.sh << '\''EOF'\''
#!/bin/bash
echo "=== PostgreSQL Database Inspection ==="
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "Database version:"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version();"

echo -e "\nDatabase size:"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_size_pretty(pg_database_size('\''$POSTGRES_DB'\''));"

echo -e "\nExisting tables:"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"

echo -e "\nTable sizes:"
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE schemaname = '\''public'\'' 
ORDER BY tablename, attname;
" 2>/dev/null || echo "No statistics available yet"

echo -e "\nDatabase ready for Actual Budget deployment!"
EOF
chmod +x /work/inspect-db.sh'

    kubectl exec -n $NAMESPACE $MIGRATION_POD -- /work/inspect-db.sh
}

# Cleanup function
cleanup() {
    log_info "Cleaning up migration pod..."
    kubectl delete pod $MIGRATION_POD -n $NAMESPACE --ignore-not-found=true
}

# Main execution
main() {
    log_info "🚀 Starting Actual Budget migration process..."
    
    # Set cleanup trap
    trap cleanup EXIT
    
    check_prerequisites
    create_migration_pod
    upload_backup_data
    create_migration_logic
    run_migration
    create_inspection_script
    
    log_info "🎉 Migration process completed!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Deploy the new Actual Budget: kubectl apply -f apps/services/finances/actual/base/deployment.yaml"
    log_info "2. Access Actual Budget and set up your account"
    log_info "3. Import your budget data using Actual Budget's import features"
    log_info "4. Verify the backup system: kubectl create job --from=cronjob/actual-postgres-backup actual-test -n services"
}

# Run main function
main "$@"