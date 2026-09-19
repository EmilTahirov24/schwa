# schwa-az

Restore Azerbaijani diacritics in text typed without them:
`sence neden basliyaq` → `səncə nədən başlıyaq`.

```bash
pip install "schwa-az[onnx] @ git+https://github.com/EmilTahirov24/schwa#subdirectory=packages/core"
```

(It is not on PyPI yet; that installs it straight from the repository, model included.)

```python
from schwa import check, restore

restore("sence neden basliyaq")  # 'səncə nədən başlıyaq'

for suggestion in check("xayis edirem"):
    print(suggestion.typed, suggestion.options)  # xayis ('xahiş', 'xalis', 'mayıs')
```

```bash
schwa "sence neden basliyaq"
cat notes.txt | schwa
schwa --spell "xayis edirem, mektbe gec qalmisam"
```

The model travels with the package: a character-level BiLSTM, quantised to 2.3 MB and run on
the CPU through onnxruntime, corrected by a lexicon of the words its training text always
spelled one way. Nothing is downloaded, and no text leaves the machine. Without the `[onnx]`
extra the package still works, with the lexicon alone.

Spelling is kept apart: `restore` only ever puts diacritics back, while `check` suggests
corrections for words that look misspelt and never applies them.

## How well it works

Measured on text no model read in training. Ambiguous words are the ones whose typed form
stands for more than one real word - the part a restorer can actually get wrong.

Wikipedia, 172,328 sentences:

<!-- results: test -->
| System | Ambiguous word accuracy | Sentence accuracy |
| --- | --- | --- |
| hybrid | 93.9% | 88.2% |

Web text, 268,532 sentences:

<!-- results: web_test -->
| System | Ambiguous word accuracy | Sentence accuracy |
| --- | --- | --- |
| hybrid | 95.7% | 92.9% |

How that was measured, where it still fails, and the browser extension and demo page that run
the same model are in the [repository](https://github.com/EmilTahirov24/schwa).

## Also in here

`az_lower` and `az_upper`, because Python's own case functions get `i`, `ı`, `İ` and `I`
wrong for Azerbaijani, and `strip_diacritics`, which turns text into what someone without the
layout would have typed.
