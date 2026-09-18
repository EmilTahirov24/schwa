"""Render the extension icons.

Chrome only accepts PNG, so the shapes in `apps/extension/icons/icon.svg` are drawn again
here rather than converted: it keeps the toolchain to one library and the sizes exact.

    uv run --group train python scripts/make_icons.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

DEFAULT_OUT = Path("apps/extension/icons")
SIZES = (16, 32, 48, 128)

BACKGROUND = "#171717"
INK = "#fafafa"
ACCENT = "#34d399"

#: Everything is drawn on a 128-unit grid and scaled down, which keeps the proportions the
#: same at every size instead of drifting with rounding.
GRID = 128
SUPERSAMPLE = 8


def draw_icon() -> Image.Image:
    """The mark: a schwa, the letter people drop most often."""
    side = GRID * SUPERSAMPLE
    scale = SUPERSAMPLE
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, side - 1, side - 1), radius=28 * scale, fill=BACKGROUND)

    stroke = 13 * scale
    centre_x, centre_y, radius = 64 * scale, 66 * scale, 31 * scale
    box = (centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius)

    # A schwa is a rotated "e", so the ring is open where the "e" opens — at the upper left
    # once turned around — and the bar sits below the centre rather than above it.
    draw.arc(box, start=245, end=560, fill=INK, width=stroke)
    draw.line(
        (centre_x - radius + stroke // 2, 76 * scale, centre_x + radius - stroke // 2, 76 * scale),
        fill=INK,
        width=stroke,
    )

    dot, dot_radius = (98 * scale, 30 * scale), 10 * scale
    draw.ellipse(
        (
            dot[0] - dot_radius,
            dot[1] - dot_radius,
            dot[0] + dot_radius,
            dot[1] + dot_radius,
        ),
        fill=ACCENT,
    )

    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()

    for size in SIZES:
        path = args.out / f"icon{size}.png"
        icon.resize((size, size), Image.LANCZOS).save(path)
        print(f"{path} ({size}x{size})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
