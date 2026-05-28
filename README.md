# UCAS-Thesis-AI-Delivery-Kit

**LaTeX → Word 交付，国科大学位论文首选**

UCAS Thesis AI Delivery Kit is the first open-source toolkit that enables UCAS dissertations to be exported from LaTeX to Word format for advisor review and submission. It also provides PDF export, AI-assisted review, format checks, and release gates.

中文名：国科大学位论文 AI 交付工具包。

> **核心贡献**：可能是首个实现国科大学位论文 LaTeX 到 Word 完整导出链路的开源项目，解决导师审阅和学位论文提交的格式转换需求。

## 中文说明

这是一个面向中国科学院大学学位论文交付流程的工具包，重点不在”再做一套模板”，而在把 LaTeX 写作后的交付链路整理清楚：

- **Word 导出（核心贡献）**：可能是首个实现国科大学位论文 LaTeX 到 Word 完整导出的开源项目，通过 `pandoc` 导出可审阅的 DOCX，解决导师审阅和学位论文提交的格式转换需求。
- **PDF 导出**：用统一命令从 LaTeX 项目构建 PDF。
- **AI 辅助审阅**：提供可复制的 prompt 模板，用于章节润色、格式审查、参考文献检查和交付门禁判断。
- **格式自检**：在交付前扫描常见 LaTeX 写作风险，例如未清理占位符、引用标点间距、浮动体参数等。
- **交付门禁**：打包前检查本机路径、高风险二进制文件、生成物和敏感标记，发布包只包含显式允许的源码、文档、prompt 和合成示例。
- **来源可追溯**：用 `PROVENANCE.md` 和 `LICENSE-NOTES.md` 记录模板、官方材料和第三方内容的来源边界。

典型使用路径：

```bash
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format --project-dir <thesis-project> --dry-run
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --output dist/UCAS-Thesis-AI-Delivery-Kit.zip
```

当前版本是 MVP：已具备统一 CLI、最小 PDF/DOCX 导出链路、Word 导出前 TeX 预处理、轻量格式/隐私检查、格式质量巡检/修复工具、AI prompt 模板和发布打包门禁。后续会继续增强 UCAS 模板基线、Word 后处理和更细的格式规则。

## 上游项目与关系

本项目基于以下两个上游项目的经验和实践：

- **[ChineseResearchLaTeX](https://github.com/Tenstu/ChineseResearchLaTeX)**：更完整的中国科研 LaTeX 写作与交付流程，包含完整的 UCAS 学位论文模板、Word 导出实践、AI 辅助写作工作流和交付门禁。**如需了解完整流程，请参考此项目。**
- **[UCAS-Dissertation](https://github.com/Tenstu/UCAS-Dissertation)**：国科大学位论文 LaTeX 模板候选基线。

**本项目定位**：专注于交付工具链（LaTeX → Word/PDF 导出、格式检查、隐私检查、发布打包），不重复上游项目的模板和写作流程。

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
| **Word export (core)** | `python scripts/ucas.py export-docx` | **核心贡献**：可能是首个实现国科大学位论文 LaTeX 到 Word 完整导出的开源项目。通过 `pandoc` 导出可审阅的 DOCX，解决导师审阅和学位论文提交的格式转换需求。 |
| TeX preprocessing | `python scripts/ucas.py prepare-tex` | Normalize TeX source before Word export, including CJK/Latin/number spacing and common time-unit spacing. Defaults to dry-run. |
| PDF build | `python scripts/ucas.py build-pdf` | Build a thesis PDF through the local LaTeX toolchain. |
| Spine build | `python scripts/ucas.py build-spine` | Build a spine/cover-side TeX file when the project provides one. |
| Format check | `python scripts/ucas.py check-format` | Scan common LaTeX manuscript risks before handoff. |
| Format quality check | `python scripts/ucas.py check-format-quality` | Generate fast/full format QA reports and optional repair feeds. |
| Format repair | `python scripts/ucas.py fix-format` | Preview or apply common automated repairs. Defaults to dry-run. |
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
- `PyYAML` for YAML-based rule loading in `check-format-quality` when a rules file is present

Development helpers:

- `git` for version control
- GitHub CLI `gh` for repository publishing

Local AI skills, subagents, and prompt workflows are development and writing aids.
They are not required to run the CLI.

`check-format-quality` and `fix-format` expect a thesis project root containing
`main.tex` and `extraTex/`; use a real thesis project as `--project-dir`, not
the tool repository root or the minimal `template/tex` smoke-test fixture.

## Quick Start

```bash
python scripts/ucas.py --help
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode fast
python scripts/ucas.py fix-format --project-dir <thesis-project> --dry-run
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --output dist/UCAS-Thesis-AI-Delivery-Kit.zip
```

The included `template/tex` files are synthetic minimal examples. They are meant
to exercise the workflow, not to replace the official UCAS requirements.

## CLI Reference

```bash
python scripts/ucas.py build-pdf     --project-dir <project>
python scripts/ucas.py build-spine   --project-dir <project>
python scripts/ucas.py prepare-tex   --project-dir <project> [--glob "*.tex"] [--dry-run|--apply]
python scripts/ucas.py export-docx   --project-dir <project> --output dist/main.docx
python scripts/ucas.py check-format  --project-dir <project>
python scripts/ucas.py check-format-quality --project-dir <project> --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format    --project-dir <project> [--issues-json .latex-cache/format-fix/latest_check.json] [--dry-run|--apply]
python scripts/ucas.py check-privacy --project-dir <project>
python scripts/ucas.py pack          --project-dir <project> --output dist/release.zip
```

All commands accept `--project-dir`. The default is the current working directory.
Commands that can modify TeX files default to dry-run; pass `--apply` only after
reviewing the proposed changes.

## Project Layout

```text
UCAS-Thesis-AI-Delivery-Kit/
├── template/              # minimal synthetic TeX entry points
├── scripts/
│   ├── ucas.py             # unified CLI
│   ├── word_export/        # DOCX export wrapper
│   ├── tex_preprocessing/   # Word-export-oriented TeX preprocessing
│   ├── format_tools/        # format QA and repair utilities
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
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format --project-dir <thesis-project> --dry-run
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

- **Word export (core contribution)**: 可能是首个实现国科大学位论文 LaTeX 到 Word 完整导出的开源项目，通过 `pandoc` 导出可审阅的 DOCX
- unified Python CLI
- TeX preprocessing before Word export
- minimal PDF build and DOCX export paths
- lightweight format and privacy checks
- fast/full format quality checks and dry-run-first repair tools
- explicit allowlist release packaging
- AI review and delivery prompt templates
- synthetic TeX example for smoke testing

Planned next steps:

- import or align with a clean UCAS template baseline after provenance review
- expand Word post-processing beyond the current `pandoc` beta path
- add more UCAS-specific format rules and regression examples
