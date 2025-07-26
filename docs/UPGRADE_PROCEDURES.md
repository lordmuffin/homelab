# Homelab Upgrade Procedures

Comprehensive procedures for safely upgrading homelab infrastructure components.

## Prerequisites

### Required Tools & Software

#### Core Tools
- **kubectl** (v1.28+) - Kubernetes command-line tool
- **helm** (v3.12+) - Kubernetes package manager
- **argocd CLI** (v2.9+) - ArgoCD command-line interface
- **task** (v3.28+) - Task runner (Go Task)
- **git** (v2.40+) - Version control system
- **jq** (v1.6+) - JSON processor for script automation

#### GitHub Integration
- **gh CLI** (v2.32+) - GitHub command-line interface
- **GitHub Actions** - CI/CD workflows enabled
- **Repository Access** - Write permissions for workflow dispatch

#### Python Dependencies
```bash
# Install required Python packages
pip install -r requirements.txt
# Core packages: PyYAML, kubernetes, click, requests
```

#### Optional Tools
- **k9s** (v0.27+) - Kubernetes TUI for monitoring
- **kubectx/kubens** - Context and namespace switching
- **stern** - Multi-pod log tailing
- **dive** - Docker image analysis

### Required Access & Permissions

#### Kubernetes Cluster Access
```bash
# Verify cluster access
kubectl auth can-i '*' '*' --all-namespaces
kubectl get nodes

# Required RBAC permissions:
# - cluster-admin or equivalent
# - ability to create/modify CRDs
# - access to all namespaces
```

#### ArgoCD Access
```bash
# Verify ArgoCD access
argocd login <server> --username admin
argocd app list
argocd version

# Required permissions:
# - admin role or applications:* permission
# - ability to sync applications
# - access to repository configurations
```

#### GitHub Actions Access
```bash
# Verify GitHub CLI authentication
gh auth status
gh workflow list

# Required permissions:
# - actions:write (trigger workflows)
# - contents:read (access repository)
# - pull_requests:write (create status checks)
```

### Required Configurations

#### Environment Setup
```bash
# Set required environment variables
export KUBECONFIG="$HOME/.kube/config"
export ARGOCD_SERVER="argocd.homelab.local"
export GITHUB_TOKEN="<your-token>"

# Verify contexts
kubectl config get-contexts
kubectl config current-context
```

#### Task Configuration
```bash
# Verify task setup
task --list-all
task validate  # Should complete without errors

# Required task dependencies:
# - kubeconform for validation
# - yamllint for YAML linting
# - Python environment for inventory scripts
```

#### Network Access
- **Cluster API** - Direct access to Kubernetes API server
- **Container Registries** - Pull access to required images
- **GitHub.com** - API and workflow access
- **ArgoCD Web UI** - Administrative access
- **Monitoring Dashboards** - Grafana and Prometheus access

### Pre-Installation Verification

#### System Requirements Check
```bash
#!/bin/bash
# File: scripts/check-prerequisites.sh

echo "🔍 Checking prerequisites..."

# Check required tools
declare -A tools=(
    ["kubectl"]="kubectl version --client"
    ["helm"]="helm version"
    ["argocd"]="argocd version --client"
    ["task"]="task --version"
    ["gh"]="gh --version"
    ["jq"]="jq --version"
    ["python3"]="python3 --version"
)

missing_tools=()
for tool in "${!tools[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        missing_tools+=("$tool")
        echo "❌ $tool not found"
    else
        echo "✅ $tool: $(${tools[$tool]} 2>/dev/null | head -1)"
    fi
done

if [ ${#missing_tools[@]} -gt 0 ]; then
    echo "❌ Missing required tools: ${missing_tools[*]}"
    exit 1
fi

# Check cluster access
echo "🔍 Checking cluster access..."
if kubectl get nodes &> /dev/null; then
    echo "✅ Kubernetes cluster accessible"
else
    echo "❌ Cannot access Kubernetes cluster"
    exit 1
fi

# Check ArgoCD access
echo "🔍 Checking ArgoCD access..."
if argocd app list &> /dev/null; then
    echo "✅ ArgoCD accessible"
else
    echo "❌ Cannot access ArgoCD - run 'argocd login'"
    exit 1
fi

# Check GitHub access
echo "🔍 Checking GitHub access..."
if gh auth status &> /dev/null; then
    echo "✅ GitHub CLI authenticated"
else
    echo "❌ GitHub CLI not authenticated - run 'gh auth login'"
    exit 1
fi

# Check Python dependencies
echo "🔍 Checking Python dependencies..."
if python3 -c "import yaml, kubernetes, click, requests" &> /dev/null; then
    echo "✅ Python dependencies available"
else
    echo "❌ Missing Python dependencies - run 'pip install -r requirements.txt'"
    exit 1
fi

echo "✅ All prerequisites satisfied"
```

#### Integration Validation
```bash
# Verify automation components before relying on them
task upgrade:validate-automation

# Run this before any upgrade to ensure automation is ready
# - GitHub Actions workflows respond correctly
# - ArgoCD can sync applications
# - Monitoring systems are collecting data
# - Backup systems are operational
```

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Upgrade Checklist](#pre-upgrade-checklist)
3. [GitHub Actions Integration](#github-actions-integration)
4. [Fallback Procedures](#fallback-procedures)
5. [Component-Specific Procedures](#component-specific-procedures)
6. [Sync Wave Strategy](#sync-wave-strategy)
7. [Validation Steps](#validation-steps)
8. [Rollback Procedures](#rollback-procedures)
9. [Implementation Status](#implementation-status)
10. [Troubleshooting](#troubleshooting)
11. [Emergency Contacts](#emergency-contacts)
12. [Maintenance Windows](#maintenance-windows)
13. [Testing Procedures](#testing-procedures)
14. [Automation & Monitoring](#automation--monitoring)

## Pre-Upgrade Checklist

### ✅ Preparation Phase (1-2 days before)

- [ ] **Review Release Notes**: Check upstream release notes for breaking changes
- [ ] **Backup Verification**: Ensure all critical data is backed up and restore-tested
- [ ] **Dependency Check**: Verify compatibility matrix between components
- [ ] **Resource Planning**: Check cluster resource availability
- [ ] **Rollback Plan**: Prepare rollback procedures and test restoration
- [ ] **Communication**: Notify team members of maintenance window
- [ ] **Change Management**: Document all planned changes and approvals

### ✅ Day-of-Upgrade Checklist

- [ ] **Cluster Health**: Verify all nodes and pods are healthy
- [ ] **ArgoCD Status**: Ensure ArgoCD is operational and synced
- [ ] **Monitoring**: Confirm monitoring stack is operational
- [ ] **GitHub Actions**: Verify CI/CD pipelines are passing
- [ ] **Security Scan**: Run comprehensive security scan and address critical issues
- [ ] **Backup Fresh**: Take fresh backup before proceeding
- [ ] **Access Verification**: Confirm access to cluster and rollback tools
- [ ] **Team Availability**: Ensure key team members are available

## GitHub Actions Integration

### 🔄 CI/CD Pipeline for Safe Upgrades

Our GitHub Actions workflows provide automated validation and security scanning to ensure safe upgrades:

#### Validation Workflow (.github/workflows/validate.yml)

**Triggers**:
- Push to main/develop branches
- Pull requests
- Manual dispatch

**Jobs**:
1. **Kustomize Validation**: Validates all kustomization builds
2. **Helm Chart Validation**: Lints and tests Helm charts
3. **Kubernetes Schema Validation**: Validates manifests against K8s schemas
4. **YAML Linting**: Checks YAML syntax and formatting
5. **ArgoCD Application Validation**: Validates ArgoCD application specs
6. **Security Scanning**: Basic security and inventory checks
7. **Summary Report**: Aggregates all validation results

**Usage**:
```bash
# Trigger validation manually
gh workflow run validate.yml

# Check validation status
gh run list --workflow=validate.yml

# View validation results
gh run view <run-id>
```

#### Security Scanning Workflow (.github/workflows/security-scan.yml)

**Comprehensive Security Analysis**:

**Jobs**:
1. **Container Security**: Trivy vulnerability scanning of all container images
2. **Infrastructure Security**: kube-score analysis for Kubernetes best practices
3. **Secret Detection**: GitLeaks scanning for exposed secrets
4. **Dependency Security**: Python/Node.js dependency vulnerability scanning
5. **Security Summary**: Comprehensive reporting with actionable insights

**Key Features**:
- **Daily Scheduled Scans**: Automated security monitoring
- **Manual Dispatch**: On-demand security assessment
- **Failure Thresholds**: Automatic failure on critical vulnerabilities
- **Comprehensive Reporting**: Detailed security posture analysis

**Usage**:
```bash
# Run full security scan
gh workflow run security-scan.yml

# Run specific scan type
gh workflow run security-scan.yml -f scan_type=containers-only

# View security reports
gh run view <run-id> --log
```

#### Pre-Upgrade Automation

**Required Checks Before Any Upgrade**:
```bash
# 1. Ensure all workflows pass
gh run list --workflow=validate.yml --status=success
gh run list --workflow=security-scan.yml --status=success

# 2. Check for critical security issues
gh run view $(gh run list --workflow=security-scan.yml --limit=1 --json databaseId --jq '.[0].databaseId')

# 3. Validate current state
task validate
python scripts/inventory-check.py --format json --output pre-upgrade-inventory.json
```

#### Post-Upgrade Validation

**Automated Post-Upgrade Checks**:
```bash
# 1. Trigger validation workflow
gh workflow run validate.yml

# 2. Run security scan
gh workflow run security-scan.yml

# 3. Wait for completion and check results
gh run watch

# 4. Generate comparison report
python scripts/inventory-check.py --format json --output post-upgrade-inventory.json
diff -u pre-upgrade-inventory.json post-upgrade-inventory.json
```

#### Integration with Renovate

**Automated Dependency Updates**:
- **Renovate Configuration**: Enhanced `renovate.json` with security-focused rules
- **Automated PRs**: Dependency updates with validation workflows
- **Security Updates**: Prioritized handling of vulnerability fixes
- **Staged Rollout**: Controlled update scheduling

**Renovate Features**:
```json
{
  "vulnerabilityAlerts": {
    "enabled": true,
    "automerge": true
  },
  "packageRules": [
    {
      "matchPackageNames": ["cert-manager", "argocd", "kube-prometheus-stack"],
      "matchUpdateTypes": ["patch"],
      "automerge": true,
      "schedule": ["before 6am on monday"]
    }
  ]
}
```

#### Workflow Status Dashboard

**Monitor CI/CD Health**:
```bash
# Check all workflow statuses
gh run list --limit=10

# Monitor specific workflows
watch 'gh run list --workflow=validate.yml --limit=5'
watch 'gh run list --workflow=security-scan.yml --limit=5'

# Get workflow success rate
gh api repos/:owner/:repo/actions/workflows/validate.yml/runs \
  --jq '.workflow_runs[:10] | group_by(.conclusion) | map({status: .[0].conclusion, count: length})'
```

## Component-Specific Procedures

### 🔐 cert-manager Upgrade

**Current**: v1.13.3 → **Target**: v1.15.5

#### Pre-Upgrade Steps
```bash
# 1. Check current certificates
kubectl get certificates --all-namespaces
kubectl get certificaterequests --all-namespaces

# 2. Backup cert-manager configuration
kubectl get -o yaml \
  certificates,certificaterequests,issuers,clusterissuers \
  --all-namespaces > cert-manager-backup.yaml

# 3. Verify webhook accessibility
kubectl get validatingwebhookconfigurations | grep cert-manager
```

#### Upgrade Process
1. **Update ArgoCD Application** (sync-wave: 1)
   - Modify `targetRevision` to `v1.15.5`
   - Remove explicit image tag overrides
   - Add `crds: enabled: true`

2. **Monitor CRD Updates**
   ```bash
   kubectl get crd | grep cert-manager
   kubectl describe crd certificates.cert-manager.io
   ```

3. **Verify Controller Startup**
   ```bash
   kubectl logs -n cert-manager deployment/cert-manager -f
   kubectl get pods -n cert-manager
   ```

#### Post-Upgrade Validation
```bash
# Verify webhook is working
kubectl get validatingwebhookconfigurations cert-manager-webhook

# Test certificate renewal
kubectl annotate certificate <cert-name> cert-manager.io/force-renewal=$(date +%s)

# Check certificate status
kubectl describe certificate <cert-name>

# Run automated validation
gh workflow run validate.yml
gh workflow run security-scan.yml

# Check for cert-manager specific issues
kubectl get certificates --all-namespaces | grep -v True
python scripts/inventory-check.py --category networking --risk-level High
```

### 🚀 ArgoCD Upgrade

**Current**: v2.9.3 → **Target**: v3.0.0

#### Pre-Upgrade Steps
```bash
# 1. Export current applications and configurations
argocd app list -o yaml > argocd-apps-backup.yaml
kubectl get configmap argocd-cm -n argocd -o yaml > argocd-config-backup.yaml

# 2. Check RBAC configurations
kubectl get clusterroles | grep argocd
kubectl get clusterrolebindings | grep argocd

# 3. Verify repository connections
argocd repo list
```

#### Upgrade Process
1. **Update Install Manifest** (sync-wave: 2)
   - Change to `v3.0.0/manifests/install.yaml`
   - Remove manual image tag overrides
   - Review overlay patches for compatibility

2. **Monitor Resource Updates**
   ```bash
   kubectl get pods -n argocd -w
   kubectl logs -n argocd deployment/argocd-server -f
   ```

3. **Verify API Access**
   ```bash
   argocd version
   argocd app list
   ```

#### Breaking Changes in v3.0
- **Enhanced RBAC**: Fine-grained permissions now default
- **API Changes**: Some v1alpha1 APIs deprecated
- **Configuration**: New security defaults

#### Post-Upgrade Tasks
```bash
# Update CLI to v3.0
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/download/v3.0.0/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

# Re-login with new CLI
argocd login <server> --username admin

# Verify all applications sync
argocd app sync --all

# Run comprehensive validation
gh workflow run validate.yml
gh workflow run security-scan.yml

# Validate ArgoCD-specific functionality
argocd app list | grep -E "(OutOfSync|Unknown|Degraded)"
python scripts/inventory-check.py --category argocd
```

### 📊 kube-prometheus-stack Upgrade

**Current**: v48.3.1 → **Target**: v75.13.0

#### Pre-Upgrade Steps
```bash
# 1. Export Grafana dashboards
kubectl get configmaps -n monitoring -l grafana_dashboard=1 -o yaml > grafana-dashboards-backup.yaml

# 2. Backup Prometheus data
kubectl exec -n monitoring prometheus-kube-prometheus-prometheus-0 -- \
  tar czf /tmp/prometheus-data.tar.gz /prometheus/

# 3. Check current metrics and alerts
kubectl get prometheusrules -n monitoring
kubectl get servicemonitors -n monitoring
```

#### Upgrade Process
1. **Update Chart Version** (sync-wave: 3)
   - Change `targetRevision` to `kube-prometheus-stack-75.13.0`
   - Update component versions in values
   - Add `RespectIgnoreDifferences=true`

2. **Monitor CRD Updates**
   ```bash
   kubectl get crd | grep monitoring.coreos.com
   kubectl logs -n monitoring deployment/kube-prometheus-kube-prome-operator -f
   ```

3. **Verify Data Retention**
   ```bash
   kubectl port-forward -n monitoring svc/kube-prometheus-kube-prome-prometheus 9090:9090
   # Check http://localhost:9090/targets
   ```

#### Component Version Updates
- **Prometheus**: v2.45.0 → v2.54.1
- **Alertmanager**: v0.25.0 → v0.27.0
- **Prometheus Operator**: v0.67.1 → v0.76.1
- **Thanos**: v0.30.1 → v0.36.1

#### Post-Upgrade Validation
```bash
# Verify all components healthy
kubectl get pods -n monitoring
kubectl get servicemonitors -n monitoring

# Check Grafana dashboards
kubectl port-forward -n monitoring svc/kube-prometheus-grafana 3000:80
# Verify dashboards load correctly

# Test alerting
kubectl patch deployment -n monitoring nginx-test --patch='{"spec":{"replicas":0}}'
# Verify alert fires in Prometheus/Alertmanager

# Run comprehensive validation
gh workflow run validate.yml
gh workflow run security-scan.yml

# Validate monitoring-specific metrics
python scripts/inventory-check.py --category monitoring
kubectl get prometheusrules -n monitoring | wc -l
kubectl get servicemonitors --all-namespaces | wc -l
```

## Sync Wave Strategy

**Wave Coordination** ensures proper upgrade sequencing:

### Wave 1: Foundation (cert-manager)
- **Purpose**: Update certificate management first
- **Dependencies**: None
- **Wait Time**: 5 minutes for CRD propagation

### Wave 2: GitOps (ArgoCD)
- **Purpose**: Update deployment orchestration
- **Dependencies**: cert-manager healthy
- **Wait Time**: 10 minutes for API availability

### Wave 3: Monitoring (kube-prometheus-stack)
- **Purpose**: Update observability stack
- **Dependencies**: ArgoCD operational
- **Wait Time**: 15 minutes for metrics collection

### Wave 4: Applications
- **Purpose**: Re-enable commented applications
- **Dependencies**: All infrastructure healthy
- **Wait Time**: 5 minutes between application groups

## Validation Steps

### Health Check Script
```bash
#!/bin/bash
# File: scripts/upgrade-validation.sh

echo "🔍 Running post-upgrade validation..."

# 1. Cluster health
kubectl get nodes
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed

# 2. ArgoCD applications
argocd app list | grep -E "(OutOfSync|Unknown|Degraded)"

# 3. Certificate status
kubectl get certificates --all-namespaces | grep -v True

# 4. Monitoring endpoints
kubectl get endpoints -n monitoring

# 5. Ingress status  
kubectl get ingress --all-namespaces

# 6. GitHub Actions validation
echo "📊 Running GitHub Actions validation..."
gh workflow run validate.yml --ref $(git branch --show-current)
gh workflow run security-scan.yml --ref $(git branch --show-current)

# Wait for workflows to complete
echo "⏳ Waiting for workflows to complete..."
sleep 30

# Check results
validate_status=$(gh run list --workflow=validate.yml --limit=1 --json conclusion --jq '.[0].conclusion')
security_status=$(gh run list --workflow=security-scan.yml --limit=1 --json conclusion --jq '.[0].conclusion')

if [[ "$validate_status" == "success" && "$security_status" == "success" ]]; then
    echo "✅ All GitHub Actions workflows passed"
else
    echo "❌ GitHub Actions validation failed"
    echo "   Validate workflow: $validate_status"
    echo "   Security workflow: $security_status"
fi

# 7. Enhanced inventory check
echo "📋 Running enhanced inventory assessment..."
python scripts/inventory-check.py --format markdown

echo "✅ Validation completed"
```

### Automated Testing
```bash
# Test certificate issuance
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: test-cert
  namespace: default
spec:
  secretName: test-cert-secret
  issuerRef:
    name: letsencrypt-staging
    kind: ClusterIssuer
  dnsNames:
  - test.example.com
EOF

# Monitor certificate issuance
kubectl wait --for=condition=Ready certificate/test-cert --timeout=300s

# Cleanup
kubectl delete certificate test-cert
kubectl delete secret test-cert-secret
```

## Rollback Procedures

### Emergency Rollback Checklist

#### 🚨 Immediate Actions (< 5 minutes)
1. **Stop Sync**: Disable ArgoCD auto-sync
   ```bash
   argocd app set <app-name> --sync-policy none
   ```

2. **Revert Critical Changes**:
   ```bash
   kubectl apply -f <previous-backup>.yaml
   ```

3. **Monitor Recovery**:
   ```bash
   kubectl get pods --all-namespaces -w
   ```

#### 📋 Systematic Rollback (5-30 minutes)

**cert-manager Rollback**:
```bash
# 1. Revert ArgoCD application
kubectl apply -f cert-manager-backup.yaml

# 2. Force pod restart if needed
kubectl rollout restart deployment/cert-manager -n cert-manager

# 3. Verify certificates
kubectl get certificates --all-namespaces
```

**ArgoCD Rollback**:
```bash
# 1. Use previous install manifest
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.11.0/manifests/install.yaml

# 2. Restore configuration
kubectl apply -f argocd-config-backup.yaml

# 3. Restart components
kubectl rollout restart deployment -n argocd
```

**kube-prometheus-stack Rollback**:
```bash
# 1. Revert to previous chart version
helm rollback kube-prometheus -n monitoring

# 2. Restore custom dashboards
kubectl apply -f grafana-dashboards-backup.yaml

# 3. Verify metrics collection
kubectl port-forward -n monitoring svc/kube-prometheus-kube-prome-prometheus 9090:9090
```

### Rollback Decision Matrix

| Issue | Severity | Rollback Threshold | Action |
|-------|----------|-------------------|---------|
| Certificate failures | High | Any cert not issued within 10 min | Immediate rollback |
| ArgoCD API unavailable | High | API down > 5 min | Immediate rollback |
| Monitoring data loss | Medium | No metrics > 15 min | Rollback during next window |
| Single app failure | Low | App-specific issue | Fix in place |

## Emergency Contacts

### Primary Contacts
- **System Administrator**: @lordmuffin
- **Backup Administrator**: [Backup contact]
- **Escalation**: [Management contact]

### Communication Channels
- **Discord**: #homelab-alerts
- **Email**: alerts@homelab.local
- **SMS**: Emergency only

### External Support
- **cert-manager**: GitHub Issues, CNCF Slack
- **ArgoCD**: GitHub Discussions, CNCF Slack  
- **Prometheus**: Prometheus Users mailing list

## Maintenance Windows

### Recommended Timing
- **Primary**: Sunday 2:00-6:00 AM EST
- **Secondary**: Wednesday 11:00 PM-1:00 AM EST
- **Emergency**: Any time with 2-hour advance notice

### Pre-Communication Template
```
Subject: Homelab Maintenance - [Date] [Time]

Scheduled maintenance window:
- Start: [DateTime]
- Duration: 2-4 hours
- Impact: Temporary service interruptions

Services affected:
- Certificate management
- GitOps deployments  
- Monitoring dashboards

Rollback plan: Ready within 30 minutes
Contact: @lordmuffin for issues

Thank you for your patience.
```

### Post-Communication Template
```
Subject: Homelab Maintenance Complete - [Date]

Maintenance completed successfully:
- Duration: [Actual time]
- Services upgraded: cert-manager, ArgoCD, monitoring
- Issues: [None/List any]

All services now operational.
Next maintenance: [Scheduled date]

Questions? Contact @lordmuffin
```

## Testing Procedures

### Development Environment Testing
1. **Clone Production**: Test on dev-lab cluster first
2. **Automated Tests**: Run CI/CD pipeline validation
3. **Manual Verification**: Test critical user flows
4. **Performance Testing**: Verify no regression
5. **Documentation**: Update procedures based on learnings

### Staging Validation
```bash
# 1. Deploy to staging cluster
kubectl config use-context staging-lab

# 2. Run upgrade procedures
./scripts/upgrade-cert-manager.sh
./scripts/upgrade-argocd.sh  
./scripts/upgrade-monitoring.sh

# 3. Automated testing
./scripts/upgrade-validation.sh

# 4. Load testing (if applicable)
kubectl apply -f test-workloads/
```

### Production Deployment
- **Maintenance Window**: Required for major upgrades
- **GitHub Actions Pre-flight**: All workflows must pass before deployment
- **Staged Rollout**: Upgrade components in waves
- **Monitoring**: Continuous monitoring during upgrade
- **Go/No-Go Decision**: At each wave completion
- **Communication**: Regular status updates
- **Post-Deployment Validation**: Automated CI/CD verification

## Automation & Monitoring

### GitHub Actions Integration

#### Pre-Upgrade Automation
```bash
# Create upgrade preparation script
#!/bin/bash
# File: scripts/prepare-upgrade.sh

echo "🚀 Preparing for upgrade..."

# 1. Run comprehensive validation
gh workflow run validate.yml --ref main
gh workflow run security-scan.yml --ref main

# 2. Generate pre-upgrade inventory
python scripts/inventory-check.py --format json --output pre-upgrade-inventory.json

# 3. Check for critical security issues
security_score=$(jq -r '.security_assessment.security_score' pre-upgrade-inventory.json)
high_risk_apps=$(jq -r '.security_assessment.high_risk_applications' pre-upgrade-inventory.json)

if [[ $high_risk_apps -gt 0 ]]; then
    echo "⚠️ High-risk applications detected: $high_risk_apps"
    echo "Review security report before proceeding"
fi

if [[ $security_score -lt 70 ]]; then
    echo "❌ Security score too low: $security_score/100"
    echo "Address security issues before upgrade"
    exit 1
fi

echo "✅ Pre-upgrade checks completed"
echo "Security Score: $security_score/100"
echo "High-Risk Apps: $high_risk_apps"
```

#### Post-Upgrade Validation
```bash
# Create post-upgrade validation script
#!/bin/bash
# File: scripts/validate-upgrade.sh

echo "🔍 Validating upgrade completion..."

# 1. Wait for all pods to be ready
kubectl wait --for=condition=Ready pods --all --all-namespaces --timeout=600s

# 2. Run GitHub Actions validation
gh workflow run validate.yml --ref main
gh workflow run security-scan.yml --ref main

# 3. Wait for workflows to complete
echo "⏳ Waiting for validation workflows..."
sleep 60

# 4. Check results
validate_run=$(gh run list --workflow=validate.yml --limit=1 --json databaseId,conclusion --jq '.[0]')
security_run=$(gh run list --workflow=security-scan.yml --limit=1 --json databaseId,conclusion --jq '.[0]')

validate_status=$(echo $validate_run | jq -r '.conclusion')
security_status=$(echo $security_run | jq -r '.conclusion')

if [[ "$validate_status" != "success" ]]; then
    echo "❌ Validation workflow failed"
    gh run view $(echo $validate_run | jq -r '.databaseId')
    exit 1
fi

if [[ "$security_status" != "success" ]]; then
    echo "❌ Security workflow failed"
    gh run view $(echo $security_run | jq -r '.databaseId')
    exit 1
fi

# 5. Generate post-upgrade comparison
python scripts/inventory-check.py --format json --output post-upgrade-inventory.json

# 6. Compare inventories
echo "📊 Upgrade Impact Analysis:"
echo "$(python scripts/compare-inventories.py pre-upgrade-inventory.json post-upgrade-inventory.json)"

echo "✅ Upgrade validation completed successfully"
```

#### Continuous Monitoring
```bash
# Setup continuous monitoring with GitHub Actions
# File: .github/workflows/health-monitor.yml

name: 🏥 Health Monitoring

on:
  schedule:
    # Every 6 hours
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Health Assessment
        run: |
          python scripts/inventory-check.py --format json --output health-report.json
          
          # Check for degraded services
          degraded_apps=$(jq -r '.summary.high_risk_applications' health-report.json)
          security_score=$(jq -r '.security_assessment.security_score' health-report.json)
          
          if [[ $degraded_apps -gt 2 ]] || [[ $security_score -lt 70 ]]; then
            echo "🚨 Health degradation detected"
            echo "High-risk applications: $degraded_apps"
            echo "Security score: $security_score/100"
            # Send alert (integrate with notification system)
          fi
```

#### Task Integration
```bash
# Enhanced Taskfile.yml commands

# Pre-upgrade preparation
task upgrade:prepare
# Runs: GitHub Actions validation, inventory check, security assessment

# Execute upgrade with validation
task upgrade:execute -- <component>
# Runs: Staged upgrade with automated validation at each step

# Post-upgrade validation
task upgrade:validate
# Runs: Comprehensive validation including GitHub Actions workflows

# Rollback if needed
task upgrade:rollback -- <component>
# Runs: Automated rollback with state verification
```

---

## References

### Official Documentation
- [cert-manager Upgrade Guide](https://cert-manager.io/docs/installation/upgrading/)
- [ArgoCD Upgrade Guide](https://argo-cd.readthedocs.io/en/stable/operator-manual/upgrading/)
- [kube-prometheus-stack Releases](https://github.com/prometheus-community/helm-charts/releases)
- [Kubernetes Version Compatibility](https://kubernetes.io/docs/setup/release/version-skew-policy/)

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Workflow Status API](https://docs.github.com/en/rest/actions/workflow-runs)

### Security Tools
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [kube-score Documentation](https://github.com/zegl/kube-score)
- [GitLeaks Documentation](https://github.com/gitleaks/gitleaks)
- [Renovate Configuration](https://docs.renovatebot.com/)

### Homelab Specific
- [Repository Structure](../README.md)
- [Task Commands](../Taskfile.yml)
- [Inventory Script](../scripts/inventory-check.py)
- [Security Assessment](../INVENTORY_REPORT.md)

*Last Updated: 2025-07-25*  
*Next Review: 2025-08-25*  
*GitHub Actions Integration: ✅ Complete*