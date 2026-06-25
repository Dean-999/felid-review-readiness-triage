#!/usr/bin/env python3
"""Package Phase 16E streaming model-filtering inputs for Colab.

This package is URL-first / remote-source-first. It does not copy images, create
zip shards, or stage the CzechLynx local image tree. Rows that only have a local
Mac path are preserved as unavailable-local-path records so the cloud runner can
fail them cleanly and continue.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    PROJECT_ROOT
    / "outputs/phase16/expanded_high_confidence_candidate_pool/phase16_expanded_high_confidence_candidate_manifest.csv"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/phase16e_candidate_model_filter_colab_package"
MANIFEST_OUT = OUTPUT_DIR / "phase16e_candidate_model_filter_manifest.csv"
CONFIG_OUT = OUTPUT_DIR / "phase16e_candidate_model_filter_config.json"
RUNNER_OUT = OUTPUT_DIR / "run_phase16e_candidate_model_filter_colab.py"
README_OUT = OUTPUT_DIR / "README_PHASE16E_COLAB.md"

EXPECTED_ROWS = 46_172
EXPECTED_COUNTS = {
    "urban_bobcat_high_confidence": 6_412,
    "wild_czechlynx_high_confidence": 39_760,
}

SENSITIVE_COLUMNS = {
    "unique_name",
    "identity_label",
    "identity",
    "individual_id",
    "individual",
    "animal_id",
    "lynx_id",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "encounter",
    "date",
    "source",
}

URL_COLUMNS = ["download_url", "image_url", "url", "remote_uri", "phase16_image_uri", "azure_url"]
DRIVE_PREFIXES = ("gdrive://", "drive://", "/content/drive/", "MyDrive/", "GoogleDrive/")

KEEP_COLUMNS = [
    "source_name",
    "target_quadrant",
    "species_label",
    "scientific_name",
    "environment_axis",
    "candidate_role",
    "source_priority",
    "image_key",
    "has_detector_geometry",
    "needs_detector_or_pose",
    "md_best_confidence",
    "md_area_fraction",
    "md_width_fraction",
    "md_height_fraction",
    "md_aspect_ratio",
    "md_edge_touch",
    "prefilter_score",
    "already_in_current_high_final",
]


def is_url(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"}


def is_drive_path(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    return bool(text) and text.startswith(DRIVE_PREFIXES)


def first_value(row: pd.Series, columns: list[str], predicate) -> str:
    for column in columns:
        if column not in row:
            continue
        value = row[column]
        if predicate(value):
            return str(value).strip()
    return ""


def infer_source_mode(row: pd.Series) -> tuple[str, str, str]:
    url = first_value(row, URL_COLUMNS, is_url)
    if url:
        return "url", url, ""

    drive = first_value(row, ["remote_uri", "phase16_image_uri", "local_image_path"], is_drive_path)
    if drive:
        return "drive_path", drive, ""

    for column in ["local_image_path", "phase16_image_uri"]:
        if column in row and not pd.isna(row[column]):
            value = str(row[column]).strip()
            if value.startswith("/Users/"):
                return "unavailable_local_path", "", value

    return "missing_source", "", ""


def build_manifest(df: pd.DataFrame) -> pd.DataFrame:
    leaked = sorted(SENSITIVE_COLUMNS.intersection(df.columns))
    if leaked:
        raise ValueError(f"Input unexpectedly contains sensitive columns: {leaked}")

    out = pd.DataFrame()
    out["candidate_id"] = [
        f"p16e_{index:06d}" for index in range(1, len(df) + 1)
    ]
    out["phase16_expanded_candidate_index"] = df["phase16_expanded_candidate_index"]
    for column in KEEP_COLUMNS:
        out[column] = df[column] if column in df.columns else ""

    source_modes = df.apply(infer_source_mode, axis=1, result_type="expand")
    out["source_mode"] = source_modes[0]
    out["image_uri"] = source_modes[1]
    out["local_path_original"] = source_modes[2]

    out["phase16e_model_filter_status"] = "pending_streaming_filter"
    out["selection_eligible_pre_model"] = out["source_mode"].isin({"url", "drive_path"})
    return out


def write_config(manifest: pd.DataFrame) -> None:
    config = {
        "phase": "16E",
        "pipeline": "url_first_remote_source_first_streaming_model_filtering",
        "input_manifest": str(INPUT),
        "output_manifest": str(MANIFEST_OUT),
        "expected_rows": EXPECTED_ROWS,
        "expected_counts": EXPECTED_COUNTS,
        "output_dir_default": "outputs/phase16/phase16e_candidate_model_filter",
        "debug_sample_limit": 80,
        "models": {
            "iqa_models": ["musiq", "topiq_nr", "brisque"],
            "viewpoint_model": "open_clip ViT-B-32 laion2b_s34b_b79k",
            "detector_or_pose": "optional_for_rows_without_detector_geometry",
            "enable_superanimal_pose": False,
            "pose_model_name": "superanimal_quadruped_hrnetw32",
            "pose_failure_is_fatal": False,
            "pose_min_keypoint_confidence": 0.30,
            "pose_min_valid_keypoint_fraction": 0.35,
        },
        "enable_superanimal_pose": False,
        "pose_model_name": "superanimal_quadruped_hrnetw32",
        "pose_failure_is_fatal": False,
        "pose_min_keypoint_confidence": 0.30,
        "pose_min_valid_keypoint_fraction": 0.35,
        "selection_boundary": [
            "Do not freeze final 3000 in Phase 16E.",
            "Do not use simple top-3000.",
            "Phase 16E only streams images, scores/filter-signals, and records failures.",
        ],
        "source_mode_counts": {
            str(key): int(value)
            for key, value in manifest["source_mode"].value_counts().sort_index().items()
        },
        "claim_boundary": (
            "streaming model filtering package only; final high-confidence selection "
            "requires constrained selection and manual calibration"
        ),
    }
    CONFIG_OUT.write_text(json.dumps(config, indent=2), encoding="utf-8")


def write_runner() -> None:
    RUNNER_OUT.write_text(
        r'''#!/usr/bin/env python3
"""Run Phase 16E streaming candidate model filtering in Colab/Kaggle.

This runner never persists all source images or all crops. URL images are
downloaded one at a time to a temporary file, scored, and then deleted.
Unavailable local Mac paths are recorded as failures and do not stop the run.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
from PIL import Image
from tqdm import tqdm


VIEW_PROMPTS = {
    "left_side": "a clear left side profile photo of a bobcat or lynx showing its flank",
    "right_side": "a clear right side profile photo of a bobcat or lynx showing its flank",
    "frontal": "a frontal photo of a bobcat or lynx facing the camera",
    "rear": "a rear view photo of a bobcat or lynx facing away from the camera",
    "partial_or_occluded": "a partial or occluded camera trap photo of a bobcat or lynx",
    "unclear": "a blurry unclear camera trap photo where the animal viewpoint is uncertain",
}

SENSITIVE_COLUMNS = {
    "unique_name",
    "identity_label",
    "identity",
    "individual_id",
    "individual",
    "animal_id",
    "lynx_id",
    "latitude",
    "longitude",
    "trap_id",
    "location",
    "cell_code",
    "encounter",
    "date",
    "source",
}

POSE_OUTPUT_COLUMNS = [
    "pose_enabled",
    "pose_model_name",
    "pose_success",
    "pose_failure_reason",
    "pose_num_keypoints",
    "pose_mean_keypoint_confidence",
    "pose_valid_keypoint_fraction",
    "pose_body_coverage_score",
    "pose_orientation_proxy",
    "pose_side_view_proxy",
    "pose_front_rear_proxy",
    "pose_partial_body_proxy",
    "pose_quality_score",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="phase16e_candidate_model_filter_manifest.csv")
    parser.add_argument("--output-dir", default="outputs/phase16/phase16e_candidate_model_filter")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--iqa-models", default="musiq,topiq_nr,brisque")
    parser.add_argument("--clip-model", default="ViT-B-32")
    parser.add_argument("--clip-pretrained", default="laion2b_s34b_b79k")
    parser.add_argument("--allow-missing-models", action="store_true")
    parser.add_argument("--debug-sample-limit", type=int, default=80)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--target-quadrant", default="")
    parser.add_argument("--source-mode", default="")
    parser.add_argument("--enable-superanimal-pose", action="store_true")
    parser.add_argument("--pose-model-name", default="superanimal_quadruped_hrnetw32")
    parser.add_argument("--pose-device", default="")
    parser.add_argument("--pose-failure-is-fatal", type=str_to_bool, default=False)
    parser.add_argument("--pose-min-keypoint-confidence", type=float, default=0.30)
    parser.add_argument("--pose-min-valid-keypoint-fraction", type=float, default=0.35)
    return parser.parse_args()


def str_to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected true/false, got {value!r}")


def load_iqa_models(names: list[str], device: str, allow_missing_models: bool = False) -> dict:
    try:
        import pyiqa
    except Exception as exc:
        message = f"pyiqa unavailable: {exc}"
        if allow_missing_models:
            print(f"WARNING {message}")
            return {}
        raise RuntimeError(message) from exc

    models = {}
    for name in names:
        name = name.strip()
        if not name:
            continue
        try:
            models[name] = pyiqa.create_metric(name, device=device)
            print(f"loaded IQA model: {name}")
        except Exception as exc:
            message = f"IQA model load failed for {name}: {exc}"
            if allow_missing_models:
                print(f"WARNING {message}")
                continue
            raise RuntimeError(message) from exc
    if not models:
        message = "No IQA models loaded."
        if allow_missing_models:
            print(f"WARNING {message}")
            return {}
        raise RuntimeError(message)
    return models


def load_clip(model_name: str, pretrained: str, device: str, allow_missing_models: bool = False):
    try:
        import open_clip
        import torch
    except Exception as exc:
        message = f"open_clip unavailable: {exc}"
        if allow_missing_models:
            print(f"WARNING {message}")
            return None
        raise RuntimeError(message) from exc

    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
            device=device,
        )
        tokenizer = open_clip.get_tokenizer(model_name)
        labels = list(VIEW_PROMPTS)
        prompts = [VIEW_PROMPTS[label] for label in labels]
        with torch.no_grad():
            text = tokenizer(prompts).to(device)
            text_features = model.encode_text(text)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        print(f"loaded CLIP model: {model_name} {pretrained}")
        return model, preprocess, labels, text_features
    except Exception as exc:
        message = f"CLIP load failed: {exc}"
        if allow_missing_models:
            print(f"WARNING {message}")
            return None
        raise RuntimeError(message) from exc


def load_superanimal_pose(args: argparse.Namespace):
    if not args.enable_superanimal_pose:
        return None
    try:
        import deeplabcut as dlc
    except Exception as exc:
        raise RuntimeError(
            "SuperAnimal pose requested but DeepLabCut is unavailable. "
            "Install a compatible DeepLabCut/SuperAnimal environment or rerun "
            "without --enable-superanimal-pose."
        ) from exc
    try:
        import imageio.v2 as imageio
    except Exception as exc:
        raise RuntimeError(
            "SuperAnimal pose requested but imageio is unavailable. "
            "Install imageio or rerun without --enable-superanimal-pose."
        ) from exc

    infer_fn = getattr(dlc, "video_inference_superanimal", None)
    if infer_fn is None:
        raise RuntimeError(
            "DeepLabCut is installed, but video_inference_superanimal was not found. "
            "Use a DeepLabCut version with SuperAnimal model-zoo inference or rerun "
            "without --enable-superanimal-pose."
        )
    print(f"loaded optional SuperAnimal pose adapter: {args.pose_model_name} on {args.pose_device}")
    return {"dlc": dlc, "imageio": imageio, "infer_fn": infer_fn}


def download_url(uri: str, tmp_dir: Path, candidate_id: str) -> Path:
    suffix = Path(uri.split("?")[0]).suffix or ".jpg"
    out = tmp_dir / f"{candidate_id}{suffix}"
    request = Request(uri, headers={"User-Agent": "phase16e-streaming-filter/1.0"})
    with urlopen(request, timeout=30) as response:
        out.write_bytes(response.read())
    return out


def resolve_image(row: pd.Series, tmp_dir: Path) -> tuple[Path | None, str]:
    mode = str(row.get("source_mode", ""))
    if mode == "url":
        try:
            return download_url(str(row["image_uri"]), tmp_dir, str(row["candidate_id"])), ""
        except Exception as exc:
            return None, f"url_download_failed:{exc}"
    if mode in {"drive_path", "drive_extracted_path", "packaged_local"}:
        path = Path(str(row["image_uri"]))
        if path.exists():
            return path, ""
        return None, f"{mode}_not_found"
    if mode == "unavailable_local_path":
        return None, "source_not_cloud_accessible"
    return None, f"unsupported_source_mode:{mode}"


def crop_by_detector(image: Image.Image, row: pd.Series, padding: float = 0.08) -> Image.Image:
    keys = ["md_x0", "md_y0", "md_x1", "md_y1"]
    if not all(key in row for key in keys):
        return image
    values = []
    for key in keys:
        try:
            value = float(row.get(key))
        except (TypeError, ValueError):
            return image
        if math.isnan(value):
            return image
        values.append(value)
    x0, y0, x1, y1 = values
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        return image
    width, height = image.size
    dx = (x1 - x0) * padding
    dy = (y1 - y0) * padding
    box = (
        max(0, int((x0 - dx) * width)),
        max(0, int((y0 - dy) * height)),
        min(width, int((x1 + dx) * width)),
        min(height, int((y1 + dy) * height)),
    )
    if box[2] - box[0] < 32 or box[3] - box[1] < 32:
        return image
    return image.crop(box)


def score_iqa(models: dict, crop: Image.Image, tmp_dir: Path, candidate_id: str) -> dict:
    scores = {}
    if not models:
        return scores
    crop_path = tmp_dir / f"{candidate_id}_crop_tmp.jpg"
    crop.convert("RGB").save(crop_path, quality=95)
    try:
        for name, model in models.items():
            try:
                value = model(str(crop_path))
                scores[f"iqa_{name}_crop_score"] = float(value.detach().cpu().reshape(-1)[0])
            except Exception as exc:
                scores[f"iqa_{name}_crop_score"] = None
                scores[f"iqa_{name}_error"] = str(exc)
    finally:
        crop_path.unlink(missing_ok=True)
    return scores


def score_clip(clip_bundle, crop: Image.Image, device: str) -> dict:
    if clip_bundle is None:
        return {}
    import torch

    model, preprocess, labels, text_features = clip_bundle
    with torch.no_grad():
        tensor = preprocess(crop.convert("RGB")).unsqueeze(0).to(device)
        image_features = model.encode_image(tensor)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)[0].cpu()
    best_idx = int(probs.argmax())
    out = {
        "clip_viewpoint_label": labels[best_idx],
        "clip_viewpoint_confidence": float(probs[best_idx]),
    }
    for label, prob in zip(labels, probs):
        out[f"clip_viewpoint_prob_{label}"] = float(prob)
    return out


def default_pose_result(args: argparse.Namespace) -> dict:
    return {
        "pose_enabled": bool(args.enable_superanimal_pose),
        "pose_model_name": args.pose_model_name if args.enable_superanimal_pose else "",
        "pose_success": False,
        "pose_failure_reason": "pose_disabled" if not args.enable_superanimal_pose else "",
        "pose_num_keypoints": 0,
        "pose_mean_keypoint_confidence": None,
        "pose_valid_keypoint_fraction": None,
        "pose_body_coverage_score": None,
        "pose_orientation_proxy": None,
        "pose_side_view_proxy": None,
        "pose_front_rear_proxy": None,
        "pose_partial_body_proxy": None,
        "pose_quality_score": None,
    }


def parse_pose_model_name(raw_name: str) -> tuple[str, str]:
    text = (raw_name or "superanimal_quadruped_hrnetw32").strip()
    if text.startswith("superanimal_"):
        parts = text.split("_")
        if len(parts) >= 3:
            superanimal_name = "_".join(parts[:2])
            model_name = "_".join(parts[2:])
            if model_name == "hrnetw32":
                model_name = "hrnet_w32"
            return superanimal_name, model_name
    return "superanimal_quadruped", text


def extract_keypoints_from_dataframe(df: pd.DataFrame) -> list[tuple[float, float, float]]:
    if df.empty:
        return []
    frame = df.iloc[0]
    points = []
    if isinstance(df.columns, pd.MultiIndex):
        columns = df.columns
        keypoint_levels = max(0, columns.nlevels - 2)
        grouped = {}
        for column, value in frame.items():
            coord = str(column[-1]).lower()
            if coord not in {"x", "y", "likelihood", "confidence", "score"}:
                continue
            key = tuple(column[:keypoint_levels]) if keypoint_levels else tuple(column[:-1])
            grouped.setdefault(key, {})[coord] = value
        for values in grouped.values():
            if "x" in values and "y" in values:
                conf = values.get("likelihood", values.get("confidence", values.get("score", 1.0)))
                points.append((float(values["x"]), float(values["y"]), float(conf)))
    else:
        columns = [str(c) for c in df.columns]
        for column in columns:
            if not column.endswith("_x"):
                continue
            base = column[:-2]
            y_col = f"{base}_y"
            conf_col = f"{base}_likelihood"
            if y_col in df.columns:
                conf = frame[conf_col] if conf_col in df.columns else 1.0
                points.append((float(frame[column]), float(frame[y_col]), float(conf)))
    return [
        point for point in points
        if all(pd.notna(value) and math.isfinite(float(value)) for value in point)
    ]


def collect_pose_keypoints(work_dir: Path, payload) -> list[tuple[float, float, float]]:
    if isinstance(payload, pd.DataFrame):
        points = extract_keypoints_from_dataframe(payload)
        if points:
            return points

    h5_files = sorted(work_dir.rglob("*.h5"), key=lambda path: path.stat().st_mtime, reverse=True)
    for h5_file in h5_files:
        try:
            points = extract_keypoints_from_dataframe(pd.read_hdf(h5_file))
            if points:
                return points
        except Exception:
            continue

    csv_files = sorted(work_dir.rglob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True)
    for csv_file in csv_files:
        try:
            points = extract_keypoints_from_dataframe(pd.read_csv(csv_file, header=[0, 1, 2]))
            if points:
                return points
        except Exception:
            try:
                points = extract_keypoints_from_dataframe(pd.read_csv(csv_file))
                if points:
                    return points
            except Exception:
                continue
    return []


def summarize_pose_keypoints(
    keypoints: list[tuple[float, float, float]],
    crop: Image.Image,
    args: argparse.Namespace,
) -> dict:
    out = default_pose_result(args)
    out["pose_failure_reason"] = ""
    out["pose_num_keypoints"] = len(keypoints)
    if not keypoints:
        out["pose_failure_reason"] = "pose_no_keypoints_parsed"
        return out

    confidences = [max(0.0, min(1.0, float(point[2]))) for point in keypoints]
    valid = [
        point for point, confidence in zip(keypoints, confidences)
        if confidence >= args.pose_min_keypoint_confidence
    ]
    valid_fraction = len(valid) / len(keypoints) if keypoints else 0.0
    mean_confidence = sum(confidences) / len(confidences)
    out["pose_mean_keypoint_confidence"] = mean_confidence
    out["pose_valid_keypoint_fraction"] = valid_fraction

    if not valid:
        out["pose_failure_reason"] = "pose_no_valid_keypoints"
        return out

    xs = [float(point[0]) for point in valid]
    ys = [float(point[1]) for point in valid]
    width, height = max(1, crop.width), max(1, crop.height)
    x_span = max(xs) - min(xs)
    y_span = max(ys) - min(ys)
    x_span_norm = max(0.0, min(1.0, x_span / width))
    y_span_norm = max(0.0, min(1.0, y_span / height))
    bbox_area = x_span_norm * y_span_norm
    coverage = max(0.0, min(1.0, math.sqrt(bbox_area) * 1.8))
    orientation_ratio = x_span_norm / max(y_span_norm, 1e-6)
    side_proxy = max(0.0, min(1.0, (orientation_ratio - 0.55) / 1.45))
    front_rear_proxy = 1.0 - side_proxy
    partial_proxy = 1.0 - max(0.0, min(1.0, 0.55 * valid_fraction + 0.45 * coverage))
    pose_quality = max(
        0.0,
        min(1.0, 0.40 * mean_confidence + 0.35 * valid_fraction + 0.25 * coverage),
    )

    out.update(
        {
            "pose_success": bool(
                valid_fraction >= args.pose_min_valid_keypoint_fraction
                and pose_quality > 0
            ),
            "pose_body_coverage_score": coverage,
            "pose_orientation_proxy": orientation_ratio,
            "pose_side_view_proxy": side_proxy,
            "pose_front_rear_proxy": front_rear_proxy,
            "pose_partial_body_proxy": partial_proxy,
            "pose_quality_score": pose_quality,
        }
    )
    if not out["pose_success"]:
        out["pose_failure_reason"] = "pose_valid_keypoint_fraction_below_threshold"
    return out


def score_superanimal_pose(pose_bundle, crop: Image.Image, tmp_dir: Path, candidate_id: str, args: argparse.Namespace) -> dict:
    out = default_pose_result(args)
    if not args.enable_superanimal_pose:
        return out
    if pose_bundle is None:
        out["pose_failure_reason"] = "pose_bundle_unavailable"
        return out
    work_dir = tmp_dir / f"{candidate_id}_pose"
    work_dir.mkdir(parents=True, exist_ok=True)
    image_path = work_dir / f"{candidate_id}_pose_input.jpg"
    video_path = work_dir / f"{candidate_id}_pose_input.mp4"
    try:
        crop.convert("RGB").save(image_path, quality=95)
        pose_bundle["imageio"].mimsave(video_path, [crop.convert("RGB")], fps=1)
        superanimal_name, model_name = parse_pose_model_name(args.pose_model_name)
        payload = pose_bundle["infer_fn"](
            [str(video_path)],
            superanimal_name=superanimal_name,
            model_name=model_name,
            video_adapt=False,
            destfolder=str(work_dir),
            scale_list=[1],
        )
        keypoints = collect_pose_keypoints(work_dir, payload)
        return summarize_pose_keypoints(keypoints, crop, args)
    except TypeError:
        try:
            payload = pose_bundle["infer_fn"](
                [str(video_path)],
                args.pose_model_name,
                destfolder=str(work_dir),
            )
            keypoints = collect_pose_keypoints(work_dir, payload)
            return summarize_pose_keypoints(keypoints, crop, args)
        except Exception as exc:
            out["pose_failure_reason"] = f"pose_inference_failed:{exc}"
            return out
    except Exception as exc:
        out["pose_failure_reason"] = f"pose_inference_failed:{exc}"
        return out


def safe_float(value, default=None):
    try:
        if value is None or pd.isna(value):
            return default
        value = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return value


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def compute_final_candidate_score(result: dict, args: argparse.Namespace) -> dict:
    topiq = safe_float(result.get("iqa_topiq_nr_crop_score"))
    musiq = safe_float(result.get("iqa_musiq_crop_score"))
    brisque = safe_float(result.get("iqa_brisque_crop_score"))
    iqa_parts = []
    if topiq is not None:
        iqa_parts.append(clamp01(topiq if topiq <= 1.5 else topiq / 100.0))
    if musiq is not None:
        iqa_parts.append(clamp01(musiq / 100.0))
    if brisque is not None:
        iqa_parts.append(clamp01(1.0 - brisque / 100.0))
    iqa_quality = sum(iqa_parts) / len(iqa_parts) if iqa_parts else None

    clip_side = (
        safe_float(result.get("clip_viewpoint_prob_left_side"), 0.0)
        + safe_float(result.get("clip_viewpoint_prob_right_side"), 0.0)
    )
    clip_side = clamp01(clip_side)
    md_area = safe_float(result.get("md_area_fraction"), 0.0)
    md_geometry = clamp01(md_area / 0.20) if md_area is not None else 0.0
    available_parts = [
        (0.45, iqa_quality),
        (0.35, clip_side),
        (0.20, md_geometry),
    ]
    used_weight = sum(weight for weight, value in available_parts if value is not None)
    base_score = (
        sum(weight * value for weight, value in available_parts if value is not None) / used_weight
        if used_weight > 0
        else None
    )

    pose_quality = safe_float(result.get("pose_quality_score"))
    pose_success = bool(result.get("pose_success", False))
    if pose_success and pose_quality is not None and base_score is not None:
        final_score = 0.75 * base_score + 0.25 * pose_quality
        fallback_used = False
    else:
        final_score = base_score
        fallback_used = bool(args.enable_superanimal_pose)

    return {
        "iqa_quality_proxy_score": iqa_quality,
        "clip_side_view_score": clip_side,
        "md_geometry_score": md_geometry,
        "base_candidate_score": base_score,
        "pose_fallback_scoring_used": fallback_used,
        "final_candidate_score": final_score,
    }


def selection_eligible(result: dict, args: argparse.Namespace) -> bool:
    if not result.get("image_load_success", False):
        return False
    if args.enable_superanimal_pose and args.pose_failure_is_fatal and not result.get("pose_success", False):
        return False
    label = str(result.get("clip_viewpoint_label", ""))
    if label in {"frontal", "rear", "partial_or_occluded", "unclear"}:
        return False
    if float(result.get("clip_viewpoint_confidence") or 0) < 0.30:
        return False
    md_area = result.get("md_area_fraction")
    try:
        if md_area is not None and not pd.isna(md_area) and float(md_area) < 0.08:
            return False
    except (TypeError, ValueError):
        pass
    return True


def series_to_markdown(series: pd.Series) -> str:
    lines = ["| value | count |", "| --- | ---: |"]
    for key, value in series.items():
        lines.append(f"| {key} | {int(value)} |")
    return "\n".join(lines)


def write_summary(scores: pd.DataFrame, output_dir: Path) -> None:
    lines = [
        "# Phase 16E Candidate Model Filter Summary",
        "",
        f"Rows: {len(scores)}",
        "",
        "## Source Mode",
        "",
        series_to_markdown(scores["source_mode"].value_counts(dropna=False)),
        "",
        "## Image Load Success",
        "",
        series_to_markdown(scores["image_load_success"].value_counts(dropna=False)),
        "",
        "## Selection Eligible",
        "",
        series_to_markdown(scores["selection_eligible"].value_counts(dropna=False)),
        "",
        "## Scoring Valid For Selection",
        "",
        series_to_markdown(scores["scoring_valid_for_selection"].value_counts(dropna=False))
        if "scoring_valid_for_selection" in scores
        else "Column missing.",
        "",
        "## Model Fallback Mode",
        "",
        series_to_markdown(scores["model_fallback_mode"].value_counts(dropna=False))
        if "model_fallback_mode" in scores
        else "Column missing.",
        "",
        "## Final Candidate Score",
        "",
        f"Numeric rows: {int(pd.to_numeric(scores.get('final_candidate_score'), errors='coerce').notna().sum())}",
        "",
        "## Claim Boundary",
        "",
        "Phase 16E only streams and scores candidates. It does not freeze final 3000 sets.",
        "",
    ]
    if "pose_enabled" in scores and bool(scores["pose_enabled"].fillna(False).any()):
        lines.extend(
            [
                "## Optional SuperAnimal Pose",
                "",
                "Pose is used only as a structural evidence proxy for completeness and viewpoint pre-calibration.",
                "",
                "### Pose Success",
                "",
                series_to_markdown(scores["pose_success"].value_counts(dropna=False)),
                "",
                "### Pose Failure Reasons",
                "",
                series_to_markdown(scores["pose_failure_reason"].fillna("").value_counts(dropna=False)),
                "",
            ]
        )
    (output_dir / "phase16e_candidate_model_filter_summary.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    if not args.pose_device:
        args.pose_device = args.device
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug_samples"
    debug_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="phase16e_stream_"))

    manifest = pd.read_csv(args.manifest, low_memory=False)
    if args.target_quadrant:
        manifest = manifest[manifest["target_quadrant"].astype(str) == args.target_quadrant].copy()
    if args.source_mode:
        manifest = manifest[manifest["source_mode"].astype(str) == args.source_mode].copy()
    if args.limit and args.limit > 0:
        manifest = manifest.head(args.limit).copy()

    iqa_models = load_iqa_models(
        args.iqa_models.split(","),
        args.device,
        allow_missing_models=args.allow_missing_models,
    )
    clip_bundle = load_clip(
        args.clip_model,
        args.clip_pretrained,
        args.device,
        allow_missing_models=args.allow_missing_models,
    )
    model_fallback_mode = bool(args.allow_missing_models and (not iqa_models or clip_bundle is None))
    model_dependency_ready = bool(iqa_models and clip_bundle is not None and not model_fallback_mode)
    pose_bundle = None
    pose_load_failure_reason = ""
    if args.enable_superanimal_pose:
        try:
            pose_bundle = load_superanimal_pose(args)
        except Exception as exc:
            pose_load_failure_reason = str(exc)
            print(f"WARNING optional SuperAnimal pose unavailable: {exc}")

    rows = []
    debug_saved = 0
    try:
        for _, row in tqdm(manifest.iterrows(), total=len(manifest)):
            result = row.to_dict()
            image_path, error = resolve_image(row, tmp_dir)
            result["image_load_success"] = image_path is not None
            result["rejection_reason"] = error
            result.update(default_pose_result(args))
            if image_path is None and args.enable_superanimal_pose:
                result["pose_failure_reason"] = "image_not_loaded"
            if image_path is not None:
                try:
                    image = Image.open(image_path).convert("RGB")
                    crop = crop_by_detector(image, row)
                    result["image_width"] = image.width
                    result["image_height"] = image.height
                    result["crop_width"] = crop.width
                    result["crop_height"] = crop.height
                    result.update(score_iqa(iqa_models, crop, tmp_dir, str(row["candidate_id"])))
                    result.update(score_clip(clip_bundle, crop, args.device))
                    if args.enable_superanimal_pose:
                        pose_result = score_superanimal_pose(
                            pose_bundle,
                            crop,
                            tmp_dir,
                            str(row["candidate_id"]),
                            args,
                        )
                        if pose_load_failure_reason and not pose_result.get("pose_success", False):
                            pose_result["pose_failure_reason"] = (
                                f"pose_module_unavailable:{pose_load_failure_reason}"
                            )
                        result.update(pose_result)
                        if args.pose_failure_is_fatal and not pose_result.get("pose_success", False):
                            result["rejection_reason"] = pose_result.get("pose_failure_reason") or "pose_failed"
                    if debug_saved < args.debug_sample_limit:
                        crop.save(debug_dir / f"{row['candidate_id']}_debug_crop.jpg", quality=90)
                        debug_saved += 1
                except Exception as exc:
                    result["image_load_success"] = False
                    result["rejection_reason"] = f"model_or_image_error:{exc}"
                finally:
                    if str(row.get("source_mode")) == "url":
                        Path(image_path).unlink(missing_ok=True)
            result.update(compute_final_candidate_score(result, args))
            result["model_fallback_mode"] = model_fallback_mode
            result["scoring_valid_for_selection"] = bool(
                result.get("image_load_success", False)
                and model_dependency_ready
                and result.get("final_candidate_score") is not None
                and result.get("iqa_quality_proxy_score") is not None
                and result.get("clip_side_view_score") is not None
            )
            result["selection_eligible"] = selection_eligible(result, args)
            rows.append(result)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    scores = pd.DataFrame(rows)
    scores_path = output_dir / "phase16e_candidate_model_filter_scores.csv"
    scores.to_csv(scores_path, index=False)
    write_summary(scores, output_dir)

    audit = {
        "manifest": args.manifest,
        "scores_output": str(scores_path),
        "manifest_rows": int(len(manifest)),
        "candidate_id_unique": bool(manifest["candidate_id"].is_unique),
        "target_counts": {
            str(key): int(value)
            for key, value in manifest["target_quadrant"].value_counts(dropna=False).sort_index().items()
        },
        "source_mode_counts": {
            str(key): int(value)
            for key, value in manifest["source_mode"].value_counts(dropna=False).sort_index().items()
        },
        "scores_output_exists": scores_path.exists(),
        "image_load_success_counts": {
            str(key): int(value)
            for key, value in scores["image_load_success"].value_counts(dropna=False).sort_index().items()
        },
        "selection_eligible_counts": {
            str(key): int(value)
            for key, value in scores["selection_eligible"].value_counts(dropna=False).sort_index().items()
        },
        "pose_enabled": bool(args.enable_superanimal_pose),
        "pose_columns_exist": bool(all(column in scores.columns for column in POSE_OUTPUT_COLUMNS)),
        "pose_success_rate": (
            float(scores["pose_success"].fillna(False).mean())
            if args.enable_superanimal_pose and "pose_success" in scores
            else None
        ),
        "pose_failure_reason_counts": (
            {
                str(key): int(value)
                for key, value in scores["pose_failure_reason"].fillna("").value_counts(dropna=False).sort_index().items()
            }
            if args.enable_superanimal_pose and "pose_failure_reason" in scores
            else {}
        ),
        "final_candidate_score_numeric": bool(
            pd.to_numeric(scores.get("final_candidate_score"), errors="coerce").notna().any()
        ),
        "model_fallback_mode": bool(model_fallback_mode),
        "scoring_valid_for_selection_counts": (
            {
                str(key): int(value)
                for key, value in scores["scoring_valid_for_selection"].value_counts(dropna=False).sort_index().items()
            }
            if "scoring_valid_for_selection" in scores
            else {}
        ),
        "fallback_scoring_count": int(
            scores.get("pose_fallback_scoring_used", pd.Series(dtype=bool)).fillna(False).sum()
        ),
        "sensitive_columns_leaked": sorted(SENSITIVE_COLUMNS.intersection(scores.columns)),
        "debug_samples_saved": int(debug_saved),
        "claim_boundary": "streaming filter only; no final 3000 freeze and no simple top-3000",
    }
    (output_dir / "phase16e_candidate_model_filter_audit.json").write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )
    print(f"PASS Phase 16E scores rows={len(scores)}")
    print(f"WROTE {output_dir}")


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )


def write_readme(manifest: pd.DataFrame) -> None:
    source_counts = manifest["source_mode"].value_counts().sort_index().to_dict()
    README_OUT.write_text(
        f"""# Phase 16E Colab Guide: URL-first / Streaming Model Filtering

## Goal

Phase 16E only runs streaming model filtering. It does not freeze final 3000 and does not simple top-3000.

Local packaging does not create CzechLynx zips, copy 39760 CzechLynx images, or create a large staging image package.

## Input Files

```text
phase16e_candidate_model_filter_manifest.csv
phase16e_candidate_model_filter_config.json
run_phase16e_candidate_model_filter_colab.py
```

Manifest rows: {len(manifest)}

Source mode distribution:

```json
{json.dumps({str(k): int(v) for k, v in source_counts.items()}, indent=2)}
```

## Run Modes

Base mode:

```text
IQA + OpenCLIP
```

Dependency policy:

```text
Formal mode is fail-fast. If pyiqa, any requested IQA model, open_clip, or the
requested CLIP model fails to load, the runner exits with return code != 0.
```

Smoke fallback mode:

```text
--allow-missing-models
```

Use this only for environment smoke tests. Fallback rows are marked
`model_fallback_mode=true` and `scoring_valid_for_selection=false`; they must
not enter recalibrated selection or final candidate pools.

Enhanced mode:

```text
IQA + OpenCLIP + optional SuperAnimal pose
```

SuperAnimal pose is only a structural evidence proxy for completeness and viewpoint pre-calibration. It does not prove identity, freeze final 3000, or replace Phase 16F laterality/manual audit.

## Run Base Mode On Colab/Kaggle

```bash
pip install -q pyiqa open_clip_torch pandas pillow tqdm
python run_phase16e_candidate_model_filter_colab.py \\
  --manifest phase16e_candidate_model_filter_manifest.csv \\
  --output-dir outputs/phase16/phase16e_candidate_model_filter
```

Test first 100 rows:

```bash
python run_phase16e_candidate_model_filter_colab.py \\
  --manifest phase16e_candidate_model_filter_manifest.csv \\
  --output-dir outputs/phase16/phase16e_candidate_model_filter_test100 \\
  --limit 100
```

## Optional SuperAnimal pose enhanced mode

SuperAnimal pose is optional, not a hard dependency. Runner loads DeepLabCut only when `--enable-superanimal-pose` is passed.

Run a small CzechLynx packaged-local test first:

```bash
python run_phase16e_candidate_model_filter_colab.py \\
  --manifest phase16e_candidate_model_filter_manifest.csv \\
  --output-dir outputs/phase16/phase16e_candidate_model_filter_pose_test20 \\
  --limit 20 \\
  --target-quadrant wild_czechlynx_high_confidence \\
  --source-mode packaged_local \\
  --enable-superanimal-pose \\
  --pose-model-name superanimal_quadruped_hrnetw32 \\
  --pose-device cuda \\
  --pose-failure-is-fatal false
```

If Colab lacks DeepLabCut/SuperAnimal dependencies, runner records a clear failure. With `--pose-failure-is-fatal false`, per-image or module-level pose failure falls back to IQA + OpenCLIP score and does not crash the batch.

## source_mode

- `url`: Colab downloads one image to a temp directory, scores it, then deletes it.
- `drive_path`: Colab reads a Google Drive or cloud-readable path.
- `drive_extracted_path` / `packaged_local`: Colab reads paths extracted from CzechLynx split zips.
- `unavailable_local_path`: local `/Users/deanshen/...` path only. Runner does not upload/copy it; it records `image_load_success=False` and `rejection_reason=source_not_cloud_accessible`.

## Output Files

Runner writes:

```text
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_scores.csv
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_audit.json
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_summary.md
outputs/phase16/phase16e_candidate_model_filter/debug_samples/
```

Pose enhanced mode adds:

```text
pose_enabled
pose_model_name
pose_success
pose_failure_reason
pose_num_keypoints
pose_mean_keypoint_confidence
pose_valid_keypoint_fraction
pose_body_coverage_score
pose_orientation_proxy
pose_side_view_proxy
pose_front_rear_proxy
pose_partial_body_proxy
pose_quality_score
pose_fallback_scoring_used
final_candidate_score
```

## Boundary

Do not treat Phase 16E results as final high-confidence 3000. Next step must use constrained selection:

```text
quality + animal completeness + viewpoint/laterality + PF-ERI gate + manual calibration
```

## CzechLynx Direct Split Zip Usage

Use:

```text
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_direct_zip_manifest.csv
```

Extract in Colab:

```bash
mkdir -p /content/phase16e_work/extracted_images
for z in /content/drive/MyDrive/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip; do
  unzip -q "$z" -d /content/phase16e_work/extracted_images
done
```

Map CzechLynx rows from `source_mode=unavailable_local_path` to
`source_mode=drive_extracted_path` or `packaged_local`, then build paths using
zip manifest `zip_internal_path`:

```text
/content/phase16e_work/extracted_images/{{zip_internal_path}}
```

This remains streaming/model filtering only. No final 3000 freeze. No simple top-3000.

""",
        encoding="utf-8",
    )


def audit_manifest(manifest: pd.DataFrame) -> dict:
    target_counts = manifest["target_quadrant"].value_counts().to_dict()
    sensitive_leaks = sorted(SENSITIVE_COLUMNS.intersection(manifest.columns))
    return {
        "input": str(INPUT),
        "output_dir": str(OUTPUT_DIR),
        "manifest": str(MANIFEST_OUT),
        "config": str(CONFIG_OUT),
        "runner": str(RUNNER_OUT),
        "readme": str(README_OUT),
        "manifest_rows": int(len(manifest)),
        "manifest_rows_expected": EXPECTED_ROWS,
        "manifest_rows_match_expected": bool(len(manifest) == EXPECTED_ROWS),
        "candidate_id_unique": bool(manifest["candidate_id"].is_unique),
        "bobcat_rows": int(target_counts.get("urban_bobcat_high_confidence", 0)),
        "czechlynx_rows": int(target_counts.get("wild_czechlynx_high_confidence", 0)),
        "expected_counts": EXPECTED_COUNTS,
        "source_mode_counts": {
            str(key): int(value)
            for key, value in manifest["source_mode"].value_counts(dropna=False).sort_index().items()
        },
        "url_rows_count": int((manifest["source_mode"] == "url").sum()),
        "unavailable_local_path_rows_count": int(
            (manifest["source_mode"] == "unavailable_local_path").sum()
        ),
        "sensitive_columns_leaked": sensitive_leaks,
        "scores_output_expected": (
            "outputs/phase16/phase16e_candidate_model_filter/"
            "phase16e_candidate_model_filter_scores.csv"
        ),
        "claim_boundary": (
            "packaging only; no image zip, no mass image copy, no final 3000 freeze"
        ),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT, low_memory=False)
    manifest = build_manifest(df)
    audit = audit_manifest(manifest)
    if audit["sensitive_columns_leaked"]:
        raise ValueError(f"Sensitive columns leaked: {audit['sensitive_columns_leaked']}")
    if not audit["manifest_rows_match_expected"]:
        raise ValueError(f"Unexpected manifest row count: {audit['manifest_rows']}")
    if audit["bobcat_rows"] != EXPECTED_COUNTS["urban_bobcat_high_confidence"]:
        raise ValueError(f"Unexpected Bobcat row count: {audit['bobcat_rows']}")
    if audit["czechlynx_rows"] != EXPECTED_COUNTS["wild_czechlynx_high_confidence"]:
        raise ValueError(f"Unexpected CzechLynx row count: {audit['czechlynx_rows']}")
    if not audit["candidate_id_unique"]:
        raise ValueError("candidate_id is not unique")

    manifest.to_csv(MANIFEST_OUT, index=False)
    write_config(manifest)
    write_runner()
    write_readme(manifest)
    (OUTPUT_DIR / "phase16e_candidate_model_filter_package_audit.json").write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )
    print(f"PASS phase16e candidate model filter package rows={len(manifest)}")
    print(json.dumps(audit["source_mode_counts"], indent=2))
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
