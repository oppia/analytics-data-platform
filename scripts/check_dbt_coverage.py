#!/usr/bin/env python3
"""Offline dbt coverage and DAG hygiene checks against target/manifest.json.

Run after `dbt parse` (no BigQuery credentials required):
    python3 scripts/check_dbt_coverage.py

Enforces 100% coverage for:
  1. Model documentation (every model has a non-empty description in schema.yml).
  2. Model data tests (every model has at least one data_tests entry).
  3. Logic model unit tests (every intermediate/ and marts/ model has at least one
     dbt unit_tests entry, unless marked `config: {meta: {unit_test_exempt: true}}`).
  4. Column documentation (every column declared in schema.yml has a description).
  5. Custom macro coverage (every project macro is exercised by a model or test).
  6. Source documentation and freshness (every source table has a description and
     freshness config unless marked `config: {meta: {freshness_exempt: true}}`).
  7. Model layering (intermediate/ and marts/ must reference models via ref(),
     never raw source() directly; staging/ must not reference intermediate/ or marts/).
"""

from __future__ import annotations

import json
import pathlib
import sys

MANIFEST_PATH = pathlib.Path("target/manifest.json")
PROJECT_NAME = "oppia_analytics"
UNIT_TEST_REQUIRED_LAYERS = {"intermediate", "marts"}


def _layer_from_path(original_file_path: str) -> str | None:
    parts = pathlib.PurePosixPath(original_file_path.replace("\\", "/")).parts
    if len(parts) >= 2 and parts[0] == "models":
        return parts[1]
    return None


def _get_meta(node: dict) -> dict:
    return node.get("config", {}).get("meta") or node.get("meta") or {}


def check_manifest(
    manifest: dict, project_name: str = PROJECT_NAME
) -> tuple[dict[str, tuple[int, int]], list[str]]:
    """Validate dbt coverage and DAG layering rules against a parsed manifest dict."""
    nodes: dict = manifest.get("nodes", {})
    sources: dict = manifest.get("sources", {})
    macros: dict = manifest.get("macros", {})
    unit_tests: dict = manifest.get("unit_tests", {})

    project_models = {
        uid: node
        for uid, node in nodes.items()
        if node.get("resource_type") == "model"
        and node.get("package_name") == project_name
    }
    project_tests = {
        uid: node
        for uid, node in nodes.items()
        if node.get("resource_type") == "test"
        and node.get("package_name") == project_name
    }
    project_unit_tests = {
        uid: ut
        for uid, ut in unit_tests.items()
        if ut.get("package_name") == project_name
    }
    project_sources = {
        uid: src
        for uid, src in sources.items()
        if src.get("package_name") == project_name
    }
    project_macros = {
        uid: macro
        for uid, macro in macros.items()
        if macro.get("package_name") == project_name
    }

    # Build sets of models covered by data_tests and unit_tests.
    data_tested_models: set[str] = set()
    for test_node in project_tests.values():
        for dep in test_node.get("depends_on", {}).get("nodes", []):
            if dep in project_models:
                data_tested_models.add(dep)

    unit_tested_models: set[str] = set()
    models_by_name = {m.get("name"): uid for uid, m in project_models.items()}
    for ut in project_unit_tests.values():
        target_uid = models_by_name.get(ut.get("model"))
        if target_uid:
            unit_tested_models.add(target_uid)

    # Build set of macros transitively reachable from any project model or test.
    direct_macro_refs: set[str] = set()
    for node in (
        *project_models.values(),
        *project_tests.values(),
        *project_unit_tests.values(),
    ):
        direct_macro_refs.update(node.get("depends_on", {}).get("macros", []))

    covered_macros: set[str] = set()
    stack = [m for m in direct_macro_refs if m in project_macros]
    while stack:
        macro_uid = stack.pop()
        if macro_uid in covered_macros:
            continue
        covered_macros.add(macro_uid)
        for dep in project_macros[macro_uid].get("depends_on", {}).get("macros", []):
            if dep in project_macros and dep not in covered_macros:
                stack.append(dep)

    errors: list[str] = []

    # 1, 2, 3, 4, 7: Model docs, data tests, unit tests, column docs, and DAG layering.
    documented_models = 0
    unit_test_required_total = 0
    unit_test_required_covered = 0

    for uid, model in sorted(project_models.items()):
        name = model["name"]
        path = model.get("original_file_path", "")
        layer = _layer_from_path(path)
        meta = _get_meta(model)

        if (model.get("description") or "").strip():
            documented_models += 1
        else:
            errors.append(
                f"Model '{name}' ({path}) is missing a description in schema.yml."
            )

        if uid not in data_tested_models:
            errors.append(
                f"Model '{name}' ({path}) has no dbt data_tests in schema.yml."
            )

        if layer in UNIT_TEST_REQUIRED_LAYERS and not meta.get(
            "unit_test_exempt", False
        ):
            unit_test_required_total += 1
            if uid in unit_tested_models:
                unit_test_required_covered += 1
            else:
                errors.append(
                    f"Model '{name}' ({path}) is in '{layer}/' and must have at least "
                    "one dbt unit_tests entry in schema.yml (see CONTRIBUTING.md, or "
                    "set config.meta.unit_test_exempt: true for trivial passthrough "
                    "models)."
                )

        for col_name, col_meta in sorted(model.get("columns", {}).items()):
            if not (col_meta.get("description") or "").strip():
                errors.append(
                    f"Column '{name}.{col_name}' in schema.yml is missing a "
                    "description."
                )

        dep_nodes = model.get("depends_on", {}).get("nodes", [])
        if layer in UNIT_TEST_REQUIRED_LAYERS:
            for dep in dep_nodes:
                if dep.startswith("source."):
                    errors.append(
                        f"Layering violation: {layer} model '{name}' references raw "
                        f"'{dep}' directly; reference a staging model via ref() "
                        "instead."
                    )
        elif layer == "staging":
            for dep in dep_nodes:
                dep_node = project_models.get(dep)
                if dep_node:
                    dep_layer = _layer_from_path(dep_node.get("original_file_path", ""))
                    if dep_layer in UNIT_TEST_REQUIRED_LAYERS:
                        errors.append(
                            f"Layering violation: staging model '{name}' references "
                            f"{dep_layer} model '{dep_node['name']}'."
                        )

    # 5: Custom macro coverage.
    for uid, macro in sorted(project_macros.items()):
        if uid not in covered_macros:
            errors.append(
                f"Macro '{macro['name']}' ({macro.get('original_file_path', '')}) "
                f"is not exercised by any model or test."
            )

    # 6: Source documentation and freshness.
    compliant_sources = 0
    for _uid, src in sorted(project_sources.items()):
        src_label = f"{src.get('source_name')}.{src.get('name')}"
        src_ok = True

        if not (src.get("description") or "").strip():
            errors.append(f"Source '{src_label}' is missing a description.")
            src_ok = False

        meta = _get_meta(src)
        if not meta.get("freshness_exempt", False):
            freshness = src.get("freshness") or {}
            has_threshold = bool(
                (freshness.get("warn_after") or {}).get("count")
                or (freshness.get("error_after") or {}).get("count")
            )
            if not src.get("loaded_at_field") or not has_threshold:
                errors.append(
                    f"Source '{src_label}' must configure config.loaded_at_field and "
                    "config.freshness (or set config.meta.freshness_exempt: true for "
                    "static tables)."
                )
                src_ok = False

        if src_ok:
            compliant_sources += 1

    summary = {
        "models_documented": (documented_models, len(project_models)),
        "models_data_tested": (len(data_tested_models), len(project_models)),
        "logic_models_unit_tested": (
            unit_test_required_covered,
            unit_test_required_total,
        ),
        "macros_covered": (len(covered_macros), len(project_macros)),
        "sources_compliant": (compliant_sources, len(project_sources)),
    }
    return summary, errors


def main(manifest_path: pathlib.Path = MANIFEST_PATH) -> int:
    if not manifest_path.exists():
        print(
            f"ERROR: {manifest_path} not found. Run `dbt parse` first.",
            file=sys.stderr,
        )
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary, errors = check_manifest(manifest)

    def _pct(num: int, den: int) -> str:
        return "100%" if den == 0 else f"{(num / den) * 100:.0f}%"

    print("dbt Coverage Summary:")
    for label, key in (
        ("Models documented       ", "models_documented"),
        ("Models data-tested      ", "models_data_tested"),
        ("Logic models unit-tested", "logic_models_unit_tested"),
        ("Macros covered          ", "macros_covered"),
        ("Sources compliant       ", "sources_compliant"),
    ):
        num, den = summary[key]
        print(f"  {label}: {num}/{den} ({_pct(num, den)})")

    if errors:
        print("\nCoverage / DAG check failures:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("\nAll dbt coverage and DAG layering checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
