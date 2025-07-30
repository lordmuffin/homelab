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
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
    argocd.argoproj.io/sync-wave: "2"
    argocd.argoproj.io/compare-options: IgnoreExtraneous
spec:
  template:
    spec:
      containers:
      - name: kasm-db-container
        env:
        # Fix the POSTGRES_PASSWORD secret reference to use kasm-all-in-one-secrets
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: kasm-all-in-one-secrets
              key: db-password
```

#### How to Apply the Fix
This fix is part of the IAC and will be automatically applied by Argo CD when the `kasm-utils` application is synced.

#### Prevention
Ensure that when using external secret management systems like 1Password with applications that have their own secrets management (like Helm charts), proper patches are created to override the default secret references.