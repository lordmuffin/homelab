# Azure AD App Registration Configuration Script (Microsoft Graph)
# This script configures the auth.lab.apj.dev app registration for OAuth authentication

# Install required modules if not already installed
if (!(Get-Module -ListAvailable -Name Microsoft.Graph)) {
    Install-Module -Name Microsoft.Graph -Force -AllowClobber
}

# Connect to Microsoft Graph
Connect-MgGraph -Scopes "Application.ReadWrite.All", "Directory.ReadWrite.All", "AppRoleAssignment.ReadWrite.All"

# App registration details
$AppId = "d431c3d5-4f09-4b9a-89c3-01da167ff759"
$RedirectUri = "https://auth.lab.apj.dev/_oauth"
$UserEmail = "andrew@healingorganics.org"

Write-Host "Configuring Azure AD app registration: $AppId" -ForegroundColor Green

# 1. Get the app registration
try {
    $App = Get-MgApplication -Filter "AppId eq '$AppId'"
    if (!$App) {
        throw "Application not found"
    }
    Write-Host "✅ Found application: $($App.DisplayName)" -ForegroundColor Green
} catch {
    Write-Host "❌ Error finding application: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. Update redirect URIs
try {
    $WebRedirectUris = $App.Web.RedirectUris
    if ($WebRedirectUris -notcontains $RedirectUri) {
        $WebRedirectUris += $RedirectUri
        $WebApp = @{
            RedirectUris = $WebRedirectUris
        }
        Update-MgApplication -ApplicationId $App.Id -Web $WebApp
        Write-Host "✅ Added redirect URI: $RedirectUri" -ForegroundColor Green
    } else {
        Write-Host "✅ Redirect URI already exists: $RedirectUri" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error updating redirect URIs: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Enable ID tokens
try {
    if (!$App.Web.ImplicitGrantSettings.EnableIdTokenIssuance) {
        $WebApp = @{
            ImplicitGrantSettings = @{
                EnableIdTokenIssuance = $true
                EnableAccessTokenIssuance = $false
            }
        }
        Update-MgApplication -ApplicationId $App.Id -Web $WebApp
        Write-Host "✅ Enabled ID token issuance" -ForegroundColor Green
    } else {
        Write-Host "✅ ID token issuance already enabled" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error enabling ID tokens: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Get the service principal (enterprise application)
try {
    $ServicePrincipal = Get-MgServicePrincipal -Filter "AppId eq '$AppId'"
    if (!$ServicePrincipal) {
        # Create service principal if it doesn't exist
        $ServicePrincipal = New-MgServicePrincipal -AppId $AppId
        Write-Host "✅ Created service principal" -ForegroundColor Green
    } else {
        Write-Host "✅ Found service principal: $($ServicePrincipal.DisplayName)" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error with service principal: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Assign user to the application
try {
    $User = Get-MgUser -Filter "UserPrincipalName eq '$UserEmail'"
    if (!$User) {
        Write-Host "❌ User not found: $UserEmail" -ForegroundColor Red
    } else {
        # Check if user is already assigned
        $Assignments = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $ServicePrincipal.Id
        $ExistingAssignment = $Assignments | Where-Object { $_.PrincipalId -eq $User.Id }
        
        if (!$ExistingAssignment) {
            # Assign user to app (default role)
            $AppRoleAssignment = @{
                PrincipalId = $User.Id
                ResourceId = $ServicePrincipal.Id
                AppRoleId = "00000000-0000-0000-0000-000000000000" # Default role
            }
            New-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $ServicePrincipal.Id -BodyParameter $AppRoleAssignment
            Write-Host "✅ Assigned user to application: $UserEmail" -ForegroundColor Green
        } else {
            Write-Host "✅ User already assigned to application: $UserEmail" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "❌ Error assigning user: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Try manually assigning the user in Azure Portal: Enterprise Applications > auth.lab.apj.dev > Users and groups" -ForegroundColor Yellow
}

# 6. Check and configure API permissions
try {
    # Microsoft Graph App ID
    $GraphAppId = "00000003-0000-0000-c000-000000000000"
    $GraphServicePrincipal = Get-MgServicePrincipal -Filter "AppId eq '$GraphAppId'"
    
    # Required permissions (delegated)
    $RequiredPermissions = @(
        "openid",
        "profile", 
        "email"
    )
    
    $CurrentPermissions = $App.RequiredResourceAccess | Where-Object { $_.ResourceAppId -eq $GraphAppId }
    
    # Create OAuth2PermissionScopes array
    $OAuth2Permissions = @()
    foreach ($Permission in $RequiredPermissions) {
        $GraphPermission = $GraphServicePrincipal.Oauth2PermissionScopes | Where-Object { $_.Value -eq $Permission }
        if ($GraphPermission) {
            $OAuth2Permissions += @{
                Id = $GraphPermission.Id
                Type = "Scope"
            }
        }
    }
    
    if ($OAuth2Permissions.Count -gt 0) {
        $ResourceAccess = @{
            ResourceAppId = $GraphAppId
            ResourceAccess = $OAuth2Permissions
        }
        
        # Update the app with required permissions
        Update-MgApplication -ApplicationId $App.Id -RequiredResourceAccess @($ResourceAccess)
        Write-Host "✅ Updated API permissions (openid, profile, email)" -ForegroundColor Green
        
        # Grant admin consent
        foreach ($Permission in $OAuth2Permissions) {
            try {
                $OAuth2Grant = @{
                    ClientId = $ServicePrincipal.Id
                    ConsentType = "AllPrincipals"
                    ResourceId = $GraphServicePrincipal.Id
                    Scope = ($RequiredPermissions -join " ")
                }
                New-MgOauth2PermissionGrant -BodyParameter $OAuth2Grant
                Write-Host "✅ Granted admin consent for required scopes" -ForegroundColor Green
                break # Only need to do this once
            } catch {
                # Permission might already be granted
                Write-Host "⚠️  Admin consent may already be granted or failed: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
} catch {
    Write-Host "❌ Error configuring API permissions: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Manually grant admin consent in Azure Portal: App registrations > auth.lab.apj.dev > API permissions > Grant admin consent" -ForegroundColor Yellow
}

# 7. Display current configuration
Write-Host "`n📋 Current Configuration:" -ForegroundColor Cyan
$UpdatedApp = Get-MgApplication -Filter "AppId eq '$AppId'"
Write-Host "App ID: $AppId"
Write-Host "App Name: $($UpdatedApp.DisplayName)"
Write-Host "Redirect URIs: $($UpdatedApp.Web.RedirectUris -join ', ')"
Write-Host "ID Tokens Enabled: $($UpdatedApp.Web.ImplicitGrantSettings.EnableIdTokenIssuance)"
Write-Host "Service Principal ID: $($ServicePrincipal.Id)"

Write-Host "`n✅ Configuration complete!" -ForegroundColor Green
Write-Host "💡 Wait 5-10 minutes for changes to propagate, then test: https://tandoor.lab.apj.dev" -ForegroundColor Yellow

# 8. Test the OAuth endpoint
Write-Host "`n🔍 Testing OAuth endpoint..." -ForegroundColor Cyan
$TestUrl = "https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/oauth2/v2.0/authorize?client_id=$AppId&redirect_uri=https%3A%2F%2Fauth.lab.apj.dev%2F_oauth&response_type=code&scope=openid+profile+email&state=test"
Write-Host "Test URL: $TestUrl"
Write-Host "💡 You can test this URL in your browser to verify the configuration" -ForegroundColor Yellow

Write-Host "`n🔧 If you still have issues, check:" -ForegroundColor Cyan
Write-Host "1. User assignment in Enterprise Applications > Users and groups"
Write-Host "2. API permissions in App registrations > API permissions (should show admin consent granted)"
Write-Host "3. Authentication settings in App registrations > Authentication (ID tokens should be enabled)"
Write-Host "4. Sign-in logs in Azure AD > Sign-in logs for detailed error messages"

# Disconnect
Disconnect-MgGraph