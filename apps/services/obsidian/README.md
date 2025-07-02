# Obsidian Knowledge Management

This deploys Obsidian, a powerful knowledge base and note-taking application, within the homelab Kubernetes cluster.

## Overview

Obsidian is deployed as a containerized application using the LinuxServer.io Docker image, providing a web-based interface for accessing and managing your notes and knowledge base.

## Features

- Web-based Obsidian interface accessible via browser
- Persistent storage for notes and configuration
- Integration with homelab networking and ingress
- Certificate management via cert-manager
- Monitoring and backup capabilities

## Configuration

The deployment includes:
- Persistent storage for Obsidian data and configuration
- Ingress configuration with SSL termination
- Resource limits and requests
- Health checks and monitoring

## Access

Once deployed, Obsidian will be accessible at:
- Internal: `http://obsidian.services.svc.cluster.local:3000`
- External: `https://obsidian.lab.apj.dev`

## Storage

The application uses persistent storage to maintain:
- Obsidian vault data
- Application configuration
- Plugins and themes
- User preferences

## Known Issues

- Graph View may experience issues due to X11 server configuration in the container
- Some complex plugins may not work in the containerized environment
