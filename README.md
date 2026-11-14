# sony-xrb-55x800h

**We set out to debloat a TV. We ended up finding the hotel mode nobody told us
about.**

This is the complete, evidence-backed record of one Sony BRAVIA XBR-55X800H
(MT5893, Android 10, locked bootloader, stock) — taken from factory-spyware-laden
consumer set, through a full debloat and mic lockdown, past a root hunt that
mapped every wall, to a hardware-verified discovery:

> **A USB stick, eight magic bytes, and the TV installs and auto-runs a privileged
> Node.js app at every boot.** Sony's hotel-deployment channel is live on consumer
> sets — the only "signature check" on the package is its file magic (`EAIP…`).
> We proved it end-to-end with Sony's own `bravia-web-control-ui` package, and the
> TV now runs it *by choice*: a web-controllable set with the Sony JSON-RPC API on
> the LAN.

## The arc

| | |
|---|---|
| **R1–R2** (Jul 2026) | 21 packages of spyware/telemetry disabled — Samba ACR, promo, voice stack |
| **R3–R4** | Sony launcher skin removed → stock Android TV home; 33 more bloat packages gone |
| **R5** | Root-caused Paramount+ breakage: DNS ad-blocking vs the Conviva SDK |
| **R6** | Total mic lockdown — all 204 packages denied, hardware-confirmed no far-field mic |
| **R7–R9** | Root hunt: full attack-surface census, artifact cache, kernel CVE triage. Walls held |
| **R10–R11** | **The USB BPK chain, mapped then verified on hardware** — and the web-control stack it installs (kept, toggleable) |

## Read this first

- 🏆 **[docs/FINDINGS.md](docs/FINDINGS.md)** — every finding, with evidence
- 🔁 **[docs/REPRODUCE.md](docs/REPRODUCE.md)** — your TV, the same path: toolchain → artifacts → USB chain, step by step
- 🛠 **[docs/OPERATIONS.md](docs/OPERATIONS.md)** — current state, the web-stack toggle, every revert
- 🧮 [KERNEL_TRIAGE.md](KERNEL_TRIAGE.md) — the 4.19.75 armv8l CVE baseline
- 📜 [docs/history/ROUNDS.md](docs/history/ROUNDS.md) — all twelve rounds, verbatim

## Quick start

```bash
ADB=~/google-glasses/tools/platform-tools/adb
$ADB connect 10.0.0.178:5555

./scripts/webstack-toggle.sh status   # web-control stack: packages, port 80, API probe
./scripts/webstack-toggle.sh off       # close the LAN API, stop node apps
./scripts/webstack-toggle.sh on        # bring it back
```

## Why it's interesting

- **It's all Sony's own code, running Sony's own packages, through Sony's own
  install flow.** The finding is that the consumer firmware enforces nothing
  before the consent dialog — the hotel-mode premise is never checked.
- Every claim is reproducible: the scripts, the exact log signatures, and the
  commands that produced them are in the repo.
- The walls that *held* are documented as carefully as the ones that fell —
  signature-gated OTA, SELinux everywhere, no setuid, a genuinely hardened
  kernel config. This TV is well-built; the BPK channel is a designed feature
  that forgot which market it was in.

*Private analysis artifacts (APKs, kernel modules, dumps) are kept out of this
repo by `.gitignore` and live in a separate untracked directory.*
