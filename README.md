# UCAS-Thesis-AI-Delivery-Kit

UCAS Thesis AI Delivery Kit：国科大学位论文 AI 交付工具包。

LaTeX -> Word/PDF export, AI-assisted review, and delivery gates for UCAS theses.

这个项目的重点不是“又一个 UCAS LaTeX 模板”，而是把论文写作交付中的几件难事做成可复用流程：

- 从 LaTeX 草稿导出 PDF 和 Word。
- 对 Word/PDF 交付前的格式风险做自动检查。
- 在打包前检查隐私、路径、日志和官方二进制原件。
- 用普通文档和 prompt 模板组织 AI 协作，而不是把个人 agent 体系变成运行依赖。

当前仓库按公开发布口径整理：只展示通用工具、合成示例、文档化流程和 prompt 模板，不展示个人论文写作的具体内容。

## Features

- **Word/PDF export first**: provide one CLI surface for building PDF and exporting DOCX from LaTeX source.
- **AI-assisted delivery workflow**: keep reusable prompts and review loops in plain Markdown, without requiring a local agent runtime.
- **Format checks**: scan common LaTeX manuscript risks before delivery.
- **Privacy checks**: block local paths, private working directories, token-like strings, and suspicious binary originals before packaging.
- **Release gate**: package only an explicit allowlist of clean source, docs, prompts, and examples.
- **Private-first provenance**: record upstream/source boundaries before any public release.

## Dependencies

Required:

- Python 3.10+.

Optional but used by core commands:

- LaTeX toolchain with `latexmk` or `xelatex` for `build-pdf` and `build-spine`.
- `pandoc` for `export-docx`.
- `biber` or `bibtex` for bibliography-aware fallback builds when `latexmk` is unavailable.

Development/publishing helpers:

- `git` for local version control.
- GitHub CLI `gh` for creating and pushing the private repository.

The local AI skills and subagents used while building this repository are development aids only. They are not runtime dependencies.

## Quick Start

```bash
python scripts/ucas.py --help
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --output dist/UCAS-Thesis-AI-Delivery-Kit.zip
```

`build-pdf` 需要本机安装 LaTeX 工具链。`export-docx` beta 入口需要 `pandoc`。
`dist/`、`.latex-cache/` 和生成的 PDF/DOCX 默认不进入发布包；公开分享前仍建议清理生成产物并运行 `check-privacy`。

## Commands

```bash
python scripts/ucas.py build-pdf
python scripts/ucas.py build-spine
python scripts/ucas.py export-docx
python scripts/ucas.py check-format
python scripts/ucas.py check-privacy
python scripts/ucas.py pack
```

所有命令都支持 `--project-dir` 指向一个论文项目目录。默认目录是当前工作目录。

## Directory Map

```text
UCAS-Thesis-AI-Delivery-Kit/
├── template/              # 干净 UCAS LaTeX 模板入口和占位示例
├── scripts/
│   ├── ucas.py             # 统一入口
│   ├── word_export/        # Word 导出 beta
│   └── checks/             # 隐私、格式、打包检查
├── docs/
│   ├── word-export/        # Word 导出说明
│   ├── ai-workflow/        # AI 协作流程
│   ├── rules/              # UCAS 格式规则与检查口径
│   ├── development/        # 构建过程、验证和开发辅助说明
│   └── official/           # 官方材料来源与 checksum 记录
├── prompts/                # 可复制的 AI prompt 模板
├── examples/               # 去隐私最小示例
├── PROVENANCE.md
├── LICENSE-NOTES.md
├── LICENSE
└── README.md
```

## Migration Policy

迁移能力和抽象流程，不迁移完整私有工作树。

可以迁移：

- UCAS 模板的最小干净入口。
- Word 导出流程中可复用的公开逻辑。
- 格式检查、隐私检查、交付门禁。
- AI 协作流程文档和 prompt 模板。

必须排除：

- 真实论文正文、图表、答辩材料、审稿回复、私有参考资料。
- `workdirs/`、真实 `plans/`、运行日志、本机路径、私有工具配置。
- 未确认可再分发的官方 `.doc/.docx/.pdf/.pptx` 原件。
- 本机 agent 状态、memory、hooks 和隐藏运行目录。

## Provenance

Current MVP source policy:

- No real thesis text, figures, defense slides, review responses, private workdirs, local logs, or official binary originals were migrated.
- The CLI, checks, docs, prompts, and minimal examples in this scaffold are newly written for this repository.
- `Tenstu/UCAS-Dissertation` remains a candidate clean UCAS template baseline, but no upstream template files are copied in this MVP.
- `ChineseResearchLaTeX` is treated as experience and workflow evidence, not as a directory to copy wholesale.
- Official UCAS materials should be recorded by source URL, acquisition note, checksum, and local placement; they are not committed by default.

See [PROVENANCE.md](PROVENANCE.md) and [LICENSE-NOTES.md](LICENSE-NOTES.md).

## Build And Verification

Recommended local verification:

```bash
python scripts/ucas.py --help
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --dry-run
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/minimal.docx
```

Before sharing a zip:

```bash
python scripts/ucas.py pack --project-dir . --output dist/UCAS-Thesis-AI-Delivery-Kit.zip
```

`pack` runs privacy and format gates and only includes allowlisted source files.

## Status

MVP scaffold:

- clean project skeleton
- unified CLI
- pandoc-based Word export beta
- lightweight format and privacy checks
- pack dry-run and zip gate
- provenance, license notes, docs, prompts, and synthetic examples
