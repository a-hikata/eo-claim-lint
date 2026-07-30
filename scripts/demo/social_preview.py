"""Draw the repository social preview card.

GitHub shows this image when the repository is shared on social sites and in
chat unfurls. It is 1280x640, the size GitHub recommends.

There is no REST API for the social preview, so the generated file has to be
uploaded by hand: Settings -> General -> Social preview -> Edit -> Upload.

    python3 scripts/demo/social_preview.py docs/assets/social-preview.png
"""

from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
BG = (255, 255, 255)
INK = (13, 17, 23)
MUTED = (87, 96, 106)
ACCENT = (9, 105, 218)
RED = (207, 34, 46)
RED_BG = (255, 235, 233)
BORDER = (208, 215, 222)


def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in paths:
        if pathlib.Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def bold(size: int) -> ImageFont.FreeTypeFont:
    return _font(
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ],
        size,
    )


def regular(size: int) -> ImageFont.FreeTypeFont:
    return _font(
        ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"],
        size,
    )


def mono(size: int) -> ImageFont.FreeTypeFont:
    return _font(
        ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Supplemental/Courier New.ttf"],
        size,
    )


def main() -> None:
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "social-preview.png")
    card = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(card)

    # A single accent rule down the left edge, so the card reads as one object
    # when it is scaled down to a chat thumbnail.
    d.rectangle([0, 0, 12, H], fill=ACCENT)

    left = 72
    d.text((left, 84), "eo-claim-lint", font=bold(76), fill=INK)
    d.text(
        (left, 182),
        "Lint Earth observation claims in CI",
        font=regular(38),
        fill=MUTED,
    )

    # The finding itself: the one line that explains the whole tool.
    panel_top, panel_bottom = 268, 386
    d.rectangle([left, panel_top, W - 72, panel_bottom], fill=RED_BG, outline=BORDER)
    d.text((left + 28, panel_top + 26), "EOC301", font=mono(30), fill=RED)
    d.text(
        (left + 28, panel_top + 68),
        "This claim references no evidence.",
        font=mono(26),
        fill=INK,
    )

    d.text(
        (left, 432),
        "A satellite-derived number should not ship without its",
        font=regular(30),
        fill=INK,
    )
    d.text(
        (left, 472),
        "uncertainty, evidence, and provenance.",
        font=regular(30),
        fill=INK,
    )

    d.text((left, 546), "uses: a-hikata/eo-claim-lint@v0", font=mono(28), fill=ACCENT)

    footer = "GitHub Action  ·  CLI  ·  Python 3.11+  ·  Apache-2.0"
    width = d.textlength(footer, font=regular(22))
    d.text((W - 72 - width, 552), footer, font=regular(22), fill=MUTED)

    out.parent.mkdir(parents=True, exist_ok=True)
    card.save(out)
    print(f"{out} ({card.width}x{card.height})")


if __name__ == "__main__":
    main()
