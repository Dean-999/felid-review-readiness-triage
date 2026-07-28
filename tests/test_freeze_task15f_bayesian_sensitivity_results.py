from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import freeze_task15f_bayesian_sensitivity_results as module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Task15FResultFreezeTests(unittest.TestCase):
    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_results(self, root: Path, validation_status: str = "PASS") -> None:
        root.mkdir(parents=True, exist_ok=True)
        prediction_rows: list[dict[str, object]] = []
        for index in range(445):
            label = int(index % 5 != 0)
            inclusion_probability = 0.2 + 0.01 * (index % 5)
            for model_id, offset in (("S3", 0.0), ("S4", 0.01)):
                probability = 0.72 + 0.02 * (index % 4) + offset
                prediction_rows.append(
                    {
                        "canonical_pair_id": f"pair_{index:03d}",
                        "pair_execution_id": f"exec_{index:03d}",
                        "component_id": f"component_{index % 116:03d}",
                        "outer_fold": index % 5,
                        "model_id": model_id,
                        "review_ready_label": label,
                        "first_order_inclusion_probability": inclusion_probability,
                        "posterior_mean_probability": probability,
                        "posterior_probability_lower_95": max(0.0, probability - 0.1),
                        "posterior_probability_upper_95": min(1.0, probability + 0.1),
                        "brier_loss": (label - probability) ** 2,
                    }
                )
        self.write_csv(root / "bayesian_oof_predictions.csv", list(prediction_rows[0]), prediction_rows)

        overall_rows = []
        outer_rows = []
        for model_id in ("S3", "S4"):
            model_rows = [row for row in prediction_rows if row["model_id"] == model_id]
            overall_rows.append(module.recompute_metric_row(model_rows, model_id=model_id))
            for fold in range(5):
                fold_rows = [row for row in model_rows if row["outer_fold"] == fold]
                outer_rows.append(module.recompute_metric_row(fold_rows, model_id=model_id, outer_fold=fold))
        self.write_csv(root / "bayesian_overall_metrics.csv", list(overall_rows[0]), overall_rows)
        self.write_csv(root / "bayesian_outer_fold_metrics.csv", list(outer_rows[0]), outer_rows)

        diagnostics = []
        parameter_rows = []
        pair_rows = []
        for fold in range(5):
            for model_id in ("S3", "S4"):
                diagnostics.append(
                    {
                        "status": "PASS",
                        "model_id": model_id,
                        "divergences": 0,
                        "failures": "[]",
                        "fixed_max_rhat": 1.003 + 0.0001 * fold,
                        "fixed_min_bulk_ess": 2200 + fold,
                        "fixed_min_tail_ess": 2800 + fold,
                        "image_offset_diagnostics": "" if model_id == "S3" else "{'max_rhat': 1.004}",
                        "outer_fold": fold,
                        "accepted_attempt": 1,
                    }
                )
                coverage = {
                    "model_id": model_id,
                    "outer_fold": fold,
                    "parameter": "local_match_coverage_fraction__z",
                    "mean": 0.2 + 0.01 * fold,
                    "sd": 0.3,
                    "lower_95": -0.2,
                    "upper_95": 0.8,
                    "posterior_probability_gt_zero": 0.75,
                }
                pair_rows.append(coverage)
                parameter_rows.append(coverage)
                if model_id == "S4":
                    parameter_rows.append(
                        {
                            "model_id": model_id,
                            "outer_fold": fold,
                            "parameter": "sigma_image",
                            "mean": 1.2 + 0.01 * fold,
                            "sd": 0.2,
                            "lower_95": 0.7,
                            "upper_95": 1.8,
                            "posterior_probability_gt_zero": 1.0,
                        }
                    )
        self.write_csv(root / "posterior_diagnostics.csv", list(diagnostics[0]), diagnostics)
        self.write_csv(root / "posterior_parameter_summary.csv", list(parameter_rows[0]), parameter_rows)
        self.write_csv(root / "pair_evidence_posterior_summary.csv", list(pair_rows[0]), pair_rows)

        firth = []
        for fold in (0, 4):
            for index in range(90):
                firth.append(
                    {
                        "canonical_pair_id": f"pair_{fold}_{index}",
                        "outer_fold": fold,
                        "model_id": "S5_FLIC_DIAGNOSTIC_ONLY",
                        "posterior_or_prediction_probability": 0.8,
                        "review_ready_label": 1,
                        "selection_eligible": False,
                        "fit_iterations": 30,
                        "retained_design_columns": 10,
                    }
                )
        self.write_csv(root / "firth_flic_diagnostic.csv", list(firth[0]), firth)

        (root / "execution_contract_frozen.json").write_text(
            json.dumps({"contract_version": "pferi_v2_task15f_bayesian_sensitivity_contract_v1"}),
            encoding="utf-8",
        )
        contract_hash = sha256(root / "execution_contract_frozen.json")
        (root / "execution_audit.json").write_text(
            json.dumps(
                {
                    "status": "RUN_COMPLETE_PENDING_VALIDATION",
                    "prediction_rows": 890,
                    "posterior_fold_fits": 10,
                    "S5_status": "TRIGGERED_DIAGNOSTIC_ONLY",
                    "locked_stage_outcomes_accessed": False,
                    "contract_sha256": contract_hash,
                }
            ),
            encoding="utf-8",
        )
        (root / "validation_audit.json").write_text(
            json.dumps({"status": validation_status, "failures": [] if validation_status == "PASS" else ["fixture"]}),
            encoding="utf-8",
        )
        (root / "prior_predictive_audit.json").write_text(
            json.dumps({"status": "PASS", "checks": [{"status": "PASS"}] * 10}), encoding="utf-8"
        )
        (root / "S4_marginalization_audit.json").write_text(
            json.dumps(
                {"status": "PASS", "checks": [{"status": "PASS", "quadrature_nodes": 20}] * 5}
            ),
            encoding="utf-8",
        )
        (root / "separation_trigger_audit.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "S5_trigger_status": "TRIGGERED_DIAGNOSTIC_ONLY",
                    "selection_eligible": False,
                    "folds": [{"outer_fold": fold, "triggered": fold in {0, 4}} for fold in range(5)],
                }
            ),
            encoding="utf-8",
        )
        (root / "TASK15F_SENSITIVITY_REPORT.md").write_text("# Fixture\n", encoding="utf-8")

        checkpoint_dir = root / "fold_checkpoints"
        posterior_dir = root / "posterior_samples"
        checkpoint_dir.mkdir()
        posterior_dir.mkdir()
        for fold in range(5):
            for model_id in ("S3", "S4"):
                (checkpoint_dir / f"{model_id}_fold{fold}.json").write_text("{}", encoding="utf-8")
                (checkpoint_dir / f"{model_id}_fold{fold}_parameters.csv").write_text("parameter\n", encoding="utf-8")
                (checkpoint_dir / f"{model_id}_fold{fold}_predictions.csv").write_text("probability\n", encoding="utf-8")
                (posterior_dir / f"{model_id}_fold{fold}_attempt1.nc").write_bytes(b"fixture")

        files = sorted(path for path in root.rglob("*") if path.is_file())
        (root / "CHECKSUMS.sha256").write_text(
            "".join(f"{sha256(path)}  {path.relative_to(root)}\n" for path in files), encoding="utf-8"
        )

    def write_task15e_freeze(self, root: Path) -> Path:
        result = root / "results"
        result.mkdir(parents=True)
        self.write_csv(
            result / "overall_model_metrics.csv",
            ["model_id", "weighted_brier", "weighted_log_loss"],
            [{"model_id": "P5", "weighted_brier": 0.14, "weighted_log_loss": 0.45}],
        )
        (root / "freeze_audit.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        (root / "development_disposition.json").write_text(
            json.dumps({"status": "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_QUALIFICATION"}), encoding="utf-8"
        )
        return root

    def write_delivery(self, root: Path, validation_status: str = "PASS") -> tuple[Path, Path, Path, Path]:
        results = root / "PF_ERI_TASK15F_RESULTS"
        self.write_results(results, validation_status=validation_status)
        zip_path = root / "PF_ERI_TASK15F_FINAL_EXPORT.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(results.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"PF_ERI_TASK15F_RESULTS/{path.relative_to(results)}")
        sha_path = root / "PF_ERI_TASK15F_FINAL_EXPORT.sha256"
        sha_path.write_text(f"{sha256(zip_path)}  /external/PF_ERI_TASK15F_FINAL_EXPORT.zip\n", encoding="utf-8")
        summary = root / "PF_ERI_TASK15F_RUN_SUMMARY.txt"
        summary.write_text(
            "status=COMPLETE\n"
            f"final_export_sha256={sha256(zip_path)}\n"
            f"final_export_size_bytes={zip_path.stat().st_size}\n"
            "final_export_members=55\n",
            encoding="utf-8",
        )
        task15e = self.write_task15e_freeze(root / "task15e")
        return zip_path, sha_path, summary, task15e

    def test_independent_analysis_recomputes_metrics_and_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_results(root)
            task15e = self.write_task15e_freeze(root / "task15e")

            analysis = module.independent_analysis(root, task15e)

            self.assertEqual(analysis["status"], "PASS")
            self.assertEqual(analysis["prediction_rows"], 890)
            self.assertEqual(analysis["unique_pairs"], 445)
            self.assertEqual(analysis["unique_components"], 116)
            self.assertEqual(analysis["posterior_diagnostics"]["divergences"], 0)
            self.assertEqual(analysis["pair_evidence"]["credible_intervals_crossing_zero"], 10)
            self.assertEqual(analysis["S5_diagnostic"]["selection_eligible_rows"], 0)
            self.assertIn("S3_minus_S4_weighted_brier", analysis)
            self.assertIn("S3_vs_P5_relative_brier_improvement_percent", analysis)

    def test_freeze_writes_complete_immutable_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root)
            output = root / "freeze"

            audit = module.freeze(zip_path, sha_path, summary, task15e, output)

            self.assertEqual(audit["status"], "PASS")
            self.assertEqual(audit["prediction_rows"], 890)
            self.assertTrue((output / "source_delivery" / zip_path.name).is_file())
            self.assertTrue((output / "results" / "posterior_samples" / "S4_fold4_attempt1.nc").is_file())
            self.assertTrue((output / "independent_recalculation.json").is_file())
            self.assertTrue((output / "task15f_disposition.json").is_file())
            self.assertTrue((output / "TASK15F_BAYESIAN_SENSITIVITY_RESULT_FREEZE_REPORT.md").is_file())
            self.assertTrue((output / "CHECKSUMS.sha256").is_file())
            disposition = json.loads((output / "task15f_disposition.json").read_text(encoding="utf-8"))
            self.assertEqual(disposition["next_authorized_task"], "Task15G exploratory performance-bound benchmark")
            self.assertFalse(disposition["final_model_selected"])

    def test_external_sha_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root)
            sha_path.write_text(f"{'0' * 64}  bad.zip\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "external ZIP SHA256 mismatch"):
                module.freeze(zip_path, sha_path, summary, task15e, root / "freeze")

    def test_internal_checksum_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root)
            results = root / "PF_ERI_TASK15F_RESULTS"
            (results / "validation_audit.json").write_text(
                '{"status":"PASS","failures":[]}', encoding="utf-8"
            )
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(results.rglob("*")):
                    if path.is_file():
                        archive.write(path, arcname=f"PF_ERI_TASK15F_RESULTS/{path.relative_to(results)}")
            sha_path.write_text(f"{sha256(zip_path)}  result.zip\n", encoding="utf-8")
            summary.write_text(
                "status=COMPLETE\n"
                f"final_export_sha256={sha256(zip_path)}\n"
                f"final_export_size_bytes={zip_path.stat().st_size}\n"
                "final_export_members=55\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "unexpected result inventory|internal checksum"):
                module.freeze(zip_path, sha_path, summary, task15e, root / "freeze")

    def test_failed_upstream_validation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root, validation_status="FAIL")
            with self.assertRaisesRegex(RuntimeError, "upstream validation did not pass"):
                module.freeze(zip_path, sha_path, summary, task15e, root / "freeze")

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root)
            output = root / "freeze"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                module.freeze(zip_path, sha_path, summary, task15e, output)

    def test_run_summary_hash_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            zip_path, sha_path, summary, task15e = self.write_delivery(root)
            summary.write_text(
                "status=COMPLETE\n"
                f"final_export_sha256={'f' * 64}\n"
                f"final_export_size_bytes={zip_path.stat().st_size}\n"
                "final_export_members=55\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "run summary ZIP SHA256 mismatch"):
                module.freeze(zip_path, sha_path, summary, task15e, root / "freeze")

    def test_declared_sha_and_summary_validation_reject_malformed_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            declaration = root / "result.sha256"
            declaration.write_text("not-a-hash\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "declaration is invalid"):
                module.parse_declared_sha(declaration)

            export = root / "result.zip"
            export.write_bytes(b"fixture")
            export_hash = sha256(export)
            cases = {
                "status": ("status=FAILED", "does not report COMPLETE"),
                "size": ("status=COMPLETE\nfinal_export_sha256=" + export_hash + "\nfinal_export_size_bytes=99\nfinal_export_members=1", "size mismatch"),
                "members": ("status=COMPLETE\nfinal_export_sha256=" + export_hash + f"\nfinal_export_size_bytes={export.stat().st_size}\nfinal_export_members=2", "member count mismatch"),
            }
            for name, (text, message) in cases.items():
                with self.subTest(name=name):
                    summary = root / f"{name}.txt"
                    summary.write_text(text + "\n", encoding="utf-8")
                    with self.assertRaisesRegex(RuntimeError, message):
                        module.verify_run_summary(summary, export, export_hash, 1)

    def test_internal_manifest_rejects_malformed_and_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "CHECKSUMS.sha256"
            manifest.write_text("malformed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "malformed"):
                module.verify_internal_checksums(root)
            manifest.write_text(f"{'0' * 64}  ../escape\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unsafe"):
                module.verify_internal_checksums(root)
            manifest.write_text("", encoding="utf-8")
            count, failures = module.verify_internal_checksums(root)
            self.assertEqual(count, 0)
            self.assertIn("CHECKSUMS.sha256:inventory", failures)

    def test_invalid_evaluation_weights_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid evaluation inclusion probability"):
            module.normalized_evaluation_weights(np.asarray([0.0, 0.5]))

    def test_task15e_binding_rejects_invalid_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task15e = self.write_task15e_freeze(root / "task15e")
            audit = task15e / "freeze_audit.json"
            disposition = task15e / "development_disposition.json"
            metrics = task15e / "results/overall_model_metrics.csv"

            audit.write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "audit did not pass"):
                module.verify_task15e_binding(task15e)
            audit.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

            disposition.write_text(json.dumps({"status": "OPEN"}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "required frozen state"):
                module.verify_task15e_binding(task15e)
            disposition.write_text(
                json.dumps({"status": "FROZEN_COMPLETE_WITHOUT_FINAL_MODEL_QUALIFICATION"}), encoding="utf-8"
            )

            self.write_csv(
                metrics,
                ["model_id", "weighted_brier", "weighted_log_loss"],
                [{"model_id": "P3", "weighted_brier": 0.14, "weighted_log_loss": 0.45}],
            )
            with self.assertRaisesRegex(RuntimeError, "P5 metrics are missing"):
                module.verify_task15e_binding(task15e)

    def test_cli_reports_success_and_failure(self) -> None:
        stdout = io.StringIO()
        with mock.patch.object(module, "freeze", return_value={"status": "PASS"}), redirect_stdout(stdout):
            code = module.main(["--output-dir", "unused"])
        self.assertEqual(code, 0)
        self.assertIn('"status": "PASS"', stdout.getvalue())

        stdout = io.StringIO()
        with mock.patch.object(module, "freeze", side_effect=RuntimeError("blocked")), redirect_stdout(stdout):
            code = module.main(["--output-dir", "unused"])
        self.assertEqual(code, 1)
        self.assertIn('"error": "blocked"', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
