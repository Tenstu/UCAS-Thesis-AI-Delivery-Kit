#!/usr/bin/env python3
"""Smoke tests for checked-in examples."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PROJECT = REPO_ROOT / "examples" / "thesis-project"


def run_ucas(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/ucas.py", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_thesis_project_example_supports_phase2_smoke_commands():
    assert (EXAMPLE_PROJECT / "main.tex").exists()
    assert (EXAMPLE_PROJECT / "extraTex").is_dir()

    check = run_ucas(
        "check-format-quality",
        "--project-dir",
        "examples/thesis-project",
        "--mode",
        "fast",
        "--emit-json",
        "--emit-repair-feed",
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "[REPAIR_FEED] json:" in check.stdout

    repair = run_ucas(
        "fix-format",
        "--project-dir",
        "examples/thesis-project",
        "--dry-run",
    )
    assert repair.returncode == 0, repair.stdout + repair.stderr
    assert "mode=dry-run" in repair.stdout
