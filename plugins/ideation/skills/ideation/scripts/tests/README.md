# Ideation CLI tests

Stdlib-only tests for `ideation_db.py` and `operator_meta.py`.

Run from repo root:

```
python -m unittest discover -s plugins/ideation/skills/ideation/scripts/tests -v
```

Each test is self-contained — creates a tempdir, initialises a logbook under it, runs assertions, tears the tempdir down.
