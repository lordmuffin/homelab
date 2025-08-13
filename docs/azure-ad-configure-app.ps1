# Azure AD App Registration Configuration Script
# This script configures the auth.lab.apj.dev app registration for OAuth authentication

# Install required modules if not already installed
if (!(Get-Module -ListAvailable -Name AzureAD)) {
    Install-Module -Name AzureAD -Force -AllowClobber
}

# Connect to Azure AD
Connect-AzureAD

# App registration details
$AppId = "d431c3d5-4f09-4b9a-89c3-01da167ff759"
$RedirectUri = "https://auth.lab.apj.dev/_oauth"
$UserEmail = "andrew@healingorganics.org"

Write-Host "Configuring Azure AD app registration: $AppId" -ForegroundColor Green

# 1. Get the app registration
try {
    $App = Get-AzureADApplication -Filter "AppId eq '$AppId'"
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
    $ReplyUrls = $App.ReplyUrls
    if ($ReplyUrls -notcontains $RedirectUri) {
        $ReplyUrls += $RedirectUri
        Set-AzureADApplication -ObjectId $App.ObjectId -ReplyUrls $ReplyUrls
        Write-Host "✅ Added redirect URI: $RedirectUri" -ForegroundColor Green
    } else {
        Write-Host "✅ Redirect URI already exists: $RedirectUri" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error updating redirect URIs: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Enable ID tokens (implicit grant flow)
try {
    $App = Get-AzureADApplication -Filter "AppId eq '$AppId'"
    if (!$App.Oauth2AllowImplicitFlow) {
        Set-AzureADApplication -ObjectId $App.ObjectId -Oauth2AllowImplicitFlow $true
        Write-Host "✅ Enabled ID tokens (implicit grant flow)" -ForegroundColor Green
    } else {
        Write-Host "✅ ID tokens already enabled" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error enabling ID tokens: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Get the service principal (enterprise application)
try {
    $ServicePrincipal = Get-AzureADServicePrincipal -Filter "AppId eq '$AppId'"
    if (!$ServicePrincipal) {
        # Create service principal if it doesn't exist
        $ServicePrincipal = New-AzureADServicePrincipal -AppId $AppId
        Write-Host "✅ Created service principal" -ForegroundColor Green
    } else {
        Write-Host "✅ Found service principal: $($ServicePrincipal.DisplayName)" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error with service principal: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Assign user to the application
try {
    $User = Get-AzureADUser -Filter "UserPrincipalName eq '$UserEmail'"
    if (!$User) {
        Write-Host "❌ User not found: $UserEmail" -ForegroundColor Red
    } else {
        # Check if user is already assigned
        $Assignment = Get-AzureADServiceAppRoleAssignment -ObjectId $ServicePrincipal.ObjectId | Where-Object { $_.PrincipalId -eq $User.ObjectId }
        if (!$Assignment) {
            # Assign user to app (default role)
            $AppRole = $ServicePrincipal.AppRoles | Where-Object { $_.Value -eq "User" -or $_.DisplayName -eq "User" } | Select-Object -First 1
            if (!$AppRole) {
                # Use default role if no specific User role exists
                $AppRoleId = [Guid]::Empty
            } else {
                $AppRoleId = $AppRole.Id
            }
            
            New-AzureADServiceAppRoleAssignment -ObjectId $ServicePrincipal.ObjectId -PrincipalId $User.ObjectId -ResourceId $ServicePrincipal.ObjectId -Id $AppRoleId
            Write-Host "✅ Assigned user to application: $UserEmail" -ForegroundColor Green
        } else {
            Write-Host "✅ User already assigned to application: $UserEmail" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "❌ Error assigning user: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Grant admin consent for required permissions
try {
    # Get required resource access (Microsoft Graph permissions)
    $GraphServicePrincipal = Get-AzureADServicePrincipal -Filter "AppId eq '00000003-0000-0000-c000-000000000000'"
    
    # Grant admin consent for openid, profile, email scopes
    $RequiredScopes = @("openid", "profile", "email")
    
    foreach ($Scope in $RequiredScopes) {
        $Permission = $GraphServicePrincipal.OAuth2Permissions | Where-Object { $_.Value -eq $Scope }
        if ($Permission) {
            try {
                # This grants consent for the permission
                $OAuth2Grant = New-AzureADOAuth2PermissionGrant -ClientId $ServicePrincipal.ObjectId -ConsentType "AllPrincipals" -ResourceId $GraphServicePrincipal.ObjectId -Scope $Scope -StartTime (Get-Date) -ExpiryTime (Get-Date).AddYears(1)
                Write-Host "✅ Granted admin consent for scope: $Scope" -ForegroundColor Green
            } catch {
                # Permission might already be granted
                Write-Host "⚠️  Scope may already be consented: $Scope" -ForegroundColor Yellow
            }
        }
    }
} catch {
    Write-Host "❌ Error granting admin consent: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 You may need to manually grant admin consent in the Azure Portal" -ForegroundColor Yellow
}

# 7. Display current configuration
Write-Host "`n📋 Current Configuration:" -ForegroundColor Cyan
Write-Host "App ID: $AppId"
Write-Host "App Name: $($App.DisplayName)"
Write-Host "Redirect URIs: $($App.ReplyUrls -join ', ')"
Write-Host "ID Tokens Enabled: $($App.Oauth2AllowImplicitFlow)"
Write-Host "Service Principal ID: $($ServicePrincipal.ObjectId)"

Write-Host "`n✅ Configuration complete!" -ForegroundColor Green
Write-Host "💡 Wait 5-10 minutes for changes to propagate, then test: https://tandoor.lab.apj.dev" -ForegroundColor Yellow

# 8. Test the OAuth endpoint
Write-Host "`n🔍 Testing OAuth endpoint..." -ForegroundColor Cyan
$TestUrl = "https://login.microsoftonline.com/5bd2f2e2-439a-4959-aefb-23be6fc9f19d/oauth2/v2.0/authorize?client_id=$AppId&redirect_uri=https%3A%2F%2Fauth.lab.apj.dev%2F_oauth&response_type=code&scope=openid+profile+email&state=test"
Write-Host "Test URL: $TestUrl"
Write-Host "💡 You can test this URL in your browser to verify the configuration" -ForegroundColor Yellow

Write-Host "`n🔧 If you still have issues, check:" -ForegroundColor Cyan
Write-Host "1. User assignment in Enterprise Applications > auth.lab.apj.dev > Users and groups"
Write-Host "2. API permissions in App registrations > auth.lab.apj.dev > API permissions"
Write-Host "3. Sign-in logs in Azure AD > Sign-in logs for detailed error messages"