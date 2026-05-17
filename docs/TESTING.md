# Testing Plan

## Tests should not require live Reddit credentials

Use mocked objects or sample JSON fixtures.

## Minimum tests

```text
filters identify relevant posts
filters ignore irrelevant posts
tool mention extraction works
SQLite schema initializes
post dedupe works
opportunity score is calculated correctly
report generator writes files
```

## Run

```bash
pytest
ruff check .
```
