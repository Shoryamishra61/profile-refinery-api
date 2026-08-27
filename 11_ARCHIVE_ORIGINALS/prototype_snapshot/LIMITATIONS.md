# Known System Limitations
**Classification:** Operational Security Brief  

While our HTTP-native approach is structurally superior to browser-based Scraping, we maintain a strict register of engineering limitations and dependencies.

## 1. Upstream Query ID Volatility (Drift)
* **Description:** The system relies on hardcoded GraphQL `queryId` hashes extracted from LinkedIn's production JavaScript bundles.
* **Impact:** If LinkedIn deploys backend schema modifications and rotates these hashes, POST `/voyager/api/graphql` queries will immediately return `HTTP 400 Bad Request` or `HTTP 410 Gone`.
* **Mitigation:** The system raises an immediate `UpstreamSchemaDriftException`. Dynamic discovery protocols must be executed to scan and extract updated hashes.

## 2. Telemetry-Silence Session Decay
* **Description:** Direct API replaying executes zero mouse-clicks, page-scrolls, or extension-probing script cycles.
* **Impact:** The security edge layers monitor client activity metrics. Operating a cookie session under zero active telemetry signals causes progressive cookie trust decay, forcing session invalidations within 500 to 1,000 requests.
* **Mitigation:** Impose conservative session request ceilings (max 100 profile extractions per day per account).

## 3. Proxy Metropolitan Market Stickiness
* **Description:** Session cookies are sensitive to geographic location hopping.
* **Impact:** Routing subsequent requests through different residential IP pools (e.g., hopping from New York to Chicago in 5 minutes) triggers immediate security checkpoints (forcing password resets or SMS multi-factor codes).
* **Mitigation:** Force sticky proxy-pinning. The proxy pool must route all requests for a single session context through the same metropolitan market gateway.

## 4. Expiring Image CDN Links
* **Description:** Image download URLs served by LinkedIn contain explicit expiresAt signatures.
* **Impact:** Storing these URLs statically in databases leads to broken images for callers within 24 to 48 hours.
* **Mitigation:** The normalizer flags expired image signatures as `stale_or_expired`. The client must dispatch a fresh API request to re-generate current CDN tokens.
