#!/usr/bin/env python3
"""Tests for TeX preprocessing scripts."""

import tempfile
from pathlib import Path

import pytest

from scripts.tex_preprocessing.fix_spacing import fix_spacing_in_text
from scripts.tex_preprocessing.normalize_time_unit_spacing import _normalize_text


class TestFixSpacing:
    """Tests for fix_spacing.py"""

    def test_chinese_number_spacing(self):
        """Test removing spaces between Chinese characters and numbers."""
        text = "实验 1 结果"
        result, changes = fix_spacing_in_text(text)
        assert result == "实验1结果"
        assert changes == 2  # Two spaces removed: 验→1 and 1→结

    def test_chinese_english_spacing(self):
        """Test removing spaces between Chinese characters and English letters."""
        text = "使用 latex 排版"
        result, changes = fix_spacing_in_text(text)
        assert result == "使用latex排版"
        assert changes == 2  # Two spaces removed: 用→l and x→排

    def test_number_chinese_spacing(self):
        """Test removing spaces between numbers and Chinese characters."""
        text = "100 个样本"
        result, changes = fix_spacing_in_text(text)
        assert result == "100个样本"
        assert changes == 1

    def test_english_chinese_spacing(self):
        """Test removing spaces between English letters and Chinese characters."""
        text = "latex 排版系统"
        result, changes = fix_spacing_in_text(text)
        assert result == "latex排版系统"
        assert changes == 1

    def test_math_mode_protected(self):
        """Test that math mode is protected from spacing changes."""
        text = "$x = 1$ 实验"
        result, changes = fix_spacing_in_text(text)
        assert "$x = 1$" in result
        assert changes == 0  # Math mode content is protected, space after sentinel not matched

    def test_cite_command_protected(self):
        """Test that citation commands are protected."""
        text = "\\cite{ref1} 文献"
        result, changes = fix_spacing_in_text(text)
        assert "\\cite{ref1}" in result
        assert changes == 0  # Citation command is protected, space after sentinel not matched

    def test_structured_spacing_protected(self):
        """Test that structured spacing patterns are protected."""
        text = "第 2 章内容"
        result, changes = fix_spacing_in_text(text)
        assert "第 2 章" in result
        assert changes == 0  # No changes to structured spacing

    def test_figure_reference_protected(self):
        """Test that figure references are protected."""
        text = "图 3-1 所示"
        result, changes = fix_spacing_in_text(text)
        assert "图 3-1" in result
        assert changes == 0  # No changes to figure references

    def test_multiple_changes(self):
        """Test multiple spacing changes in one text."""
        text = "实验 1 使用 latex 排版"
        result, changes = fix_spacing_in_text(text)
        assert result == "实验1使用latex排版"
        assert changes == 4  # Four spaces removed: 验→1, 1→用, 用→l, x→排


class TestNormalizeTimeUnitSpacing:
    """Tests for normalize_time_unit_spacing.py"""

    def test_day_unit(self):
        """Test normalizing day unit spacing."""
        text = "60 d"
        result, changes, previews = _normalize_text(text)
        assert result == "60~d"
        assert changes == 1

    def test_rpm_unit(self):
        """Test normalizing rpm unit spacing."""
        text = "8000 rpm"
        result, changes, previews = _normalize_text(text)
        assert result == "8000~rpm"
        assert changes == 1

    def test_gram_unit(self):
        """Test normalizing gram unit spacing."""
        text = "5.28 g"
        result, changes, previews = _normalize_text(text)
        assert result == "5.28~g"
        assert changes == 1

    def test_mg_kg_unit(self):
        """Test normalizing mg/kg unit spacing."""
        text = "0.28 mg/kg"
        result, changes, previews = _normalize_text(text)
        assert result == "0.28~mg/kg"
        assert changes == 1

    def test_math_mode_protected(self):
        """Test that math mode is protected from unit normalization."""
        text = "$60 d$ 实验"
        result, changes, previews = _normalize_text(text)
        assert "$60 d$" in result
        assert changes == 0  # No changes in math mode

    def test_comment_protected(self):
        """Test that comments are protected from unit normalization."""
        text = "% 60 d 实验"
        result, changes, previews = _normalize_text(text)
        assert "% 60 d" in result
        assert changes == 0  # No changes in comments

    def test_multiple_units(self):
        """Test normalizing multiple units in one text."""
        text = "60 d 8000 rpm"
        result, changes, previews = _normalize_text(text)
        assert result == "60~d 8000~rpm"
        assert changes == 2

    def test_no_units(self):
        """Test text without units."""
        text = "普通文本"
        result, changes, previews = _normalize_text(text)
        assert result == "普通文本"
        assert changes == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
