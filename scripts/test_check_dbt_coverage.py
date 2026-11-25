"""Unit tests for scripts/check_dbt_coverage.py."""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

import check_dbt_coverage as cov


def _model(
    name: str,
    path: str,
    *,
    description: str = "Model description.",
    columns: dict[str, dict] | None = None,
    depends_on_nodes: list[str] | None = None,
    depends_on_macros: list[str] | None = None,
    config: dict | None = None,
) -> tuple[str, dict]:
    uid = f"model.oppia_analytics.{name}"
    node: dict = {
        "resource_type": "model",
        "package_name": "oppia_analytics",
        "name": name,
        "original_file_path": path,
        "description": description,
        "columns": columns if columns is not None else {},
        "depends_on": {
            "nodes": depends_on_nodes or [],
            "macros": depends_on_macros or [],
        },
    }
    if config is not None:
        node["config"] = config
    return uid, node


def _data_test(
    name: str,
    *,
    depends_on_nodes: list[str] | None = None,
    depends_on_macros: list[str] | None = None,
) -> tuple[str, dict]:
    uid = f"test.oppia_analytics.{name}"
    return uid, {
        "resource_type": "test",
        "package_name": "oppia_analytics",
        "name": name,
        "depends_on": {
            "nodes": depends_on_nodes or [],
            "macros": depends_on_macros or [],
        },
    }


def _unit_test(
    name: str,
    *,
    model: str,
    depends_on_nodes: list[str] | None = None,
    depends_on_macros: list[str] | None = None,
) -> tuple[str, dict]:
    uid = f"unit_test.oppia_analytics.{model}.{name}"
    return uid, {
        "package_name": "oppia_analytics",
        "model": model,
        "depends_on": {
            "nodes": depends_on_nodes or [],
            "macros": depends_on_macros or [],
        },
    }


def _macro(
    name: str,
    *,
    depends_on_macros: list[str] | None = None,
) -> tuple[str, dict]:
    uid = f"macro.oppia_analytics.{name}"
    return uid, {
        "package_name": "oppia_analytics",
        "name": name,
        "original_file_path": f"macros/{name}.sql",
        "depends_on": {"macros": depends_on_macros or []},
    }


def _source(
    source_name: str,
    table_name: str,
    *,
    description: str = "Raw source table.",
    loaded_at_field: str | None = "TIMESTAMP_MICROS(event_timestamp)",
    freshness: dict | None = None,
    include_default_freshness: bool = True,
    config: dict | None = None,
) -> tuple[str, dict]:
    uid = f"source.oppia_analytics.{source_name}.{table_name}"
    src: dict = {
        "package_name": "oppia_analytics",
        "source_name": source_name,
        "name": table_name,
        "description": description,
    }
    if loaded_at_field is not None:
        src["loaded_at_field"] = loaded_at_field
    if freshness is not None:
        src["freshness"] = freshness
    elif include_default_freshness:
        src["freshness"] = {"error_after": {"count": 48, "period": "hour"}}
    if config is not None:
        src["config"] = config
    return uid, src


def _build_manifest(
    *,
    models: list[tuple[str, dict]] | None = None,
    data_tests: list[tuple[str, dict]] | None = None,
    unit_tests: list[tuple[str, dict]] | None = None,
    macros: list[tuple[str, dict]] | None = None,
    sources: list[tuple[str, dict]] | None = None,
) -> dict:
    nodes: dict[str, dict] = {}
    for uid, node in (models or []) + (data_tests or []):
        nodes[uid] = node
    return {
        "nodes": nodes,
        "unit_tests": dict(unit_tests or []),
        "macros": dict(macros or []),
        "sources": dict(sources or []),
    }


class CheckDbtCoverageTest(unittest.TestCase):
    def test_layer_from_path_returns_layer_for_models_and_none_otherwise(self) -> None:
        self.assertEqual(
            cov._layer_from_path("models/staging/web/stg_events.sql"), "staging"
        )
        self.assertIsNone(cov._layer_from_path("tests/test_something.sql"))

    def test_valid_staging_manifest_passes_with_full_coverage(self) -> None:
        src_uid, src = _source("raw", "events_*")
        stg_uid, stg = _model(
            "stg_events",
            "models/staging/web/stg_events.sql",
            columns={"user_id": {"description": "User identifier."}},
            depends_on_nodes=[src_uid],
        )
        macro_uid, macro = _macro("my_macro")
        test_entry = _data_test(
            "not_null_stg_events_user_id",
            depends_on_nodes=[stg_uid],
            depends_on_macros=[macro_uid],
        )
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[test_entry],
            macros=[(macro_uid, macro)],
            sources=[(src_uid, src)],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["models_documented"], (1, 1))
        self.assertEqual(summary["models_data_tested"], (1, 1))
        self.assertEqual(summary["logic_models_unit_tested"], (0, 0))
        self.assertEqual(summary["macros_covered"], (1, 1))
        self.assertEqual(summary["sources_compliant"], (1, 1))

    def test_model_without_description_fails(self) -> None:
        stg_uid, stg = _model(
            "stg_events", "models/staging/web/stg_events.sql", description=""
        )
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[_data_test("t_stg", depends_on_nodes=[stg_uid])],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["models_documented"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("Model 'stg_events'", errors[0])
        self.assertIn("missing a description", errors[0])

    def test_model_without_data_tests_fails(self) -> None:
        stg_uid, stg = _model("stg_events", "models/staging/web/stg_events.sql")
        manifest = _build_manifest(models=[(stg_uid, stg)])

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["models_data_tested"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("Model 'stg_events'", errors[0])
        self.assertIn("has no dbt data_tests", errors[0])

    def test_column_without_description_fails(self) -> None:
        stg_uid, stg = _model(
            "stg_events",
            "models/staging/web/stg_events.sql",
            columns={"user_id": {"description": "   "}},
        )
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[_data_test("t_stg", depends_on_nodes=[stg_uid])],
        )

        _, errors = cov.check_manifest(manifest)

        self.assertEqual(len(errors), 1)
        self.assertIn("Column 'stg_events.user_id'", errors[0])

    def test_mart_without_unit_test_fails(self) -> None:
        mart_uid, mart = _model(
            "fct_lessons", "models/marts/curriculum/fct_lessons.sql"
        )
        manifest = _build_manifest(
            models=[(mart_uid, mart)],
            data_tests=[_data_test("t_mart", depends_on_nodes=[mart_uid])],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["logic_models_unit_tested"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("fct_lessons", errors[0])
        self.assertIn("unit_tests", errors[0])

    def test_mart_with_unit_test_passes(self) -> None:
        mart_uid, mart = _model(
            "fct_lessons", "models/marts/curriculum/fct_lessons.sql"
        )
        manifest = _build_manifest(
            models=[(mart_uid, mart)],
            data_tests=[_data_test("t_mart", depends_on_nodes=[mart_uid])],
            unit_tests=[_unit_test("basic", model="fct_lessons")],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["logic_models_unit_tested"], (1, 1))

    def test_mart_with_unit_test_exempt_passes(self) -> None:
        mart_uid, mart = _model(
            "fct_lessons",
            "models/marts/curriculum/fct_lessons.sql",
            config={"meta": {"unit_test_exempt": True}},
        )
        manifest = _build_manifest(
            models=[(mart_uid, mart)],
            data_tests=[_data_test("t_mart", depends_on_nodes=[mart_uid])],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["logic_models_unit_tested"], (0, 0))

    def test_mart_with_only_unit_test_still_requires_data_test(self) -> None:
        mart_uid, mart = _model(
            "fct_lessons", "models/marts/curriculum/fct_lessons.sql"
        )
        manifest = _build_manifest(
            models=[(mart_uid, mart)],
            unit_tests=[_unit_test("basic", model="fct_lessons")],
        )

        _, errors = cov.check_manifest(manifest)

        self.assertEqual(len(errors), 1)
        self.assertIn("fct_lessons", errors[0])
        self.assertIn("data_tests", errors[0])

    def test_mart_referencing_raw_source_fails_layering(self) -> None:
        src_uid, src = _source("raw", "events_*")
        stg_uid, stg = _model("stg_events", "models/staging/web/stg_events.sql")
        mart_uid, mart = _model(
            "fct_bad",
            "models/marts/users/fct_bad.sql",
            depends_on_nodes=[src_uid, stg_uid],
        )
        manifest = _build_manifest(
            models=[(stg_uid, stg), (mart_uid, mart)],
            data_tests=[
                _data_test("t_stg", depends_on_nodes=[stg_uid]),
                _data_test("t_mart", depends_on_nodes=[mart_uid]),
            ],
            unit_tests=[_unit_test("basic", model="fct_bad")],
            sources=[(src_uid, src)],
        )

        _, errors = cov.check_manifest(manifest)

        self.assertEqual(len(errors), 1)
        self.assertIn("Layering violation: marts model 'fct_bad'", errors[0])

    def test_staging_referencing_mart_fails_layering(self) -> None:
        mart_uid, mart = _model(
            "fct_lessons", "models/marts/curriculum/fct_lessons.sql"
        )
        stg_uid, stg = _model(
            "stg_bad",
            "models/staging/web/stg_bad.sql",
            depends_on_nodes=[mart_uid],
        )
        manifest = _build_manifest(
            models=[(mart_uid, mart), (stg_uid, stg)],
            data_tests=[
                _data_test("t_mart", depends_on_nodes=[mart_uid]),
                _data_test("t_stg", depends_on_nodes=[stg_uid]),
            ],
            unit_tests=[_unit_test("basic", model="fct_lessons")],
        )

        _, errors = cov.check_manifest(manifest)

        self.assertEqual(len(errors), 1)
        self.assertIn("Layering violation: staging model 'stg_bad'", errors[0])

    def test_staging_referencing_staging_and_non_layer_model_pass(self) -> None:
        stg_a_uid, stg_a = _model("stg_a", "models/staging/web/stg_a.sql")
        stg_b_uid, stg_b = _model(
            "stg_b",
            "models/staging/web/stg_b.sql",
            depends_on_nodes=[stg_a_uid],
        )
        misc_uid, misc = _model("misc_model", "other/misc_model.sql")
        manifest = _build_manifest(
            models=[(stg_a_uid, stg_a), (stg_b_uid, stg_b), (misc_uid, misc)],
            data_tests=[
                _data_test("t_a", depends_on_nodes=[stg_a_uid]),
                _data_test("t_b", depends_on_nodes=[stg_b_uid]),
                _data_test("t_misc", depends_on_nodes=[misc_uid]),
            ],
        )

        _, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])

    def test_uncovered_macro_fails(self) -> None:
        macro_uid, macro = _macro("unused_macro")
        manifest = _build_manifest(macros=[(macro_uid, macro)])

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["macros_covered"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("Macro 'unused_macro'", errors[0])

    def test_transitively_referenced_macro_and_cycles_pass(self) -> None:
        macro_a_uid, macro_a = _macro(
            "macro_a",
            depends_on_macros=[
                "macro.oppia_analytics.macro_b",
                "macro.dbt.builtin_macro",
            ],
        )
        macro_b_uid, macro_b = _macro(
            "macro_b", depends_on_macros=["macro.oppia_analytics.macro_a"]
        )
        stg_uid, stg = _model(
            "stg_events",
            "models/staging/web/stg_events.sql",
            depends_on_macros=[macro_b_uid, macro_a_uid],
        )
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[_data_test("t_stg", depends_on_nodes=[stg_uid])],
            macros=[(macro_a_uid, macro_a), (macro_b_uid, macro_b)],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["macros_covered"], (2, 2))

    def test_non_model_test_dependency_and_unknown_unit_test_target_ignored(
        self,
    ) -> None:
        src_uid, src = _source("raw", "events_*")
        stg_uid, stg = _model("stg_events", "models/staging/web/stg_events.sql")
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[
                _data_test("t_stg", depends_on_nodes=[stg_uid, src_uid]),
            ],
            unit_tests=[_unit_test("ghost", model="nonexistent_model")],
            sources=[(src_uid, src)],
        )

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["models_data_tested"], (1, 1))

    def test_source_without_description_fails(self) -> None:
        src_uid, src = _source("raw", "events_*", description="")
        manifest = _build_manifest(sources=[(src_uid, src)])

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["sources_compliant"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("Source 'raw.events_*' is missing a description", errors[0])

    def test_source_without_freshness_fails(self) -> None:
        src_uid, src = _source("raw", "events_*", include_default_freshness=False)
        manifest = _build_manifest(sources=[(src_uid, src)])

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(summary["sources_compliant"], (0, 1))
        self.assertEqual(len(errors), 1)
        self.assertIn("config.freshness", errors[0])

    def test_source_with_freshness_exempt_passes(self) -> None:
        src_uid, src = _source(
            "raw",
            "static_lookup",
            loaded_at_field=None,
            include_default_freshness=False,
            config={"meta": {"freshness_exempt": True}},
        )
        manifest = _build_manifest(sources=[(src_uid, src)])

        summary, errors = cov.check_manifest(manifest)

        self.assertEqual(errors, [])
        self.assertEqual(summary["sources_compliant"], (1, 1))

    def test_main_returns_error_when_manifest_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stderr_buf = io.StringIO()
            with contextlib.redirect_stderr(stderr_buf):
                code = cov.main(pathlib.Path(tmpdir) / "missing.json")

        self.assertEqual(code, 1)
        self.assertIn("not found", stderr_buf.getvalue())

    def test_main_returns_zero_for_valid_manifest(self) -> None:
        stg_uid, stg = _model("stg_events", "models/staging/web/stg_events.sql")
        manifest = _build_manifest(
            models=[(stg_uid, stg)],
            data_tests=[_data_test("t_stg", depends_on_nodes=[stg_uid])],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = pathlib.Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            stdout_buf = io.StringIO()
            with contextlib.redirect_stdout(stdout_buf):
                code = cov.main(manifest_path)

        self.assertEqual(code, 0)
        self.assertIn(
            "All dbt coverage and DAG layering checks passed.", stdout_buf.getvalue()
        )

    def test_main_returns_error_and_prints_failures_for_invalid_manifest(self) -> None:
        stg_uid, stg = _model(
            "stg_events", "models/staging/web/stg_events.sql", description=""
        )
        manifest = _build_manifest(models=[(stg_uid, stg)])
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = pathlib.Path(tmpdir) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            stdout_buf = io.StringIO()
            stderr_buf = io.StringIO()
            with (
                contextlib.redirect_stdout(stdout_buf),
                contextlib.redirect_stderr(stderr_buf),
            ):
                code = cov.main(manifest_path)

        self.assertEqual(code, 1)
        self.assertIn("Coverage / DAG check failures:", stderr_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
