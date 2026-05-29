# UCAS-Thesis-AI-Delivery-Kit

**面向中国科学院大学学位论文的 LaTeX -> Word/PDF 交付工具包。**

本项目的目标不是再做一套论文模板，而是把“用 LaTeX 写作之后如何交付”
整理成可复用、可检查、可打包的命令行流程。核心贡献是围绕 UCAS 学位
论文场景，提供从 TeX 预处理、DOCX 导出、格式检查、隐私检查到发布打包
的一组公开工具和合成示例。

当前版本已经可以导出可审阅 DOCX。项目后续目标是逐步把 Word 导出做成
“可直接交付最终 Word”的完整流程：导出、后处理、域更新、图表/参考文献
处理、质量报告和交付门禁都由 Kit 串起来，而不是依赖人工记忆一串零散步骤。

## 项目原则

- **交付优先**：关注导师审阅、Word 提交、格式复核和发布打包这些实际交付问题。
- **干运行优先**：会修改文件的命令默认预览，用户确认后再 `--apply`。
- **公开示例优先**：仓库只放 synthetic fixture，不放私有论文正文、官方二进制模板或生成交付物。
- **可验证优先**：每个导出能力都应有 fixture、测试、报告或 dry-run 证据。
- **边界清楚**：来源、许可、隐私和发布内容通过 `PROVENANCE.md`、`LICENSE-NOTES.md`、`check-privacy` 和 `pack` 管住。

## Word 导出流程

推荐把 Word 导出理解为一条交付流水线，而不是单个转换命令。

### 1. 预处理 TeX

先检查 Word 导出前的 TeX 清理建议：

```bash
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
```

确认 dry-run 输出后再写回：

```bash
python scripts/ucas.py prepare-tex --project-dir template/tex --apply
```

当前预处理会处理常见 CJK/Latin/数字间距和时间单位空格，同时保护 LaTeX
命令、数学片段和结构化内容。

### 2. 导出 DOCX

使用 Pandoc 生成 Word 草稿：

```bash
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
```

如需套用 Word 样式参考文件，可传入：

```bash
python scripts/ucas.py export-docx \
  --project-dir template/tex \
  --reference-doc path/to/reference.docx \
  --output dist/main.docx
```

当前 `export-docx` 产物定位为“可审阅 DOCX”。最终提交前仍需检查目录、
页眉页脚、页码、图表题注、参考文献和学校格式要求。

### 3. 检查和修复格式风险

对真实论文项目或 synthetic smoke project 运行质量检查：

```bash
python scripts/ucas.py check-format-quality --project-dir examples/thesis-project --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format --project-dir examples/thesis-project --dry-run
```

`check-format-quality` 生成质量报告和 repair feed；`fix-format` 默认只预览
可自动修复项。

### 4. 交付前门禁

分享或打包前运行隐私和发布门禁：

```bash
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --dry-run
```

`pack` 只收录显式 allowlist 中的源码、文档、prompt 和公开示例，避免把本机
路径、私有材料、生成 DOCX/PDF 或本地 agent 文件带入发布包。

## Word 导出规划

本项目的 Word 导出规划聚焦“让用户直接得到可交付 Word”的必要能力。

### 当前已具备

- `prepare-tex`：Word 导出前 TeX 预处理。
- `export-docx`：通过 Pandoc 导出 DOCX。
- `check-format-quality`：快速/完整格式质量检查入口。
- `fix-format`：常见格式问题 dry-run-first 修复入口。
- `check-privacy` 和 `pack`：交付前隐私和打包门禁。
- `examples/thesis-project`：公开 synthetic fixture，包含中英文参考文献、
  双语图题和双语表题样例。

### 近期目标

- 增强 `export-docx` 的 CSL、BibTeX、`citeproc` 支持。
- 增加 BibTeX 清洗，减少 Pandoc DOCX 中的参考文献异常。
- 增加 DOCX 完整性检查和导出报告。
- 定义最小 caption marker 协议，让图题、表题后处理有稳定输入。
- 增加可选 Word 域更新命令，用于刷新目录、图目录、表目录等 Word 域。

### 中期目标

- 增加 `postprocess-docx`，把 DOCX 检查、caption 处理、域更新和报告生成串起来。
- 增加 UCAS Word profile 配置，明确元数据、章节结构、参考文献、图表题注和输出文件约定。
- 增加 `export-final-word`，把 `prepare-tex -> export-docx -> postprocess-docx -> validate` 串成一条可复现命令。

### 交付级目标

- 输出 `final.docx` 和 `final-report.md`。
- 报告目录、页眉页脚、页码、图表题注、参考文献和隐私检查结果。
- 对公开 synthetic project 做自动化回归。
- 对 Windows + Microsoft Word 环境提供可选人工 smoke checklist。

## 常用命令

```bash
python scripts/ucas.py --help
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py check-format --project-dir .
python scripts/ucas.py check-format-quality --project-dir examples/thesis-project --mode fast
python scripts/ucas.py fix-format --project-dir examples/thesis-project --dry-run
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --dry-run
```

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

所有命令都接受 `--project-dir`。默认值是当前工作目录。会修改 TeX 文件的
命令默认 dry-run，确认输出后再显式传入 `--apply`。

## 依赖

必需：

- Python 3.10+

按命令可选：

- `pandoc`：用于 `export-docx`
- `latexmk` 或 `xelatex`：用于 `build-pdf` 和 `build-spine`
- `biber` 或 `bibtex`：当 `latexmk` 不可用且项目产生 bibliography 元数据时使用
- `PyYAML`：当 `check-format-quality` 读取 YAML 规则文件时使用
- Windows + Microsoft Word：后续 Word 域更新和最终 Word smoke 检查会使用

本地 AI skills、subagents 和 prompt 工作流只是开发/写作辅助，不是运行 CLI 的依赖。

## 项目结构

```text
UCAS-Thesis-AI-Delivery-Kit/
├── template/              # minimal synthetic TeX entry points
├── scripts/
│   ├── ucas.py            # unified CLI
│   ├── word_export/       # DOCX export wrapper
│   ├── tex_preprocessing/ # Word-export-oriented TeX preprocessing
│   ├── format_tools/      # format QA and repair utilities
│   └── checks/            # format, privacy, and pack gates
├── docs/
│   ├── word-export/       # Word export notes
│   ├── ai-workflow/       # AI collaboration workflow
│   ├── rules/             # format-rule notes
│   ├── development/       # build process and development notes
│   └── official/          # official-material metadata policy
├── examples/              # public synthetic examples and smoke fixtures
├── prompts/               # reusable AI prompt templates
├── PROVENANCE.md
├── LICENSE-NOTES.md
├── LICENSE
└── README.md
```

## 验证

分享或发布前建议至少运行：

```bash
python -m pytest tests/ -v
python scripts/ucas.py --help
python scripts/ucas.py check-format-quality --project-dir examples/thesis-project --mode fast
python scripts/ucas.py fix-format --project-dir examples/thesis-project --dry-run
python scripts/ucas.py check-privacy --project-dir .
python scripts/ucas.py pack --project-dir . --dry-run
```

可选机器依赖检查：

```bash
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/minimal.docx
```

## 来源与许可

仓库原创代码、文档、prompt 和 synthetic examples 使用 MIT License。

官方 UCAS 材料和任何第三方模板材料必须保留各自来源和再分发边界。本项目通过
[PROVENANCE.md](PROVENANCE.md) 和 [LICENSE-NOTES.md](LICENSE-NOTES.md)
记录这些边界。
