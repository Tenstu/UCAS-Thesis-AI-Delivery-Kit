from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportOptions:
    project_dir: Path
    tex_file: str
    output: Path
    reference_doc: Path | None = None


def _require_pandoc() -> str:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError(
            "pandoc was not found on PATH. Install pandoc or run only the PDF/check commands."
        )
    return pandoc


def export_docx(options: ExportOptions) -> Path:
    project_dir = options.project_dir.resolve()
    source = (project_dir / options.tex_file).resolve()
    output = options.output.resolve()

    if not source.exists():
        raise FileNotFoundError(f"TeX source not found: {source}")
    if options.reference_doc and not options.reference_doc.exists():
        raise FileNotFoundError(f"Reference DOCX not found: {options.reference_doc}")

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        _require_pandoc(),
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

    completed = subprocess.run(cmd, cwd=project_dir, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"pandoc export failed with exit code {completed.returncode}")
    return output
