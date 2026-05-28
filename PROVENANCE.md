# Provenance

This file records where reusable ideas and files come from, and what must stay
out of this repository.

## Project Purpose

`UCAS-Thesis-AI-Delivery-Kit` is a clean public toolkit for UCAS thesis delivery:
LaTeX to PDF/Word export, format checks, privacy checks, delivery gates, and AI
collaboration prompts.

It is not intended to become a full copy of a previous personal thesis project
or a full clone of a LaTeX package monorepo.

## Sources

### UCAS-Dissertation

`Tenstu/UCAS-Dissertation` is a candidate baseline for clean UCAS template
files. If files are imported from that repository, copy only the minimal template
files needed for this toolkit and preserve upstream license, commit, and
attribution.

Current status: no upstream template source files have been copied in this MVP
scaffold. The current local audit did not confirm an explicit `UCAS-Dissertation`
source declaration in the files reviewed, so this repository must not claim that
lineage until it is verified.

### ChineseResearchLaTeX

`Tenstu/ChineseResearchLaTeX` and the local writing checkout contain useful
experience around UCAS Word export, thesis workflows, format checks, privacy
review, and delivery gates.

Only abstractions, rewritten scripts, checklists, and clean prompt templates
should be migrated. Do not copy full private project directories or large
project-specific scripts that embed personal assumptions.

Current status: this MVP rewrites a small standalone CLI and checks from scratch.
No private thesis content, generated deliverables, official binary originals, or
local agent state has been intentionally migrated.

## File-Level Provenance

| File or directory | Source | Commit/version/acquisition note | License or redistribution status | Content status |
|---|---|---|---|---|
| `README.md` | This repository | Created during MVP scaffold | Repository `LICENSE` | Original |
| `scripts/` | This repository | Created during MVP scaffold | Repository `LICENSE` | Original lightweight implementation |
| `docs/` | This repository | Created during MVP scaffold | Repository `LICENSE` | Original documentation |
| `prompts/` | This repository | Created during MVP scaffold | Repository `LICENSE` | Original prompt templates |
| `template/tex/` | This repository | Created during MVP scaffold | Repository `LICENSE` | Synthetic minimal example |
| `examples/` | This repository | Created during MVP scaffold | Repository `LICENSE` | Synthetic minimal example notes |
| `dist/` | Local generated output | Ignored; not included in release source | Not committed by default | Generated artifacts |

If later versions import files from `UCAS-Dissertation`, `ChineseResearchLaTeX`,
official UCAS materials, or any third-party source, add a row before including
that content in a public release. Record the source repository or acquisition
note, commit/version/access date, license, redistribution status, and whether the
content is original, rewritten, or imported verbatim.

### Official UCAS Materials

Official UCAS or institute materials should be tracked as metadata:

- source title
- source URL or acquisition note
- access date
- SHA256 checksum
- expected local placement
- redistribution status

Do not commit official binary originals by default.

## Must Not Be Migrated

- real thesis chapters, abstracts, acknowledgements, CV content, figures, data,
  tables, appendices, or defense slides
- reviewer comments, response letters, private progress plans, and run logs
- generated workdirs, OCR outputs, extracted literature notes, private Zotero or
  OneFind material, and private source indexes
- local absolute paths and local tool configuration
- local agent state, memory, hooks, and hidden runtime directories
- official `.doc`, `.docx`, `.pdf`, or `.pptx` originals unless redistribution is
  explicitly confirmed

## Publish Gate

Before any public release, run privacy checks, inspect the release zip manually,
and verify every copied template file has clear provenance and license coverage.
