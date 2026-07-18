#!/usr/bin/env python3
"""Package high-confidence candidates for cloud IQA and viewpoint rescoring.

The package is intentionally model-agnostic: local code builds a stable manifest,
while the generated Colab runner uses pretrained no-reference IQA and CLIP-style
viewpoint scoring on GPU. Returned scores should be used for high-confidence
selection and laterality balance, not as final identity labels.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs/phase16/high_confidence_quality_viewpoint_rescore"
MANIFEST = OUTPUT_DIR / "phase16_high_confidence_quality_viewpoint_manifest.csv"
README = OUTPUT_DIR / "README.md"
COLAB_RUNNER = OUTPUT_DIR / "run_phase16_quality_viewpoint_colab.py"
AUDIT_JSON = OUTPUT_DIR / "phase16_high_confidence_quality_viewpoint_package_audit.json"

SOURCE_FILES = [
    (
        "current_bobcat_high_final",
        PROJECT_ROOT
        / "outputs/phase14/phase14_final_2x2_working_labels/phase14_bobcat_high_confidence_3000_working_final_labels.csv",
        "urban_bobcat_high_confidence",
        "current_high_final",
    ),
    (
        "current_czechlynx_high_final",
        PROJECT_ROOT
        / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_confidence_3000_working_final_labels.csv",
        "wild_czechlynx_high_confidence",
        "current_high_final",
    ),
    (
        "bobcat_high_candidate_pool",
        PROJECT_ROOT
        / "outputs/phase14/phase14_colab_megadetector_final_selection/phase14_colab_megadetector_all_gated_candidates.csv",
        "urban_bobcat_high_confidence",
        "topup_candidate_pool",
    ),
    (
        "czechlynx_high_topup_passed_pool",
        PROJECT_ROOT
        / "outputs/phase14/phase14_final_2x2_working_labels/phase14_czechlynx_high_topup_passed_pool.csv",
        "wild_czechlynx_high_confidence",
        "topup_candidate_pool",
    ),
]

PATH_COLUMNS = [
    "image_path",
    "candidate_source_path",
    "evidence_image_path",
    "local_relative_path",
    "local_image_path",
    "review_image_path_local",
    "path",
]

KEEP_OPTIONAL_COLUMNS = [
    "image_id",
    "file_name",
    "source_dataset",
    "species_label",
    "scientific_name",
    "environment_context",
    "phase14_2x2_quadrant",
    "human_review_bucket",
    "human_review_confidence",
    "md_best_confidence",
    "md_area_fraction",
    "md_width_fraction",
    "md_height_fraction",
    "md_aspect_ratio",
    "md_edge_touch",
    "md_x0",
    "md_y0",
    "md_x1",
    "md_y1",
    "auto_quality_score",
    "auto_evidence_score",
    "image_evidence_utility_score",
]


def _first_existing_path(row: pd.Series) -> str:
    for column in PATH_COLUMNS:
        if column not in row or pd.isna(row[column]):
            continue
        value = str(row[column]).strip()
        if not value:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / value
        if path.exists():
            return str(path)
    return ""


def _read_source(name: str, path: Path, quadrant: str, role: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, low_memory=False)
    out = pd.DataFrame(index=df.index)
    out["phase16_rescore_source"] = name
    out["phase16_candidate_role"] = role
    out["source_quadrant"] = (
        df["phase14_2x2_quadrant"] if "phase14_2x2_quadrant" in df.columns else quadrant
    )
    out["phase16_target_quadrant"] = quadrant
    out["phase16_image_path"] = df.apply(_first_existing_path, axis=1)
    out["phase16_source_row_index"] = range(1, len(df) + 1)
    for column in KEEP_OPTIONAL_COLUMNS:
        out[column] = df[column] if column in df.columns else ""
    return out


def build_manifest() -> pd.DataFrame:
    frames = [_read_source(*source) for source in SOURCE_FILES]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[combined["phase16_image_path"].astype(str).str.len() > 0].copy()
    combined["phase16_existing_current_high"] = combined["phase16_candidate_role"].eq(
        "current_high_final"
    )
    combined = combined.sort_values(
        [
            "phase16_existing_current_high",
            "phase16_target_quadrant",
            "phase16_candidate_role",
            "phase16_rescore_source",
        ],
        ascending=[False, True, True, True],
    )
    combined = combined.drop_duplicates("phase16_image_path", keep="first")
    combined = combined.reset_index(drop=True)
    combined.insert(0, "phase16_rescore_index", range(1, len(combined) + 1))
    combined["phase16_quality_viewpoint_status"] = "pending_cloud_rescore"
    return combined


def write_colab_runner() -> None:
    COLAB_RUNNER.write_text(
        r'''#!/usr/bin/env python3
"""Run Phase 16 high-confidence IQA and viewpoint scoring on Colab/Kaggle.

Expected usage:
    python run_phase16_quality_viewpoint_colab.py \
      --manifest phase16_high_confidence_quality_viewpoint_manifest.csv \
      --output phase16_high_confidence_quality_viewpoint_scores.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--iqa-models", default="musiq,topiq_nr,brisque")
    parser.add_argument("--clip-model", default="ViT-B-32")
    parser.add_argument("--clip-pretrained", default="laion2b_s34b_b79k")
    return parser.parse_args()


def normalized_crop(image: Image.Image, row: pd.Series, padding: float = 0.08) -> Image.Image:
    values = []
    for key in ["md_x0", "md_y0", "md_x1", "md_y1"]:
        try:
            values.append(float(row.get(key)))
        except (TypeError, ValueError):
            return image
    if len(values) != 4 or any(pd.isna(value) for value in values):
        return image
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


def load_iqa_models(names: list[str], device: str):
    import pyiqa

    models = {}
    for name in names:
        name = name.strip()
        if not name:
            continue
        try:
            models[name] = pyiqa.create_metric(name, device=device)
            print(f"loaded IQA model: {name}")
        except Exception as exc:
            print(f"SKIP IQA model {name}: {exc}")
    return models


def score_iqa(models: dict, image_path: str, crop: Image.Image, tmp_dir: Path) -> dict:
    scores = {}
    crop_path = tmp_dir / "phase16_tmp_crop.jpg"
    crop.convert("RGB").save(crop_path, quality=95)
    for name, model in models.items():
        try:
            value = model(str(crop_path))
            scores[f"iqa_{name}_crop_score"] = float(value.detach().cpu().reshape(-1)[0])
        except Exception as exc:
            scores[f"iqa_{name}_crop_score"] = None
            scores[f"iqa_{name}_error"] = str(exc)
    return scores


def load_clip(model_name: str, pretrained: str, device: str):
    import open_clip
    import torch

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
    return model, preprocess, labels, text_features


def score_viewpoint(model, preprocess, labels, text_features, crop: Image.Image, device: str) -> dict:
    import torch

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


def main() -> None:
    args = parse_args()
    manifest = pd.read_csv(args.manifest, low_memory=False)
    output = Path(args.output)
    tmp_dir = output.parent / "_phase16_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    iqa_models = load_iqa_models(args.iqa_models.split(","), args.device)
    clip_model, clip_preprocess, clip_labels, clip_text_features = load_clip(
        args.clip_model,
        args.clip_pretrained,
        args.device,
    )

    rows = []
    for _, row in tqdm(manifest.iterrows(), total=len(manifest)):
        result = row.to_dict()
        path = str(row["phase16_image_path"])
        try:
            image = Image.open(path).convert("RGB")
            crop = normalized_crop(image, row)
            result["phase16_rescore_error"] = ""
            result.update(score_iqa(iqa_models, path, crop, tmp_dir))
            result.update(
                score_viewpoint(
                    clip_model,
                    clip_preprocess,
                    clip_labels,
                    clip_text_features,
                    crop,
                    args.device,
                )
            )
        except Exception as exc:
            result["phase16_rescore_error"] = str(exc)
        rows.append(result)

    pd.DataFrame(rows).to_csv(output, index=False)
    audit = {
        "manifest": args.manifest,
        "output": str(output),
        "rows": len(rows),
        "iqa_models": args.iqa_models,
        "clip_model": args.clip_model,
        "clip_pretrained": args.clip_pretrained,
        "claim_boundary": "pretrained quality/viewpoint rescoring only; not final identity validation",
    }
    output.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS wrote {output} rows={len(rows)}")


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )


def write_readme(row_count: int, counts: dict[str, int]) -> None:
    README.write_text(
        f"""# Phase 16 High-Confidence Quality + Viewpoint Rescore Package

Purpose: rescore high-confidence image candidates with pretrained quality and
viewpoint models before freezing Dataset v1.

Rows: {row_count}

Quadrant counts:

```json
{json.dumps(counts, indent=2)}
```

Recommended cloud setup:

```bash
pip install -q pyiqa open_clip_torch pandas pillow tqdm
python run_phase16_quality_viewpoint_colab.py \\
  --manifest phase16_high_confidence_quality_viewpoint_manifest.csv \\
  --output phase16_high_confidence_quality_viewpoint_scores.csv
```

Model logic:

- NR-IQA models estimate perceptual/technical quality on the animal crop.
- CLIP prompt scores provide a zero-shot viewpoint/laterality prefilter.
- Returned labels are not final truth. They define priority for manual audit and
  balanced high-confidence selection.

Claim boundary:

Do not claim that generic IQA proves Re-ID evidence. Use IQA as one gate inside
PF-ERI, combined with detector geometry, flank/pattern evidence, laterality
balance, and manual calibration.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    manifest.to_csv(MANIFEST, index=False)
    counts = {
        str(key): int(value)
        for key, value in manifest["phase16_target_quadrant"].value_counts().sort_index().items()
    }
    write_colab_runner()
    write_readme(len(manifest), counts)
    audit = {
        "source_files": [
            {"name": name, "path": str(path), "quadrant": quadrant, "role": role}
            for name, path, quadrant, role in SOURCE_FILES
        ],
        "manifest": str(MANIFEST),
        "colab_runner": str(COLAB_RUNNER),
        "rows": int(len(manifest)),
        "quadrant_counts": counts,
        "claim_boundary": (
            "cloud package only; quality/viewpoint scores require returned model outputs "
            "and manual calibration before final high-confidence selection"
        ),
    }
    AUDIT_JSON.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"PASS phase16 high-confidence quality/viewpoint package rows={len(manifest)}")
    print(f"WROTE {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
