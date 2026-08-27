# Forensic Audit: PhantomBuster Documentation & Schema Contradictions
This document highlights specific, verifiable discrepancies between PhantomBuster's public marketing, documentation, and actual technical execution schemas.

---

## 1. The Profile Image Paradox
* **The Marketing / Feature Claim:** On the official LinkedIn Profile Scraper product landing page, a bold warning box states:
    > *"Important: The LinkedIn Profile Scraper doesn't extract profile pictures. For profile images, full work history, skills, and endorsements, use the LinkedIn Profile Visitor instead."*
* **The Support / Tutorial Contradiction:** Within the same website's detailed setup tutorial and technical output specifications, the following variables are explicitly listed as supported outputs of the Scraper:
    * `linkedinProfileImageUrl` (The direct URL pointing to the user's profile image).
    * `linkedinProfileImageUrn` (The direct platform URN representing the image asset).
* **Forensic Resolution:** This contradiction reveals a **product partitioning strategy** that has drifted over time. In earlier versions of the platform, profile image URLs were strictly hidden behind full-page navigation. When LinkedIn exposed image assets inside the initial JSON payload of `/voyager/api/identity/profileView` and GraphQL profile cards, PhantomBuster's engineers added the image fields to the Scraper's schema. However, the marketing team left the warning intact to continue driving upsells to the more expensive, higher-margin **Profile Visitor** product.

---

## 2. The "1,500 Profiles/Day is Safe" Fallacy
* **The Vendor Guidance:** PhantomBuster's official support articles repeatedly assure users that the Profile Scraper can "safely scrape up to 1,500 profiles per day" without risk to their accounts.
* **The Independent Enforcement Reality:** Third-party security studies and longitudinal tracking (such as Linked Helper's security audit and ConnectSafely.ai reports) paint a vastly more dangerous picture:
    * **25%–35% of heavy cloud-automation users face account restrictions** within 60 days, even when remaining strictly below the 1,500/day threshold.
    * Real-world safe limits for automated actions on standard LinkedIn accounts are actually constrained to **50–100 profiles per day**.
* **Forensic Resolution:** PhantomBuster's daily guidance is based on pure request-capacity limits of their cloud sandboxes, completely ignoring LinkedIn's server-side **Request-Map anomaly detection** (which flags accounts making direct API calls without accompanying frontend page-load telemetry) and **TLS fingerprint mismatch analysis** (blocking default Node.js or curl-based handshakes).

---

## 3. The CSV vs. JSON Fallacy
* **The Documentation Claim:** PhantomBuster states that full profile data (e.g., unlimited career and education history) is available for download in JSON format, implying that the CSV format's 2-job restriction is merely a layout limitation of spreadsheets.
* **The Technical Reality:** The Profile Scraper **applies the 2-job limit at the extraction stage**, not the export mapping stage. Regardless of whether the user downloads the output as a CSV or JSON, the work history array is strictly truncated. The only way to retrieve complete career histories is to execute a completely different runtime container using the **Profile Visitor** phantom.