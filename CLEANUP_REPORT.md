# Sony BRAVIA 4K UR3 (XBR-55X800H) Cleanup Report

**Date:** 2026-07-23
**Device:** Sony BRAVIA 4K UR3 / Android 10 / build QTG3.200305.006.S97 / user release-keys (stock, not rooted)
**Address:** 10.0.0.178 (wireless ADB on port 5555)
**Scope chosen:** Moderate (adware/tracking/ACR + Sony promo/demo) + telemetry/diagnostics; keep all streaming apps.

## What was removed (per-user, reversible)

Method: `pm uninstall -k --user 0 <pkg>` (APK retained; restorable via `pm install-existing` or factory reset).

| Package | Category |
|---|---|
| tv.samba.ssm | Samba TV Automatic Content Recognition (advertiser software; fingerprints viewing) |
| com.sony.dtv.promos | Sony promotional content (was already disabled) |
| com.sony.dtv.demosupport | Retail demo support |
| com.sony.dtv.demosystemsupport | Retail demo system support |
| com.sony.dtv.multiscreendemo | Multiscreen demo |
| com.sony.dtv.sonybugreportsys | Sony bug/diagnostic report uploader |
| com.google.android.tv.bugreportsender | Google TV crash report sender |
| com.google.android.feedback | Google feedback/telemetry |
| com.sony.dtv.sonyloglevelsettingsys | Sony log-level settings (diagnostics) |

Package count: 213 -> 204 (installed for user 0). Core packages verified intact: launcher, Google Play Services, SystemUI, TV input/tuner, network stack.

## Ad-domain blocking (Private DNS, no root)

Hosts file cannot be edited without root (read-only /system), so system-wide DNS-over-TLS filtering was configured instead:

```
settings put global private_dns_mode hostname
settings put global private_dns_specifier dns.adguard-dns.com
```

Verified from the TV shell:
- google.com -> resolves (normal traffic works)
- doubleclick.net -> 127.0.0.1 (blocked)
- www.google-analytics.com -> 127.0.0.1 (blocked)

Note: DNS-level blocking covers ad/tracker domains resolved via DNS. A few services with hardcoded IPs are not caught by DNS alone; a router-level Pi-hole/AdGuard Home would complement this if desired.

## How to revert

- Full revert: `./backups/restore.sh` (re-installs the 9 packages and resets Private DNS).
- DNS only: `./backups/restore.sh --dns-only`
- Packages only: `./backups/restore.sh --pkgs-only`
- Factory reset also restores everything.

## To switch ad-block provider (optional)

```
adb -s 10.0.0.178:5555 shell settings put global private_dns_specifier <DoT hostname>
```
Alternatives: NextDNS (custom blocklists, `dns.nextdns.io`), ControlD, Quad9 (`dns.quad9.net`).

## Notes / persistence

- Private DNS is stored in `Settings.Global` and survives reboots and standby.
- If Sony's OTA update or a reset re-enables any removed package, re-run `restore.sh --pkgs-only` is not needed (removal is per-user; OTA may restore system packages -> just re-run the removal loop).
- Original state snapshot saved in `backups/snapshot-20260723-160017/` (package lists, props, DNS settings).

---

# Round 2 (2026-07-23): voice disable + aggressive perf/privacy tuning

Ad-blocking unchanged (AdGuard Private DNS kept). No reboot performed by the operator; ADB disabled at the end.

## Packages disabled for user 0 (via `pm disable-user --user 0`; reversible with `pm enable`)

Voice / Assistant (mic privacy):
- com.google.android.tv.assistant
- com.sony.dtv.assistantadapter
- com.sony.dtv.voicerecognitionconfirmation

Recommendations / sourcing (privacy + perf; home screen rec rows now empty, apps row intact):
- com.google.android.katniss
- com.google.android.tvrecommendations

Unused background services (perf; Cast-to-TV, DLNA, Vewd browser, Play Games, Play Movies stop working):
- com.google.android.apps.mediashell (Cast receiver)
- com.sonyericsson.dlna, com.sony.huey.dlna.module, com.sony.huey.dlna.renderersettings (DLNA)
- com.vewd.core.service (Vewd browser)
- com.google.android.play.games, com.google.android.videos (Play Games, Play Movies)

## System tuning
- Animation scales -> 0 (window/transition/animator); revert: set back to 1.0.
- Cache trimmed: /data free 1.75 GB -> 2.93 GB (usage 73% -> 55%).
- Force-stopped idle streaming apps (none were running at the time).

## Ads personalization (UI step, user to tap on TV)
- Launched `com.google.android.gms/.adid.settings.AdsSettingsActivity`.
- Tap "Opt out of Ads Personalization" + "Reset advertising ID". (Menu path: Settings -> Device Preferences -> Google -> Ads.)

## How to revert round 2
- `./backups/restore.sh --round2` re-enables all 12 packages and resets animations to 1.0.
- Or per-package: `adb -s 10.0.0.178:5555 shell pm enable <pkg>`.
- Full revert (both rounds + DNS): `./backups/restore.sh`.

## ADB disabled on exit
- Final command: `settings put global adb_enabled 0` (network port 5555 closes).
- To re-clean later: re-enable "Network ADB debugging" in Developer Options on the TV, then reconnect.
- Round-2 pre-state snapshot saved in `backups/round2-prestate.txt`.
