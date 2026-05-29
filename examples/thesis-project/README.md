# Minimal Thesis Project

This synthetic example is a thesis-project-root fixture for Phase 2 tools. It is
not a complete UCAS dissertation template.

Required smoke commands:

```bash
python scripts/ucas.py check-format-quality --project-dir examples/thesis-project --mode fast --emit-json --emit-repair-feed
python scripts/ucas.py fix-format --project-dir examples/thesis-project --dry-run
```

The project intentionally contains a small, fixable formatting sample in
`extraTex/chapter1.tex` so that the repair feed and dry-run repair path can be
exercised without touching private thesis content.

Phase 3 Word export extraction fixtures are also synthetic:

- `bibs/references.bib` contains one Chinese and one English bibliography
  record for future CSL/BibTeX command tests.
- `extraTex/word_export_fixtures.tex` contains one bilingual figure caption and
  one bilingual table caption for future marker and DOCX postprocess tests.
