"""A chat export becomes sentences for the hand-annotated set: only one person's, and only
the ones safe and useful to annotate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "scripts"))

from import_chat import telegram_messages, usable, whatsapp_messages  # noqa: E402

SCRIPT = Path(__file__).parents[3] / "scripts" / "import_chat.py"


def test_both_whatsapp_formats_and_both_clocks_are_read():
    lines = [
        "24.09.2026, 14:05 - Emil: sabah gorusek",
        "[24.09.26, 14:05:33] Emil: sence neden basliyaq",
        "9/24/26, 2:05 PM - Emil: axsam zeng edecem",
        "9/24/26, 2:06\u202fPM - Emil: cox sagol",
    ]
    assert [text for _, text in whatsapp_messages(lines)] == [
        "sabah gorusek",
        "sence neden basliyaq",
        "axsam zeng edecem",
        "cox sagol",
    ]


def test_a_message_over_several_lines_stays_one_message():
    lines = [
        "24.09.2026, 14:05 - Emil: birinci setir",
        "ikinci setir",
        "",
        "24.09.2026, 14:06 - Aysel: ok",
    ]
    assert list(whatsapp_messages(lines)) == [
        ("Emil", "birinci setir ikinci setir"),
        ("Aysel", "ok"),
    ]


def test_whatsapps_own_notices_are_not_glued_onto_a_message():
    lines = [
        "24.09.2026, 14:00 - Emil: salam necesen",
        "24.09.2026, 14:01 - Messages and calls are end-to-end encrypted.",
        "lines after a notice belong to nobody",
    ]
    assert list(whatsapp_messages(lines)) == [("Emil", "salam necesen")]


def test_telegram_text_with_formatting_is_read_whole_and_forwards_are_skipped():
    export = {
        "messages": [
            {
                "type": "message",
                "from": "Emil",
                "text": ["sabah ", {"type": "bold", "text": "gorusek"}],
            },
            {
                "type": "message",
                "from": "Emil",
                "text": "basqasinin yazdigi",
                "forwarded_from": "X",
            },
            {"type": "service", "actor": "Emil", "text": ""},
        ]
    }
    assert list(telegram_messages(export)) == [("Emil", "sabah gorusek")]


def test_a_plain_message_is_kept_as_one_clean_line():
    assert usable("sence  neden\nbasliyaq") == "sence neden basliyaq"
    assert usable("men bunu duzeltdim <This message was edited>") == "men bunu duzeltdim"


def test_anything_private_or_not_really_a_message_is_dropped():
    for text in [
        "bax bura https://example.com cox maraqlidir",
        "mene yaz emil@example.com unvanina",
        "nomrem +994 50 123 45 67 zeng et",
        "<Media omitted>",
        "\u200eimage omitted",
        "This message was deleted",
        "ok",  # too short to be a sentence
        "123 456 789",  # nothing that could be restored
    ]:
        assert usable(text) is None, text


def test_only_the_chosen_author_is_written_and_nothing_is_overwritten(tmp_path: Path):
    chat = tmp_path / "chat.txt"
    chat.write_text(
        "\n".join(
            [
                "24.09.2026, 14:05 - Emil: sabah gorusek inshallah",
                "24.09.2026, 14:06 - Aysel: menim mesajim burda olmamalidir",
                "24.09.2026, 14:07 - Emil: sence neden basliyaq",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "raw.txt"

    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(chat), "--out", str(out), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    assert "Aysel" in run().stdout  # without --me it only lists the authors
    assert not out.exists()

    assert run("--me", "Emil").returncode == 0
    assert sorted(out.read_text(encoding="utf-8").splitlines()) == [
        "sabah gorusek inshallah",
        "sence neden basliyaq",
    ]
    assert run("--me", "Emil").returncode == 1  # the file is there; no --append
