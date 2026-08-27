# Component Interfaces: Module Definitions & Type Signatures

This document defines the strict Python type annotations, class interfaces, and boundary contracts for each core pipeline component. This ensures decoupling between components and provides robust contract enforcement.

```python
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# --- Shared Data Transfer Objects (DTOs) ---

class ProvenanceMetadata(BaseModel):
    source_operation: str = Field(..., description="The upstream API/GraphQL endpoint called")
    observation_time: str = Field(..., description="RFC 3339 timestamp of the lookup")
    raw_entity_reference: str = Field(..., description="Stable URN pointer, e.g., urn:li:member:123")
    normalization_performed: str = Field(..., description="Transformations applied to the raw value")
    schema_version: str = Field(..., description="Semantic version of the target schema")

class FieldContainer(BaseModel):
    value: Optional[Any] = Field(None, description="The normalized field value")
    status: str = Field(..., description="One of the 9-State Field Ontology values")
    provenance: Optional[ProvenanceMetadata] = Field(None, description="Provenance tracing metadata")

# --- Pipeline Interfaces ---

class URLCanonicalizer:
    """Parses and validates incoming user input to prevent SSRF and secure inputs."""
    
    @staticmethod
    def canonicalize(raw_url: str) -> str:
        """
        Validates the host is strictly linkedin.com or www.linkedin.com.
        Strips tracking parameters, query parameters, and sub-domains.
        Returns the clean, alphanumeric profile vanity slug.
        
        Raises:
            ValueError: If URL is malformed, targets internal hosts, or isn't LinkedIn.
        """
        pass


class IdentityResolver:
    """Resolves mutable vanity slugs to immutable platform URNs."""
    
    def __init__(self, transport: 'LinkedInTransportAdapter'):
        self.transport = transport

    def resolve_slug_to_urn(self, slug: str) -> str:
        """
        Executes a targeted lookup to map a vanity slug to a stable platform URN.
        Returns: e.g., 'urn:li:fsd_profile:ACoAAAtp-4U'
        
        Raises:
            LookupError: If profile does not exist.
        """
        pass


class SessionManager:
    """Manages and monitors programmatic session credentials."""
    
    def __init__(self, credentials_pool: List[Dict[str, str]]):
        self.pool = credentials_pool

    def get_healthy_session(self) -> Dict[str, Any]:
        """
        Selects a valid session containing 'li_at' and 'JSESSIONID'.
        Derives the 'csrf-token' header.
        Matches proxy bindings to avoid location mismatch triggers.
        
        Raises:
            RuntimeError: If all sessions in the pool are marked as EXPIRED or CHALLENGED.
        """
        pass

    def flag_session_failure(self, session_id: str, reason: str) -> None:
        """Flags a failing session in the pool to remove it from rotation."""
        pass


class LinkedInTransportAdapter:
    """Isolates HTTP-native communication from core normalization logic."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def execute_request(self, method: str, path: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Executes raw HTTP calls using curl_cffi to match JA4 TLS fingerprints.
        Injects the session cookies and derived 'csrf-token' header.
        
        Raises:
            ConnectionError: If network edge blocks the request.
            HTTPError: For status codes >= 400.
        """
        pass


class ResponseValidator:
    """Validates and inspects raw API responses before parsing."""
    
    @staticmethod
    def inspect_response(status_code: int, payload: Dict[str, Any]) -> None:
        """
        Checks for security checkpoints, challenges, redirects, or rate limits.
        
        Raises:
            ValueError: If payload indicates upstream schema drift or unexpected data shapes.
            PermissionError: If security challenge is triggered.
        """
        pass


class EntityAssembler:
    """Parses and de-normalizes flat JSON-LD structured REST/GraphQL arrays."""
    
    @staticmethod
    def assemble_entities(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses the nested 'included' array, linking entities (experiences, educations)
        back to parent profiles based on stable relational URNs.
        Returns a de-flattened, structured JSON graph.
        """
        pass
```
