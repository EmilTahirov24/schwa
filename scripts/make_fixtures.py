"""Record what the Python package answers, for the browser build to be checked against.

The extension and the demo page run a JavaScript port of the alphabet, the windowing, the
hybrid and the spell checker, on a different ONNX runtime. Their tests replay these cases and
must agree exactly. Rerun this whenever the bundled model changes.

    uv run python scripts/make_fixtures.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from schwa.alphabet import strip_diacritics
from schwa.bundled import default_restorer, default_speller

DEV = Path("data/processed/dev.txt")
FIXTURES = Path("apps/extension/test/fixtures")

# What no Wikipedia sentence covers: informal text, a name the tagger gets wrong on its own,
# capitals, empty input, and text long enough to be cut into overlapping windows.
RESTORE_CASES = [
    "sence neden basliyaq",
    "men bu gun mektebe getmedim",
    "Sulaveri kendi qedimdir",
    "usaqlar bagcada oynayir",
    "telefonumu evde unutmusam",
    "ISIQ SONDU",
    "",
    "a",
    "salam! nece sen? " * 20,
]

# Typos, colloquial spellings, a capitalised word mid-sentence, a suffixed rare form.
SPELLING_CASES = [
    "sabah mektbe gedecem, xayis edirem",
    "men getmedim, nembilim",
    "Mektb uzaqdir. Mektb",
    "dunen Mektb geldi",
    "kitablarin hamisi burdadi",
    "",
]


def write(name: str, cases: list[dict]) -> None:
    path = FIXTURES / name
    text = json.dumps(cases, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(cases)} cases -> {path}")


def main() -> int:
    if not DEV.exists():
        print(f"missing: {DEV}", file=sys.stderr)
        return 1
    dev = DEV.read_text(encoding="utf-8").splitlines()

    restorer = default_restorer()
    if restorer.name != "hybrid":
        print(f"the bundle gave {restorer.name!r}, not the hybrid; is it built?", file=sys.stderr)
        return 1
    typed = [strip_diacritics(sentence) for sentence in dev[:40]] + RESTORE_CASES
    write("python-hybrid.json", [{"typed": t, "expected": restorer.restore(t)} for t in typed])

    speller = default_speller()
    texts = [strip_diacritics(sentence) for sentence in random.Random(0).sample(dev, 30)]
    write(
        "python-spelling.json",
        [
            {"text": text, "expected": [found.as_dict() for found in speller.check(text)]}
            for text in texts + SPELLING_CASES
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
