# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a sophisticated GitOps-managed Kubernetes homelab implementing infrastructure as code principles. The repository contains both Kubernetes application definitions for a comprehensive self-hosted ecosystem and a modern web application stack for development.

## Core Technologies

**Primary Infrastructure:**
- **Kubernetes (K3s)** - Lightweight Kubernetes distribution
- **GitOps** - ArgoCD and Flux for declarative deployment management
- **Infrastructure as Code** - Pulumi (Python), Terraform, Packer for VM provisioning
- **Proxmox VE** - Virtual machine hypervisor
- **Kairos OS** - Immutable Linux distribution for Kubernetes nodes

**Web Application Stack:**
- **Frontend**: Next.js 14 with TypeScript, Tailwind CSS, React Query
- **Backend**: FastAPI with Python, Anthropic SDK integration
- **Database**: PostgreSQL with Docker Compose orchestration
- **Caching**: Redis for session management

## Main Task Commands

The repository uses **Go Task** (Taskfile.yml) as the primary task runner:

```bash
task --list                    # Show all available tasks
task validate                  # Validate Kubernetes YAML files
task lint                      # YAML linting with yamllint
task cluster:pre-seed          # Initialize cluster with prerequisites
task argocd:install           # Install ArgoCD GitOps controller
task 1password:install        # Setup 1Password secret management
task namespaces:create        # Create required Kubernetes namespaces
```

**Development Commands:**
```bash
# Docker Compose (web application)
docker-compose up -d          # Start full development stack
docker-compose down           # Stop all services

# Frontend development (Next.js)
cd frontend
npm run dev                   # Development server on :3000
npm run build                 # Production build
npm run lint                  # ESLint validation
npm run type-check            # TypeScript validation

# Infrastructure validation
task validate                 # Kubeconform validation
task calc                     # Resource quota calculation
```

## Architecture Overview

**Application Categories** (`/apps/`):
- **argocd/** & **argocd-cloud/** - GitOps management for different environments
- **arr-stack/** - Media automation (Sonarr, Radarr, Jellyfin, qBittorrent)
- **networking/** - Infrastructure (Traefik, Cilium, cert-manager, Tailscale)
- **monitoring/** - Observability (Prometheus, Grafana, Uptime Kuma)
- **services/** - Business applications (Gitea, n8n, Paperless, LiteLLM)
- **secrets/** - 1Password Connect integration for secret management
- **data/** - Database and storage services

**Infrastructure Provisioning** (`/pulumi/`):
- **k3s-bootstrap/** - Cluster initialization and Cilium networking
- **k3s-nodes/** - Node provisioning with Kairos OS
- **config/** - Environment-specific configurations (dev-lab, prod-lab, cloud)

**Deployment Management** (`/clusters/`):
- **cloud-homelabr/** - Flux GitOps for cloud environments

## Key Development Patterns

**Kubernetes Configuration:**
- **Kustomize** for native configuration management
- **Helm Charts** for complex applications with `charts/` subdirectories
- **1Password Connect** for secret injection via `*-1password.yaml` files
- **Environment separation** with base/ and overlay/ patterns

**Secret Management:**
- All secrets use 1Password Connect operator
- Pattern: `<service>-<credential-type>-1password.yaml`
- Never commit plain text secrets

**Application Structure:**
- Each app has `base/` with core Kubernetes manifests
- `kustomization.yaml` files define resource collections
- Ingress routing through Traefik with middleware

**GitOps Workflow:**
- ArgoCD manages application lifecycle
- Applications defined in `/apps/argocd*/base/`
- Automatic sync from Git repository

## Environment Management

**Multiple Environments:**
- **dev-lab** - Development Kubernetes cluster
- **prod-lab** - Production Kubernetes cluster  
- **cloud-homelabr** - Cloud-hosted cluster managed by Flux

**Context Switching:**
```bash
task cluster:update-config    # Update kubeconfig contexts
kubectl config use-context dev-lab
kubectl config use-context prod-lab
```

## Infrastructure Deployment

**VM Provisioning:**
```bash
# Pulumi infrastructure deployment
cd pulumi/k3s-bootstrap
pulumi up --stack <environment>

cd ../k3s-nodes  
pulumi up --stack <environment>
```

**Cluster Bootstrap Process:**
1. Provision VMs with Packer templates
2. Deploy Kairos OS via Pulumi
3. Bootstrap K3s control plane
4. Install Cilium networking (replaces kube-proxy)
5. Install ArgoCD for GitOps management
6. Deploy 1Password Connect for secrets
7. Apply application manifests

## Application Categories

**Media & Entertainment:**
- Jellyfin, Sonarr, Radarr, Lidarr, Prowlarr, Jellyseerr
- qBittorrent with Flood UI, SABnzbd, Unpackerr

**Development & Productivity:**
- Gitea with Woodpecker CI, JupyterLab, n8n automation
- Paperless-ngx document management, Vikunja task tracking

**AI & Machine Learning:**
- LiteLLM proxy for multiple AI providers
- Milvus vector database, local AI model hosting

**Networking & Security:**
- Tailscale mesh VPN, AdGuard DNS filtering
- Cert-manager with Let's Encrypt, Traefik reverse proxy

**Monitoring & Observability:**
- Prometheus + Grafana stack, Uptime Kuma
- Beszel system monitoring, Unifi network monitoring

## Important File Locations

**Main Configuration:**
- `Taskfile.yml` - Primary task definitions
- `docker-compose.yaml` - Local development stack
- `apps/argocd*/base/` - ArgoCD application definitions

**Environment Configs:**
- `pulumi/config/` - Infrastructure configurations per environment
- `clusters/` - Flux GitOps configurations

**Secret Templates:**
- `apps/secrets/` - 1Password Connect secret definitions
- Pattern: organized by service category

## Development Workflow

1. **Local Development**: Use Docker Compose for web application development
2. **Infrastructure Changes**: Modify Pulumi configurations and deploy
3. **Application Updates**: Update Kubernetes manifests in `/apps/`
4. **GitOps Sync**: ArgoCD automatically deploys changes from Git
5. **Validation**: Always run `task validate` before committing

This homelab demonstrates enterprise-grade Kubernetes practices with comprehensive application lifecycle management, automated secret handling, and GitOps-driven deployments suitable for both learning and production use.

## SuperClaude Agent Configuration

### Intelligent Task-Agent Routing System

**Auto-Detection Rules**: Keywords, file patterns, and domain indicators trigger optimal agent selection with framework-specific specialists and universal fallbacks.

### Technology-Agent Mapping

#### Infrastructure & Operations
**Kubernetes & GitOps** → `kubernetes-devops-expert` | `backend-developer` | `api-architect`
- **Auto-Triggers**: `apps/`, `clusters/`, `*.yaml`, `kustomization.yaml`, ArgoCD patterns, Helm charts
- **Tasks**: Cluster management, GitOps workflows, infrastructure deployment, service mesh, monitoring
- **MCP**: `--seq` (systematic analysis), `--c7` (K8s/Helm patterns)
- **Commands**: `/build`, `/analyze --infrastructure`, `/implement --type service`, `/deploy`

**Pulumi Infrastructure** → `kubernetes-devops-expert` | `backend-developer` | `api-architect`
- **Auto-Triggers**: `pulumi/`, `__main__.py`, IaC patterns, Proxmox configurations, Terraform files
- **Tasks**: VM provisioning, Kairos OS deployment, network automation, infrastructure as code
- **MCP**: `--c7` (Pulumi/Terraform patterns), `--seq` (infrastructure design)
- **Commands**: `/implement --framework pulumi`, `/analyze --focus infrastructure`, `/build --infra`

#### Application Domains
**AI/ML Services** → `laravel-backend-expert` | `api-architect` | `backend-developer`
- **Auto-Triggers**: `apps/mlops/`, `litellm`, `milvus`, `localai`, ML model patterns
- **Tasks**: LiteLLM proxy configuration, vector database setup, model serving
- **MCP**: `--c7` (ML frameworks), `--seq` (system architecture)
- **Commands**: `/implement --type api`, `/analyze --focus performance`

**Media Automation** → `backend-developer` | `performance-optimizer`
- **Auto-Triggers**: `apps/arr-stack/`, `jellyfin`, `sonarr`, `radarr`, media workflows
- **Tasks**: Arr stack optimization, transcoding pipelines, storage management
- **MCP**: `--seq` (performance analysis), `--play` (E2E validation)
- **Commands**: `/improve --perf`, `/troubleshoot`, `/analyze --focus performance`

**Development Tools** → `laravel-backend-expert` | `frontend-developer` | `tailwind-frontend-expert`
- **Auto-Triggers**: `gitea`, `woodpecker`, `jupyterlab`, `n8n`, CI/CD patterns
- **Tasks**: Git hosting, CI/CD pipelines, automation workflows, dev environments
- **MCP**: `--magic` (dashboard UI), `--c7` (dev tools), `--seq` (workflow design)
- **Commands**: `/implement --type component`, `/build --framework next`, `/design`

#### Monitoring & Observability
**Monitoring Stack** → `project-analyst` | `performance-optimizer` | `code-reviewer`
- **Auto-Triggers**: `apps/monitoring/`, `prometheus`, `grafana`, observability patterns
- **Tasks**: Metrics collection, dashboard creation, alerting configuration
- **MCP**: `--seq` (systematic analysis), `--play` (monitoring validation)
- **Commands**: `/analyze`, `/troubleshoot`, `/improve --focus monitoring`

**Security & Compliance** → `code-reviewer` | `backend-developer`
- **Auto-Triggers**: `apps/secrets/`, `1password`, `cert-manager`, security patterns
- **Tasks**: Secret management, certificate automation, security hardening
- **MCP**: `--seq` (security analysis), `--validate` mode
- **Commands**: `/analyze --focus security`, `/improve --security`

### Framework-Specific Agent Selection

#### Task Type Routing
**API Endpoints & Services** → `laravel-api-architect` | `api-architect` | `backend-developer`
- **Patterns**: Service definitions, endpoint configuration, API gateways
- **Auto-Detection**: `service.yaml`, `ingress.yaml`, API documentation
- **MCP**: `--c7` (API patterns), `--seq` (design analysis)

**Frontend Components** → `tailwind-frontend-expert` | `frontend-developer`
- **Patterns**: Dashboard UIs, admin interfaces, monitoring frontends
- **Auto-Detection**: UI component files, frontend frameworks, styling patterns
- **MCP**: `--magic` (component generation), `--c7` (framework patterns)

**Database Operations** → `laravel-eloquent-expert` | `backend-developer` | `performance-optimizer`
- **Patterns**: Database schemas, migration files, ORM configurations
- **Auto-Detection**: PostgreSQL configs, database manifests, persistence patterns
- **MCP**: `--c7` (database patterns), `--seq` (optimization analysis)

**Infrastructure Code** → `kubernetes-devops-expert` | `backend-developer` | `project-analyst`
- **Patterns**: Infrastructure as Code, configuration management, automation, CI/CD pipelines
- **Auto-Detection**: Pulumi files, Terraform configs, automation scripts, pipeline YAML
- **MCP**: `--seq` (infrastructure analysis), `--c7` (IaC patterns)

### Advanced Orchestration Patterns

#### Multi-Agent Coordination
**Comprehensive System Analysis** → `tech-lead-orchestrator` + Domain Specialists
- **Triggers**: `/analyze --comprehensive`, complex multi-domain operations
- **Strategy**: Wave orchestration with specialized agent delegation
- **Workflow**: Analysis → Planning → Implementation → Validation

**Large-Scale Infrastructure** → `project-analyst` + `--delegate --parallel-dirs`
- **Triggers**: >50 manifests, multi-environment deployments
- **Strategy**: Parallel directory analysis with coordinated implementation
- **Performance**: 60-80% time reduction through intelligent parallelization

**Security Audits** → `code-reviewer` + `--wave-strategy systematic`
- **Triggers**: Security keywords, compliance requirements, audit requests
- **Strategy**: Systematic security assessment with validation checkpoints
- **Scope**: Infrastructure, applications, secrets, network policies

### Universal Fallback Strategy

**When Framework-Specific Agents Unavailable:**
1. **Primary Fallback**: `general-purpose` agent with enhanced context
2. **Secondary Fallback**: `backend-developer` + `frontend-developer` combination  
3. **Tertiary Fallback**: `project-analyst` for comprehensive analysis
4. **Emergency Fallback**: Core Claude Code with explicit tool coordination

### Agent Performance Optimization

**Context Retention**: ≥90% context preservation across agent handoffs
**Response Time**: Sub-5s agent selection and activation
**Quality Gates**: 8-step validation cycle with agent-specific checkpoints
**Resource Management**: Dynamic token allocation based on complexity and scope

### Integration with Existing Workflows

**Task Runner Integration**: Seamless integration with existing `Taskfile.yml` commands
**GitOps Compatibility**: Respect existing ArgoCD and Flux workflows
**Development Workflow**: Preserve Docker Compose and validation patterns
**CI/CD Integration**: Maintain GitHub Actions and pipeline automation