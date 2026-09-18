# schwa

Restore Azerbaijani diacritics in text typed without them:
`sence neden basliyaq` → `səncə nədən başlıyaq`.

This package holds the library and the command line tool. The browser extension, the web
demo, and the training pipeline live in the [project repository](https://github.com/EmilTahirov24/schwa).

```python
from schwa import strip_diacritics, az_lower

strip_diacritics("səncə nədən başlayaq")  # -> "sence neden baslayaq"
az_lower("IŞIQ")  # -> "ışıq", unlike str.lower()
```

Restoration itself is in progress; this release contains the alphabet layer it is built
on. See the repository for current results.
