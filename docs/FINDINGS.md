# Findings

*What's actually inside a consumer Sony BRAVIA — and what eight magic bytes wake up.*

Everything below is **verified on hardware** unless marked otherwise. Evidence
signatures (log lines, commands, responses) are quoted throughout; the full
round-by-round investigation log lives in [history/ROUNDS.md](history/ROUNDS.md).

---

## 1. The USB BPK chain — a privileged app store with no receipt check ⭐

**One USB stick, eight magic bytes, and your TV installs and auto-runs a privileged
Node.js app at every boot. No signature. No checksum. No certificate.**

Sony ships a complete hotel/commercial deployment platform inside every consumer set.
Packages (`.pkg` "BPK" files) on a USB volume are detected, user-confirmed once, and
installed into the Node.js runtime — which holds one of the most powerful permission
sets on the device.

### The chain, as executed on 2026-11-13

```
USB stick with extapp_installer.pkg at volume root
   │  validation: first 8 bytes must equal  EAIP 00 00 01 00   ← the ENTIRE check
   ▼
usbmsgservice (uid 1000) broadcasts IsExistNodeInstallerFile=true
   ▼
NodeRuntimePrivilege.UsbDetector (uid 10033, system priv-app)
   │  single-BPK path SKIPS the pincode dialog AND the hotel-mode gate
   │  (both gates apply only to the multi-package scan path)
   ▼
Vewd web-app consent UI  ── operator taps OK ──▶  AES decrypt → TGZ extract
   ▼
TV force-reboots; on boot:
   bravia-web-control-ui auto-launches in NodeProcessService0 (uid 10033)
   ▼
   …and the platform starts nginx (root → uid 2900) on 0.0.0.0:80
```

Verified boot-log signature:

```
NodeProcess:: execNodeAsSharedlib: auid:name = bravia-web-control-ui
  args = /data/user/0/com.sony.dtv.b2b.noderuntime.privilege/app/node_services/
         bravia-web-control-ui/index.js
```

### What uid 10033 runs with

`NodeRuntimePrivilege` is a system `priv-app` holding:

```
WRITE_SECURE_SETTINGS   MASTER_CLEAR          REBOOT
INTERACT_ACROSS_USERS_FULL   MANAGE_USERS     WRITE_MEDIA_STORAGE
REQUEST_INSTALL_PACKAGES / REQUEST_DELETE_PACKAGES
CAPTURE_VIDEO_OUTPUT    KILL_BACKGROUND_PROCESSES   CONNECTIVITY_INTERNAL
```

…and ships **JNA, bytedeco-javacpp, and commons-compress (CPIO)** — native-code
invocation and archive extraction in the same runtime.

### The honest boundary

Crafting a *new* BPK requires Sony's RSA private key (the package body key is
RSA-wrapped; the runtime recovers it via `ProSettings.decryptPhrase`). **Replaying an
existing one requires nothing.** Four legitimate Sony BPKs sit in the runtime APK's
`assets/preinstall/` — we installed `bravia-web-control-ui` from there — and every
hotel TV and firmware dump in the world carries more. Consumer sets enforce no
precondition beyond the OK button: the design assumes hotel-mode TVs see BPKs and
consumer TVs don't, but nothing on the consumer path checks.

### What we did with it

We installed Sony's own `bravia-web-control-ui` — turning the TV into a
**web-controllable set** (kept deliberately; toggle with `scripts/webstack-toggle.sh`):

| Endpoint | Reachable from | Auth |
|---|---|---|
| `POST /sony/avContent` (input list, status) | **entire LAN** (0.0.0.0:80) | **none** |
| `POST /sony/system`, `/sony/IRCC`, … | LAN | webauth (PIN for LAN clients) |
| `http://127.0.0.1:80/sony/webauth/auth_tv` | on-device only | trusted — issues tokens with no PIN |

---

## 2. The dual-OS boundary — a second OS hiding in the mount table

The X800H runs Sony's TV-OS beside Android. Its filesystems are mounted **inside
Android's namespace** and gated only by SELinux (DAC alone would not stop you — one
root boot script chmods the shared staging dir to **0777**):

| Mount | Purpose | Shell access |
|---|---|---|
| `/mnt/vendor/linux_rootfs` (+`/basic`, `/etc`) | the TV-OS root | denied |
| `/mnt/vendor/3rd` | TV-OS third-party apps | denied |
| `/vendor/recipe` (fmask=0000!) | panel calibration data | denied |
| `/perm`, `/fdata` (rw) | per-device permissions / factory data | denied |
| `/data/vendor/tmp` | **shared staging ground** (root sockets `DTVService`, `dtv_svc_application_ipc`, `DFBInput` live here) | denied by SELinux type |

`adb bugreport` sidesteps some of this: the root-collected dumpstate streams back the
kernel command line (full partition map with encryption flags, `builtinmic=0`),
kernel log, iptables, and SMAPS of every process — while the `dumpstate` binary itself
is exec-blocked for shell.

## 3. The four-month crash loop nobody noticed

July's debloat disabled the Vewd browser engine; nobody noticed the TV then crashed
**~10 times per second for four months** (954+ crash-buffer entries, load average 30+).
Root cause is a five-link chain, each link individually mundane:

1. `airplayapp` is `FLAG_PERSISTENT` and binds Vewd in `Application.onCreate` → instant FATAL
2. `homekit` shares its UID *and* process, and starts it at boot
3. the persistent-restart path ignores `disabled-user` **and** per-user uninstall state
4. boot self-heal re-installs per-user uninstalls (with or without `-k`)
5. `pm disable` is SecurityException-denied for Sony-privileged packages

Only adb-reachable fix: keep Vewd enabled. Documented so no one repeats it.

## 4. Paramount+ and the analytics SDK that ate streaming

Symptom: app UI loads, every video = infinite spinner, **zero errors logged**.
Cause: DNS-level ad blocking sinkholes `conviva.com`; Paramount+ (v17.4.0) gates
stream start on Conviva QoE init, which fails instantly and silently, forever.
Diagnosed by connection-table forensics (analytics-only sessions during the spinner;
Akamai CDN + live Conviva sessions once DNS was off) — a clean A/B with AdGuard's own
resolver as the referee. Fix: allowlist `conviva.com` on any filtering resolver you
actually want to run on a TV.

## 5. Total microphone lockdown — verified in hardware

Permission grants revoked, `appops RECORD_AUDIO deny` applied to **all 204 packages**
(the enforcement layer — fails closed against future grants and the policy-fixed active
IME), and the bootloader itself confirms the hardware: `androidboot.svp.builtinmic=0`.
The remote's push-to-talk mic feeds a voice stack that's been disabled since round 2.

## 6. What held (the walls that didn't fall)

- **OTA updater**: the exported `offerPayload` bridge is callergated in code —
  `SignatureVerifier.hasValidSignature()` against four pinned Sony signer SHA-256s.
- **No setuid/setgid binaries** anywhere; SELinux Enforcing; dm-verity on all root code.
- **Kernel 4.19.75 armv8l**: no userfaultfd/SysVIPC/FUSE/AF_ALG/RxRPC/pedit → the 2026
  COW-class LPE wave has no surface here; perf locked (`paranoid=3`); KASLR + emulated
  PAN + REFCOUNT_FULL. Details: [KERNEL_TRIAGE.md](../KERNEL_TRIAGE.md).
- **No public root** for US-retail sets (locked bootloader; only Chinese-market
  X8500G-era units had fastboot unlocks).
- **Secrets hygiene**: static sweep of 115 APKs found nothing — Sony build-redacts
  private keys with literal `[REDACTED PRIVATE KEY]` placeholders.

## Leads still open (next session)

- `ImportExport` (uid 1000): the `Bravia*HotelSettings.dat` USB import path — a
  system-uid parser for removable-media data (format not yet reversed).
- Custom driver RE: `dtv_driver.ko` (13.6 MB, permanent) and the `sony_pqctrl` family
  (no `.ko` on disk — loaded from the TV-OS side; live `/proc/driver` interface).
- Mali `r21p0` advisory cross-reference; post-Feb-2026 4.19 stable regressions.
- The web stack's own surface: the auth flows on `/sony/webauth`, and what else
  answers before authentication.
