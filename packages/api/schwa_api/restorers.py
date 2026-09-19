"""Pick the restorer the service runs.

With no configuration it runs the model the package ships - the tagger corrected by the
lexicon, the system the README's numbers are about. The environment can point it at other
files instead: a bare lexicon, the context model, another tagger. Whichever is in use is
reported by ``/v1/info``, so a deployment can never quietly serve a weaker model than the
numbers next to it claim.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from schwa.context import ContextModel
from schwa.lexicon import Lexicon
from schwa.restore import (
    ContextRestorer,
    HybridRestorer,
    IdentityRestorer,
    LexiconRestorer,
    Restorer,
)

ENV_LEXICON = "SCHWA_LEXICON"
ENV_CONTEXT = "SCHWA_CONTEXT"
ENV_TAGGER = "SCHWA_TAGGER"


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


def shipped() -> Loaded:
    """The model the package carries, or no change at all if this installation has none."""
    from schwa import bundled

    if not bundled.is_bundled():
        return Loaded(IdentityRestorer(), {})
    return Loaded(bundled.default_restorer(), {"bundle": str(bundled.MODEL.parent)})


def load_restorer() -> Loaded:
    """The restorer the environment names, or the shipped one when it names none."""
    sources: dict[str, str] = {}

    tagger_path = _path_from_env(ENV_TAGGER)
    lexicon_path = _path_from_env(ENV_LEXICON)

    if tagger_path is not None:
        sources["tagger"] = str(tagger_path)
        # An .onnx file runs on onnxruntime alone, which is what lets the image ship
        # without torch; a checkpoint is still accepted for a machine that has it.
        if tagger_path.suffix == ".onnx":
            from schwa.onnx_tagger import load_onnx_restorer

            tagger: Restorer = load_onnx_restorer(tagger_path)
        else:
            from schwa.tagger import TaggerRestorer

            tagger = TaggerRestorer.from_checkpoint(tagger_path)

        # With a lexicon beside it the tagger gets overruled on words the training text was
        # unanimous about, which is worth 1.5 points of whole-sentence accuracy on dev.
        if lexicon_path is not None:
            sources["lexicon"] = str(lexicon_path)
            return Loaded(HybridRestorer(tagger, Lexicon.load(lexicon_path)), sources)

        return Loaded(tagger, sources)

    if lexicon_path is None:
        return shipped()

    sources["lexicon"] = str(lexicon_path)
    lexicon = Lexicon.load(lexicon_path)

    context_path = _path_from_env(ENV_CONTEXT)
    if context_path is not None:
        sources["context"] = str(context_path)
        return Loaded(ContextRestorer(lexicon, ContextModel.load(context_path)), sources)

    return Loaded(LexiconRestorer(lexicon), sources)
