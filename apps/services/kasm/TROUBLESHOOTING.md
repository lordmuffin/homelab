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