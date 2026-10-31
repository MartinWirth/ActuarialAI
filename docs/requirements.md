# Business requirements and acceptance criteria

**BR-01** As an actuary, I want reproducible cumulative paid claims triangles to demonstrate reserving without exposing customer data.

**BR-02** As an actuary, I want volume-weighted age-to-age development factors and an ultimate/reserve estimate per origin period.

**BR-03** As an analyst, I want to inspect observed and completed triangles and origin-year reserves in a dashboard.

**BR-04** As an engineer, I want automated tests and CI on pushes and pull requests.

## Acceptance criteria

1. The same seed and origin-period count produce identical triangles.
2. The algorithm excludes origin periods without both observed development ages when estimating a factor.
3. A known three-year triangle returns factors 1.5 and 1.2, and total reserve 140.
4. Invalid non-monotonic triangles and zero denominator factors are rejected.
5. The dashboard runs with `streamlit run app.py`.
6. CI runs linting and unit tests on Python 3.10 and 3.12.
