# Fix for auth.lab.apj.dev Accessibility Issue

## Problem Summary
The domain `auth.lab.apj.dev` is not accessible because it lacks a DNS entry pointing to the Traefik LoadBalancer.

## Root Cause Analysis

1. **DNS Resolution**: The domain returns NXDOMAIN (domain not found)
2. **Kubernetes Status**: All services are running correctly:
   - Traefik LoadBalancer: `192.237.224.50` (External IP)
   - traefik-forward-auth: Running (1/1 replicas)
   - IngressRoute: Configured correctly for `auth.lab.apj.dev`

## Solution

Add the following entry to your `/etc/hosts` file:

```bash
192.237.224.50 auth.lab.apj.dev
```

### Manual Method:
```bash
sudo nano /etc/hosts
# Add the line above
```

### Command Method:
```bash
echo "192.237.224.50 auth.lab.apj.dev" | sudo tee -a /etc/hosts
```

## Verification

After adding the hosts entry, test with:
```bash
curl -I https://auth.lab.apj.dev
```

## Alternative Solutions

1. **DNS Provider**: Add an A record for `auth.lab.apj.dev` pointing to `192.237.224.50`
2. **Local DNS**: Configure your local DNS server (if using one) to resolve the domain

## Related Services
- Similar entry exists for `dashboard.lab.apj.dev` → `50.56.48.17`
- Auth service also accessible via `auth.labs.andrewpjackson.com` → `192.168.1.40`