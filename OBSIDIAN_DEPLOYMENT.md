# Obsidian Deployment Guide

This guide shows how to deploy Obsidian using your existing homelab ArgoCD setup with 1Password integration.

## Prerequisites

1. ArgoCD is deployed and running in your cluster
2. 1Password Connect operator is installed
3. Traefik ingress controller is configured
4. External DNS is configured for `lab.apj.dev` domain
5. Wildcard certificate `lab-apj-dev-tls` exists

## 1Password Setup

Create the following item in your 1Password HomeLab vault:
- Item name: `obsidian-creds-1password`
- Fields: Add any credentials if needed (optional for basic deployment)

## Files Created

The following files have been created in your homelab repository:

### Service Files
```
apps/services/obsidian/
├── README.md
├── kustomization.yaml
└── base/
    ├── kustomization.yaml
    ├── deployment.yaml
    ├── service.yaml
    ├── pvc.yaml
    └── ingress.yaml
```

### Secret Files
```
apps/secrets/services/
└── obsidian-creds-1password.yaml
```

### ArgoCD Application
```
apps/argocd-cloud/base/services/
└── obsidian.yaml
```

## Deployment Steps

1. **Commit and push** the changes to your homelab repository:
   ```bash
   git add .
   git commit -m "Add Obsidian service deployment"
   git push origin main
   ```

2. **ArgoCD will automatically sync** the new application within a few minutes.

3. **Check deployment status**:
   ```bash
   kubectl get pods -n services | grep obsidian
   kubectl get pvc -n services | grep obsidian
   ```

4. **Access Obsidian**:
   - URL: https://obsidian.lab.apj.dev
   - The application will be protected by Traefik forward auth

## Configuration Details

### Storage
- **PVC**: 10Gi using your configured storage class
- **Mount**: `/config` in container for Obsidian data

### Networking
- **Service**: ClusterIP on ports 3000 (HTTP) and 3001 (WebSocket)
- **Ingress**: Traefik IngressRoute with SSL termination
- **Domain**: obsidian.lab.apj.dev
- **Certificate**: Uses existing wildcard cert `lab-apj-dev-tls`

### Resources
- **Requests**: 512Mi memory, 250m CPU
- **Limits**: 2Gi memory, 1000m CPU

### Security
- Protected by Traefik forward auth middleware
- Uses non-root user (PUID/PGID: 1000)

## Customization

To customize the deployment:

1. **Change domain**: Edit `apps/services/obsidian/base/ingress.yaml`
2. **Adjust resources**: Edit `apps/services/obsidian/base/deployment.yaml`
3. **Modify storage**: Edit `apps/services/obsidian/base/pvc.yaml`
4. **Add environment variables**: Edit deployment for additional config

## Troubleshooting

### Pod not starting
```bash
kubectl describe pod -n services -l app=obsidian
kubectl logs -n services -l app=obsidian
```

### PVC issues
```bash
kubectl get pvc -n services obsidian-pvc
kubectl describe pvc -n services obsidian-pvc
```

### Ingress issues
```bash
kubectl get ingressroute -n services obsidian
kubectl describe ingressroute -n services obsidian
```

### DNS issues
```bash
# Check external-dns logs
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns
```

## Known Limitations

1. **Graph View**: May not work properly due to X11 limitations in container
2. **File System**: Some file operations may be limited
3. **Plugins**: Complex plugins requiring system access may not function

## Backup

### Automated Backups
The deployment includes automated daily backups using a CronJob that:
- Runs daily at 3:00 AM
- Creates compressed tar.gz archives of the entire Obsidian config directory
- Uploads backups to Backblaze B2 cloud storage
- Stores backups in the `obsidian/` folder within your `cloud-homelab-backups` bucket

### Backup Configuration
- **Schedule**: Daily at 3:00 AM (`0 3 * * *`)
- **Storage**: Backblaze B2 (`cloud-homelab-backups` bucket)
- **Format**: Compressed tar.gz archives
- **Retention**: Managed by your B2 bucket lifecycle policies

### Manual Backup
To trigger a manual backup:
```bash
kubectl create job --from=cronjob/obsidian-backup obsidian-manual-backup -n services
```

### Restore Process
1. Download backup from B2: `obsidian/obsidian_backup_YYYYMMDD_HHMMSS.tar.gz`
2. Extract to a temporary location
3. Copy contents to the PVC mount point
4. Restart the Obsidian pod

### Backup Monitoring
Check backup job status:
```bash
kubectl get cronjobs -n services obsidian-backup
kubectl get jobs -n services | grep obsidian-backup
kubectl logs -n services job/obsidian-backup-<timestamp>
```
