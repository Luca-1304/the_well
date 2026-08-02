# Test evidence

Last verified: 2 August 2026

## Recorded source state

The standalone application files in this export are the same blobs exercised in `Luca-1304/the_well` before extraction.

## Fifteen-pass result

GitHub Actions run `30763264864` completed:

- NASA clean-package Linux: 15/15 consecutive cycles passed;
- NASA clean-package Windows: 15/15 consecutive cycles passed;
- failures: 0;
- retries used to construct either sequence: 0.

Each cycle performed:

1. source compilation;
2. all offline unit tests;
3. launcher syntax validation;
4. a fresh wheel build;
5. a new virtual environment;
6. installation from the wheel;
7. installed CLI and health validation;
8. packaged local-server startup using a deterministic fake upstream client;
9. dashboard retrieval;
10. APOD, near-Earth-object, DONKI and EONET local-route probes;
11. expected 400 and 404 response checks;
12. cleanup before the next cycle.

The normal application matrix also passed on Python 3.10, 3.11, 3.12 and 3.13.

## Claims boundary

This is deterministic software evidence for the tested source state and environments. It does not establish permanent absence of defects, NASA service availability, the validity of a disclosed credential, or completion of the separately credentialed live upstream soak.

The registered-key live soak remains pending until a newly rotated `NASA_API_KEY` is supplied through an encrypted secret and the manual live option is explicitly selected.
