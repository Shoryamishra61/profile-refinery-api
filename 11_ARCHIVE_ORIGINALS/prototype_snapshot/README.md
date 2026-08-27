# LinkedIn Profile API (Pure HTTP-Native, Browser-less Implementation)

This repository contains a fully reverse-engineered, high-performance, and lightweight public HTTPS API that accepts a LinkedIn profile URL and returns comprehensive profile information as highly structured, schema-validated JSON.

In strict compliance with the **Mandatory Tross Pivot**, this system operates **entirely without a web browser at runtime**. There are zero dependencies on Selenium, Playwright, Puppeteer, Chromium, browser automation scripts, headless workers, or GUI screenshot fallbacks. All data acquisition is executed through direct, wire-level HTTP protocol requests replayed against LinkedIn's internal Rest.li and GraphQL gateways.

## Repository Layout
```
/api/
  ├── __init__.py
  ├── canonicalizer.py    # URL parsing, canonicalization, and SSRF prevention
  ├── session.py          # Session rotation and CSRF token derivation
  ├── transport.py        # Programmatic HTTP request replayer (Mock/Live modes)
  ├── resolver.py         # Member vanity slug-to-URN resolver
  ├── assembler.py        # Relational entity-graph de-flattening engine
  ├── normalizer.py       # Canonical normalization and 9-State Field Ontology mapper
  ├── models.py           # Draft-07 JSON Schema validator
  ├── errors.py           # RFC 9457 Problem Details exception mappings
  └── main.py             # FastAPI entrypoint, caller auth, rate limiter, and redactor
├── tests/
  └── test_suite.py       # Comprehensive regression test suite
├── fixtures/
  ├── jane_doe_raw.json   # Mock network payload for a rich profile (Gold Standard)
  ├── john_smith_raw.json # Mock network payload for a sparse profile
  ├── yuki_sato_raw.json  # Multilingual Japanese-English profile
  ├── bob_jones_raw.json  # Expired CDN media token profile
  └── alice_wonder_raw.json # Restricted 3rd-degree out-of-network profile
├── run_evaluation.py    # Metric-backed gold standard evaluation harness
└── requirements.txt     # Python dependency lockfile
```

## Quick Start (Local Setup & Run)

### 1. Installation
Ensure Python 3.12+ is installed, then clone this repository and install the locked dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Copy the template configuration and populate your secure credentials (only required for live integration mode; mock mode runs fully offline):
```bash
cp .env.example .env
```
Inside `.env`:
```ini
X_API_KEY=tross_test_key_123
PORT=8000
# Live mode credentials (for session manager)
LINKEDIN_LI_AT=AQFAAFs29_8AAAF5...
LINKEDIN_JSESSIONID="ajax:812219885785541610"
```

### 3. Run the Service
Start the FastAPI server on port 8000:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 4. Query the API
Query the endpoint using curl:
```bash
curl -X GET "http://localhost:8000/v1/profiles?url=https://www.linkedin.com/in/jane-doe-engineering-leader&mock=true"   -H "X-API-Key: tross_test_key_123"
```

## Executing Tests and Benchmarks
To run the automated regression test suite:
```bash
python -m unittest tests/test_suite.py
```
To run the program-level benchmarking suite comparing actual extractions against our human-verified ground truth:
```bash
python run_evaluation.py
```
