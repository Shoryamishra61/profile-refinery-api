# Definition of Done

## Build
- [ ] fresh clone installs
- [ ] no path hacks
- [ ] fixtures/schema/registry shipped

## Tross pivot
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
- [ ] API key required
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
