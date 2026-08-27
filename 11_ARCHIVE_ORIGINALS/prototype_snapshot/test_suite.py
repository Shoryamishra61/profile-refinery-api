import sys
import unittest
from fastapi.testclient import TestClient

# Ensure /workspace/scratch/ is in path so we can import 'api' package
sys.path.insert(0, '/workspace/scratch')

from api.canonicalizer import URLCanonicalizer
from api.session import SessionManager
from api.transport import LinkedInTransportAdapter
from api.resolver import IdentityResolver
from api.assembler import EntityAssembler
from api.normalizer import CanonicalNormalizer
from api.models import SchemaValidator
from api.errors import ProblemDetailException, InvalidSlugException
from api.main import app, PIIRedactingFormatter, rate_limits_db
import logging

class TestLinkedInProfileAPI(unittest.TestCase):
    
    def setUp(self):
        # Reset the rate limits database to prevent 429 failures in parallel/sequence runs
        rate_limits_db.clear()
        self.session_mgr = SessionManager()
        self.transport = LinkedInTransportAdapter(session_manager=self.session_mgr, mock_mode=True)
        self.resolver = IdentityResolver(self.transport)
        self.normalizer = CanonicalNormalizer()
        self.validator = SchemaValidator()
        self.client = TestClient(app)

    # --- 1. URL Validation Tests ---
    def test_url_canonicalizer_valid(self):
        slug = URLCanonicalizer.canonicalize("https://www.linkedin.com/in/jane-doe-engineering-leader")
        self.assertEqual(slug, "jane-doe-engineering-leader")
        
        slug2 = URLCanonicalizer.canonicalize("linkedin.com/pub/john-smith-123?utm_source=share")
        self.assertEqual(slug2, "john-smith-123")

    def test_url_canonicalizer_invalid_host(self):
        with self.assertRaises(ValueError) as context:
            URLCanonicalizer.canonicalize("https://www.google.com/in/jane-doe")
        self.assertIn("Security Block: Arbitrary host", str(context.exception))

    def test_url_canonicalizer_ssrf_mitigation(self):
        with self.assertRaises(ValueError) as context:
            URLCanonicalizer.canonicalize("https://127.0.0.1/in/jane-doe")
        self.assertIn("Security Block", str(context.exception))

    # --- 2. Identity Resolution & Session Tests ---
    def test_identity_resolution_jane(self):
        urn = self.resolver.resolve_slug_to_urn("jane-doe-engineering-leader")
        self.assertEqual(urn, "urn:li:fsd_profile:ACoAAAtp-4U")

    def test_csrf_token_derivation(self):
        session_ctx = self.session_mgr.get_healthy_session()
        self.assertEqual(session_ctx["csrf_token"], "ajax:812219885785541610")

    def test_session_failure_marking(self):
        self.session_mgr.flag_session_failure("session_1", "Challenge triggered")
        with self.assertRaises(RuntimeError) as context:
            self.session_mgr.get_healthy_session()
        self.assertIn("Session Pool Exhausted", str(context.exception))

    # --- 3. Parsing & Normalization Tests ---
    def test_normalization_jane_rich(self):
        raw_payload = self.transport.execute_request("POST", "/voyager/api/graphql", slug="jane-doe")
        member_urn = "urn:li:fsd_profile:ACoAAAtp-4U"
        assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
        
        normalized = self.normalizer.normalize(assembled, "jane-doe", member_urn, viewer_state="V1")
        
        # Verify schema validity
        is_valid, errs = self.validator.validate(normalized)
        self.assertTrue(is_valid, f"Validation errors: {errs}")
        
        # Verify specific values & statuses
        self.assertEqual(normalized["headline"]["value"], "Engineering Director & Protocol Researcher")
        self.assertEqual(normalized["headline"]["status"], "present")
        self.assertEqual(normalized["about"]["status"], "present")
        
        # Verify multiple nested experience entries
        exp_entries = normalized["experience"]["value"]
        self.assertEqual(len(exp_entries), 3)
        self.assertEqual(exp_entries[0]["title"], "Director of Engineering")
        self.assertEqual(exp_entries[0]["company_name"], "Google")
        self.assertEqual(exp_entries[1]["title"], "Staff Software Engineer")
        self.assertEqual(exp_entries[1]["company_name"], "Google") # Grouped under same company
        self.assertEqual(exp_entries[2]["company_name"], "Facebook")

    def test_normalization_john_sparse_missing_sections(self):
        raw_payload = self.transport.execute_request("POST", "/voyager/api/graphql", slug="john-smith")
        member_urn = "urn:li:fsd_profile:ACoAAABjohn"
        assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
        
        normalized = self.normalizer.normalize(assembled, "john-smith", member_urn, viewer_state="V1")
        
        # Verify missing section handles blank about correctly
        self.assertIsNone(normalized["about"]["value"])
        self.assertEqual(normalized["about"]["status"], "not_provided")
        self.assertEqual(normalized["experience"]["status"], "not_provided")

    def test_multilingual_locale_parsing(self):
        raw_payload = self.transport.execute_request("POST", "/voyager/api/graphql", slug="yuki-sato")
        member_urn = "urn:li:fsd_profile:ACoAAACyuki"
        assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
        
        normalized = self.normalizer.normalize(assembled, "yuki-sato", member_urn, viewer_state="V2")
        self.assertEqual(normalized["headline"]["value"], "マルチリンガル ソフトウェアエンジニア / Multilingual Engineer")

    def test_image_token_expiry_handling(self):
        raw_payload = self.transport.execute_request("POST", "/voyager/api/graphql", slug="bob-jones")
        member_urn = "urn:li:fsd_profile:ACoAAADbob"
        assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
        
        normalized = self.normalizer.normalize(assembled, "bob-jones", member_urn, viewer_state="V1")
        
        # Profile Picture status must be stale_or_expired because signature expiresAt is 1600000000 (September 2020)
        self.assertEqual(normalized["profile_image"]["status"], "stale_or_expired")

    def test_out_of_network_restrictions(self):
        raw_payload = self.transport.execute_request("POST", "/voyager/api/graphql", slug="alice-wonder")
        member_urn = "urn:li:fsd_profile:ACoAAAEalice"
        assembled = EntityAssembler.assemble_entities(raw_payload, target_urn=member_urn)
        
        normalized = self.normalizer.normalize(assembled, "alice-wonder", member_urn, viewer_state="V3")
        
        # Under V3 state, summary and pictures are restricted
        self.assertEqual(normalized["about"]["status"], "not_visible_to_viewer")
        self.assertEqual(normalized["profile_image"]["status"], "not_visible_to_viewer")
        self.assertEqual(normalized["experience"]["status"], "not_visible_to_viewer")

    # --- 4. API Endpoint Integration & Error Tests ---
    def test_api_valid_mock_request(self):
        resp = self.client.get(
            "/v1/profiles?url=https://www.linkedin.com/in/jane-doe-engineering-leader&mock=true",
            headers={"X-API-Key": "tross_test_key_123"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["identity"]["value"]["vanity_slug"], "jane-doe-engineering-leader")

    def test_api_unauthorized(self):
        resp = self.client.get(
            "/v1/profiles?url=https://www.linkedin.com/in/jane-doe&mock=true",
            headers={"X-API-Key": "malicious_key"}
        )
        self.assertEqual(resp.status_code, 401)
        data = resp.json()
        self.assertEqual(data["title"], "Unauthorized Caller")

    def test_api_rate_limiter_exceeded(self):
        # Trigger rate limiter by sending 11 rapid requests
        for _ in range(10):
            self.client.get("/v1/profiles?url=https://www.linkedin.com/in/jane-doe&mock=true")
        resp = self.client.get("/v1/profiles?url=https://www.linkedin.com/in/jane-doe&mock=true")
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["title"], "API Rate Limit Exceeded")

    def test_pii_log_redaction_formatter(self):
        formatter = PIIRedactingFormatter()
        log_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Sending request with cookie: li_at=AQFAAFs29_8AAAF5-fake-li-at, JSESSIONID=\"ajax:812219885785541610\" and header X-API-Key: tross_test_key_123",
            args=(),
            exc_info=None
        )
        formatted = formatter.format(log_record)
        self.assertIn("li_at=[REDACTED]", formatted)
        self.assertIn("JSESSIONID=[REDACTED]", formatted)
        self.assertIn("X-API-Key: [REDACTED]", formatted)

if __name__ == "__main__":
    unittest.main()
