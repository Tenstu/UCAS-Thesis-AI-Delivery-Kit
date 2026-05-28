# License Notes

This project is intended to be published as a clean public repository. The
repository-original code, documentation, prompts, and synthetic examples use the
MIT License in `LICENSE`.

## Source Boundaries

- `UCAS-Dissertation`-derived template code, if imported later, must keep
  upstream attribution, commit information, and license notices. Do not claim
  this lineage before it is verified.
- Workflow ideas learned from `ChineseResearchLaTeX` may be rewritten here as
  clean documentation or standalone scripts, but private thesis content,
  workdirs, run logs, local paths, and agent memory must not be copied.
- UCAS official `.doc`, `.docx`, `.pdf`, or `.pptx` files should be described by
  source, access date, checksum, and expected local placement. They should not be
  committed by default.
- New code and documentation written directly for this repository are covered by
  the repository `LICENSE`.

## Before Public Release

1. Confirm the exact upstream license of any imported template files.
2. Replace this private license with an appropriate public license only if the
   whole repository is publishable.
3. Keep `PROVENANCE.md` current.
4. Run `python scripts/ucas.py check-privacy --project-dir .`.
5. Run `python scripts/ucas.py pack --project-dir . --output dist/<name>.zip`.

## Release Interpretation

For a public release, original code, original documentation, prompt templates,
and synthetic examples in this repository may be handled under the repository
`LICENSE`.

Any imported upstream template, official material, or third-party content must
follow its own license and redistribution terms. The repository `LICENSE` does
not relicense those materials.

Release contents should be classified before publication:

- repository-original code and documentation
- synthetic examples
- imported upstream content with preserved notices
- official binary originals or private materials, which are excluded by default
