"""Train the character tagger.

The model reads text without diacritics and answers, for every character that could carry
one, whether it does. Characters that could not carry a diacritic are masked out of the
loss: two thirds of the text is punctuation, digits and letters with no alternative, and
learning to say "keep" there teaches nothing.

The defaults train on the Wikipedia split alone: two epochs, about a quarter of an hour on a
laptop GPU. Several files may be given; they are read in full and shuffled together. The
shipped model reads the web sample too, which is what `poe tagger` runs:

    uv run --group train python scripts/train_tagger.py --sentences 200000   # a quick run
    uv run --group train python scripts/train_tagger.py \\
        --train data/processed/train.txt data/processed/web_train.txt \\
        --dev data/processed/dev.txt data/processed/web_dev.txt --parts 2
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import torch
from schwa._tagger_model import PAD_ID, CharTagger, predict_labels, save_checkpoint
from schwa.alphabet import az_upper, is_foldable, strip_diacritics, to_labels
from schwa.tagger import CharVocabulary, TaggerConfig
from schwa.tokenize import iter_words
from torch import nn

DEFAULT_TRAIN = Path("data/processed/train.txt")
DEFAULT_DEV = Path("data/processed/dev.txt")
DEFAULT_OUT = Path("models/tagger.pt")

IGNORE = -100


def read_sentences(path: Path, limit: int = 0) -> list[str]:
    with path.open(encoding="utf-8") as source:
        if not limit:
            return [line.strip() for line in source if line.strip()]
        sentences = []
        for line in source:
            if line.strip():
                sentences.append(line.strip())
            if len(sentences) >= limit:
                break
        return sentences


def shout(sentence: str, rate: float, rng: random.Random) -> str:
    """Now and then put the sentence, or one word of it, in capitals.

    Headlines and emphasis are typed in capitals, and there the i-family turns around: a
    plain "I" is dotted İ far more often than dotless I, while a plain "i" is usually just i.
    Wikipedia has too few capitals to teach that, and on web text words in capitals were
    the ones the model got wrong most often.
    """
    if rate <= 0:
        return sentence
    shouted = sentence
    if rng.random() < rate:
        shouted = az_upper(sentence)
    elif rng.random() < rate:
        spans = iter_words(sentence)
        if spans:
            start, end = rng.choice(spans)
            shouted = sentence[:start] + az_upper(sentence[start:end]) + sentence[end:]
    # Upper-casing may not change the length; if some rare character would, leave it be.
    return shouted if len(shouted) == len(sentence) else sentence


def encode_pair(sentence: str, vocabulary: CharVocabulary) -> tuple[list[int], list[int]]:
    """Return character ids and the target label of every position."""
    stripped, labels = to_labels(sentence)
    ids = vocabulary.encode(stripped)
    targets = [
        label if is_foldable(char) else IGNORE for char, label in zip(stripped, labels, strict=True)
    ]
    return ids, targets


def batches(
    sentences: Sequence[str],
    vocabulary: CharVocabulary,
    batch_size: int,
    device: torch.device | str,
    shuffle: bool = True,
    caps: float = 0.0,
    rng: random.Random | None = None,
) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
    """Yield padded batches, grouping texts of similar length to waste less padding.

    Augmentation draws from its own `rng`, so switching it on changes what the model reads
    and nothing else: the order of the batches stays the same.
    """
    rng = rng or random.Random(0)
    order = list(range(len(sentences)))
    if shuffle:
        random.shuffle(order)
        # Sort inside large chunks: keeps batches uniform in length while staying random.
        chunk = batch_size * 64
        order = [
            index
            for start in range(0, len(order), chunk)
            for index in sorted(order[start : start + chunk], key=lambda i: len(sentences[i]))
        ]

    for start in range(0, len(order), batch_size):
        rows = [
            encode_pair(shout(sentences[index], caps, rng), vocabulary)
            for index in order[start : start + batch_size]
        ]
        width = max(len(ids) for ids, _ in rows)

        ids = torch.full((len(rows), width), PAD_ID, dtype=torch.long)
        targets = torch.full((len(rows), width), IGNORE, dtype=torch.long)
        for row, (row_ids, row_targets) in enumerate(rows):
            ids[row, : len(row_ids)] = torch.tensor(row_ids, dtype=torch.long)
            targets[row, : len(row_targets)] = torch.tensor(row_targets, dtype=torch.long)

        yield ids.to(device), targets.to(device)


@torch.inference_mode()
def decision_accuracy(
    model: CharTagger,
    vocabulary: CharVocabulary,
    sentences: Sequence[str],
    config: TaggerConfig,
    device: torch.device | str,
) -> float:
    """Share of correct answers on the characters that actually needed a decision."""
    model.eval()
    correct = total = 0

    # The model is only ever given text without diacritics; handing it the reference would
    # measure something it will never see.
    typed = [strip_diacritics(sentence) for sentence in sentences]
    predictions = predict_labels(model, vocabulary, typed, config, device=device)
    for sentence, predicted in zip(sentences, predictions, strict=True):
        stripped, labels = to_labels(sentence)
        for char, expected, got in zip(stripped, labels, predicted, strict=True):
            if is_foldable(char):
                total += 1
                correct += expected == got

    model.train()
    return correct / total if total else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--train", type=Path, nargs="+", default=[DEFAULT_TRAIN])
    parser.add_argument("--dev", type=Path, nargs="+", default=[DEFAULT_DEV])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--sentences", type=int, default=0, help="training sentences to use from each file"
    )
    parser.add_argument(
        "--dev-sentences", type=int, default=3000, help="sentences for checks, from each file"
    )
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=3e-3)
    parser.add_argument("--eval-every", type=int, default=1000, help="batches between checks")
    parser.add_argument(
        "--caps",
        type=float,
        default=0.0,
        help="chance of a sentence in capitals, and again of one word in capitals",
    )
    parser.add_argument(
        "--parts",
        type=int,
        default=1,
        help="push each batch through in this many parts: the same gradient, less GPU memory",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    for path in (*args.train, *args.dev):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    random.seed(args.seed)
    shouting = random.Random(args.seed + 1)
    torch.manual_seed(args.seed)

    print("reading sentences", flush=True)
    training = [
        sentence for path in args.train for sentence in read_sentences(path, args.sentences)
    ]
    development = [
        sentence for path in args.dev for sentence in read_sentences(path, args.dev_sentences)
    ]
    print(f"{len(training)} training sentences, {len(development)} for checks", flush=True)

    vocabulary = CharVocabulary.from_texts(training[:200_000], min_count=50)
    config = TaggerConfig()
    model = CharTagger(len(vocabulary), config).to(args.device)
    parameters = sum(p.numel() for p in model.parameters())
    print(f"{len(vocabulary)} characters, {parameters / 1e6:.2f}M parameters", flush=True)

    optimiser = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * math.ceil(len(training) / args.batch_size)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimiser, max_lr=args.lr, total_steps=steps)
    # Summed, then divided by the decisions in the whole batch: the mean over the batch, however
    # many parts it is pushed through in.
    loss_function = nn.CrossEntropyLoss(ignore_index=IGNORE, reduction="sum")
    use_amp = args.device.startswith("cuda")

    best = 0.0
    step = 0
    started = time.perf_counter()
    model.train()

    for epoch in range(args.epochs):
        for ids, targets in batches(
            training, vocabulary, args.batch_size, args.device, caps=args.caps, rng=shouting
        ):
            decisions = (targets != IGNORE).sum().clamp(min=1)
            optimiser.zero_grad(set_to_none=True)
            loss = torch.zeros((), device=args.device)
            for part_ids, part_targets in zip(
                ids.chunk(args.parts), targets.chunk(args.parts), strict=True
            ):
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=use_amp):
                    logits = model(part_ids)
                    part = loss_function(logits.reshape(-1, 2), part_targets.reshape(-1))
                    part = part / decisions
                part.backward()
                loss += part.detach()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            schedule.step()
            step += 1

            if step % args.eval_every == 0 or step == steps:
                accuracy = decision_accuracy(model, vocabulary, development, config, args.device)
                rate = step * args.batch_size / (time.perf_counter() - started)
                print(
                    f"epoch {epoch + 1} step {step}/{steps} loss {loss.item():.4f} "
                    f"dev decisions {accuracy:.4f} ({rate:.0f} sentences/s)",
                    flush=True,
                )
                if accuracy > best:
                    best = accuracy
                    save_checkpoint(args.out, model, vocabulary, config)

    print(f"best dev decision accuracy {best:.4f} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
