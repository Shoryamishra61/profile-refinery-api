# Tross LinkedIn Profile API — Master Engineering Handoff

This is the canonical build package for the **Tross LinkedIn Profile API hiring challenge**.

> Build a publicly hosted HTTPS API that accepts a LinkedIn profile URL and returns most profile-page information as structured JSON.

## Mandatory Tross clarification

The deployed LinkedIn solution must be **purely reverse engineered, directly hit LinkedIn endpoints, and not use a browser**.

Production therefore contains **no Selenium, Playwright, Puppeteer, Chromium, headless/headful browser worker, DOM scraper, screenshot extractor, or browser fallback**. Manual DevTools/HAR inspection is permitted only as a controlled research instrument on an account/profile you are authorized to inspect.

## Why this package exists

The uploaded corpus is unusually strong in research breadth, protocol thinking, schema design, failure taxonomy, and competitive analysis. But several generated documents describe mock/hypothetical behavior as if it were live-proven. This package preserves every original artifact verbatim under `11_ARCHIVE_ORIGINALS/` and places a stricter source-of-truth layer above it.

### Read first
1. `00_START_HERE/AGENTS.md`
2. `00_START_HERE/MASTER_AUDIT.md`
3. `01_PRODUCT_AND_REQUIREMENTS/REQUIREMENTS.md`
4. `01_PRODUCT_AND_REQUIREMENTS/SRS.md`
5. `02_RESEARCH_AND_REVERSE_ENGINEERING/REVERSE_ENGINEERING_PROTOCOL.md`
6. `03_ARCHITECTURE_AND_DESIGN/SYSTEM_DESIGN.md`
7. `06_TESTING_AND_EVALUATION/TEST_PLAN.md`
8. `07_IMPLEMENTATION_AND_RELEASE/IMPLEMENTATION_PLAN.md`
9. `07_IMPLEMENTATION_AND_RELEASE/DEFINITION_OF_DONE.md`
10. `09_AGENT_PROMPTS/MASTER_BUILD_AGENT_PROMPT.md`

## Engineering thesis

The winning submission should prove:
- direct endpoint acquisition at runtime;
- zero runtime browser dependencies;
- current, evidence-backed operation registry;
- stable nested public schema over volatile upstream representations;
- explicit partial/unavailable states and provenance;
- independent fixture and live benchmarks;
- secure secret isolation;
- public HTTPS reproducibility.

Do **not** optimize for source-count, anti-detect tricks, or marketing-style performance claims. Optimize for executable evidence.
