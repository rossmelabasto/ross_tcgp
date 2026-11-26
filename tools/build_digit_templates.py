"""Build ``src/ross_tcgp/digits.npz`` from screenshots of the "My Cards" grid.

Step 1, group the digit shapes found in the badges and draw them:

    python tools/build_digit_templates.py collect PAGES_DIR clusters.npz clusters.png

Look at clusters.png: every numbered tile is one distinct shape.

Step 2, say which digit each cluster is (cluster:digit pairs) and save:

    python tools/build_digit_templates.py label clusters.npz "0:1,1:2,2:3,..."

Only needed when the game changes its font, or to add a digit that was missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ross_tcgp import counts, grid

OUT = Path(__file__).resolve().parents[1] / "src" / "ross_tcgp" / "digits.npz"


def collect(pages: Path, out_npz: Path, out_png: Path, threshold: float = 0.10) -> None:
    centres: list[np.ndarray] = []
    members: list[list[np.ndarray]] = []
    for path in sorted(pages.glob("*.png")):
        img = Image.open(path).convert("RGB")
        for slot in grid.find_slots(img):
            mask = counts.digit_mask(img, slot)
            if mask is None:
                continue
            for g in counts.glyphs(mask):
                dists = [float(np.abs(g - c).mean()) for c in centres]
                if dists and min(dists) < threshold:
                    i = int(np.argmin(dists))
                    members[i].append(g)
                    centres[i] = np.mean(members[i], axis=0)
                else:
                    centres.append(g)
                    members.append([g])
    order = np.argsort([-len(m) for m in members])
    centres = [centres[i] for i in order]
    sizes = [len(members[i]) for i in order]
    np.savez(out_npz, *centres)

    scale = 6
    gw, gh = counts.GLYPH[0] * scale, counts.GLYPH[1] * scale
    sheet = Image.new("L", ((gw + 10) * len(centres), gh + 30), 255)
    draw = ImageDraw.Draw(sheet)
    for i, c in enumerate(centres):
        tile = Image.fromarray((255 - c * 255).astype(np.uint8)).resize((gw, gh), Image.Resampling.NEAREST)
        sheet.paste(tile, (i * (gw + 10), 0))
        draw.text((i * (gw + 10), gh + 5), f"{i} ({sizes[i]})", fill=0)
    sheet.save(out_png)
    print(f"{len(centres)} clusters, sizes {sizes}")


def label(clusters: Path, mapping: str) -> None:
    data = np.load(clusters)
    arrays = [data[f"arr_{i}"] for i in range(len(data.files))]
    templates = {}
    for pair in mapping.split(","):
        idx, digit = pair.split(":")
        digit = digit.strip()
        # Several shapes per digit are fine: keys "3", "3_b", "3_c"…
        key = digit
        suffix = iter("bcdefgh")
        while key in templates:
            key = f"{digit}_{next(suffix)}"
        templates[key] = arrays[int(idx)]
    np.savez(OUT, **templates)
    print(f"saved digits {sorted(templates)} to {OUT}")


if __name__ == "__main__":
    if sys.argv[1] == "collect":
        collect(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    elif sys.argv[1] == "label":
        label(Path(sys.argv[2]), sys.argv[3])
    else:
        print(__doc__)
