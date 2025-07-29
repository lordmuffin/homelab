# KASM Workspaces

KASM Workspaces provides streaming containerized apps and desktops to your web browser. This installation uses Helm charts to deploy KASM in Kubernetes.

## Components

This ArgoCD application deploys the following components:

- KASM API Server
- KASM Manager
- KASM Proxy
- Database (PostgreSQL)
- Guacamole Server
- RDP Gateway
- KASM Share

## Installation

The deployment is managed by ArgoCD and uses the official KASM Helm chart.

### Prerequisites

- Kubernetes cluster with persistent storage support
- Ingress controller (NGINX)
- DNS record for kasm.lab.apj.dev pointing to your cluster

### Configuration

The main configuration is in the ArgoCD Application manifest, which sets:

- KASM hostname: kasm.lab.apj.dev
- Deployment size: small (suitable for homelab environments)
- Resource requests and limits for each component
- Persistent storage for database and user profiles

### Access

After deployment, KASM will be available at: https://kasm.lab.apj.dev

Credentials:
- Username: admin@kasm.local
- Password: Stored in 1Password under the "kasm-admin-creds-1password" entry

The deployment uses 1Password for secure credential management, with the following secrets:
- kasm-admin-creds: Admin user credentials
- kasm-db-postgres-creds: Database credentials
- kasm-encryption-key: Encryption key for secure communications

## Post-Installation Configuration

After initial login, configure the following:

1. Update admin user credentials
2. Configure Zone settings:
   - Set Proxy Port to 0 for automatic port detection
   - Configure Upstream Auth Address to "proxy" or specific FQDN

## Troubleshooting

Common issues:

1. If persistent volumes fail to mount, check your storage class configuration
2. If networking issues occur, verify ingress controller settings
3. For workspace connection issues, check the KASM logs:

```bash
kubectl -n kasm logs -l app=kasm-manager
kubectl -n kasm logs -l app=kasm-proxy
```

## Resources

- [KASM Documentation](https://kasmweb.com/docs/latest/index.html)
- [KASM Helm Charts Repository](https://github.com/kasmtech/helm-charts)