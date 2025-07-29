"""
Enhanced Tandoor client with Microsoft authentication middleware support.
"""
import logging
import requests
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
import time
import re

from tandoor_client import TandoorClient, TandoorAPIError

logger = logging.getLogger(__name__)


class TandoorAuthenticatedClient(TandoorClient):
    """Enhanced Tandoor client that handles Microsoft authentication middleware."""
    
    def __init__(self, base_url: str, api_token: str, 
                 msft_username: str = None, msft_password: str = None,
                 skip_msft_auth: bool = False):
        """
        Initialize Tandoor client with Microsoft authentication support.
        
        Args:
            base_url: Tandoor instance URL
            api_token: Tandoor API token
            msft_username: Microsoft account username (optional)
            msft_password: Microsoft account password (optional)
            skip_msft_auth: Skip Microsoft authentication (for testing)
        """
        self.msft_username = msft_username
        self.msft_password = msft_password
        self.skip_msft_auth = skip_msft_auth
        self.authenticated_session = None
        
        # Don't call parent __init__ yet - we need to authenticate first
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        
        # Set up basic headers and SSL handling
        self.session.headers.update({
            'User-Agent': 'OneNote-Tandoor-Migration/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        # Configure SSL and connection settings for better reliability
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set longer timeout for middleware authentication
        self.session.timeout = 30
        
        # Perform Microsoft authentication if required
        if not self.skip_msft_auth:
            self._authenticate_with_microsoft()
        
        # Now set up API authentication headers
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'  # Help identify as API request
        })
        
        # Test API connection with authentication
        self._test_authenticated_connection()
    
    def _authenticate_with_microsoft(self):
        """Handle Microsoft authentication middleware with SSL error recovery."""
        logger.info("Authenticating with Microsoft middleware...")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Step 1: Access the Tandoor URL to get redirected to Microsoft login
                logger.debug(f"Accessing Tandoor URL: {self.base_url} (attempt {attempt + 1}/{max_attempts})")
                
                # Use different approaches for SSL issues
                if attempt == 0:
                    # First attempt: normal request
                    response = self.session.get(self.base_url, allow_redirects=True, timeout=30)
                elif attempt == 1:
                    # Second attempt: disable SSL verification (for middleware issues)
                    logger.warning("Retrying with SSL verification disabled due to middleware")
                    response = self.session.get(self.base_url, allow_redirects=True, timeout=30, verify=False)
                else:
                    # Third attempt: try with different SSL context
                    import ssl
                    self.session.verify = False
                    response = self.session.get(self.base_url, allow_redirects=True, timeout=45)
                
                # Check if we're already authenticated (no redirect to Microsoft)
                if 'login.microsoftonline.com' not in response.url and response.status_code == 200:
                    logger.info("Already authenticated or no Microsoft middleware detected")
                    return
                
                # Step 2: Check if we were redirected to Microsoft login
                if 'login.microsoftonline.com' not in response.url:
                    logger.warning("No Microsoft authentication redirect detected")
                    if not self.skip_msft_auth:
                        logger.info("Proceeding without Microsoft authentication")
                    return
                
                logger.info("Microsoft authentication redirect detected")
                
                # Step 3: Handle the Microsoft login flow
                if self.msft_username and self.msft_password:
                    self._complete_microsoft_login(response)
                    return  # Success, exit retry loop
                else:
                    logger.error("Microsoft authentication required but credentials not provided")
                    raise TandoorAPIError(
                        "Microsoft authentication required. Please provide TANDOOR_MSFT_USERNAME and TANDOOR_MSFT_PASSWORD"
                    )
                    
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                logger.warning(f"SSL/Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Failed after {max_attempts} attempts")
                    if not self.skip_msft_auth:
                        raise TandoorAPIError(f"Microsoft authentication failed after {max_attempts} attempts: {e}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed during Microsoft authentication: {e}")
                if not self.skip_msft_auth:
                    raise TandoorAPIError(f"Microsoft authentication failed: {e}")
                break
    
    def _complete_microsoft_login(self, auth_response):
        """Complete the Microsoft login process."""
        logger.debug("Completing Microsoft login process")
        
        try:
            # Parse the login page to extract necessary form data
            login_data = self._extract_microsoft_login_data(auth_response.text)
            
            if not login_data:
                raise TandoorAPIError("Could not extract Microsoft login form data")
            
            # Step 1: Submit username
            logger.debug("Submitting username to Microsoft")
            username_response = self._submit_microsoft_username(login_data, auth_response.url)
            
            # Step 2: Submit password
            logger.debug("Submitting password to Microsoft")
            password_response = self._submit_microsoft_password(username_response)
            
            # Step 3: Handle potential 2FA or consent screens
            final_response = self._handle_microsoft_post_auth(password_response)
            
            # Verify we're back at Tandoor and complete the flow
            if self.base_url.replace('https://', '').replace('http://', '') in final_response.url:
                logger.info("Successfully authenticated with Microsoft middleware")
            else:
                logger.warning("Authentication completed but may not have returned to Tandoor properly")
                # Force completion of OAuth flow by accessing Tandoor directly
                logger.debug("Attempting to complete OAuth flow by accessing Tandoor")
                try:
                    final_response = self.session.get(self.base_url, allow_redirects=True, timeout=30)
                    if self.base_url.replace('https://', '').replace('http://', '') in final_response.url:
                        logger.info("Successfully completed OAuth callback flow")
                    else:
                        logger.warning("OAuth callback may not have completed properly")
                except Exception as e:
                    logger.error(f"Failed to complete OAuth callback: {e}")
                
        except Exception as e:
            logger.error(f"Microsoft login process failed: {e}")
            raise TandoorAPIError(f"Microsoft login failed: {e}")
    
    def _extract_microsoft_login_data(self, html_content: str) -> Optional[Dict[str, str]]:
        """Extract form data from Microsoft login page."""
        try:
            # Look for the login form and extract necessary fields
            form_data = {}
            
            # Extract flowToken (common in Microsoft login)
            flow_token_match = re.search(r'"sFT":"([^"]+)"', html_content)
            if flow_token_match:
                form_data['flowToken'] = flow_token_match.group(1)
            
            # Extract canary token
            canary_match = re.search(r'"canary":"([^"]+)"', html_content)
            if canary_match:
                form_data['canary'] = canary_match.group(1)
            
            # Extract ctx (context)
            ctx_match = re.search(r'"sCtx":"([^"]+)"', html_content)
            if ctx_match:
                form_data['ctx'] = ctx_match.group(1)
            
            # Extract hpgact and hpgid
            hpgact_match = re.search(r'"hpgact":([^,}]+)', html_content)
            if hpgact_match:
                form_data['hpgact'] = hpgact_match.group(1)
            
            hpgid_match = re.search(r'"hpgid":([^,}]+)', html_content)
            if hpgid_match:
                form_data['hpgid'] = hpgid_match.group(1)
            
            logger.debug(f"Extracted login form data: {list(form_data.keys())}")
            return form_data if form_data else None
            
        except Exception as e:
            logger.error(f"Failed to extract Microsoft login data: {e}")
            return None
    
    def _submit_microsoft_username(self, login_data: Dict[str, str], login_url: str) -> requests.Response:
        """Submit username to Microsoft login."""
        # Prepare form data for username submission
        form_data = {
            'i13': '0',
            'login': self.msft_username,
            'loginfmt': self.msft_username,
            'type': '11',
            'LoginOptions': '3',
            'lrt': '',
            'lrtPartition': '',
            'hisRegion': '',
            'hisScaleUnit': '',
            'passwd': '',
            'ps': '2',
            'psRNGCDefaultType': '',
            'psRNGCEntropy': '',
            'psRNGCSLK': '',
            'canary': login_data.get('canary', ''),
            'ctx': login_data.get('ctx', ''),
            'hpgrequestid': '',
            'flowToken': login_data.get('flowToken', ''),
            'PPSX': '',
            'NewUser': '1',
            'FoundMSAs': '',
            'fspost': '0',
            'i21': '0',
            'CookieDisclosure': '0',
            'IsFidoSupported': '1',
            'isSignupPost': '0',
            'i19': '15000'
        }
        
        # Update headers for form submission
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': login_url
        }
        
        response = self.session.post(login_url, data=form_data, headers=headers)
        response.raise_for_status()
        return response
    
    def _submit_microsoft_password(self, username_response: requests.Response) -> requests.Response:
        """Submit password to Microsoft login."""
        # The response should contain the password submission URL and form data
        response_data = username_response.json() if username_response.headers.get('content-type', '').startswith('application/json') else {}
        
        # Extract the URL for password submission
        if 'urlPost' in response_data:
            password_url = response_data['urlPost']
        else:
            # Fallback to constructing the URL
            password_url = username_response.url
        
        # Prepare password form data
        form_data = {
            'i13': '1',
            'login': self.msft_username,
            'loginfmt': self.msft_username,
            'type': '11',
            'LoginOptions': '3',
            'passwd': self.msft_password,
            'ps': '2',
            'jsRemember': '0',
            'flowToken': response_data.get('sFT', ''),
            'canary': response_data.get('canary', ''),
            'ctx': response_data.get('sCtx', ''),
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': username_response.url
        }
        
        response = self.session.post(password_url, data=form_data, headers=headers)
        response.raise_for_status()
        return response
    
    def _handle_microsoft_post_auth(self, password_response: requests.Response) -> requests.Response:
        """Handle post-authentication steps and complete OAuth flow."""
        current_response = password_response
        max_redirects = 10
        redirect_count = 0
        
        while redirect_count < max_redirects:
            # Check if we're back at Tandoor
            if self.base_url.replace('https://', '').replace('http://', '') in current_response.url:
                return current_response
            
            # Handle different Microsoft post-auth scenarios
            if 'login.microsoftonline.com' in current_response.url:
                if 'consent' in current_response.url.lower():
                    logger.info("Handling consent screen")
                    current_response = self._handle_consent_screen(current_response)
                elif 'mfa' in current_response.url.lower() or '2fa' in current_response.url.lower():
                    logger.warning("2FA detected - this may require manual intervention")
                    # For now, try to continue
                    current_response = self._attempt_continue(current_response)
                else:
                    # Try to follow any auto-redirects
                    current_response = self._attempt_continue(current_response)
            else:
                # Follow any remaining redirects
                current_response = self._attempt_continue(current_response)
            
            redirect_count += 1
        
        logger.warning(f"Reached maximum redirects ({max_redirects}) during post-auth handling")
        return current_response
    
    def _handle_consent_screen(self, response: requests.Response) -> requests.Response:
        """Handle Microsoft consent screen if present."""
        try:
            # Look for consent form and submit it
            if 'consent' in response.text.lower():
                # Extract form data and submit consent
                logger.debug("Submitting consent form")
                # This is a simplified consent handler - may need refinement
                consent_data = {'consent': 'yes'}
                return self.session.post(response.url, data=consent_data)
            
            return response
        except Exception as e:
            logger.error(f"Failed to handle consent screen: {e}")
            return response
    
    def _attempt_continue(self, response: requests.Response) -> requests.Response:
        """Attempt to continue through any remaining redirects or forms."""
        try:
            # Check for meta redirects
            meta_redirect = re.search(r'<meta[^>]+http-equiv[^>]+refresh[^>]+content[^>]+url=([^">]+)', response.text, re.IGNORECASE)
            if meta_redirect:
                redirect_url = meta_redirect.group(1)
                logger.debug(f"Following meta redirect to: {redirect_url}")
                return self.session.get(redirect_url)
            
            # Check for JavaScript redirects
            js_redirect = re.search(r'window\.location\.replace\(["\']([^"\']+)["\']', response.text)
            if js_redirect:
                redirect_url = js_redirect.group(1)
                logger.debug(f"Following JS redirect to: {redirect_url}")
                return self.session.get(redirect_url)
            
            # Check for form auto-submit
            form_action = re.search(r'<form[^>]+action[^>]+["\']([^"\']+)["\']', response.text, re.IGNORECASE)
            if form_action and 'autosubmit' in response.text.lower():
                form_url = form_action.group(1)
                logger.debug(f"Auto-submitting form to: {form_url}")
                return self.session.post(form_url)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to continue authentication flow: {e}")
            return response
    
    def _test_connection(self):
        """Test API connection and authentication (enhanced for middleware)."""
        try:
            # First, try to access a simple API endpoint
            response = self.session.get(f'{self.base_url}/api/user/')
            
            # If we get redirected to Microsoft login, we need to authenticate
            if 'login.microsoftonline.com' in response.url:
                logger.info("API access requires Microsoft authentication")
                if not self.skip_msft_auth:
                    self._authenticate_with_microsoft()
                    # Retry the API call
                    response = self.session.get(f'{self.base_url}/api/user/')
            
            response.raise_for_status()
            logger.info("Successfully connected to Tandoor API with authentication")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Tandoor API: {e}")
            raise TandoorAPIError(f"Connection test failed: {e}")


    def _test_authenticated_connection(self):
        """Test API connection after Microsoft authentication."""
        try:
            # Test with a simple API call that doesn't require complex permissions
            response = self.session.get(f'{self.base_url}/api/user/', timeout=30)
            
            if response.status_code == 307:  # Still being redirected
                logger.error("API calls are still being redirected - authentication session may have failed")
                # Try to re-authenticate
                if not self.skip_msft_auth:
                    logger.info("Attempting to re-authenticate...")
                    self._authenticate_with_microsoft()
                    response = self.session.get(f'{self.base_url}/api/user/', timeout=30)
            
            response.raise_for_status()
            
            # Verify we got JSON, not HTML
            if not response.headers.get('content-type', '').startswith('application/json'):
                logger.error(f"Expected JSON response, got: {response.headers.get('content-type')}")
                raise TandoorAPIError("API returned non-JSON response - authentication may have failed")
            
            logger.info("Successfully connected to Tandoor API with Microsoft authentication")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to authenticated Tandoor API: {e}")
            raise TandoorAPIError(f"Authenticated connection test failed: {e}")


def create_tandoor_client(base_url: str, api_token: str, 
                         msft_username: str = None, msft_password: str = None,
                         skip_msft_auth: bool = False) -> TandoorClient:
    """
    Factory function to create the appropriate Tandoor client.
    
    Returns TandoorAuthenticatedClient if Microsoft credentials are provided,
    otherwise returns the standard TandoorClient.
    """
    if msft_username and msft_password and not skip_msft_auth:
        logger.info("Creating authenticated Tandoor client with Microsoft middleware support")
        return TandoorAuthenticatedClient(
            base_url=base_url,
            api_token=api_token,
            msft_username=msft_username,  
            msft_password=msft_password,
            skip_msft_auth=skip_msft_auth
        )
    else:
        logger.info("Creating standard Tandoor client")
        return TandoorClient(base_url=base_url, api_token=api_token)