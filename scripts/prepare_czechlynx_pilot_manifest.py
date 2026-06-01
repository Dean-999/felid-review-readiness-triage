from pathlib import Path
import shutil
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "czechlynx"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "czechlynx"
LABEL_DIR = PROJECT_ROOT / "data" / "labels" / "czechlynx"
REVIEW_IMAGE_DIR = INTERIM_DIR / "pilot_review_images"

REAL_CSV = RAW_DIR / "CzechLynxDataset-Metadata-Real.csv"
PILOT_INDIVIDUALS = 100
IMAGES_PER_INDIVIDUAL = 2

INTERIM_DIR.mkdir(parents=True, exist_ok=True)
LABEL_DIR.mkdir(parents=True, exist_ok=True)
REVIEW_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(REAL_CSV)

df["local_image_path"] = df["path"].apply(lambda p: str(RAW_DIR / p))
df["image_exists"] = df["local_image_path"].apply(lambda p: Path(p).exists())

manifest_cols = [
    "source",
    "date",
    "encounter",
    "unique_name",
    "path",
    "local_image_path",
    "image_exists",
    "relative_age",
    "coat_pattern",
    "location",
    "cell_code",
    "latitude",
    "longitude",
    "trap_id",
    "split-geo_aware",
    "split-time_open",
    "split-time_closed",
    "split-pose",
]

manifest = df[manifest_cols].copy()
manifest.to_csv(INTERIM_DIR / "czechlynx_real_manifest.csv", index=False)

eligible = manifest[manifest["image_exists"]].copy()
counts = eligible["unique_name"].value_counts()
eligible_ids = counts[counts >= IMAGES_PER_INDIVIDUAL].index.to_series()

sampled_ids = eligible_ids.sample(
    n=min(PILOT_INDIVIDUALS, len(eligible_ids)),
    random_state=42,
).tolist()

pilot_internal = (
    eligible[eligible["unique_name"].isin(sampled_ids)]
    .groupby("unique_name", group_keys=False)
    .sample(n=IMAGES_PER_INDIVIDUAL, random_state=43)
    .reset_index(drop=True)
)

pilot_internal = pilot_internal.sample(frac=1, random_state=44).reset_index(drop=True)
pilot_internal["pilot_image_id"] = [f"czlx_pilot_{i:04d}" for i in range(len(pilot_internal))]
pilot_internal["review_image_filename"] = pilot_internal["pilot_image_id"] + ".jpg"
pilot_internal["review_image_path"] = pilot_internal["review_image_filename"].apply(
    lambda name: str(REVIEW_IMAGE_DIR / name)
)

for _, row in pilot_internal.iterrows():
    src = Path(row["local_image_path"])
    dst = Path(row["review_image_path"])
    shutil.copy2(src, dst)

internal_cols = [
    "pilot_image_id",
    "review_image_filename",
    "review_image_path",
    "source",
    "date",
    "encounter",
    "unique_name",
    "path",
    "local_image_path",
    "relative_age",
    "coat_pattern",
    "location",
    "cell_code",
    "latitude",
    "longitude",
    "trap_id",
    "split-geo_aware",
    "split-time_open",
    "split-time_closed",
]

pilot_internal[internal_cols].to_csv(
    INTERIM_DIR / "czechlynx_pilot_internal_with_ids.csv",
    index=False,
)

triage = pd.DataFrame({
    "pilot_image_id": pilot_internal["pilot_image_id"],
    "dataset": "CzechLynx",
    "species_label": "Eurasian Lynx",
    "source_role": "quantitative_validation",
    "image_path": pilot_internal["review_image_path"],
    "triage_label": "",
    "blur_level": "",
    "occlusion_level": "",
    "lighting_condition": "",
    "night_ir_artifact": "",
    "visible_side": "",
    "side_comparability": "",
    "visible_region": "",
    "pattern_visibility": "",
    "body_fraction_visible": "",
    "distance_to_camera": "",
    "camera_angle": "",
    "metadata_completeness": "complete",
    "reviewer_confidence": "",
    "uncertainty_flag": "",
    "exclusion_reason": "",
    "notes": "",
})

triage.to_csv(LABEL_DIR / "czechlynx_pilot_triage_blinded.csv", index=False)

summary = {
    "real_rows": len(df),
    "real_images_existing": int(df["path"].apply(lambda p: (RAW_DIR / p).exists()).sum()),
    "unique_working_individual_ids": int(df["unique_name"].nunique()),
    "eligible_individuals_with_at_least_2_images": int(len(eligible_ids)),
    "pilot_rows": int(len(triage)),
    "pilot_unique_internal_ids": int(pilot_internal["unique_name"].nunique()),
    "images_per_individual_in_pilot": int(IMAGES_PER_INDIVIDUAL),
    "max_images_per_id_in_pilot": int(pilot_internal["unique_name"].value_counts().max()),
    "review_images_written": int(len(list(REVIEW_IMAGE_DIR.glob("*.jpg")))),
}

summary_path = INTERIM_DIR / "czechlynx_pilot_sampling_summary.txt"
with summary_path.open("w", encoding="utf-8") as f:
    for k, v in summary.items():
        f.write(f"{k}: {v}\n")

print("Wrote:", INTERIM_DIR / "czechlynx_real_manifest.csv")
print("Wrote:", INTERIM_DIR / "czechlynx_pilot_internal_with_ids.csv")
print("Wrote:", LABEL_DIR / "czechlynx_pilot_triage_blinded.csv")
print("Wrote:", summary_path)
print("Wrote review images to:", REVIEW_IMAGE_DIR)
print()
for k, v in summary.items():
    print(f"{k}: {v}")
