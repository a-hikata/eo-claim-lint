"""Compose the eo-claim-lint demo GIF from real GitHub screenshots.

Every panel is a crop of an actual screenshot of the demo pull request; the
only synthetic pixels are the caption strip and the title/end cards.
"""

from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 675
BG = (255, 255, 255)
INK = (13, 17, 23)
MUTED = (87, 96, 106)
ACCENT = (9, 105, 218)
RED = (207, 34, 46)
GREEN = (26, 127, 55)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    cands = (
        ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"]
        if bold
        else ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]
    )
    for cand in cands:
        if pathlib.Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                continue
    return ImageFont.load_default()


def mono(size: int) -> ImageFont.FreeTypeFont:
    for cand in (
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ):
        if pathlib.Path(cand).exists():
            return ImageFont.truetype(cand, size)
    return font(size)


def fit(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scale a crop to fill the panel box. Sources are 2x DPI, so modest
    upscaling of a small crop still resolves text cleanly."""
    scale = min(box_w / img.width, box_h / img.height)
    return img.resize(
        (max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS
    )


def panel_scene(shot: Image.Image, caption: str, sub: str | None = None, accent=INK) -> Image.Image:
    """A captioned screenshot panel."""
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)

    top = 22
    d.text((48, top), caption, font=font(34, bold=True), fill=accent)
    y = top + 46
    if sub:
        d.text((48, y), sub, font=font(21), fill=MUTED)
        y += 32

    area_top = y + 14
    box_w, box_h = W - 96, H - area_top - 30
    im = fit(shot, box_w, box_h)
    x = (W - im.width) // 2
    # Centre short strips in the remaining space rather than pinning them high.
    top = area_top + max(0, (box_h - im.height) // 2)
    canvas.paste(im, (x, top))
    d.rectangle([x - 1, top - 1, x + im.width, top + im.height], outline=(208, 215, 222))
    return canvas


def title_card(line1: str, line2: str | None = None, kicker: str | None = None) -> Image.Image:
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    cy = H // 2
    if kicker:
        w = d.textlength(kicker, font=font(24, bold=True))
        d.text(((W - w) / 2, cy - 130), kicker, font=font(24, bold=True), fill=ACCENT)
    f1 = font(54, bold=True)
    w1 = d.textlength(line1, font=f1)
    d.text(((W - w1) / 2, cy - 60), line1, font=f1, fill=INK)
    if line2:
        f2 = mono(30)
        w2 = d.textlength(line2, font=f2)
        d.text(((W - w2) / 2, cy + 30), line2, font=f2, fill=ACCENT)
    return canvas


def crop(img: Image.Image, rect) -> Image.Image:
    """rect is (left, top, right, bottom) in fractions of the source size."""
    left, top, right, bottom = rect
    return img.crop(
        (
            int(left * img.width),
            int(top * img.height),
            int(right * img.width),
            int(bottom * img.height),
        )
    )


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("usage: compose.py STORYBOARD.json FRAMES_DIR OUT_DIR")
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    frames_dir = pathlib.Path(sys.argv[2])
    # encode.sh is handed the build directory and looks for scenes/ inside it.
    outdir = pathlib.Path(sys.argv[3]) / "scenes"
    outdir.mkdir(parents=True, exist_ok=True)

    frames: list[Image.Image] = []
    durations: list[int] = []

    for scene in spec["scenes"]:
        if scene["kind"] == "title":
            img = title_card(scene["line1"], scene.get("line2"), scene.get("kicker"))
        else:
            src = Image.open(frames_dir / scene["src"]).convert("RGB")
            if "crop" in scene:
                src = crop(src, scene["crop"])
            accent = {"red": RED, "green": GREEN, "ink": INK}[scene.get("accent", "ink")]
            img = panel_scene(src, scene["caption"], scene.get("sub"), accent)
        frames.append(img)
        durations.append(int(scene["ms"]))

    for i, f in enumerate(frames):
        f.save(outdir / f"scene-{i:02d}.png")

    total = sum(durations) / 1000
    print(f"{len(frames)} scenes, {total:.1f}s")
    (outdir / "durations.json").write_text(json.dumps(durations))


if __name__ == "__main__":
    main()
