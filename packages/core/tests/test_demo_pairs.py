"""The demo page's example sentences must be what the model actually returns.

The opening animation on the site shows five sentences restoring themselves, and the page
says they are recorded from the shipped model. This test keeps that sentence true: if the
model changes and its answers move, the demo has to be updated rather than quietly showing
output the model no longer produces.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from schwa import bundled

STRINGS = Path(__file__).parents[3] / "apps" / "web" / "src" / "lib" / "strings.ts"
PAIR = re.compile(r'\["([^"]+)",\s*"([^"]+)"\]')

pytest.importorskip("onnxruntime")
pytestmark = pytest.mark.skipif(not bundled.is_bundled(), reason="run `poe bundle` first")


def demo_pairs() -> list[tuple[str, str]]:
    source = STRINGS.read_text(encoding="utf-8")
    block = source.split("DEMO_PAIRS", 1)[1].split("];", 1)[0]
    return PAIR.findall(block)


def test_the_demo_has_examples():
    assert len(demo_pairs()) >= 3


@pytest.mark.parametrize(("typed", "shown"), demo_pairs())
def test_each_example_is_the_models_real_answer(typed: str, shown: str):
    assert bundled.restore(typed) == shown
