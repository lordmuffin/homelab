# Traefik Forward Auth Redirect Loop Issue - Complete Troubleshooting Guide

## Issue Summary

**Problem**: Authentication redirect loops with traefik-forward-auth causing "ERR_TOO_MANY_REDIRECTS" and "We couldn't sign you in" errors when accessing protected applications.

**Root Cause**: The OAuth callback endpoint `/_oauth` was not whitelisted in traefik-forward-auth, causing it to protect its own callback URL and creating infinite redirect loops.

**Final Solution**: Add `/_oauth` to the WHITELIST environment variable in traefik-forward-auth deployment.

## Environment Details

- **Tenant ID**: `5bd2f2e2-439a-4959-aefb-23be6fc9f19d`
- **Client ID**: `b7545134-1236-4a22-a2a2-fb508824c04b`
- **Auth Host**: `auth.lab.apj.dev`
- **OAuth Callback**: `https://auth.lab.apj.dev/_oauth`
- **User Account**: `andrew@healingorganics.org` (native to tenant)
- **Management**: ArgoCD controls deployment configuration

## Symptom Timeline

1. **Initial**: Continuous redirect loops in traefik-forward-auth logs
2. **After redirect URI fix**: Microsoft OAuth login page appears
3. **User authentication**: "We couldn't sign you in. Please try again." error
4. **Browser error**: "ERR_TOO_MANY_REDIRECTS" from login.microsoftonline.com

## Troubleshooting Process

### Phase 1: Basic Configuration Verification

#### Check Pod Status and Logs
```bash
kubectl get pods -n traefik | grep traefik-forward-auth
kubectl logs -n traefik deployment/traefik-forward-auth --tail=30
```

**Expected Issue**: Continuous redirects to Microsoft OAuth with no callback processing.

#### Verify Service Configuration
```bash
kubectl get deployment traefik-forward-auth -n traefik -o yaml | grep -A 20 env
```

### Phase 2: Azure AD Configuration Analysis

#### Check Redirect URI Configuration
1. **Azure Portal** → **Enterprise Applications** → Search Client ID
2. **Authentication** → Verify redirect URI: `https://auth.lab.apj.dev/_oauth`

**Key Finding**: Redirect URI was correctly configured but authentication still failed.

#### Analyze Sign-in Logs
1. **Azure AD** → **Sign-ins** → Look for failed attempts
2. **Critical Error Found**: `AADSTS50011` - Redirect URI mismatch

**Resolution**: Error was misleading - redirect URI was actually correct.

#### Assignment Requirements
- **Assignment required**: NO
- **User assigned**: YES (`andrew@healingorganics.org`)
- **Account status**: Enabled
- **Tenant verification**: All components in same tenant

### Phase 3: Network and DNS Verification

#### Test OAuth Endpoints
```bash
nslookup login.microsoftonline.com
curl -I "https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/oauth2/v2.0/authorize?client_id=b7545134-1236-4a22-a2a2-fb508824c04b&redirect_uri=https://auth.lab.apj.dev/_oauth&response_type=code&scope=openid&state=test"
```

**Result**: Network connectivity confirmed working.

#### Test Callback Endpoint
```bash
curl -I "https://auth.lab.apj.dev/_oauth"
```

**Critical Discovery**: Returns 307 redirect to Microsoft OAuth instead of handling callback!

### Phase 4: Traefik Configuration Analysis

#### Check Ingress Routes
```bash
kubectl get ingressroute -n traefik -o yaml | grep -A 20 "auth.lab.apj.dev"
```

**Finding**: `auth.lab.apj.dev` ingress route correctly has NO middleware applied.

#### Verify Middleware Application
```bash
kubectl get ingressroute -A -o yaml | grep -A 10 -B 5 "traefik-forward-auth"
```

**Confirmation**: Other services correctly have `traefik-forward-auth` middleware applied.

### Phase 5: Root Cause Discovery

#### OAuth Callback Protection Issue

**Problem Identified**: The `/_oauth` endpoint was being protected by traefik-forward-auth itself!

**Flow Analysis**:
1. Microsoft redirects to `https://auth.lab.apj.dev/_oauth`
2. Traefik receives request for `auth.lab.apj.dev`
3. traefik-forward-auth middleware processes request
4. `/_oauth` not in whitelist → treated as unauthenticated request
5. Redirects back to Microsoft OAuth
6. **Infinite loop created**

#### Whitelist Verification
```bash
kubectl logs -n traefik deployment/traefik-forward-auth --tail=50 | grep "Starting with config"
```

**Current Whitelist**: `/webhook,/form,/webhook-test,/test-webhook,/service-worker.js,/manifest.json,/favicon.ico,/robots.txt,/static/*,/.well-known/*,/assets/*,/css/*,/js/*,/img/*,/images/*`

**Missing**: `/_oauth`

## Solution Implementation

### Step 1: Update Deployment Configuration

Edit the deployment file:
```yaml
# File: apps/networking/traefik-kustomize/auth/deployment.yaml
- name: WHITELIST
  value: "/webhook,/form,/webhook-test,/test-webhook,/service-worker.js,/manifest.json,/favicon.ico,/robots.txt,/static/*,/.well-known/*,/assets/*,/css/*,/js/*,/img/*,/images/*,/_oauth"
```

### Step 2: Apply Changes

**Important**: Due to ArgoCD management, changes must be committed to Git first.

```bash
# Apply locally (will be overridden by ArgoCD)
kubectl apply -f apps/networking/traefik-kustomize/auth/deployment.yaml -n traefik

# Verify deployment
kubectl rollout status deployment/traefik-forward-auth -n traefik
```

### Step 3: Commit to Git

```bash
git add apps/networking/traefik-kustomize/auth/deployment.yaml
git commit -m "🐛 fix: add /_oauth to traefik-forward-auth whitelist to prevent redirect loops"
git push
```

### Step 4: ArgoCD Sync

ArgoCD will automatically detect and apply the changes.

## Verification Steps

### 1. Check Configuration Applied
```bash
kubectl logs -n traefik deployment/traefik-forward-auth --tail=5 | grep "Starting with config"
```

**Expected**: Whitelist should include `/_oauth`

### 2. Test OAuth Callback
```bash
curl -I "https://auth.lab.apj.dev/_oauth"
```

**Expected**: Should NOT return 307 redirect (should handle callback or return different response)

### 3. Test Authentication Flow
1. Clear browser cookies for `*.lab.apj.dev` and `*.microsoftonline.com`
2. Navigate to `https://tandoor.lab.apj.dev`
3. Complete Microsoft OAuth flow
4. Should redirect back to application successfully

### 4. Monitor Logs
```bash
kubectl logs -n traefik deployment/traefik-forward-auth --tail=20 -f
```

**Expected**: Should see successful OAuth callback processing instead of continuous redirects.

## Common Troubleshooting Commands

### Check Current Configuration
```bash
kubectl get deployment traefik-forward-auth -n traefik -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="WHITELIST")].value}'
```

### Force Restart (if needed)
```bash
kubectl delete pod -n traefik -l app=traefik-forward-auth
kubectl rollout status deployment/traefik-forward-auth -n traefik
```

### Check ArgoCD Status
```bash
kubectl get applications.argoproj.io -A | grep traefik
```

### Manual Environment Override (temporary)
```bash
kubectl set env deployment/traefik-forward-auth -n traefik WHITELIST="/webhook,/form,/webhook-test,/test-webhook,/service-worker.js,/manifest.json,/favicon.ico,/robots.txt,/static/*,/.well-known/*,/assets/*,/css/*,/js/*,/img/*,/images/*,/_oauth"
```

## Key Learnings

### 1. OAuth Callback Must Be Whitelisted
The OAuth provider's callback URL must be excluded from authentication to prevent loops.

### 2. ArgoCD Override Behavior
Manual `kubectl` changes are overridden by ArgoCD. All configuration changes must be committed to Git.

### 3. Misleading Error Messages
Azure AD error messages can be misleading. Always verify the actual network flow and configuration.

### 4. Browser Caching Issues
During troubleshooting, browser caching can make problems appear to persist. Always test with fresh sessions.

### 5. Log Analysis Importance
The absence of OAuth callback logs in traefik-forward-auth was the key indicator of the real problem.

## Related Files

- **Deployment**: `apps/networking/traefik-kustomize/auth/deployment.yaml`
- **Ingress Route**: `apps/networking/traefik-kustomize/auth/ingressroute.yaml`
- **Middleware**: `apps/networking/traefik-kustomize/auth/middleware.yaml`
- **Service**: `apps/networking/traefik-kustomize/auth/service.yaml`

## Environment Variables Reference

```yaml
env:
- name: DOMAIN
  value: "lab.apj.dev"
- name: COOKIE_DOMAIN  
  value: "lab.apj.dev"
- name: AUTH_HOST
  value: "auth.lab.apj.dev"
- name: DEFAULT_PROVIDER
  value: "oidc"
- name: WHITELIST
  value: "/webhook,/form,/webhook-test,/test-webhook,/service-worker.js,/manifest.json,/favicon.ico,/robots.txt,/static/*,/.well-known/*,/assets/*,/css/*,/js/*,/img/*,/images/*,/_oauth"
- name: MATCH_WHITELIST_OR_DOMAIN
  value: "true"
- name: LOG_LEVEL
  value: "debug"
```

## Testing URLs

- **Application**: `https://tandoor.lab.apj.dev`
- **Auth Host**: `https://auth.lab.apj.dev`
- **OAuth Callback**: `https://auth.lab.apj.dev/_oauth`
- **Direct OAuth Test**: `https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/oauth2/v2.0/authorize?client_id=b7545134-1236-4a22-a2a2-fb508824c04b&redirect_uri=https://auth.lab.apj.dev/_oauth&response_type=code&scope=openid+profile+email&state=test`

## Detailed Diagnostic Flow

### 1. Symptom Recognition
- Browser shows "ERR_TOO_MANY_REDIRECTS"
- Microsoft OAuth page displays "We couldn't sign you in"
- traefik-forward-auth logs show continuous redirects with no OAuth callback processing

### 2. Initial Troubleshooting (Wrong Paths Taken)
- ❌ **Browser cache clearing**: Problem persisted across devices and incognito
- ❌ **DNS/network issues**: Network connectivity was fine
- ❌ **Azure AD configuration**: Redirect URIs were correctly configured
- ❌ **Tenant mismatch**: All components in same tenant
- ❌ **User assignment**: User properly assigned and enabled

### 3. Key Breakthrough
- **Critical test**: `curl -I "https://auth.lab.apj.dev/_oauth"` returned 307 redirect
- **Discovery**: OAuth callback endpoint was being protected by auth middleware
- **Root cause**: `/_oauth` missing from WHITELIST environment variable

### 4. Solution Verification
- **Before fix**: `curl` to `/_oauth` returns 307 redirect to Microsoft
- **After fix**: Should handle callback properly or return different response
- **Auth flow**: Should complete successfully without redirect loops

## Historical Context

### Previous Troubleshooting Attempts (2024-08-07/08)
1. **AUTH-LAB-APJ-DEV-FIX.md**: Initial redirect URI investigations
2. **OAUTH-CONFIGURATION-ISSUE.md**: Azure AD configuration analysis
3. **TANDOOR-ACCESS-ISSUE.md**: Application-specific access problems
4. **TANDOOR-AUTH-FLOW-ANALYSIS.md**: Detailed authentication flow analysis

### Final Resolution (2024-08-08)
The issue was not with any of the previously investigated areas but with the basic whitelist configuration in traefik-forward-auth itself protecting its own callback endpoint.

---

**Document Updated**: 2025-08-08  
**Status**: Solution identified, implementation pending Git commit  
**Next Action**: Commit changes to Git and verify ArgoCD sync  
**Critical Fix**: Add `/_oauth` to WHITELIST in `apps/networking/traefik-kustomize/auth/deployment.yaml`