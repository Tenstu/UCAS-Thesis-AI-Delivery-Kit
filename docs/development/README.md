# Development Notes

This repository was initialized as a clean public project, not by copying the
previous thesis working tree.

## Build Process Used For This Scaffold

1. Audit migration boundaries in read-only mode.
2. Create a new project directory and initialize a fresh Git repository.
3. Write provenance, license notes, README, and `.gitignore` before adding tools.
4. Implement a small `python scripts/ucas.py` CLI.
5. Add minimal Word export, format check, privacy check, and pack gate modules.
6. Add synthetic LaTeX examples and Markdown prompt templates.
7. Verify CLI help, privacy checks, format checks, pack dry-run, PDF build, and DOCX export.
8. Keep generated files under ignored paths such as `dist/` and `.latex-cache/`.

## Phase 1/2 Verification Evidence

Current Phase 1/2 verification commands:

```bash
python -m pytest tests/ -v
python scripts/ucas.py --help
python scripts/ucas.py prepare-tex --help
python scripts/ucas.py check-format-quality --help
python scripts/ucas.py fix-format --help
```

The Phase 2 follow-up run on 2026-05-28 passed `57` existing tests plus `4`
new CLI regression tests. The CLI help output lists `prepare-tex`,
`check-format-quality`, and `fix-format`.

`check-format-quality` and `fix-format` are thesis-project commands. They expect
`main.tex` and `extraTex/` under `--project-dir`; running them against this tool
repository root is a usage error, not a successful smoke test.

## Local Skills Referenced During Development

The following local skills guided the implementation process only:

- `brainstorming`: project positioning, MVP boundary, and naming discussion.
- `writing-plans`: implementation plan structure.
- `secrets-hygiene`: token/path/privacy handling while using GitHub CLI.
- `git-commit`: commit preparation and conventional commit guidance.
- `requesting-code-review` / `receiving-code-review`: review and feedback handling.
- `verification-before-completion`: final command-based verification before reporting status.

These skills are not project dependencies and are not required for users.

## Subagent Assistance

Subagents were used for bounded read-only review tasks:

- migration whitelist/blacklist review
- license/provenance/privacy risk review
- README/docs/prompts outline review
- release readiness review

The main thread made final decisions, edited files, ran verification commands,
and prepared the repository for push.
