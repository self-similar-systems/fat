---
name: fat
description: "Local receptor for fat: the single reserve beneath sss.saarland's skin that holds every organ's admitted media, releases it on demand, fails closed, and signals what it holds."
version: "1.1"
---

# FAT — local receptor

Enter through the shared-root field first; this receptor adds only what is local.

## Identity

`fat` is the organism's subcutaneous reserve. One fat for the whole body, never one per work. Constitution: `INDEX.yaml` (Mobilization · Reserve · Insulation · Signal) and `_cambium.yaml`. The skin (Display, `self-similar-systems/cambium`) draws from it; fat never draws, renders, or interprets.

## Law

- **Source stays home.** Originals live in their own organism (e.g. `/philipp/schattenseiten` on Drive). Fat holds only web-ready derivatives.
- **Only what a feed admits.** `z/deposit.py <organ-root> <address>` reads the organ's own `_feed/current.json` and nothing else. Every path-valued field of an admitted work is deposited at `x/<address>/<field>/<source name>` (shared sources, like a row's cluster, once); images wider than 2048 px are reduced. What the feed stops admitting is removed on the next deposit.
- **The organ's public feed travels with its deposit** as `x/<address>/feed.json`, paths rewritten to the deposit. Nothing private crosses: no Drive paths, no names the organ did not admit.
- **Sized media stays in Fat.** `z/media_variants.py x/<address>/feed.json` generates 512-pixel WebPs solely from the deposit's currently admitted path-valued images. The same helper runs after `z/deposit.py` rewrites the public feed. Shared source paths are processed once; aspect ratio is preserved, smaller images are not upscaled, and static derivatives use Pillow/LANCZOS, WebP quality 90, method 6. The public feed declares `media_variants: {"512": {"<original path>": "sizes/512/<member>"}}`; original works, words and larger public media remain source-owned and unchanged. Animated WebPs keep every frame, duration, loop and background only after actual encode/decode readback proves equality; unsupported or changed animation semantics are explicit friction, never a frozen/truncated surrogate. Paths are normalized and resolved inside the deposit; the helper retires only exact previously declared, admitted-source outputs in its `sizes/512` scope. Standalone generation rejects unexpected public files, while deposition keeps admitted originals, declared variants and the feed, removes exact contained stale files and audits the final managed deposit. No unadmitted stray remains publicly releasable.
- **Signal.** `y/signal.py` writes `_feed/current.json`: which organs hold deposits here, where, how much.
- **Mobilization.** GitHub Pages releases `x/` and `_feed/` only (`.github/workflows/mobilize.yml`). Pages has soft limits and answers abuse with throttling, never a bill: fat fails closed. It is never backed by R2 or any metered origin.
- **Video** longer than a loop is not deposited; it is embedded from a platform that carries its own bandwidth.

## Shell

`_stomach` for incoming deposit requests, `_feed` = the signal, `_root` = HOME rings of deposits, `_waste` for retired deposits' records.

Version 1.1 sized-media correction (2026-10-03): admitted images now have source-faithful 512 variants in the same unmetered reserve, with relative public declarations, full animation-semantic witnesses, exact derived retirement and managed-deposit admission checks. Release remains the existing GitHub Pages workflow; HOME follows the final organism witness.
