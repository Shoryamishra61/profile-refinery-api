import re
from typing import Dict, List, Optional, Any

class SessionManager:
    """
    Manages and monitors programmatic session credentials.
    Performs dynamic CSRF token derivation by stripping double quotes.
    Supports session rotation and health tagging.
    """
    def __init__(self, credentials_pool: Optional[List[Dict[str, str]]] = None):
        # Default fallback pool for testing
        self.pool = credentials_pool or [
            {
                "id": "session_1",
                "li_at": "AQFAAFs29_8AAAF5-fake-li-at",
                "JSESSIONID": '"ajax:812219885785541610"',
                "status": "healthy"
            }
        ]

    def get_healthy_session(self) -> Dict[str, Any]:
        """
        Retrieves a session from the pool with "healthy" status.
        Derives the csrf-token header dynamically from JSESSIONID.
        """
        for sess in self.pool:
            if sess.get("status") == "healthy":
                # Extract and parse JSESSIONID to derive CSRF token
                raw_jsession = sess.get("JSESSIONID", "")
                # Strip leading/trailing double quotes
                csrf_token = raw_jsession.strip('"')
                
                return {
                    "id": sess["id"],
                    "li_at": sess["li_at"],
                    "JSESSIONID": raw_jsession,
                    "csrf_token": csrf_token
                }
        raise RuntimeError("Session Pool Exhausted: All programmatic credentials are EXPIRED or CHALLENGED.")

    def flag_session_failure(self, session_id: str, reason: str) -> None:
        """
        Flags a session as broken (expired or challenged) and marks it unhealthy.
        """
        for sess in self.pool:
            if sess.get("id") == session_id:
                sess["status"] = "unhealthy"
                sess["failure_reason"] = reason
                break
