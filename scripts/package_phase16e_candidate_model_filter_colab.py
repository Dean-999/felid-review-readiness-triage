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
README_OUT = OUTPUT_DIR / "README_PHASE16E_COLAB_CN.md"

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
        },
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="phase16e_candidate_model_filter_manifest.csv")
    parser.add_argument("--output-dir", default="outputs/phase16/phase16e_candidate_model_filter")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--iqa-models", default="musiq,topiq_nr,brisque")
    parser.add_argument("--clip-model", default="ViT-B-32")
    parser.add_argument("--clip-pretrained", default="laion2b_s34b_b79k")
    parser.add_argument("--debug-sample-limit", type=int, default=80)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def load_iqa_models(names: list[str], device: str) -> dict:
    try:
        import pyiqa
    except Exception as exc:
        print(f"WARNING pyiqa unavailable: {exc}")
        return {}

    models = {}
    for name in names:
        name = name.strip()
        if not name:
            continue
        try:
            models[name] = pyiqa.create_metric(name, device=device)
            print(f"loaded IQA model: {name}")
        except Exception as exc:
            print(f"WARNING skip IQA model {name}: {exc}")
    return models


def load_clip(model_name: str, pretrained: str, device: str):
    try:
        import open_clip
        import torch
    except Exception as exc:
        print(f"WARNING open_clip unavailable: {exc}")
        return None

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
        print(f"WARNING CLIP load failed: {exc}")
        return None


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


def selection_eligible(result: dict) -> bool:
    if not result.get("image_load_success", False):
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
        "## Claim Boundary",
        "",
        "Phase 16E only streams and scores candidates. It does not freeze final 3000 sets.",
        "",
    ]
    (output_dir / "phase16e_candidate_model_filter_summary.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = output_dir / "debug_samples"
    debug_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="phase16e_stream_"))

    manifest = pd.read_csv(args.manifest, low_memory=False)
    if args.limit and args.limit > 0:
        manifest = manifest.head(args.limit).copy()

    iqa_models = load_iqa_models(args.iqa_models.split(","), args.device)
    clip_bundle = load_clip(args.clip_model, args.clip_pretrained, args.device)

    rows = []
    debug_saved = 0
    try:
        for _, row in tqdm(manifest.iterrows(), total=len(manifest)):
            result = row.to_dict()
            image_path, error = resolve_image(row, tmp_dir)
            result["image_load_success"] = image_path is not None
            result["rejection_reason"] = error
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
                    if debug_saved < args.debug_sample_limit:
                        crop.save(debug_dir / f"{row['candidate_id']}_debug_crop.jpg", quality=90)
                        debug_saved += 1
                except Exception as exc:
                    result["image_load_success"] = False
                    result["rejection_reason"] = f"model_or_image_error:{exc}"
                finally:
                    if str(row.get("source_mode")) == "url":
                        Path(image_path).unlink(missing_ok=True)
            result["selection_eligible"] = selection_eligible(result)
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
        f"""# Phase 16E Colab 使用说明：URL-first / Streaming Model Filtering

## 目标

Phase 16E 只做 streaming model filtering，不冻结 final 3000，不做 simple top-3000。

本地不会生成 CzechLynx zip，不复制 39760 张 CzechLynx 图片，也不会创建大型 staging 图片包。

## 输入文件

```text
phase16e_candidate_model_filter_manifest.csv
phase16e_candidate_model_filter_config.json
run_phase16e_candidate_model_filter_colab.py
```

Manifest rows: {len(manifest)}

Source mode 分布：

```json
{json.dumps({str(k): int(v) for k, v in source_counts.items()}, indent=2)}
```

## 在 Colab/Kaggle 上运行

```bash
pip install -q pyiqa open_clip_torch pandas pillow tqdm
python run_phase16e_candidate_model_filter_colab.py \\
  --manifest phase16e_candidate_model_filter_manifest.csv \\
  --output-dir outputs/phase16/phase16e_candidate_model_filter
```

如果只想先测试 100 张：

```bash
python run_phase16e_candidate_model_filter_colab.py \\
  --manifest phase16e_candidate_model_filter_manifest.csv \\
  --output-dir outputs/phase16/phase16e_candidate_model_filter_test100 \\
  --limit 100
```

## source_mode 解释

- `url`: Colab 逐张下载图片到临时目录，跑完后立即删除。
- `drive_path`: Colab 直接读取 Google Drive / cloud-readable path。
- `drive_extracted_path` / `packaged_local`: 用 CzechLynx split zip 解压后的路径读取。
- `unavailable_local_path`: 只有本机 `/Users/deanshen/...` 路径，不上传、不复制；runner 记录 `image_load_success=False` 和 `rejection_reason=source_not_cloud_accessible`。

## 输出文件

runner 会写入：

```text
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_scores.csv
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_audit.json
outputs/phase16/phase16e_candidate_model_filter/phase16e_candidate_model_filter_summary.md
outputs/phase16/phase16e_candidate_model_filter/debug_samples/
```

## 重要边界

不要把 Phase 16E 结果直接当 final high-confidence 3000。下一步必须做 constrained selection：

```text
quality + animal completeness + viewpoint/laterality + PF-ERI gate + manual calibration
```

## CzechLynx direct split zip 使用方式

如果使用：

```text
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip
outputs/phase16/phase16e_czechlynx_direct_zips/phase16e_czechlynx_direct_zip_manifest.csv
```

Colab 解压：

```bash
mkdir -p /content/phase16e_work/extracted_images
for z in /content/drive/MyDrive/phase16e_czechlynx_direct_zips/phase16e_czechlynx_images_part_*.zip; do
  unzip -q "$z" -d /content/phase16e_work/extracted_images
done
```

然后把 CzechLynx rows 从 `source_mode=unavailable_local_path` 映射为
`source_mode=drive_extracted_path` 或 `packaged_local`，并用
zip manifest 的 `zip_internal_path` 拼接：

```text
/content/phase16e_work/extracted_images/{{zip_internal_path}}
```

这仍然只是 streaming/model filtering，不冻结 final 3000，不做 simple top-3000。

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
