# Contributing & Pull Request Guide

## Making a Pull Request

### 1. Branch from `develop` in this repository
Analytics team members should push feature branches directly to `oppia/analytics-data-platform` rather than from a personal fork:

```bash
git checkout develop
git pull origin develop
git checkout -b feature/<short-description>
```

> **Why upstream branches instead of forks?** GitHub withholds cloud credentials from fork-origin PRs for security. PRs from forks will still run offline linting and `dbt parse`, but **BigQuery Build & Test** will fail and block merging until the PR is reopened from a branch in `oppia/analytics-data-platform`.

### 2. Run checks locally before pushing
Install dev dependencies once (`pip install -r requirements-dev.txt`), then verify your changes:

```bash
# Offline linting, Python unit tests (100% coverage), dbt parsing, and dbt coverage checks
yamllint --strict .
ruff check .
ruff format --check .
coverage run -m unittest discover -s scripts -v && coverage report
sqlfluff lint models/ tests/
dbt parse
python3 scripts/check_dbt_coverage.py

# Full build and data tests in your personal oppia-analytics-test sandbox
dbt build --target dev
```

For SQL conventions, folder placement, and partitioning/clustering rules, see [models/README.md](models/README.md).

#### Testing requirements (enforced in CI)
- **All models:** Must have a `description` and at least one `data_tests` entry in `schema.yml`.
- **`intermediate/` and `marts/` models:** Must also include at least one native dbt `unit_tests:` entry in `schema.yml` to verify transformation logic against mocked rows (use `format: sql` if inputs contain BigQuery `STRUCT`/`ARRAY` columns; trivial passthrough models can opt out with `config: {meta: {unit_test_exempt: true}}`). Example:
  ```yaml
  unit_tests:
    - name: test_fct_lesson_completions_dedup
      model: fct_lesson_completions
      given:
        - input: ref('stg_web_analytics__events')
          rows:
            - {user_pseudo_id: 'u1', event_name: 'lesson_complete', event_date: '20261101'}
      expect:
        rows:
          - {user_pseudo_id: 'u1', completion_count: 1}
  ```
- **Custom macros (`macros/`):** Must be exercised by at least one model or test in `tests/`.
- **Sources (`src_*.yml`):** Must include a `description`, `config.loaded_at_field`, and `config.freshness` (or `config: {meta: {freshness_exempt: true}}` for static lookup tables).

### 3. Open the PR targeting `develop`
- Keep PRs focused on a single logical change and link the relevant GitHub issue.
- Include a brief summary of what changed, which models/tests were added or updated, and any expected schema or metric impact.
- Never commit `profiles.yml`, service account JSON keys, or `target/` artifacts.
- Wait for both **Static Checks (Lint & dbt Parse)** and **BigQuery Build & Test** to pass, then request review from an approved reviewer.

---

## Reviewing a Pull Request

Reviewers should verify the following before approving and merging into `develop`:

- **CI checks:** Confirm both **Static Checks (Lint & dbt Parse)** and **BigQuery Build & Test** are green. (Fork PRs intentionally fail **BigQuery Build & Test**; ask the author to reopen the PR from an upstream branch in `oppia/analytics-data-platform`.)
- **SQL & dbt hygiene:**
  - Models use `{{ ref() }}` / `{{ source() }}` (no hardcoded project or dataset names).
  - Final `SELECT` lists columns explicitly (no `SELECT *` in final projections) and queries are idempotent.
  - High-volume intermediate and mart tables define `partition_by` and `cluster_by` configs.
- **Documentation & tests:** New or changed models have clear descriptions, `data_tests` (`not_null`, `unique`, etc.) on critical keys, and meaningful `unit_tests` for `intermediate/` and `marts/` logic (verify any `unit_test_exempt` or `freshness_exempt` opt-outs are genuinely justified).
- **Safety & scope:** No credentials or local config files committed, and any changes to `.github/workflows/` or `dbt_project.yml` are intentional and carefully reviewed.

---

## CI/CD & GCP Authentication Reference

CI uses **GCP Workload Identity Federation (WIF)** via `google-github-actions/auth@v3` — no static service account JSON keys are stored in GitHub. Test and production credentials are strictly separated:

| Workflow | GCP Project | GitHub Secrets | GCP IAM Attribute Condition |
| :--- | :--- | :--- | :--- |
| [pr_validation.yml](.github/workflows/pr_validation.yml) | `oppia-analytics-test` | `GCP_TEST_WIF_PROVIDER`, `GCP_TEST_SERVICE_ACCOUNT` | `assertion.repository == 'oppia/analytics-data-platform'` |
| [weekly_run.yml](.github/workflows/weekly_run.yml) | `oppia-analytics-prod` | `GCP_PROD_WIF_PROVIDER`, `GCP_PROD_SERVICE_ACCOUNT` | `assertion.repository == 'oppia/analytics-data-platform' && assertion.ref == 'refs/heads/develop'` |

Because the production WIF provider restricts `assertion.ref` to `refs/heads/develop`, PR branches cannot authenticate to `oppia-analytics-prod` even at the GCP IAM layer.

### Repo Guardrails (GitHub Settings)
Protect `develop` with a branch protection rule / ruleset that:
1. Blocks direct pushes and force-pushes to `develop`.
2. Requires pull request approval from approved reviewers (`CODEOWNERS`).
3. Requires the **Static Checks (Lint & dbt Parse)** and **BigQuery Build & Test** status checks to pass before merging.
4. Enables *"Automatically delete head branches"* so merged feature branches stay cleaned up.
