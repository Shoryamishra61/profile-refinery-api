import re
from urllib.parse import urlparse

class URLCanonicalizer:
    """
    Parses and canonicalizes untrusted LinkedIn URLs.
    Extracts the clean, alphanumeric profile vanity slug.
    Prevents SSRF and arbitrary-host routing.
    """
    
    @staticmethod
    def canonicalize(raw_url: str) -> str:
        if not raw_url:
            raise ValueError("Input URL is empty.")
        
        # Strip outer whitespace
        raw_url = raw_url.strip()
        
        # Ensure it has a scheme, default to https if none
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url
            
        try:
            parsed = urlparse(raw_url)
        except Exception as e:
            raise ValueError(f"Malformed URL: {str(e)}")
            
        host = parsed.netloc.lower()
        
        # Strict Host Validation: MUST be linkedin.com or its subdomains
        if not (host == "linkedin.com" or host.endswith(".linkedin.com")):
            raise ValueError(f"Security Block: Arbitrary host '{host}' is prohibited. Must be linkedin.com.")
            
        path = parsed.path
        
        # Path validation: Must represent a public profile path
        # Match shapes like: /in/vanity-slug or /pub/vanity-slug
        # Match alphanumeric, dashes, and underscores in slug
        match = re.search(r"/(?:in|pub)/([A-Za-z0-9_-]+)", path)
        if not match:
            raise ValueError(f"Invalid path structure: Profile vanity slug could not be parsed from path '{path}'.")
            
        slug = match.group(1)
        if not slug:
            raise ValueError("Empty profile slug parsed from URL.")
            
        return slug
