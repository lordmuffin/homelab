# CouchDB Kustomize Configuration

This directory contains the Kustomize configuration for CouchDB networking setup.

## Structure

- `base/` - Base configuration for CouchDB ingress
  - `ingress.yaml` - IngressRoute configuration with Traefik
  - `kustomization.yaml` - Base kustomization file

## Configuration Details

### Ingress Route
- **Hostname**: `couchdb.lab.apj.dev`
- **Port**: 5984 (standard CouchDB port)
- **Authentication**: Uses traefik-forward-auth middleware for all paths
- **TLS**: Uses letsencrypt-production cluster issuer
- **External DNS**: Configured for lab.apj.dev domain

### Security
All CouchDB access requires authentication through the traefik-forward-auth middleware, ensuring secure access to the database management interface and APIs.

## Usage

This configuration is designed to be included in your main networking kustomization or deployed separately for CouchDB-specific routing needs.
