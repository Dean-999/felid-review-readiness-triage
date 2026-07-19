from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GPU_DIR = ROOT / "gpu/kaggle_v2_local_matcher_v2"
sys.path.insert(0, str(GPU_DIR))


def write_pair_manifest(path: Path, pair_ids: list[str]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pair_execution_id", "left_asset_filename", "right_asset_filename"],
        )
        writer.writeheader()
        for index, pair_id in enumerate(pair_ids):
            writer.writerow(
                {
                    "pair_execution_id": pair_id,
                    "left_asset_filename": f"left_{index}.jpg",
                    "right_asset_filename": f"right_{index}.jpg",
                }
            )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_synthetic_shard_result(
    output_dir: Path,
    spec: object,
    common: object,
    *,
    status: str = "PARTIAL",
    binding_token: str = "binding_a",
    canonical_ids: list[str] | None = None,
    omit_direction: bool = False,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pair_ids = list(spec.pair_ids if canonical_ids is None else canonical_ids)
    canonical = []
    directional = []
    provenance = []
    for pair_id in pair_ids:
        canonical.append({
            "pair_execution_id": pair_id,
            "local_match_coverage_fraction": "",
            "value_status": "model_inference_failure",
            "failure_code": "insufficient_matches",
            "a_to_b_coverage_fraction": "",
            "b_to_a_coverage_fraction": "",
            "pair_runtime_seconds": "1.0",
            "manual_rescue_count": "0",
        })
        directions = ["A_to_B"] if omit_direction else ["A_to_B", "B_to_A"]
        for direction in directions:
            directional.append({
                "pair_execution_id": pair_id,
                "direction": direction,
                "source_asset_filename": "a.jpg",
                "target_asset_filename": "b.jpg",
                "local_match_coverage_fraction": "",
                "value_status": "model_inference_failure",
                "failure_code": "insufficient_matches",
                "source_region_area_px": "100",
                "target_region_area_px": "100",
                "inlier_count": "",
                "runtime_seconds": "0.5",
                "manual_rescue_count": "0",
            })
            provenance.append({
                "pair_execution_id": pair_id,
                "direction": direction,
                "region_source": "full_image",
                "target_region_source": "full_image",
                "retry_level": "level_3",
                "fallback_reason": "",
            })
    write_csv_rows(output_dir / "canonical_measurements.csv", common.CANONICAL_COLUMNS, canonical)
    write_csv_rows(output_dir / "directional_measurements.csv", common.DIRECTIONAL_COLUMNS, directional)
    write_csv_rows(output_dir / "region_provenance.csv", common.PROVENANCE_COLUMNS, provenance)
    (output_dir / "runtime_errors.json").write_text("[]\n", encoding="utf-8")
    (output_dir / "run_audit.json").write_text(json.dumps({
        "status": status,
        "pair_manifest_sha256": spec.manifest_sha256,
        "pair_count": spec.pair_count,
        "directional_row_count": len(directional),
        "canonical_row_count": len(canonical),
        "error_codes": [],
    }), encoding="utf-8")
    binding_artifacts = {
        key: hashlib.sha256(f"{binding_token}:{key}".encode("utf-8")).hexdigest()
        for key in (
            "inventory_sha256",
            "wrapper_sha256",
            "core_runner_sha256",
            "protocol_sha256",
            "freeze_record_sha256",
            "image_set_sha256",
            "weight_set_sha256",
        )
    }
    binding_fingerprint = hashlib.sha256(
        json.dumps(binding_artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (output_dir / "shard_execution_binding.json").write_text(json.dumps({
        "binding_version": "pferi_v2_shard_execution_binding_v1",
        "shard_id": spec.shard_id,
        "pair_manifest_sha256": spec.manifest_sha256,
        "execution_fingerprint": binding_fingerprint,
        **binding_artifacts,
    }), encoding="utf-8")
    checksum_targets = (
        "canonical_measurements.csv",
        "directional_measurements.csv",
        "region_provenance.csv",
        "runtime_errors.json",
        "run_audit.json",
        "shard_execution_binding.json",
    )
    (output_dir / "shard_output_checksums.json").write_text(json.dumps({
        "checksum_version": "pferi_v2_shard_output_checksums_v1",
        "files": {
            name: hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
            for name in checksum_targets
        },
    }), encoding="utf-8")


class SharedExecutionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        import full_frame_execution_common as common

        self.common = common

    def test_colab_roots_are_fully_configurable(self) -> None:
        paths = self.common.ExecutionPaths.from_roots(
            control_root=Path("/content/control"),
            image_root=Path("/content/images"),
            result_root=Path("/content/drive/MyDrive/results"),
            export_root=Path("/content/drive/MyDrive/export"),
        )
        self.assertEqual(paths.inventory_path, Path("/content/control/shard_inventory.json"))
        self.assertEqual(paths.manifest_root, Path("/content/control/public_pair_manifests"))
        self.assertEqual(paths.control_state_dir, Path("/content/drive/MyDrive/results/_control"))
        self.assertEqual(paths.final_export_zip, Path("/content/drive/MyDrive/export/PF_ERI_FINAL_EXPORT.zip"))

    def test_inventory_discovers_only_declared_noncontiguous_shards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_root = root / "public_pair_manifests"
            entries = []
            for shard_id in ("calibration_shard_006", "calibration_shard_010", "development_shard_001"):
                path = manifest_root / f"{shard_id}.csv"
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["pair_execution_id", "left_asset_filename", "right_asset_filename"])
                    writer.writeheader()
                    writer.writerow({"pair_execution_id": f"{shard_id}_pair", "left_asset_filename": f"{shard_id}_left.jpg", "right_asset_filename": f"{shard_id}_right.jpg"})
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append(
                    {
                        "shard_id": shard_id,
                        "manifest_path": f"stale/absolute/semantic/path/{shard_id}.csv",
                        "pair_count": 1,
                        "manifest_sha256": digest,
                    }
                )
            inventory_path = root / "shard_inventory.json"
            inventory_path.write_text(json.dumps(entries), encoding="utf-8")
            specs = self.common.load_inventory(inventory_path, manifest_root)
        self.assertEqual([spec.shard_id for spec in specs], [
            "calibration_shard_006",
            "calibration_shard_010",
            "development_shard_001",
        ])
        self.assertEqual(specs[0].manifest_path.name, "calibration_shard_006.csv")

    def test_inventory_rejects_duplicate_shard_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_root = root / "public_pair_manifests"
            path = manifest_root / "calibration_shard_001.csv"
            digest = write_pair_manifest(path, ["pair_a"])
            entry = {
                "shard_id": "calibration_shard_001",
                "manifest_path": "ignored.csv",
                "pair_count": 1,
                "manifest_sha256": digest,
            }
            inventory_path = root / "shard_inventory.json"
            inventory_path.write_text(json.dumps([entry, entry]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate shard_id"):
                self.common.load_inventory(inventory_path, manifest_root)

    def test_inventory_rejects_manifest_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_root = root / "public_pair_manifests"
            write_pair_manifest(manifest_root / "confirmation_shard_001.csv", ["pair_a"])
            inventory_path = root / "shard_inventory.json"
            inventory_path.write_text(
                json.dumps([
                    {
                        "shard_id": "confirmation_shard_001",
                        "manifest_path": "ignored.csv",
                        "pair_count": 1,
                        "manifest_sha256": "0" * 64,
                    }
                ]),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                self.common.load_inventory(inventory_path, manifest_root)

    def test_inventory_rejects_reversed_duplicate_unordered_image_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_root = root / "public_pair_manifests"
            entries = []
            rows = [
                ("calibration_shard_001", "pair_a", "left.jpg", "right.jpg"),
                ("development_shard_001", "pair_b", "right.jpg", "left.jpg"),
            ]
            for shard_id, pair_id, left, right in rows:
                path = manifest_root / f"{shard_id}.csv"
                write_csv_rows(
                    path,
                    ["pair_execution_id", "left_asset_filename", "right_asset_filename"],
                    [{
                        "pair_execution_id": pair_id,
                        "left_asset_filename": left,
                        "right_asset_filename": right,
                    }],
                )
                entries.append({
                    "shard_id": shard_id,
                    "manifest_path": f"public_pair_manifests/{shard_id}.csv",
                    "pair_count": 1,
                    "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
            inventory = root / "shard_inventory.json"
            inventory.write_text(json.dumps(entries), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unordered image pair"):
                self.common.load_inventory(inventory, manifest_root)


class InventoryDrivenOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        import full_frame_execution_common as common
        import full_frame_execution_orchestrator as orchestrator

        self.common = common
        self.orchestrator = orchestrator

    def make_spec(self, root: Path, shard_id: str) -> object:
        manifest = root / f"{shard_id}.csv"
        digest = write_pair_manifest(manifest, [f"{shard_id}_pair"])
        return self.common.ShardSpec(
            shard_id=shard_id,
            role=shard_id.split("_shard_", 1)[0],
            manifest_path=manifest,
            pair_count=1,
            manifest_sha256=digest,
            pair_ids=(f"{shard_id}_pair",),
        )

    def make_full_inventory(self, root: Path) -> list[object]:
        shard_ids = [
            *[f"calibration_shard_{index:03d}" for index in range(1, 11)],
            *[f"confirmation_shard_{index:03d}" for index in range(1, 11)],
            *[f"development_shard_{index:03d}" for index in range(1, 11)],
        ]
        return [self.make_spec(root, shard_id) for shard_id in shard_ids]

    def test_plan_uses_only_inventory_entries_and_skips_valid_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = [
                self.make_spec(root, "calibration_shard_006"),
                self.make_spec(root, "calibration_shard_010"),
            ]
            result_root = root / "results"
            plan = self.orchestrator.build_execution_plan(
                specs,
                result_root,
                completion_checker=lambda spec, _: spec.shard_id == "calibration_shard_006",
            )
        self.assertEqual(plan.completed_shards, ("calibration_shard_006",))
        self.assertEqual(plan.pending_shards, ("calibration_shard_010",))
        self.assertNotIn("calibration_shard_011", plan.pending_shards)

    def test_fresh_run_plan_always_covers_the_full_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = self.make_full_inventory(root)
            plan = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=1,
                completion_checker=lambda _spec, _path: False,
            )
        self.assertEqual(plan.declared_shards[0], "calibration_shard_001")
        self.assertEqual(plan.declared_shards[-1], "development_shard_010")
        self.assertEqual(len(plan.declared_shards), 30)
        self.assertEqual(plan.scheduled_shards, ("calibration_shard_001",))

    def test_fresh_first_batch_limit_and_resume_follow_inventory_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = self.make_full_inventory(root)
            one = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=1,
                completion_checker=lambda _spec, _path: False,
            )
            two = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=2,
                completion_checker=lambda _spec, _path: False,
            )
            completed = {"calibration_shard_001", "calibration_shard_002"}
            resumed = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=2,
                completion_checker=lambda spec, _path: spec.shard_id in completed,
            )
        self.assertEqual(one.scheduled_shards, ("calibration_shard_001",))
        self.assertEqual(two.scheduled_shards, ("calibration_shard_001", "calibration_shard_002"))
        self.assertEqual(resumed.scheduled_shards, ("calibration_shard_003", "calibration_shard_004"))

    def test_fresh_run_terminal_statuses_have_no_external_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = self.make_full_inventory(root)
            batch_plan = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=2,
                completion_checker=lambda spec, _path: spec.shard_id in {
                    "calibration_shard_001", "calibration_shard_002"
                },
            )
            complete_plan = self.orchestrator.build_execution_plan(
                specs,
                root / "results",
                max_shards_per_run=2,
                completion_checker=lambda _spec, _path: True,
            )
        self.assertEqual(self.orchestrator.run_status(batch_plan), "BATCH_COMPLETE")
        self.assertEqual(self.orchestrator.run_status(complete_plan), "RUN_COMPLETE")

    def test_cli_defaults_start_fresh_one_shard_at_a_time_and_has_no_start_index(self) -> None:
        parser = self.orchestrator.build_parser()
        args = parser.parse_args([
            "--control-root", "/content/control",
            "--image-root", "/content/images",
            "--result-root", "/content/results",
            "--export-root", "/content/export",
        ])
        self.assertFalse(hasattr(args, "start_index"))
        self.assertEqual(args.max_shards_per_run, 1)

    def test_dry_run_loads_no_model_and_reports_full_inventory_scope_and_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control"
            manifest_root = control / "public_pair_manifests"
            shard_ids = [
                *[f"calibration_shard_{index:03d}" for index in range(1, 11)],
                *[f"confirmation_shard_{index:03d}" for index in range(1, 11)],
                *[f"development_shard_{index:03d}" for index in range(1, 11)],
            ]
            inventory = []
            image_filenames = []
            for shard_id in shard_ids:
                pair_ids = [f"{shard_id}_pair_{index}" for index in range(5)]
                manifest = manifest_root / f"{shard_id}.csv"
                rows = []
                for index, pair_id in enumerate(pair_ids):
                    left = f"{shard_id}_left_{index}.jpg"
                    right = f"{shard_id}_right_{index}.jpg"
                    rows.append({
                        "pair_execution_id": pair_id,
                        "left_asset_filename": left,
                        "right_asset_filename": right,
                    })
                    image_filenames.extend((left, right))
                write_csv_rows(
                    manifest,
                    ["pair_execution_id", "left_asset_filename", "right_asset_filename"],
                    rows,
                )
                digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
                inventory.append({
                    "shard_id": shard_id,
                    "manifest_path": f"public_pair_manifests/{shard_id}.csv",
                    "pair_count": 5,
                    "manifest_sha256": digest,
                })
            (control / "shard_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            (control / "full_frame_local_match_runner.py").write_text("synthetic runner\n", encoding="utf-8")
            image_root = root / "images"
            image_root.mkdir()
            for filename in image_filenames:
                (image_root / filename).write_bytes(filename.encode())
            paths = self.common.ExecutionPaths.from_roots(
                control_root=control,
                image_root=image_root,
                result_root=root / "results",
                export_root=root / "exports",
            )
            state = self.orchestrator.execute(
                paths=paths,
                python_executable="python3",
                dry_run=True,
                max_shards_per_run=1,
            )
        self.assertEqual(state["status"], "DRY_RUN_PASS")
        self.assertEqual(state["declared_shard_count"], 30)
        self.assertEqual(state["declared_shards"][0], "calibration_shard_001")
        self.assertEqual(state["completed_shards"], [])
        self.assertEqual(len(state["pending_shards"]), 30)
        self.assertEqual(state["scheduled_shards"], ["calibration_shard_001"])
        self.assertEqual(state["completion_assurance"], "structural_only_dry_run_no_model_loaded")

    def test_partial_checkpoint_resume_requires_current_execution_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.make_spec(root, "confirmation_shard_001")
            output = root / "results" / spec.shard_id
            checkpoints = output / "pair_checkpoints"
            checkpoints.mkdir(parents=True)
            pair_id = spec.pair_ids[0]
            checkpoint = checkpoints / f"{pair_id}.json"
            checkpoint.write_text(json.dumps({
                "pair_execution_id": pair_id,
                "directional": [{"direction": "A_to_B"}, {"direction": "B_to_A"}],
                "canonical": {"pair_execution_id": pair_id},
                "provenance": [{}, {}],
                "runtime_errors": [],
            }), encoding="utf-8")
            self.assertFalse(self.orchestrator.safe_resume_check(spec, output, "current"))
            (output / "shard_execution_binding.json").write_text(json.dumps({
                "binding_version": "pferi_v2_shard_execution_binding_v1",
                "shard_id": spec.shard_id,
                "pair_manifest_sha256": spec.manifest_sha256,
                "execution_fingerprint": "current",
            }), encoding="utf-8")
            self.assertTrue(self.orchestrator.safe_resume_check(spec, output, "current"))
            self.assertFalse(self.orchestrator.safe_resume_check(spec, output, "different"))

    def test_dry_run_refuses_result_root_created_by_different_control_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control"
            manifest = control / "public_pair_manifests" / "calibration_shard_001.csv"
            digest = write_pair_manifest(manifest, ["pair_a"])
            (control / "shard_inventory.json").write_text(json.dumps([{
                "shard_id": "calibration_shard_001",
                "manifest_path": "public_pair_manifests/calibration_shard_001.csv",
                "pair_count": 1,
                "manifest_sha256": digest,
            }]), encoding="utf-8")
            runner = control / "full_frame_local_match_runner.py"
            runner.write_text("version one\n", encoding="utf-8")
            image_root = root / "images"
            image_root.mkdir()
            (image_root / "left_0.jpg").write_bytes(b"left")
            (image_root / "right_0.jpg").write_bytes(b"right")
            paths = self.common.ExecutionPaths.from_roots(
                control_root=control,
                image_root=image_root,
                result_root=root / "results",
                export_root=root / "exports",
            )
            self.orchestrator.execute(
                paths=paths,
                python_executable="python3",
                dry_run=True,
                max_shards_per_run=1,
            )
            runner.write_text("version two\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "incompatible RESULT_ROOT"):
                self.orchestrator.execute(
                    paths=paths,
                    python_executable="python3",
                    dry_run=True,
                    max_shards_per_run=1,
                )

    def test_fresh_run_execution_code_and_colab_readme_have_no_continuation_semantics(self) -> None:
        source = (GPU_DIR / "full_frame_execution_orchestrator.py").read_text(encoding="utf-8")
        readme = (GPU_DIR / "README.md").read_text(encoding="utf-8")
        forbidden = (
            "--start-index",
            "WAITING_FOR_EXTERNAL_RESULTS",
            "external_result_required",
            "outside_current_execution_scope",
            "Kaggle migration",
            "start-index 10",
        )
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, source)
                self.assertNotIn(value, readme)

    def test_one_canonical_package_builder_and_readme(self) -> None:
        from scripts import build_v2_full_frame_local_match_control_package as package_builder

        self.assertEqual(
            package_builder.OUTPUT_NAME,
            "PF_ERI_V2_FULL_FRAME_LOCAL_MATCH_CONTROL.zip",
        )
        self.assertEqual(package_builder.EXPECTED_SHARD_COUNT, 30)
        self.assertEqual(package_builder.EXPECTED_PAIR_COUNT, 28295)
        self.assertIn("README.md", package_builder.CONTROL_FILES)
        self.assertFalse(any(name.startswith("README_FULL_FRAME_") for name in package_builder.CONTROL_FILES))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "output filename must be"):
                package_builder.build(
                    root,
                    root / "superseded-version.zip",
                    root / "audit.json",
                )

    def test_wrapper_initializes_lightglue_before_final_freeze_and_writes_outputs_atomically(self) -> None:
        source = (GPU_DIR / "full_frame_local_match_runner.py").read_text(encoding="utf-8")
        freeze_source = source[source.index("def freeze("):source.index("def smoke(")]
        finalize_source = source[source.index("def finalize_shard("):source.index("def main(")]
        self.assertIn("LightGlue", freeze_source)
        self.assertLess(freeze_source.index("LightGlue"), freeze_source.index("core.freeze"))
        self.assertIn("core.canonicalize", source[source.index("def smoke("):source.index("def atomic_checkpoint(")])
        self.assertIn("atomic_write_csv", finalize_source)
        self.assertIn("atomic_write_json", finalize_source)

    def test_runner_command_uses_configured_colab_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.make_spec(root, "development_shard_001")
            paths = self.common.ExecutionPaths.from_roots(
                control_root=Path("/content/control"),
                image_root=Path("/content/images/assets"),
                result_root=Path("/content/drive/MyDrive/results"),
                export_root=Path("/content/drive/MyDrive/export"),
            )
            command = self.orchestrator.shard_command(
                python_executable="python3",
                paths=paths,
                spec=spec,
            )
        self.assertIn("/content/control/full_frame_local_match_runner.py", command)
        self.assertIn("/content/images/assets", command)
        self.assertIn("/content/drive/MyDrive/results/shards/development_shard_001", command)
        self.assertNotIn("/kaggle/", " ".join(command))

    def test_state_file_round_trip_is_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "execution_state.json"
            state = {
                "status": "IN_PROGRESS",
                "inventory_sha256": "a" * 64,
                "completed_shards": ["calibration_shard_006"],
                "pending_shards": ["calibration_shard_010"],
                "failed_shards": [],
            }
            self.orchestrator.write_state(path, state)
            recovered = self.orchestrator.read_state(path)
        self.assertEqual(recovered, state)

    def test_image_inventory_is_stable_and_fails_before_gpu_on_missing_asset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.make_spec(root, "development_shard_001")
            rows, _ = self.common.read_csv(spec.manifest_path)
            image_root = root / "images"
            image_root.mkdir()
            for filename in (rows[0]["left_asset_filename"], rows[0]["right_asset_filename"]):
                (image_root / filename).write_bytes(filename.encode("utf-8"))
            first = self.orchestrator.build_image_inventory([spec], image_root)
            second = self.orchestrator.build_image_inventory([spec], image_root)
            self.assertEqual(first["image_set_sha256"], second["image_set_sha256"])
            (image_root / rows[0]["left_asset_filename"]).unlink()
            with self.assertRaisesRegex(FileNotFoundError, "referenced image missing"):
                self.orchestrator.build_image_inventory([spec], image_root)

    def test_post_smoke_weight_inventory_detects_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "superpoint.pth").write_bytes(b"superpoint")
            (root / "lightglue.pth").write_bytes(b"lightglue")
            first = self.orchestrator.build_model_weight_inventory(root)
            (root / "lightglue.pth").write_bytes(b"changed")
            second = self.orchestrator.build_model_weight_inventory(root)
        self.assertEqual(first["weight_file_count"], 2)
        self.assertNotEqual(first["weight_set_sha256"], second["weight_set_sha256"])


class GlobalValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        import full_frame_execution_common as common
        import validate_full_frame_results as validator

        self.common = common
        self.validator = validator

    def make_spec(self, root: Path, shard_id: str, pair_ids: list[str]) -> object:
        manifest = root / "manifests" / f"{shard_id}.csv"
        digest = write_pair_manifest(manifest, pair_ids)
        return self.common.ShardSpec(
            shard_id=shard_id,
            role=shard_id.split("_shard_", 1)[0],
            manifest_path=manifest,
            pair_count=len(pair_ids),
            manifest_sha256=digest,
            pair_ids=tuple(pair_ids),
        )

    def test_accepts_structurally_complete_partial_shards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = [
                self.make_spec(root, "calibration_shard_001", ["pair_a"]),
                self.make_spec(root, "development_shard_001", ["pair_b"]),
            ]
            for spec in specs:
                write_synthetic_shard_result(root / "results" / spec.shard_id, spec, self.common)
            report = self.validator.validate_full_frame(specs, root / "results")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["expected_pair_count"], 2)
        self.assertEqual(report["observed_unique_pair_count"], 2)

    def test_rejects_missing_shard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = [
                self.make_spec(root, "calibration_shard_001", ["pair_a"]),
                self.make_spec(root, "calibration_shard_002", ["pair_b"]),
            ]
            write_synthetic_shard_result(root / "results" / specs[0].shard_id, specs[0], self.common)
            report = self.validator.validate_full_frame(specs, root / "results")
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("missing_shard_result", report["error_codes"])

    def test_rejects_duplicate_or_unexpected_pair_and_missing_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.make_spec(root, "confirmation_shard_001", ["pair_a", "pair_b"])
            write_synthetic_shard_result(
                root / "results" / spec.shard_id,
                spec,
                self.common,
                canonical_ids=["pair_a", "pair_x"],
                omit_direction=True,
            )
            report = self.validator.validate_full_frame([spec], root / "results")
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("canonical_pair_set_mismatch", report["error_codes"])
        self.assertIn("directional_pair_direction_mismatch", report["error_codes"])

    def test_rejects_mixed_execution_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = [
                self.make_spec(root, "calibration_shard_001", ["pair_a"]),
                self.make_spec(root, "development_shard_001", ["pair_b"]),
            ]
            write_synthetic_shard_result(root / "results" / specs[0].shard_id, specs[0], self.common, binding_token="one")
            write_synthetic_shard_result(root / "results" / specs[1].shard_id, specs[1], self.common, binding_token="two")
            report = self.validator.validate_full_frame(specs, root / "results")
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("mixed_execution_fingerprint", report["error_codes"])

    def test_rejects_shard_output_changed_after_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.make_spec(root, "calibration_shard_001", ["pair_a"])
            output = root / "results" / spec.shard_id
            write_synthetic_shard_result(output, spec, self.common)
            with (output / "directional_measurements.csv").open("a", encoding="utf-8") as handle:
                handle.write("\n")
            report = self.validator.validate_full_frame([spec], root / "results")
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("shard_output_checksum_mismatch", report["error_codes"])


class DeterministicMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        import full_frame_execution_common as common
        import merge_full_frame_results as merger
        import validate_full_frame_results as validator

        self.common = common
        self.merger = merger
        self.validator = validator

    def make_spec(self, root: Path, shard_id: str, pair_ids: list[str]) -> object:
        manifest = root / "manifests" / f"{shard_id}.csv"
        digest = write_pair_manifest(manifest, pair_ids)
        return self.common.ShardSpec(
            shard_id=shard_id,
            role=shard_id.split("_shard_", 1)[0],
            manifest_path=manifest,
            pair_count=len(pair_ids),
            manifest_sha256=digest,
            pair_ids=tuple(pair_ids),
        )

    def test_merge_follows_inventory_and_manifest_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = [
                self.make_spec(root, "development_shard_010", ["pair_b", "pair_a"]),
                self.make_spec(root, "calibration_shard_006", ["pair_c"]),
            ]
            for spec in specs:
                write_synthetic_shard_result(root / "results" / spec.shard_id, spec, self.common)
            validation = self.validator.validate_full_frame(specs, root / "results")
            audit = self.merger.merge_full_frame(
                specs,
                root / "results",
                root / "merged",
                validation,
            )
            canonical, fields = self.common.read_csv(root / "merged" / "canonical_measurements.csv")
            shard_index, shard_fields = self.common.read_csv(root / "merged" / "shard_audit_index.csv")
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(fields[:2], ["shard_id", "partition_role"])
        self.assertEqual([row["pair_execution_id"] for row in canonical], ["pair_b", "pair_a", "pair_c"])
        self.assertEqual(audit["canonical_row_count"], 3)
        self.assertEqual(audit["directional_row_count"], 6)
        self.assertEqual(shard_fields[:2], ["shard_id", "partition_role"])
        self.assertEqual([row["shard_id"] for row in shard_index], [
            "development_shard_010", "calibration_shard_006"
        ])

    def test_merge_refuses_failed_global_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "global validation PASS"):
                self.merger.merge_full_frame([], root / "results", root / "merged", {"status": "FAIL"})


class FinalExportBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        import build_final_export as exporter
        import full_frame_execution_common as common
        import merge_full_frame_results as merger
        import validate_full_frame_results as validator

        self.common = common
        self.exporter = exporter
        self.merger = merger
        self.validator = validator

    def prepare_execution(self, root: Path) -> tuple[object, list[object]]:
        control = root / "control"
        manifests = control / "public_pair_manifests"
        manifest = manifests / "calibration_shard_006.csv"
        digest = write_pair_manifest(manifest, ["pair_a"])
        inventory = [{
            "shard_id": "calibration_shard_006",
            "manifest_path": "public_pair_manifests/calibration_shard_006.csv",
            "pair_count": 1,
            "manifest_sha256": digest,
        }]
        (control / "shard_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        for name in (
            "full_frame_local_match_runner.py",
            "local_match_runner_v2.py",
            "local_match_execution_protocol_v2.json",
            "requirements.txt",
        ):
            (control / name).write_text(f"synthetic {name}\n", encoding="utf-8")
        paths = self.common.ExecutionPaths.from_roots(
            control_root=control,
            image_root=root / "images",
            result_root=root / "results",
            export_root=root / "exports",
        )
        specs = self.common.load_inventory(paths.inventory_path, paths.manifest_root)
        write_synthetic_shard_result(paths.shard_results_root / specs[0].shard_id, specs[0], self.common)
        (paths.shard_results_root / specs[0].shard_id / "pair_checkpoints").mkdir()
        paths.control_state_dir.mkdir(parents=True)
        environment = {"cuda": "synthetic"}
        for name, content in (
            ("matcher_freeze_record.json", {"status": "FROZEN", "environment": environment}),
            ("environment_report.json", environment),
            ("full_frame_smoke_test.json", {"status": "PASS"}),
            ("smoke_gate_binding.json", {}),
            ("execution_image_inventory.json", {"image_set_sha256": "synthetic_images"}),
            ("model_weight_inventory.json", {"weight_set_sha256": "synthetic_weights", "weights": [{"filename": "weights.pt"}]}),
            ("execution_state.json", {}),
        ):
            (paths.control_state_dir / name).write_text(json.dumps(content), encoding="utf-8")
        artifacts = {
            "inventory_sha256": hashlib.sha256(paths.inventory_path.read_bytes()).hexdigest(),
            "wrapper_sha256": hashlib.sha256(paths.runner_path.read_bytes()).hexdigest(),
            "core_runner_sha256": hashlib.sha256((control / "local_match_runner_v2.py").read_bytes()).hexdigest(),
            "protocol_sha256": hashlib.sha256((control / "local_match_execution_protocol_v2.json").read_bytes()).hexdigest(),
            "freeze_record_sha256": hashlib.sha256((paths.control_state_dir / "matcher_freeze_record.json").read_bytes()).hexdigest(),
            "image_set_sha256": "synthetic_images",
            "weight_set_sha256": "synthetic_weights",
        }
        fingerprint = hashlib.sha256(json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        shard_dir = paths.shard_results_root / specs[0].shard_id
        (shard_dir / "shard_execution_binding.json").write_text(json.dumps({
            "binding_version": "pferi_v2_shard_execution_binding_v1", "shard_id": specs[0].shard_id,
            "pair_manifest_sha256": specs[0].manifest_sha256, "execution_fingerprint": fingerprint, **artifacts,
        }), encoding="utf-8")
        checksum_targets = self.common.SHARD_OUTPUT_HASH_FILES
        (shard_dir / "shard_output_checksums.json").write_text(json.dumps({
            "checksum_version": "pferi_v2_shard_output_checksums_v1",
            "files": {name: hashlib.sha256((shard_dir / name).read_bytes()).hexdigest() for name in checksum_targets},
        }), encoding="utf-8")
        smoke_path = paths.control_state_dir / "full_frame_smoke_test.json"
        (paths.control_state_dir / "smoke_gate_binding.json").write_text(json.dumps({
            "binding_version": "pferi_v2_smoke_gate_binding_v1",
            "pair_manifest_sha256": specs[0].manifest_sha256,
            "execution_fingerprint": fingerprint,
            "smoke_report_sha256": hashlib.sha256(smoke_path.read_bytes()).hexdigest(),
        }), encoding="utf-8")
        (paths.control_state_dir / "execution_state.json").write_text(json.dumps({
            "status": "RUN_COMPLETE", "run_mode": "fresh_full_inventory",
            "declared_shards": [specs[0].shard_id], "inventory_sha256": artifacts["inventory_sha256"],
            "execution_fingerprint": fingerprint,
        }), encoding="utf-8")
        validation = self.validator.validate_full_execution(specs, paths)
        self.validator.write_validation_outputs(validation, paths.validation_root)
        self.merger.merge_full_frame(specs, paths.shard_results_root, paths.merged_root, validation)
        return paths, specs

    def test_builds_one_integrity_checked_zip_without_images_or_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, specs = self.prepare_execution(root)
            audit = self.exporter.build_final_export(paths, specs)
            with zipfile.ZipFile(paths.final_export_zip) as archive:
                names = archive.namelist()
                self.assertIn("PF_ERI_FINAL_EXPORT/FINAL_EXPORT_AUDIT.json", names)
                self.assertIn("PF_ERI_FINAL_EXPORT/EXECUTION_SUMMARY.md", names)
                checksum_lines = archive.read("PF_ERI_FINAL_EXPORT/CHECKSUMS.sha256").decode().splitlines()
                for line in checksum_lines:
                    digest, relative = line.split("  ", 1)
                    self.assertEqual(hashlib.sha256(archive.read(relative)).hexdigest(), digest)
            delivered_files = sorted(path.name for path in paths.export_root.iterdir())
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(delivered_files, ["PF_ERI_FINAL_EXPORT.zip"])
        self.assertTrue(all("pair_checkpoints" not in name for name in names))
        self.assertTrue(all(not name.lower().endswith((".jpg", ".jpeg", ".png")) for name in names))
        self.assertIn("PF_ERI_FINAL_EXPORT/merged/canonical_measurements.csv", names)
        self.assertIn("PF_ERI_FINAL_EXPORT/validation/full_frame_validation.json", names)

    def test_refuses_export_when_validation_is_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, specs = self.prepare_execution(root)
            (paths.validation_root / "full_frame_validation.json").write_text(
                json.dumps({"status": "FAIL"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "validation PASS"):
                self.exporter.build_final_export(paths, specs)

    def test_refuses_export_while_batch_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, specs = self.prepare_execution(root)
            (paths.control_state_dir / "execution_state.json").write_text(
                json.dumps({"status": "BATCH_COMPLETE"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "not export-eligible"):
                self.exporter.build_final_export(paths, specs)

    def test_refuses_export_when_execution_control_fingerprint_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, specs = self.prepare_execution(root)
            (paths.control_state_dir / "execution_state.json").write_text(
                json.dumps({"status": "RUN_COMPLETE"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "execution control"):
                self.exporter.build_final_export(paths, specs)


if __name__ == "__main__":
    unittest.main()
