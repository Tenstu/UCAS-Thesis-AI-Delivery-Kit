from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".bib",
    ".cls",
    ".csv",
    ".json",
    ".lua",
    ".md",
    ".py",
    ".sty",
    ".tex",
    ".txt",
    ".yaml",
    ".yml",
}

IGNORED_DIRS = {
    ".git",
    ".latex-cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "tmp",
}

DENY_DIR_NAMES = {
    ".chatmem",
    ".claude",
    ".codex",
    ".mempalace",
    ".serena",
    "hooks",
    "logs",
    "memory",
    "private",
    "references_local",
    "workdirs",
}

SUSPICIOUS_BINARY_SUFFIXES = {
    ".7z",
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".xls",
    ".xlsx",
    ".zip",
}

CONTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("windows absolute path", re.compile(r"\b[A-Za-z]:[\\/][^\s)>\"]+")),
    ("unc path", re.compile(r"\\\\[A-Za-z0-9._-]+\\[A-Za-z0-9.$_-]+(?:\\[^\s)>\"]*)?")),
    ("wsl absolute path", re.compile(r"/mnt/[a-z]/[^\s)>\"]+", re.I)),
    ("unix home path", re.compile(r"(?<!\w)/(?:Users|home)/[A-Za-z0-9._-]+/[^\s)>\"]+")),
    ("api key assignment", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}")),
    ("private key block", re.compile(r"-----BEGIN (?:OPENSSH|RSA|DSA|EC|PRIVATE) KEY-----")),
    ("private workflow path", re.compile(r"(?i)(?:^|[\\/])(?:private|personal|workdirs|final-delivery|references_local|paper-fetch|mineru-output)(?:[\\/]|$)")),
    ("local agent marker", re.compile(r"(?i)\b(?:\\.codex|\\.claude|\\.serena|\\.mempalace|\\.chatmem)\b")),
    ("uncleared author placeholder", re.compile(r"待作者确认|NUL")),
]


@dataclass(frozen=True)
class PrivacyIssue:
    path: Path
    line: int
    level: str
    message: str

    def format(self, root: Path) -> str:
        rel = self.path.relative_to(root) if self.path.is_relative_to(root) else self.path
        loc = f"{rel}" if self.line == 0 else f"{rel}:{self.line}"
        return f"[{self.level}] {loc} - {self.message}"


def _iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def scan_privacy(root: Path, paths: list[Path] | None = None) -> list[PrivacyIssue]:
    root = root.resolve()
    issues: list[PrivacyIssue] = []

    source_paths = paths if paths is not None else list(_iter_files(root))
    for path in source_paths:
        path = path.resolve()
        rel_parts = path.relative_to(root).parts
        lower_parts = {part.lower() for part in rel_parts}

        blocked_dirs = lower_parts.intersection(DENY_DIR_NAMES)
        if blocked_dirs:
            issues.append(
                PrivacyIssue(path, 0, "error", f"file is inside blocked private directory: {sorted(blocked_dirs)[0]}")
            )

        if path.suffix.lower() in SUSPICIOUS_BINARY_SUFFIXES:
            issues.append(
                PrivacyIssue(path, 0, "error", "high-risk binary or archive file found; keep official, private, and generated assets outside releases by default")
            )

        text = _read_text(path)
        if text is None:
            continue

        for index, line in enumerate(text.splitlines(), start=1):
            if path.name == "privacy.py" and "re.compile" in line:
                continue
            for name, pattern in CONTENT_PATTERNS:
                if pattern.search(line):
                    issues.append(PrivacyIssue(path, index, "error", f"suspicious {name}"))

    return issues
