#!/usr/bin/env bash
# Encode the scene stills into GIF/MP4. Scenes are static, so the frame
# sequence is built by repeating each still for its scene duration.
set -euo pipefail

BUILD="${1:?usage: encode.sh BUILD_DIR   (BUILD_DIR holds scenes/ from compose.py)}"
SCENES="$BUILD/scenes"
WORK="$BUILD/enc"
OUT="$BUILD/out"
FPS="${FPS:-10}"
WIDTH="${WIDTH:-1200}"

rm -rf "$WORK"; mkdir -p "$WORK" "$OUT"

# Expand scenes into a flat, fixed-rate frame sequence.
python3 - "$SCENES" "$WORK" "$FPS" <<'PY'
import json, pathlib, shutil, sys
scenes, work, fps = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
durations = json.loads((scenes / "durations.json").read_text())
n = 0
for i, ms in enumerate(durations):
    src = scenes / f"scene-{i:02d}.png"
    for _ in range(max(1, round(ms / 1000 * fps))):
        shutil.copyfile(src, work / f"f-{n:05d}.png")
        n += 1
print(f"{n} frames at {fps}fps = {n/fps:.1f}s")
PY

# --- Variant A: readability first (gifski, full width, high quality) ---
gifski --fps "$FPS" --width "$WIDTH" --quality 90 --no-sort \
  -o "$OUT/demo-A.gif" "$WORK"/f-*.png >/dev/null 2>&1

# --- Variant B: size first (narrower, fewer colours, ffmpeg palette) ---
ffmpeg -y -framerate "$FPS" -i "$WORK/f-%05d.png" \
  -vf "scale=960:-2:flags=lanczos,palettegen=max_colors=64:stats_mode=diff" \
  "$WORK/pal.png" -loglevel error
ffmpeg -y -framerate "$FPS" -i "$WORK/f-%05d.png" -i "$WORK/pal.png" \
  -lavfi "scale=960:-2:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -gifflags +transdiff "$OUT/demo-B.gif" -loglevel error

# --- MP4 (H.264, no audio) ---
# H.264 requires even dimensions; trim one row rather than rescale.
ffmpeg -y -framerate "$FPS" -i "$WORK/f-%05d.png" \
  -vf "crop=trunc(iw/2)*2:trunc(ih/2)*2:0:0" \
  -c:v libx264 -pix_fmt yuv420p -profile:v high -crf 20 \
  -movflags +faststart -an "$OUT/demo.mp4" -loglevel error

# --- Poster (the title card) ---
cp "$SCENES/scene-00.png" "$OUT/demo-poster.png"

ls -la "$OUT"
