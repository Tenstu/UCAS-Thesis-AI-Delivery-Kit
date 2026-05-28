#!/usr/bin/env python3
"""Tests for format_utils.py - LaTeX parsing utilities."""

import pytest

from scripts.format_tools.format_utils import (
    parse_braced,
    parse_bracketed,
    parse_macro_args,
    latex_inline_to_text,
    _normalize_cjk_number_classifier_spacing,
    _extract_graphicspaths,
    _parse_includegraphics_path,
    _is_simple_stat_inline_math,
    _plainify_simple_stat_inline_math,
)


class TestParseBraced:
    """Tests for parse_braced function."""

    def test_simple_braces(self):
        text = "{hello}"
        result, end = parse_braced(text, 0)
        assert result == "hello"
        assert end == 7

    def test_nested_braces(self):
        text = "{a{b}c}"
        result, end = parse_braced(text, 0)
        assert result == "a{b}c"
        assert end == 7

    def test_escaped_braces(self):
        text = r"{a\{b\}c}"
        result, end = parse_braced(text, 0)
        assert result == r"a\{b\}c"
        assert end == 9

    def test_empty_braces(self):
        text = "{}"
        result, end = parse_braced(text, 0)
        assert result == ""
        assert end == 2

    def test_unbalanced_raises(self):
        text = "{hello"
        with pytest.raises(ValueError, match="unbalanced braces"):
            parse_braced(text, 0)

    def test_not_start_with_brace_raises(self):
        text = "hello"
        with pytest.raises(ValueError, match="expects '{' at start"):
            parse_braced(text, 0)


class TestParseBracketed:
    """Tests for parse_bracketed function."""

    def test_simple_brackets(self):
        text = "[hello]"
        result, end = parse_bracketed(text, 0)
        assert result == "hello"
        assert end == 7

    def test_nested_brackets(self):
        text = "[a[b]c]"
        result, end = parse_bracketed(text, 0)
        assert result == "a[b]c"
        assert end == 7

    def test_empty_brackets(self):
        text = "[]"
        result, end = parse_bracketed(text, 0)
        assert result == ""
        assert end == 2

    def test_unbalanced_raises(self):
        text = "[hello"
        with pytest.raises(ValueError, match="unbalanced brackets"):
            parse_bracketed(text, 0)


class TestParseMacroArgs:
    """Tests for parse_macro_args function."""

    def test_single_arg(self):
        text = r"\cite{ref1}"
        result = parse_macro_args(text, "cite", 1)
        assert result == ["ref1"]

    def test_multiple_args(self):
        text = r"\newcommand{\mycmd}{arg2}"
        result = parse_macro_args(text, "newcommand", 2)
        assert result == ["\\mycmd", "arg2"]

    def test_no_match(self):
        text = r"\other{ref1}"
        result = parse_macro_args(text, "cite", 1)
        assert result is None

    def test_with_spaces(self):
        text = r"\cite {ref1}"
        result = parse_macro_args(text, "cite", 1)
        assert result == ["ref1"]


class TestLatexInlineToText:
    """Tests for latex_inline_to_text function."""

    def test_subscript(self):
        text = r"H$_2$O"
        result = latex_inline_to_text(text)
        assert "H" in result
        assert "O" in result

    def test_superscript(self):
        text = r"x$^{2}$"
        result = latex_inline_to_text(text)
        assert "x" in result

    def test_greek_letters(self):
        text = r"\alpha \beta \gamma"
        result = latex_inline_to_text(text)
        assert "α" in result
        assert "β" in result
        assert "γ" in result

    def test_inequalities(self):
        text = r"\leq \geq"
        result = latex_inline_to_text(text)
        assert "≤" in result
        assert "≥" in result

    def test_celsius(self):
        text = r"25\textcelsius"
        result = latex_inline_to_text(text)
        assert "℃" in result

    def test_textbf_removed(self):
        text = r"\textbf{bold}"
        result = latex_inline_to_text(text)
        assert result == "bold"

    def test_textit_to_asterisk(self):
        text = r"\textit{italic}"
        result = latex_inline_to_text(text)
        assert result == "*italic*"

    def test_url_to_angle_brackets(self):
        text = r"\url{https://example.com}"
        result = latex_inline_to_text(text)
        assert result == "<https://example.com>"


class TestNormalizeCjkNumberClassifierSpacing:
    """Tests for _normalize_cjk_number_classifier_spacing function."""

    def test_remove_spaces_cjk_number_cjk(self):
        text = "样本 3 个"
        result = _normalize_cjk_number_classifier_spacing(text)
        assert result == "样本3个"

    def test_no_spaces(self):
        text = "样本3个"
        result = _normalize_cjk_number_classifier_spacing(text)
        assert result == "样本3个"

    def test_empty_string(self):
        text = ""
        result = _normalize_cjk_number_classifier_spacing(text)
        assert result == ""


class TestExtractGraphicspaths:
    """Tests for _extract_graphicspaths function."""

    def test_single_path(self):
        text = r"\graphicspath{{figures/}}"
        result = _extract_graphicspaths(text)
        assert result == ["figures/"]

    def test_multiple_paths(self):
        text = r"\graphicspath{{figures/}{images/}}"
        result = _extract_graphicspaths(text)
        assert result == ["figures/", "images/"]

    def test_no_graphicspath(self):
        text = r"\documentclass{article}"
        result = _extract_graphicspaths(text)
        assert result == []


class TestParseIncludegraphicsPath:
    """Tests for _parse_includegraphics_path function."""

    def test_simple_path(self):
        text = r"\includegraphics{image.png}"
        result = _parse_includegraphics_path(text)
        assert result == "image.png"

    def test_with_options(self):
        text = r"\includegraphics[width=0.5\textwidth]{image.png}"
        result = _parse_includegraphics_path(text)
        assert result == "image.png"

    def test_no_includegraphics(self):
        text = r"\begin{figure}"
        result = _parse_includegraphics_path(text)
        assert result is None


class TestIsSimpleStatInlineMath:
    """Tests for _is_simple_stat_inline_math function."""

    def test_p_value(self):
        expr = r"P<0.05"
        assert _is_simple_stat_inline_math(expr) is True

    def test_r_value(self):
        expr = r"r=0.85"
        assert _is_simple_stat_inline_math(expr) is True

    def test_f_value(self):
        expr = r"F(1,2)=3.45"
        assert _is_simple_stat_inline_math(expr) is True  # F-statistic is a valid simple stat

    def test_percentage(self):
        expr = r"-7.6\%"
        assert _is_simple_stat_inline_math(expr) is True

    def test_confidence_interval(self):
        expr = r"[-0.97, -0.66]"
        assert _is_simple_stat_inline_math(expr) is True

    def test_empty_string(self):
        expr = ""
        assert _is_simple_stat_inline_math(expr) is False


class TestPlainifySimpleStatInlineMath:
    """Tests for _plainify_simple_stat_inline_math function."""

    def test_p_value(self):
        expr = r"P<0.05"
        result = _plainify_simple_stat_inline_math(expr)
        assert "P" in result
        assert "<" in result
        assert "0.05" in result

    def test_r_value(self):
        expr = r"r=0.85"
        result = _plainify_simple_stat_inline_math(expr)
        assert "r" in result
        assert "=" in result
        assert "0.85" in result

    def test_percentage(self):
        expr = r"-7.6\%"
        result = _plainify_simple_stat_inline_math(expr)
        assert "-7.6%" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
