# Manual Azure App Registration Setup

Since your personal Microsoft account doesn't have an Azure subscription, follow these steps:

## Step 1: Access Microsoft Entra (Azure AD)

1. Go to [Microsoft Entra admin center](https://entra.microsoft.com/)
2. Sign in with your `andrew.p.jackson@outlook.com` account
3. If prompted about no subscription, click "Continue anyway" or look for "Azure Active Directory" access

## Step 2: Create App Registration

1. In the left menu, find "App registrations" (may be under "Applications")
2. Click "New registration"
3. Fill out the form:
   - **Name**: `OneNote-Tandoor-Migration`
   - **Supported account types**: "Accounts in this organizational directory only"
   - **Redirect URI**: Select "Web" and enter `http://localhost:8400`
4. Click "Register"

## Step 3: Get Your Credentials

### Application (Client) ID
- On the app's Overview page, copy the **Application (client) ID**

### Tenant ID
- On the same Overview page, copy the **Directory (tenant) ID**

### Client Secret
1. Go to "Certificates & secrets" in the left menu
2. Click "New client secret"
3. Description: `Migration Tool Secret`
4. Expires: 24 months (or your preference)
5. Click "Add"
6. **IMMEDIATELY COPY THE SECRET VALUE** - you won't see it again!

## Step 4: Add API Permissions

1. Go to "API permissions" in the left menu
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions"
5. Search for and add these permissions:
   - `Notes.Read` - Read user OneNote notebooks
   - `Notes.Read.All` - Read all OneNote notebooks
6. Click "Add permissions"
7. Click "Grant admin consent for [your directory]" (important!)

## Step 5: Microsoft Authentication for Tandoor (Optional)

If your Tandoor instance is protected by Microsoft authentication middleware (like Azure AD), you'll need to provide additional credentials. The migration tool supports automatic login through Microsoft SSO.

**When to use this:**
- Your Tandoor is behind organizational SSO
- You get redirected to Microsoft login when accessing Tandoor
- Your Tandoor requires corporate credentials

**Configuration:**
- `TANDOOR_MSFT_USERNAME`: Your Microsoft/corporate username
- `TANDOOR_MSFT_PASSWORD`: Your Microsoft/corporate password  
- `TANDOOR_SKIP_MSFT_AUTH`: Set to `false` to enable authentication

**Security Note:** The tool handles the Microsoft login flow automatically, including consent screens and redirects. Credentials are only used for authentication and are not stored permanently.

## Step 6: OneNote Page Filtering

The migration tool can filter pages by name to only process specific pages containing recipes. This is useful if you have a dedicated "recipes" page within your notebook.

**Configuration Options:**
- `ONENOTE_PAGE_NAME_FILTER`: Set to `recipes` to only process pages with "recipes" in the title
- Leave empty for automatic recipe detection based on content and title keywords

**Examples:**
- `ONENOTE_PAGE_NAME_FILTER=recipes` - Only processes pages containing "recipes"
- `ONENOTE_PAGE_NAME_FILTER=cooking` - Only processes pages containing "cooking"  
- `ONENOTE_PAGE_NAME_FILTER=""` - Uses automatic recipe detection

## Step 7: Authentication Flow

**Important**: The migration tool uses **interactive authentication** which means:
- When you run the migration, a browser window will open
- You'll be prompted to sign in with your Microsoft account
- This is required because OneNote API needs delegated permissions (user access)
- The authentication is cached, so you won't need to authenticate on every run

**Alternative**: If you can't use browser authentication, the tool will fall back to device code authentication where you manually enter a code at microsoft.com/devicelogin.

## Step 8: Create Environment File

Run this command with your actual values:

```bash
cd /home/lordmuffin/Claude/Git/homelab/apps/services/tandoor/migration
./scripts/create-env.sh
```

Then edit the `.env` file to add your Tandoor credentials.

## Alternative: Manual .env Creation

Create `/home/lordmuffin/Claude/Git/homelab/apps/services/tandoor/migration/.env`:

```env
# Azure App Registration Credentials
MICROSOFT_CLIENT_ID=your_application_client_id_here
MICROSOFT_CLIENT_SECRET=your_client_secret_here
MICROSOFT_TENANT_ID=your_tenant_id_here

# Tandoor Configuration
TANDOOR_URL=https://your-tandoor-instance.com
TANDOOR_API_TOKEN=your_tandoor_api_token_here

# Microsoft Authentication for Tandoor (if protected by middleware)
TANDOOR_MSFT_USERNAME=your_microsoft_username_for_tandoor
TANDOOR_MSFT_PASSWORD=your_microsoft_password_for_tandoor
TANDOOR_SKIP_MSFT_AUTH=false

# Migration Settings
ONENOTE_NOTEBOOK_NAME=Recipes
ONENOTE_PAGE_NAME_FILTER=recipes
BATCH_SIZE=10
SKIP_DUPLICATES=true
DRY_RUN=false

# Logging
LOG_LEVEL=INFO
LOG_CONSOLE=true
```

## Troubleshooting

- If you can't access Entra admin center, try [portal.azure.com](https://portal.azure.com) and search for "Azure Active Directory"
- Personal accounts may have limited access - if you can't create app registrations, you'll need to create a free Azure account
- The tenant ID for personal accounts is often a GUID that represents your personal directory