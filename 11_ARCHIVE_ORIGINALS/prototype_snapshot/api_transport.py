import os
import json
import httpx
from typing import Dict, Optional, Any
from api.session import SessionManager
from api.errors import SessionExpiredException, SecurityChallengeException, ProfileNotFoundException

class LinkedInTransportAdapter:
    """
    Isolates HTTP-native communication from core normalization logic.
    Supports a highly robust deterministic 'mock' mode for offline testing
    and schema evaluation using local raw fixture files.
    """
    def __init__(self, session_manager: SessionManager, mock_mode: bool = True):
        self.session_manager = session_manager
        self.mock_mode = mock_mode
        self.client = httpx.Client(timeout=10.0, follow_redirects=True)

    def execute_request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None, 
        json_data: Optional[Dict] = None,
        slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes HTTP requests. If mock_mode=True, loads a deterministic raw JSON file
        representing the expected response for the specified profile vanity slug.
        """
        if self.mock_mode:
            return self._load_mock_fixture(slug, path)

        # Retrieve a healthy session context
        session_ctx = self.session_manager.get_healthy_session()
        
        # Build headers to mimic a legitimate browser client
        headers = {
            "Accept": "application/vnd.linkedin.normalized+json+2.1",
            "X-RestLi-Protocol-Version": "2.0.0",
            "csrf-token": session_ctx["csrf_token"],
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # Inject aligned cookies
        cookies = {
            "li_at": session_ctx["li_at"],
            "JSESSIONID": session_ctx["JSESSIONID"]
        }

        # Resolve relative target path to full URL
        url = f"https://www.linkedin.com{path}"

        try:
            resp = self.client.request(
                method=method,
                url=url,
                headers=headers,
                cookies=cookies,
                params=params,
                json=json_data
            )
            
            # Inspect response status codes
            if resp.status_code == 401:
                self.session_manager.flag_session_failure(session_ctx["id"], "401 Session Expired")
                raise SessionExpiredException("Programmatic session has expired or been revoked by LinkedIn.")
            elif resp.status_code == 403:
                # Could be a CSRF mismatch or rate limit / security challenge
                raise SecurityChallengeException("Access Denied: Security challenge or invalid csrf-token.")
            elif resp.status_code == 404:
                raise ProfileNotFoundException(f"Profile requested via path '{path}' was not found on the platform.")
            elif resp.status_code >= 500:
                raise httpx.HTTPStatusError(f"Upstream Server Error: {resp.status_code}", request=resp.request, response=resp)
                
            return resp.json()
            
        except httpx.RequestError as exc:
            raise ConnectionError(f"Network transport level connection failure: {str(exc)}")

    def _load_mock_fixture(self, slug: str, path: str) -> Dict[str, Any]:
        """
        Loads local mock fixture JSON files depending on slug and requested path.
        """
        if not slug:
            slug = "jane-doe-engineering-leader"
            
        # Standardize slugs to point to known mock fixtures
        if "jane-doe" in slug:
            filename = "jane_doe_raw.json"
        elif "john-smith" in slug:
            filename = "john_smith_raw.json"
        elif "yuki-sato" in slug:
            filename = "yuki_sato_raw.json"
        elif "bob-jones" in slug:
            filename = "bob_jones_raw.json"
        elif "alice-wonder" in slug:
            filename = "alice_wonder_raw.json"
        else:
            filename = "jane_doe_raw.json"

        # Separate endpoints to match specific profile-section requests
        if "contactInfo" in path:
            # Return custom mock contact details
            return {
                "emailAddress": f"{slug.replace('-','.')}@gmail.com" if "private" not in slug else None,
                "websites": [
                    {"url": f"https://{slug}.dev", "type": "PERSONAL"}
                ] if "private" not in slug else [],
                "twitterHandles": []
            }
        
        # Read the mock raw profile JSON from local file
        filepath = os.path.join('/workspace/scratch/fixtures', filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Mock fixture file '{filepath}' does not exist.")
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        return data
