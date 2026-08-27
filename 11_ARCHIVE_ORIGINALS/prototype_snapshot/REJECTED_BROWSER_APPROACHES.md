# Rejected Browser-Based Architectures: Teardown & Forensic Failure Analysis
**Author:** Director of Defensive Engineering & Adversarial Reviewer  
**Status:** Architecture Deprecation Record  

To protect our development resources and guarantee account longevity, we are explicitly **rejecting** several highly public but structurally insecure web-automation paradigms. This document explains why these browser-driven models fail under LinkedIn's adversarial scanning.

---

## 1. Selenium-Based Page Traversal (DOM Scraping)
* **The Method:** Launching Chrome or Firefox via a standard Selenium WebDriver, navigating to profile URLs, waiting for the DOM elements to load, and parsing the HTML content via XPath or CSS selectors [201, 264].
* **Forensic Reason for Rejection:**
  1. **Brittle Selectors:** LinkedIn's frontend microservices frequently alter CSS class names and layout structures during canaries and routine deployments, immediately breaking parser logic [201, 202].
  2. **CDP & WebDriver Flags:** Standard Selenium-driven browsers expose the `navigator.webdriver` property and custom Javascript variables, which are immediately scanned by LinkedIn's basic fingerprinting script (`getHasLiedBrowser()`), flagging the account for a ban [1004, 1061].
  3. **Performance Overhead:** Running full GUI-less browser containers consumes massive RAM and CPU, severely limiting scalability and API throughput [209, 306].

---

## 2. Playwright / Puppeteer with "Stealth" Plugins
* **The Method:** Re-writing native browser objects (e.g., masking the webdriver flag, spoofing plugins, injecting consistent fonts) using libraries like `puppeteer-extra-plugin-stealth` inside virtualized Chromium sessions [20, 267, 1081].
* **Forensic Reason for Rejection:**
  1. **TLS Handshake Discrepancies:** While stealth plugins attempt to mask client-side Javascript variables, they do not touch the network transport handshake. The Web Application Firewall (WAF) compares the client's JA3/JA4 TLS handshake signatures with the declared User-Agent [25, 265]. A vanilla Playwright container shaking hands like a NodeJS client while claiming to be Chrome is instantly detected [25, 265].
  2. **Inconsistent WebGL & AudioContexts:** Simulated WebGL and AudioContext hashes injected by generic stealth plugins often contain mathematical inconsistencies [267, 1083]. LinkedIn's APFC "Lie Detection" script (`getHasLiedOS`, `getHasLiedResolution`) detects these mismatches, raising the session fraud score and invalidating the cookie [131, 280].

---

## 3. Extension-Based Page Interception (The "Expandi" Model)
* **The Method:** Injecting custom content scripts into the page context of a legitimate user browser, monkey-patching `XMLHttpRequest.prototype.send` or `window.fetch`, and hijacking Voyager API data as the user browses [143, 630].
* **Forensic Reason for Rejection:**
  1. **AED and Spectroscopy Vulnerability:** LinkedIn's active defensive modules actively hunt for these extensions [131, 285]. The AED scanner probes Chrome’s internal directories for exposed assets (e.g., `injected.js`), identifying the extension even if it is dormant [285, 287].
  2. **Monkey-Patch Detection:** Spectroscopy scans the entire DOM for any references to `chrome-extension://` paths, which content scripts regularly inject [287]. Furthermore, because the `send` method is wrapped, testing `Function.prototype.toString.call(XMLHttpRequest.prototype.send)` immediately returns the wrapper code instead of `"function send() { [native code] }"` [144, 634]. This is a trivial, 1-line check for LinkedIn’s JavaScript.

---

## 4. Telemetry Endpoint Blocklists (uBlock / declarativeNetRequest)
* **The Method:** Blocking outgoing network requests targeting `li/track`, `/platform-telemetry/li/apfcDf`, `/apfc/collect`, or HUMAN Security (`li.protechts.net`) using static JSON blocking rules in manifest V3 [150, 651].
* **Forensic Reason for Rejection:**
  1. **The Telemetry-Silence Anomaly:** Blocking telemetry while continuing to query Voyager API endpoints creates a highly distinct signature [150, 638]. A legitimate user browser *always* generates a parallel stream of tracking events as they interact with the page [133]. Querying profiles at a rate of 50/day with *zero* accompanying telemetry pings stands out instantly in server-side logs as a bot pattern [133, 154].
  2. **decoy Telemetry Endpoints:** LinkedIn can easily route telemetry to dynamically generated, session-specific endpoints [651]. If a blocker fails to block even one new endpoint, the telemetry silence is instantly broken and reported, exposing the bypass attempt [651].
