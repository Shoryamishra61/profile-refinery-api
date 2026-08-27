# Reverse Engineering Methodology & Protocol Exploration

This document outlines the process and research methodologies used to map LinkedIn's private API layer and replicate its behavior without web browser dependencies.

## 1. Controlled Session Protocol Inspection
To understand the private web application's communication pathways, a controlled browser session was established on an account we control. 
* **Tooling:** Chrome DevTools Network Panel and HAR (HTTP Archive) captures.
* **Observation:** When loading a profile, the single-page application (SPA) does not load a pre-rendered HTML document. Instead, it dispatches structured asynchronous queries to internal API endpoints.

## 2. Rest.li 2.0 Mapping & Grammar Analysis
LinkedIn's backend relies heavily on the Rest.li protocol, utilizing structured URL-encoded string syntax to convey complexes and lists in query strings.
* **Object Notation:** Represented as parenthesis-wrapped colon-separated pairs: `(key:value)`.
* **Collection Expansions:** Relational collections are recursively expanded using decoration masks (asterisk-tilde operations `*~`). For example: `(positions*~(companyName,title))` forces the server-side datastore to join position details with matching organization names before sending JSON back to the client.

## 3. GraphQL Pre-Registered Query Extraction
The modern web application routes queries through a consolidated POST gateway `/voyager/api/graphql`.
* **The Mechanism:** To prevent arbitrary query injection and minimize transport payload sizes, LinkedIn uses *Pre-Registered Queries*. The query structure is compiled into production JavaScript bundles as a static hash (`queryId`).
* **The Extraction:** Production Webpack chunks (e.g., `chunk.905.js`) were scraped under controlled research sessions to extract active queryIds mapping to `voyagerIdentityDashProfiles`. Replaying these queries with customized variables (`memberIdentity:jane-doe`) allows the API to directly fetch section payloads.
