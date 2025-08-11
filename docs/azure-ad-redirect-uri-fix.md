# Azure AD Redirect URI Fix for Tandoor Authentication

## Issue
Getting "We couldn't sign you in. Please try again." error when accessing Tandoor via https://tandoor.lab.apj.dev

## Root Cause
Azure AD app registration redirect URI doesn't match the URI being sent by traefik-forward-auth.

## Current Configuration
- Client ID: `b7545134-1236-4a22-a2a2-fb508824c04b`
- Tenant ID: `5bd2f2e2-439a-4959-aefb-23be6fc9f19d`
- Current redirect URI being sent: `https://auth.lab.apj.dev/_oauth`

## Solution Steps

1. Go to Azure Portal → App Registrations
2. Find app with Client ID: `b7545134-1236-4a22-a2a2-fb508824c04b`
3. Navigate to **Authentication** section
4. Under **Redirect URIs**, add:
   ```
   https://auth.lab.apj.dev/_oauth
   ```
5. Make sure it's configured as **Web** platform (not SPA)
6. Save changes

## Verification
After updating the redirect URI:
1. Clear browser cookies for `*.lab.apj.dev`
2. Try accessing https://tandoor.lab.apj.dev again
3. Should successfully redirect to Microsoft login and back to Tandoor

## Notes
- The redirect URI must match EXACTLY (including protocol, path, case)
- No trailing slashes should be added
- This affects ALL services using the traefik-forward-auth middleware