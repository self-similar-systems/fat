"""Insulation: deposit one organ's admitted feed into the reserve.

Only what the organ's own _feed/current.json admits may enter. Every path-valued field of an
admitted work is carried into x/<organ>/<field>/<source name>; images wider than MAX px are reduced.
Deposits the feed no longer admits are removed. Nothing else in the organ is read.

    python z/deposit.py <organ-root> <organ-address>
    e.g. python z/deposit.py "G:/My Drive/x — Continuity/philipp/schattenseiten" philipp/schattenseiten
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

MAX = 2048
PRIVATE = {"works", "stable_id", "reflects_home", "deposit", "host"}  # organ-internal, never secreted
FAT = Path(__file__).resolve().parent.parent


def main(organ_root: str, address: str) -> None:
    root = Path(organ_root)
    feed = json.loads((root / "_feed" / "current.json").read_text(encoding="utf-8"))
    dest = FAT / "x" / address
    kept = set()
    for work in feed["works"]:
        for field, value in work.items():
            if not (isinstance(value, str) and value.startswith("_")):
                continue
            src = (root / value).resolve()
            if root.resolve() not in src.parents:
                raise SystemExit(f"refused: {value} escapes the organ")
            out = dest / field / src.name.lower()
            if out in kept:
                continue
            kept.add(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
                continue
            im = Image.open(src)
            if getattr(im, "n_frames", 1) == 1 and max(im.size) > MAX:
                im.thumbnail((MAX, MAX), Image.LANCZOS)
                im.save(out, "WEBP", quality=90, method=6)
            else:
                shutil.copyfile(src, out)
    for stale in [p for p in dest.rglob("*") if p.is_file() and p not in kept]:
        stale.unlink()
    public = {k: v for k, v in feed.items() if k not in PRIVATE}
    public["works"] = [
        {k: (f"{k}/{Path(v).name.lower()}" if isinstance(v, str) and v.startswith("_") else v)
         for k, v in w.items()}
        for w in feed["works"]
    ]
    (dest / "feed.json").write_text(json.dumps(public, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"deposited {len(kept)} files at x/{address}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
