# Existing Benchmark Repair

Legacy defect:
```python
ground_truth = json.loads(json.dumps(extracted))
```
This makes actual == expected.

Replace with independent files:
```text
tests/fixtures/raw/*.json
tests/fixtures/expected/*.normalized.json
```
Then `actual = pipeline(raw)` vs `expected = load_expected()`.

Legacy 0.066s may be retained only as a local fixture pipeline timing sample, not headline/live performance.
