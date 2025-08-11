# Traefik Forward Auth Root Cause Analysis

## Problem Statement
OAuth redirect loops persist despite `/_oauth` being added to WHITELIST. The issue is a **fundamental architecture misconfiguration**.

## Root Cause Discovery

### Current (INCORRECT) Configuration
```yaml
# apps/networking/traefik-kustomize/auth/ingressroute.yaml
spec:
  routes:
    - match: Host(`auth.lab.apj.dev`)
      kind: Rule
      services:
        - name: traefik-forward-auth
          port: 4181
```

**Problem**: This routes ALL traffic to `auth.lab.apj.dev` directly to the traefik-forward-auth container, treating it as a regular web service.

### How traefik-forward-auth Should Work

1. **ForwardAuth Middleware**: traefik-forward-auth should be used as a ForwardAuth middleware, not a direct service
2. **Auth Host Routing**: The auth host should serve a simple response or redirect, not process authentication
3. **OAuth Callback**: The `/_oauth` endpoint should be handled by the auth service when it's properly configured

### Current Behavior Analysis
1. Request to `https://auth.lab.apj.dev/_oauth` 
2. Traefik routes to traefik-forward-auth service directly
3. traefik-forward-auth processes it as an authentication request (not callback)
4. Redirects back to Microsoft OAuth
5. Infinite loop created

### Evidence
- Direct port-forward test shows malformed redirect_uri: `redirect_uri=%3A%2F%2F%2F_oauth`
- Logs show `uri=` (empty) when accessing `/_oauth`
- No OAuth callback processing visible in logs
- Service acts as authenticator, not callback handler

## Solution Options

### Option 1: Remove Auth Host IngressRoute (Recommended)
Remove the direct routing to traefik-forward-auth and let it work purely as middleware.

### Option 2: Create Proper Auth Host Service
Create a dedicated auth host service that handles the OAuth flow properly.

### Option 3: Fix traefik-forward-auth Configuration
Modify the traefik-forward-auth configuration to properly handle its own auth host.

## Implementation Plan
Testing Option 1 first as it's the most straightforward and aligns with best practices.