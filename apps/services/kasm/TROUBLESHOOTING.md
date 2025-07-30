# Kasm Troubleshooting

## Database Connection Issues

### Issue: `kasm-db-statefulset-0` Pod in `CreateContainerConfigError` State

#### Problem Description
The Kasm database pod (`kasm-db-statefulset-0`) was stuck in a `CreateContainerConfigError` state. The error occurred because the StatefulSet was configured to use a secret named `kasm-secrets` for the database password, but the pod was attempting to use this secret directly while we're actually using the `kasm-all-in-one-secrets` secret that contains the necessary credentials.

#### Root Cause
The Helm chart for Kasm creates a StatefulSet that references `kasm-secrets` for the database password, but our setup uses 1Password to generate secrets, and the database password is stored in the `kasm-all-in-one-secrets` secret.

#### Solution
Updated the `db-container-patch.yaml` file to include a patch for the environment variables in the database container, specifically to point the `POSTGRES_PASSWORD` environment variable to use the `kasm-all-in-one-secrets` secret instead of the `kasm-secrets` secret:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kasm-db-statefulset
  namespace: kasm
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true,Prune=false
    argocd.argoproj.io/sync-wave: "2"
    argocd.argoproj.io/compare-options: IgnoreExtraneous
    argocd.argoproj.io/sync-hook: Sync
    argocd.argoproj.io/sync-hook-weight: "10"
spec:
  template:
    spec:
      # Updated volumes configuration
      volumes:
      - name: kasm-db-data-sql
        configMap:
          name: kasm-db-data-sql
      # Update the main db-configs volume to use the Helm-created ConfigMap
      - name: kasm-db-configs
        configMap:
          name: kasm-db-init-startup  # Changed from kasm-db-configmap to kasm-db-init-startup
      # Use kasm-db-cert from the kasm application
      - name: kasm-db-cert
        secret:
          secretName: kasm-db-cert
      containers:
      - name: kasm-db-container
        # Replace all environment variables to ensure we override the existing ones
        env:
        - name: POSTGRES_DB
          value: kasm
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets  # Direct reference to the existing secret
              key: db-password
        - name: POSTGRES_USER
          value: kasmapp
        volumeMounts:
        - name: kasm-db-data-sql
          mountPath: /docker-entrypoint-initdb.d/data.sql
          subPath: data.sql
```

### Issue: Failed Mount for ConfigMap and Secret

#### Problem Description
After fixing the secret reference, the pod encountered another issue with mounting volumes:
```
Warning  FailedMount  4s (x7 over 36s)  kubelet  MountVolume.SetUp failed for volume "kasm-db-configs" : configmap "kasm-db-configmap" not found
Warning  FailedMount  4s (x7 over 36s)  kubelet  MountVolume.SetUp failed for volume "kasm-db-cert" : secret "kasm-db-cert" not found
```

#### Root Cause
After extensive investigation, we've identified multiple issues with the ArgoCD synchronization:

1. **Resource Naming Conflicts**: The Helm chart is creating resources with different names than what's defined in our custom manifests:
   - Helm chart uses `kasm-db-init-startup` while our manifest defines `kasm-db-configmap`
   - The `kasm-db-cert` Secret is not being properly created

2. **Application Conflicts**: The `kasm` and `kasm-utils` applications are both trying to manage some of the same resources, particularly the `kasm-ingress` resource. This creates conflicts during the sync process.

3. **Sync Termination**: The sync operation is being terminated before it completes, possibly due to these conflicts.

#### Solution
To resolve these issues, we need to:

1. **Align Resource Names**: Update our manifests to match the resource names created by the Helm chart:
   - Rename `kasm-db-configmap` to `kasm-db-init-startup` in our volume mounts and ConfigMap definition
   - Update the StatefulSet patch to reference the correct ConfigMap name

2. **Resolve Application Conflicts**: Update the `kasm-utils` application to avoid managing resources that are already managed by the `kasm` application:
   - Add explicit exclusions for shared resources in the ArgoCD application definition
   - Consider moving conflicting resources into the main Helm chart

3. **Fix the StatefulSet Configuration**: Update the StatefulSet to use the correct volume references:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: kasm-db-statefulset
  namespace: kasm
spec:
  template:
    spec:
      volumes:
      - name: kasm-db-configs
        configMap:
          name: kasm-db-init-startup  # Updated name to match Helm chart
      containers:
      - name: kasm-db-container
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: db-password
        volumeMounts:
        - name: kasm-db-configs
          mountPath: /var/lib/postgresql/conf
```

#### How to Apply the Fix
To properly fix this issue:

1. **Update manifests**: Modify the custom resource definitions to align with the Helm chart
2. **Synchronize applications**: Ensure that `kasm` application is synced first, then `kasm-utils`
3. **Manage conflicts**: Explicitly ignore shared resources in one of the applications

#### Prevention
To prevent similar issues in the future:

1. **Resource Coordination**: Carefully coordinate resources between Helm charts and custom manifests
2. **Application Boundaries**: Clearly define which application manages which resources
3. **Naming Conventions**: Use consistent naming conventions across all deployments
4. **Testing**: Test changes in a development environment before applying to production
5. **Documentation**: Document the ownership of each resource and how applications interact

## Successfully Resolved Issues

### July 30, 2025: Fixed Database StatefulSet Pod

We've successfully resolved the database pod issues by completely replacing the approach to secret management:

1. **Direct Reference Approach**: Instead of trying to create a separate `kasm-secrets` secret, we now directly reference the `kasm-all-in-one-secrets` secret in the StatefulSet patch.

2. **Simplified Solution**: Removed the complex sync job from `secrets.yaml` that was trying to create and maintain a separate `kasm-secrets` secret.

3. **Enhanced ArgoCD Integration**: Added proper ArgoCD annotations to ensure the patch is applied correctly, including:
   ```yaml
   argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true,Prune=false
   argocd.argoproj.io/sync-hook: Sync
   argocd.argoproj.io/sync-hook-weight: "10"
   ```

4. **Temporary Direct Patch**: To immediately fix the issue, we applied a direct patch to the StatefulSet:
   ```bash
   kubectl patch statefulset kasm-db-statefulset -n kasm --type json \
     -p '[{"op": "replace", "path": "/spec/template/spec/containers/0/env/1/valueFrom/secretKeyRef/name", "value": "kasm-all-in-one-secrets"}]'
   ```

5. **Results**: The database pod is now running successfully, though we observed some authentication failures in the logs that might need further investigation.

### Ongoing Monitoring

After fixing the database pod, we need to monitor the other components to ensure they start successfully. Some components might still be in the initialization phase as they wait for the database to be fully operational.

## Comprehensive Fix for All Kasm Components

### Problem: All Kasm Pods Failing with "secret kasm-secrets not found"

After fixing the database pod, we discovered that all other Kasm components (API, Manager, Guac, Proxy, Share) were also failing with the same error. All these pods were trying to use a secret named `kasm-secrets` for various credentials, but this secret didn't exist in our cluster. Instead, we have a `kasm-all-in-one-secrets` secret that contains all the necessary credentials.

### Solution: Patch All Deployments to Use kasm-all-in-one-secrets

We created patch files for each deployment to override their environment variables to use the existing `kasm-all-in-one-secrets` secret. Here's an example for the API deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kasm-api-deployment
  namespace: kasm
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true,Prune=false
    argocd.argoproj.io/sync-wave: "2"
    argocd.argoproj.io/compare-options: IgnoreExtraneous
    argocd.argoproj.io/sync-hook: Sync
    argocd.argoproj.io/sync-hook-weight: "10"
spec:
  template:
    spec:
      initContainers:
      - name: db-is-ready
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets  # Changed from kasm-secrets
              key: db-password
      containers:
      - name: kasm-api-container
        env:
        - name: START_SERVICES
          value: "true"
        - name: KUBERNETES_SERVICE_HOST
          value: "true"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets  # Changed from kasm-secrets
              key: db-password
```

We created similar patches for all the other deployments and updated the kustomization.yaml file to include these patches:

```yaml
patches:
  - path: db-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: StatefulSet
      name: kasm-db-statefulset
      namespace: kasm
  - path: api-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: kasm-api-deployment
      namespace: kasm
  - path: manager-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: kasm-manager-deployment
      namespace: kasm
  - path: guac-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: kasm-guac-deployment
      namespace: kasm
  - path: proxy-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: kasm-proxy-deployment
      namespace: kasm
  - path: share-container-patch.yaml
    target:
      group: apps
      version: v1
      kind: Deployment
      name: kasm-share-deployment
      namespace: kasm
```

### Key Insights and Recommendations

1. **Secret Standardization**: Instead of trying to create and maintain a separate `kasm-secrets` secret, we directly reference the existing `kasm-all-in-one-secrets` secret in all deployments.

2. **Simplified Approach**: This approach is simpler and more reliable than trying to create a sync job that copies data between secrets.

3. **ArgoCD Optimization**: We added proper ArgoCD annotations to ensure the patches are applied correctly and not pruned during sync operations.

4. **Dependency Chain**: We observed that other pods were waiting for the API pod to be ready before they could initialize, creating a dependency chain: DB → API → Other components.

5. **Comprehensive Patching**: Rather than patching each deployment individually through kubectl, we created proper patch files that are applied through ArgoCD, maintaining the GitOps workflow.

### Future Recommendations

1. **Standardize Secret Names**: When using Helm charts with custom secret management (like 1Password), ensure that the secret names are standardized or that proper overrides are in place.

2. **Documentation**: Document the relationship between components and their dependencies to make troubleshooting easier.

3. **Monitoring**: Set up proper monitoring for secret-related issues, as they can cause cascading failures across all components.

4. **Testing**: Test changes in a development environment before applying to production to catch similar issues early.

## Database Initialization Issues

### Problem: Database Not Properly Initialized

After fixing the secret references, we observed that the pods were still not starting properly. The API pod was stuck in an init container loop with the message "Waiting for DB to initialize..." even though the database pod was running. Further investigation revealed that while the database was running, it didn't have the required schema and data.

#### Root Cause

1. **Missing Schema**: The database was created but not properly initialized with the required tables and data.
2. **Init Container Check**: The API pod's init container was checking for at least 2 records in the `zones` table, but this table didn't exist.
3. **Failed Initialization Job**: The original database initialization job was using the wrong secret references (`kasm-secrets` instead of `kasm-all-in-one-secrets`).

#### Detailed Analysis

We found these key components involved in database initialization:

1. **kasm-db-init-startup ConfigMap**: Contains the `startup.sh` script that performs database initialization, including:
   - Creating the database if it doesn't exist
   - Setting up the schema
   - Populating initial data like admin accounts and tokens
   - The script checks if the `settings` table exists, and if not, runs the initialization

2. **kasm-db-init-job**: A Kubernetes job that runs the database initialization script. This job was failing because it was using the non-existent `kasm-secrets` secret.

3. **API Pod Check**: The API pod's init container has this check:
   ```bash
   while [ ! $(PGPASSWORD=$POSTGRES_PASSWORD psql -U kasmapp -d kasm -h db -t -c "select zone_id from zones" 2>/dev/null | wc -l) -ge 2 ]; do 
     echo "Waiting for DB to initialize..."; 
     sleep 5; 
   done
   ```
   This check is waiting for at least 2 records in the `zones` table, which wasn't being created.

### Solution: Create a Database Initialization Job

We created a new job (`kasm-db-init-fix-job`) that properly references the existing `kasm-all-in-one-secrets` secret for all credentials:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: kasm-db-init-fix-job
  namespace: kasm
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true,Prune=false
    argocd.argoproj.io/sync-wave: "3"
    argocd.argoproj.io/compare-options: IgnoreExtraneous
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: OnFailure
      initContainers:
      - name: db-is-ready
        image: kasmweb/api:1.17.0
        command:
        - /bin/bash
        - -c
        - |
          while ! pg_isready -h db -p 5432 -t 10; do 
            echo "Waiting for DB..."; 
            sleep 5; 
          done
      containers:
      - name: kasm-db-init-container
        image: kasmweb/api:1.17.0
        command:
        - /bin/bash
        - -c
        - |
          # First check if zones table exists
          if ! PGPASSWORD="$POSTGRES_PASSWORD" psql -U kasmapp -d kasm -h db -c "SELECT 1 FROM zones LIMIT 1" &>/dev/null; then
            echo "Zones table doesn't exist, initializing database..."
            export DB_AUTO_INITIALIZE="true"
            /usr/bin/startup.sh
            echo "Database initialization completed"
          else
            count=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -U kasmapp -d kasm -h db -t -c "SELECT COUNT(*) FROM zones" 2>/dev/null)
            echo "Found $count zones records"
            if [ "$count" -lt 2 ]; then
              echo "Not enough zones records, initializing database..."
              export DB_AUTO_INITIALIZE="true"
              /usr/bin/startup.sh
              echo "Database initialization completed"
            else
              echo "Database already properly initialized."
            fi
          fi
        env:
        - name: DEFAULT_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: admin-password
        - name: DEFAULT_MANAGER_TOKEN
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: manager-token
        - name: DEFAULT_REGISTRATION_TOKEN
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: service-token
        - name: DEFAULT_USER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: user-password
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: db-password
        volumeMounts:
        - name: db-init-script
          mountPath: /usr/bin/startup.sh
          subPath: startup.sh
      volumes:
      - name: db-init-script
        configMap:
          name: kasm-db-init-startup
          defaultMode: 0755
```

This job:
1. Waits for the database to be ready
2. Checks if the `zones` table exists, and if not, runs the initialization
3. If the `zones` table exists but has fewer than 2 records, also runs the initialization
4. Uses the existing `kasm-all-in-one-secrets` secret for all credentials
5. Uses the existing `startup.sh` script from the `kasm-db-init-startup` ConfigMap

### Lessons Learned

1. **Initialization Dependencies**: Database initialization is a critical dependency for all other components. It's important to ensure that this step completes successfully before other components try to use the database.

2. **Validation Checks**: It's important to have proper validation checks in initialization scripts. In this case, the API pod was checking for a specific condition (2 records in the `zones` table) that wasn't being met.

3. **Secret Consistency**: When using custom secret management, it's critical to ensure that all components use the same secret references consistently.