#!/usr/bin/env python3
"""Tests for Word export command construction and bibliography handling."""

from __future__ import annotations

from pathlib import Path

from scripts.word_export import pandoc_export


def test_build_pandoc_command_includes_citation_options(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    source = project_dir / "main.tex"
    source.write_text("\\cite{synthetic-zh-2026}", encoding="utf-8")
    reference_doc = project_dir / "reference.docx"
    reference_doc.write_bytes(b"placeholder")
    csl = project_dir / "gbt.csl"
    csl.write_text("<style />", encoding="utf-8")
    sanitized_bib = project_dir / ".latex-cache" / "word-export" / "references.bib"
    sanitized_bib.parent.mkdir(parents=True)
    sanitized_bib.write_text("@article{synthetic}", encoding="utf-8")

    options = pandoc_export.ExportOptions(
        project_dir=project_dir,
        tex_file="main.tex",
        output=project_dir / "main.docx",
        reference_doc=reference_doc,
        citeproc=True,
        csl=csl,
        bibliographies=(project_dir / "bibs" / "references.bib",),
    )

    command = pandoc_export.build_pandoc_command(
        options,
        pandoc_path="pandoc",
        bibliography_paths=(sanitized_bib,),
    )

    assert command[:2] == ["pandoc", str(source.resolve())]
    assert "--citeproc" in command
    assert command[command.index("--csl") + 1] == str(csl.resolve())
    assert command[command.index("--bibliography") + 1] == str(sanitized_bib.resolve())
    assert command[command.index("--reference-doc") + 1] == str(reference_doc.resolve())


def test_sanitize_bibtex_text_removes_large_or_local_fields():
    source = """@article{synthetic-zh-2026,
  title = {合成土壤研究的公开示例},
  abstract = {This long abstract is not needed in Word output.},
  file = {local-pdf-placeholder},
  keywords = {private, local},
  year = {2026}
}
"""

    sanitized = pandoc_export.sanitize_bibtex_text(source)

    assert "title = {合成土壤研究的公开示例}" in sanitized
    assert "year = {2026}" in sanitized
    assert "abstract" not in sanitized
    assert "file" not in sanitized
    assert "keywords" not in sanitized
    assert "local-pdf-placeholder" not in sanitized


def test_sanitize_bibtex_text_removes_multiline_quoted_fields():
    source = """@article{synthetic-quoted-2026,
  title = {Synthetic quoted field study},
  abstract = "line one
line two
line three",
  year = {2026}
}
"""

    sanitized = pandoc_export.sanitize_bibtex_text(source)

    assert "title = {Synthetic quoted field study}" in sanitized
    assert "year = {2026}" in sanitized
    assert "abstract" not in sanitized
    assert "line one" not in sanitized
    assert "line two" not in sanitized
    assert "line three" not in sanitized


def test_prepare_bibliographies_writes_sanitized_copies(tmp_path):
    project_dir = tmp_path / "project"
    bib_dir = project_dir / "bibs"
    output_dir = project_dir / ".latex-cache" / "word-export"
    bib_dir.mkdir(parents=True)
    original = bib_dir / "references.bib"
    original.write_text(
        "@article{synthetic-en-2026,\n"
        "  title = {Synthetic soil study},\n"
        "  file = {local-pdf-placeholder},\n"
        "  year = {2026}\n"
        "}\n",
        encoding="utf-8",
    )

    sanitized_paths = pandoc_export.prepare_bibliographies(
        (original,),
        output_dir=output_dir,
    )

    assert len(sanitized_paths) == 1
    assert sanitized_paths[0].parent == output_dir.resolve()
    assert sanitized_paths[0].exists()
    text = sanitized_paths[0].read_text(encoding="utf-8")
    assert "Synthetic soil study" in text
    assert "file" not in text
    assert "local-pdf-placeholder" not in text


def test_export_docx_missing_bibliography_fails_before_pandoc(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main.tex").write_text("\\cite{missing}", encoding="utf-8")
    missing_bib = project_dir / "bibs" / "missing.bib"

    options = pandoc_export.ExportOptions(
        project_dir=project_dir,
        tex_file="main.tex",
        output=project_dir / "main.docx",
        citeproc=True,
        bibliographies=(missing_bib,),
    )

    try:
        pandoc_export.export_docx(options)
    except FileNotFoundError as exc:
        assert "Bibliography file not found" in str(exc)
        assert str(missing_bib) in str(exc)
    else:
        raise AssertionError("missing bibliography should fail before running pandoc")
