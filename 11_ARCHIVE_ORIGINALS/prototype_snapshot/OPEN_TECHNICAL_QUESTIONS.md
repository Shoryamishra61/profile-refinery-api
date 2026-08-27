# Open Technical Questions: Experimental Calibration & Verification Plan
**Author:** Principal Protocol Researcher  
**Status:** Confidential R&D Agenda  

This document outlines the critical technical gaps that cannot be resolved from the static source corpus. Every unresolved question is mapped to the **exact evidence needed** to resolve it and paired with a **controlled, cheap experiment**.

---

## The 15 Highest-Value Unknowns

### 1. GraphQL `queryId` Rotation Frequency [P0]
* *The Unknown:* What is the exact deployment frequency of the pre-registered GraphQL hashes (`queryId`) in LinkedIn’s frontend bundles? Do they rotate daily, weekly, or only during major platform releases [402, 403]?
* *Evidence Required:* Longitudinal capture of production Webpack bundles (`chunk.905` or similar) over a 30-day window, extracting the queryId hashes for `voyagerIdentityDashProfiles` and diffing them [403, 416].
* *Controlled Experiment:* Deploy a scheduled cron job (running every 6 hours) that downloads the main profile bootstrap JavaScript file, parses out all queryIds matching the profile schemas, and alerts on any change or deprecation.

### 2. Lifespan of `li_at` Session Cookie Under Programmatic HTTP Use [P0]
* *The Unknown:* What is the exact decay rate and expiration profile of a hijacked `li_at` cookie when executed via headless HTTP queries versus a real browser session [242]?
* *Evidence Required:* HTTP response headers from sequential requests using a replayed cookie; check for `Set-Cookie` expiration updates or immediate `HTTP 401 Unauthorized` responses [101, 102].
* *Controlled Experiment:* Set up 3 identical test accounts. Log into all three via Chrome. Export the `li_at` cookie. 
  * Account A: Replay 50 requests/day using `curl_cffi` (Chrome TLS mimic).
  * Account B: Replay 50 requests/day using standard Python `requests`.
  * Account C: Keep idle. Monitor which cookies expire first and record the timestamp.

### 3. Server-Side Sensitivity to Telemetry Silence [P0]
* *The Unknown:* Does the backend actively flag accounts that query `/voyager/api/` but send zero telemetry events to `/li/track` or `/platform-telemetry/` [150, 154]?
* *Evidence Required:* Account restriction logs comparing telemetry-blocking sessions vs. telemetry-simulating sessions under identical query volumes [150].
* *Controlled Experiment:* Query 100 profiles over 48 hours using 2 distinct accounts:
  * Account A: Fire raw Voyager queries only.
  * Account B: Interleave each Voyager query with a simulated, LZ-compressed telemetry POST to `/li/track` mapping typical scroll/dwell-time events. Compare restriction outcomes.

### 4. Browser User-Agent and TLS Handshake (JA4) Mismatch [P0]
* *The Unknown:* Does the network edge instantly drop requests where the User-Agent header (e.g., Chrome 124) does not match the JA4 signature (e.g., standard Go or Python requests) [25, 267]?
* *Evidence Required:* HTTP status codes and TLS handshake logs returned from raw standard client requests versus uTLS/curl_cffi clients [25, 300].
* *Controlled Experiment:* Execute 50 GET requests targeting `/voyager/api/` using Python `requests` with a Chrome User-Agent header. Note the percentage of instant WAF blocks. Repeat using `curl_cffi` set to impersonate Chrome.

### 5. Geolocation-Session Binding Sensitivity [P1]
* *The Unknown:* What is the geographic distance threshold that triggers a session invalidation when a cookie is replayed from a new IP address [186, 224]?
* *Evidence Required:* Challenge/verification response logs when a session is moved across different regional proxies [224].
* *Controlled Experiment:* Capture a valid session cookie on an IP in New York. Replay that cookie through rotating proxies located in:
  * Cohort A: New Jersey (regional proximity).
  * Cohort B: California (cross-country).
  * Cohort C: Germany (international). Measure the time-to-challenge for each.

### 6. Profile Search vs. Direct Profile View Rate Limits [P1]
* *The Unknown:* Does querying `/voyager/api/identity/profiles/...` have a separate, sliding rate limit compared to search queries, or are they tracked under a unified session bucket [241, 242]?
* *Evidence Required:* HTTP response headers (checking for custom rate-limit indicators) or HTTP 429 status occurrences under distinct query distributions.
* *Controlled Experiment:* Split accounts into two groups. Group A queries only profiles (100/day). Group B queries search results (100/day). Run for 7 days, mapping any throttling patterns or challenges.

### 7. JSON-LD Public Fallback Rate Limits [P1]
* *The Unknown:* What is the unauthenticated public profile view limit per IP address before meeting a login wall, and does it vary between residential and datacenter proxy ranges [193, 202]?
* *Evidence Required:* Fetch response structures (inspecting for redirect locations to `/uas/login`) across a large IP pool [194, 202].
* *Controlled Experiment:* Deploy a scraper targeting public profiles without any cookies. Query at a rate of 1 request every 5 seconds. Repeat across:
  * Pool A: Datacenter IPs (AWS).
  * Pool B: Residential IPs. Track the exact request index where the login wall redirect is returned.

### 8. `JSESSIONID` Cryptographic CSRF Transformation Stability [P1]
* *The Unknown:* Is the CSRF check on state-changing requests purely a string comparison against the `JSESSIONID` cookie value, or is there a server-side cryptographic verification that checks key expiration [19, 404]?
* *Evidence Required:* HTTP 403 error rates when tampering with the alphanumeric structure of the `csrf-token` header while keeping the cookie constant [19, 404].
* *Controlled Experiment:* Replay a valid profile request but mutate the last character of the `csrf-token` header while leaving the `JSESSIONID` cookie unaltered. Check if the request is accepted.

### 9. Premium vs. Free Account Session Resiliency [P1]
* *The Unknown:* Do Sales Navigator or Premium session cookies enjoy a higher rate-limit threshold and lower fraud-score acceleration compared to standard free accounts [238, 242]?
* *Evidence Required:* Restriction rates and rate-limit thresholds mapped across account tiers [238, 242].
* *Controlled Experiment:* Deploy a parallel scrape task fetching 200 profiles/day using:
  * Account A: Free standard tier.
  * Account B: Sales Navigator tier.
  * Account C: Recruiter Lite tier. Compare restriction rates and speed-to-challenge.

### 10. Secondary Language Profile Extraction Routing [P2]
* *The Unknown:* How does the Voyager API route requests when a profile contains a secondary localized language profile? Does it require additional query parameters or headers [66]?
* *Evidence Required:* API payload responses of localized profiles, searching for alternate language arrays or translation sub-keys [66].
* *Controlled Experiment:* Intercept the network requests of a multi-language profile in a browser. Diff the REST/GraphQL queries when toggling between English and Spanish views.

### 11. Image Asset Expiry Mapping [P2]
* *The Unknown:* What is the exact mathematical lifespan of signed profile image URLs (`media.licdn.com`) returned in the JSON payload, and are they refreshable without repeating the primary query [66, 600]?
* *Evidence Required:* Extraction of the `downloadUrlExpiresAt` timestamp field from GraphQL responses and validating the image load status past that epoch [358, 600].
* *Controlled Experiment:* Fetch a profile, extract its profile image URL and the `downloadUrlExpiresAt` timestamp. Attempt to load the image URL every hour starting 24 hours prior to the expiration epoch and continuing 12 hours past it.

### 12. Couchbase Caching Latency Verification [P2]
* *The Unknown:* How long does LinkedIn cache a serialized profile in its Couchbase layer before forcing a read-through to the Espresso datastore [444, 445]?
* *Evidence Required:* Latency spikes in HTTP responses when querying a profile immediately after a member update is committed [443, 444].
* *Controlled Experiment:* Have a test user update their headline. Immediately query their profile JSON via the API every 10 seconds. Measure the exact latency in seconds before the updated headline is reflected in the API response.

### 13. Mobile API SSL Pinning Evasion via Frida [P2]
* *The Unknown:* Does the latest LinkedIn mobile application binary use custom certificate pinning or native HMAC request signing that prevents Frida-based SSL bypass [101, 102]?
* *Evidence Required:* Traffic capture status (e.g., mitmproxy handshakes) on an Android device running Frida scripts.
* *Controlled Experiment:* Install the latest LinkedIn APK on a rooted emulator. Attach Frida with a standard Certificate Pinning Bypass script. Attempt to intercept and record the API requests using `mitmproxy`.

### 14. Detection of Concurrently Shared Session Cookies [P2]
* *The Unknown:* How does LinkedIn detect a single `li_at` cookie being accessed concurrently by a real browser and our backend scraping workers [293, 294]?
* *Evidence Required:* Session restrictions committed when a session is driven in parallel [293, 294].
* *Controlled Experiment:* Log into an account on a local machine. Concurrently, have an egress worker query 1 profile per minute from a different regional IP using the same cookie. Monitor for session invalidation.

### 15. The "decoy profile" Honeytrap Signature [P2]
* *The Unknown:* Does LinkedIn deploy honeypot/decoy profiles to catch crawler traversal, and what are their specific structural or behavioral indicators [321, 339]?
* *Evidence Required:* Account bans correlated with accessing specific profiles that have zero real network connections or are designated as crawlers.
* *Controlled Experiment:* Seed a set of fresh lookups with profiles containing low engagement markers or strange vanity URLs, tracking if accessing these specific records correlates with accelerated account restrictions.
