# Contradiction Ledger: Discrepancy & Adversarial Analysis of Source Corpus
**Author:** Evidence Auditor & Adversarial Reviewer  
**Status:** Ground-Truth Discrepancy Map  

This ledger identifies and dissects the major contradictory claims, divergent developer assumptions, and marketing narratives found within the source corpus regarding LinkedIn profile extraction [4, 43].

---

## 1. Browser-Less API Extraction vs. "Browser Necessary" Dogma
* **Contradiction:** Several standard vendor guides (e.g., Kondo, Scrapfly) claim that because LinkedIn pages are built on dynamic JavaScript frameworks, "simple HTTP request libraries won't work" and that developers "must run a headless browser" to execute JavaScript and retrieve profile data [191, 198]. Conversely, open-source libraries (e.g., `open-linkedin-api`, `linkedin-api` wrapper) and engineering audits prove that because the web client calls structured JSON endpoints (Voyager), a raw HTTP client using a replayed `li_at` cookie and JSESSIONID CSRF token can fetch 100% of the profile data as structured JSON without executing any JavaScript or running a browser [171, 218].
* **Resolution:** The "browser necessary" claim is a simplified vendor assumption aimed at novice scrapers [191]. The web client is a Single Page Application (SPA); while it requires JavaScript to render the HTML UI for human eyes, the underlying data *is already fetched as raw JSON* via Voyager/GraphQL [171, 402]. Replaying these requests directly is highly feasible, faster, and computationally cheaper [171, 218].

---

## 2. API Stability: "Highly Fragile" vs. "Long-Term Stable"
* **Contradiction:** Unipile and LobeHub developer logs warn that LinkedIn's undocumented GraphQL endpoints "change weekly," making hardcoded custom scripts highly fragile and prone to frequent breakage [697, 723]. On the other hand, the core `linkedin-api` repository went without a single release from November 2024 through early 2026, yet remained highly functional for basic profile extraction, indicating that the fundamental resource models are relatively stable [242, 269].
* **Resolution:** The stability is highly dependent on the endpoint tier [405]. The legacy `/voyager/api/identity/profiles/{id}/profileView` REST resource is deprecated and frequently disabled, yielding HTTP 410 Gone errors [7, 402]. The newer GraphQL gateway `/voyager/api/graphql` is technically stable in structure, but the *queryId hashes* required for requests are highly volatile [402, 403]. The queryId hashes are rotated during routine web deployments, creating the illusion of a broken API schema when, in reality, only the pre-registered query hash has changed [28, 403].

---

## 3. Safe Scaling Volumes: "1,500 Profiles/Day" vs. "50-100 Profiles/Day"
* **Contradiction:** PhantomBuster's marketing material and user guides claim that a single account can safely extract up to 1,500 profiles per day without triggering security restrictions [7, 320]. However, defensive SRE audits and competing scrapers (e.g., LinkdAPI) argue that any volume exceeding 100 profiles per day on a single standard account will trigger immediate browser fingerprint checkpoints, email verifications, or account bans [238, 293].
* **Resolution:** The 1,500/day limit is highly conditional on account tier and session distribution [42, 238]. High-volume limits require aged, premium accounts (e.g., Recruiter or Sales Navigator) operating through high-reputation residential proxies that match the account owner's geolocation [238, 267]. For standard free accounts, executing 1,500 profile lookups in a single day is a major behavioral anomaly that triggers automated restrictions [339, 342].

---

## 4. IP Geolocation: "Proxy Rotation Required" vs. "Session Sticky Alignment"
* **Contradiction:** Scraping proxy providers claim that developers must rotate residential IPs on *every single request* to bypass rate limiting [11, 267]. Conversely, PhantomBuster and security audits prove that rotating the IP address on every request while maintaining the same session cookie (`li_at`) is a primary signal of session sharing or automation [186, 224]. Switch devices mid-run or changing geolocations rapidly causes LinkedIn to instantly invalidate the cookie [186, 224].
* **Resolution:** For unauthenticated public page scraping, aggressive IP rotation is necessary [409]. However, for authenticated Voyager API extraction, the IP address *must remain sticky* to the specific session [326]. Rotating geolocations under an active `li_at` cookie violates IP-session alignment, triggering immediate security checkpoints [186, 224].

---

## 5. Telemetry Blocking: "Essential Evasion" vs. "A Stark Footprint"
* **Contradiction:** Chrome extension scrapers (e.g., uBlock-style rules in Waalaxy or Dux-Soup) block outgoing pings to `/li/track`, `/platform-telemetry/li/apfcDf`, and HUMAN Security iframe endpoints, claiming it hides automation activity [150]. Conversely, security analysts prove that blocking these endpoints while continuing to make heavy profile data queries creates a highly distinctive "telemetry-silence anomaly" on the server-side, immediately flagging the user [150, 638].
* **Resolution:** Telemetry silence is its own footprint [150]. Bypassing client-side tracking scripts is only effective if the backend client *simulates* mock tracking payloads that match the profile query map, rather than sending zero tracking events [133, 134].
