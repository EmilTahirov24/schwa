"""Tests for the change list."""

from __future__ import annotations

import pytest
from schwa.changes import changes_between


def test_lists_only_the_words_that_differ():
    changes = changes_between("sence neden gelmedin", "səncə nədən gəlmədin")
    assert [change.typed for change in changes] == ["sence", "neden", "gelmedin"]
    assert [change.restored for change in changes] == ["səncə", "nədən", "gəlmədin"]


def test_reports_spans_that_index_back_into_the_text():
    typed = "bu isiq sondu"
    change = changes_between(typed, "bu işıq söndü")[0]
    assert typed[change.start : change.end] == "isiq"
    assert change.start == 3


def test_identical_texts_have_no_changes():
    assert changes_between("hər şey yerindədir", "hər şey yerindədir") == []


def test_words_that_did_not_change_are_left_out():
    changes = changes_between("men gelmedim", "mən gelmedim")
    assert len(changes) == 1
    assert changes[0].typed == "men"


def test_serialises_for_the_api():
    change = changes_between("sence", "səncə")[0]
    assert change.as_dict() == {"start": 0, "end": 5, "from": "sence", "to": "səncə"}


def test_rejects_texts_of_different_length():
    with pytest.raises(ValueError):
        changes_between("sence", "səncə dedi")
