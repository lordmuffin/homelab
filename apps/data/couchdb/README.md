# CouchDB Deployment

This directory contains the configuration for deploying Apache CouchDB using Helm charts in the homelab Kubernetes cluster.

## Overview

CouchDB is a NoSQL document database that uses JSON for documents, HTTP for an API, and JavaScript for MapReduce queries.

## Configuration

- **Helm Chart**: Apache CouchDB official Helm chart from https://apache.github.io/couchdb-helm
- **Version**: 4.5.3
- **Namespace**: couchdb
- **Cluster Size**: 3 nodes for high availability
- **Storage**: 10Gi SSD persistent volumes per node

## Secrets Management

Admin credentials are managed through 1Password integration:
- **1Password Item**: `couchdb-admin-creds-1password` in HomeLab vault
- **Secret**: `couchdb-admin-secret` in couchdb namespace

## Access

CouchDB will be available at:
- Internal service: `couchdb.couchdb.svc.cluster.local:5984`
- Admin interface: `http://couchdb.couchdb.svc.cluster.local:5984/_utils`

## Monitoring

- Prometheus metrics are enabled through the `prometheus: enabled` namespace label
- Pod monitoring is available through the cluster monitoring stack

## Storage

- Uses SSD storage class for better performance
- Each CouchDB node gets a 10Gi persistent volume
- ReadWriteOnce access mode

## Security

- Admin party mode is disabled
- Authentication is required for all operations
- Admin credentials are securely managed through 1Password
