# Operations

*Everything you need to keep this TV in its current, deliberate state — and how to
change your mind about any part of it.*

## Connect

```bash
ADB=~/google-glasses/tools/platform-tools/adb     # any adb ≥30 works (macOS universal)
DEV=10.0.0.178:5555                               # TV keeps this DHCP lease
$ADB connect $DEV
$ADB -s $DEV shell
```

**Pitfall:** if `adb connect` fails with `No route to host` while `ping`/`nc` work,
a stale adb server lost its local-network permission — `adb kill-server && adb
start-server` and retry.

## Current device state (2026-11-14, post round-24 — campaign closed)

| Layer | State |
|---|---|
| Launcher | stock Android TV (`com.google.android.tvlauncher`), Sony skin removed |
| Packages | **49 disabled** + 9 removed-for-user (spyware/demo/telemetry rounds 1–6, sweep round 24) |
| Tracking/telemetry | **9 components disabled** — IDD agent, SEEDS auth/iot/remotestart, Sony Select, privacy-policy, user-context, smarthelp, bivlinfo |
| Research BPKs | **ALL UNINSTALLED** — remote-firmware-update-service, crestronconnected, bravia-updater gone; ports 20335/20341/20343 closed |
| Node services | 1 — `bravia-web-control-ui` on **127.0.0.1:20338 only** (not LAN-visible), auto-starts at boot |
| Web-control API | nginx on 0.0.0.0:80 — JSON-RPC token-gated, `/sony/avContent` unauthenticated (input list only) |
| Webui admin password | `1234abcd` — **still set** (gates the webui; removal = pending operator decision, see below) |
| Microphone | total lockdown — all grants revoked, `appops deny` on all 204 packages, no far-field mic (`builtinmic=0`) — **verified intact after all reboots** |
| Ad DNS | **off** (AdGuard sinkholes `conviva.com` and breaks Paramount+ playback; specifier preserved) |
| ADB | enabled on 5555 |
| AirPlay crash loop | fixed (Vewd stays enabled — do not disable it again, see FINDINGS §3) |
| Stability | verified 2026-11-14: 0 FATAL / 0 ANR; last reboots were remote-power-key + BPK install/uninstall cycles |

## Webui (the one remaining research surface)

```bash
$ADB -s $DEV forward tcp:18081 tcp:20338
open http://127.0.0.1:18081/sony/webui/          # login admin / 1234abcd
```

Through it: full JSON-RPC control (`/api/webapi/:path`), IRCC remote control,
settings import/export, and the bridge proxy
(`/api/androidbridge/system/generateWebApiAuthToken` mints JSON-RPC tokens on demand).

**To close it entirely:**

```bash
# clear the admin password (re-gates the webui behind error?code=1)
$ADB -s $DEV shell pm clear com.sony.dtv.b2b.adminpassword
# and/or disable the web stack (reverse with scripts/webstack-toggle.sh on)
./scripts/webstack-toggle.sh off
```

**To remove the webui app itself:** the runtime's own uninstaller —
`assets/autoUninstaller.pkg` from the NodeRuntimePrivilege APK, run through the
USB chain (see `docs/REPRODUCE.md`), or `pm uninstall --user 0
com.sony.dtv.b2b.noderuntime.privilege` (runtime-level).

## Reverts (per round)

```bash
./backups/restore.sh --round1     # re-install the 9 removed packages
./backups/restore.sh --round2     # re-enable voice/recs/cast pkgs (vewd stays enabled!)
./backups/restore.sh --round3     # Sony launcher skin + SELECT + tvx + homekit
./backups/restore.sh --round4     # bloat/telemetry disables
./backups/restore.sh --dns-only   # reset Private DNS
./backups/restore.sh              # everything
```

**Round-24 tracking-sweep reverts (manual, not in restore.sh):**

```bash
$ADB -s $DEV shell pm enable com.sonyericsson.idd.agent        # Sony IDD telemetry agent
$ADB -s $DEV shell pm enable com.sony.dtv.seeds.auth           # SEEDS auth
```

**Round-18 B2B support-stack reverts (manual; these are webui dependencies):**

```bash
$ADB -s $DEV shell pm enable com.sony.dtv.b2b.hotelmode        # hotel settings provider
$ADB -s $DEV shell pm enable com.sony.dtv.b2b.importexport     # settings import/export
$ADB -s $DEV shell pm enable com.sony.dtv.b2b.adminpassword    # password gate (clears webui lock)
$ADB -s $DEV shell pm enable com.sony.dtv.b2b.prosettings      # ProSettingsService
```

**Mic lockdown reversal:** `adb shell appops reset`, then targeted
`pm grant <pkg> android.permission.RECORD_AUDIO`, then
`pm enable com.sony.dtv.acousticautocalibration`
(full record: `backups/mic-lockdown-20261113.txt`).

**Restore ad-blocking:** `adb shell settings put global private_dns_mode hostname`
(specifier `dns.adguard-dns.com` still stored) — but Paramount+ will spin forever
unless your resolver allowlists `conviva.com` (personal AdGuard/NextDNS server or a
LAN AdGuard Home with `@@||conviva.com^`).

## After a future OTA (v6.7+)

1. Re-run the round 1/3/4/24 disable lists (`backups/` + this file have them all).
2. Re-verify the crash-loop fix holds (`logcat -d -b crash` clean of airplayapp).
3. Re-check `webstack-toggle.sh status` — an OTA may re-disable or re-enable parts.
4. Expect `adb_enabled` to survive; if not: Settings → Device Preferences →
   About → Build ×7 → Developer options → Network ADB debugging.
5. The update validator will reject anything unsigned — an OTA applies only if it
   is a genuine Sony package (see FINDINGS: the A/B pipeline is fully fingerprinted).

## Removing the USB stick

Safe at any time. The stick still carries `extapp_installer.pkg` (re-staged by the
zip-slip tests) — inert without a mount-event trigger, but pull it to be tidy.
A re-inserted stick fires the B2B detection chain (`bpk_installation` hotel setting
is `On`); reset it with:

```bash
$ADB -s $DEV shell content delete \
  --uri content://com.sony.dtv.b2b.hotelsettings/hotel --where "name='bpk_installation'"
```

## Known quirks (benign, documented)

- `vold: Failed to find mounted volume for /dev/null/Android/data/...` —
  noderuntime cache-dir fallback quirk. Zero impact.
- `linker: CANNOT LINK EXECUTABLE /vendor/bin/cat (libtombstone.so)` —
  MTK crash-dumper cosmetic failure.
- `NodeRuntimeNormal: PrepareInstall: AESDecryptByRSA = -1` on USB mounts —
  the normal runtime's installer reacting to B2B files on a stick; harmless.
- `system_server` runs hot (~90% CPU) — characteristic of this MTK platform since stock.

## Root: the closed doors (do not re-open without new information)

1. Firmware payload signature — Sony's OTA key, verified in the A/B update engine
2. Anti-rollback — client-side (`isNewerThanRunningVersion`), enforced before offerPayload
3. BPK forging — needs Sony's RSA private key (the EAIP magic is the only file check,
   but the AppInstallerCore AES-key unwrap is not forgeable)
4. SELinux — enforcing, no permissive cmdline, no reachable setter
5. `/data/system`, `/data/local/tmp`, app-private dirs — SELinux-blocked from every context we hold
6. ProSettingsService `processRequest*` — NodeRuntime-uid gated
7. TV-OS side (`/var/app`, `/data/upgrade`) — invisible from Android

Full maps: `docs/FINDINGS.md`, `docs/history/ROUNDS.md` (rounds 1–24).
