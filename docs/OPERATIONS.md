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

## Current device state (2026-11-13, post round-11)

| Layer | State |
|---|---|
| Launcher | stock Android TV (`com.google.android.tvlauncher`), Sony skin removed |
| Packages | **49 disabled** + 9 removed-for-user (spyware/demo/telemetry rounds 1–6) |
| Web-control stack | **RUNNING (kept)** — nginx on 0.0.0.0:80, `bravia-web-control-ui` node app (uid 10033) auto-starts at boot; toggle below |
| Microphone | total lockdown — all grants revoked, `appops deny` on all 204 packages, no far-field mic (`builtinmic=0`) |
| Ad DNS | **off** (AdGuard sinkholes `conviva.com` and breaks Paramount+ playback; specifier preserved) |
| ADB | enabled on 5555 |
| AirPlay crash loop | fixed (Vewd stays enabled — do not disable it again, see FINDINGS §3) |

## Web-control stack

```bash
./scripts/webstack-toggle.sh status   # packages, port 80, node process, API probe
./scripts/webstack-toggle.sh off      # close the API, stop node apps (reversible)
./scripts/webstack-toggle.sh on       # bring it back
```

What "on" means for your LAN: the Sony JSON-RPC API serves on port 80 —
`/sony/avContent` answers **without authentication** (input list/status only, verified);
everything interesting (`/sony/system`, `/sony/IRCC`, app control) sits behind the
webauth flow (LAN clients get a PIN prompt). On-device clients can mint tokens with no
PIN via `http://127.0.0.1/sony/webauth/auth_tv`.

Example — list inputs from any machine on the LAN:

```bash
curl -X POST http://10.0.0.178/sony/avContent \
  -H 'Content-Type: application/json' \
  -d '{"method":"getCurrentExternalInputsStatus","params":[],"id":1,"version":"1.0"}'
```

## Reverts (per round)

```bash
./backups/restore.sh --round1     # re-install the 9 removed packages
./backups/restore.sh --round2     # re-enable voice/recs/cast pkgs (vewd stays enabled!)
./backups/restore.sh --round3     # Sony launcher skin + SELECT + tvx + homekit
./backups/restore.sh --round4     # bloat/telemetry disables
./backups/restore.sh --dns-only   # reset Private DNS
./backups/restore.sh              # everything
```

**Mic lockdown reversal:** `adb shell appops reset`, then targeted
`pm grant <pkg> android.permission.RECORD_AUDIO`, then
`pm enable com.sony.dtv.acousticautocalibration`
(full record: `backups/mic-lockdown-20261113.txt`).

**Restore ad-blocking:** `adb shell settings put global private_dns_mode hostname`
(specifier `dns.adguard-dns.com` still stored) — but Paramount+ will spin forever
unless your resolver allowlists `conviva.com` (personal AdGuard/NextDNS server or a
LAN AdGuard Home with `@@||conviva.com^`).

**Full BPK-app removal** (beyond just toggling off): the runtime's own uninstaller —
`assets/autoUninstaller.pkg` from the NodeRuntimePrivilege APK, run through the same
USB chain that installed the app — or delete the install record via the runtime's
`deleteInstallRecord` flow.

## After a future OTA (v6.7+)

1. Re-run the round 1/3/4 disable lists (`backups/` has them all).
2. Re-verify the crash-loop fix holds (`logcat -d -b crash` clean of airplayapp).
3. Re-check `webstack-toggle.sh status` — an OTA may re-disable or re-enable parts.
4. Expect `adb_enabled` to survive; if not: Settings → Device Preferences →
   About → Build ×7 → Developer options → Network ADB debugging.

## Removing the USB stick

Safe at any time. The installed app no longer needs it; the stick's
`extapp_installer.pkg` was consumed during install. Nothing auto-runs from a
re-inserted stick without the consent dialog.
