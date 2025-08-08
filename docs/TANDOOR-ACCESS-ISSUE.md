# Tandoor Access Issue - Root Cause Analysis

## Problem
https://tandoor.lab.apj.dev is not accessible

## Root Cause
The service is working correctly but is protected by authentication middleware that redirects to `auth.lab.apj.dev`, which doesn't resolve in DNS.

## Chain of Events
1. User tries to access `tandoor.lab.apj.dev`
2. DNS resolves correctly to `192.237.224.50` (via CNAME to homelab-cloud.lab.apj.dev)
3. Traefik receives the request and applies the `traefik-forward-auth` middleware
4. The middleware redirects (HTTP 307) to `auth.lab.apj.dev` for authentication
5. Since `auth.lab.apj.dev` has no DNS entry, the authentication fails

## Solution
Add the auth.lab.apj.dev entry to your `/etc/hosts` file:

```bash
echo "192.237.224.50 auth.lab.apj.dev" | sudo tee -a /etc/hosts
```

This will fix access to BOTH:
- `auth.lab.apj.dev` - The authentication service
- `tandoor.lab.apj.dev` - The Tandoor recipes application (and any other protected services)

## Verification
After adding the hosts entry:
1. First verify auth works: `curl https://auth.lab.apj.dev`
2. Then access Tandoor: `https://tandoor.lab.apj.dev`

## Technical Details
- Tandoor is running correctly in the cluster
- The ingress route is properly configured with forward-auth middleware
- The authentication flow requires auth.lab.apj.dev to be accessible
- All protected services (using traefik-forward-auth) will have this same issue until auth.lab.apj.dev is resolvable