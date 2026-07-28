#!/usr/bin/env python3
"""Build the immutable Task 15I GPU descriptor-inference control package."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST_DIR = ROOT / "archive/pferi_v2/task_runs/model_development/2026-07-25_task15i_descriptor_execution_manifest_v1"
OUTPUT = ROOT / "work/pferi_v2/gpu/packages/task15i_descriptor_inference"
PACKAGE_NAME = "PF_ERI_TASK15I_DESCRIPTOR_MODELSCOPE_PACKAGE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(package: Path) -> None:
    files = sorted(path for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256")
    (package / "PACKAGE_MANIFEST.sha256").write_text("".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files), encoding="utf-8")


def verify_manifest(package: Path) -> None:
    declared: set[str] = set()
    for line in (package / "PACKAGE_MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = package / relative
        if relative in declared or not target.is_file() or sha256(target) != expected:
            raise RuntimeError(f"package verification failed: {relative}")
        declared.add(relative)
    actual = {str(path.relative_to(package)) for path in package.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.sha256"}
    if declared != actual:
        raise RuntimeError("package manifest inventory mismatch")


def requirements_text() -> str:
    return """numpy==2.3.3
pillow==11.3.0
timm==1.0.27
transformers==5.12.1
torch==2.11.0+cu128
torchvision==0.26.0+cu128
--extra-index-url https://download.pytorch.org/whl/cu128
"""


def readme_text() -> str:
    return """# PF-ERI Task 15I dual-descriptor ModelScope GPU control package

此控制包与已经提供的 `TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip` 配合使用。图片 ZIP 保持独立，避免重复上传约 2.6 GB 的图片；本包只包含冻结合同、三列图片清单、运行器和完整性校验。

运行只读取图片清单中的 `image_id`、`image_path_relative`、`content_sha256`，不会读取结果标签、个体身份标签、校准结局、确认结局或机制确认结局。它只产生可复现的双描述子 embedding 和每张图片的有向 top-20 候选，不构成身份结论、性能通过结论或 Task 15I 通过结论。

## ModelScope GPU 环境

选择 CUDA GPU 镜像，建议 Python 3.12 和至少 16 GB 显存。上传并解压两个文件：

1. `TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip`
2. `PF_ERI_TASK15I_DESCRIPTOR_MODELSCOPE_PACKAGE.zip`

在 ModelScope 终端执行：

```bash
unzip TASK15I_INDEPENDENT_DESCRIPTOR_IMAGES.zip
unzip PF_ERI_TASK15I_DESCRIPTOR_MODELSCOPE_PACKAGE.zip
cd PF_ERI_TASK15I_DESCRIPTOR_MODELSCOPE_PACKAGE

python -m pip install -U uv
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt

MANIFEST=inputs/descriptor_execution_manifest.csv
IMAGE_ROOT=../v2_descriptor_execution_package/images

python run_task15i_descriptor.py smoke --package-root . --manifest "$MANIFEST" --image-root "$IMAGE_ROOT" --output-dir PF_ERI_TASK15I_SMOKE
python run_task15i_descriptor.py run --package-root . --manifest "$MANIFEST" --image-root "$IMAGE_ROOT" --output-dir PF_ERI_TASK15I_DESCRIPTOR_RESULTS --batch-size 16
python run_task15i_descriptor.py validate --package-root . --manifest "$MANIFEST" --results-dir PF_ERI_TASK15I_DESCRIPTOR_RESULTS
python run_task15i_descriptor.py export --results-dir PF_ERI_TASK15I_DESCRIPTOR_RESULTS --zip PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT.zip
sha256sum PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT.zip > PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT.sha256
```

`smoke` 会验证控制包、合同、4,108 张图片的 SHA256、CUDA 可用性和运行时；`run` 再次验证全部图片后加载 `hf-hub:BVRA/MegaDescriptor-L-384` 和 `facebook/dinov2-vitl14`。任一解码、完整性、模型或输出错误都会使整个任务失败，绝不静默跳过图片。

预期成功输出为 MegaDescriptor `(4108, 1536)`、DINOv2 `(4108, 1024)`，每个描述子各有 `4108 x 20 = 82,160` 条无自配对、有 rank 的有向候选记录。成功的 `validate` 后，回传：

```text
PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT.zip
PF_ERI_TASK15I_DESCRIPTOR_FINAL_EXPORT.sha256
```
"""


def build(output: Path = OUTPUT) -> dict[str, Any]:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {output}")
    sources = {
        "run_task15i_descriptor.py": ROOT / "scripts/task15i_descriptor_modelscope_runner.py",
        "contracts/task15i_descriptor_inference_contract.json": ROOT / "schemas/pferi_v2/task15i_descriptor_inference_contract_v1.json",
        "inputs/descriptor_execution_manifest.csv": SOURCE_MANIFEST_DIR / "descriptor_execution_manifest.csv",
        "audits/manifest_audit.json": SOURCE_MANIFEST_DIR / "manifest_audit.json",
        "audits/descriptor_image_package_audit.json": SOURCE_MANIFEST_DIR / "descriptor_package_audit.json",
    }
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".task15i_descriptor_package_") as temporary:
        stage = Path(temporary)
        package = stage / PACKAGE_NAME
        for relative, source in sources.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (package / "requirements.txt").write_text(requirements_text(), encoding="utf-8")
        (package / "README_MODELSCOPE.md").write_text(readme_text(), encoding="utf-8")
        write_manifest(package)
        verify_manifest(package)
        zip_path = stage / f"{PACKAGE_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"{PACKAGE_NAME}/{path.relative_to(package)}")
        with zipfile.ZipFile(zip_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"bad ZIP member: {bad}")
        audit = {
            "status": "PASS",
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "package_name": PACKAGE_NAME,
            "file_count_excluding_manifest": len(sources) + 2,
            "manifest_sha256": sha256(package / "PACKAGE_MANIFEST.sha256"),
            "zip_sha256": sha256(zip_path),
            "runner_source_sha256": sha256(ROOT / "scripts/task15i_descriptor_modelscope_runner.py"),
            "runner_packaged_sha256": sha256(package / "run_task15i_descriptor.py"),
            "contract_sha256": sha256(package / "contracts/task15i_descriptor_inference_contract.json"),
            "input_manifest_sha256": sha256(package / "inputs/descriptor_execution_manifest.csv"),
            "image_zip_included": False,
            "image_zip_required_sha256": json.loads((SOURCE_MANIFEST_DIR / "descriptor_package_audit.json").read_text(encoding="utf-8"))["zip_sha256"],
            "locked_stage_outcomes_included": False,
            "claim_boundary": "Control package only; it does not contain labels/outcomes and does not establish any Task 15I pass conclusion.",
        }
        (stage / "package_build_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (stage / f"{PACKAGE_NAME}.sha256").write_text(f"{audit['zip_sha256']}  {PACKAGE_NAME}.zip\n", encoding="utf-8")
        shutil.copytree(stage, output)
    return audit


def main() -> int:
    try:
        audit = build()
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__, "error": str(error)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
