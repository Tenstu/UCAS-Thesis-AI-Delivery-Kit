# Format Rules

本目录记录 UCAS 学位论文格式规则和本项目自动检查口径。

## Current Automated Checks

`python scripts/ucas.py check-format --project-dir .` 当前只做轻量 TeX 文本扫描：

- `$$ ... $$` 显示公式风险。
- 图表浮动参数过宽。
- 引用命令与中英文标点间距风险。
- `TODO`、`FIXME`、`待补`、`待确认` 等未清理标记。

## Manual Review Items

这些项目暂不由 MVP 自动判断：

- 封面、声明页、书脊。
- 目录、图表目录和页码。
- 页眉页脚。
- 图题、表题、跨页表。
- 参考文献格式。
- Word 与 PDF 的版面差异。

后续规则应优先写成可解释检查项，再决定是否自动化。

## Phase 2 Quality And Repair

`check-format-quality` adds a deeper thesis-project quality pass:

```bash
python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py check-format-quality --project-dir <thesis-project> --mode full --emit-markdown
```

Use `fix-format` only after reviewing the report or repair feed:

```bash
python scripts/ucas.py fix-format --project-dir <thesis-project> --dry-run
python scripts/ucas.py fix-format --project-dir <thesis-project> --issues-json .latex-cache/format-fix/latest_check.json --apply
```

These commands expect a thesis project root containing `main.tex` and
`extraTex/`. Running them against the tool repository root is expected to fail
because the root is not itself a thesis project.

Generated reports and feeds are written under `.latex-cache/quality-check/` and
`.latex-cache/format-fix/`. Automated repair is intentionally dry-run by default;
human review remains required before applying edits.
