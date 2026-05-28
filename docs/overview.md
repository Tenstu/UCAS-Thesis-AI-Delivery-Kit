# Overview

`UCAS-Thesis-AI-Delivery-Kit` organizes a thesis delivery workflow around source
files, generated deliverables, checks, AI-assisted review, and human approval.

## Scope

- Write and build thesis source from LaTeX.
- Export a reviewable Word draft from LaTeX.
- Check common format risks before delivery.
- Check privacy and packaging risks before sharing.
- Use AI prompts for review and revision while keeping human decisions explicit.

## Non-Goals

- Do not replace current UCAS or institute rules.
- Do not promise a fully automatic Word file that needs no manual review.
- Do not store private thesis content or official binary originals.
- Do not require a local agent skill system to use the project.

## Workflow

1. Prepare clean LaTeX source.
2. Build PDF for layout review.
3. Export DOCX for Word-based review or submission workflows.
4. Run format checks.
5. Run privacy checks.
6. Use AI prompts for targeted review.
7. Apply human-approved changes to source.
8. Pack only allowlisted project files.
