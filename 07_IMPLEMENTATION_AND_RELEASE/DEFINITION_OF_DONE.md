# Definition of Done

## Build

- [ ] fresh clone installs
- [ ] no path hacks
- [ ] fixtures/schema/registry shipped

## Profile Refinery pivot

- [ ] direct LinkedIn HTTP runtime
- [ ] no Selenium/Playwright/Puppeteer/Chromium/DOM/browser fallback

## Live functionality

- [ ] URL -> live core fields on permitted profile
- [ ] experience
- [ ] education
- [ ] skills
- [ ] certifications
- [ ] languages
- [ ] image when available
- [ ] partial response behavior

## Quality

- [ ] independent fixture benchmark
- [ ] independent controlled-live benchmark with sample sizes
- [ ] no circular ground truth
- [ ] schema fail-closed
- [ ] operation drift test

## Security

- [ ] no secrets in git/logs
- [x] Public request-scoped route needs no product key; operator routes remain protected
- [ ] fixed outbound host
- [ ] SSRF/redirect tests
- [ ] challenge fail-closed

## Deployment/docs

- [ ] HTTPS URL
- [ ] health/readiness
- [ ] evaluator request succeeds
- [ ] restart works
- [ ] README fresh-clone reproduction
- [ ] API/architecture/method/results/limitations/privacy-platform notes

Only then mark the challenge PASS.

## Execution evaluation — 2026-08-27

The detailed, evidence-linked evaluation is in root `JUDGE_AUDIT.md`. Build, offline contracts, fixture benchmark, security, partial behavior, and documentation gates pass. Current live operations, controlled-live benchmarks, and public HTTPS deployment are externally blocked, so the challenge is not marked PASS.
