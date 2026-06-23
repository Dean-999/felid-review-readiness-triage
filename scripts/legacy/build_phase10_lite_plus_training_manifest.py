#!/usr/bin/env python3
"""Compatibility entrypoint for building the Phase 10-Lite Plus manifest."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).with_name("build_phase10_lite_plus_matched_training_manifest.py")),
        run_name="__main__",
    )
