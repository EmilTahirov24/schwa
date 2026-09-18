"""duzelt - restore Azerbaijani diacritics in text typed without them.

>>> from duzelt import restore
>>> restore("sence neden basliyaq")
'səncə nədən başlayaq'
"""

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
from duzelt.bundled import default_restorer, is_bundled, restore

__version__ = "0.1.0.dev0"

__all__ = [
    "FOLD_PAIRS",
    "LABEL_KEEP",
    "LABEL_MARK",
    "STRIP_MAP",
    "__version__",
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
