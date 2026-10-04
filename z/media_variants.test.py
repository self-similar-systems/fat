"""Behavioral tests of public variants and the native deposition boundary."""
from io import StringIO
from contextlib import redirect_stdout
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image
import media_variants as V
import deposit


class PublicVariants(unittest.TestCase):
    def test_tier64_preserves512_and_replays_revision(self):
        self.image("still/one.webp", (1024, 1024))
        self.feed([{"still":"still/one.webp"}])
        high=V.generate(self.d)
        high_path=self.d/high["media_variants"]["still/one.webp"]
        before=high_path.read_bytes()
        low=V.generate(self.d,size=64)
        with Image.open(self.d/low["media_variants"]["still/one.webp"]) as image:
            self.assertEqual(image.size,(64,64))
        self.assertEqual(high_path.read_bytes(),before)
        self.assertEqual(low["feed"]["media_variants"]["512"],high["media_variants"])
        self.assertEqual(V.generate(self.d,size=64)["feed"]["media_revisions"]["64"],low["feed"]["media_revisions"]["64"])
        with self.assertRaises(ValueError): V.generate(self.d,size=128)

    def test_tier64_animation_semantics(self):
        original=self.animation();self.feed([{"animation":"animation/sequence.webp"}])
        low=V.generate(self.d,size=64)
        self.assertEqual(low["friction"],[])
        with Image.open(original) as image: expected=V.animation_info(image)
        with Image.open(self.d/low["media_variants"]["animation/sequence.webp"]) as image:
            self.assertEqual(V.animation_info(image),expected);self.assertLessEqual(max(image.size),64)

    def setUp(self):
        self.scratch = Path(__file__).resolve().parents[2]
        self.temp = tempfile.TemporaryDirectory(prefix="fat-variants-test-", dir=self.scratch)
        self.home = Path(self.temp.name).resolve()
        self.addCleanup(self.cleanup)
        self.d = self.home / "public"
        self.d.mkdir()

    def cleanup(self):
        if self.scratch.resolve() not in self.home.parents:
            raise ValueError("test cleanup escaped the named scratch workspace")
        self.temp.cleanup()

    def image(self, relative, size=(960, 640), color=(20, 70, 150, 180)):
        target = self.d / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, color).save(target, "WEBP", lossless=True)
        return target

    def feed(self, works):
        value = {"organ": "fixture", "words": ["source words"], "works": works}
        V.write_feed(self.d / "feed.json", value)
        return value

    def animation(self):
        target = self.d / "animation/sequence.webp"
        target.parent.mkdir(parents=True, exist_ok=True)
        frames = [Image.new("RGBA", (900, 600), color) for color in [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]]
        frames[0].save(target, "WEBP", save_all=True, append_images=frames[1:], duration=[40, 70, 110], loop=3, background=(7, 8, 9, 0), lossless=True)
        for frame in frames:
            frame.close()
        return target

    def test_dimensions_shared_admission_no_upscale_and_repeat(self):
        large = self.image("still/large.webp")
        small = self.image("still/small.webp", (30, 20))
        public = self.feed([{"id": "a", "still": "still/large.webp", "cluster": "still/large.webp"}, {"id": "b", "still": "still/large.webp", "small": "still/small.webp"}])
        originals = {p: p.read_bytes() for p in (large, small)}
        with mock.patch.object(V, "encode_variant", wraps=V.encode_variant) as encode:
            result = V.generate(self.d)
            self.assertEqual(encode.call_count, 2, "shared source processed once")
        self.assertEqual(result["variant_count"], 1)
        self.assertEqual(result["media_variants"], {"still/large.webp": "sizes/512/still/large.webp"})
        variant = self.d / result["media_variants"]["still/large.webp"]
        with Image.open(variant) as image:
            self.assertEqual(image.size, (512, 341))
            self.assertEqual(getattr(image, "n_frames", 1), 1)
        before = variant.read_bytes()
        repeated = V.generate(self.d)
        self.assertEqual(repeated["media_variants"], result["media_variants"])
        self.assertEqual(variant.read_bytes(), before, "deterministic encode regeneration")
        self.assertEqual(repeated["feed"]["works"], public["works"])
        self.assertEqual(repeated["feed"]["words"], public["words"])
        self.assertTrue(all(p.read_bytes() == raw for p, raw in originals.items()))

    def test_actual_animation_sequence_duration_loop_background_and_repeat(self):
        original = self.animation()
        self.feed([{"animation": "animation/sequence.webp"}])
        source_bytes = original.read_bytes()
        with Image.open(original) as image:
            expected = V.animation_info(image)
        result = V.generate(self.d)
        self.assertEqual(result["friction"], [], "actual encoder/decoder, no feature flag assumption")
        variant = self.d / result["media_variants"]["animation/sequence.webp"]
        with Image.open(variant) as image:
            self.assertEqual(image.size, (512, 341))
            self.assertEqual(V.animation_info(image), expected)
            for index, channel in enumerate([0, 1, 2]):
                image.seek(index)
                pixel = image.convert("RGBA").getpixel((256, 170))
                self.assertGreater(pixel[channel], 220, "sequence content/order survives resize")
        before = variant.read_bytes()
        self.assertEqual(V.generate(self.d)["friction"], [])
        self.assertEqual(variant.read_bytes(), before)
        self.assertEqual(original.read_bytes(), source_bytes)

    def test_animation_encoder_failure_is_friction_never_freeze(self):
        original = self.animation()
        self.feed([{"animation": "animation/sequence.webp"}])
        result = V.generate(self.d)
        variant = self.d / result["media_variants"]["animation/sequence.webp"]
        with mock.patch.object(Image.Image, "save", side_effect=OSError("animation encoder absent")):
            failed = V.generate(self.d)
        self.assertEqual(len(failed["friction"]), 1)
        self.assertEqual(failed["media_variants"], {})
        self.assertFalse(variant.exists(), "unproven derivative is not left undeclared/releasable")
        with Image.open(original) as image:
            self.assertEqual(image.n_frames, 3, "larger original is not frozen/truncated")

    def test_exact_owned_retirement(self):
        removed = self.image("still/removed.webp")
        small = self.image("still/retained.webp", (32, 16))
        self.feed([{"still": "still/removed.webp"}, {"still": "still/retained.webp"}])
        first = V.generate(self.d)
        variant = self.d / first["media_variants"]["still/removed.webp"]
        removed.unlink()  # fixture models the depositing owner's original retirement
        updated = {"organ": "fixture", "works": [{"still": "still/retained.webp"}]}
        result = V.generate(self.d, updated)
        self.assertEqual(result["retired"], ["sizes/512/still/removed.webp"])
        self.assertFalse(variant.exists())
        self.assertTrue(small.exists())

    def test_path_private_and_unadmitted_stray_boundaries(self):
        self.image("still/one.webp")
        self.feed([{"still": "still/one.webp"}])
        stray = self.d / "unadmitted.webp"
        stray.write_bytes(b"private/unadmitted bytes must not be read")
        with mock.patch.object(V.Image, "open") as opening:
            with self.assertRaisesRegex(ValueError, "unadmitted"):
                V.generate(self.d)
            opening.assert_not_called()
        self.assertEqual(stray.read_bytes(), b"private/unadmitted bytes must not be read")
        stray.unlink()
        for invalid in ["../private.webp", "_private/secret.webp", "C:/private.webp", "still/../private.webp", "https://private.invalid/secret.webp"]:
            with mock.patch.object(V.Image, "open") as opening:
                with self.assertRaises(ValueError):
                    V.generate(self.d, {"works": [{"still": invalid}]})
                opening.assert_not_called()
        original_feed = V.read_feed(self.d / "feed.json")
        original_feed["media_variants"] = {"512": {"still/one.webp": "../private.webp"}}
        V.write_feed(self.d / "feed.json", original_feed)
        with self.assertRaises(ValueError):
            V.generate(self.d)

    def test_native_deposit_keeps_variants_and_cleans_unadmitted_stray(self):
        fat = self.home / "fat"
        (fat / "x").mkdir(parents=True)
        organ = self.home / "organ"
        (organ / "_feed").mkdir(parents=True)
        (organ / "_media").mkdir()
        source = organ / "_media/shared.webp"
        Image.new("RGB", (960, 640), (12, 80, 200)).save(source, "WEBP", lossless=True)
        unadmitted_private = organ / "_media/private.webp"
        unadmitted_private.write_bytes(b"not admitted and never opened")
        feed = {"organ": "fixture", "host": "G:/private source", "words": ["unchanged"], "works": [{"still": "_media/shared.webp"}, {"still": "_media/shared.webp"}]}
        (organ / "_feed/current.json").write_text(json.dumps(feed), encoding="utf-8")
        dest = fat / "x/test"
        with mock.patch.object(deposit, "FAT", fat), redirect_stdout(StringIO()):
            deposit.main(str(organ), "test")
            public = V.read_feed(dest / "feed.json")
            self.assertNotIn("host", public)
            self.assertEqual(public["works"], [{"still": "still/shared.webp"}] * 2)
            self.assertEqual(public["media_variants"]["512"], {"still/shared.webp": "sizes/512/still/shared.webp"})
            variant = dest / "sizes/512/still/shared.webp"
            original_hash = hashlib.sha256((dest / "still/shared.webp").read_bytes()).hexdigest()
            variant_hash = hashlib.sha256(variant.read_bytes()).hexdigest()
            stray = dest / "unadmitted.txt"
            stray.write_bytes(b"must not remain publicly releasable")
            deposit.main(str(organ), "test")
            self.assertFalse(stray.exists())
            self.assertTrue(variant.exists(), "next deposit preserves current declared variant")
            self.assertEqual(hashlib.sha256(variant.read_bytes()).hexdigest(), variant_hash)
            self.assertEqual(hashlib.sha256((dest / "still/shared.webp").read_bytes()).hexdigest(), original_hash)
            self.assertEqual(V.read_feed(dest / "feed.json")["words"], ["unchanged"])
            V.audit_deposit(dest, V.read_feed(dest / "feed.json"))
            with self.assertRaises(SystemExit):
                deposit.main(str(organ), "../../escape")


if __name__ == "__main__":
    unittest.main()
