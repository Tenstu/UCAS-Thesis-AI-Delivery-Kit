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


def test_phase3_word_export_fixtures_are_public_and_documented():
    bib_fixture = EXAMPLE_PROJECT / "bibs" / "references.bib"
    tex_fixture = EXAMPLE_PROJECT / "extraTex" / "word_export_fixtures.tex"
    word_export_doc = REPO_ROOT / "docs" / "word-export" / "README.md"

    assert bib_fixture.exists()
    bib_text = bib_fixture.read_text(encoding="utf-8")
    assert "@article{synthetic-zh-2026" in bib_text
    assert "@article{synthetic-en-2026" in bib_text
    assert "合成土壤研究" in bib_text
    assert "Synthetic soil study" in bib_text

    assert tex_fixture.exists()
    tex_text = tex_fixture.read_text(encoding="utf-8")
    assert "\\begin{figure}" in tex_text
    assert "\\begin{table}" in tex_text
    assert "合成图" in tex_text
    assert "Synthetic figure" in tex_text
    assert "合成表" in tex_text
    assert "Synthetic table" in tex_text

    doc_text = word_export_doc.read_text(encoding="utf-8")
    assert "## Phase 3 Boundary" in doc_text
    assert "Supported" in doc_text
    assert "Unsupported" in doc_text
    assert "No generated DOCX fixture is committed" in doc_text


def test_word_export_docs_explain_external_csl_source():
    word_export_doc = REPO_ROOT / "docs" / "word-export" / "README.md"
    doc_text = word_export_doc.read_text(encoding="utf-8")

    assert "## CSL Style Source" in doc_text
    assert "citation-style-language/styles-distribution" in doc_text
    assert "china-national-standard-gb-t-7714-2015-author-date.csl" in doc_text
    assert "CC BY-SA 3.0" in doc_text
    assert "--csl path/to/china-national-standard-gb-t-7714-2015-author-date.csl" in doc_text
