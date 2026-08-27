from typing import Dict, Any
from api.transport import LinkedInTransportAdapter
from api.errors import ProfileNotFoundException

class IdentityResolver:
    """
    Resolves mutable profile vanity slugs to stable platform member URNs.
    e.g., 'jane-doe' -> 'urn:li:fsd_profile:ACoAAAtp-4U'
    """
    def __init__(self, transport: LinkedInTransportAdapter):
        self.transport = transport

    def resolve_slug_to_urn(self, slug: str) -> str:
        """
        Executes an identity mapping lookup.
        In mock/fixture mode, retrieves from the loaded json representation.
        """
        try:
            raw_payload = self.transport.execute_request(
                method="POST",
                path="/voyager/api/graphql",
                slug=slug
            )
            
            # Find the member profile block to extract stable URN
            elements = raw_payload.get("data", {}).get("voyagerIdentityDashProfiles", {}).get("elements", [])
            if not elements:
                # Fallback to check raw Jane Doe structure from RAW_FIXTURE_SPEC
                elements = raw_payload.get("data", {}).get("identityDashProfilesByMemberIdentity", {}).get("*elements", [])
                if elements:
                    return elements[0]
                
            if elements and "entityUrn" in elements[0]:
                return elements[0]["entityUrn"]
                
            # If nothing in elements, inspect the 'included' block for any Profile type
            included = raw_payload.get("included", [])
            for item in included:
                if item.get("$type") == "com.linkedin.voyager.dash.identity.Profile":
                    return item["entityUrn"]
                    
            # Fallback for Jane Doe structure
            for item in included:
                if "urn:li:fsd_profile" in item.get("entityUrn", ""):
                    return item["entityUrn"]
                    
            raise ProfileNotFoundException(f"Profile resolution failed: Unable to map slug '{slug}' to a stable member URN.")
            
        except FileNotFoundError:
            raise ProfileNotFoundException(f"Profile resolution failed: Mock fixture for slug '{slug}' was not found.")
