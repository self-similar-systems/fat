"""Signal: tell the organism what the reserve holds.

Walks x/ for deposited organs (a folder holding feed.json) and writes _feed/current.json:
which organs have deposits, where, and how much. Never lists anything that is not deposited.
"""
import json
from pathlib import Path

FAT = Path(__file__).resolve().parent.parent


def main() -> None:
    organs = []
    for feed in sorted((FAT / "x").rglob("feed.json")):
        home = feed.parent
        files = [p for p in home.rglob("*") if p.is_file() and p.name != "feed.json"]
        organs.append({
            "organ": home.relative_to(FAT / "x").as_posix(),
            "feed": feed.relative_to(FAT).as_posix(),
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
        })
    out = {"organism": "fat", "holds": organs}
    (FAT / "_feed").mkdir(exist_ok=True)
    (FAT / "_feed" / "current.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
