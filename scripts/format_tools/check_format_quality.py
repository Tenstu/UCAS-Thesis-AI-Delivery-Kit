#!/usr/bin/env python3
"""UCAS 项目格式巡检脚本（Fast + Full）。

目标：
1) 统一读取 DOCX 质量报告、LaTeX 日志和静态规则扫描结果。
2) 输出终端摘要 + JSON + Markdown 报告。
3) 默认只统计不阻断：无论发现问题与否，退出码始终为 0。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


DEFAULT_RULES_REL = Path("docs/rules/ucas_format_rules.yaml")
DEFAULT_OUT_DIR_REL = Path(".latex-cache/quality-check")
DEFAULT_REPAIR_FEED_REL = Path(".latex-cache/format-fix/latest_check.json")
DEFAULT_DOCX_REPORT_NAME = "quality_report.md"
DEFAULT_MAIN_LOG_REL = Path(".latex-cache/main.log")

F_STAT_PATTERN = re.compile(r"F\s*[（(]\s*(\d+)\s*[,，]\s*(\d+)\s*[)）]")
CJK_ABBR_LEFT_PATTERN = re.compile(r"([\u4e00-\u9fff])[ \t]+(Cd|Se)(?![A-Za-z])")
CJK_ABBR_RIGHT_PATTERN = re.compile(r"(?<![A-Za-z])(Cd|Se)[ \t]+([\u4e00-\u9fff])")
REF_TILDE_BEFORE_PUNCT_PATTERN = re.compile(
    r"~[ \t]*\\(?:ref|eqref|pageref)\{[^}]+\}(?=[，。；：,.!?！？])"
)
REF_SPACE_BEFORE_PUNCT_PATTERN = re.compile(
    r"\\(?:ref|eqref|pageref)\{[^}]+\}[ \t]+(?=[，。；：,.!?！？])"
)
PLACEHOLDER_PATTERN = re.compile(
    r"(PLACEHOLDER(?:_\d+)?|\bNUL\b|文献待补|数值待补|待核验|\bTODO\b|\bTBD\b)"
)
DOUBLE_DOLLAR_PATTERN = re.compile(r"\$\$")
MACROBUTTON_PATTERN = re.compile(r"MACROBUTTON[ \t]+AcceptAllChangesShown", re.IGNORECASE)
HTBP_PATTERN = re.compile(r"\[\s*htbp\s*\]")
ESCAPED_ENV_PATTERN = re.compile(r"\\\\(?:begin|end)\{(?:figure|table)\}")
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
BCF_CITEKEY_PATTERN = re.compile(
    r'<bcf:citekey order="(?P<order>\d+)" intorder="(?P<intorder>\d+)">(?P<key>[^<]+)</bcf:citekey>'
)
BBL_ENTRY_PATTERN = re.compile(r"\\entry\{([^}]+)\}\{([^}]+)\}\{\}\{\}(.*?)\\endentry", re.S)
BBL_AUTHOR_COUNT_PATTERN = re.compile(r"\\name\{author\}\{(\d+)\}")
BBL_FIELD_PATTERN_TEMPLATE = r"\\field\{%s\}\{([^}]*)\}"
BBL_AUTHOR_BLOCK_PATTERN = re.compile(r"\\name\{author\}\{\d+\}\{\}\{\%(.*?)\n\s*\}", re.S)
BBL_FAMILY_PATTERN = re.compile(r"family=\{([^}]*)\}")
BBL_GIVEN_PATTERN = re.compile(r"given=\{([^}]*)\}")
BBL_GIVENI_PATTERN = re.compile(r"giveni=\{([^}]*)\}")
BIB_ENTRY_KEY_PATTERN = re.compile(r"@\w+\{([^,]+),")
CITATION_PARENTHESES_PATTERN = re.compile(r"\(([^()]*)\)")


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: List[str]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_token() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def tail_lines(text: str, n: int = 40) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return "(no output)"
    return "\n".join(lines[-n:])


def is_project_root(path: Path) -> bool:
    return (path / "main.tex").exists() and (path / "extraTex").exists()


def find_project_root(start: Path) -> Path:
    origin = start.expanduser().resolve()
    for candidate in [origin, *origin.parents]:
        if is_project_root(candidate):
            return candidate
    raise FileNotFoundError(
        "无法定位 thesis 项目根目录。请在项目目录运行，或使用 --project-dir 显式指定。"
    )


def resolve_project_dir(project_dir: Optional[Path]) -> Path:
    if project_dir is None:
        return find_project_root(Path.cwd())
    candidate = project_dir.expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if candidate.exists() and is_project_root(candidate):
        return candidate
    return find_project_root(candidate)


def resolve_path(project_dir: Path, raw: Path) -> Path:
    if raw.is_absolute():
        return raw
    return (project_dir / raw).resolve()


def find_repo_root_for_thesis_tool(project_dir: Path) -> Optional[Path]:
    for candidate in [project_dir, *project_dir.parents]:
        tool = candidate / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py"
        if tool.exists():
            return candidate
    return None


def choose_word_python() -> Tuple[str, str]:
    env_override = os.environ.get("BENSZ_DOCX_PYTHON", "").strip()
    if env_override:
        override = Path(env_override)
        if override.exists():
            return str(override), "env_override"
        which_override = shutil.which(env_override)
        if which_override:
            return which_override, "env_override"

    ordered = (
        [CRLATEX_WIN_WINDOWS_PYTHON, CRLATEX_WIN_WSL_PYTHON]
        if os.name == "nt"
        else [CRLATEX_WIN_WSL_PYTHON, CRLATEX_WIN_WINDOWS_PYTHON]
    )
    for candidate in ordered:
        if candidate.exists():
            return str(candidate), "crlatex_win"

    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found, f"fallback_{name}"
    return sys.executable, "fallback_sys_executable"


def _to_windows_path_for_wsl(path_text: str) -> str:
    match = re.match(r"^/mnt/([a-zA-Z])/(.+)$", path_text)
    if not match:
        return path_text
    drive = match.group(1).upper()
    tail = match.group(2).replace("/", "\\")
    return f"{drive}:\\{tail}"


def normalize_cmd_for_interpreter(cmd: Sequence[str], interpreter: str) -> List[str]:
    normalized = list(cmd)
    if os.name == "nt":
        return normalized

    # WSL 中调用 Windows python.exe 时，需要把 /mnt/<drive>/... 参数映射成 Windows 路径。
    if not re.match(r"^/mnt/[a-zA-Z]/.+/python\.exe$", interpreter):
        return normalized

    mapped: List[str] = [normalized[0]]
    for arg in normalized[1:]:
        if arg.startswith("/mnt/"):
            mapped.append(_to_windows_path_for_wsl(arg))
        else:
            mapped.append(arg)
    return mapped


def should_enable_word_update_fields(policy: str, *, export_python: str = "") -> bool:
    normalized = policy.strip().lower()
    if normalized == "always":
        return True
    if normalized == "never":
        return False
    # auto: Windows 本机启用；或在 WSL/Linux 下命中 Windows python.exe 时启用。
    if os.name == "nt":
        return True
    return bool(export_python and export_python.lower().endswith("python.exe"))


def run_cmd(cmd: Sequence[str], cwd: Optional[Path] = None) -> CommandResult:
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return CommandResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            cmd=list(cmd),
        )
    except Exception as exc:
        return CommandResult(
            returncode=999,
            stdout="",
            stderr=f"命令执行异常: {exc}",
            cmd=list(cmd),
        )


def load_rules(rules_path: Path) -> Dict[str, Any]:
    if not rules_path.exists():
        raise FileNotFoundError(f"规则文件不存在：{rules_path}")

    text = safe_read_text(rules_path)
    data: Any
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        # 兼容兜底：若环境无 PyYAML，则尝试按 JSON 读取。
        data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("规则文件根节点必须是对象（mapping）。")

    required = [
        "docx_quality_checks",
        "log_warning_baseline",
        "static_pattern_checks",
        "known_experience",
        "severity_map",
    ]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"规则文件缺少必要节点：{', '.join(missing)}")
    return data


def make_issue(
    *,
    severity: str,
    category: str,
    key: str,
    message: str,
    detail: str = "",
    file: Optional[str] = None,
    line: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "severity": severity,
        "category": category,
        "key": key,
        "message": message,
    }
    if detail:
        payload["detail"] = detail
    if file:
        payload["file"] = file
    if line is not None:
        payload["line"] = line
    if extra:
        payload.update(extra)
    return payload


def parse_docx_quality_report(report_path: Path) -> Dict[str, Dict[str, str]]:
    if not report_path.exists():
        return {}
    text = safe_read_text(report_path)
    parsed: Dict[str, Dict[str, str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in {"检查项", "---", "结果", ""}:
            continue
        if set(cells[0]) == {"-"}:
            continue
        item = cells[0]
        status = cells[1].upper()
        detail = "|".join(cells[2:]).strip()
        if item:
            parsed[item] = {"status": status, "detail": detail}
    return parsed


def parse_bib_keys(bib_path: Path) -> set[str]:
    if not bib_path.exists():
        return set()
    text = safe_read_text(bib_path)
    return {match.group(1).strip() for match in BIB_ENTRY_KEY_PATTERN.finditer(text)}


def parse_bcf_cite_groups(bcf_path: Path) -> List[List[str]]:
    if not bcf_path.exists():
        return []
    text = safe_read_text(bcf_path)
    bucket: Dict[int, List[Tuple[int, str]]] = {}
    for match in BCF_CITEKEY_PATTERN.finditer(text):
        order = int(match.group("order"))
        intorder = int(match.group("intorder"))
        key = match.group("key").strip()
        bucket.setdefault(order, []).append((intorder, key))
    groups: List[List[str]] = []
    for order in sorted(bucket):
        groups.append([item[1] for item in sorted(bucket[order], key=lambda x: x[0])])
    return groups


def _extract_bbl_field(entry_text: str, field_name: str) -> str:
    pattern = re.compile(BBL_FIELD_PATTERN_TEMPLATE % re.escape(field_name))
    match = pattern.search(entry_text)
    return match.group(1).strip() if match else ""


def _ascii_initials_from_given(given: str) -> str:
    cleaned = re.sub(r"[{}]", "", given)
    cleaned = cleaned.replace(".", " ")
    parts = [part for part in re.split(r"[-\s]+", cleaned) if part]
    initials: List[str] = []
    for part in parts:
        m = re.search(r"[A-Za-z]", part)
        if m:
            initials.append(m.group(0).upper())
    return "-".join(initials)


def parse_bbl_entries(bbl_path: Path) -> List[Dict[str, Any]]:
    if not bbl_path.exists():
        return []
    text = safe_read_text(bbl_path)
    entries: List[Dict[str, Any]] = []
    for idx, match in enumerate(BBL_ENTRY_PATTERN.finditer(text), start=1):
        key = match.group(1).strip()
        entry_type = match.group(2).strip()
        body = match.group(3)
        author_count_match = BBL_AUTHOR_COUNT_PATTERN.search(body)
        author_count = int(author_count_match.group(1)) if author_count_match else 0

        author_block_match = BBL_AUTHOR_BLOCK_PATTERN.search(body)
        author_block = author_block_match.group(1) if author_block_match else ""
        first_family = ""
        first_given = ""
        first_giveni = ""
        family_match = BBL_FAMILY_PATTERN.search(author_block)
        if family_match:
            first_family = family_match.group(1).strip()
        given_match = BBL_GIVEN_PATTERN.search(author_block)
        if given_match:
            first_given = given_match.group(1).strip()
        giveni_match = BBL_GIVENI_PATTERN.search(author_block)
        if giveni_match:
            first_giveni = giveni_match.group(1).strip()

        entry = {
            "order": idx,
            "key": key,
            "type": entry_type,
            "author_count": author_count,
            "first_author_family": first_family,
            "first_author_given": first_given,
            "first_author_giveni": first_giveni.replace(r"\bibinitperiod", "").replace(".", "").strip(),
            "first_author_initials": _ascii_initials_from_given(first_given),
            "year": _extract_bbl_field(body, "year"),
            "langid": _extract_bbl_field(body, "langid"),
            "lansortorder": _extract_bbl_field(body, "lansortorder"),
            "namehash": _extract_bbl_field(body, "namehash"),
            "extradate": _extract_bbl_field(body, "extradate"),
        }
        entries.append(entry)
    return entries


def _is_ascii_name(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[A-Za-z]", text)) and not bool(re.search(r"[\u4e00-\u9fff]", text))


def _normalize_pdf_body_text(pdf_text: str) -> str:
    if not pdf_text:
        return ""
    body = pdf_text
    marker = body.find("参考文献")
    if marker > 0:
        body = body[:marker]
    body = body.replace("\r", " ").replace("\n", " ")
    body = re.sub(r"\s+", " ", body)
    return body.strip()


def load_main_pdf_text(project_dir: Path, out_dir: Path) -> Tuple[str, Dict[str, Any]]:
    pdf_root = project_dir / "main.pdf"
    pdf_cache = project_dir / ".latex-cache" / "main.pdf"
    candidate = pdf_root if pdf_root.exists() else pdf_cache
    fallback_txt = project_dir / ".latex-cache" / "main_after.txt"
    artifact: Dict[str, Any] = {
        "pdf_path": str(candidate),
        "pdf_exists": candidate.exists(),
        "text_path": "",
        "source": "",
    }
    if not candidate.exists():
        if fallback_txt.exists():
            artifact["text_path"] = str(fallback_txt)
            artifact["source"] = "fallback_main_after"
            return safe_read_text(fallback_txt), artifact
        return "", artifact

    pdftotext = shutil.which("pdftotext")
    txt_path = out_dir / "citation_audit_main.txt"
    if pdftotext:
        result = run_cmd([pdftotext, str(candidate), str(txt_path)], cwd=project_dir)
        if result.returncode == 0 and txt_path.exists():
            artifact["text_path"] = str(txt_path)
            artifact["source"] = "pdftotext"
            return safe_read_text(txt_path), artifact

    if fallback_txt.exists():
        artifact["text_path"] = str(fallback_txt)
        artifact["source"] = "fallback_main_after"
        return safe_read_text(fallback_txt), artifact

    return "", artifact


def _severity_from_level(level: str) -> str:
    normalized = (level or "").strip().upper()
    if normalized == "FAIL":
        return "new_issue"
    if normalized == "WARN":
        return "baseline_issue"
    return "info"


def _build_citation_rule_config(rules: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for entry in rules.get("citation_audit_checks", []):
        key = str(entry.get("key", "")).strip()
        if not key:
            continue
        result[key] = {
            "level_on_match": str(entry.get("level_on_match", "FAIL")).upper(),
            "description": str(entry.get("description", "")).strip(),
            "enabled": str(entry.get("enabled", True)).lower(),
        }
    return result


def _citation_issue(
    issues: List[Dict[str, Any]],
    *,
    rule_key: str,
    rule_conf: Dict[str, Dict[str, str]],
    message: str,
    detail: str = "",
    sample_hits: Optional[List[Dict[str, Any]]] = None,
) -> None:
    conf = rule_conf.get(rule_key, {})
    level = conf.get("level_on_match", "FAIL")
    payload_extra: Dict[str, Any] = {"audit_level": level}
    if sample_hits:
        payload_extra["sample_hits"] = sample_hits[:20]
    issues.append(
        make_issue(
            severity=_severity_from_level(level),
            category="citation_audit",
            key=rule_key,
            message=message,
            detail=detail or conf.get("description", ""),
            extra=payload_extra,
        )
    )


def run_citation_audit(
    project_dir: Path,
    rules: Dict[str, Any],
    out_dir: Path,
    issues: List[Dict[str, Any]],
    artifacts: Dict[str, Any],
) -> Dict[str, Any]:
    rule_conf = _build_citation_rule_config(rules)
    required_keys = [
        "CIT_SURNAME_DISAMBIG_INITIALS",
        "CIT_MULTI_CITE_YEAR_ASC",
        "CIT_MULTI_CITE_PUNCT_EN",
        "CIT_SAME_AUTHOR_YEAR_SUFFIX",
        "BIB_COVERAGE_CITED_ONLY",
        "BIB_AUTHOR_ORDER_SINGLE_THEN_COAUTH",
        "BIB_AUTHOR_ORDER_CHRONO",
        "BIB_LANGUAGE_BLOCK_ORDER",
    ]
    check_result: Dict[str, Dict[str, Any]] = {key: {"status": "PASS", "hits": 0} for key in required_keys}

    bcf_path = project_dir / ".latex-cache" / "main.bcf"
    bbl_path = project_dir / ".latex-cache" / "main.bbl"
    bib_path = project_dir / "bibs" / "references.bib"
    cite_groups = parse_bcf_cite_groups(bcf_path)
    cited_keys = {key for group in cite_groups for key in group}
    bbl_entries = parse_bbl_entries(bbl_path)
    bbl_keys = {entry["key"] for entry in bbl_entries}
    bib_keys = parse_bib_keys(bib_path)
    entry_by_key = {entry["key"]: entry for entry in bbl_entries}

    pdf_text_raw, pdf_artifact = load_main_pdf_text(project_dir, out_dir)
    pdf_text = _normalize_pdf_body_text(pdf_text_raw)
    artifacts["citation_audit_inputs"] = {
        "bcf_path": str(bcf_path),
        "bcf_exists": bcf_path.exists(),
        "bbl_path": str(bbl_path),
        "bbl_exists": bbl_path.exists(),
        "bib_path": str(bib_path),
        "bib_exists": bib_path.exists(),
        **pdf_artifact,
    }

    # 0) 输入完整性
    for label, path in (("bcf", bcf_path), ("bbl", bbl_path), ("bib", bib_path)):
        if not path.exists():
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="citation_audit",
                    key="citation_audit_input_missing",
                    message=f"缺少 citation_audit 输入文件：{label}",
                    detail=str(path),
                    extra={"audit_level": "FAIL"},
                )
            )

    if not pdf_text:
        for key in ("CIT_SURNAME_DISAMBIG_INITIALS", "CIT_MULTI_CITE_PUNCT_EN"):
            check_result[key]["status"] = "WARN"
            issues.append(
                make_issue(
                    severity="baseline_issue",
                    category="citation_audit",
                    key=key,
                    message="未获取到可解析的 PDF 文本，相关规则已跳过。",
                    detail="请安装 pdftotext 或提供 .latex-cache/main_after.txt 以启用正文标注文本检查。",
                    extra={"audit_level": "WARN"},
                )
            )

    # 1) 覆盖完整性（先执行）
    missing_in_bib = sorted(cited_keys - bib_keys)
    missing_in_bbl = sorted(cited_keys - bbl_keys)
    uncited_in_bbl = sorted(bbl_keys - cited_keys)
    if missing_in_bib or missing_in_bbl or uncited_in_bbl:
        check_result["BIB_COVERAGE_CITED_ONLY"]["status"] = "FAIL"
        hit_count = int(bool(missing_in_bib)) + int(bool(missing_in_bbl)) + int(bool(uncited_in_bbl))
        check_result["BIB_COVERAGE_CITED_ONLY"]["hits"] = hit_count
        _citation_issue(
            issues,
            rule_key="BIB_COVERAGE_CITED_ONLY",
            rule_conf=rule_conf,
            message="参考文献覆盖一致性失败（存在缺失或多余条目）。",
            detail="missing_in_bib={}; missing_in_bbl={}; uncited_in_bbl={}".format(
                ",".join(missing_in_bib[:20]) or "-",
                ",".join(missing_in_bbl[:20]) or "-",
                ",".join(uncited_in_bbl[:20]) or "-",
            ),
        )

    # 2) 同姓缩写（外文第一作者）
    ambiguous_surnames: Dict[str, set[str]] = {}
    cited_western_entries = [
        entry
        for entry in bbl_entries
        if entry.get("key") in cited_keys and _is_ascii_name(str(entry.get("first_author_family", "")))
    ]
    for entry in cited_western_entries:
        surname = str(entry.get("first_author_family", "")).strip()
        initials = str(entry.get("first_author_initials", "")).strip()
        if not surname or not initials:
            continue
        ambiguous_surnames.setdefault(surname, set()).add(initials)
    ambiguous_surnames = {k: v for k, v in ambiguous_surnames.items() if len(v) >= 2}

    surname_violations: List[Dict[str, Any]] = []
    if ambiguous_surnames and pdf_text:
        for chunk in CITATION_PARENTHESES_PATTERN.findall(pdf_text):
            if not re.search(r"\d{4}[a-z]?", chunk):
                continue
            for surname, initials_set in ambiguous_surnames.items():
                if surname not in chunk:
                    continue
                for seg in [part.strip() for part in chunk.split(";") if part.strip()]:
                    if surname not in seg:
                        continue
                    m = re.search(
                        rf"\b{re.escape(surname)}(?:\s+([A-Z](?:-[A-Z])?))?(?:\s+et al\.)?\s*,\s*\d{{4}}[a-z]?\b",
                        seg,
                    )
                    if not m:
                        continue
                    shown_initials = (m.group(1) or "").strip()
                    if not shown_initials:
                        surname_violations.append(
                            {"snippet": seg, "reason": f"{surname} 同姓作者未显示名缩写（期望之一：{sorted(initials_set)}）"}
                        )
                        continue
                    if shown_initials not in initials_set:
                        surname_violations.append(
                            {"snippet": seg, "reason": f"{surname} 缩写 `{shown_initials}` 不在期望集合 {sorted(initials_set)}"}
                        )

                    if re.search(rf"\b{re.escape(surname)}\s+[A-Z]\.", seg):
                        surname_violations.append(
                            {"snippet": seg, "reason": f"{surname} 缩写不应带点号。"}
                        )
    if surname_violations:
        check_result["CIT_SURNAME_DISAMBIG_INITIALS"]["status"] = "FAIL"
        check_result["CIT_SURNAME_DISAMBIG_INITIALS"]["hits"] = len(surname_violations)
        _citation_issue(
            issues,
            rule_key="CIT_SURNAME_DISAMBIG_INITIALS",
            rule_conf=rule_conf,
            message="检测到同姓外文作者引用未按要求显示名缩写。",
            detail="同姓集合: " + ", ".join(f"{k}:{'/'.join(sorted(v))}" for k, v in ambiguous_surnames.items()),
            sample_hits=[{"snippet": item["snippet"], "reason": item["reason"]} for item in surname_violations[:20]],
        )

    # 3) 同作者同年 a/b/c
    same_author_year_violations: List[Dict[str, Any]] = []
    author_year_bucket: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for entry in cited_western_entries:
        surname = str(entry.get("first_author_family", "")).strip()
        year = str(entry.get("year", "")).strip()
        if not surname or not year:
            continue
        author_year_bucket.setdefault((surname, year), []).append(entry)

    for (surname, year), entries_in_group in author_year_bucket.items():
        if len(entries_in_group) <= 1:
            continue
        missing = [item["key"] for item in entries_in_group if not str(item.get("extradate", "")).strip()]
        if missing:
            same_author_year_violations.append(
                {
                    "group": f"{surname}-{year}",
                    "missing_keys": missing,
                }
            )

    if same_author_year_violations:
        check_result["CIT_SAME_AUTHOR_YEAR_SUFFIX"]["status"] = "FAIL"
        check_result["CIT_SAME_AUTHOR_YEAR_SUFFIX"]["hits"] = len(same_author_year_violations)
        _citation_issue(
            issues,
            rule_key="CIT_SAME_AUTHOR_YEAR_SUFFIX",
            rule_conf=rule_conf,
            message="检测到同一作者同年文献未完整生成 a/b/c 区分。",
            sample_hits=[{"snippet": item["group"], "missing_keys": ",".join(item["missing_keys"])} for item in same_author_year_violations[:20]],
        )

    # 4) 同处多引文排序 + 标点
    year_order_violations: List[Dict[str, Any]] = []
    for group in cite_groups:
        if len(group) <= 1:
            continue
        years: List[int] = []
        keys_used: List[str] = []
        for key in group:
            year_raw = str(entry_by_key.get(key, {}).get("year", ""))
            m = re.search(r"\d{4}", year_raw)
            if not m:
                continue
            years.append(int(m.group(0)))
            keys_used.append(key)
        if len(years) <= 1:
            continue
        if any(years[idx] > years[idx + 1] for idx in range(len(years) - 1)):
            year_order_violations.append(
                {"keys": ";".join(keys_used), "years": ";".join(str(y) for y in years)}
            )
    if year_order_violations:
        check_result["CIT_MULTI_CITE_YEAR_ASC"]["status"] = "FAIL"
        check_result["CIT_MULTI_CITE_YEAR_ASC"]["hits"] = len(year_order_violations)
        _citation_issue(
            issues,
            rule_key="CIT_MULTI_CITE_YEAR_ASC",
            rule_conf=rule_conf,
            message="检测到同一处多篇文献引用未按年份由远及近排序。",
            sample_hits=[{"snippet": item["keys"], "years": item["years"]} for item in year_order_violations[:20]],
        )

    punct_violations: List[Dict[str, Any]] = []
    if pdf_text:
        for chunk in CITATION_PARENTHESES_PATTERN.findall(pdf_text):
            if ";" not in chunk or not re.search(r"\d{4}[a-z]?", chunk):
                continue
            hit_reasons: List[str] = []
            if "，" in chunk or "；" in chunk:
                hit_reasons.append("存在中文全角逗号/分号")
            if re.search(r"[;,](?! )", chunk):
                hit_reasons.append("逗号/分号后缺少空格")
            if re.search(r"[;,] {2,}", chunk):
                hit_reasons.append("逗号/分号后空格超过1个")
            if hit_reasons:
                punct_violations.append({"snippet": chunk.strip(), "reason": "; ".join(hit_reasons)})
    if punct_violations:
        check_result["CIT_MULTI_CITE_PUNCT_EN"]["status"] = "FAIL"
        check_result["CIT_MULTI_CITE_PUNCT_EN"]["hits"] = len(punct_violations)
        _citation_issue(
            issues,
            rule_key="CIT_MULTI_CITE_PUNCT_EN",
            rule_conf=rule_conf,
            message="检测到同处多引文标点不符合英文半角+单空格规则。",
            sample_hits=[{"snippet": item["snippet"], "reason": item["reason"]} for item in punct_violations[:20]],
        )

    # 5) 文后排序（单著在前、语种块顺序）
    # gb7714-2015ay 的 biber 排序模板先按作者名排序，再按年份排序；
    # 因此文后同姓/同第一作者条目不应被单独强制判定为年份升序。
    check_result["BIB_AUTHOR_ORDER_CHRONO"]["note"] = "Skipped for gb7714-2015ay: sortname precedes year in the bibliography sorting template."
    single_then_coauthor_violations: List[Dict[str, Any]] = []
    lang_order_violations: List[Dict[str, Any]] = []

    # 5.1 语种块顺序
    lang_orders: List[int] = []
    for entry in bbl_entries:
        raw_order = str(entry.get("lansortorder", "")).strip()
        if raw_order.isdigit():
            lang_orders.append(int(raw_order))
    if lang_orders and any(lang_orders[idx] > lang_orders[idx + 1] for idx in range(len(lang_orders) - 1)):
        lang_order_violations.append({"sequence": ",".join(str(x) for x in lang_orders[:60])})

    # 5.2 / 5.3 first-author 分组检查
    group_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for entry in bbl_entries:
        surname = str(entry.get("first_author_family", "")).strip()
        if not surname:
            continue
        group_key = (str(entry.get("lansortorder", "")), surname)
        group_map.setdefault(group_key, []).append(entry)

    for (_, surname), grouped in group_map.items():
        if len(grouped) <= 1:
            continue
        orders = [item["order"] for item in grouped]
        grouped_sorted = [item for _, item in sorted(zip(orders, grouped), key=lambda x: x[0])]
        seen_coauthor = False

        for entry in grouped_sorted:
            author_count = int(entry.get("author_count", 0) or 0)
            if author_count <= 1:
                if seen_coauthor:
                    single_then_coauthor_violations.append(
                        {"author": surname, "key": entry.get("key", ""), "order": entry.get("order", 0)}
                    )
            else:
                seen_coauthor = True

    if single_then_coauthor_violations:
        check_result["BIB_AUTHOR_ORDER_SINGLE_THEN_COAUTH"]["status"] = "FAIL"
        check_result["BIB_AUTHOR_ORDER_SINGLE_THEN_COAUTH"]["hits"] = len(single_then_coauthor_violations)
        _citation_issue(
            issues,
            rule_key="BIB_AUTHOR_ORDER_SINGLE_THEN_COAUTH",
            rule_conf=rule_conf,
            message="检测到同一第一作者分组中，共同署名条目先于单独署名条目。",
            sample_hits=[{"snippet": f"{item['author']}:{item['key']}", "order": item["order"]} for item in single_then_coauthor_violations[:20]],
        )


    if lang_order_violations:
        check_result["BIB_LANGUAGE_BLOCK_ORDER"]["status"] = "FAIL"
        check_result["BIB_LANGUAGE_BLOCK_ORDER"]["hits"] = len(lang_order_violations)
        _citation_issue(
            issues,
            rule_key="BIB_LANGUAGE_BLOCK_ORDER",
            rule_conf=rule_conf,
            message="检测到文后参考文献语种分组顺序异常（应为中文→日文→西文→俄文→其他）。",
            sample_hits=[{"snippet": item["sequence"]} for item in lang_order_violations[:20]],
        )

    # 为 8 项检查补齐 PASS 结果
    for key in required_keys:
        if check_result[key]["status"] == "PASS":
            issues.append(
                make_issue(
                    severity="info",
                    category="citation_audit",
                    key=key,
                    message="参考文献专项检查通过。",
                    detail=rule_conf.get(key, {}).get("description", ""),
                    extra={"audit_level": "INFO"},
                )
            )

    counter = Counter(issue.get("severity", "info") for issue in issues if issue.get("category") == "citation_audit")
    return {
        "checks": check_result,
        "summary": {
            "new_issue": int(counter.get("new_issue", 0)),
            "baseline_issue": int(counter.get("baseline_issue", 0)),
            "info": int(counter.get("info", 0)),
        },
    }


def normalize_warning_signature(line: str) -> str:
    normalized = line.strip()
    normalized = re.sub(r"\d+(?:\.\d+)?", "<num>", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def extract_warning_lines(log_text: str) -> List[str]:
    lines: List[str] = []
    for raw in log_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if "Warning:" in line:
            lines.append(line)
            continue
        if line.startswith("Overfull \\hbox") or line.startswith("Underfull \\hbox"):
            lines.append(line)
            continue
        if line.startswith("Missing character:"):
            lines.append(line)
    return lines


def _line_snippet(line: str, max_len: int = 160) -> str:
    line = line.rstrip()
    if len(line) <= max_len:
        return line
    return f"{line[: max_len - 3]}..."


def collect_files_for_target(project_dir: Path, rule: Dict[str, Any]) -> List[Path]:
    target = str(rule.get("target", "")).strip()
    include_ext = [ext.lower() for ext in rule.get("include_ext", []) if isinstance(ext, str)]
    files: List[Path] = []

    if target == "source_tex_bib":
        for subdir in ("extraTex", "bibs"):
            root = project_dir / subdir
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if include_ext and path.suffix.lower() not in include_ext:
                    continue
                files.append(path)
    elif target == "markdown_word_source":
        patterns = rule.get(
            "globs",
            [
                "main_from_tex_word_source*.md",
                ".latex-cache/smoke/main_from_tex_word_source*.md",
            ],
        )
        for raw_glob in patterns:
            for path in project_dir.glob(str(raw_glob)):
                if path.is_file():
                    files.append(path)
    else:
        patterns = rule.get("globs", [])
        for raw_glob in patterns:
            for path in project_dir.glob(str(raw_glob)):
                if path.is_file():
                    files.append(path)

    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in sorted(files):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def scan_patterns(
    files: Sequence[Path],
    patterns: Sequence[str],
    *,
    max_hits: int = 200,
) -> Tuple[int, List[Dict[str, Any]], List[str]]:
    if not files:
        return 0, [], []

    compiled: List[re.Pattern[str]] = []
    invalid_patterns: List[str] = []
    for raw in patterns:
        try:
            compiled.append(re.compile(raw))
        except re.error:
            invalid_patterns.append(raw)

    total_hits = 0
    sampled_hits: List[Dict[str, Any]] = []
    for file_path in files:
        text = safe_read_text(file_path)
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            for reg in compiled:
                if reg.search(line):
                    total_hits += 1
                    if len(sampled_hits) < max_hits:
                        sampled_hits.append(
                            {
                                "file": str(file_path),
                                "line": line_no,
                                "pattern": reg.pattern,
                                "snippet": _line_snippet(line),
                            }
                        )
    return total_hits, sampled_hits, invalid_patterns


def _short_snippet(line: str, span: tuple[int, int], pad: int = 32) -> str:
    start, end = span
    left = max(0, start - pad)
    right = min(len(line), end + pad)
    return line[left:right].strip()


def _iter_non_math_segments(line: str) -> Iterable[tuple[int, str]]:
    cursor = 0
    for match in INLINE_MATH_SEGMENT_PATTERN.finditer(line):
        if match.start() > cursor:
            yield cursor, line[cursor:match.start()]
        cursor = match.end()
    if cursor < len(line):
        yield cursor, line[cursor:]


def _append_repair_issue(
    issues: List[Dict[str, Any]],
    *,
    code: str,
    file_rel: str,
    line: int,
    message: str,
    snippet: str,
    fixable: bool,
    recommended_fix: str,
    source_key: str,
    source_severity: str,
) -> None:
    issue_id = f"ISSUE-{len(issues) + 1:05d}"
    issues.append(
        {
            "issue_id": issue_id,
            "code": code,
            "file": file_rel,
            "line": line,
            "message": message,
            "snippet": snippet,
            "fixable": fixable,
            "recommended_fix": recommended_fix,
            "source_key": source_key,
            "source_severity": source_severity,
        }
    )


def _scan_repair_line(file_rel: str, line_no: int, line: str, issues: List[Dict[str, Any]]) -> None:
    for match in F_STAT_PATTERN.finditer(line):
        canonical = f"F({match.group(1)},{match.group(2)})"
        if match.group(0) == canonical:
            continue
        _append_repair_issue(
            issues,
            code="STAT_F_FORMAT",
            file_rel=file_rel,
            line=line_no,
            message="统计量 F 的自由度建议统一写为 F(a,b)（不保留额外空格或中文逗号）。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=f"改为 `{canonical}`。",
            source_key="stat_f_format",
            source_severity="new_issue",
        )

    for match in CJK_ABBR_LEFT_PATTERN.finditer(line):
        token = match.group(2)
        _append_repair_issue(
            issues,
            code="MIXED_ABBR_SPACING",
            file_rel=file_rel,
            line=line_no,
            message="中文与英文缩写（Cd/Se）之间检测到多余空格。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=f"将“{match.group(1)} {token}”改为“{match.group(1)}{token}”。",
            source_key="cjk_latin_spacing",
            source_severity="baseline_issue",
        )

    for match in CJK_ABBR_RIGHT_PATTERN.finditer(line):
        token = match.group(1)
        _append_repair_issue(
            issues,
            code="MIXED_ABBR_SPACING",
            file_rel=file_rel,
            line=line_no,
            message="英文缩写（Cd/Se）与中文之间检测到多余空格。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=f"将“{token} {match.group(2)}”改为“{token}{match.group(2)}”。",
            source_key="cjk_latin_spacing",
            source_severity="baseline_issue",
        )

    for match in TIME_UNIT_SPACING_PATTERN.finditer(line):
        fixed = f"{match.group(1)}~{match.group(2)}"
        _append_repair_issue(
            issues,
            code="TIME_UNIT_SPACING",
            file_rel=file_rel,
            line=line_no,
            message="检测到数字与单位之间使用普通空格，建议使用不换行空格连接单位。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=f"将“{match.group(0)}”改为“{fixed}”。",
            source_key="time_unit_spacing",
            source_severity="baseline_issue",
        )

    for match in SIMPLE_STAT_INLINE_MATH_PATTERN.finditer(line):
        fixed = f"{match.group(1)} {match.group(2)} {match.group(3)}"
        _append_repair_issue(
            issues,
            code="SIMPLE_STAT_INLINE_MATH",
            file_rel=file_rel,
            line=line_no,
            message="检测到简单统计表达被写成 `$...$` 数学模式，建议改为正文普通文本。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=f"将“{match.group(0)}”改为“{fixed}”。",
            source_key="simple_stat_inline_math",
            source_severity="baseline_issue",
        )

    for segment_offset, segment in _iter_non_math_segments(line):
        for match in STAT_EXPR_SPACING_PATTERN.finditer(segment):
            fixed = f"{match.group(1)} {match.group(2)} {match.group(3)}"
            span = (segment_offset + match.start(), segment_offset + match.end())
            _append_repair_issue(
                issues,
                code="STAT_EXPR_SPACING",
                file_rel=file_rel,
                line=line_no,
                message="检测到统计表达缺少空格，建议统一为 `变量 操作符 数值`。",
                snippet=_short_snippet(line, span),
                fixable=True,
                recommended_fix=f"将“{match.group(0)}”改为“{fixed}”。",
                source_key="stat_expr_spacing",
                source_severity="baseline_issue",
            )

    for match in REF_TILDE_BEFORE_PUNCT_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="REF_TILDE_BEFORE_PUNCT",
            file_rel=file_rel,
            line=line_no,
            message=r"检测到 `~\ref{}` 紧邻标点，可能在 DOCX 中形成异常空格。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=r"移除 `~`，保持 `\ref{}` 后直接跟标点。",
            source_key="ref_punctuation_spacing",
            source_severity="new_issue",
        )

    for match in REF_SPACE_BEFORE_PUNCT_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="REF_SPACE_BEFORE_PUNCT",
            file_rel=file_rel,
            line=line_no,
            message=r"检测到 `\ref{}` 与后续标点之间存在空格。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix=r"移除 `\ref{}` 与标点之间的空格。",
            source_key="ref_punctuation_spacing",
            source_severity="new_issue",
        )

    for match in PLACEHOLDER_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="PLACEHOLDER_TOKEN",
            file_rel=file_rel,
            line=line_no,
            message="检测到占位词，正式版本应清零。",
            snippet=_short_snippet(line, match.span()),
            fixable=False,
            recommended_fix="请人工替换为最终表述或删除。",
            source_key="placeholder_tokens",
            source_severity="new_issue",
        )

    for match in DOUBLE_DOLLAR_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="DOUBLE_DOLLAR_MATH",
            file_rel=file_rel,
            line=line_no,
            message="检测到 `$$` 数学块写法，建议改为 `\\[ ... \\]`。",
            snippet=_short_snippet(line, match.span()),
            fixable=False,
            recommended_fix="请人工改写为 `\\[ ... \\]` 并检查多行公式排版。",
            source_key="double_dollar_math",
            source_severity="new_issue",
        )

    for match in MACROBUTTON_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="LATEX_ARTIFACT_MACROBUTTON",
            file_rel=file_rel,
            line=line_no,
            message="检测到可疑 Word 伪影文本 `MACROBUTTON AcceptAllChangesShown`。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix="移除该伪影文本。",
            source_key="latex_artifacts",
            source_severity="new_issue",
        )

    for match in HTBP_PATTERN.finditer(line):
        prefix = line[: match.start()].rstrip()
        if prefix.endswith(r"\begin{figure}") or prefix.endswith(r"\begin{table}"):
            continue
        _append_repair_issue(
            issues,
            code="LATEX_ARTIFACT_HTBP",
            file_rel=file_rel,
            line=line_no,
            message="检测到孤立 `[htbp]` 文本，疑似 LaTeX 伪影。",
            snippet=_short_snippet(line, match.span()),
            fixable=True,
            recommended_fix="若为残留文本，请删除 `[htbp]`。",
            source_key="latex_artifacts",
            source_severity="new_issue",
        )

    for match in ESCAPED_ENV_PATTERN.finditer(line):
        _append_repair_issue(
            issues,
            code="LATEX_ARTIFACT_ESCAPED_ENV",
            file_rel=file_rel,
            line=line_no,
            message=r"检测到 `\\begin{...}` / `\\end{...}` 形式文本，疑似伪影。",
            snippet=_short_snippet(line, match.span()),
            fixable=False,
            recommended_fix="请人工确认是否应为真实环境命令或普通文本。",
            source_key="latex_artifacts",
            source_severity="new_issue",
        )


def _to_project_rel_path(project_dir: Path, file_text: str) -> Optional[str]:
    candidate = Path(file_text)
    if not candidate.is_absolute():
        candidate = (project_dir / candidate).resolve()
    else:
        candidate = candidate.resolve()
    try:
        return candidate.relative_to(project_dir).as_posix()
    except ValueError:
        return None


def _append_static_hit_as_repair_issue(
    project_dir: Path,
    repair_issues: List[Dict[str, Any]],
    *,
    key: str,
    severity: str,
    hit: Dict[str, Any],
    seen: set[tuple[str, str, int, str]],
) -> None:
    file_text = str(hit.get("file", "")).strip()
    line_no = int(hit.get("line", 0) or 0)
    snippet = str(hit.get("snippet", "")).strip()
    if not file_text or line_no <= 0 or not snippet:
        return

    file_rel = _to_project_rel_path(project_dir, file_text)
    if file_rel is None:
        return

    # 仅桥接“低风险可自动修复”的静态命中，避免将高风险规则误导入自动修复链路。
    mapped: Optional[Dict[str, Any]] = None
    if key == "ref_space_before_punct":
        if REF_TILDE_BEFORE_PUNCT_PATTERN.search(snippet):
            mapped = {
                "code": "REF_TILDE_BEFORE_PUNCT",
                "message": r"静态巡检命中 `~\ref{}` 紧邻标点。",
                "fixable": True,
                "recommended_fix": r"移除 `~`，保持 `\ref{}` 后直接跟标点。",
            }
        elif REF_SPACE_BEFORE_PUNCT_PATTERN.search(snippet):
            mapped = {
                "code": "REF_SPACE_BEFORE_PUNCT",
                "message": r"静态巡检命中 `\ref{}` 与后续标点之间空格。",
                "fixable": True,
                "recommended_fix": r"移除 `\ref{}` 与标点之间空格。",
            }
    elif key == "cjk_latin_spacing":
        if CJK_ABBR_LEFT_PATTERN.search(snippet) or CJK_ABBR_RIGHT_PATTERN.search(snippet):
            mapped = {
                "code": "MIXED_ABBR_SPACING",
                "message": "静态巡检命中中文与 Cd/Se 缩写间多余空格。",
                "fixable": True,
                "recommended_fix": "移除中文与 Cd/Se 之间的冗余空格。",
            }
    elif key == "time_unit_spacing":
        match = TIME_UNIT_SPACING_PATTERN.search(snippet)
        if match:
            mapped = {
                "code": "TIME_UNIT_SPACING",
                "message": "静态巡检命中数字与单位之间的普通空格写法。",
                "fixable": True,
                "recommended_fix": f"将“{match.group(0)}”改为“{match.group(1)}~{match.group(2)}”。",
            }
    elif key == "stat_expr_spacing":
        match = None
        for _, segment in _iter_non_math_segments(snippet):
            match = STAT_EXPR_SPACING_PATTERN.search(segment)
            if match:
                break
        if match:
            mapped = {
                "code": "STAT_EXPR_SPACING",
                "message": "静态巡检命中统计表达空格异常。",
                "fixable": True,
                "recommended_fix": f"将“{match.group(0)}”改为“{match.group(1)} {match.group(2)} {match.group(3)}”。",
            }
    elif key == "simple_stat_inline_math":
        match = SIMPLE_STAT_INLINE_MATH_PATTERN.search(snippet)
        if match:
            mapped = {
                "code": "SIMPLE_STAT_INLINE_MATH",
                "message": "静态巡检命中简单统计表达的数学模式写法。",
                "fixable": True,
                "recommended_fix": f"将“{match.group(0)}”改为“{match.group(1)} {match.group(2)} {match.group(3)}”。",
            }

    if mapped is None:
        return

    dedup_key = (mapped["code"], file_rel, line_no, snippet)
    if dedup_key in seen:
        return
    seen.add(dedup_key)
    _append_repair_issue(
        repair_issues,
        code=mapped["code"],
        file_rel=file_rel,
        line=line_no,
        message=mapped["message"],
        snippet=snippet,
        fixable=bool(mapped["fixable"]),
        recommended_fix=mapped["recommended_fix"],
        source_key=key,
        source_severity=severity,
    )


def _bridge_static_hits_to_repair_feed(
    project_dir: Path,
    quality_issues: Sequence[Dict[str, Any]],
    repair_issues: List[Dict[str, Any]],
) -> None:
    seen = {
        (
            str(item.get("code", "")),
            str(item.get("file", "")),
            int(item.get("line", 0) or 0),
            str(item.get("snippet", "")),
        )
        for item in repair_issues
    }
    for quality_issue in quality_issues:
        if quality_issue.get("category") != "static_pattern":
            continue
        key = str(quality_issue.get("key", "")).strip()
        if key not in {"ref_space_before_punct", "cjk_latin_spacing", "time_unit_spacing", "stat_expr_spacing", "simple_stat_inline_math"}:
            continue
        severity = str(quality_issue.get("severity", "info"))
        for hit in quality_issue.get("sample_hits", [])[:50]:
            if not isinstance(hit, dict):
                continue
            _append_static_hit_as_repair_issue(
                project_dir,
                repair_issues,
                key=key,
                severity=severity,
                hit=hit,
                seen=seen,
            )


def collect_repair_feed(
    project_dir: Path,
    quality_issues: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    tex_files = sorted(path for path in project_dir.glob("extraTex/*.tex") if path.is_file())
    issues: List[Dict[str, Any]] = []
    for tex_file in tex_files:
        file_rel = tex_file.relative_to(project_dir).as_posix()
        for line_no, line in enumerate(safe_read_text(tex_file).splitlines(), start=1):
            _scan_repair_line(file_rel, line_no, line, issues)
    if quality_issues:
        _bridge_static_hits_to_repair_feed(project_dir, quality_issues, issues)

    counts_by_code: Dict[str, int] = {}
    for issue in issues:
        code = issue.get("code", "UNKNOWN")
        counts_by_code[code] = counts_by_code.get(code, 0) + 1
    counts_by_code = dict(sorted(counts_by_code.items(), key=lambda item: (-item[1], item[0])))

    return {
        "generated_at": now_str(),
        "project_dir": str(project_dir),
        "scan_glob": "extraTex/*.tex",
        "files_scanned": [path.relative_to(project_dir).as_posix() for path in tex_files],
        "total_files": len(tex_files),
        "total_issues": len(issues),
        "fixable_issues": sum(1 for item in issues if item.get("fixable", False)),
        "issues_by_code": counts_by_code,
        "issues": issues,
    }


def run_full_pipeline(
    project_dir: Path,
    issues: List[Dict[str, Any]],
    artifacts: Dict[str, Any],
    *,
    full_word_update_fields: str = "auto",
) -> None:
    artifacts["full_word_update_fields_policy"] = full_word_update_fields
    artifacts["full_word_update_fields_applied"] = False

    repo_root = find_repo_root_for_thesis_tool(project_dir)
    python3_exe, _python_reason = choose_word_python()

    if repo_root is None:
        issues.append(
            make_issue(
                severity="new_issue",
                category="full_mode",
                key="build_tool_missing",
                message="未找到 thesis_project_tool.py，无法执行 full 模式 PDF 构建。",
            )
        )
    else:
        build_tool = repo_root / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py"
        build_cmd = [python3_exe, str(build_tool), "build", "--project-dir", str(project_dir)]
        build_result = run_cmd(build_cmd, cwd=repo_root)
        artifacts["full_build"] = {
            "cmd": build_result.cmd,
            "returncode": build_result.returncode,
            "stdout_tail": tail_lines(build_result.stdout, 30),
            "stderr_tail": tail_lines(build_result.stderr, 30),
        }
        if build_result.returncode != 0:
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="full_mode",
                    key="full_build_failed",
                    message="full 模式 PDF 构建失败。",
                    detail=tail_lines(f"{build_result.stdout}\n{build_result.stderr}", 40),
                )
            )

    export_script = project_dir / "scripts" / "export_docx.py"
    smoke_dir = project_dir / ".latex-cache" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    smoke_docx = smoke_dir / "main_from_tex_资环模板_smoke.docx"
    smoke_md = smoke_dir / "main_from_tex_word_source_smoke.md"
    smoke_report = smoke_dir / "main_from_tex_资环模板_smoke_质量报告.md"

    artifacts["smoke_output"] = {
        "docx": str(smoke_docx),
        "markdown": str(smoke_md),
        "quality_report": str(smoke_report),
    }

    if not export_script.exists():
        issues.append(
            make_issue(
                severity="new_issue",
                category="full_mode",
                key="export_docx_missing",
                message="未找到 export_docx.py，无法执行 full 模式 DOCX smoke 导出。",
            )
        )
        return

    export_python, reason = choose_word_python()
    word_update_enabled = should_enable_word_update_fields(
        full_word_update_fields,
        export_python=export_python,
    )
    artifacts["full_word_update_fields_applied"] = word_update_enabled

    export_cmd = [
        export_python,
        str(export_script),
        "--project-dir",
        str(project_dir),
        "--mode",
        "strict",
        "--output",
        str(smoke_docx),
        "--markdown-output",
        str(smoke_md),
        "--quality-report",
        str(smoke_report),
    ]
    if word_update_enabled:
        export_cmd.append("--word-update-fields")
    normalized_export_cmd = normalize_cmd_for_interpreter(export_cmd, export_python)
    export_result = run_cmd(normalized_export_cmd, cwd=project_dir)
    artifacts["full_docx_smoke"] = {
        "python": export_python,
        "python_reason": reason,
        "cmd": export_result.cmd,
        "returncode": export_result.returncode,
        "stdout_tail": tail_lines(export_result.stdout, 30),
        "stderr_tail": tail_lines(export_result.stderr, 30),
    }

    if export_result.returncode != 0:
        issues.append(
            make_issue(
                severity="new_issue",
                category="full_mode",
                key="full_docx_smoke_failed",
                message="full 模式 strict DOCX smoke 导出失败。",
                detail=tail_lines(f"{export_result.stdout}\n{export_result.stderr}", 40),
            )
        )


def build_experience_hits(
    rules: Dict[str, Any],
    issues: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    triggered_keys = {issue.get("key", "") for issue in issues if issue.get("severity") != "info"}
    hits: List[Dict[str, Any]] = []
    for exp in rules.get("known_experience", []):
        mapped = set(exp.get("mapped_checks", []))
        related = sorted(key for key in mapped if key in triggered_keys)
        if not related:
            continue
        hits.append(
            {
                "key": exp.get("key", ""),
                "title": exp.get("title", ""),
                "source": exp.get("source", ""),
                "message": exp.get("message", ""),
                "related_checks": related,
            }
        )
    return hits


def generate_snapshot(
    *,
    observed_docx_checks: Dict[str, Dict[str, str]],
    rules: Dict[str, Any],
    warning_counts: Dict[str, int],
) -> Dict[str, Any]:
    docx_snapshot = []
    for item, payload in sorted(observed_docx_checks.items()):
        docx_snapshot.append(
            {
                "item": item,
                "status": payload.get("status", ""),
                "detail": payload.get("detail", ""),
            }
        )

    baseline_snapshot = []
    for entry in rules.get("log_warning_baseline", []):
        key = str(entry.get("key", ""))
        baseline_snapshot.append(
            {
                "key": key,
                "regex": entry.get("regex", ""),
                "current_count": int(warning_counts.get(key, 0)),
                "suggested_max_count": int(warning_counts.get(key, 0)),
            }
        )

    return {
        "generated_at": now_str(),
        "docx_quality_checks": docx_snapshot,
        "log_warning_baseline": baseline_snapshot,
    }


def write_snapshot_files(out_dir: Path, snapshot: Dict[str, Any]) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = now_token()
    json_path = out_dir / f"baseline_snapshot_{ts}.suggested.json"
    md_path = out_dir / f"baseline_snapshot_{ts}.suggested.md"
    json_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 基线建议快照（自动导出）",
        "",
        f"- 生成时间：{snapshot.get('generated_at', '')}",
        "",
        "## DOCX 质量检查当前状态",
        "",
        "| 检查项 | 状态 | 说明 |",
        "|---|---|---|",
    ]
    for item in snapshot.get("docx_quality_checks", []):
        lines.append(
            f"| {item.get('item', '')} | {item.get('status', '')} | {item.get('detail', '')} |"
        )

    lines.extend(
        [
            "",
            "## LaTeX Warning 建议基线",
            "",
            "| key | current_count | suggested_max_count | regex |",
            "|---|---:|---:|---|",
        ]
    )
    for row in snapshot.get("log_warning_baseline", []):
        lines.append(
            "| {key} | {c} | {m} | `{regex}` |".format(
                key=row.get("key", ""),
                c=row.get("current_count", 0),
                m=row.get("suggested_max_count", 0),
                regex=row.get("regex", ""),
            )
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UCAS 项目格式巡检脚本（Fast + Full）")
    parser.add_argument("--mode", choices=["fast", "full"], default="fast", help="巡检模式。")
    parser.add_argument("--project-dir", type=Path, default=None, help="项目目录。")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_REL, help="规则文件路径。")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR_REL, help="报告输出目录。")
    parser.add_argument(
        "--full-word-update-fields",
        choices=["auto", "always", "never"],
        default="auto",
        help="仅 full 模式生效：控制 strict smoke 导出是否追加 --word-update-fields。",
    )
    parser.add_argument(
        "--repair-feed-path",
        type=Path,
        default=DEFAULT_REPAIR_FEED_REL,
        help="模式修复输入文件路径（默认：.latex-cache/format-fix/latest_check.json）。",
    )

    parser.add_argument("--emit-json", dest="emit_json", action="store_true", default=True)
    parser.add_argument("--no-emit-json", dest="emit_json", action="store_false")
    parser.add_argument("--emit-markdown", dest="emit_markdown", action="store_true", default=True)
    parser.add_argument("--no-emit-markdown", dest="emit_markdown", action="store_false")
    parser.add_argument("--emit-repair-feed", dest="emit_repair_feed", action="store_true", default=True)
    parser.add_argument("--no-emit-repair-feed", dest="emit_repair_feed", action="store_false")

    parser.add_argument(
        "--print-known-experience",
        action="store_true",
        help="在终端打印命中的经验规则说明。",
    )
    parser.add_argument(
        "--snapshot-baseline",
        action="store_true",
        help="导出当前状态建议基线（不改规则文件）。",
    )
    return parser.parse_args()


def run() -> int:
    args = parse_args()
    project_dir = resolve_project_dir(args.project_dir)
    rules_path = resolve_path(project_dir, args.rules)
    out_dir = resolve_path(project_dir, args.out_dir)
    repair_feed_path = resolve_path(project_dir, args.repair_feed_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    rules = load_rules(rules_path)
    issues: List[Dict[str, Any]] = []
    artifacts: Dict[str, Any] = {
        "project_dir": str(project_dir),
        "rules_path": str(rules_path),
        "mode": args.mode,
        "repair_feed_path": str(repair_feed_path),
    }

    if args.mode == "full":
        run_full_pipeline(
            project_dir,
            issues,
            artifacts,
            full_word_update_fields=args.full_word_update_fields,
        )

    default_docx_report = (
        project_dir / DEFAULT_DOCX_REPORT_NAME
        if args.mode == "fast"
        else project_dir / ".latex-cache" / "smoke" / "main_from_tex_资环模板_smoke_质量报告.md"
    )
    log_path = project_dir / DEFAULT_MAIN_LOG_REL

    artifacts["docx_quality_report"] = {
        "path": str(default_docx_report),
        "exists": default_docx_report.exists(),
    }
    artifacts["main_log"] = {
        "path": str(log_path),
        "exists": log_path.exists(),
    }

    # 1) DOCX 质量报告检查
    observed_docx_checks = parse_docx_quality_report(default_docx_report)
    if not default_docx_report.exists():
        issues.append(
            make_issue(
                severity="new_issue",
                category="docx_quality",
                key="docx_quality_report_missing",
                message="缺少 DOCX 质量报告文件。",
                detail=str(default_docx_report),
            )
        )
    elif not observed_docx_checks:
        issues.append(
            make_issue(
                severity="new_issue",
                category="docx_quality",
                key="docx_quality_report_unparsed",
                message="DOCX 质量报告存在，但未解析到检查表。",
                detail=str(default_docx_report),
            )
        )

    for entry in rules.get("docx_quality_checks", []):
        key = str(entry.get("key", "")).strip()
        item = str(entry.get("item", "")).strip()
        expected_raw = entry.get("expected_status", "PASS")
        expected_list = (
            [status.upper() for status in expected_raw]
            if isinstance(expected_raw, list)
            else [str(expected_raw).upper()]
        )

        observed = observed_docx_checks.get(item)
        if observed is None:
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="docx_quality",
                    key=key or item,
                    message=f"未在质量报告中找到检查项：{item}",
                    detail=f"expected={expected_list}",
                )
            )
            continue

        actual = observed.get("status", "").upper()
        detail = observed.get("detail", "")
        if actual in expected_list:
            if any(x.startswith("WARN") for x in expected_list):
                issues.append(
                    make_issue(
                        severity="baseline_issue",
                        category="docx_quality",
                        key=key or item,
                        message=f"{item} 命中已知基线状态：{actual}",
                        detail=detail,
                    )
                )
            else:
                issues.append(
                    make_issue(
                        severity="info",
                        category="docx_quality",
                        key=key or item,
                        message=f"{item} 状态符合预期：{actual}",
                        detail=detail,
                    )
                )
            continue

        if "PASS" in expected_list and actual != "PASS":
            sev = "new_issue"
        elif any(x.startswith("WARN") for x in expected_list) and actual == "PASS":
            sev = "info"
        else:
            sev = "new_issue"

        issues.append(
            make_issue(
                severity=sev,
                category="docx_quality",
                key=key or item,
                message=f"{item} 状态偏离基线：expected={expected_list}, actual={actual}",
                detail=detail,
            )
        )

    # 2) 日志 warning 检查
    warning_counts: Dict[str, int] = {}
    baseline_warning_patterns: List[Tuple[Dict[str, Any], Optional[re.Pattern[str]]]] = []
    log_text = ""
    if log_path.exists():
        log_text = safe_read_text(log_path)
    else:
        issues.append(
            make_issue(
                severity="new_issue",
                category="log_warning",
                key="main_log_missing",
                message="缺少 .latex-cache/main.log，无法执行 warning 基线检查。",
                detail=str(log_path),
            )
        )

    for entry in rules.get("log_warning_baseline", []):
        key = str(entry.get("key", "")).strip()
        regex = str(entry.get("regex", "")).strip()
        max_count = int(entry.get("max_count", 0))
        try:
            compiled = re.compile(regex, re.MULTILINE)
        except re.error as exc:
            compiled = None
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="rule_config",
                    key=key or "invalid_regex",
                    message=f"log_warning_baseline 正则无效：{regex}",
                    detail=str(exc),
                )
            )
        baseline_warning_patterns.append((entry, compiled))
        count = len(compiled.findall(log_text)) if compiled else 0
        warning_counts[key] = count

        if count > max_count:
            severity = "new_issue"
            msg = f"log warning 超出基线：{key} ({count} > {max_count})"
        elif count > 0:
            severity = "baseline_issue"
            msg = f"log warning 命中基线：{key} ({count}/{max_count})"
        else:
            severity = "info"
            msg = f"log warning 当前未命中：{key} (0/{max_count})"

        issues.append(
            make_issue(
                severity=severity,
                category="log_warning",
                key=key,
                message=msg,
                detail=entry.get("description", ""),
            )
        )

    if log_text:
        unknown_signatures: Counter[str] = Counter()
        warning_lines = extract_warning_lines(log_text)
        compiled_list = [pat for _, pat in baseline_warning_patterns if pat is not None]
        for line in warning_lines:
            if any(pat.search(line) for pat in compiled_list):
                continue
            unknown_signatures[normalize_warning_signature(line)] += 1

        for signature, count in unknown_signatures.most_common():
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="log_warning",
                    key="unknown_warning_signature",
                    message=f"发现未纳入基线的 warning 签名（{count} 次）",
                    detail=signature,
                )
            )

    # 3) 静态扫描
    for entry in rules.get("static_pattern_checks", []):
        key = str(entry.get("key", ""))
        severity_on_match = str(entry.get("severity_on_match", "new_issue"))
        files = collect_files_for_target(project_dir, entry)
        patterns = [str(p) for p in entry.get("patterns", [])]
        total_hits, sampled_hits, invalid_patterns = scan_patterns(files, patterns)

        if invalid_patterns:
            issues.append(
                make_issue(
                    severity="new_issue",
                    category="rule_config",
                    key=key,
                    message="静态规则存在无效正则。",
                    detail="; ".join(invalid_patterns),
                )
            )

        if total_hits > 0:
            issues.append(
                make_issue(
                    severity=severity_on_match,
                    category="static_pattern",
                    key=key,
                    message=f"静态规则命中 {total_hits} 处。",
                    detail=entry.get("description", ""),
                    extra={"sample_hits": sampled_hits[:20]},
                )
            )
        else:
            issues.append(
                make_issue(
                    severity="info",
                    category="static_pattern",
                    key=key,
                    message="静态规则未命中（当前为 0）。",
                    detail=entry.get("description", ""),
                )
            )

    # 4) 参考文献专项检查（citation_audit）
    citation_audit_payload = run_citation_audit(
        project_dir=project_dir,
        rules=rules,
        out_dir=out_dir,
        issues=issues,
        artifacts=artifacts,
    )

    # 5) 经验规则命中
    experience_hits = build_experience_hits(rules, issues)

    if args.print_known_experience and experience_hits:
        print("[经验命中]")
        for item in experience_hits:
            print(
                "- {title} ({source}) -> {checks}".format(
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    checks=", ".join(item.get("related_checks", [])),
                )
            )

    # 6) 汇总与输出
    summary_counter = Counter(issue.get("severity", "info") for issue in issues)
    summary = {
        "new_issue": int(summary_counter.get("new_issue", 0)),
        "baseline_issue": int(summary_counter.get("baseline_issue", 0)),
        "info": int(summary_counter.get("info", 0)),
        "total": len(issues),
    }

    snapshot: Optional[Dict[str, Any]] = None
    snapshot_paths: Dict[str, str] = {}
    if args.snapshot_baseline:
        snapshot = generate_snapshot(
            observed_docx_checks=observed_docx_checks,
            rules=rules,
            warning_counts=warning_counts,
        )
        snapshot_paths = write_snapshot_files(out_dir, snapshot)

    payload = {
        "meta": {
            "timestamp": now_str(),
            "mode": args.mode,
            "project_dir": str(project_dir),
            "rules_path": str(rules_path),
            "out_dir": str(out_dir),
        },
        "artifacts": artifacts,
        "summary": summary,
        "issues": issues,
        "citation_audit": citation_audit_payload,
        "experience_hits": experience_hits,
        "snapshot": snapshot if snapshot is not None else {},
    }

    # full 模式下构建会重建 .latex-cache，输出前再次确保 out-dir 存在。
    out_dir.mkdir(parents=True, exist_ok=True)

    report_paths: Dict[str, str] = {}
    stamp = now_token()
    if args.emit_json:
        json_path = out_dir / f"format_quality_{args.mode}_{stamp}.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report_paths["json"] = str(json_path)

    if args.emit_markdown:
        md_path = out_dir / f"format_quality_{args.mode}_{stamp}.md"
        lines = [
            "# UCAS 格式巡检报告",
            "",
            f"- 时间：{payload['meta']['timestamp']}",
            f"- 模式：`{args.mode}`",
            f"- 项目目录：`{project_dir}`",
            f"- 规则文件：`{rules_path}`",
            "",
            "## 汇总",
            "",
            f"- 新增问题：`{summary['new_issue']}`",
            f"- 基线问题：`{summary['baseline_issue']}`",
            f"- 信息：`{summary['info']}`",
            f"- 总计：`{summary['total']}`",
            "",
            "## 关键产物",
            "",
        ]
        for key, value in artifacts.items():
            lines.append(f"- `{key}`: `{value}`")

        new_issues = [item for item in issues if item.get("severity") == "new_issue"]
        baseline_issues = [item for item in issues if item.get("severity") == "baseline_issue"]

        lines.extend(["", "## 新增问题", ""])
        if not new_issues:
            lines.append("- 无。")
        else:
            for item in new_issues:
                lines.append(
                    "- `{key}` [{category}] {message}".format(
                        key=item.get("key", ""),
                        category=item.get("category", ""),
                        message=item.get("message", ""),
                    )
                )
                if item.get("detail"):
                    lines.append(f"  detail: {item['detail']}")
                if item.get("sample_hits"):
                    for hit in item["sample_hits"][:5]:
                        lines.append(
                            "  sample: {file}:{line} {snippet}".format(
                                file=hit.get("file", ""),
                                line=hit.get("line", ""),
                                snippet=hit.get("snippet", ""),
                            )
                        )

        lines.extend(["", "## 基线问题", ""])
        if not baseline_issues:
            lines.append("- 无。")
        else:
            for item in baseline_issues:
                lines.append(
                    "- `{key}` [{category}] {message}".format(
                        key=item.get("key", ""),
                        category=item.get("category", ""),
                        message=item.get("message", ""),
                    )
                )

        lines.extend(["", "## 参考文献专项检查", ""])
        citation_checks = citation_audit_payload.get("checks", {})
        if not citation_checks:
            lines.append("- 无（未产出专项检查结果）。")
        else:
            for check_key in sorted(citation_checks.keys()):
                item = citation_checks.get(check_key, {})
                lines.append(
                    "- `{key}`: `{status}` (hits={hits})".format(
                        key=check_key,
                        status=item.get("status", "PASS"),
                        hits=item.get("hits", 0),
                    )
                )
            citation_new = [
                item
                for item in issues
                if item.get("category") == "citation_audit" and item.get("severity") == "new_issue"
            ]
            citation_warn = [
                item
                for item in issues
                if item.get("category") == "citation_audit" and item.get("severity") == "baseline_issue"
            ]
            if citation_new:
                lines.extend(["", "### 参考文献新增问题", ""])
                for item in citation_new:
                    lines.append(f"- `{item.get('key', '')}` {item.get('message', '')}")
                    if item.get("detail"):
                        lines.append(f"  detail: {item.get('detail', '')}")
                    if item.get("sample_hits"):
                        for hit in item["sample_hits"][:3]:
                            lines.append(f"  sample: {hit}")
            if citation_warn:
                lines.extend(["", "### 参考文献基线问题", ""])
                for item in citation_warn:
                    lines.append(f"- `{item.get('key', '')}` {item.get('message', '')}")

        lines.extend(["", "## 经验命中", ""])
        if not experience_hits:
            lines.append("- 无。")
        else:
            for hit in experience_hits:
                lines.append(
                    "- `{title}` -> {checks}".format(
                        title=hit.get("title", ""),
                        checks=", ".join(hit.get("related_checks", [])),
                    )
                )
                lines.append(f"  source: {hit.get('source', '')}")
                lines.append(f"  note: {hit.get('message', '')}")

        if snapshot_paths:
            lines.extend(["", "## 基线快照", ""])
            if snapshot_paths.get("json"):
                lines.append(f"- json: `{snapshot_paths['json']}`")
            if snapshot_paths.get("markdown"):
                lines.append(f"- markdown: `{snapshot_paths['markdown']}`")

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report_paths["markdown"] = str(md_path)

    repair_feed_paths: Dict[str, str] = {}
    if args.emit_repair_feed:
        repair_payload = collect_repair_feed(project_dir, quality_issues=issues)
        repair_payload["source_mode"] = args.mode
        repair_payload["quality_report_json"] = report_paths.get("json", "")
        repair_payload["quality_report_markdown"] = report_paths.get("markdown", "")
        repair_payload["rules_path"] = str(rules_path)
        repair_feed_path.parent.mkdir(parents=True, exist_ok=True)
        repair_feed_path.write_text(
            json.dumps(repair_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        repair_feed_paths["json"] = str(repair_feed_path)
        artifacts["repair_feed"] = {
            "path": str(repair_feed_path),
            "total_issues": repair_payload.get("total_issues", 0),
            "fixable_issues": repair_payload.get("fixable_issues", 0),
        }

    print(
        "[SUMMARY] mode={mode} new_issue={new_issue} baseline_issue={baseline_issue} info={info} total={total}".format(
            mode=args.mode,
            **summary,
        )
    )
    top_new = [item for item in issues if item.get("severity") == "new_issue"][:10]
    if top_new:
        print("[TOP NEW ISSUES]")
        for item in top_new:
            print(
                "- {key} [{category}] {message}".format(
                    key=item.get("key", ""),
                    category=item.get("category", ""),
                    message=item.get("message", ""),
                )
            )
    else:
        print("[TOP NEW ISSUES] none")

    if report_paths.get("json"):
        print(f"[REPORT] json: {report_paths['json']}")
    if report_paths.get("markdown"):
        print(f"[REPORT] markdown: {report_paths['markdown']}")
    if snapshot_paths.get("json"):
        print(f"[SNAPSHOT] json: {snapshot_paths['json']}")
    if snapshot_paths.get("markdown"):
        print(f"[SNAPSHOT] markdown: {snapshot_paths['markdown']}")
    if repair_feed_paths.get("json"):
        print(f"[REPAIR_FEED] json: {repair_feed_paths['json']}")

    # 只统计不阻断：始终返回 0
    return 0


def main() -> int:
    try:
        return run()
    except Exception:
        print("[FATAL] check_format_quality.py 内部异常，按只统计口径返回 0。", file=sys.stderr)
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
