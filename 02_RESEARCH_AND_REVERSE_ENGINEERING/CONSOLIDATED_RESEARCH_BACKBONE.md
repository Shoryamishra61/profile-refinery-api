# LinkedIn Profile API — Consolidated Research Backbone

## Audit status

This report treats the 14 supplied research reports as one corpus and accepts the user's stated **168 verified sources** as the raw corpus size. It does **not** pad that number.

A source-manifest audit found an important reproducibility gap: the supplied reports contain **108 unique explicit URLs**, not a single canonical 168-row bibliography. The remaining source count is represented through named references, duplicated records, or prose citations rather than a complete row-level URL manifest. Because the governing quality rule is “never fabricate,” this report does **not** invent the missing manifest entries merely to recreate 168 rows.

Instead, the deliverables are:

1. a decision-grade consolidated research report;
2. a canonical high-value inventory of **72** sources that should actually drive the assignment;
3. the **108-URL raw explicit-link manifest** extracted from all 14 reports, preserving traceability;
4. a links-only master list for the canonical inventory.

The high-value bibliography deliberately excludes low-marginal-value SEO pages, unsupported restriction-rate claims, cookie cookbooks, anti-detect recipes, and endpoint/solver guides whose primary value is operational evasion rather than research.

---

# 1. Executive Research Summary

## 1.1 The assignment is a profile-observability problem before it is a scraper problem

The semantic target is not “the LinkedIn profile.” The target is a **viewer-conditioned observation of a profile at a specific time**.

The same URL can yield materially different observable fields depending on:

- logged-out versus authenticated state;
- member-controlled public/off-LinkedIn visibility;
- connection degree;
- product context;
- account/partner entitlement;
- upstream rendering state;
- partial failures and lazy loading.

Therefore the most important schema principle is:

> **absence, hiddenness, inaccessibility, not-loaded, stale, and extraction-failed are different states.**

A response contract that collapses all of these to `null` can look complete while being epistemically wrong.

## 1.2 The sanctioned API path does not satisfy arbitrary URL → rich third-party profile retrieval

Current official documentation supports authenticated/self or consented-member access, with additional fields available only under specific programs/tiers. The historical `r_fullprofile` permission is closed. `/identityMe` is a consented 3-legged OAuth flow for the member authorizing access; it is not a generic paste-a-profile-URL endpoint.

This resolves the first major decision: **the official path is an essential baseline, not a complete implementation of the assignment as written.**

## 1.3 The assignment's credentialed/public-hosted interpretation is materially riskier than “public web scraping”

LinkedIn's current User Agreement, Prohibited Software help, Automated Activity guidance and crawling terms must be treated as P0 constraints. The corpus's early “hiQ made LinkedIn scraping legal” phrasing is not supportable.

A defensible legal-layer reading separates:

- **CFAA/computer-access doctrine**;
- **contract/platform authorization**;
- **privacy/data-protection law**;
- other possible claims such as misappropriation, fraud or trademark theories.

The 2022 Ninth Circuit hiQ opinion is important, but it addressed **public, gates-down** access at a preliminary-injunction posture. The later N.D. California summary-judgment record found breach of LinkedIn's User Agreement, and the case ended in a consent judgment/permanent injunction. Meta v. Bright Data is similarly non-transferable: the favorable contract analysis turned materially on logged-off/public collection under Meta's contract facts.

## 1.4 Privacy is not cured by the word “public”

The strongest directly analogous regulator record is KASPR. CNIL fined it €240,000 after it collected LinkedIn contact details including data whose visibility users had restricted. In March 2026, CNIL closed the order after KASPR demonstrated compliance measures including deleting its database and ceasing all LinkedIn collection.

The 2024 joint statement from 16 privacy authorities also states that publicly accessible personal information generally remains subject to privacy/data-protection law. EDPB Guidelines 03/2026 are current but still draft/consultation guidance and must be labeled accordingly.

For India, use the DPDP Act, official commencement notification, and 2025 Rules directly. Do not substitute vendor summaries or pretend the Data Protection Board has already resolved every question about publicly posted professional data.

## 1.5 PhantomBuster is useful prior art, but only when its own documentation is read precisely

Current July 2026 first-party material establishes two materially different products:

**Profile Scraper**

- LinkedIn session-backed;
- vendor says it extracts via API calls and does not register a profile visit;
- current support page lists a profile image URL;
- past two jobs/experiences only;
- no endorsements or screenshots;
- optional email/company enrichment;
- vendor claims up to 1,500 profiles/day.

**Profile Visitor**

- explicitly visits profiles;
- richer output;
- includes endorsements, profile pictures and full-profile screenshots;
- materially different footprint.

Two corrections follow:

1. “PhantomBuster has no profile-image URL” is stale against the current support page.
2. “1,500/day is safe” is **PhantomBuster's vendor guidance**, not a LinkedIn-published or independently validated restriction threshold.

PhantomBuster is therefore prior art for **schema, product partitioning and operating tradeoffs**, not a legality warrant and not a source of ground-truth ban probabilities.

## 1.6 Proxycurl is high-value negative evidence

Proxycurl's founder says LinkedIn sued in January 2025 and Proxycurl shut down on 4 July 2025; he describes it as roughly a $10M revenue business. Treat the revenue number as self-reported, but treat the shutdown/litigation sequence as strong negative commercial evidence corroborated by LinkedIn and the federal docket.

This is more relevant than dozens of “is scraping legal?” SEO posts.

## 1.7 Exact LinkedIn restriction thresholds remain unverified

The corpus contains many numbers for “safe actions/day,” account bans, proxy success rates and challenge thresholds. They disagree, are often vendor marketing, and are not supported by LinkedIn's official rate-limit documentation.

Therefore:

- do not cite an exact ban probability;
- do not claim a universal safe daily threshold;
- do not use proxy-vendor success percentages as LinkedIn-specific performance evidence.

This uncertainty is itself an experimental finding: the operating envelope is account/context/mechanism-dependent and cannot be responsibly inferred from generic vendor blogs.

## 1.8 There is no satisfactory public gold dataset for this assignment

SWDE, WebSRC, WebArena, BrowserGym, WorkArena and WebVoyager are useful methodological benchmarks, but they do not provide:

> current LinkedIn profiles × controlled profile contents × controlled visibility settings × viewer relationships × field-level ground truth.

Using leaked/scraped profile dumps as “ground truth” would reproduce the same provenance/terms problem and would not establish what was actually observable to a given viewer.

The correct benchmark is **generated evidence**: a small, consented fixture pack with explicit view states and timestamped ground truth.

## 1.9 ML/LLMs are not justified by the current evidence

The extraction literature predates modern LLMs by decades: wrapper induction, RoadRunner, partial tree alignment, FiVaTech, DOM record mining, schema inference and robust parsing already address much of the underlying problem.

Web-agent benchmarks also remain far from human reliability. Entity-matching literature shows structured regimes in which deep learning does not automatically beat strong classical methods.

The correct rule is:

> **No ML component earns a place until a measured deterministic failure mode establishes a need.**

If learned extraction is later evaluated, it must be compared against deterministic baselines with hallucination/grounding tests and failure abstention.

## 1.10 The highest-value “better than PhantomBuster” dimension is not more aggressive access

A student system is unlikely to outcompete a mature vendor on session fleets or enrichment marketplaces. The defensible advantage is **contract quality**:

- explicit provenance;
- field-level availability reasons;
- schema versioning;
- consented evaluation;
- honest partial success;
- no email harvesting by default;
- safe public-API boundary;
- reproducible fixtures;
- measured field recall;
- no secrets in the repository.

This is the direction that can improve technical credibility without inheriting the least defensible parts of the commercial analogue.

---

# 2. Challenge Research Map

```text
CHALLENGE
LinkedIn profile URL -> structured JSON over HTTPS
|
+-- A. Semantic target
|   +-- What counts as "most information"?
|   +-- Which sections exist?
|   +-- Whose view is ground truth?
|   +-- What is observable vs hidden vs absent?
|
+-- B. Sanctioned access baseline
|   +-- Profile API
|   +-- /identityMe
|   +-- partner/tier boundaries
|   +-- storage/use restrictions
|
+-- C. Viewer-conditioned observability
|   +-- logged-out
|   +-- authenticated unrelated member
|   +-- consenting connected member
|   +-- public/off-LinkedIn settings
|
+-- D. Acquisition-method families
|   +-- official consented OAuth
|   +-- public page representation
|   +-- rendered browser observation
|   +-- unsupported structured web-client representations
|   +-- third-party commercial enrichment
|   +-- hybrid/fallback
|
+-- E. Extraction + normalization
|   +-- identity
|   +-- experience / education
|   +-- skills / certifications / languages
|   +-- media
|   +-- dates / locales
|   +-- stable identity across vanity URL changes
|
+-- F. Stable outward contract
|   +-- JSON Schema
|   +-- provenance
|   +-- availability_reason
|   +-- partial success
|   +-- RFC 9457 errors
|   +-- versioning
|
+-- G. Reliability / drift
|   +-- upstream representation change
|   +-- partial failure
|   +-- retry budgets
|   +-- cache/freshness semantics
|   +-- regression fixtures
|
+-- H. Security / abuse
|   +-- URL validation / SSRF
|   +-- caller authentication
|   +-- quotas
|   +-- secret management
|   +-- PII-safe observability
|
+-- I. Contract / privacy / enforcement
|   +-- LinkedIn terms/help/crawling terms
|   +-- hiQ / Van Buren
|   +-- Meta v Bright Data
|   +-- Nubela / Proxycurl
|   +-- GDPR / CNIL / EDPB
|   +-- India DPDP
|
+-- J. Evaluation
    +-- consented fixture pack
    +-- visibility matrix
    +-- field-level precision / recall
    +-- missingness classification accuracy
    +-- latency / freshness
    +-- drift / failure recovery
```

---

# 3. Consolidated Evidence Map

| Component | Best-supported claim | Evidence class | Confidence | Best source cluster |
|---|---|---:|---:|---|
| Official access | Sanctioned access is consent/permission/tier constrained and does not equal arbitrary rich-profile URL lookup | Primary docs | Very high | Profile API, Full Profile Closed, /identityMe |
| Visibility | Profile observability varies with member settings and viewer state | Primary docs | Very high | Public Profile Visibility, Off-LinkedIn Visibility |
| Platform permission | LinkedIn explicitly prohibits scraping/copying profiles and unauthorized automation | Primary contract/help | Very high | User Agreement, Prohibited Software, Crawling Terms |
| CFAA | hiQ supports narrow public gates-down CFAA reasoning, not a general scraping license | Court opinions | Very high | Van Buren, hiQ II |
| Contract | Later hiQ proceedings materially undercut “hiQ = legal authorization” simplification | Court opinion/docket | Very high | N.D. Cal. 2022, final docket |
| Bright Data transfer | Meta v Bright Data is fact/contract specific and emphasizes logged-off/public collection | Court order | High | N.D. Cal. Jan. 2024 order |
| Commercial enforcement | Proxycurl/Nubela demonstrates existential enforcement risk in this product category | Court docket + both parties' statements | Very high | Nubela docket, LinkedIn news, Proxycurl shutdown |
| Privacy | Public availability does not itself resolve lawful-basis/transparency/retention duties | Regulators | Very high | CNIL KASPR, joint statement |
| PhantomBuster coverage | Fast scraper is intentionally partial; visitor is richer | First-party product docs | Very high | PB Scraper + Visitor |
| PB operating limits | 1,500/day is vendor guidance, not independent LinkedIn evidence | Vendor claim | Moderate as “PB says this”; low as universal threshold | PB support |
| Exact restriction rates | No defensible universal numeric threshold found | Negative evidence | High | Contradictory practitioner corpus + official rate-limit docs |
| Parser drift | Web extraction/wrapper maintenance is a known long-running problem | Peer-reviewed/foundational | High | Kushmerick, RoadRunner, Laender, FiVaTech |
| LLM need | No current evidence makes LLMs a required default extractor | Negative comparative evidence | High | Web-agent benchmarks, entity-matching evidence |
| Benchmark | No public LinkedIn-specific visibility-conditioned gold set was found | Corpus-wide negative finding | High | benchmark search + existing web datasets |
| Schema | Typed partial results + provenance are technically justified regardless of acquisition method | Standards + problem structure | Very high | JSON Schema, RFC 9457, PROV-DM |
| Public API security | A URL-input endpoint requires SSRF controls, caller gating and quotas | Security standards | Very high | OWASP SSRF + API Top 10 + Secrets |

---

# 4. Cross-Report Consensus

The reports converge strongly on these points:

1. The sanctioned LinkedIn API surface is narrower than the assignment's arbitrary-profile objective.
2. The page should be studied as a distributed data/view system, not only as HTML.
3. PhantomBuster is the most relevant named prior art.
4. Profile completeness is visibility-dependent.
5. Unsupported interfaces and page representations are volatile.
6. Secrets/session material must never be committed to the public repository.
7. A robust outward schema matters independently of the extraction mechanism.
8. Exact ban/rate claims are weakly evidenced.
9. Legal analysis must separate CFAA from contract and privacy.
10. A real evaluation set is missing.
11. More generic scraper SEO research has low marginal value.
12. ML is optional and currently unsupported as a default.

---

# 5. Disagreements and Resolutions

## D1. “hiQ made scraping legal”

**Resolution:** Reject. The 2022 Ninth Circuit ruling is narrow, public/gates-down and preliminary-injunction focused. Later district-court contract findings and the consent judgment matter.

## D2. “Meta v Bright Data means credentials are fine”

**Resolution:** Reject. Different platform, terms and login state. The court's logged-off/public distinction is precisely why this is not a transferable credentialed-access warrant.

## D3. “PhantomBuster extracts no profile image”

**Resolution:** Stale/contradicted. The current July 2026 support article lists `linkedinProfileImageUrl`. Preserve the documentation contradiction as a versioning lesson.

## D4. “PhantomBuster = full profile”

**Resolution:** Reject as a generic statement. Its current Profile Scraper explicitly limits history and omits endorsements/screenshots; the Visitor product is richer.

## D5. “1,500/day is a safe LinkedIn limit”

**Resolution:** Downgrade. Accurate only as “PhantomBuster currently recommends/claims this for its product.” It is not a LinkedIn-published limit and not independently established.

## D6. “Residential proxies are 99%+ successful”

**Resolution:** Do not use as LinkedIn-specific evidence. Vendor marketing about protected websites does not establish this assignment's success rate.

## D7. “LLM extraction self-heals schema changes”

**Resolution:** Unsupported. Treat as a hypothesis requiring benchmark evidence, not as architecture.

## D8. “publicly available = privacy-exempt”

**Resolution:** Reject as a cross-jurisdictional statement. Statutory treatment differs; GDPR/privacy regulators explicitly warn that public accessibility does not remove data-protection obligations.

---

# 6. Research Gaps That Still Matter

## P0 — Generate evidence, do not search more generally

### G1. Assignment field-recall / visibility matrix

For each required field, measure whether it is observable under each consented viewer state.

### G2. Ground-truth definition

Define “most information” as:
`fields visible to viewer V at timestamp T`, not “whatever one extractor returned.”

### G3. Missingness ontology

At minimum distinguish:

- `not_provided`
- `not_visible_to_viewer`
- `not_available_in_surface`
- `not_loaded`
- `extraction_failed`
- `stale_or_expired`
- `unknown`

### G4. Evaluator incentive/rubric

Determine whether a ToS-honest partial implementation is rewarded more than a brittle cookie clone. This cannot be inferred from scraper marketing.

### G5. Independent PhantomBuster black-box comparison

If lawful/appropriate, compare PB output to the same consented ground truth. Do **not** assume its “no visit” claim proves underlying mechanism.

### G6. Image URL lifetime

Measure signed/ephemeral image behavior over time rather than assuming stable media URLs.

### G7. India DPDP application

Track official Board/government interpretation as it develops; avoid inventing settled doctrine for publicly posted professional data.

---

# 7. Recommended Research Sequence

## Stage 1 — Lock the rules of the problem

Study:

- User Agreement
- Prohibited Software
- Profile API
- Full Profile Closed
- /identityMe
- public/off-LinkedIn visibility
- hiQ / Van Buren
- CNIL KASPR

**Output:** one-page legal/platform layer memo separating contract, CFAA and privacy.

## Stage 2 — Define the semantic contract before implementation

Create the complete assignment field taxonomy and explicit `availability_reason` model.

**Output:** JSON Schema draft + source/provenance fields + partial-success semantics.

## Stage 3 — Build the consented fixture pack

Use the developer's own profile plus volunteers who explicitly consent.

Capture:

- controlled section presence/absence;
- visibility settings;
- viewer relationship state;
- timestamped human ground truth.

**Output:** evaluation corpus, not production data.

## Stage 4 — Measure acquisition families

Compare methods at the level of **observable field recall**, not sophistication.

Candidate families:

- sanctioned OAuth/self baseline;
- logged-out public representation;
- consented rendered-browser observation;
- any other method only if permitted and justified.

Do not optimize bypass behavior. The research question is what each surface can faithfully observe.

## Stage 5 — Normalize and prove provenance

Map each returned field to:

- source surface;
- observation timestamp;
- raw-to-normalized transformation;
- confidence/availability state.

## Stage 6 — Drift and regression testing

Replay fixtures across upstream changes. Track:

- field disappearance;
- section-layout changes;
- media expiry;
- schema change;
- partial failure.

## Stage 7 — Only then choose service architecture

Select sync/async behavior, caching, worker model and deployment from measured latency/failure data.

This order deliberately prevents a premature “Voyager + Redis + FastAPI” answer.

## Stage 8 — Evaluate optional learned methods

Only if deterministic extraction fails measurably:

- define the failure slice;
- add a learned baseline;
- require grounding to source content;
- measure hallucination/omission;
- include abstention;
- compare cost and latency.

---

# 8. Experimental / Evaluation Plan

## 8.1 Fixture design

Minimum useful matrix:

| Dimension | Suggested states |
|---|---|
| Profile completeness | sparse / medium / rich |
| Required sections | each required section present in at least several fixtures |
| Public visibility | high / restricted |
| Viewer | logged-out / authenticated unrelated / consenting connected |
| Locale | English + at least one non-English profile |
| Employment | single / multiple / grouped roles |
| Education | none / one / multiple |
| Media | photo present / absent |
| Temporal state | initial + later recapture |

## 8.2 Ground truth

Human-label the fields actually visible in the corresponding consented view. Store:

- timestamp;
- viewer-state label;
- field value;
- section;
- visibility state;
- optional screenshot/reference artifact only where consent permits.

## 8.3 Core metrics

### Field precision

Of returned fields, how many match ground truth?

### Observable-field recall

Of fields visible to that viewer, how many were returned?

### Availability-class accuracy

Did the system correctly distinguish hidden/unavailable/failed rather than returning an undifferentiated null?

### Section coverage

Experience, education, skills, certifications, languages, about, media.

### Freshness

Difference between observed source state and returned cached state.

### Failure transparency

Fraction of failures mapped to a correct typed error/partial-response reason.

### Latency

P50/P95 by acquisition family.

### Drift recovery

Regression success after a deliberate fixture/schema change.

## 8.4 Baselines

1. Official consented profile API/self route where applicable.
2. Logged-out public representation.
3. Deterministic rendered-page extraction against consented fixtures.
4. Commercial product output only as black-box prior art where permitted.
5. Learned/LLM extraction only after a deterministic failure slice exists.

## 8.5 Required ablations

- provenance metadata on/off;
- typed missingness vs null-only;
- cache on/off;
- deterministic parser vs learned fallback, if a learned fallback is introduced;
- field-level versus whole-profile success criteria.

---

# 9. Best-Supported Solution Directions — without prematurely choosing architecture

The evidence supports these **design principles**, not a specific scraping stack:

1. **Visibility-aware contract**
2. **Partial results are first-class**
3. **Field-level provenance**
4. **Consent-based evaluation**
5. **No email enrichment by default**
6. **No hidden “full profile” claim**
7. **Caller authentication and quotas**
8. **Strict URL allowlisting / SSRF prevention**
9. **Secrets outside repo with rotation**
10. **Golden fixtures + drift detection**
11. **Acquisition method abstracted from normalization**
12. **ML only behind measured need**
13. **Current legal/platform constraints documented in README**
14. **Vendor claims labeled as vendor claims**
15. **No unverified restriction-rate numbers**

---

# 10. Adversarial Reviewer Verdict

## What would cause rejection

- Claiming hiQ generally legalized LinkedIn scraping.
- Treating a personal session cookie as a harmless API key.
- Publishing credential-handling or bypass recipes as the “research contribution.”
- Citing a universal “safe profiles/day” number.
- Evaluating against scraped dumps rather than consented ground truth.
- Claiming “full profile” without defining viewer state.
- Returning `null` for all forms of non-observability.
- Using an LLM because it looks research-heavy.
- Calling a vendor's success percentage an empirical LinkedIn benchmark.
- Designing the entire queue/proxy/cache stack before measuring the semantic target.

## What would signal strong judgment

- A one-page legal-layer memo with distinct CFAA/contract/privacy columns.
- A consented visibility matrix.
- An explicit field-recall table.
- A stable schema with provenance and `unavailable_reason`.
- A current PhantomBuster comparison that preserves its own limitations.
- A README that states exactly what the system does **not** claim.
- A reproducible evaluation harness.
- Evidence-driven architecture after the experiments.

---

# 11. Priority Reading Order

## P0 — read first

1. LinkedIn User Agreement
2. LinkedIn Prohibited Software and Extensions
3. LinkedIn Profile API
4. Full Profile Fields (Closed)
5. `/identityMe` + authentication docs
6. LinkedIn public/off-LinkedIn visibility docs
7. hiQ II (9th Cir. 2022)
8. N.D. Cal. hiQ summary judgment + final docket
9. Meta v Bright Data summary judgment
10. LinkedIn v Nubela docket + Proxycurl shutdown
11. CNIL KASPR 2024 + 2026 closure
12. 2024 joint regulator scraping statement
13. PhantomBuster Profile Scraper support article
14. PhantomBuster Profile Visitor
15. JSON Schema + RFC 9457 + PROV-DM
16. OWASP API Top 10 + SSRF + secrets management
17. Wang & Strong on data quality
18. Little & Rubin on missing data

## P1 — research foundations

- LinkedIn Engineering Profile/GraphQL/Rest.li material
- Kushmerick
- Laender survey
- RoadRunner
- Mining Data Records
- Partial Tree Alignment
- FiVaTech
- Discoverer
- Browser Fingerprinting survey
- WebSRC
- WebArena
- WebVoyager
- BrowserGym / WorkArena
- entity-resolution foundations

---

# 12. Stopping Rule

General web search is now lower value than measurement.

Stop searching when:

- a claim is already supported by primary platform/legal/regulatory evidence;
- new results only repeat vendor/SEO summaries;
- numeric restriction claims lack independent data;
- operational anti-detect material adds bypass detail rather than decision value.

Resume external research only for a **specific unresolved question**, such as:

- a new LinkedIn policy/API release;
- a new court/regulator decision;
- a concrete DPDP Board interpretation;
- a newly published benchmark directly relevant to viewer-conditioned profile extraction.

The next high-value work is **generated evidence**:

1. the consented visibility/field-recall matrix;
2. the legal-layer memo;
3. the schema/missingness contract;
4. the reproducible evaluation harness.

That is the evidence base that should precede any architecture choice.
