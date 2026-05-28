#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


DEFAULT_PROJECT_DIR = Path.cwd()
DEFAULT_OUTPUT_DIR = Path(".latex-cache") / "format-fix"
DEFAULT_QUALITY_DIR = Path(".latex-cache") / "quality-check"
DEFAULT_ISSUES_JSON = DEFAULT_OUTPUT_DIR / "latest_check.json"
DEFAULT_SUMMARY_JSON = DEFAULT_OUTPUT_DIR / "latest_repair.json"
DEFAULT_SUMMARY_MD = DEFAULT_OUTPUT_DIR / "latest_repair.md"
DEFAULT_ERROR_LIBRARY = Path(__file__).resolve().parent / "format_error_library.yaml"

F_STAT_PATTERN = re.compile(r"F\s*[（(]\s*(\d+)\s*[,，]\s*(\d+)\s*[)）]")
CJK_ABBR_LEFT_PATTERN = re.compile(r"([\u4e00-\u9fff])[ \t]+(Cd|Se)(?![A-Za-z])")
CJK_ABBR_RIGHT_PATTERN = re.compile(r"(?<![A-Za-z])(Cd|Se)[ \t]+([\u4e00-\u9fff])")
REF_TILDE_BEFORE_PUNCT_PATTERN = re.compile(
    r"~[ \t]*(\\(?:ref|eqref|pageref)\{[^}]+\})(?=[，。；：,.!?！？])"
)
REF_SPACE_BEFORE_PUNCT_PATTERN = re.compile(
    r"(\\(?:ref|eqref|pageref)\{[^}]+\})[ \t]+(?=[，。；：,.!?！？])"
)
MACROBUTTON_PATTERN = re.compile(r"MACROBUTTON[ \t]+AcceptAllChangesShown", re.IGNORECASE)
HTBP_PATTERN = re.compile(r"\[\s*htbp\s*\]")
TIME_UNIT_SPACING_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)[ \t]+(mg/kg|rpm|d|g)(?=$|[^A-Za-z/])"
)
STAT_EXPR_SPACING_PATTERN = re.compile(
    r"(?<![A-Za-z])([Pprn])([=<>])(-?\d+(?:\.\d+)?)(?![A-Za-z])"
)
SIMPLE_STAT_INLINE_MATH_PATTERN = re.compile(
    r"\$\s*([Pprn])\s*(<=|>=|=|<|>)\s*(-?\d+(?:\.\d+)?)\s*\$"
)
INLINE_MATH_SEGMENT_PATTERN = re.compile(r"(\$[^$]*\$)")


def _fix_stat_f_format(text: str) -> tuple[str, int]:
    changes = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal changes
        canonical = f"F({match.group(1)},{match.group(2)})"
        if match.group(0) != canonical:
            changes += 1
            return canonical
        return match.group(0)

    return F_STAT_PATTERN.sub(repl, text), changes


def _fix_mixed_abbr_spacing(text: str) -> tuple[str, int]:
    fixed = 0
    text, count1 = CJK_ABBR_LEFT_PATTERN.subn(r"\1\2", text)
    text, count2 = CJK_ABBR_RIGHT_PATTERN.subn(r"\1\2", text)
    fixed += count1 + count2
    return text, fixed


def _fix_time_unit_spacing(text: str) -> tuple[str, int]:
    return TIME_UNIT_SPACING_PATTERN.subn(r"\1~\2", text)


def _fix_stat_expr_spacing(text: str) -> tuple[str, int]:
    changes = 0
    lines = text.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        segments = INLINE_MATH_SEGMENT_PATTERN.split(line)
        line_changed = 0
        for seg_idx, segment in enumerate(segments):
            if seg_idx % 2 == 1:
                continue
            fixed_segment, count = STAT_EXPR_SPACING_PATTERN.subn(r"\1 \2 \3", segment)
            if count > 0:
                line_changed += count
                segments[seg_idx] = fixed_segment
        if line_changed > 0:
            changes += line_changed
            lines[idx] = "".join(segments)
    return "".join(lines), changes


def _fix_simple_stat_inline_math(text: str) -> tuple[str, int]:
    return SIMPLE_STAT_INLINE_MATH_PATTERN.subn(r"\1 \2 \3", text)


def _fix_ref_tilde_before_punct(text: str) -> tuple[str, int]:
    return REF_TILDE_BEFORE_PUNCT_PATTERN.subn(r"\1", text)


def _fix_ref_space_before_punct(text: str) -> tuple[str, int]:
    return REF_SPACE_BEFORE_PUNCT_PATTERN.subn(r"\1", text)


def _fix_latex_artifact_macrobutton(text: str) -> tuple[str, int]:
    return MACROBUTTON_PATTERN.subn("", text)


def _fix_latex_artifact_htbp(text: str) -> tuple[str, int]:
    fixed = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal fixed
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start : match.start()].rstrip()
        if prefix.endswith(r"\begin{figure}") or prefix.endswith(r"\begin{table}"):
            return match.group(0)
        fixed += 1
        return ""

    return HTBP_PATTERN.sub(repl, text), fixed


FIXERS: dict[str, Callable[[str], tuple[str, int]]] = {
    "STAT_F_FORMAT": _fix_stat_f_format,
    "MIXED_ABBR_SPACING": _fix_mixed_abbr_spacing,
    "TIME_UNIT_SPACING": _fix_time_unit_spacing,
    "SIMPLE_STAT_INLINE_MATH": _fix_simple_stat_inline_math,
    "STAT_EXPR_SPACING": _fix_stat_expr_spacing,
    "REF_TILDE_BEFORE_PUNCT": _fix_ref_tilde_before_punct,
    "REF_SPACE_BEFORE_PUNCT": _fix_ref_space_before_punct,
    "LATEX_ARTIFACT_MACROBUTTON": _fix_latex_artifact_macrobutton,
    "LATEX_ARTIFACT_HTBP": _fix_latex_artifact_htbp,
}

FIXER_ORDER = [
    "STAT_F_FORMAT",
    "MIXED_ABBR_SPACING",
    "TIME_UNIT_SPACING",
    "SIMPLE_STAT_INLINE_MATH",
    "STAT_EXPR_SPACING",
    "REF_TILDE_BEFORE_PUNCT",
    "REF_SPACE_BEFORE_PUNCT",
    "LATEX_ARTIFACT_MACROBUTTON",
    "LATEX_ARTIFACT_HTBP",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_latest_quality_report_json(project_dir: Path, mode: str = "fast") -> Path | None:
    quality_dir = (project_dir / DEFAULT_QUALITY_DIR).resolve()
    if not quality_dir.exists():
        return None
    candidates = sorted(quality_dir.glob(f"format_quality_{mode}_*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _read_related_new_issue_count(path: Path) -> int | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return None
    value = summary.get("new_issue")
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _count_by_code(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        code = str(item.get("code", "UNKNOWN"))
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _safe_issue(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_id": str(issue.get("issue_id", "")),
        "code": str(issue.get("code", "UNKNOWN")),
        "file": str(issue.get("file", "")),
        "line": int(issue.get("line", 0) or 0),
        "message": str(issue.get("message", "")),
        "snippet": str(issue.get("snippet", "")),
        "fixable": bool(issue.get("fixable", False)),
        "recommended_fix": str(issue.get("recommended_fix", "")),
    }


def _suggested_plan_for_code(code: str) -> str:
    suggestions = {
        "PLACEHOLDER_TOKEN": "补齐占位词对应证据并删除占位文本。",
        "DOUBLE_DOLLAR_MATH": "将 $$ 数学块改写为 \\[...\\] 并复核多行公式布局。",
        "SIMPLE_STAT_INLINE_MATH": "去掉简单统计表达外层 `$...$`，并统一为空格分隔的正文写法。",
        "LATEX_ARTIFACT_ESCAPED_ENV": "确认是否应恢复为真实环境命令，避免文本伪影进入正文。",
    }
    return suggestions.get(code, "补充该问题类型的规则与自动修复映射。")


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value == "null":
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {"version": 1, "updated_at": "", "items": []}
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("version:"):
            result["version"] = _parse_scalar(line.split(":", 1)[1])
            continue
        if line.startswith("updated_at:"):
            result["updated_at"] = _parse_scalar(line.split(":", 1)[1])
            continue
        if line.startswith("items:"):
            continue
        if line.startswith("  - "):
            current = {}
            items.append(current)
            fragment = line[4:]
            if ":" in fragment:
                key, value = fragment.split(":", 1)
                current[key.strip()] = _parse_scalar(value)
            continue
        if line.startswith("    ") and current is not None and ":" in line.strip():
            key, value = line.strip().split(":", 1)
            current[key.strip()] = _parse_scalar(value)
    result["items"] = items
    return result


def _load_error_library(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "updated_at": "", "items": []}
    text = path.read_text(encoding="utf-8")

    parsed: dict[str, Any] | None = None
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            parsed = loaded
    except Exception:
        parsed = None

    if parsed is None:
        parsed = _parse_simple_yaml(text)

    items = parsed.get("items", [])
    if not isinstance(items, list):
        items = []
    normalized_items: list[dict[str, Any]] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        normalized_items.append(
            {
                "code": str(raw_item.get("code", "UNKNOWN")),
                "first_seen": str(raw_item.get("first_seen", "")),
                "last_seen": str(raw_item.get("last_seen", "")),
                "count": int(raw_item.get("count", 0) or 0),
                "sample_file": str(raw_item.get("sample_file", "")),
                "sample_line": int(raw_item.get("sample_line", 0) or 0),
                "sample_snippet": str(raw_item.get("sample_snippet", "")),
                "suggested_plan": str(raw_item.get("suggested_plan", "")),
                "status": str(raw_item.get("status", "open")),
            }
        )
    return {
        "version": int(parsed.get("version", 1) or 1),
        "updated_at": str(parsed.get("updated_at", "")),
        "items": normalized_items,
    }


def _yaml_quote(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _write_error_library(path: Path, library: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"version: {int(library.get('version', 1) or 1)}")
    lines.append(f"updated_at: {_yaml_quote(library.get('updated_at', ''))}")
    lines.append("items:")
    items = library.get("items", [])
    if not items:
        lines.append("  []")
    else:
        for item in items:
            lines.append(f"  - code: {_yaml_quote(item.get('code', 'UNKNOWN'))}")
            lines.append(f"    first_seen: {_yaml_quote(item.get('first_seen', ''))}")
            lines.append(f"    last_seen: {_yaml_quote(item.get('last_seen', ''))}")
            lines.append(f"    count: {_yaml_quote(int(item.get('count', 0) or 0))}")
            lines.append(f"    sample_file: {_yaml_quote(item.get('sample_file', ''))}")
            lines.append(f"    sample_line: {_yaml_quote(int(item.get('sample_line', 0) or 0))}")
            lines.append(f"    sample_snippet: {_yaml_quote(item.get('sample_snippet', ''))}")
            lines.append(f"    suggested_plan: {_yaml_quote(item.get('suggested_plan', ''))}")
            lines.append(f"    status: {_yaml_quote(item.get('status', 'open'))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _update_error_library(path: Path, unresolved_issues: list[dict[str, Any]]) -> dict[str, Any]:
    library = _load_error_library(path)
    now_day = datetime.now().date().isoformat()
    items_by_code = {item.get("code", "UNKNOWN"): item for item in library.get("items", [])}

    for issue in unresolved_issues:
        code = issue.get("code", "UNKNOWN")
        entry = items_by_code.get(code)
        if entry is None:
            entry = {
                "code": code,
                "first_seen": now_day,
                "last_seen": now_day,
                "count": 0,
                "sample_file": issue.get("file", ""),
                "sample_line": issue.get("line", 0),
                "sample_snippet": issue.get("snippet", ""),
                "suggested_plan": _suggested_plan_for_code(code),
                "status": "open",
            }
            items_by_code[code] = entry
        entry["count"] = int(entry.get("count", 0) or 0) + 1
        entry["last_seen"] = now_day
        if not entry.get("sample_file"):
            entry["sample_file"] = issue.get("file", "")
            entry["sample_line"] = issue.get("line", 0)
            entry["sample_snippet"] = issue.get("snippet", "")
        if not entry.get("suggested_plan"):
            entry["suggested_plan"] = _suggested_plan_for_code(code)
        if not entry.get("status"):
            entry["status"] = "open"

    sorted_items = sorted(
        items_by_code.values(),
        key=lambda item: (-int(item.get("count", 0) or 0), str(item.get("code", ""))),
    )
    library["items"] = sorted_items
    library["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_error_library(path, library)
    return library


def _build_markdown_summary(
    *,
    generated_at: str,
    issues_json: Path,
    dry_run: bool,
    backup_dir: Path | None,
    updated_files: list[str],
    fixed_issues: int,
    remaining_issues: list[dict[str, Any]],
    total_issues: int,
    fixable_issues: int,
    fixed_by_code: dict[str, int],
    remaining_by_code: dict[str, int],
    error_library: Path,
    related_new_issue_count: int | None,
    quality_report_json: Path | None,
) -> str:
    lines: list[str] = []
    lines.append("# TeX 模式修复报告")
    lines.append("")
    lines.append(f"- 生成时间：`{generated_at}`")
    lines.append(f"- 执行模式：`{'dry-run（仅预演，不落盘）' if dry_run else 'apply（写回修复）'}`")
    lines.append(f"- 输入巡检：`{issues_json}`")
    if dry_run:
        lines.append("- 备份目录：`未生成（dry-run 不写回）`")
    else:
        lines.append(f"- 备份目录：`{backup_dir}`" if backup_dir is not None else "- 备份目录：`未生成（无文件改动）`")
    lines.append(f"- 更新文件数：`{len(updated_files)}`")
    lines.append(f"- 总问题数：`{total_issues}`")
    lines.append(f"- 可修复问题数：`{fixable_issues}`")
    lines.append(f"- 已修复问题数：`{fixed_issues}`")
    lines.append(f"- 剩余问题数：`{len(remaining_issues)}`")
    lines.append(f"- 错误库：`{error_library}`")
    if quality_report_json is not None:
        lines.append(f"- 关联巡检报告：`{quality_report_json}`")
    lines.append(
        "- 关联巡检新增问题：`{}`".format(related_new_issue_count if related_new_issue_count is not None else "unknown")
    )
    lines.append("")
    lines.append("## 修复分布")
    lines.append("")
    lines.append("| code | fixed | remaining |")
    lines.append("|---|---:|---:|")
    all_codes = sorted(set(fixed_by_code) | set(remaining_by_code))
    if all_codes:
        for code in all_codes:
            lines.append(f"| `{code}` | {fixed_by_code.get(code, 0)} | {remaining_by_code.get(code, 0)} |")
    else:
        lines.append("| `-` | 0 | 0 |")
    lines.append("")
    lines.append("## 更新文件")
    lines.append("")
    if updated_files:
        for file_path in updated_files:
            lines.append(f"- `{file_path}`")
    else:
        lines.append("- 无文件被修改。")
    lines.append("")
    lines.append("## 未修复问题样例（前 30 条）")
    lines.append("")
    lines.append("| issue_id | code | file | line | fixable | snippet |")
    lines.append("|---|---|---|---:|---|---|")
    if remaining_issues:
        for issue in remaining_issues[:30]:
            snippet = str(issue.get("snippet", "")).replace("|", r"\|")
            lines.append(
                "| "
                f"`{issue.get('issue_id', '')}` | `{issue.get('code', '')}` | "
                f"`{issue.get('file', '')}` | {issue.get('line', 0)} | "
                f"{'yes' if issue.get('fixable', False) else 'no'} | `{snippet}` |"
            )
    else:
        lines.append("| `-` | `-` | `-` | 0 | no | `-` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="UCAS TeX 格式模式修复脚本")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="项目根目录（默认：当前脚本上级目录）",
    )
    parser.add_argument(
        "--issues-json",
        type=Path,
        default=None,
        help="巡检 JSON 路径（默认：<project>/.latex-cache/format-fix/latest_check.json）",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="修复摘要 JSON 路径（默认：<project>/.latex-cache/format-fix/latest_repair.json）",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=None,
        help="修复摘要 Markdown 路径（默认：<project>/.latex-cache/format-fix/latest_repair.md）",
    )
    parser.add_argument(
        "--error-library",
        type=Path,
        default=DEFAULT_ERROR_LIBRARY,
        help="错误库 YAML 路径（默认：scripts/format_error_library.yaml）",
    )
    parser.add_argument(
        "--quality-report-json",
        type=Path,
        default=None,
        help="关联的巡检 JSON 报告路径（默认：自动选择最新 format_quality_fast_*.json）",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="显式执行写回模式：修复命中并更新备份/摘要（默认行为）。",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="只预演修复并输出摘要，不写回文件、不生成备份，也不更新错误库。",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.expanduser().resolve()
    issues_json = (args.issues_json or project_dir / DEFAULT_ISSUES_JSON).expanduser().resolve()
    summary_json = (args.summary_json or project_dir / DEFAULT_SUMMARY_JSON).expanduser().resolve()
    summary_md = (args.summary_md or project_dir / DEFAULT_SUMMARY_MD).expanduser().resolve()
    error_library = args.error_library.expanduser().resolve()
    quality_report_json = (
        args.quality_report_json.expanduser().resolve()
        if args.quality_report_json is not None
        else _find_latest_quality_report_json(project_dir, mode="fast")
    )

    if not project_dir.exists():
        raise SystemExit(f"项目目录不存在：{project_dir}")
    if not issues_json.exists():
        raise SystemExit(f"巡检结果不存在：{issues_json}。请先运行 check_format_quality.py。")

    raw_payload = _read_json(issues_json)
    raw_issues = raw_payload.get("issues", [])
    if not isinstance(raw_issues, list):
        raise SystemExit(f"巡检 JSON 格式无效：{issues_json}")
    issues = [_safe_issue(item) for item in raw_issues]

    fixable_issues = [item for item in issues if item["fixable"] and item["code"] in FIXERS]
    fixable_by_file: dict[str, set[str]] = {}
    for issue in fixable_issues:
        fixable_by_file.setdefault(issue["file"], set()).add(issue["code"])

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = project_dir / DEFAULT_OUTPUT_DIR / "backups" / timestamp
    backup_created = False

    updated_files: list[str] = []
    applied_counts: dict[tuple[str, str], int] = {}

    for relative_file, codes in sorted(fixable_by_file.items()):
        abs_file = (project_dir / relative_file).resolve()
        if not abs_file.exists():
            continue
        original = abs_file.read_text(encoding="utf-8")
        repaired = original
        touched = False
        for code in FIXER_ORDER:
            if code not in codes:
                continue
            fixer = FIXERS[code]
            repaired, changed = fixer(repaired)
            if changed > 0:
                applied_counts[(relative_file, code)] = applied_counts.get((relative_file, code), 0) + changed
                touched = True
        if touched and repaired != original:
            if not args.dry_run:
                backup_path = backup_root / relative_file
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(abs_file, backup_path)
                backup_created = True
                abs_file.write_text(repaired, encoding="utf-8", newline="\n")
            updated_files.append(relative_file)

    fixed_issue_ids: set[str] = set()
    remaining_budget = dict(applied_counts)
    for issue in issues:
        if not issue["fixable"] or issue["code"] not in FIXERS:
            continue
        key = (issue["file"], issue["code"])
        budget = remaining_budget.get(key, 0)
        if budget > 0:
            fixed_issue_ids.add(issue["issue_id"])
            remaining_budget[key] = budget - 1

    remaining_issues = [item for item in issues if item["issue_id"] not in fixed_issue_ids]
    fixed_issues = [item for item in issues if item["issue_id"] in fixed_issue_ids]

    if not args.dry_run:
        _update_error_library(error_library, remaining_issues)
    generated_at = datetime.now().isoformat(timespec="seconds")

    fixed_by_code = _count_by_code(fixed_issues)
    remaining_by_code = _count_by_code(remaining_issues)
    related_new_issue_count = None
    if quality_report_json is not None and quality_report_json.exists():
        related_new_issue_count = _read_related_new_issue_count(quality_report_json)

    summary_payload = {
        "generated_at": generated_at,
        "dry_run": bool(args.dry_run),
        "project_dir": str(project_dir),
        "issues_json": str(issues_json),
        "backup_dir": str(backup_root) if backup_created else "",
        "updated_files": updated_files,
        "total_issues": len(issues),
        "fixable_issues": len([item for item in issues if item["fixable"]]),
        "fixed_issues": len(fixed_issues),
        "remaining_issues": len(remaining_issues),
        "remaining_fixable_issues": len([item for item in remaining_issues if item["fixable"]]),
        "fixed_by_code": fixed_by_code,
        "remaining_by_code": remaining_by_code,
        "error_library": str(error_library),
        "quality_report_json": str(quality_report_json) if quality_report_json is not None else "",
        "related_new_issue_count": related_new_issue_count,
    }
    _write_json(summary_json, summary_payload)

    summary_md_text = _build_markdown_summary(
        generated_at=generated_at,
        issues_json=issues_json,
        backup_dir=backup_root if backup_created else None,
        updated_files=updated_files,
        fixed_issues=len(fixed_issues),
        remaining_issues=remaining_issues,
        total_issues=len(issues),
        fixable_issues=len([item for item in issues if item["fixable"]]),
        fixed_by_code=fixed_by_code,
        remaining_by_code=remaining_by_code,
        error_library=error_library,
        related_new_issue_count=related_new_issue_count,
        dry_run=bool(args.dry_run),
        quality_report_json=quality_report_json,
    )
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(summary_md_text + "\n", encoding="utf-8")

    print(
        "[format-repair] "
        f"mode={'dry-run' if args.dry_run else 'apply'} "
        f"total={len(issues)} fixed={len(fixed_issues)} "
        f"remaining={len(remaining_issues)} updated_files={len(updated_files)}"
    )
    if backup_created:
        print(f"[format-repair] backups={backup_root}")
    print(f"[format-repair] summary_json={summary_json}")
    print(f"[format-repair] summary_md={summary_md}")
    print(f"[format-repair] error_library={error_library}")
    if quality_report_json is not None:
        print(f"[format-repair] quality_report_json={quality_report_json}")
    if related_new_issue_count is not None:
        print(f"[format-repair] related_new_issue_count={related_new_issue_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
