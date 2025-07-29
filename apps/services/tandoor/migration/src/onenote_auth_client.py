"""
Enhanced OneNote client with interactive user authentication for delegated permissions.
"""
import logging
from typing import List, Dict, Optional, Any
import webbrowser
from urllib.parse import parse_qs, urlparse
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

import msal
from msgraph import GraphServiceClient
from azure.identity import InteractiveBrowserCredential

from onenote_client import OneNoteClient, OneNoteRecipe

logger = logging.getLogger(__name__)


class RedirectHandler(BaseHTTPRequestHandler):
    """Handler for OAuth redirect callback."""
    
    def do_GET(self):
        """Handle the OAuth callback GET request."""
        # Parse the authorization code from the callback
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <head><title>Authentication Complete</title></head>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this browser window and return to the application.</p>
                    <script>window.close();</script>
                </body>
                </html>
            ''')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>No authorization code received. Please try again.</p>
                </body>
                </html>
            ''')
        
        # Signal that we're done
        self.server.auth_complete = True
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


class OneNoteAuthenticatedClient(OneNoteClient):
    """Enhanced OneNote client with interactive user authentication."""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str, 
                 use_interactive_auth: bool = True):
        """
        Initialize OneNote client with delegated authentication support.
        
        Args:
            client_id: Azure app client ID
            client_secret: Azure app client secret
            tenant_id: Azure tenant ID
            use_interactive_auth: Use interactive browser authentication
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.use_interactive_auth = use_interactive_auth
        self._graph_client = None
        self._msal_app = None
        self._access_token = None
        
        # Don't call parent __init__ as we need different auth flow
        self._setup_graph_client()
    
    def _setup_graph_client(self):
        """Initialize Microsoft Graph client with interactive authentication."""
        try:
            if self.use_interactive_auth:
                self._setup_interactive_auth()
            else:
                self._setup_device_code_auth()
            
            logger.info("Microsoft Graph client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Graph client: {e}")
            raise
    
    def _setup_interactive_auth(self):
        """Setup interactive browser-based authentication."""
        try:
            # For interactive auth with confidential clients, we need to handle the auth code flow manually
            # Let's fall back to device code flow which is more reliable
            logger.info("Using device code authentication for better compatibility...")
            self._setup_device_code_auth()
            
        except Exception as e:
            logger.error(f"Interactive authentication failed: {e}")
            # Fallback to device code flow
            logger.info("Falling back to device code authentication...")
            self._setup_device_code_auth()
    
    def _setup_device_code_auth(self):
        """Setup authorization code authentication with manual code entry."""
        try:
            # Create MSAL app for authorization flow
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )
            
            # Define the scopes we need
            scopes = [
                "https://graph.microsoft.com/Notes.Read",
                "https://graph.microsoft.com/Notes.Read.All"
            ]
            
            # First, try to get token from cache
            accounts = self._msal_app.get_accounts()
            if accounts:
                logger.info("Found cached account, attempting silent authentication...")
                result = self._msal_app.acquire_token_silent(scopes, account=accounts[0])
                if result and 'access_token' in result:
                    self._access_token = result['access_token']
                    self._create_graph_client_with_token()
                    return
            
            # Check if auth code was provided via environment variable
            import os
            provided_auth_code = os.environ.get('MICROSOFT_AUTH_CODE')
            
            if provided_auth_code:
                logger.info("Using provided authorization code...")
                # Use localhost redirect for the authorization flow
                redirect_uri = "http://localhost:8400"
                
                # Exchange authorization code for tokens
                result = self._msal_app.acquire_token_by_authorization_code(
                    code=provided_auth_code,
                    scopes=scopes,
                    redirect_uri=redirect_uri
                )
                
                if 'access_token' in result:
                    self._access_token = result['access_token']
                    self._create_graph_client_with_token()
                    print("Authentication successful!")
                    return
                else:
                    error_msg = result.get('error_description', 'Unknown error')
                    raise Exception(f"Authorization code authentication failed: {error_msg}")
            
            # Generate authorization URL for manual authentication
            logger.info("Starting manual authorization code flow...")
            
            # Use localhost redirect for the authorization flow
            redirect_uri = "http://localhost:8400"
            
            auth_url = self._msal_app.get_authorization_request_url(
                scopes=scopes,
                redirect_uri=redirect_uri
            )
            
            print("\n" + "="*80)
            print("MICROSOFT AUTHENTICATION REQUIRED")
            print("="*80)
            print("1. Open this URL in your browser:")
            print(f"   {auth_url}")
            print("2. Sign in with your Microsoft account")
            print("3. After authentication, you'll be redirected to localhost:8400")
            print("4. The page will show 'connection refused' - that's normal!")
            print("5. Copy the ENTIRE URL from your browser's address bar")
            print("6. Run the command again with --auth-code parameter:")
            print("   python migrate.py --auth-code 'PASTE_THE_CODE_FROM_URL_HERE'")
            print("="*80)
            
            # Since we can't get interactive input, raise an exception with instructions
            raise Exception("Please provide the authorization code using --auth-code parameter")
                
        except Exception as e:
            logger.error(f"Authorization code authentication failed: {e}")
            raise
    
    def _create_graph_client_with_token(self):
        """Create Graph client using the acquired access token."""
        # Create a custom credential that provides our token
        class CustomTokenCredential:
            def __init__(self, access_token):
                self.access_token = access_token
            
            def get_token(self, *scopes, **kwargs):
                from azure.core.credentials import AccessToken
                import time
                # Return token that expires in 1 hour (3600 seconds)
                return AccessToken(self.access_token, int(time.time()) + 3600)
        
        credential = CustomTokenCredential(self._access_token)
        
        # Create Graph client
        self._graph_client = GraphServiceClient(
            credentials=credential,
            scopes=["https://graph.microsoft.com/.default"]
        )


def create_onenote_client(client_id: str, client_secret: str, tenant_id: str,
                         use_interactive_auth: bool = True) -> OneNoteClient:
    """
    Factory function to create the appropriate OneNote client.
    
    Args:
        client_id: Azure app client ID
        client_secret: Azure app client secret  
        tenant_id: Azure tenant ID
        use_interactive_auth: Use interactive browser auth vs device code auth
        
    Returns:
        OneNoteAuthenticatedClient with delegated permissions (OneNote API requirement)
    """
    # OneNote API requires delegated permissions, so always use authenticated client
    if use_interactive_auth:
        logger.info("Creating authenticated OneNote client with browser authentication")
    else:
        logger.info("Creating authenticated OneNote client with device code authentication")
    
    return OneNoteAuthenticatedClient(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id,
        use_interactive_auth=use_interactive_auth
    )