# PowerShell script to update Azure AD redirect URI
# Run this in Azure Cloud Shell or with Azure PowerShell module installed

# Connect to Azure AD (if not already connected)
Connect-AzureAD

# Your application details
$AppId = "b7545134-1236-4a22-a2a2-fb508824c04b"
$NewRedirectUri = "https://auth.lab.apj.dev/_oauth"

# Get the current application
$App = Get-AzureADApplication -Filter "AppId eq '$AppId'"

if ($App) {
    Write-Host "Found application: $($App.DisplayName)"
    
    # Get current redirect URIs
    $CurrentUris = $App.ReplyUrls
    Write-Host "Current redirect URIs:"
    $CurrentUris | ForEach-Object { Write-Host "  - $_" }
    
    # Add new URI if not already present
    if ($NewRedirectUri -notin $CurrentUris) {
        $UpdatedUris = $CurrentUris + $NewRedirectUri
        
        # Update the application
        Set-AzureADApplication -ObjectId $App.ObjectId -ReplyUrls $UpdatedUris
        
        Write-Host "Successfully added redirect URI: $NewRedirectUri" -ForegroundColor Green
        Write-Host "Updated redirect URIs:"
        $UpdatedUris | ForEach-Object { Write-Host "  - $_" -ForegroundColor Green }
    } else {
        Write-Host "Redirect URI already exists: $NewRedirectUri" -ForegroundColor Yellow
    }
} else {
    Write-Host "Application not found with ID: $AppId" -ForegroundColor Red
}