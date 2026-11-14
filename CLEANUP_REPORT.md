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

---

# Round 3 (2026-11-10): remove Sony launcher skin, de-Sony home + services

**Operator goals:** Sony launcher gone, stock Android TV home instead; sponsored content killed;
no live TV used; HDMI input switching must keep working.

## Device architecture findings (XBR-55X800H / BRAVIA_UR3_UC / Android 10)

- `com.sony.dtv.tvx` is **not** the home app — it registers no `android.intent.category.HOME`
  filter at all. Home = `com.google.android.tvlauncher` (stock, priority 2, default).
- The "Sony launcher" look = `com.sony.dtv.tvlaunchercustomizer` (v5.0.10) + RRO overlay
  `com.sony.dtv.tvlaunchercustomizer.overlay.apporder` (targets the customizer, not the launcher)
  + `com.sony.dtv.sonyselect` (Sony SELECT sponsored-content feed).
- Live TV / EPG / input stack lives in separate `com.sony.dtv.tvinput.*` packages
  (tuner, external/HDMI, hardwaremanager, provider). `tvx` only hosts TV-player UI
  (tune receivers, EPG program data, input-setup receiver).

## Round 3 changes (disable-user --user 0; reversible with `pm enable`)

- com.sony.dtv.tvlaunchercustomizer (Sony home skin, hosts SonySelectProvider)
- com.sony.dtv.tvlaunchercustomizer.overlay.apporder
- com.sony.dtv.sonyselect
- com.sony.dtv.tvx
- com.sony.dtv.homekit
- Launcher state reset: `pm clear com.google.android.tvlauncher` (clears stale "Shop"/"Apps"
  tiles left behind by the removed Sony home; app row rebuilds from installed apps;
  launcher shows an account picker once after the clear — pick an account or press back).

## The AirPlay crash loop (root cause chain — documented so nobody repeats it)

1. July round 2 disabled `com.vewd.core.service` (Vewd browser engine).
2. `com.sony.dtv.airplayapp` has `FLAG_PERSISTENT` and binds Vewd's `BrowserServiceImpl`
   inside `Application.onCreate` → instant FATAL on every process start.
3. `com.sony.dtv.homekit` shares UID 10085 **and** the process with airplayapp; its
   `BootCompletedReceiver` starts the shared process at boot.
4. On this firmware the persistent-app restart path (`am_proc_start ... restart`) ignores
   BOTH `enabled=3` (disabled-user) AND per-user uninstall state.
5. Packages uninstalled for user 0 — with OR without `-k` — are **re-installed automatically
   at boot** (Finsky `shouldRecoverRestoredPackages` / firmware self-heal; verified with
   fresh ceDataInode values after each reboot).
6. Net result: ~10 crashes/second crash loop since July (954+ crash-buffer entries at start
   of session; load average 30+).

## Resolution

- `pm enable com.vewd.core.service` — the only adb-reachable fix. airplayapp now starts
  cleanly and idles resident (~80 MB). July round-2 item reverted deliberately.
- airplayapp/homekit **cannot be removed without root**. Verified futile:
  `pm disable-user` (respawns), `pm uninstall -k --user 0` (restored at boot),
  `pm uninstall --user 0` (restored at boot), `pm disable` (SecurityException:
  "Shell cannot change component state"). All package states revert at boot.
- `airplayptp` (root init daemon, AirPlay PTP) cannot be stopped without root.

## Round 4: bloat/telemetry disable list (33 packages, all disable-user --user 0)

Support/help/promo: com.sony.dtv.customersupport, com.sony.dtv.customersupport.provider.res,
com.sony.dtv.eulaviewer, com.sony.dtv.helpguidecontents, com.sony.dtv.smarthelp,
com.sony.dtv.privacypolicy, com.sony.dtv.softwarelicense, com.sony.dtv.bivlinfo,
com.sony.dtv.livingfit, com.sony.dtv.notificationcenter, com.sony.dtv.usercontext

IoT/telemetry: com.sony.dtv.seeds.iot, com.sony.dtv.seeds.iot.remotestart

Hotel/commercial (b2b): adminpassword, deviceadminsettings, frameworkextension, hotelmode,
importexport, noderuntime.normal, noderuntime.privilege,
noderuntimeextension.node_20_11_1, prosettings, webappruntimedrm (all `com.sony.dtv.b2b.*`)

Legacy casting/mirroring/media: com.sony.dtv.networkapp.wifidirect, com.sony.dtv.homenetwork,
com.sony.dtv.webapi.core (Sony mobile-app REST API), com.sony.dtv.interactivetvutil,
com.sony.dtv.interactivetvutil.output, com.sony.dtv.seconddispsetting, com.sony.dtv.hddmgr

Setup wizards: com.sony.dtv.quicksetup, com.sony.dtv.QuickSetupCustomizer

Kept deliberately (input/CEC/core): com.sony.dtv.tvinput.* (all), com.sony.dtv.tvapi,
com.sony.dtv.frame, com.sony.dtv.braviasync{menu,service,setting} (HDMI-CEC),
com.sony.dtv.connecteddevicesettings, com.sony.dtv.networksettings, com.sony.dtv.imeproxy,
com.sony.dtv.audiooutput, com.sony.dtv.HomeTheatreControl, com.sony.dtv.smartmediaapp,
com.sony.dtv.seeds.auth, com.sony.dtv.sonysystemservice, com.sony.dtv.settingsprovider,
com.sony.dtv.modelvariation, com.sony.dtv.configsettings, com.sony.dtv.irb{service,laster},
com.sony.dtv.remotecontrolsettings, com.sony.dtv.timers, com.sony.dtv.servicemode.

## Verification (2026-11-10)

- HOME resolves to `com.google.android.tvlauncher/.MainActivity` (`isDefault=true`),
  launcher process stable, zero new crashes of any kind after the vewd re-enable.
- Operator smoke test: stock home (no Sony branding) ✓, HDMI input switching ✓,
  Netflix/YouTube playback ✓, Settings navigation ✓.
- airplayapp crash loop: 0 new crashes post-fix (was ~10/sec).

## Root status (researched 2026-11-10)

- No public root for US-retail XBR-55X800H (MT5893, Android 10; platform per
  `ro.board.platform`). Sony ships locked TV
  bootloaders and has no TV unlock program. Only documented Sony TV roots: Chinese-market
  variants (X8500G via fastboot unlock, XDA) and pre-2017 models via stale one-click-root
  bugs. Kernel exploits exist for other vendors' MTK TV sets (e.g. Xiaomi) but no public
  port for this platform. Root would add: purging persistent packages (airplayapp), hosts
  -file blocking. Judged not worth the brick risk on a working set.

## Firmware note

- TV runs S97 (incremental 662301, 2020); Sony published v6.6230 for NA on 2026-04-28.
- An OTA will likely re-enable/restore Sony packages and patch ADB — after any update,
  re-run the Round 3/4 disable lists (and re-verify the crash-loop fix holds).
- AdGuard Private DNS (dns.adguard-dns.com) is still active from round 1.

## ADB state at end of round 3/4

- Left ENABLED (`10.0.0.178:5555`) for iteration. To harden:
  `adb shell settings put global adb_enabled 0` or toggle "Network ADB debugging" off.

## Revert

- Round 3 disable-user items + Round 4 list: `pm enable <pkg>` (or `./backups/restore.sh --round3` / `--round4`).
- airplayapp/homekit: already re-installed by the firmware; `pm enable` re-activates.
- Re-disabling vewd will RE-CREATE the AirPlay crash loop on this firmware — see above.
- Full revert script: `./backups/restore.sh`.

---

# Round 5 (2026-11-13): Paramount+ infinite spinner — AdGuard DNS vs Conviva

**Symptom:** Paramount+ (com.cbs.ott) main page loads; any playback = infinite loading
circle. App auto-updated to v17.4.0 the same evening (18:37).

## Root cause

- AdGuard Private DNS (round 1) sinkholes `conviva.com` / `livepass.conviva.com` → 0.0.0.0.
- The Paramount+ app gates stream start on Conviva (video QoE analytics) SDK init.
  With the domain sinkholed, init fails instantly and silently → infinite retry loop.
- Signature in logs: NO errors, NO DRM/CDN activity from com.cbs.ott, only heavy GC churn.
  Connection table during spinner: Adobe Analytics (63.140.32.0/19) + Conviva sensor IPs
  + Google GMS + Fastly — no video CDN, no Widevine license server.
- Connection table during working playback (DNS off): Akamai (video CDN, rDNS-confirmed),
  AWS/CloudFront, Fastly, Google, live Conviva sessions (162.247.241.4,
  2620:10b:7001:11::149, livepass → 199.127.194.40 — Conviva sensor CIDRs
  199.127.194.0/24, 162.247.224.0/20, 2620:10b:7000::/44).
- A/B: AdGuard on → spinner (reproducible); off → plays. Scattered identical user reports
  ("app loads but episodes spin") on status trackers the same day suggest v17.4.0 made
  the Conviva init mandatory for ad-blocking households.

## Resolution (operator decision 2026-11-13)

- Private DNS left OFF on the TV for now:
  `settings put global private_dns_mode off` (specifier `dns.adguard-dns.com` preserved).
- Restore ad-blocking later: `settings put global private_dns_mode hostname`
  (specifier still stored), or switch to a personal AdGuard/NextDNS server with an
  `@@||conviva.com^` allowlist exception, or — once the operator's self-hosted server
  exists — a LAN AdGuard Home with the same exception and the TV pointed at it via
  static DNS.

## Root / hosts-file check (verified 2026-11-13)

- `adb root` → "adbd cannot run as root in production builds" (user build, ro.debuggable=0).
- No su binary (system/bin, system/xbin, sbin).
- `/system/etc/hosts` root-owned, `/vendor` on dm-verity device (`/dev/block/dm-1`, ro);
  write test → "Read-only file system". Hosts-file ad-blocking requires root; no public
  root for this set (see round 3).

## On-device ML inventory (2026-11-13): negative

- Platform `mt5893`; no APU/NPU props, no neural HALs, no tflite/onnx/mnn/nb model files
  anywhere under /system /vendor /odm /product. 2020-era MediaTek TV SoC predates the
  AI-PQ/AI-SR units of later chips; Sony's upscaling/PQ runs on the TV-OS side
  (basic/linux_rootfs/3rd_ro partitions — outside Android's namespace, per the
  fastboot partition table research in round 3). Google Assistant hotword models, if
  present, live in GMS private data (unreadable without root).
