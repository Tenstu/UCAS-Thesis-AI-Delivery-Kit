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

## Expectations

- `prepare-tex` normalizes CJK/Latin/number spacing and common time-unit spacing
  while protecting LaTeX commands and math segments.
- 这是“可审 Word 草稿”导出，不保证直接满足最终提交格式。
- 目录、页眉页脚、封面、书脊、图表目录、复杂公式和浮动体都需要人工复核。
- 官方 UCAS Word 模板默认不提交到仓库；只记录来源、checksum 和本地放置建议。

## Future Work

- DOCX 后处理。
- 参考模板样式对齐。
- Word 域更新和图表目录刷新。
- 更严格的质量报告。
