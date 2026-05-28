# UCAS-Thesis-AI-Delivery-Kit

UCAS Thesis AI Delivery Kit is a delivery-focused toolkit for UCAS dissertations:
LaTeX -> Word/PDF export, AI-assisted review, format checks, and release gates.

中文名：国科大学位论文 AI 交付工具包。

## Why This Project

UCAS thesis writing often starts comfortably in LaTeX, but the final workflow may
require Word files, manual format review, advisor feedback, and carefully checked
delivery packages. This project turns those recurring handoff steps into a small,
scriptable toolkit.

It is not just another UCAS LaTeX template. The main value is the workflow around
the template:

- export LaTeX drafts to reviewable Word and PDF outputs
- run pre-delivery format checks
- catch local paths, generated binaries, and risky files before packaging
- use reusable AI prompts for review, polishing, and delivery decisions
- package only an explicit allowlist of clean project files

## Highlights

| Capability | Command or location | Purpose |
|---|---|---|
| PDF build | `python scripts/ucas.py build-pdf` | Build a thesis PDF through the local LaTeX toolchain. |
| Spine build | `python scripts/ucas.py build-spine` | Build a spine/cover-side TeX file when the project provides one. |
| Word export beta | `python scripts/ucas.py export-docx` | Export LaTeX to DOCX through `pandoc`. |
| Format check | `python scripts/ucas.py check-format` | Scan common LaTeX manuscript risks before handoff. |
| Privacy check | `python scripts/ucas.py check-privacy` | Detect local paths, sensitive markers, and high-risk binary files. |
| Release pack | `python scripts/ucas.py pack` | Build a privacy-gated zip from an explicit allowlist. |
| AI workflow | `prompts/`, `docs/ai-workflow/` | Provide task prompts for review, polish, references, and delivery gates. |

## Dependencies

Required:

- Python 3.10+

Optional by command:

- `latexmk` or `xelatex` for `build-pdf` and `build-spine`
- `pandoc` for `export-docx`
- `biber` or `bibtex` for bibliography-aware fallback builds when `latexmk` is unavailable

Development helpers:

- `git` for version control
- GitHub CLI `gh` for repository publishing

Local AI skills, subagents, and prompt workflows are development and writing aids.
They are not required to run the CLI.

## Quick Start

```bash
python scripts/ucas.py --help
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --output dist/UCAS-Thesis-AI-Delivery-Kit.zip
```

The included `template/tex` files are synthetic minimal examples. They are meant
to exercise the workflow, not to replace the official UCAS requirements.

## CLI Reference

```bash
python scripts/ucas.py build-pdf     --project-dir <project>
python scripts/ucas.py build-spine   --project-dir <project>
python scripts/ucas.py export-docx   --project-dir <project> --output dist/main.docx
python scripts/ucas.py check-format  --project-dir <project>
python scripts/ucas.py check-privacy --project-dir <project>
python scripts/ucas.py pack          --project-dir <project> --output dist/release.zip
```

All commands accept `--project-dir`. The default is the current working directory.

## Project Layout

```text
UCAS-Thesis-AI-Delivery-Kit/
├── template/              # minimal synthetic TeX entry points
├── scripts/
│   ├── ucas.py             # unified CLI
│   ├── word_export/        # DOCX export wrapper
│   └── checks/             # format, privacy, and pack gates
├── docs/
│   ├── word-export/        # Word export notes
│   ├── ai-workflow/        # AI collaboration workflow
│   ├── rules/              # format-rule notes
│   ├── development/        # build process and development notes
│   └── official/           # official-material metadata policy
├── prompts/                # reusable AI prompt templates
├── examples/               # minimal example notes
├── PROVENANCE.md
├── LICENSE-NOTES.md
├── LICENSE
└── README.md
```

## Verification

Recommended checks before sharing a package:

```bash
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --dry-run
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/minimal.docx
```

`pack` runs the format and privacy gates, then writes only allowlisted files to
the release zip. Generated files under `dist/` and LaTeX cache directories are
ignored by Git.

## Source And Licensing

Repository-original code, documentation, prompts, and synthetic examples are
released under the MIT License.

Official UCAS materials and any future third-party template imports must keep
their own source and redistribution terms. This repository records those
boundaries in [PROVENANCE.md](PROVENANCE.md) and [LICENSE-NOTES.md](LICENSE-NOTES.md).

## Current Status

MVP scaffold:

- unified Python CLI
- minimal PDF build and DOCX export paths
- lightweight format and privacy checks
- explicit allowlist release packaging
- AI review and delivery prompt templates
- synthetic TeX example for smoke testing

Planned next steps:

- import or align with a clean UCAS template baseline after provenance review
- expand Word post-processing beyond the current `pandoc` beta path
- add more UCAS-specific format rules and regression examples
