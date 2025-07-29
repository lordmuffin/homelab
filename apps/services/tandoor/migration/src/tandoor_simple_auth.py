"""
Simplified Tandoor client with Microsoft OAuth through Traefik middleware.
"""
import logging
import requests
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs
import webbrowser

from tandoor_client import TandoorClient, TandoorAPIError

logger = logging.getLogger(__name__)


class TandoorOAuthClient(TandoorClient):
    """Simplified Tandoor client that handles Microsoft OAuth through Traefik middleware."""
    
    def __init__(self, base_url: str, api_token: str, skip_msft_auth: bool = False):
        """
        Initialize Tandoor client with Microsoft OAuth support.
        
        Args:
            base_url: Tandoor instance URL
            api_token: Tandoor API token
            skip_msft_auth: Skip Microsoft authentication (for testing)
        """
        self.skip_msft_auth = skip_msft_auth
        
        # Don't call parent __init__ yet - we need to authenticate first
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up basic headers
        self.session.headers.update({
            'User-Agent': 'OneNote-Tandoor-Migration/1.0'
        })
        
        # Perform Microsoft OAuth authentication if required
        if not self.skip_msft_auth:
            self._authenticate_with_oauth()
        
        # Now set up API authentication headers
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Referer': self.base_url,
            'Origin': self.base_url
        })
        
        # Add CSRF token to headers if we have it
        csrf_token = self.session.cookies.get('csrftoken')
        if csrf_token:
            self.session.headers.update({
                'X-CSRFToken': csrf_token
            })
        
        # Test API connection
        self._test_connection()
    
    def _authenticate_with_oauth(self):
        """Handle Microsoft OAuth authentication through Traefik middleware."""
        logger.info("Starting Microsoft OAuth authentication...")
        
        print(f"\n{'='*60}")
        print("MICROSOFT OAUTH AUTHENTICATION REQUIRED")
        print(f"{'='*60}")
        print("To authenticate with Tandoor through Microsoft OAuth:")
        print()
        print(f"1. Open your browser and go to: {self.base_url}")
        print("2. Complete the Microsoft login process")
        print("3. Once logged in successfully, return here")
        print(f"{'='*60}")
        
        # Optionally try to open browser automatically
        try:
            webbrowser.open(self.base_url)
            print("Browser opened automatically. If it didn't open, manually visit the URL above.")
        except:
            print("Please manually visit the URL above.")
        
        # Get session cookies from the user after they've logged in
        print("\nAfter logging in, we need to get your session cookies:")
        print("1. Press F12 to open Developer Tools")
        print("2. Go to the 'Network' tab")
        print("3. Refresh the page (F5)")
        print("4. Click on the first request to your Tandoor domain")
        print("5. In the 'Request Headers' section, find the 'Cookie:' line")
        print("6. Copy the entire value after 'Cookie: '")
        print()
        print("Example of what you're looking for:")
        print("Cookie: sessionid=abc123; csrftoken=xyz789; other_cookie=value")
        print("Just copy everything after 'Cookie: '")
        print()
        print("OR manually find these cookies in Application > Cookies:")
        print("- sessionid (most important)")
        print("- csrftoken") 
        print("- any other cookies from your domain")
        
        while True:
            cookies_input = input("\nPaste your cookies here: ").strip()
            if cookies_input and '=' in cookies_input:
                # Check if it looks like it has sessionid
                if 'sessionid=' in cookies_input.lower():
                    break
                else:
                    print("Make sure you include the 'sessionid' cookie - that's the main authentication cookie.")
                    continue
            print("Please enter valid cookies. Look for the 'Cookie:' header in Network tab.")
        
        # Parse and set cookies
        logger.info("Setting session cookies...")
        try:
            for cookie_pair in cookies_input.split(';'):
                if '=' in cookie_pair:
                    name, value = cookie_pair.strip().split('=', 1)
                    self.session.cookies.set(name.strip(), value.strip(), domain=urlparse(self.base_url).hostname)
            
            logger.info("Session cookies set successfully!")
            
        except Exception as e:
            logger.error(f"Failed to parse cookies: {e}")
            raise TandoorAPIError(f"Cookie parsing failed: {e}")
    
    def _test_connection(self):
        """Test API connection after authentication."""
        try:
            response = self.session.get(f'{self.base_url}/api/user/', timeout=30)
            
            # Check for redirect (authentication failed)
            if response.status_code == 307 or 'login.microsoftonline.com' in response.url:
                raise TandoorAPIError("API calls are being redirected - authentication failed")
            
            response.raise_for_status()
            
            # Verify we got JSON response
            if not response.headers.get('content-type', '').startswith('application/json'):
                raise TandoorAPIError(f"Expected JSON response, got: {response.headers.get('content-type')}")
            
            logger.info("Successfully connected to Tandoor API")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection test failed: {e}")
            raise TandoorAPIError(f"Connection test failed: {e}")


def create_tandoor_client(base_url: str, api_token: str,
                         msft_username: str = None, msft_password: str = None,
                         skip_msft_auth: bool = False) -> TandoorClient:
    """
    Factory function to create the appropriate Tandoor client.
    
    Returns TandoorOAuthClient with OAuth support, or standard TandoorClient if auth is skipped.
    """
    if not skip_msft_auth:
        logger.info("Creating OAuth-enabled Tandoor client")
        return TandoorOAuthClient(
            base_url=base_url,
            api_token=api_token,
            skip_msft_auth=skip_msft_auth
        )
    else:
        logger.info("Creating standard Tandoor client (auth skipped)")
        return TandoorClient(base_url=base_url, api_token=api_token)