"""Tests for infralatex.py — covers bugs #1, #2, #3, #8."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from infralatex import latex_escape, format_entry_latex, build_section_latex


# ── Bug 3 : volume_s / issue_s non échappés → compilation LaTeX cassée ──

class TestVolumeIssueEscape:
    BASE = {
        "docType_s": "ART",
        "authFullName_s": ["Smith John"],
        "title_s": ["Test article"],
        "publicationDateY_i": 2024,
        "journalTitle_s": "Nature",
    }

    def test_volume_ampersand_is_escaped(self):
        doc = {**self.BASE, "volume_s": "S1&2"}
        result = format_entry_latex(doc, 1, "art")
        assert "S1&2" not in result, "& brut ne doit pas apparaître dans le LaTeX"
        assert r"S1\&2" in result

    def test_issue_underscore_is_escaped(self):
        doc = {**self.BASE, "volume_s": "10", "issue_s": "3_4"}
        result = format_entry_latex(doc, 1, "art")
        assert "3_4" not in result
        assert r"3\_4" in result

    def test_volume_percent_is_escaped(self):
        doc = {**self.BASE, "volume_s": "50%"}
        result = format_entry_latex(doc, 1, "art")
        assert "50%" not in result
        assert r"50\%" in result


# ── Bug 1 : docType_s='UNDEFINED' (preprint HAL) non reconnu ──

class TestPreprintUndefined:
    def test_undefined_without_journal_shows_preprint_label(self):
        """Sans revue, UNDEFINED doit afficher \\textit{Preprint} — pas juste le titre."""
        doc = {
            "docType_s": "UNDEFINED",
            "authFullName_s": ["Doe Jane"],
            "title_s": ["Un article quelconque"],   # titre sans 'Preprint'
            "producedDateY_i": 2024,
        }
        result = format_entry_latex(doc, 1, "preprint")
        assert r"\textit{Preprint}" in result, f"Label Preprint absent : {result}"

    def test_undefined_with_journal_shows_journal(self):
        """Avec une revue, UNDEFINED doit afficher la revue en gras."""
        doc = {
            "docType_s": "UNDEFINED",
            "authFullName_s": ["Doe Jane"],
            "title_s": ["Un article quelconque"],
            "publicationDateY_i": 2024,
            "journalTitle_s": "arXiv",
        }
        result = format_entry_latex(doc, 1, "preprint")
        assert r"\textbf{arXiv}" in result


# ── Bug 2 : injection LaTeX via identifiants bruts dans \href{URL} ──

class TestHrefInjection:
    BASE = {
        "docType_s": "ART",
        "authFullName_s": ["Smith John"],
        "title_s": ["Test"],
        "publicationDateY_i": 2024,
    }

    def test_doi_brace_does_not_inject(self):
        doc = {**self.BASE, "doiId_s": "10.1000/test}inject"}
        result = format_entry_latex(doc, 1, "art")
        # L'URL brute avec } ne doit pas apparaître telle quelle
        assert "https://doi.org/10.1000/test}inject}" not in result

    def test_hal_id_brace_does_not_inject(self):
        doc = {**self.BASE, "halId_s": "hal-123}evil"}
        result = format_entry_latex(doc, 1, "art")
        assert "https://hal.science/hal-123}evil}" not in result

    def test_swhid_brace_does_not_inject(self):
        doc = {
            "docType_s": "SOFTWARE",
            "authFullName_s": ["Smith John"],
            "title_s": ["Tool"],
            "producedDateY_i": 2024,
            "swhidId_s": "swh:1:rev:abc}evil",
        }
        result = format_entry_latex(doc, 1, "software")
        assert "softwareheritage.org/swh:1:rev:abc}evil}" not in result


# ── Bug 8 : numérotation inversée — [1] doit être la 1re entrée (la plus récente) ──

class TestSectionNumbering:
    DOCS = [
        {"docType_s": "ART", "authFullName_s": ["A"], "title_s": ["T1"], "publicationDateY_i": 2024},
        {"docType_s": "ART", "authFullName_s": ["B"], "title_s": ["T2"], "publicationDateY_i": 2023},
        {"docType_s": "ART", "authFullName_s": ["C"], "title_s": ["T3"], "publicationDateY_i": 2022},
    ]
    SECTION = {"types": ["ART"], "title": "Articles", "label": "art"}

    def test_first_entry_is_numbered_1(self):
        result = build_section_latex(self.SECTION, self.DOCS)
        item_lines = [l for l in result.split("\n") if r"\item[" in l]
        assert r"\textbf{[1]}" in item_lines[0], f"Premier item : {item_lines[0]}"

    def test_last_entry_has_highest_number(self):
        result = build_section_latex(self.SECTION, self.DOCS)
        item_lines = [l for l in result.split("\n") if r"\item[" in l]
        assert r"\textbf{[3]}" in item_lines[-1], f"Dernier item : {item_lines[-1]}"

    def test_two_entries_numbered_1_then_2(self):
        """Avec 2 docs : le 1er (plus récent) = [1], le 2e = [2]."""
        docs = self.DOCS[:2]
        result = build_section_latex(self.SECTION, docs)
        item_lines = [l for l in result.split("\n") if r"\item[" in l]
        assert r"\textbf{[1]}" in item_lines[0]
        assert r"\textbf{[2]}" in item_lines[1]
