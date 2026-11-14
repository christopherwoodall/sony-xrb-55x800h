# Sony BRAVIA XBR-55X800H — Cleanup & Security Report

| | |
|---|---|
| **Device** | Sony BRAVIA 4K UR3, XBR-55X800H (MT5893, armv8l) |
| **OS** | Android 10, build `QTG3.200305.006.S97` / 662301 (= v6.6230-era, SPL 2026-02-01, kernel 4.19.75 built 2026-04-08) |
| **Boot state** | bootloader locked, verified boot **green**, dm-verity enforcing (read-only, non-rooted) |
| **Access** | network ADB `10.0.0.178:5555` (enabled; see [Operations](#operations)) |
| **Sessions** | R1–R2: 2026-07-23 · R3–R9: 2026-11-10/13 |
| **Companion docs** | [KERNEL_TRIAGE.md](KERNEL_TRIAGE.md) · local `~/sony-xrb-55x800h-analysis/` (HUNT.md, cached artifacts) |

---

## TL;DR — what was done

| Round | Date | Change | Reversibility |
|---|---|---|---|
| 1 | 2026-07-23 | 9 spyware/adware/telemetry packages removed (Samba ACR, promos, demo, bug-reporters) | `restore.sh --round1` |
| 2 | 2026-07-23 | 12 packages disabled (voice stack, recommendations, Cast/DLNA/Vewd/Games) + animations off; ⚠️ Vewd disable later caused a crash loop — see R3 | `restore.sh --round2` |
| 3 | 2026-11-10 | Sony launcher skin removed → **stock Android TV home** (customizer + RRO + Sony SELECT + tvx + homekit disabled) | `restore.sh --round3` |
| 4 | 2026-11-10 | 33 bloat/telemetry/hotel-mode packages disabled | `restore.sh --round4` |
| 5 | 2026-11-13 | **Paramount+ spinner root-caused** (AdGuard DNS vs Conviva); Private DNS left **off** | `private_dns_mode hostname` |
| 6 | 2026-11-13 | **Total microphone lockdown** (grants revoked + AppOps deny on all 204 packages) | see [Mic](#microphone-lockdown) |
| 7–9 | 2026-11-13 | Root hunt: attack-surface audit, artifact cache (2.1GB, local-only), kernel CVE triage | read-only |

Net: **55 packages disabled/removed**, stock launcher, mic sealed, telemetry minimized,
inputs/streaming/settings fully verified working by the operator after every destructive
round. Everything is reversible; nothing was rooted or flashed.

---

## Current device state

### Launcher & home
- HOME = `com.google.android.tvlauncher` (stock, unskinned). Sony's skin
  (`tvlaunchercustomizer` + RRO `overlay.apporder` + `sonyselect`) disabled.
- Launcher data cleared once (round 3) to drop stale Sony "Shop"/"Apps" tiles.

### Packages (55 disabled/removed for user 0)
- **Round 1 — removed** (`pm uninstall --user 0`, APK kept): Samba TV ACR (`tv.samba.ssm`),
  promos, demosupport/demosystemsupport, multiscreendemo, sonybugreportsys,
  bugreportsender, feedback, sonyloglevelsettingsys.
- **Round 2 — disabled**: tv.assistant, assistantadapter, voicerecognitionconfirmation,
  katniss, tvrecommendations, mediashell (Cast), sonyericsson.dlna + huey.dlna.*,
  play.games, videos. *(vewd re-enabled in round 3 — see below.)*
- **Round 3 — disabled**: tvlaunchercustomizer, tvlaunchercustomizer.overlay.apporder,
  sonyselect, tvx, homekit.
- **Round 4 — disabled**: customersupport(+provider), eulaviewer, helpguidecontents,
  smarthelp, privacypolicy, softwarelicense, bivlinfo, livingfit, notificationcenter,
  usercontext, seeds.iot(+remotestart), all 10 remaining `b2b.*`, networkapp.wifidirect,
  homenetwork, webapi.core, interactivetvutil(+output), seconddispsetting, hddmgr,
  quicksetup(+customizer), tvpositionscreen.
- **Round 6 — disabled**: acousticautocalibration (last Sony mic consumer).
- **Kept deliberately**: all `tvinput.*`, `tvapi`, `frame`, `braviasync*` (HDMI-CEC),
  `connecteddevicesettings`, `networksettings`, `imeproxy`, `audiooutput`,
  `HomeTheatreControl`, `smartmediaapp`, `seeds.auth`, `sonysystemservice`,
  `settingsprovider`, `modelvariation`, `configsettings`, `irb*`, `remotecontrolsettings`,
  `timers`, `servicemode`.
- **Firmware self-heal caveat**: `airplayapp`/`homekit` re-install themselves at boot and
  their persistent processes ignore disabled/uninstalled state (see
  [The AirPlay crash loop](#the-airplay-crash-loop)). They are inert post-fix.

### DNS (ad/tracker blocking)
- Round 1 set AdGuard DoT (`dns.adguard-dns.com`). Round 5 **disabled it**: AdGuard
  sinkholes `conviva.com`, which Paramount+ requires before starting playback.
- Current: `private_dns_mode=off` (specifier preserved).
- Restore blocking: `settings put global private_dns_mode hostname` — but Paramount+
  breaks again unless a personal AdGuard/NextDNS server with `@@||conviva.com^` is used.
- Long-term plan: LAN AdGuard Home + static DNS on the TV once self-hosted.

### Microphone lockdown
- All `RECORD_AUDIO` grants revoked (Gboard's active-IME grant is system-policy-fixed —
  covered by AppOps instead).
- `appops set <pkg> RECORD_AUDIO deny` applied to **all 204 packages** (enforcement
  layer; fails closed against any future grant).
- Hardware: no far-field mic in the TV (`androidboot.svp.builtinmic=0`, no audio input
  device registered); remote mic is push-to-talk into the disabled voice stack.
- Reversal: `appops reset` + targeted `pm grant` + `pm enable acousticautocalibration`.
  Details: `backups/mic-lockdown-20261113.txt`.

### ADB
- Enabled on 5555 for iteration. Harden when done:
  `adb shell settings put global adb_enabled 0`.

---

## The AirPlay crash loop

Why round 2's Vewd disable silently degraded the TV for four months, and why Vewd must
stay enabled:

1. Round 2 disabled `com.vewd.core.service`.
2. `com.sony.dtv.airplayapp` (`FLAG_PERSISTENT`) binds Vewd's `BrowserServiceImpl` in
   `Application.onCreate` → instant FATAL on every start.
3. `com.sony.dtv.homekit` shares UID 10085 + process with airplayapp and its
   BootCompletedReceiver starts the shared process at boot.
4. This firmware's persistent-restart path ignores BOTH `disabled-user` state and
   per-user uninstall; boot self-heal re-installs per-user uninstalls (verified with
   fresh `ceDataInode`s, with and without `-k`).
5. Result: ~10 crashes/sec since July (954+ buffer entries, load average 30+).

**Fix:** `pm enable com.vewd.core.service` (the only adb-reachable lever) — airplayapp
now idles resident (~80 MB) instead of burning a core. Do **not** re-disable Vewd.

---

## Paramount+ / AdGuard conflict (round 5)

- Symptom: app UI loads, every video = infinite spinner, **zero logged errors**
  (only GC churn + analytics-only connections: Adobe, Conviva, GMS, Fastly — no CDN, no
  Widevine license server).
- Cause: AdGuard sinkholes `conviva.com`/`livepass.conviva.com`; Paramount+ (v17.4.0)
  gates stream start on Conviva init. Verified by A/B and by AdGuard's own DoH resolver.
- Status: DNS blocking off on this TV (operator decision). Personal-server allowlist or
  LAN AdGuard Home with the `conviva.com` exception are the clean long-term fixes.

---

## Architecture & security findings

### Launcher architecture
`com.sony.dtv.tvx` is **not** the home app (no HOME intent filter). The Sony look is
`tvlaunchercustomizer` + RRO overlay + `sonyselect` on top of the stock
`com.google.android.tvlauncher`. Live TV/inputs live in separate `tvinput.*` packages.

### Dual-OS boundary
The TV runs a second OS (Sony's TV-OS) beside Android. Its mounts appear in Android's
namespace — `/mnt/vendor/linux_rootfs`, `/mnt/vendor/3rd`, `/vendor/recipe` (fmask=0000),
`/perm`, `/fdata` (rw), `/data/vendor/3rd_rw`, `/data/vendor/persist` — **all SELinux-denied
to the shell domain** (verified per-path). The shared staging ground is
`LINUX_TMP_PATH=/data/vendor/tmp` (root chmod 777 at boot by `dtv-svc`, hosts the
`DTVService`/`dtv_svc_application_ipc`/`DFBInput` sockets) — blocked to shell by SELinux
type, not DAC.

### Privilege surface (audited rounds 7–9)
- 38 packages run as uid 1000. Manifest audit of system-uid apps found 35 exported
  components **without manifest permission guards** — but the top lead (OTA bridge
  `UpdateSessionManagerService.offerPayload`) is **callergated in code**:
  `SignatureVerifier.hasValidSignature()` against four pinned Sony OTA-signer SHA-256s.
  Even direct `IUpdateEngine` bind requires a Sony-signed payload.
- `adb bugreport` works and returns a **root-collected dumpstate** (18.7MB cached:
  kernel cmdline with the full partition/encryption map, kernel log, iptables, EBPF
  stats, PRINTENV, SMAPS of all processes). `dumpstate` binary itself is exec-blocked
  for shell; the binder path is the door.
- **Trusty TEE + RPMB** (storageproxyd ↔ `/dev/trusty-ipc-dev0`); `trusty_version`
  denied even to root dumpstate. **Root nginx** ("reverseproxy") starts on property
  `vendor.svp.reverseproxy.enable=1`.
- **No setuid/setgid binaries** anywhere; SELinux Enforcing; kernel 4.19.75 armv8l
  (32-bit userland); no userfaultfd/SysVIPC/FUSE/AF_ALG/RxRPC/pedit → the 2026
  COW-class LPE wave and classic race primitives are unreachable. Details:
  [KERNEL_TRIAGE.md](KERNEL_TRIAGE.md).

### Root status
No public root for US-retail XBR-55X800H (locked bootloader, no unlock program; only
Chinese-market X8500G-era units have documented fastboot unlocks). `adb root` refused
(production build), no su binary, hosts file on read-only verity partitions. Practical
root paths, if ever pursued: custom-driver RE (`dtv_driver.ko` 13.6MB, `sony_pqctrl`),
Mali r21p0 advisory cross-reference, or post-SPL 4.19 regressions — see
[KERNEL_TRIAGE.md](KERNEL_TRIAGE.md).

### Secrets hygiene (verified)
Static sweep of 115 cached APKs: no credentials. Sony build-redacts private keys with
literal `[REDACTED PRIVATE KEY]` placeholders (IddAgent, OtaUrlProvisioning).

---

## Operations

```bash
ADB=~/google-glasses/tools/platform-tools/adb   # macOS universal (repo copy is linux-x86_64)
DEV=10.0.0.178:5555

$ADB connect $DEV                 # stale-server pitfall: kill-server first if
                                  # connect fails EHOSTUNREACH while ping/nc work
$ADB -s $DEV shell <cmd>          # uid 2000 shell — all admin below uses this
```

| Task | Command |
|---|---|
| Revert round 1 | `./backups/restore.sh --round1` |
| Revert round 2 (vewd stays enabled) | `./backups/restore.sh --round2` |
| Revert round 3 | `./backups/restore.sh --round3` |
| Revert round 4 | `./backups/restore.sh --round4` |
| Restore ad-blocking (breaks Paramount+) | `adb shell settings put global private_dns_mode hostname` |
| Undo mic lockdown | `adb shell appops reset` + targeted `pm grant` + `pm enable acousticautocalibration` |
| Disable ADB when done | `adb shell settings put global adb_enabled 0` |
| Factory reset | restores everything Sony (and re-runs setup wizard) |

**After any future OTA (v6.7+):** re-run rounds 1/3/4 disable lists, re-verify the
crash-loop fix holds, re-check ADB. Package-state snapshots live in `backups/`.

---

## Round log (details)

### Round 1 (2026-07-23) — spyware/adware removal
Removed per-user (APK retained, restorable via `pm install-existing`): Samba TV ACR
(`tv.samba.ssm` — fingerprints viewing), promos, demosupport/demosystemsupport,
multiscreendemo, sonybugreportsys, bugreportsender, feedback, sonyloglevelsettingsys.
213 → 204 installed packages; core packages verified intact. AdGuard DoT configured
and verified (doubleclick → 127.0.0.1). Snapshot: `backups/snapshot-20260723-160017/`.

### Round 2 (2026-07-23) — voice + perf tuning
Disabled: voice stack (tv.assistant, assistantadapter, voicerecognitionconfirmation),
recommendations (katniss, tvrecommendations), unused background services (mediashell,
DLNA trio, vewd, play.games, videos). Animations → 0. Ads personalization opted out
on-device. ⚠️ The Vewd disable here seeded the AirPlay crash loop (fixed round 3).

### Round 3 (2026-11-10) — stock launcher
Disabled tvlaunchercustomizer + overlay.apporder + sonyselect + tvx + homekit;
`pm clear com.google.android.tvlauncher` to drop stale Shop/Apps tiles (account picker
appears once after clear). Verified: stock home, HDMI switching, Netflix/YouTube,
Settings — all ✓. Crash loop fixed (vewd re-enable) with 0 new crashes after.

### Round 4 (2026-11-10) — bloat/telemetry pass
33 packages disabled (full list preserved in git history and `backups/`): support/help/
promo apps, all remaining `b2b.*` hotel-mode packages, `seeds.iot*`, `webapi.core`,
`homenetwork`, `wifidirect`, `interactivetvutil*`, `seconddispsetting`, `hddmgr`,
`quicksetup*`. Input-critical packages kept (list in round-4 commit).

### Round 5 (2026-11-13) — Paramount+ spinner
Root-caused and resolved as described above ([TL;DR](#tldr--what-was-done),
[Paramount+ section](#paramount--adguard-conflict-round-5)).

### Round 6 (2026-11-13) — microphone lockdown
As described in [Microphone lockdown](#microphone-lockdown). Pre-state: 6 apps held the
grant; last actual mic use was YouTube ~245 days prior (557 ms).

### Round 7 (2026-11-13) — privesc attack-surface audit
Read-only root hunt. 38 system-uid packages; 11 audited via manifest parse → 35 exported
components without manifest guards; OTA bridge lead killed by in-code signature gating
(four pinned certs extracted); TV-OS sockets/mounts confirmed blocked; verdict: no
trivial root. Artifacts kept out of the repo (Sony code) in the local analysis dir.

### Round 8 (2026-11-13) — artifact cache + kernel evidence
2.1GB local cache built (`~/sony-xrb-55x800h-analysis/`, sha256 manifest): 115 APKs,
18 kernel modules + root `.ko`s, 66 init .rc files, partial /vendor/bin (root HAL
daemons are SELinux-uncachable), full kernel config + lsmod + getprop + sysctls.
`.gitignore` hardened. Firmware understanding corrected (see [meta](#tldr--what-was-done)
table — build is v6.6230-era, not 2020).

### Round 9 (2026-11-13) — artifact exploitation hunt
Full campaign log: `~/sony-xrb-55x800h-analysis/HUNT.md`. Highlights: the
confused-deputy door into OwnerService (audited — action-dispatched modules, no
attacker-controlled sinks at grep depth); `adb bugreport` root data stream; Trusty TEE,
root nginx, keydldaemon mapped; static secret hunt clean; usbmsgservice fake-USB chain
mapped end-to-end and closed.

---

## Repository layout

```
CLEANUP_REPORT.md      this document
KERNEL_TRIAGE.md       kernel CVE triage baseline (round 8)
backups/
  restore.sh           revert script (--round1..4, --dns-only; vewd-safe)
  snapshot-*/          pre-change package/prop snapshots
  mic-lockdown-*.txt   mic lockdown record + reversal
  round2-prestate.txt
.gitignore             keeps device artifacts out of git (*.apk/*.ko/*.dex/…)
platform-tools/        linux-x86_64 adb bundled by round 1 (macOS users: use
                       ~/google-glasses/tools/platform-tools/adb instead)
```

Local-only (never committed): `~/sony-xrb-55x800h-analysis/` — 2.1GB artifact cache
(APKs, modules, init rcs, kernel evidence, bugreport), `HUNT.md` campaign log,
decompiled trees, audit tooling. See its `README.md`.

---

# Round 10 (2026-11-13): the USB BPK chain — full map, hardware test pending

**Operator offers physical USB access; "walk the usb path and reenable those services".**

## The chain (all verified in decompiled code, not yet on hardware)

1. USB volume with `extapp_installer.pkg` at root → MTK DeviceManager real mount →
   `usbmsgservice` (uid 1000) broadcasts `IsExistNodeInstallerFile=true` + mount path.
2. `com.sony.dtv.b2b.noderuntime.privilege` `UsbDetector` (uid 10033, system priv-app):
   the single-BPK branch **skips the pincode dialog and the hotel-mode autorun gate**
   (both apply only to the multi-package scan path).
3. `AppInstallerUtil.isBpkPkgFile()` = **8-byte magic check only**
   (`EAIP\x00\x00\x01\x00`) — no signature, no checksum, no certificate.
4. `NodeRuntimeService` installs + launches the BPK as uid 10033, which holds
   WRITE_SECURE_SETTINGS, MASTER_CLEAR, REBOOT, INTERACT_ACROSS_USERS_FULL,
   MANAGE_USERS, WRITE_MEDIA_STORAGE, REQUEST_INSTALL/DELETE_PACKAGES,
   CAPTURE_VIDEO_OUTPUT, KILL_BACKGROUND_PROCESSES — and ships JNA/javacpp/
   commons-compress for native reach.
5. BPK body = installer JSON with a literal `cmd` key, `installation`, `options`
   (forcereboot, avoid_interruption), `meta` — format reconstruction in progress.

Second chain on the same stick: `Bravia*HotelSettings.dat` → ImportExport (uid 1000,
system) → HotelSettings provider writes.

## Closed this round

- nginx reverseproxy: `setprop vendor.svp.reverseproxy.enable` is SELinux-denied to
  shell; nginx not running; 2026 CVE set (15176 alias+rewrite heap overflow et al.)
  dormant unless the reverseproxy is ever started by Sony features.

## Next (hardware phase)

1. Reconstruct exact BPK body format from `loadInstallerInfo*` + `NodeRuntimeService`.
2. `pm enable` the noderuntime packages (reversible).
3. Operator plugs in USB → stage BPK via adb onto the stick → observe install/launch
   in logcat → verify uid + capabilities of the running node app.
4. Rollback: `pm disable` again, remove USB files.

---

# Round 11 (2026-11-13): USB BPK chain — VERIFIED END-TO-END ON HARDWARE

Operator plugged in a USB stick; the full chain was exercised with Sony's own
`bravia-web-control-ui` BPK (extracted from the runtime APK's `assets/preinstall/`).

## What happened (log-verified)

1. Stick mounted (real MTK mount) → usbmsgservice broadcast `IsExistNodeInstallerFile=true`.
2. NodeRuntimePrivilege UsbDetector fired; single-BPK path bypassed pincode + hotel gates.
3. Three round-4-disabled dependencies had to be re-enabled as the chain demanded them
   (each logged its absence): `prosettings` (supplies the RSA key via
   `ProSettings.decryptPhrase`), `noderuntime.normal` (its PermissionActivity is the
   forward target — its absence crashed the consent dialog in onCreate), `webapi.core`
   (WebApiCoreService for platform tokens).
4. Consent UI: `extapp_basic_installer3` Vewd web app (WebAppRuntimeActivity, uid 10002)
   loaded, talking to the runtime's `AppInstallerBackendServer` on 127.0.0.1:20040/20041.
   Operator confirmed "sony bravia web control ui 1.1.8 is ready to install" → OK.
5. Install completed; `forcereboot` fired (TV rebooted itself).
6. After reboot: **bravia-web-control-ui auto-launched** via BootReceiver →
   `NodeProcessService0` (uid 10033) `execNodeAsSharedlib` of
   `/data/user/0/com.sony.dtv.b2b.noderuntime.privilege/app/node_services/bravia-web-control-ui/index.js`.
7. The platform started **nginx reverseproxy** (root → uid 2900) on **0.0.0.0:80**.

## Resulting LAN exposure (verified by probe)

- `POST /sony/avContent` (getCurrentExternalInputsStatus) → **200 with full input list,
  NO authentication**.
- `POST /sony/system` / `/sony/IRCC` → 403 + webauth flow (`auth_default` = LAN PIN,
  `auth_tv` = localhost-trusted token issuance on 127.0.0.1:80).
- Node stack internal listener 127.0.0.1:20338 (uid 10033).

## Security assessment

- **Chain proven**: physical USB + 8-byte magic (`EAIP\0\0\1\0`) → privileged node app
  (uid 10033: WRITE_SECURE_SETTINGS, MASTER_CLEAR, REBOOT, INTERACT_ACROSS_USERS_FULL,
  MANAGE_USERS, REQUEST_INSTALL_PACKAGES…) persistently auto-running at boot. The BPK
  body is RSA-wrapped (Sony key needed to craft NEW packages) but ANY existing
  legitimately-built BPK (hotel TVs, firmware dumps, the four in the runtime APK itself)
  replays onto any consumer set with operator consent only.
- **Current posture regression**: the web API surface (removed in round 4) is back and
  partially unauthenticated on the LAN; node platform runs at boot.

## Rollback (when desired)

- `pm disable` noderuntime.{privilege,normal,extension} + prosettings + webapi.core →
  node app stops, nginx goes away, API closes. BPK remains installed but inert.
- Full removal of the installed app: the runtime's uninstaller
  (`assets/autoUninstaller.pkg` — cached) or the install-record deletion flow.

---

# Round 12 (2026-11-13): docs restructure — keep decision + narrative

- Operator decision: **web-control stack stays** (nginx + Sony JSON-RPC API on :80,
  bravia-web-control-ui auto-running). Toggle: `scripts/webstack-toggle.sh`.
- Repository restructured: findings showcase → `docs/FINDINGS.md`; runbook →
  `docs/OPERATIONS.md`; full reproduction guide → `docs/REPRODUCE.md`; analysis
  tooling → `scripts/`; this round-by-round log → `docs/history/ROUNDS.md`
  (was CLEANUP_REPORT.md — superseded as front document, preserved verbatim).
- Current state (verified live): 49 packages disabled, 9 removed, mic lockdown,
  DNS blocking off, web stack running, ADB on 5555.

---

# Round 13 (2026-11-13): ProSettingsService — exported system admin API

Operator pivots to root. Removed CLEANUP_REPORT.md (fully superseded by docs/).

## Finding

`com.sony.dtv.b2b.prosettings/.ProSettingsService` (uid 1000) is **exported and
guarded only by `android.permission.WRITE_SECURE_SETTINGS`** — an adb-grantable
development permission. Full admin interface: decryptPhrase (BPK MasterKey path),
getConfiguredWifiNetworks, getIpControlPSK, installLogo/uninstallLogo, setHotelMode,
setFeatures, enable/disableAppPackage, clearAllAccount, firmware-write flows,
processRequestSync (JSON-RPC router — only service "system"/prepareFwWrite, dead
post-Treble). decryptPhrase executes the native `/system/bin/b2bcmd decrypt_phrase`
(shell-blocked binary) as uid 1000; the fallback packed pubkey in NodeRuntimePrivilege
was build-stripped (`PACKED_PUBKEY = new int[0]`).

## Probe (built + executed on hardware)

`scripts/prosettings-probe/` — 20.8KB APK (Glass toolchain recipe; Sony AIDL
interfaces extracted per-device, not redistributed). Results:
- bind OK from an adb-installed untrusted app (pm grant WRITE_SECURE_SETTINGS)
- wifi configs disclosed (SSIDs/WPA/MACs; PSKs masked by toString)
- IpControlPSK empty; deviceId `[redacted MAC]`; SW PKG6.6230.0725NAA
- decryptPhrase → {"success":false} (b2bcmd semantics unresolved)

## Web-control stack state

- `/sony/webui/` (Nuxt SPA served by the node app, Express on 127.0.0.1:20338,
  proxied via nginx :80) returns error?code=1 for all routes — app-internal
  error state (suspect: hotel-mode configuration prerequisite).
- `adb forward` = localhost client: auth_tv endpoint reachable, guide/
  getSupportedApiInfo gated, accessControl/act → error 12.

## Open leads

- installLogo(String): candidate file-write primitive as uid 1000
- b2bcmd decrypt_phrase semantics (why success:false; lock file at
  /vendor/tmp/odm/b2b/b2bcmd.lock)
- wifi PSK unmasking via other system-uid paths
- webui error state prerequisite (hotel mode?)

---

# Round 14 (2026-11-13): MasterKey extracted → full offline BPK decryption

## Chain

1. Root-log trick (logcat carries `B2BCMD` stderr): our first decryptPhrase failed
   with `decrypt_phrase_error: -5` — **a corrupted constant in our probe** (hand-copied
   pubkey blob differed from ground truth at byte 451). Fixed programmatically; no more
   hand-copying crypto material.
2. Rebuilt probe against platform-34 (android-34-ext11 jar + build-tools r34, both now
   in the analysis dir); targetSdk 29 (clears the "app is old" warning).
3. `decryptPhrase("MasterKey", ENCRYPTED_PUBKEY)` → success → **RSA-2048 master public
   key** (PEM, openssl-verified).
4. Wrote `scripts/bpk_decrypt.py` (stdlib + openssl CLI): parses the EAIP header,
   RSA-public-recovers the wrapped key (48 bytes = 32-byte AES key + 16-byte MD5),
   verifies the body MD5, AES-256-CBC zero-IV decrypts to TGZ.
5. **Decrypted `bravia-web-control-ui` 1.1.8+230** (7,532 files, 72MB): MD5 OK,
   valid gzip, full source extracted.

## Web-control UI internals (from decrypted source)

- `app.js`: every route sits behind `hasAdminPassword` + `digestPassport.auth` —
  **the error?code=1 state is "no admin password set"**. Set the B2B admin password
  and the UI un-gates (then HTTP DIGEST auth).
- Authenticated surface: `POST /sony/webui/api/ircc`, `ALL /api/firmwareupdate/:method/:id`,
  `ALL /api/import` (settings import, chunk-upload-storage), `ALL /api/export`,
  `POST /api/androidbridge/:service/:method` (**generic Android-side forwarding proxy**),
  GraphQL at `/api/graphql`, webapi + IRCC proxies.
- The androidbridge proxy → `webappservice` (uid 1000) — the web shell skeleton.

## Next

Set the admin password (B2B flow / ProSettingsService `setFeatures`), digest-auth to
the webui, then audit `/api/androidbridge` + `/api/import` for write primitives.
