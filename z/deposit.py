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

from media_variants import audit_deposit, contained, declared_paths, deposit_files, generate, media_path

MAX = 2048
PRIVATE = {"works", "stable_id", "reflects_home", "deposit", "host"}  # organ-internal, never secreted
FAT = Path(__file__).resolve().parent.parent


def main(organ_root: str, address: str) -> None:
    root = Path(organ_root)
    feed = json.loads((root / "_feed" / "current.json").read_text(encoding="utf-8"))
    dest = (FAT / "x" / address).resolve()
    if (FAT / "x").resolve() not in dest.parents:
        raise SystemExit("refused: deposit address escapes the reserve")
    dest.mkdir(parents=True, exist_ok=True)
    kept = set()
    for work in feed["works"]:
        for field, value in work.items():
            if not (isinstance(value, str) and value.startswith("_")):
                continue
            src = (root / value).resolve()
            if root.resolve() not in src.parents:
                raise SystemExit(f"refused: {value} escapes the organ")
            relative = media_path(f"{field}/{src.name.lower()}")
            out = contained(dest, relative)
            if out in kept:
                continue
            kept.add(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
                continue
            with Image.open(src) as im:
                if getattr(im, "n_frames", 1) == 1 and max(im.size) > MAX:
                    im.thumbnail((MAX, MAX), Image.LANCZOS)
                    im.save(out, "WEBP", quality=90, method=6)
                else:
                    shutil.copyfile(src, out)
    public = {k: v for k, v in feed.items() if k not in PRIVATE}
    public["works"] = [
        {k: (f"{k}/{Path(v).name.lower()}" if isinstance(v, str) and v.startswith("_") else v)
         for k, v in w.items()}
        for w in feed["works"]
    ]
    # Variants are derived only after organ paths have become public deposit paths.
    # Never import an organ-private/stale variant declaration as publication authority.
    public.pop("media_variants", None)
    report = generate(dest, public, audit=False)
    kept.add(dest / "feed.json")
    kept.update(contained(dest, path) for path in declared_paths(dest, report["feed"]))
    # Preserve the managed-deposit fail-closed cleanup: unknown/unadmitted files
    # cannot stay releasable. Check every exact target; never delete a directory.
    stale_files = [path for path in deposit_files(dest) if path not in kept]
    for stale in stale_files:
        contained(dest, stale.relative_to(dest).as_posix())
        stale.unlink()
        if stale.exists():
            raise RuntimeError("managed deposit retirement did not complete")
    audit_deposit(dest, report["feed"])
    if report["friction"]:
        print(json.dumps({"animation_friction": report["friction"]}), file=sys.stderr)
    print(f"deposited {len(kept) - 1} media files at x/{address}; {report['variant_count']} sized variants")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
