"""Pick the best restorer the deployment actually has files for.

The service should run with whatever is present: a bare lexicon on a small box, the context
model when it is shipped alongside, the character tagger once it is trained. Each step up is
optional, and the one in use is reported by ``/v1/info`` so a demo can never quietly serve a
weaker model than the numbers next to it claim.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from duzelt.context import ContextModel
from duzelt.lexicon import Lexicon
from duzelt.restore import (
    ContextRestorer,
    HybridRestorer,
    IdentityRestorer,
    LexiconRestorer,
    Restorer,
)

ENV_LEXICON = "DUZELT_LEXICON"
ENV_CONTEXT = "DUZELT_CONTEXT"
ENV_TAGGER = "DUZELT_TAGGER"


@dataclass(frozen=True)
class Loaded:
    """The restorer in use and where it came from."""

    restorer: Restorer
    sources: dict[str, str]

    @property
    def name(self) -> str:
        return self.restorer.name


def _path_from_env(variable: str) -> Path | None:
    value = os.environ.get(variable)
    if not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def load_restorer() -> Loaded:
    """Build the strongest restorer whose files are present."""
    sources: dict[str, str] = {}

    tagger_path = _path_from_env(ENV_TAGGER)
    lexicon_path = _path_from_env(ENV_LEXICON)

    if tagger_path is not None:
        sources["tagger"] = str(tagger_path)
        # An .onnx file runs on onnxruntime alone, which is what lets the image ship
        # without torch; a checkpoint is still accepted for a machine that has it.
        if tagger_path.suffix == ".onnx":
            from duzelt.onnx_tagger import load_onnx_restorer

            tagger: Restorer = load_onnx_restorer(tagger_path)
        else:
            from duzelt.tagger import TaggerRestorer

            tagger = TaggerRestorer.from_checkpoint(tagger_path)

        # With a lexicon beside it the tagger gets overruled on words the training text was
        # unanimous about, which is worth 1.5 points of whole-sentence accuracy on dev.
        if lexicon_path is not None:
            sources["lexicon"] = str(lexicon_path)
            return Loaded(HybridRestorer(tagger, Lexicon.load(lexicon_path)), sources)

        return Loaded(tagger, sources)

    if lexicon_path is None:
        return Loaded(IdentityRestorer(), sources)

    sources["lexicon"] = str(lexicon_path)
    lexicon = Lexicon.load(lexicon_path)

    context_path = _path_from_env(ENV_CONTEXT)
    if context_path is not None:
        sources["context"] = str(context_path)
        return Loaded(ContextRestorer(lexicon, ContextModel.load(context_path)), sources)

    return Loaded(LexiconRestorer(lexicon), sources)
