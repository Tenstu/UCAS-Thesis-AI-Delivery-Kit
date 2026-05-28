from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.checks.format import scan_format
from scripts.checks.pack import create_release_zip
from scripts.checks.privacy import scan_privacy
from scripts.word_export.pandoc_export import ExportOptions, export_docx
from scripts.tex_preprocessing.prepare_tex_for_word_export import (
    build_steps as build_tex_preprocessing_steps,
    run_step as run_tex_preprocessing_step,
)


def _project_dir(value: str | None) -> Path:
    return Path(value or ".").resolve()


def _run_latex(project_dir: Path, tex_file: str, output_name: str) -> Path:
    source = project_dir / tex_file
    if not source.exists():
        raise FileNotFoundError(f"TeX source not found: {source}")

    cache_dir = project_dir / ".latex-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    latexmk = shutil.which("latexmk")
    if latexmk:
        cmd = [
            latexmk,
            "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-outdir={cache_dir}",
            str(source),
        ]
        completed = subprocess.run(cmd, cwd=project_dir, text=True)
        if completed.returncode != 0:
            raise RuntimeError(f"latexmk failed with exit code {completed.returncode}")
    else:
        xelatex = shutil.which("xelatex")
        if not xelatex:
            raise RuntimeError("Neither latexmk nor xelatex was found on PATH.")

        def run_xelatex() -> None:
            completed = subprocess.run(
                [
                    xelatex,
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-output-directory={cache_dir}",
                    str(source),
                ],
                cwd=project_dir,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError(f"xelatex failed with exit code {completed.returncode}")

        run_xelatex()
        stem = Path(tex_file).stem
        if (cache_dir / f"{stem}.bcf").exists():
            biber = shutil.which("biber")
            if not biber:
                raise RuntimeError("biber metadata was produced, but biber was not found on PATH.")
            completed = subprocess.run([biber, stem], cwd=cache_dir, text=True)
            if completed.returncode != 0:
                raise RuntimeError(f"biber failed with exit code {completed.returncode}")
        elif (cache_dir / f"{stem}.aux").exists():
            bibtex = shutil.which("bibtex")
            if bibtex:
                completed = subprocess.run([bibtex, stem], cwd=cache_dir, text=True)
                if completed.returncode != 0:
                    raise RuntimeError(f"bibtex failed with exit code {completed.returncode}")
        run_xelatex()
        run_xelatex()

    built_pdf = cache_dir / f"{Path(tex_file).stem}.pdf"
    target_pdf = project_dir / output_name
    if not built_pdf.exists():
        raise RuntimeError(f"expected PDF was not produced: {built_pdf}")
    shutil.copy2(built_pdf, target_pdf)
    return target_pdf


def cmd_build_pdf(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    pdf = _run_latex(project_dir, args.tex_file, args.output)
    print(f"PDF written: {pdf}")
    return 0


def cmd_export_docx(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    output = Path(args.output or project_dir / f"{Path(args.tex_file).stem}.docx")
    docx = export_docx(
        ExportOptions(
            project_dir=project_dir,
            tex_file=args.tex_file,
            output=output,
            reference_doc=Path(args.reference_doc).resolve() if args.reference_doc else None,
        )
    )
    print(f"DOCX written: {docx}")
    return 0


def cmd_check_format(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    issues = scan_format(project_dir)
    for issue in issues:
        print(issue.format(project_dir))
    print(f"format issues: {len(issues)}")
    return 1 if any(issue.level == "error" for issue in issues) else 0


def cmd_check_privacy(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    issues = scan_privacy(project_dir)
    for issue in issues:
        print(issue.format(project_dir))
    print(f"privacy issues: {len(issues)}")
    return 1 if issues else 0


def cmd_pack(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    output = Path(args.output or project_dir / "dist" / "UCAS-Thesis-AI-Delivery-Kit.zip")
    files = create_release_zip(project_dir, output, dry_run=args.dry_run)
    if args.dry_run:
        print("pack dry run:")
        for path in files:
            print(path.relative_to(project_dir).as_posix())
        print(f"files: {len(files)}")
    else:
        print(f"release zip written: {output.resolve()}")
        print(f"files: {len(files)}")
    return 0


def cmd_prepare_tex(args: argparse.Namespace) -> int:
    project_dir = _project_dir(args.project_dir)
    if not project_dir.exists():
        print(f"[ERROR] 项目目录不存在：{project_dir}")
        return 1

    if args.apply and args.dry_run:
        print("[ERROR] `--apply` 与 `--dry-run` 不能同时使用。")
        return 1

    mode = "apply" if args.apply else "dry-run"
    print(f"[INFO] mode={mode} project_dir={project_dir}")
    steps = build_tex_preprocessing_steps(
        sys.executable,
        project_dir,
        apply=args.apply,
        glob_pattern=args.glob,
    )
    for step in steps:
        exit_code = run_tex_preprocessing_step(step, project_dir)
        if exit_code != 0:
            print(f"[STOP] {step.name} 失败，后续步骤已中止。")
            return exit_code
    print("[OK] 预处理链执行完成。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UCAS Thesis AI Delivery Kit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_project_arg(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-dir", default=".", help="Thesis/project directory")

    build_pdf = subparsers.add_parser("build-pdf", help="Build main PDF from LaTeX")
    add_project_arg(build_pdf)
    build_pdf.add_argument("--tex-file", default="main.tex")
    build_pdf.add_argument("--output", default="main.pdf")
    build_pdf.set_defaults(func=cmd_build_pdf)

    build_spine = subparsers.add_parser("build-spine", help="Build spine PDF from LaTeX")
    add_project_arg(build_spine)
    build_spine.add_argument("--tex-file", default="spine.tex")
    build_spine.add_argument("--output", default="spine.pdf")
    build_spine.set_defaults(func=cmd_build_pdf)

    export = subparsers.add_parser("export-docx", help="Export LaTeX to DOCX through pandoc")
    add_project_arg(export)
    export.add_argument("--tex-file", default="main.tex")
    export.add_argument("--output", default=None)
    export.add_argument("--reference-doc", default=None)
    export.set_defaults(func=cmd_export_docx)

    check_format = subparsers.add_parser("check-format", help="Run lightweight LaTeX format checks")
    add_project_arg(check_format)
    check_format.set_defaults(func=cmd_check_format)

    check_privacy = subparsers.add_parser("check-privacy", help="Run privacy and release-safety checks")
    add_project_arg(check_privacy)
    check_privacy.set_defaults(func=cmd_check_privacy)

    pack = subparsers.add_parser("pack", help="Create a privacy-gated release zip")
    add_project_arg(pack)
    pack.add_argument("--output", default=None)
    pack.add_argument("--dry-run", action="store_true")
    pack.set_defaults(func=cmd_pack)

    prepare_tex = subparsers.add_parser(
        "prepare-tex",
        help="Run TeX preprocessing for Word export (space cleanup + time unit normalization)",
    )
    add_project_arg(prepare_tex)
    prepare_tex.add_argument("--glob", default="*.tex", help="File glob pattern")
    prepare_tex.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    prepare_tex.add_argument("--dry-run", action="store_true", help="Explicit dry-run mode")
    prepare_tex.set_defaults(func=cmd_prepare_tex)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
