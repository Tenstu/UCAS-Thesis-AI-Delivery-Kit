from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .format import scan_format
from .privacy import scan_privacy


REQUIRED_RELEASE_FILES = {
    "LICENSE",
    "LICENSE-NOTES.md",
    "PROVENANCE.md",
    "README.md",
}

ALLOWLIST_FILES = {
    ".gitignore",
    *REQUIRED_RELEASE_FILES,
    "docs/overview.md",
    "docs/ai-workflow/README.md",
    "docs/official/README.md",
    "docs/rules/README.md",
    "docs/word-export/README.md",
    "docs/development/README.md",
    "examples/minimal-thesis/README.md",
    "prompts/chapter_polish.md",
    "prompts/delivery_gate.md",
    "prompts/export_to_word.md",
    "prompts/format_audit.md",
    "prompts/reference_check.md",
    "scripts/__init__.py",
    "scripts/ucas.py",
    "scripts/checks/__init__.py",
    "scripts/checks/format.py",
    "scripts/checks/pack.py",
    "scripts/checks/privacy.py",
    "scripts/word_export/__init__.py",
    "scripts/word_export/pandoc_export.py",
    "template/README.md",
    "template/tex/main.tex",
    "template/tex/spine.tex",
}


def _is_allowlisted(root: Path, path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    return rel in ALLOWLIST_FILES


def iter_pack_files(root: Path) -> list[Path]:
    root = root.resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and _is_allowlisted(root, path):
            files.append(path)
    return sorted(files)


def create_release_zip(root: Path, output: Path, dry_run: bool = False) -> list[Path]:
    root = root.resolve()
    missing = sorted(name for name in REQUIRED_RELEASE_FILES if not (root / name).exists())
    if missing:
        raise RuntimeError(f"required release metadata missing: {', '.join(missing)}")

    files = iter_pack_files(root)

    privacy_issues = scan_privacy(root, files)
    if privacy_issues:
        formatted = "\n".join(issue.format(root) for issue in privacy_issues[:20])
        raise RuntimeError(f"privacy gate failed before packing:\n{formatted}")

    format_issues = scan_format(root)
    blocking_format_issues = [issue for issue in format_issues if issue.level == "error"]
    if blocking_format_issues:
        formatted = "\n".join(issue.format(root) for issue in blocking_format_issues[:20])
        raise RuntimeError(f"format gate failed before packing:\n{formatted}")

    if dry_run:
        return files

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(root).as_posix())
    return files
