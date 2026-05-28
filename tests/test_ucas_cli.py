#!/usr/bin/env python3
"""Tests for the unified UCAS CLI glue code."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts import ucas
from scripts.format_tools import check_format_quality


def test_fix_format_defaults_to_dry_run(monkeypatch):
    captured_argv = []

    def fake_run_format_repair():
        captured_argv[:] = sys.argv
        return 0

    monkeypatch.setattr(ucas, "run_format_repair", fake_run_format_repair)

    exit_code = ucas.main(["fix-format", "--project-dir", str(Path.cwd())])

    assert exit_code == 0
    assert "--dry-run" in captured_argv
    assert "--apply" not in captured_argv


def test_format_cli_restores_sys_argv_after_subcommand(monkeypatch):
    original_argv = ["ucas.py", "sentinel"]
    monkeypatch.setattr(sys, "argv", original_argv.copy())

    def fake_run_format_quality_check():
        assert sys.argv[0] == "check_format_quality.py"
        assert "--emit-json" in sys.argv
        return 0

    monkeypatch.setattr(
        ucas, "run_format_quality_check", fake_run_format_quality_check
    )

    exit_code = ucas.main(
        [
            "check-format-quality",
            "--project-dir",
            str(Path.cwd()),
            "--emit-json",
        ]
    )

    assert exit_code == 0
    assert sys.argv == original_argv


def test_repair_cli_restores_sys_argv_after_subcommand(monkeypatch):
    original_argv = ["ucas.py", "sentinel"]
    monkeypatch.setattr(sys, "argv", original_argv.copy())

    def fake_run_format_repair():
        assert sys.argv[0] == "format_repair.py"
        assert "--dry-run" in sys.argv
        return 0

    monkeypatch.setattr(ucas, "run_format_repair", fake_run_format_repair)

    exit_code = ucas.main(["fix-format", "--project-dir", str(Path.cwd())])

    assert exit_code == 0
    assert sys.argv == original_argv


def test_quality_cli_exposes_no_emit_flags(monkeypatch):
    captured_argv = []

    def fake_run_format_quality_check():
        captured_argv[:] = sys.argv
        return 0

    monkeypatch.setattr(
        ucas, "run_format_quality_check", fake_run_format_quality_check
    )

    exit_code = ucas.main(
        [
            "check-format-quality",
            "--project-dir",
            str(Path.cwd()),
            "--no-emit-json",
            "--no-emit-markdown",
            "--no-emit-repair-feed",
        ]
    )

    assert exit_code == 0
    assert "--no-emit-json" in captured_argv
    assert "--no-emit-markdown" in captured_argv
    assert "--no-emit-repair-feed" in captured_argv


def test_choose_word_python_falls_back_without_crlatex_install(monkeypatch):
    monkeypatch.delenv("BENSZ_DOCX_PYTHON", raising=False)
    monkeypatch.setattr(check_format_quality.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        check_format_quality,
        "CRLATEX_WIN_WINDOWS_PYTHON",
        Path("Z:/missing/python.exe"),
    )
    monkeypatch.setattr(
        check_format_quality,
        "CRLATEX_WIN_WSL_PYTHON",
        Path("/mnt/z/missing/python.exe"),
    )

    interpreter, source = check_format_quality.choose_word_python()

    assert interpreter == sys.executable
    assert source == "fallback_sys_executable"
