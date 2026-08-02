# Verification gate

This research baseline must remain a draft unless the current pull-request merge context passes the repository's complete GitHub Actions workflow.

Required evidence:

- pre-commit passes without modifying files;
- the full parent test suite passes on Python 3.10;
- the full parent test suite passes on Python 3.13;
- `tests/test_metamorphosis.py` is collected within that suite;
- the analytic runner imports from the installed `the_well` package;
- the analytic runner and tests remain provider-free and deterministic;
- no result is described as evidence of three-dimensional global regularity.

Local focused commands:

```bash
python -m the_well.research.metamorphosis.run_analytic_baseline
pytest tests/test_metamorphosis.py
```

## Verified evidence

On 2 August 2026, GitHub Actions run 50 passed after the executable modules were moved into the installed `the_well.research.metamorphosis` package and duplicate top-level Python modules were removed:

- pre-commit: passed;
- full parent suite on Python 3.10: passed;
- full parent suite on Python 3.13: passed.

This evidence records software behaviour for that exact branch state. Any later code change or changed merge context must pass the gate again.

A green software-verification run establishes only that the implemented equations, diagnostics, fixtures and packaging behave as tested. It does not establish the proposed redistribution hypothesis, physical effectiveness, or a Navier–Stokes proof.
