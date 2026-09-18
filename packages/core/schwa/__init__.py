"""schwa - restore Azerbaijani diacritics in text typed without them.

>>> from schwa import restore
>>> restore("sence neden basliyaq")
'səncə nədən başlayaq'
"""

from schwa.alphabet import (
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
from schwa.bundled import check, default_restorer, is_bundled, restore

__version__ = "0.1.0.dev0"

__all__ = [
    "FOLD_PAIRS",
    "LABEL_KEEP",
    "LABEL_MARK",
    "STRIP_MAP",
    "__version__",
    "check",
    "default_restorer",
    "is_bundled",
    "restore",
    "apply_labels",
    "az_lower",
    "az_upper",
    "is_foldable",
    "mark",
    "strip_diacritics",
    "to_labels",
]
