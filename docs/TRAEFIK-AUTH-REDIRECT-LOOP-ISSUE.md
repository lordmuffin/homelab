# Traefik Forward Auth - Redirect Loop Issue

## Problem
The traefik-forward-auth logs show a continuous redirect loop when trying to authenticate. The browser keeps getting redirected between:
1. `auth.lab.apj.dev` → Microsoft OAuth
2. Microsoft OAuth → back to `auth.lab.apj.dev`
3. Then immediately back to Microsoft OAuth again

## Key Observations

1. **Rapid CSRF Cookie Generation**: New CSRF cookies are being generated every second, indicating the auth flow is restarting repeatedly
2. **No OAuth Callback Processing**: The logs show redirects TO Microsoft but no processing of the OAuth callback
3. **Client Secret Exposed**: The logs show the client secret in plain text (security concern)

## Root Causes

### 1. OAuth Redirect URI Mismatch
The Microsoft App Registration expects a different redirect URI than what's configured:
- Configured: `https://auth.lab.apj.dev/_oauth`
- Microsoft might expect: `https://auth.labs.andrewpjackson.com/_oauth`

### 2. Cookie Domain Issues
The auth cookies are set for `.lab.apj.dev` domain, but if Microsoft is redirecting to a different domain, the cookies won't persist.

### 3. OAuth State Validation Failure
The state parameter in the OAuth flow might be failing validation, causing the auth to restart.

## Solution Steps

1. **Verify Microsoft App Registration**:
   - Login to Azure Portal
   - Check the redirect URIs configured for app `b7545134-1236-4a22-a2a2-fb508824c04b`
   - Ensure `https://auth.lab.apj.dev/_oauth` is listed

2. **Check Browser Developer Tools**:
   - Open Network tab
   - Try to access `https://tandoor.lab.apj.dev`
   - Look for the OAuth callback URL and any error parameters

3. **Temporary Workaround**:
   - Add both domains to /etc/hosts:
   ```
   192.237.224.50 auth.lab.apj.dev
   192.237.224.50 auth.labs.andrewpjackson.com
   ```

4. **Security Fix**:
   - The client secret should not be logged
   - Update LOG_LEVEL from "trace" to "info" or "warn"

## Debugging Commands

```bash
# Watch the OAuth flow
kubectl logs -n traefik deployment/traefik-forward-auth -f | grep -E "(_oauth|callback|error)"

# Check for any errors in the OAuth callback
curl -I "https://auth.lab.apj.dev/_oauth?error=test" -v
```

## Expected Fix

Once the redirect URI is properly configured in Microsoft Azure, the flow should be:
1. User accesses protected service
2. Redirect to Microsoft login
3. After login, redirect to `https://auth.lab.apj.dev/_oauth`
4. Forward-auth processes the callback and sets auth cookie
5. User is redirected to the original protected service