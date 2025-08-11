# Azure AD OAuth Troubleshooting Checklist

## Current Issue: "We couldn't sign you in. Please try again."

### Step 1: Check Client Secret Expiration
1. Go to Azure Portal → App Registrations → auth.lab.apj.dev
2. Navigate to **Certificates & secrets**
3. Check if your client secret has expired
4. If expired, create a new secret and update your Kubernetes secret

### Step 2: Verify User Assignment
1. Go to Azure Portal → Enterprise Applications → auth.lab.apj.dev  
2. Navigate to **Users and groups**
3. Verify andrew@healingorganics.org is assigned
4. If not assigned, click **Add user/group** and add your account

### Step 3: Grant Admin Consent
1. In App Registrations → auth.lab.apj.dev
2. Go to **API permissions**
3. Click **Grant admin consent for [tenant]**
4. Confirm all permissions are granted

### Step 4: Check Sign-in Logs
1. Azure Portal → Azure Active Directory → Sign-in logs
2. Filter by your username: andrew@healingorganics.org
3. Look for recent failed sign-ins
4. Check the error details for specific AADSTS codes

### Step 5: Verify App Configuration
1. In App Registrations, confirm:
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URIs**: https://auth.lab.apj.dev/_oauth is present
   - **ID tokens**: Enabled under Authentication

### Common AADSTS Error Codes:
- **AADSTS50012**: Invalid client secret
- **AADSTS70002**: Error validating credentials  
- **AADSTS50105**: User not assigned to application
- **AADSTS65001**: User consent required

## Next Steps After Changes:
1. Wait 5-15 minutes for propagation
2. Update Kubernetes secret if client secret changed
3. Restart traefik-forward-auth pod
4. Test in incognito browser