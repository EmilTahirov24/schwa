"""duzelt - restore Azerbaijani diacritics in text typed without them."""

from duzelt.alphabet import (
    FOLD_PAIRS,
    LABEL_KEEP,
    LABEL_MARK,
    STRIP_MAP,
    apply_labels,
    az_lower,
    az_upper,
    is_foldable,
    mark,
    strip_diacritics,
    to_labels,
)

__version__ = "0.1.0.dev0"

__all__ = [
    "FOLD_PAIRS",
    "LABEL_KEEP",
    "LABEL_MARK",
    "STRIP_MAP",
    "__version__",
    "apply_labels",
    "az_lower",
    "az_upper",
    "is_foldable",
    "mark",
    "strip_diacritics",
    "to_labels",
]
