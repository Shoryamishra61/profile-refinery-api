import logging
import re
from fastapi import FastAPI, Query, Header, Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List

from api.canonicalizer import URLCanonicalizer
from api.session import SessionManager
from api.transport import LinkedInTransportAdapter
from api.resolver import IdentityResolver
from api.assembler import EntityAssembler
from api.normalizer import CanonicalNormalizer
from api.models import SchemaValidator
from api.errors import (
    ProblemDetailException, 
    InvalidSlugException, 
    RateLimitExceededException, 
    ProfileNotFoundException,
    UpstreamSchemaDriftException
)

# Custom logging formatter to redact sensitive secrets and cookie credentials
class PIIRedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # Redact cookie values
        msg = re.sub(r"li_at=[A-Za-z0-9_-]+", "li_at=[REDACTED]", msg)
        msg = re.sub(r"JSESSIONID=\"[A-Za-z0-9_:-]+\"", "JSESSIONID=[REDACTED]", msg)
        msg = re.sub(r"csrf-token=[A-Za-z0-9_:-]+", "csrf-token=[REDACTED]", msg)
        # Redact API Keys
        msg = re.sub(r"X-API-Key:\s*[A-Za-z0-9_-]+", "X-API-Key: [REDACTED]", msg)
        return msg

# Configure app logger
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(PIIRedactingFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)

app = FastAPI(
    title="Programmatic browser-less LinkedIn Extraction API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# In-memory rate limits tracker for callers (IP-based)
rate_limits_db: Dict[str, List[float]] = {}

# In-memory API key catalog for programmatic callers
API_KEYS = {"tross_test_key_123", "evaluator_secret_token_abc"}

@app.exception_handler(ProblemDetailException)
async def problem_detail_handler(request: Request, exc: ProblemDetailException):
    return exc.to_json_response()

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Standard fallback to RFC 9457 internal server error
    payload = {
        "type": "https://api.tross-profile-challenge.com/errors/internal-server-error",
        "title": "Internal Server Error",
        "status": 500,
        "detail": str(exc),
        "instance": request.url.path
    }
    return JSONResponse(
        status_code=500,
        content=payload,
        headers={"Content-Type": "application/problem+json"}
    )

@app.get("/v1/profiles")
async def get_profile(
    request: Request,
    url: str = Query(..., description="Legitimate public LinkedIn Profile URL to extract"),
    mock: bool = Query(True, description="Enable deterministic mock fixture mode for offline validation"),
    viewer_state: str = Query("V1", description="Mock viewer state: V1 (1st degree), V2 (2nd degree), V3 (3rd degree/out of network)"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    # 1. Caller Authentication
    if x_api_key and x_api_key not in API_KEYS:
        return JSONResponse(
            status_code=401,
            content={
                "type": "https://api.tross-profile-challenge.com/errors/unauthorized",
                "title": "Unauthorized Caller",
                "status": 401,
                "detail": "The provided X-API-Key header is invalid or has been revoked."
            },
            headers={"Content-Type": "application/problem+json"}
        )

    # 2. Simple Rate Limiting Check (Max 10 requests per minute per IP for testing)
    client_ip = request.client.host if request.client else "unknown"
    import time
    now = time.time()
    user_requests = rate_limits_db.get(client_ip, [])
    # Filter requests from last 60 seconds
    user_requests = [t for t in user_requests if now - t < 60]
    if len(user_requests) >= 10:
        raise RateLimitExceededException("Rate limit exceeded. Callers are restricted to 10 extractions per minute.")
    user_requests.append(now)
    rate_limits_db[client_ip] = user_requests

    # Log incoming request securely
    logger.info(f"Incoming Extraction: url='{url}', mock={mock}, viewer_state={viewer_state}, caller_key='{x_api_key}'")

    # 3. URL Canonicalization
    try:
        slug = URLCanonicalizer.canonicalize(url)
    except ValueError as val_err:
        raise InvalidSlugException(str(val_err), instance=request.url.path)

    # 4. Pipeline Execution
    session_mgr = SessionManager()
    transport = LinkedInTransportAdapter(session_manager=session_mgr, mock_mode=mock)
    resolver = IdentityResolver(transport=transport)
    
    # Resolve vanity slug to stable member URN
    member_urn = resolver.resolve_slug_to_urn(slug)
    
    # Retrieve raw profile payloads
    raw_payload = transport.execute_request(
        method="POST",
        path="/voyager/api/graphql",
        slug=slug
    )
    
    # Secondary enrichment request: GET /contactInfo
    # Under connection degree restrictions, contact info might be unavailable
    contact_payload = None
    if viewer_state != "V3":
        try:
            contact_payload = transport.execute_request(
                method="GET",
                path=f"/voyager/api/identity/profiles/{member_urn}/contactInfo",
                slug=slug
            )
        except Exception as e:
            logger.warning(f"Secondary enrichment contactInfo fetch failed: {str(e)}")

    # 5. Entity/URN Assembler
    assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
    if contact_payload:
        # Enrich profile object with email address from contact payload if present
        assembled["profile"]["email_address"] = contact_payload.get("emailAddress")
        assembled["profile"]["websites"] = contact_payload.get("websites")

    # 6. Normalization & Field Ontology Status Layer
    normalizer = CanonicalNormalizer()
    normalized_profile = normalizer.normalize(
        assembled=assembled,
        slug=slug,
        member_urn=member_urn,
        viewer_state=viewer_state
    )

    # 7. Outbound Schema Validation Check
    validator = SchemaValidator()
    is_valid, validation_errors = validator.validate(normalized_profile)
    if not is_valid:
        logger.error(f"Internal Outbound Schema Validation Defect: {validation_errors}")
        raise UpstreamSchemaDriftException(
            detail=f"Outbound profile model drifted from schema specification: {validation_errors[0]}",
            instance=request.url.path
        )

    logger.info(f"Successful Extraction: slug='{slug}', URN='{member_urn}'")
    return normalized_profile
