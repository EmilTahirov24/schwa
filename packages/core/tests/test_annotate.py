"""Annotating a sentence should cost as little typing as the correction needs, and never let
anything but diacritics change."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))

from annotate import apply_answer  # noqa: E402

SCRIPT = Path(__file__).parents[3] / "scripts" / "annotate.py"
TYPED = "bu gun yeni ev aldiq"
GUESS = "bu gün yeni ev aldıq"


def test_enter_keeps_the_suggestion():
    assert apply_answer(TYPED, GUESS, "") == GUESS


def test_one_wrong_word_is_put_right_by_typing_only_that_word():
    assert apply_answer(TYPED, GUESS, "yəni") == "bu gün yəni ev aldıq"


def test_the_word_takes_the_capitals_of_the_word_it_replaces():
    assert apply_answer("Yeni ev aldiq", "Yeni ev aldıq", "yəni") == "Yəni ev aldıq"
    assert apply_answer("YENI EV", "YENI EV", "yəni") == "YƏNİ EV"


def test_several_words_can_be_put_right_at_once():
    typed = "sehere gedirem yeni"
    assert apply_answer(typed, "səhərə gedirəm yeni", "şəhərə yəni") == "şəhərə gedirəm yəni"


def test_the_whole_sentence_still_replaces_the_suggestion():
    assert apply_answer(TYPED, GUESS, "bu gün yəni ev aldıq") == "bu gün yəni ev aldıq"


def test_a_word_that_is_not_in_the_sentence_or_is_there_twice_is_refused():
    assert apply_answer(TYPED, GUESS, "yani") is None  # not these letters
    assert apply_answer(TYPED, GUESS, "gəlirəm") is None  # not in the sentence
    assert apply_answer("yeni yeni", "yeni yeni", "yəni") is None  # which one?


def test_fixes_add_up_until_enter_accepts_them(tmp_path: Path):
    raw = tmp_path / "raw.txt"
    raw.write_text(f"{TYPED}\nsabah gorusek\n", encoding="utf-8")
    lexicon = tmp_path / "lexicon.jsonl"
    forms = {
        "bu": {"bu": 9},
        "gun": {"gün": 9},
        "yeni": {"yeni": 9, "yəni": 8},
        "ev": {"ev": 9},
        "aldiq": {"aldıq": 9},
    }
    lexicon.write_text(
        "".join(
            json.dumps({"key": k, "forms": v}, ensure_ascii=False) + "\n" for k, v in forms.items()
        ),
        encoding="utf-8",
    )
    out = tmp_path / "annotated.jsonl"

    # A word nobody wrote, then the right word, then Enter; then stop at the second sentence.
    typing = "gəlirəm\nyəni\n\nq\n"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--raw", str(raw), "--out", str(out)]
        + ["--lexicon", str(lexicon), "--annotator", "test"],
        input=typing,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"typed": TYPED, "correct": "bu gün yəni ev aldıq", "annotator": "test"}]
