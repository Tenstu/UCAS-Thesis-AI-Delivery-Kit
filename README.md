# UCAS-Thesis-AI-Delivery-Kit

**UCAS 学位论文 LaTeX -> Word/PDF 交付工具包 | AI 辅助写作 Harness | 格式检查 | 隐私门禁**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pandoc](https://img.shields.io/badge/pandoc-2.0+-green.svg)](https://pandoc.org/)

**关键词**：UCAS 论文、学位论文、LaTeX Word 导出、AI 辅助写作、Harness Engineering、格式检查、隐私门禁、Pandoc、XeLaTeX、学术写作流程

本项目的目标不是再做一套论文模板，而是把”用 LaTeX 写作之后如何交付”
整理成可复用、可检查、可打包的命令行流程。核心贡献是围绕 UCAS 学位
论文场景，提供从 TeX 预处理、DOCX 导出、格式检查、隐私检查到发布打包
的一组公开工具和合成示例。

## 适用场景

- **UCAS 学位论文**：中国科学院大学博士/硕士学位论文的 LaTeX -> Word/PDF 交付
- **AI 辅助写作**：结构化的 AI 协作流程，体现 Harness Engineering 思想
- **格式检查**：自动化格式质量检查和修复
- **隐私门禁**：交付前隐私检查和打包验证

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
- `export-docx`：通过 Pandoc 导出 DOCX，支持 `--reference-doc`、
  `--citeproc`、`--csl` 和重复 `--bibliography`。
- BibTeX 清洗：导出前把 `abstract`、`file`、`keywords` 等本地或冗余字段
  写入 sanitized 临时副本，避免污染 DOCX 引文输出。
- CSL 来源说明：默认不把第三方 CSL 文件打进仓库；GB/T 7714-2015 样式
  可按 [docs/word-export/README.md](docs/word-export/README.md) 的来源说明
  下载后通过 `--csl` 显式传入。
- `check-format-quality`：快速/完整格式质量检查入口。
- `fix-format`：常见格式问题 dry-run-first 修复入口。
- `check-privacy` 和 `pack`：交付前隐私和打包门禁。
- `examples/thesis-project`：公开 synthetic fixture，包含中英文参考文献、
  双语图题和双语表题样例。

### 近期目标

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

## AI 辅助能力

本项目提供一套结构化的 AI 协作流程和 Prompt 模板，用于辅助论文交付全流程。
AI 能力定位为**人工审阅的辅助层**，不是运行 CLI 的依赖，也不绑定特定 agent 框架。

### AI 协作流程（Harness Engineering）

本项目以 **五步写作流程** 为核心，体现了 **Harness Engineering** 的核心思想：将AI能力结构化地集成到人类主导的写作流程中，既利用AI的效率，又保持人类的控制权和学术诚信。

**Harness Engineering 原则**：
- **结构化集成**：五步流程定义了清晰的工作流，AI辅助被结构化地嵌入各阶段
- **人类控制权**：主控角色（人工）负责最终裁定、正文回填、验证和提交
- **可验证性**：每一步都有明确的输入输出，记录与正文分离确保可追溯性
- **职责边界**：明确区分人类和AI的职责，AI作为工具辅助而非替代人类判断

任务型 AI 辅助可以嵌入五步流程中的任何一步，提供针对性支持。

#### 五步写作流程（核心流程）

参考 [ChineseResearchLaTeX - thesis-writing-workflow](https://github.com/Tenstu/ChineseResearchLaTeX/tree/submit-thesis-writing-workflow/skills/thesis-writing-workflow)，五步流程定义了AI在协助论文写作的基本循环：

```text
scan -> adjudicate -> apply -> verify -> deliver
```

1. **Scan（扫描）**：只读检查目标文件，记录候选问题、位置、类型和建议动作
2. **Adjudicate（裁定）**：把候选问题分为"直接处理""需人工确认""延后处理"，并说明原因
3. **Apply（回填）**：只在正式 LaTeX 源文件中小批量回填已裁定修改；过程记录不得成为正文来源
4. **Verify（验证）**：执行目标检索、diff 检查和论文构建命令；涉及图表编号时同步检查引用、标签和图表环境参数
5. **Deliver（交付）**：更新本轮摘要、未决项和人工审阅记录；若后续继续修改，追加新轮次，不覆盖旧记录

#### 任务型 AI 辅助（嵌入五步流程）

单轮任务型 AI 辅助（如章节润色、格式检查、引用核对）可以嵌入五步流程的任意一步，提供针对性支持：

- **Scan 阶段**：使用 `format_audit.md` 或 `reference_check.md` 快速识别问题
- **Adjudicate 阶段**：AI 辅助分类问题优先级，但最终裁定由人工决定
- **Apply 阶段**：使用 `chapter_polish.md` 草拟改写建议，人工确认后回填
- **Verify 阶段**：使用 `export_to_word.md` 检查 Word 导出质量
- **Deliver 阶段**：使用 `delivery_gate.md` 进行交付门禁复核

#### 角色边界

- **主控角色**（人工）：负责最终裁定、正文回填、验证和提交
- **审查角色**（AI）：只输出候选问题，不直接修改正文
- 人工审阅意见先编号和分类，再进入正文回填

#### 记录与正文分离

- 正文源文件是唯一真相源
- 候选问题记录、裁定记录、运行记录、交付记录都保存在隐藏工作目录中
- 公开仓库只提交空模板和流程说明，不提交真实记录

### Prompt 模板

`prompts/` 目录提供 5 个任务型模板，覆盖论文交付全流程：

| 模板 | 用途 | 关键能力 |
|---|---|---|
| `chapter_polish.md` | 章节润色 | 保留 LaTeX 命令/引用/公式，修复逻辑跳跃和口语化，输出改写稿和改动说明 |
| `format_audit.md` | 格式审查 | 检查标题层级、图表题/交叉引用、目录页码、参考文献一致性，只指出有证据的问题 |
| `reference_check.md` | 引用一致性检查 | 检查正文 key 是否存在于 .bib、条目字段缺失、中英文文献格式、重复引用/漏引 |
| `export_to_word.md` | Word 导出质检 | 按 Critical/Important/Minor 分级，区分可自动修复和必须人工复核项 |
| `delivery_gate.md` | 交付门禁复核 | 输出 Pass/Conditional Pass/Blocked 决策，隐私泄漏或官方二进制误入时必须 Blocked |

所有 Prompt 共同特征：角色明确、约束具体、输出格式结构化、强调证据驱动和人工确认。

### AI 辅助边界

AI 可以：
- 发现格式风险和不一致
- 归纳导师/审阅人意见
- 草拟改写建议
- 检查引用和格式一致性

AI 不应替代：
- 学校规范的最终判断
- 导师审阅和学术意见
- 隐私合规判断
- 人工最终验收

详细工作流说明参见：
- 本地文档：[docs/ai-workflow/README.md](docs/ai-workflow/README.md)
- 五步写作流程编排：[ChineseResearchLaTeX - thesis-writing-workflow](https://github.com/Tenstu/ChineseResearchLaTeX/tree/submit-thesis-writing-workflow/skills/thesis-writing-workflow)

## 常用命令

```bash
python scripts/ucas.py --help
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
python scripts/ucas.py export-docx --project-dir examples/thesis-project --citeproc --bibliography examples/thesis-project/bibs/references.bib --output dist/main.docx
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
python scripts/ucas.py export-docx   --project-dir <project> --output dist/main.docx [--reference-doc reference.docx] [--citeproc] [--csl style.csl] [--bibliography refs.bib]
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

## 相关项目

- [ChineseResearchLaTeX](https://github.com/Tenstu/ChineseResearchLaTeX) - 中文研究论文 LaTeX 模板集合（基于 [huangwb8/ChineseResearchLaTeX](https://github.com/huangwb8/ChineseResearchLaTeX) 的个人改进版）
  - [thesis-writing-workflow](https://github.com/Tenstu/ChineseResearchLaTeX/tree/submit-thesis-writing-workflow/skills/thesis-writing-workflow) - 五步写作流程编排（Harness Engineering）
- [UCAS-Dissertation](https://github.com/Tenstu/UCAS-Dissertation) - 中国科学院大学学位论文 LaTeX 模板

本工具包与上述 LaTeX 模板配合使用，提供从 LaTeX 写作到 Word/PDF 交付的完整流程。

## 学术引用

如果您在学术工作中使用了本项目，请引用：

```bibtex
@software{ucas_thesis_ai_delivery_kit,
  author = {Tenstu},
  title = {UCAS-Thesis-AI-Delivery-Kit: LaTeX to Word/PDF Delivery Toolkit for UCAS Theses},
  year = {2026},
  url = {https://github.com/Tenstu/UCAS-Thesis-AI-Delivery-Kit}
}
```

## 来源与许可

仓库原创代码、文档、prompt 和 synthetic examples 使用 MIT License。

官方 UCAS 材料和任何第三方模板材料必须保留各自来源和再分发边界。本项目通过
[PROVENANCE.md](PROVENANCE.md) 和 [LICENSE-NOTES.md](LICENSE-NOTES.md)
记录这些边界。
