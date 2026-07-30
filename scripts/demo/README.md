# Regenerating the README demo

These scripts rebuild `docs/assets/eo-claim-lint-demo.gif` (and the `.mp4` and
poster beside it).

The demo is assembled from **screenshots of a real pull request** that ran the
published action at `a-hikata/eo-claim-lint@v0`. The captions and the two title
cards are the only drawn pixels; every pane showing GitHub is a photograph of
GitHub. Nothing is mocked up, and no output is retyped by hand — if you change
what the linter prints, you have to re-record rather than edit the text.

## Requirements

- Node with `playwright` (`npm i playwright && npx playwright install chromium`)
- Python with `Pillow`
- `ffmpeg` and `gifski` (`brew install ffmpeg gifski`)
- A GitHub account that can see the demo repository

## 1. Record a pull request

Create a throwaway **public** repository — public so the pages render without
any account-specific chrome — containing one workflow:

```yaml
name: EO Claim Lint

on: pull_request

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
      - uses: a-hikata/eo-claim-lint@v0
        with:
          files: claims/*.json
```

Use `@v0`, never `uses: ./` — the point of the demo is the published action.

Open a pull request that adds `claims/forest-loss.json` with `"evidence": []`.
Use synthetic data only: no real place, organisation, or observation. The
document should be shaped so that **EOC301 is the only finding**, otherwise the
demo has to explain warnings it is not about. Check that before pushing:

```sh
python -m eo_claim_lint check claims/forest-loss.json   # expect EOC301, exit 1
```

Wait for the check to go red. Then capture the red frames (see step 2), and only
afterwards push a second commit that adds one evidence entry and changes
nothing else. Wait for green, then capture again.

## 2. Capture the frames

GitHub renders the merge box and the Actions log only for signed-in viewers, so
`capture.js` opens a browser and waits for you to sign in once.

```sh
node capture.js \
  --repo        OWNER/REPO \
  --pr          2 \
  --red-job-url https://github.com/OWNER/REPO/actions/runs/<run>/job/<job> \
  --fix-sha     <sha of the evidence commit> \
  --out         ./frames \
  --profile     ./gh-profile
```

**Delete `./gh-profile` when you are done.** It holds a live GitHub session.

```sh
rm -rf ./gh-profile
```

This leaves five files in `./frames`, named as `storyboard.json` expects:
`pr-red-files.png`, `pr-red-conversation.png`, `job-red-log.png`,
`pr-fix-diff.png`, `pr-green-conversation.png`.

## 3. Compose and encode

`storyboard.json` holds the scene order, the captions, the per-scene duration in
milliseconds, and the crop applied to each screenshot. Crops are fractions of
the source image, so they survive a re-capture at a different page height only
if the layout is unchanged — expect to retune them after a GitHub redesign.

```sh
python3 compose.py storyboard.json ./frames ./build   # writes build/scenes/*.png
./encode.sh ./build                                   # writes build/out/*
```

`encode.sh` produces two GIFs so they can be compared before one is adopted:

| | `demo-A.gif` | `demo-B.gif` |
|---|---|---|
| width | 1200 px | 960 px |
| encoder | gifski, quality 90 | ffmpeg, 64-colour palette |

`demo-A.gif` is the one currently shipped: at this size the difference between
them is a few hundred kilobytes, and the README needs the log text to be
legible more than it needs the smaller file.

Copy the chosen files into place:

```sh
cp build/out/demo-A.gif      ../../docs/assets/eo-claim-lint-demo.gif
cp build/out/demo.mp4        ../../docs/assets/eo-claim-lint-demo.mp4
cp build/out/demo-poster.png ../../docs/assets/eo-claim-lint-demo-poster.png
```

## 4. Delete the recording repository

```sh
gh repo delete OWNER/REPO --yes
gh repo view OWNER/REPO      # expect: could not resolve to a Repository
```
