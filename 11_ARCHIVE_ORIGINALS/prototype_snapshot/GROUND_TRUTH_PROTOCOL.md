# Ground-Truth Data Quality Verification Protocol
**Role:** Lead Evaluation Scientist and Protocol Auditor  
**Status:** Approved Operational Protocol

---

## 1. Objectives
This protocol defines the step-by-step process for establishing human-verified **ground-truth** profiles. This baseline represents the absolute, uncompromised professional identity observable on LinkedIn's UI, acting as the mathematical control against which the programmatic, browser-less HTTPS extraction API is evaluated.

---

## 2. Phase-1: Session Configuration & Context Binding
Before executing human validation, the auditor must document the active session parameters to ensure the connections are controlled:
1. **Determine Connection Degree ($V$):** Document the connection degree between the observer account and the target profile $P$ ($V_1, V_2, V_3$, or $V_0$).
2. **Synchronize System Time ($T$):** Record the exact start time of the verification pass.
3. **Capture Session Identifiers:** Securely capture the browser session context (`User-Agent` and geolocation) without storing plain-text credentials.

---

## 3. Phase-2: UI Auditing Checksheet (The Human Verification Step)
The auditor must systematically navigate the target profile in a controlled, manual browser window and extract raw, un-transformed facts. The auditor must record:

### Section A: Identity & Headline
- [ ] Record the exact spelling of Name and Surname as rendered on the profile card.
- [ ] Copy the exact text string of the Headline.
- [ ] Copy the exact text string of the Location name.

### Section B: Images
- [ ] Verify if a Profile Image is visible. Copy its raw rendering URL.
- [ ] Verify if a Background Banner Image is visible. Copy its raw rendering URL.

### Section C: About Section
- [ ] Click "See more" on the summary block.
- [ ] Copy the complete raw string, including all spaces, indentation, and trailing carriage returns.

### Section D: Career Experience
- [ ] Expand the entire experience timeline.
- [ ] Count and list the total number of distinct corporate entities.
- [ ] Detect **grouped promotions**: Check if multiple roles are nested under a single corporate logo.
- [ ] For each role, record:
  - Exact Role Title.
  - Company Name.
  - Exact start and end dates (Month + Year).
  - Description text (expand "See more" for each position).

### Section E: Education History
- [ ] Expand the education block.
- [ ] Count total education records.
- [ ] Record: School Name, Degree, Field of Study, and dates.

### Section F: Skills & Certifications
- [ ] Click "Show all skills" and document the total count.
- [ ] Record each skill and its exact endorsement count.
- [ ] Click "Show all certifications" and record the Name, Issuing Authority, License Number, and Date of each entry.

---

## 4. Phase-3: Technical Payload Correlation (DevTools)
To bridge the gap between visual rendering and raw data payload, the protocol requires capturing the underlying HTTP communication during manual audit:
1. Open Chrome DevTools (`Inspect -> Network` tab) before loading the profile [84].
2. Filter requests by `/voyager/api/graphql` or `/voyager/api/identity/` [84, 402].
3. Locate the response body mapping to the core profile view [83, 1000].
4. Save the raw JSON payload to `/workspace/scratch/raw_network_fixtures/{slug}_raw.json`.
5. Isolate relational company, school, and member URNs from the `included` arrays [19, 1000].

---

## 5. Phase-4: Freezing the Ground-Truth Baseline
The verified UI facts and network payload elements must be combined and frozen into a normalized Ground Truth document adhering to our strict target schema. This document must be saved as:
`/workspace/scratch/ground_truth/{fixture_id}_ground_truth.json`
