"""Tests for autolab.results_tables — pure formatting helpers and the
end-to-end markdown generator."""

from __future__ import annotations

import json

from autolab.results_tables import (
    detect_proposed_baseline_pairs,
    fmt_num,
    format_results_tables,
    is_stat_dict,
    pick_summary_metric,
)


class TestFmtNum:
    def test_none_renders_dash(self):
        assert fmt_num(None) == "—"

    def test_zero(self):
        assert fmt_num(0) == "0"
        assert fmt_num(0.0) == "0"

    def test_non_numeric_string_passes_through(self):
        assert fmt_num("not a number") == "not a number"

    def test_small_decimal_uses_decimal(self):
        out = fmt_num(0.1234)
        assert "e" not in out
        assert out.startswith("0.")

    def test_very_small_uses_scientific(self):
        out = fmt_num(0.0000123)
        assert "e" in out

    def test_very_large_uses_scientific(self):
        out = fmt_num(1234567)
        assert "e" in out


class TestIsStatDict:
    def test_canonical_stat_dict(self):
        assert is_stat_dict({"mean": 0.5, "stddev": 0.1, "n_seeds": 3})

    def test_int_mean_is_accepted(self):
        assert is_stat_dict({"mean": 1})

    def test_missing_mean_rejected(self):
        assert not is_stat_dict({"stddev": 0.1})

    def test_string_mean_rejected(self):
        assert not is_stat_dict({"mean": "high"})

    def test_non_dict_rejected(self):
        assert not is_stat_dict(0.5)
        assert not is_stat_dict([1, 2, 3])
        assert not is_stat_dict(None)


class TestDetectProposedBaselinePairs:
    def test_prefix_pairs(self):
        m = {
            "proposed_acc": {"mean": 0.9},
            "baseline_acc": {"mean": 0.7},
            "unrelated": {"mean": 0.0},
        }
        pairs = detect_proposed_baseline_pairs(m)
        assert pairs == [("acc", "proposed_acc", "baseline_acc")]

    def test_suffix_pairs(self):
        m = {
            "acc_proposed": {"mean": 0.9},
            "acc_baseline": {"mean": 0.7},
        }
        pairs = detect_proposed_baseline_pairs(m)
        assert pairs == [("acc", "acc_proposed", "acc_baseline")]

    def test_unpaired_proposed_is_dropped(self):
        m = {"proposed_acc": {"mean": 0.9}}
        assert detect_proposed_baseline_pairs(m) == []

    def test_pair_only_counted_once(self):
        # Walking both keys in the dict shouldn't double-count.
        m = {
            "proposed_acc": {"mean": 0.9},
            "baseline_acc": {"mean": 0.7},
        }
        assert len(detect_proposed_baseline_pairs(m)) == 1


class TestPickSummaryMetric:
    def test_predicted_metric_wins(self):
        m = {
            "delta_x": {"mean": 0.1},
            "val_acc": {"mean": 0.9},
        }
        assert pick_summary_metric(m, "val_acc") == "val_acc"

    def test_falls_back_to_delta_like_name(self):
        m = {
            "loss": {"mean": 0.1},
            "delta_val_acc": {"mean": 0.05},
        }
        assert pick_summary_metric(m, "missing") == "delta_val_acc"

    def test_falls_back_to_first_stat_dict(self):
        m = {"some_metric": {"mean": 0.5}}
        assert pick_summary_metric(m, "missing") == "some_metric"

    def test_returns_none_when_no_stat_dicts(self):
        assert pick_summary_metric({"x": 1.0}, "x") is None


class TestFormatResultsTablesEndToEnd:
    def _write_result(self, exp_dir, plan_id, payload):
        d = exp_dir / plan_id
        d.mkdir(parents=True)
        (d / "result.json").write_text(json.dumps(payload))

    def test_no_results_returns_empty_string(self, tmp_path):
        assert format_results_tables([], tmp_path) == ""

    def test_renders_summary_for_canonical_schema(self, tmp_path):
        thread = [
            {
                "type": "Hypothesis",
                "id": "HYP-001",
                "summary": "Hypothesis claim text",
                "prediction_metric": "val_acc",
                "prediction_threshold": 0.05,
                "prediction_direction": "greater",
            },
            {"type": "ExperimentPlan", "id": "EXP-001", "parent": "HYP-001"},
            {
                "type": "ExperimentResult",
                "id": "RES-001",
                "plan_id": "EXP-001",
                "status": "fail",
            },
        ]
        self._write_result(
            tmp_path,
            "EXP-001",
            {
                "metrics": {
                    "val_acc": {"mean": 0.05, "stddev": 0.01, "n_seeds": 3},
                },
                "notes": "single-line note",
            },
        )
        out = format_results_tables(thread, tmp_path)
        assert "### Results Summary" in out
        assert "EXP-001" in out
        # The picked summary metric appears as a column.
        assert "val_acc" in out

    def test_renders_proposed_baseline_pair(self, tmp_path):
        thread = [
            {"type": "ExperimentPlan", "id": "EXP-007"},
            {
                "type": "ExperimentResult",
                "id": "RES-007",
                "plan_id": "EXP-007",
                "status": "pass",
            },
        ]
        self._write_result(
            tmp_path,
            "EXP-007",
            {
                "metrics": {
                    "proposed_acc": {"mean": 0.9, "stddev": 0.02, "n_seeds": 3},
                    "baseline_acc": {"mean": 0.7, "stddev": 0.03, "n_seeds": 3},
                }
            },
        )
        out = format_results_tables(thread, tmp_path)
        assert "Proposed" in out and "Baseline" in out
        # The base metric name (without prefix) is what surfaces in the row.
        assert "acc" in out

    def test_missing_result_json_handled_gracefully(self, tmp_path):
        # Plan exists but no result.json on disk — the renderer should still
        # produce SOMETHING (either skip the row or render with placeholders),
        # and must not raise.
        thread = [
            {"type": "ExperimentPlan", "id": "EXP-002"},
            {
                "type": "ExperimentResult",
                "id": "RES-002",
                "plan_id": "EXP-002",
                "status": "crash",
            },
        ]
        out = format_results_tables(thread, tmp_path)
        # No assertion on content shape; just guarding against a crash and
        # confirming we get a string back.
        assert isinstance(out, str)
