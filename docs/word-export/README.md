# Word Export

Word 导出是本项目的核心能力之一，但 MVP 只提供 beta 级 pandoc wrapper。

## Command

Run TeX preprocessing first and review the proposed edits:

```bash
python scripts/ucas.py prepare-tex --project-dir template/tex --dry-run
```

Apply only after reviewing the dry-run output:

```bash
python scripts/ucas.py prepare-tex --project-dir template/tex --apply
```

Then export DOCX:

```bash
python scripts/ucas.py export-docx --project-dir template/tex --output dist/main.docx
```

可选传入参考 Word 样式：

```bash
python scripts/ucas.py export-docx \
  --project-dir template/tex \
  --reference-doc path/to/reference.docx \
  --output dist/main.docx
```

可选启用 Pandoc citation processing，并传入 CSL 与 BibTeX：

```bash
python scripts/ucas.py export-docx \
  --project-dir examples/thesis-project \
  --citeproc \
  --csl path/to/style.csl \
  --bibliography examples/thesis-project/bibs/references.bib \
  --output dist/main.docx
```

`--bibliography` 可以重复传入。导出前，Kit 会把 BibTeX 写入
`.latex-cache/word-export/` 下的 sanitized 副本，并移除 `abstract`、
`file`、`keywords` 等不适合进入 Word 引文输出的字段。

## Expectations

- `prepare-tex` normalizes CJK/Latin/number spacing and common time-unit spacing
  while protecting LaTeX commands and math segments.
- 这是“可审 Word 草稿”导出，不保证直接满足最终提交格式。
- 目录、页眉页脚、封面、书脊、图表目录、复杂公式和浮动体都需要人工复核。
- 官方 UCAS Word 模板默认不提交到仓库；只记录来源、checksum 和本地放置建议。

## Phase 3 Boundary

Supported in the Phase 3 extraction plan:

- Synthetic fixtures for mixed Chinese/English bibliography records in
  `examples/thesis-project/bibs/references.bib`.
- Synthetic bilingual figure and table captions in
  `examples/thesis-project/extraTex/word_export_fixtures.tex`.
- Pandoc citation command construction with `--citeproc`, `--csl`, and repeated
  `--bibliography`.
- Future small commands for optional Word field updates, caption markers, and
  lightweight DOCX integrity reports.

Unsupported in the Delivery Kit unless a later PR adds a narrow contract:

- UCAS cover metadata synchronization.
- UCAS front/back matter section, header/footer, and page-number rules.
- Full figure/table catalog page-number materialization.
- Word OpenAndRepair as part of a large thesis-specific postprocess chain.
- Private thesis content, official binary templates, and generated DOCX/PDF
  deliverables.

No generated DOCX fixture is committed in PR 1. A future field-update fixture
must either be generated deterministically during tests or be introduced only
after its source and redistribution safety are documented.

## Future Work

- DOCX 后处理。
- 参考模板样式对齐。
- Word 域更新和图表目录刷新。
- 更严格的质量报告。
