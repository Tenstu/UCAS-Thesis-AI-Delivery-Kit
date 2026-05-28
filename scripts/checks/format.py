from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TEX_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("warning", "double dollar display math", re.compile(r"\$\$")),
    ("warning", "figure/table float uses broad htbp placement", re.compile(r"\\begin\{(?:figure|table)\}\[!?(?:htbp|hbp|tbp)\]")),
    ("warning", "citation command followed by Chinese punctuation spacing risk", re.compile(r"\\cite[tp]?\{[^}]+\}\s+[，。；：,.;:]")),
    ("error", "unresolved placeholder marker", re.compile(r"TODO|FIXME|待补|待确认")),
]


@dataclass(frozen=True)
class FormatIssue:
    path: Path
    line: int
    level: str
    message: str

    def format(self, root: Path) -> str:
        rel = self.path.relative_to(root) if self.path.is_relative_to(root) else self.path
        return f"[{self.level}] {rel}:{self.line} - {self.message}"


def scan_format(root: Path) -> list[FormatIssue]:
    root = root.resolve()
    issues: list[FormatIssue] = []
    ignored = {".git", ".latex-cache", "dist", "build", "__pycache__"}

    for path in root.rglob("*.tex"):
        if any(part in ignored for part in path.relative_to(root).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, line in enumerate(text.splitlines(), start=1):
            for level, message, pattern in TEX_PATTERNS:
                if pattern.search(line):
                    issues.append(FormatIssue(path, index, level, message))
    return issues
