from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class ExportOptions:
    project_dir: Path
    tex_file: str
    output: Path
    reference_doc: Path | None = None
    citeproc: bool = False
    csl: Path | None = None
    bibliographies: tuple[Path, ...] = ()


DROP_BIBTEX_FIELDS = {
    "abstract",
    "annote",
    "file",
    "keywords",
}

FIELD_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=")
QUOTED_FIELD_END_PATTERN = re.compile(r'(?<!\\)"\s*,?\s*$')


def _require_pandoc() -> str:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError(
            "pandoc was not found on PATH. Install pandoc or run only the PDF/check commands."
        )
    return pandoc


def sanitize_bibtex_text(text: str) -> str:
    """Remove large or local-only BibTeX fields before Pandoc citation export."""
    sanitized_lines: list[str] = []
    skip_mode: str | None = None
    brace_depth = 0

    for line in text.splitlines():
        if skip_mode == "braced":
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                skip_mode = None
            continue
        if skip_mode == "quoted":
            if QUOTED_FIELD_END_PATTERN.search(line):
                skip_mode = None
            continue

        match = FIELD_PATTERN.match(line)
        if match and match.group(1).lower() in DROP_BIBTEX_FIELDS:
            brace_depth = line.count("{") - line.count("}")
            if brace_depth > 0:
                skip_mode = "braced"
            elif '"' in line and not QUOTED_FIELD_END_PATTERN.search(line):
                skip_mode = "quoted"
            continue

        sanitized_lines.append(line)

    return "\n".join(sanitized_lines) + ("\n" if text.endswith("\n") else "")


def prepare_bibliographies(
    bibliographies: tuple[Path, ...],
    output_dir: Path,
) -> tuple[Path, ...]:
    if not bibliographies:
        return ()

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sanitized_paths: list[Path] = []
    for index, bibliography in enumerate(bibliographies, start=1):
        source = bibliography.resolve()
        if not source.exists():
            raise FileNotFoundError(f"Bibliography file not found: {source}")

        target = output_dir / f"{index:02d}-{source.name}"
        target.write_text(
            sanitize_bibtex_text(source.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        sanitized_paths.append(target)

    return tuple(sanitized_paths)


def build_pandoc_command(
    options: ExportOptions,
    pandoc_path: str,
    bibliography_paths: tuple[Path, ...] | None = None,
) -> list[str]:
    project_dir = options.project_dir.resolve()
    source = (project_dir / options.tex_file).resolve()
    output = options.output.resolve()

    cmd = [
        pandoc_path,
        str(source),
        "--from",
        "latex",
        "--to",
        "docx",
        "--output",
        str(output),
        "--resource-path",
        str(project_dir),
    ]
    if options.reference_doc:
        cmd.extend(["--reference-doc", str(options.reference_doc.resolve())])
    if options.citeproc:
        cmd.append("--citeproc")
    if options.csl:
        cmd.extend(["--csl", str(options.csl.resolve())])

    for bibliography in bibliography_paths or options.bibliographies:
        cmd.extend(["--bibliography", str(bibliography.resolve())])

    return cmd


def export_docx(options: ExportOptions) -> Path:
    project_dir = options.project_dir.resolve()
    source = (project_dir / options.tex_file).resolve()
    output = options.output.resolve()

    if not source.exists():
        raise FileNotFoundError(f"TeX source not found: {source}")
    if options.reference_doc and not options.reference_doc.exists():
        raise FileNotFoundError(f"Reference DOCX not found: {options.reference_doc}")
    if options.csl and not options.csl.exists():
        raise FileNotFoundError(f"CSL file not found: {options.csl}")
    for bibliography in options.bibliographies:
        if not bibliography.exists():
            raise FileNotFoundError(f"Bibliography file not found: {bibliography}")

    output.parent.mkdir(parents=True, exist_ok=True)

    prepared_bibliographies = prepare_bibliographies(
        options.bibliographies,
        output_dir=project_dir / ".latex-cache" / "word-export",
    )
    cmd = build_pandoc_command(
        options,
        pandoc_path=_require_pandoc(),
        bibliography_paths=prepared_bibliographies,
    )

    completed = subprocess.run(cmd, cwd=project_dir, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"pandoc export failed with exit code {completed.returncode}")
    return output
