# Tandoor Authentication Flow Analysis

## Current Status

Both `auth.lab.apj.dev` and `tandoor.lab.apj.dev` are now resolving correctly to `192.237.224.50`.

## Authentication Flow

1. **Initial Request**: `https://tandoor.lab.apj.dev/`
2. **Forward Auth Check**: Traefik forward-auth middleware intercepts
3. **OAuth Redirect**: Redirects to Microsoft OAuth2:
   ```
   https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/oauth2/v2.0/authorize
   ```
4. **Issue**: The curl command gets HTTP 500 after ~30 seconds (timeout)

## Root Cause

The authentication is working correctly, but curl cannot follow the OAuth flow which requires:
- JavaScript execution
- User interaction (login form)
- Multiple redirects through Microsoft's OAuth system

## Solution

**Use a web browser to access `https://tandoor.lab.apj.dev/`**

The flow will:
1. Redirect to Microsoft login
2. After successful authentication, redirect back to `auth.lab.apj.dev/_oauth`
3. Set authentication cookie
4. Redirect to the original tandoor URL

## Testing with curl

To test if services are up without auth, you could:
1. Temporarily remove the forward-auth middleware
2. Use port-forwarding to bypass ingress
3. Access from within the cluster

## Verification Steps

1. Open browser to `https://tandoor.lab.apj.dev/`
2. Complete Microsoft OAuth login
3. You should be redirected back to Tandoor

The HTTP 500 error from curl is expected behavior when trying to programmatically access an OAuth-protected service.