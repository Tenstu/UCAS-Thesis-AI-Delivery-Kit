# Overview

`UCAS-Thesis-AI-Delivery-Kit` organizes a thesis delivery workflow around source
files, generated deliverables, checks, AI-assisted review, and human approval.

## Scope

- Write and build thesis source from LaTeX.
- Normalize TeX source before Word export.
- Export a reviewable Word draft from LaTeX.
- Check common format risks before delivery, including deeper quality reports and repair feeds.
- Check privacy and packaging risks before sharing.
- Use AI prompts for review and revision while keeping human decisions explicit.

## Non-Goals

- Do not replace current UCAS or institute rules.
- Do not promise a fully automatic Word file that needs no manual review.
- Do not store private thesis content or official binary originals.
- Do not require a local agent skill system to use the project.

## Workflow

1. Prepare clean LaTeX source.
2. Run TeX preprocessing before Word export:
   `python scripts/ucas.py prepare-tex --project-dir <thesis-project> --dry-run`.
3. Build PDF for layout review.
4. Export DOCX for Word-based review or submission workflows.
5. Run lightweight format checks:
   `python scripts/ucas.py check-format --project-dir <repo-or-project>`.
6. Run format quality checks on a thesis project root:
   `python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode fast --emit-json --emit-repair-feed`.
7. Preview automated repair:
   `python scripts/ucas.py fix-format --project-dir <thesis-project> --dry-run`.
8. Run privacy checks.
9. Use AI prompts for targeted review.
10. Apply human-approved changes to source.
11. Pack only allowlisted project files.

`check-format-quality` and `fix-format` expect a thesis project root containing
`main.tex` and `extraTex/`. They write reports and repair feeds under
`.latex-cache/quality-check/` and `.latex-cache/format-fix/`.
