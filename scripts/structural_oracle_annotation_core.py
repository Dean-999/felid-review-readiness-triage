"""Safe packet and response primitives for structural-oracle annotation."""
from __future__ import annotations

import csv
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

PACKET_COLUMNS = ["annotation_packet_id", "left_asset_token", "right_asset_token", "instrument_version", "annotation_form_schema_version"]
CONTINUOUS_NAMES = ["left_visible_pattern_area_fraction", "right_visible_pattern_area_fraction", "left_occlusion_fraction", "right_occlusion_fraction", "shared_body_region_fraction"]
CONTINUOUS_FIELDS = {name: "0.00" for name in CONTINUOUS_NAMES}
VIEWPOINTS = ["compatible", "partial", "incompatible", "unknown"]
ANNOTATORS = {"annotator_a", "annotator_b"}
RESPONSE_COLUMNS = ["annotation_packet_id", "raw_annotation_response_id", *CONTINUOUS_NAMES, "viewpoint_compatibility_class", "technical_problem_flag", "annotator_id", "submitted_at_utc"]


def load_packet(package_root: Path) -> pd.DataFrame:
    package_root = package_root.resolve()
    packet_path = package_root / "annotation_packets.csv"
    if not packet_path.is_file() or not (package_root / "ANNOTATOR_INSTRUCTIONS.txt").is_file() or not (package_root / "images").is_dir():
        raise ValueError("invalid structural-oracle package layout")
    frame = pd.read_csv(packet_path, dtype=str, keep_default_na=False).fillna("")
    if list(frame.columns) != PACKET_COLUMNS or frame.empty or frame["annotation_packet_id"].duplicated().any():
        raise ValueError("invalid anonymous packet manifest")
    for token in frame[["annotation_packet_id", "left_asset_token", "right_asset_token"]].to_numpy().ravel():
        if not str(token).replace("_", "").isalnum() or not str(token).startswith(("packet_", "asset_")):
            raise ValueError("packet has non-opaque token")
    return frame


def resolve_asset(package_root: Path, token: str) -> Path:
    if not token.startswith("asset_") or not token.replace("_", "").isalnum():
        raise ValueError("invalid asset token")
    images = (package_root.resolve() / "images").resolve()
    matches = list(images.glob(f"{token}.*"))
    if len(matches) != 1 or not matches[0].is_file() or not matches[0].resolve().is_relative_to(images):
        raise ValueError("opaque asset missing or ambiguous")
    return matches[0].resolve()


def empty_response(packet_id: str) -> dict[str, str]:
    return {"annotation_packet_id": packet_id, "raw_annotation_response_id": "", **{name: "" for name in CONTINUOUS_NAMES}, "viewpoint_compatibility_class": "", "technical_problem_flag": "no", "annotator_id": "", "submitted_at_utc": ""}


def validate_response(values: dict[str, str]) -> None:
    if values.get("technical_problem_flag") not in {"yes", "no"}:
        raise ValueError("technical_problem_flag must be yes or no")
    if values["technical_problem_flag"] == "yes":
        if any(values.get(name, "") for name in CONTINUOUS_NAMES) or values.get("viewpoint_compatibility_class", ""):
            raise ValueError("technical problem responses cannot contain structural values")
        return
    for name in CONTINUOUS_NAMES:
        try: value = float(values.get(name, ""))
        except ValueError as exc: raise ValueError(f"{name} requires a value") from exc
        if not 0 <= value <= 1 or round(value * 20) != value * 20:
            raise ValueError(f"{name} must use the 0.05 grid")
    if values.get("viewpoint_compatibility_class") not in VIEWPOINTS:
        raise ValueError("choose a viewpoint compatibility class")


def response_path(output_root: Path, annotator_id: str) -> Path:
    if annotator_id not in ANNOTATORS: raise ValueError("invalid fixed annotator")
    return output_root / annotator_id / "structural_oracle_responses.csv"


def load_responses(output_root: Path, annotator_id: str, packet_ids: set[str]) -> pd.DataFrame:
    path = response_path(output_root, annotator_id)
    if not path.exists(): return pd.DataFrame(columns=RESPONSE_COLUMNS)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
    if list(frame.columns) != RESPONSE_COLUMNS or not set(frame["annotation_packet_id"]).issubset(packet_ids): raise ValueError("invalid response export")
    return frame.drop_duplicates("annotation_packet_id", keep="last")


def save_response(output_root: Path, annotator_id: str, responses: pd.DataFrame, values: dict[str, str]) -> None:
    validate_response(values)
    packet_ids = set(responses["annotation_packet_id"]) | {values["annotation_packet_id"]}
    if not values["annotation_packet_id"].startswith("packet_"): raise ValueError("invalid packet token")
    item = {key: values.get(key, "") for key in RESPONSE_COLUMNS}
    item["raw_annotation_response_id"] = f"response_{values['annotation_packet_id'].split('_',1)[1]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    item["annotator_id"] = annotator_id; item["submitted_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    merged = pd.concat([responses[responses["annotation_packet_id"] != item["annotation_packet_id"]], pd.DataFrame([item])], ignore_index=True)
    path = response_path(output_root, annotator_id); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, newline="", encoding="utf-8") as handle:
        merged[RESPONSE_COLUMNS].to_csv(handle, index=False); temporary = Path(handle.name)
    os.replace(temporary, path)
