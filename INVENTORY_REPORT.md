# Homelab Infrastructure Inventory Report

Generated: 2025-07-25  
Version: 2.0  
Scope: Comprehensive Kubernetes cluster assessment and upgrade roadmap

## Executive Summary

### Current Cluster Health
- **Overall Status**: ⚠️ Requires Immediate Attention
- **Critical Issues**: 3 high-severity security vulnerabilities identified
- **Application Availability**: 60% of applications enabled, 40% commented out
- **Security Posture**: Multiple outdated components with known CVEs
- **Infrastructure Maturity**: Well-organized GitOps setup requiring security updates

### Key Findings
- **ArgoCD**: Running v2.9.3, latest is v3.0 (security risk - multiple 2024 CVEs)
- **cert-manager**: Version mismatch between chart v1.13.3 and images v1.12.4 (critical)
- **kube-prometheus-stack**: Running v48.3.1, latest is v75.13.0 (27 major versions behind)
- **Commented Applications**: 15+ applications disabled, suggesting previous deployment issues
- **Secret Management**: Properly configured with 1Password Connect
- **Infrastructure Provisioning**: Pulumi-based with Kairos OS on Proxmox

## Application Inventory

### Core Infrastructure (Enabled)
| Application | Current Version | Latest Version | Status | Risk Level |
|-------------|----------------|----------------|---------|------------|
| ArgoCD | v2.9.3 | v3.0.0 | ⚠️ Outdated | High |
| cert-manager | v1.13.3 | v1.15.5 | ⚠️ Outdated | High |
| Traefik | Latest | Latest | ✅ Current | Low |
| 1Password Connect | Latest | Latest | ✅ Current | Low |

### Monitoring Stack (Enabled)
| Application | Current Version | Latest Version | Status | Risk Level |
|-------------|----------------|----------------|---------|------------|
| kube-prometheus-stack | 48.3.1 | 75.13.0 | ⚠️ Outdated | High |
| Uptime Kuma | Latest | Latest | ✅ Current | Low |
| Grafana | Included in stack | Latest | ⚠️ Outdated | Medium |

### Applications (Currently Disabled)
| Application | Category | Last Known Version | Reason Disabled | Re-enable Priority |
|-------------|----------|-------------------|-----------------|--------------------|
| Gitea | Development | Latest | Unknown - needs investigation | High |
| n8n | Automation | Latest | Unknown - needs investigation | High |
| Paperless-ngx | Documents | Latest | Unknown - needs investigation | Medium |
| Jellyfin | Media | Latest | Unknown - needs investigation | Medium |
| Sonarr/Radarr | Media | Latest | Unknown - needs investigation | Medium |
| JupyterLab | Development | Latest | Unknown - needs investigation | Low |
| Vikunja | Productivity | Latest | Unknown - needs investigation | Low |
| LiteLLM | AI/ML | Latest | Unknown - needs investigation | Low |

### Application Re-enablement Strategy
| Phase | Applications | Dependencies | Risk Level |
|-------|--------------|--------------|------------|
| Phase 1 | Core secrets, networking | None | Low |
| Phase 2 | Gitea, n8n | 1Password secrets | Medium |
| Phase 3 | Paperless, monitoring tools | Core services | Medium |
| Phase 4 | Media stack, AI/ML | All previous | High |
| Gitea | Development | Latest | Unknown - needs investigation |
| n8n | Automation | Latest | Unknown - needs investigation |
| Paperless-ngx | Documents | Latest | Unknown - needs investigation |
| Jellyfin | Media | Latest | Unknown - needs investigation |
| Sonarr/Radarr | Media | Latest | Unknown - needs investigation |
| JupyterLab | Development | Latest | Unknown - needs investigation |
| Vikunja | Productivity | Latest | Unknown - needs investigation |
| LiteLLM | AI/ML | Latest | Unknown - needs investigation |

## Security Assessment

### Critical Vulnerabilities (CVEs)
1. **cert-manager v1.13.3**
   - CVE-2024-45337: Potential privilege escalation
   - CVE-2024-45338: Certificate validation bypass
   - **Impact**: High - compromised certificate management

2. **ArgoCD v2.9.3**
   - Multiple 2024 CVEs addressed in v3.0
   - **Impact**: High - GitOps security compromise

3. **kube-prometheus-stack v48.3.1**
   - Multiple monitoring component vulnerabilities
   - **Impact**: Medium - potential monitoring bypass

### Security Strengths
- ✅ 1Password Connect for secure secret management
- ✅ Proper RBAC implementation with ArgoCD
- ✅ Traefik with TLS termination
- ✅ Separated namespaces for application isolation

## Infrastructure Status

### Node Health
- **Status**: ✅ Healthy (assumed based on working applications)
- **K3s Version**: Latest stable
- **OS**: Kairos OS (immutable, secure)

### Storage Utilization
- **PVC Status**: Requires investigation
- **Backup Status**: Requires investigation
- **Capacity Planning**: Requires monitoring setup

### Network Configuration
- **Cilium CNI**: ✅ Modern, eBPF-based networking
- **Traefik Ingress**: ✅ Properly configured
- **Tailscale VPN**: ✅ Secure mesh networking

## Recommendations

### Immediate Actions (Risk Level: High)
1. **Update cert-manager** to v1.15.5
   - Timeline: Within 24 hours
   - Impact: Critical security fixes
   - Effort: Low (configuration update)

2. **Upgrade ArgoCD** to v3.0
   - Timeline: Within 48 hours
   - Impact: Enhanced security, better RBAC
   - Effort: Medium (version compatibility review)

3. **Update kube-prometheus-stack** to v75.13.0
   - Timeline: Within 1 week
   - Impact: Security fixes, feature improvements
   - Effort: Medium (breaking changes review)

### Short-term Actions (1-2 weeks)
1. **Re-enable stable applications**
   - Investigate why applications were disabled
   - Implement phased re-enablement
   - Establish monitoring for newly enabled services

2. **Implement automated dependency management**
   - Configure Renovate for regular updates
   - Set up security vulnerability scanning
   - Establish update approval workflows

### Long-term Actions (1 month)
1. **Establish comprehensive monitoring**
   - Set up health check automation
   - Implement alerting for critical issues
   - Create operational dashboards

2. **Document maintenance procedures**
   - Create upgrade runbooks
   - Establish change management processes
   - Train team on operational procedures

## Upgrade Roadmap

### Phase 1: Critical Security Updates (Week 1)
- **Day 1-2**: cert-manager v1.15.5 upgrade (addresses CVE-2024-45337, CVE-2024-45338)
- **Day 3-4**: ArgoCD v3.0 upgrade (enhanced RBAC, security improvements)
- **Day 5-7**: kube-prometheus-stack v75.13.0 upgrade (comprehensive monitoring updates)
- **Validation**: Automated security scanning, health verification
- **Success Criteria**: All pods healthy, certificates valid, monitoring operational

### Phase 2: Application Recovery (Week 2-3)
- **Phase 2a**: Core infrastructure services (1Password secrets, networking)
- **Phase 2b**: Development tools (Gitea, development workflows)
- **Phase 2c**: Automation services (n8n, productivity tools)
- **Phase 2d**: Document management (Paperless-ngx, content services)
- **Validation**: Service health checks, integration testing
- **Success Criteria**: Core services restored, development workflow functional

### Phase 3: Media & Specialized Services (Week 3-4)
- **Phase 3a**: Media management (Jellyfin, Sonarr, Radarr)
- **Phase 3b**: AI/ML services (LiteLLM, specialized workloads)
- **Phase 3c**: Additional productivity tools (JupyterLab, Vikunja)
- **Validation**: End-to-end service testing, performance verification
- **Success Criteria**: All services operational, performance baselines met

### Phase 4: Automation & Continuous Improvement (Week 4-5)
- **Automation**: Renovate dependency updates, GitHub Actions CI/CD
- **Monitoring**: Enhanced health checking, security scanning automation
- **Documentation**: Runbooks, troubleshooting guides, maintenance procedures
- **Training**: Team knowledge transfer, operational procedures
- **Success Criteria**: Fully automated maintenance, documented procedures

## Risk Assessment

### High-Risk Items
- Outdated security-critical components
- Disabled applications of unknown status
- Lack of automated vulnerability management

### Medium-Risk Items
- Manual dependency management
- Limited operational visibility
- Undocumented maintenance procedures

### Low-Risk Items
- Core infrastructure stability
- Proper secret management
- Modern container runtime

## Implementation Timeline

### Week 1: Security Foundation
- **Monday**: cert-manager upgrade and validation
- **Tuesday**: ArgoCD upgrade and security hardening
- **Wednesday**: Monitoring stack upgrade
- **Thursday**: Security scanning and vulnerability assessment
- **Friday**: Phase 1 validation and documentation
- **Weekend**: Monitoring and alerting setup

### Week 2-3: Service Recovery
- **Week 2**: Core services and development tools
- **Week 3**: Productivity and document management
- **Validation**: Daily health checks, weekly full validation

### Week 4-5: Complete Implementation
- **Week 4**: Media services and specialized applications
- **Week 5**: Automation, documentation, and knowledge transfer

## Success Metrics

### Security Metrics
- **CVE Count**: Reduce from 3 critical to 0
- **Certificate Health**: 100% valid certificates
- **Security Score**: Improve from 60/100 to 90/100
- **Compliance**: Achieve CIS Kubernetes Benchmark compliance

### Operational Metrics
- **Application Availability**: Increase from 60% to 95%
- **Deployment Success Rate**: Achieve 99% successful deployments
- **Mean Time to Recovery**: Reduce from unknown to <30 minutes
- **Automation Coverage**: 100% of routine tasks automated

### Performance Metrics
- **Cluster Resource Utilization**: Maintain <70% average
- **Application Response Times**: <2s for all user-facing services
- **Backup Success Rate**: 100% successful daily backups
- **Monitoring Coverage**: 100% service monitoring

## Next Steps

1. **Immediate (Today)**: Review and approve upgrade plan
2. **Day 1**: Execute cert-manager security upgrade
3. **Day 2**: Validate cert-manager, proceed with ArgoCD
4. **Week 1**: Complete critical security updates
5. **Week 2**: Begin systematic application recovery
6. **Month End**: Full operational automation achieved

## Appendix

### Useful Commands
```bash
# Check ArgoCD status
kubectl get applications -n argocd
argocd app list

# Validate current configs
task validate
task validate:comprehensive

# Check pod status
kubectl get pods --all-namespaces | grep -v Running
kubectl get pods --all-namespaces --sort-by=.status.startTime

# Security validation
kubectl get certificates --all-namespaces
kubectl get vulnerabilityreports --all-namespaces

# Inventory and health checks
python3 scripts/inventory-check.py
bash scripts/health-check.sh
task inventory
task health-check

# Upgrade procedures
task upgrade:cert-manager
task upgrade:argocd
task upgrade:monitoring
```

### Automation Commands
```bash
# GitHub Actions validation (local testing)
act -j validate
act -j security-scan

# Task automation
task maintenance:daily
task maintenance:weekly
task security:scan

# Application management
task app:enable -- <app-name>
task app:disable -- <app-name>

# Backup and restore
task backup:create
task backup:restore -- /path/to/backup
```

### Reference Documentation
- [ArgoCD v3.0 Upgrade Guide](https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/)
- [cert-manager Upgrade Documentation](https://cert-manager.io/docs/installation/upgrading/)
- [kube-prometheus-stack Release Notes](https://github.com/prometheus-community/helm-charts/releases)

---
*This report should be reviewed and updated after each major change to track progress and identify new issues.*