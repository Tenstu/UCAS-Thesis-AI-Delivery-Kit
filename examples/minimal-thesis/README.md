# Minimal Thesis Example

当前 PDF/DOCX 最小示例使用 `template/tex/`。

```bash
python scripts/ucas.py build-pdf --project-dir template/tex
python scripts/ucas.py export-docx --project-dir template/tex --output dist/minimal.docx
python scripts/ucas.py check-format --project-dir template/tex
```

示例文本全部为合成内容，不含真实论文材料。

Phase 2 格式质量和修复工具需要 thesis project root，即 `main.tex` 加
`extraTex/`。对应 smoke 示例在 `examples/thesis-project/`：

```bash
python scripts/ucas.py check-format-quality --project-dir examples/thesis-project --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format --project-dir examples/thesis-project --dry-run
```
