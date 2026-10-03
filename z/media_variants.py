"""Derived 512 WebPs from one admitted public deposit, never private source.

    python z/media_variants.py x/<address>/feed.json

The public feed keeps its works/words and declares only relative variant paths.
Animations are accepted only after full frame/timing/loop/background readback.
"""
from __future__ import annotations

from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

from PIL import Image

SIZE = 512
IMAGE_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".ppm", ".pgm"}


class AnimationFriction(ValueError):
    """No smaller animation may be declared when its semantics cannot be proven."""


def media_path(value: str) -> str:
    if not isinstance(value, str) or not value or any(c in value for c in "\\:\x00?#"):
        raise ValueError("media path must be a normalized deposit-relative path")
    parts = value.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") for part in parts):
        raise ValueError("media path has a private/traversing component")
    if parts[0].startswith("_") or parts[0] == "sizes":
        raise ValueError("media source is private or already derived")
    if PurePosixPath(value).suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("unsupported admitted image member")
    return value


def admitted_paths(feed: dict) -> set[str]:
    works = feed.get("works")
    if not isinstance(works, list) or not all(isinstance(work, dict) for work in works):
        raise ValueError("public works must be a list of admitted work objects")
    return {
        media_path(value)
        for work in works for value in work.values()
        if isinstance(value, str) and PurePosixPath(value).suffix.lower() in IMAGE_SUFFIXES
    }


def contained(deposit: Path, relative: str) -> Path:
    root = deposit.resolve()
    lexical = root.joinpath(*PurePosixPath(relative).parts)
    resolved = lexical.resolve()
    if root not in resolved.parents or resolved != lexical:
        raise ValueError("refused path escape or alias in managed deposit")
    return resolved


def variant_path(source: str) -> str:
    source = media_path(source)
    return f"sizes/{SIZE}/{source}" + ("" if source.lower().endswith(".webp") else ".webp")


def declared_paths(deposit: Path, feed: dict) -> set[str]:
    sources = admitted_paths(feed)
    variants = feed.get("media_variants", {})
    if not isinstance(variants, dict):
        raise ValueError("variant declaration must be an object")
    paths = set()
    for size, mapping in variants.items():
        if not isinstance(size, str) or not size.isdecimal() or not isinstance(mapping, dict):
            raise ValueError("unsupported variant declaration")
        for source, target in mapping.items():
            if source not in sources or not isinstance(target, str):
                raise ValueError("variant must be attached to a currently admitted image")
            expected = f"sizes/{size}/{media_path(source)}" + ("" if source.lower().endswith(".webp") else ".webp")
            if target != expected:
                raise ValueError("variant path is outside its exact sized ownership")
            contained(deposit, target)
            paths.add(target)
    return paths


def deposit_files(deposit: Path):
    """Inspect names only, rejecting aliases before traversing any directory."""
    root = deposit.resolve()
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            contained(root, relative)
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                yield path


def audit_deposit(deposit: Path, feed: dict) -> None:
    allowed = admitted_paths(feed) | declared_paths(deposit, feed) | {"feed.json"}
    for path in deposit_files(deposit):
        if path.relative_to(deposit.resolve()).as_posix() not in allowed:
            raise ValueError("unexpected unadmitted file in managed public deposit")


def read_feed(path: Path) -> dict:
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def write_feed(path: Path, feed: dict) -> None:
    old = path.read_bytes() if path.exists() else b""
    newline = "\r\n" if b"\r\n" in old or (not old and sys.platform == "win32") else "\n"
    prefix = b"\xef\xbb\xbf" if old.startswith(b"\xef\xbb\xbf") else b""
    raw = prefix + json.dumps(feed, ensure_ascii=False, indent=1).replace("\n", newline).encode("utf-8")
    path.write_bytes(raw)
    if path.read_bytes() != raw or read_feed(path) != feed:
        raise RuntimeError("public feed did not independently round-trip")


def animation_info(image: Image.Image) -> dict:
    if image.format != "WEBP":
        raise AnimationFriction("animated non-WebP background/disposal semantics are not supported")
    loop, background = image.info.get("loop"), image.info.get("background")
    if type(loop) is not int or not isinstance(background, tuple) or len(background) != 4:
        raise AnimationFriction("animation loop/background is not explicit")
    durations = []
    for index in range(image.n_frames):
        image.seek(index)
        image.load()
        duration = image.info.get("duration")
        if type(duration) is not int or duration < 0:
            raise AnimationFriction("animation frame duration is not explicit")
        durations.append(duration)
    return {"frames": image.n_frames, "durations": durations, "loop": loop, "background": background}


def encode_variant(source: Path) -> tuple[bytes | None, dict]:
    with Image.open(source) as image:
        original_size = image.size
        info = {"source_size": list(original_size), "source_frames": getattr(image, "n_frames", 1)}
        if max(original_size) <= SIZE:
            return None, {**info, "skipped": "already within 512; no upscaling"}
        output = BytesIO()
        if info["source_frames"] == 1:
            frame = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
            frame.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
            frame.save(output, "WEBP", quality=90, method=6)
            expected_size = frame.size
            frame.close()
            expected = None
        else:
            expected = animation_info(image)
            frames = []
            try:
                for index in range(image.n_frames):
                    image.seek(index)
                    frame = image.convert("RGBA")
                    frame.thumbnail((SIZE, SIZE), Image.Resampling.LANCZOS)
                    frames.append(frame)
                expected_size = frames[0].size
                frames[0].save(output, "WEBP", save_all=True, append_images=frames[1:],
                               duration=expected["durations"], loop=expected["loop"], background=expected["background"],
                               quality=90, method=6, minimize_size=False, kmin=1, kmax=2)
            except (OSError, ValueError) as error:
                raise AnimationFriction("actual animation encoding unavailable: " + str(error)) from error
            finally:
                for frame in frames:
                    frame.close()
        data = output.getvalue()
        with Image.open(BytesIO(data)) as decoded:
            if decoded.size != expected_size or max(decoded.size) > SIZE:
                raise ValueError("variant dimensions did not round-trip")
            if expected is not None:
                actual = animation_info(decoded)
                if actual != expected:
                    raise AnimationFriction("encoded animation changed frame sequence/timing/loop/background")
                info.update({"frames": actual["frames"], "durations": actual["durations"],
                             "loop": actual["loop"], "background": list(actual["background"])})
            elif getattr(decoded, "n_frames", 1) != 1:
                raise ValueError("static image became animated")
        return data, {**info, "size": list(expected_size), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def generate(deposit: Path, public: dict | None = None, *, audit: bool = True, progress=None) -> dict:
    deposit = deposit.resolve()
    feed_path = deposit / "feed.json"
    previous = read_feed(feed_path) if feed_path.exists() else {"works": []}
    public = copy.deepcopy(previous if public is None else public)
    sources = admitted_paths(public)
    previous_declared = declared_paths(deposit, previous)
    if audit:
        audit_deposit(deposit, previous)
    # Validate all admitted sources and exact target scopes before opening any media.
    targets = {source: contained(deposit, variant_path(source)) for source in sorted(sources)}
    inputs = {source: contained(deposit, source) for source in sorted(sources)}
    if not all(path.is_file() for path in inputs.values()):
        raise ValueError("admitted public media is missing")
    plans, mapping, entries, friction = {}, {}, [], []
    def encode(item):
        source, path = item
        try:
            data, info = encode_variant(path)
            return source, data, info, None
        except AnimationFriction as error:
            return source, None, None, str(error)
    # Independent media encodes are bounded to four workers; ordered results and
    # all filesystem writes stay deterministic and serial after verification.
    with ThreadPoolExecutor(max_workers=min(4, len(inputs) or 1)) as workers:
        for source, data, info, error in workers.map(encode, inputs.items()):
            if error is not None:
                friction.append({"source": source, "reason": error})
                if progress:
                    progress(source, "friction")
                continue
            entries.append({"source": source, **info})
            if data is not None:
                target = variant_path(source)
                mapping[source] = target
                plans[target] = data
            if progress:
                progress(source, "verified")
    variants = copy.deepcopy(public.get("media_variants", {}))
    if not isinstance(variants, dict):
        raise ValueError("variant metadata must be an object")
    variants[str(SIZE)] = mapping
    public["media_variants"] = variants
    declared_paths(deposit, public)
    stale = sorted(path for path in previous_declared - set(mapping.values()) if path.startswith(f"sizes/{SIZE}/"))
    # Every retirement was previously attached to admitted works and matches its
    # exact derived path. Never glob/delete arbitrary files in the sizes tree.
    retire = [contained(deposit, path) for path in stale]
    for relative, data in plans.items():
        target = contained(deposit, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = contained(deposit, relative)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise RuntimeError("derived bytes failed independent readback")
    for target in retire:
        if target.exists():
            contained(deposit, target.relative_to(deposit).as_posix())
            target.unlink()
            if target.exists():
                raise RuntimeError("derived retirement did not complete")
    write_feed(feed_path, public)
    if audit:
        audit_deposit(deposit, public)
    return {"feed": public, "media_variants": mapping, "entries": entries, "friction": friction,
            "retired": stale, "variant_count": len(mapping), "variant_bytes": sum(len(data) for data in plans.values())}


def main(feed_path: str) -> None:
    feed = Path(feed_path).resolve()
    reserve = Path(__file__).resolve().parent.parent / "x"
    if reserve.resolve() not in feed.parents or feed.name != "feed.json":
        raise SystemExit("refused: generator accepts only x/<address>/feed.json")
    report = generate(feed.parent, progress=lambda source, status: print(f"{status}: {source}", file=sys.stderr, flush=True))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
