---
name: fat
description: "Local receptor for fat: the single reserve beneath sss.saarland's skin that holds every organ's admitted media, releases it on demand, fails closed, and signals what it holds."
version: "1.0"
---

# FAT — local receptor

Enter through the shared-root field first; this receptor adds only what is local.

## Identity

`fat` is the organism's subcutaneous reserve. One fat for the whole body, never one per work. Constitution: `INDEX.yaml` (Mobilization · Reserve · Insulation · Signal) and `_cambium.yaml`. The skin (Display, `self-similar-systems/cambium`) draws from it; fat never draws, renders, or interprets.

## Law

- **Source stays home.** Originals live in their own organism (e.g. `/philipp/schattenseiten` on Drive). Fat holds only web-ready derivatives.
- **Only what a feed admits.** `z/deposit.py <organ-root> <address>` reads the organ's own `_feed/current.json` and nothing else. Every path-valued field of an admitted work is deposited at `x/<address>/<field>/<source name>` (shared sources, like a row's cluster, once); images wider than 2048 px are reduced. What the feed stops admitting is removed on the next deposit.
- **The organ's public feed travels with its deposit** as `x/<address>/feed.json`, paths rewritten to the deposit. Nothing private crosses: no Drive paths, no names the organ did not admit.
- **Signal.** `y/signal.py` writes `_feed/current.json`: which organs hold deposits here, where, how much.
- **Mobilization.** GitHub Pages releases `x/` and `_feed/` only (`.github/workflows/mobilize.yml`). Pages has soft limits and answers abuse with throttling, never a bill: fat fails closed. It is never backed by R2 or any metered origin.
- **Video** longer than a loop is not deposited; it is embedded from a platform that carries its own bandwidth.

## Shell

`_stomach` for incoming deposit requests, `_feed` = the signal, `_root` = HOME rings of deposits, `_waste` for retired deposits' records.
