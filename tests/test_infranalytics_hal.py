"""Tests for Infranalytics_Hal.py — covers bugs #5, #6, #7, #9."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from Infranalytics_Hal import _first, deduplicate, format_doc


# ── Bug 5 & 6 : _first() peut retourner un non-string, crashant [:10] / [:400] ──

class TestFirst:
    def test_none_in_list_returns_default_not_none(self):
        """abstract_s = [None] → _first doit retourner '' et non None."""
        result = _first([None])
        assert result == "", f"Expected '', got {result!r}"

    def test_none_in_list_is_sliceable(self):
        """_first([None])[:400] ne doit pas lever TypeError."""
        assert _first([None])[:400] == ""

    def test_empty_list_returns_default(self):
        assert _first([]) == ""

    def test_scalar_string_returned_as_is(self):
        assert _first("hello") == "hello"

    def test_list_first_element_returned(self):
        assert _first(["a", "b"]) == "a"


class TestFormatDocDateSlice:
    """format_doc ne doit pas crasher si producedDate_tdate est un entier."""

    def test_integer_date_field_does_not_crash(self):
        doc = {
            "halId_s": "hal-001",
            "title_s": ["Titre"],
            "producedDate_tdate": 1700000000,   # entier — cas anormal mais défensif
        }
        result = format_doc(doc)
        # doit retourner une string de longueur ≤ 10 sans lever TypeError
        assert isinstance(result["date_publication"], str)
        assert len(result["date_publication"]) <= 10

    def test_integer_submitted_date_does_not_crash(self):
        doc = {
            "halId_s": "hal-001",
            "title_s": ["Titre"],
            "submittedDate_tdate": 1700000000,
        }
        result = format_doc(doc)
        assert isinstance(result["date_depot"], str)

    def test_abstract_none_in_list_does_not_crash(self):
        doc = {
            "halId_s": "hal-001",
            "title_s": ["Titre"],
            "abstract_s": [None],
        }
        result = format_doc(doc)
        assert isinstance(result["resume"], str)


# ── Bug 7 : deduplicate() — clé vide provoque fusion silencieuse ──

class TestDeduplicate:
    def test_docs_without_halid_all_kept(self):
        """Deux docs sans halId_s ni docid doivent être tous deux conservés."""
        docs = [{"title_s": "A"}, {"title_s": "B"}, {"title_s": "C"}]
        result = deduplicate(docs)
        assert len(result) == 3

    def test_real_duplicates_removed(self):
        docs = [
            {"halId_s": "hal-001", "title_s": "First"},
            {"halId_s": "hal-001", "title_s": "Duplicate"},
            {"halId_s": "hal-002", "title_s": "Other"},
        ]
        result = deduplicate(docs)
        assert len(result) == 2
        assert result[0]["title_s"] == "First"

    def test_doc_without_id_kept_alongside_empty_halid(self):
        """Un doc sans champ halId_s ne doit pas fusionner avec halId_s=''."""
        docs = [{"title_s": "No field"}, {"halId_s": "", "title_s": "Empty string"}]
        result = deduplicate(docs)
        assert len(result) == 2
