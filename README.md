# sony-xrb-55x800h

Debloat, privacy-hardening and security research for a **Sony BRAVIA XBR-55X800H**
(MT5893, Android 10, locked bootloader, stock/no-root) over network ADB — fully
documented, fully reversible.

**Read:** [CLEANUP_REPORT.md](CLEANUP_REPORT.md) — current device state, all findings,
the operations runbook, and the complete round-by-round history.
**Kernel work:** [KERNEL_TRIAGE.md](KERNEL_TRIAGE.md) — LinPEAS-style CVE baseline for
the 4.19.75 armv8l kernel.

## Highlights

- 55 packages disabled/removed (Samba ACR, Sony promo/demo, voice stack, hotel-mode
  `b2b.*`, telemetry) — stock Android TV launcher, inputs/HDMI-CEC untouched
- Total microphone lockdown (grants revoked + `appops` deny on all 204 packages;
  hardware has no far-field mic — `builtinmic=0`)
- Root-caused & fixed: a 4-month 10-crashes/sec AirPlay boot loop (persistent-app +
  shared-UID + boot self-heal firmware behavior), and a Paramount+ playback breakage
  caused by DNS-level Conviva blocking
- Privilege-escalation audit: no public root; OTA bridge signature-gated in code;
  dual-OS boundary mapped; artifact cache + kernel evidence preserved locally

## Re-clean after an OTA

```bash
ADB=~/google-glasses/tools/platform-tools/adb
$ADB connect 10.0.0.178:5555
./backups/restore.sh --round1   # see CLEANUP_REPORT.md → Operations for the rest
```

*Private/local analysis artifacts (APKs, kernel modules, dumps) are kept out of this
repo by `.gitignore` and live in a separate untracked directory.*
