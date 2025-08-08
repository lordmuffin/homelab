# OAuth Configuration Issue - auth.lab.apj.dev

## Problem
Microsoft OAuth login fails with "We couldn't sign you in. Please try again." error.

## Root Cause Analysis

The OAuth configuration has a mismatch:

1. **Current Configuration**:
   - AUTH_HOST: `auth.lab.apj.dev`
   - Secret name: `auth-labs-andrewpjackson-com-apptoken-1password`
   - The secret name suggests it was originally configured for `auth.labs.andrewpjackson.com`

2. **Issue**: The Microsoft App Registration likely has the redirect URI configured for the old domain (`auth.labs.andrewpjackson.com`) but the service is now running on `auth.lab.apj.dev`.

## Solution Options

### Option 1: Update Microsoft App Registration
1. Go to Azure Portal > App Registrations
2. Find the app with Client ID: `b7545134-1236-4a22-a2a2-fb508824c04b`
3. Under Authentication > Redirect URIs, add:
   - `https://auth.lab.apj.dev/_oauth`
4. Save changes

### Option 2: Use the Original Domain
Add to `/etc/hosts`:
```
192.237.224.50 auth.labs.andrewpjackson.com
```

Then access services via the original domain that matches the OAuth configuration.

### Option 3: Create New OAuth App
1. Create a new Microsoft App Registration for `auth.lab.apj.dev`
2. Update the Kubernetes secret with new credentials
3. Restart the forward-auth deployment

## Verification

The OAuth redirect URI must match exactly. The current configuration expects:
- Issuer: `https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/v2.0`
- Redirect URI: `https://auth.lab.apj.dev/_oauth`

But Microsoft is likely configured for:
- Redirect URI: `https://auth.labs.andrewpjackson.com/_oauth`

This mismatch causes the authentication failure.