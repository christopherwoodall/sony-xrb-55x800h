# Reproduce — from stock TV to web-controlled TV

*The full toolchain and every step that got us here. If you own an XBR-55X800H
(or a sibling MT5893 Sony Android 10 set) and a USB stick, this is the path.*

> ⚠️ Everything here runs against hardware you own. The end state installs Sony's own
> hotel web-control stack on your TV and exposes a partially-unauthenticated API on
> your LAN — see [OPERATIONS.md](OPERATIONS.md) for the off switch.

## 0. Host toolchain

```bash
brew install jadx                       # decompiler (1.5.6 used)
# aapt + dexdump: any Android build-tools; ancient ones work (we used android-14-era)
# adb: any platform-tools ≥ 30 — on this Mac: ~/google-glasses/tools/platform-tools/adb
```

Artifact cache layout (outside the repo, gitignored):

```
~/sony-xrb-55x800h-analysis/
  device-fs/          # mirrors the TV filesystem: 115 Sony/MTK APKs, vendor tree
  modules/            # kernel .ko files
  kernel/             # /proc/config.gz, lsmod, getprop, sysctls
  decompiled/         # jadx output per package
  HUNT.md             # working campaign log (findings / leads / dead ends)
```

## 1. Cache the artifacts from the TV

```bash
ADB=~/google-glasses/tools/platform-tools/adb; DEV=10.0.0.178:5555

# every Sony/MTK APK (~1GB) — generate the dir list on-device, tar once, pull once
$ADB -s $DEV shell "pm list packages | grep -E 'sony|mtk|ericsson' | sed 's/package://' \
  | while read p; do pm path \$p 2>/dev/null | head -1 | sed 's/package://;s#/[^/]*\$##'; done \
  | sort -u > /sdcard/sony_dirs.txt; tar -cf /sdcard/sony_apks.tar -T /sdcard/sony_dirs.txt"
$ADB -s $DEV pull /sdcard/sony_apks.tar . && tar -xf sony_apks.tar -C device-fs/

# SELinux blocks adbd (not shell) on /vendor — bridge via shell-cat through /sdcard:
$ADB -s $DEV shell "cat /vendor/app/OndAgentService/OndAgentService.apk > /sdcard/x.apk"
$ADB -s $DEV pull /sdcard/x.apk device-fs/vendor-bridged-apks/

# kernel config + modules (drivers)
$ADB -s $DEV shell zcat /proc/config.gz > kernel/config-4.19.75
$ADB -s $DEV pull /vendor/lib/modules modules/
```

## 2. Audit the attack surface

```bash
adb -s $DEV shell dumpsys package > pkg_dump_now.txt    # uid map input
python3 scripts/sweep_components.py    # exported-unguarded components BY UID
python3 scripts/dump_actions.py        # their intent-filter actions
python3 scripts/sweep_secrets.py        # credential sweep (expect: clean)
```

The output that mattered: **13 system-uid packages with 37 exported components and no
manifest guard** — including `com.sony.dtv.usbmsgservice` and the node runtimes.

## 3. Read the code that handles USB packages

```bash
jadx -d decompiled/NodeRuntimePrivilege --no-res device-fs/system/priv-app/NodeRuntimePrivilege/NodeRuntimePrivilege.apk
```

Key files (all under `sources/com/sony/dtv/b2b/noderuntime/`):

| File | What it tells you |
|---|---|
| `receiver/UsbDetector.java` | single-BPK path skips pincode + hotel-mode gates; rewrites `/storage/`→`/mnt/media_rw/` |
| `appinstaller/AppInstallerUtil.java` | `isBpkPkgFile()` = 8-byte magic `EAIP\0\0\1\0`, nothing else |
| `appinstaller/AppInstallerPackageHeader.java` | full BPK format: magic, version=256, RSA-wrapped AES keys, JSON metadata, encrypted TGZ body |
| `appinstaller/AppInstallerCore.java` | key comes from `ProSettings.decryptPhrase`; body decrypts to a `.tgz` |
| `AndroidManifest.xml` | the permission set (WRITE_SECURE_SETTINGS, MASTER_CLEAR, REBOOT, …) |

## 4. Extract a legitimate BPK

Sony ships four, inside the runtime APK itself:

```bash
unzip device-fs/system/priv-app/NodeRuntimePrivilege/NodeRuntimePrivilege.apk \
  "assets/preinstall/com.sony.tv.b2b.bravia-web-control-ui/extapp_installer.pkg"
# → assets/preinstall/com.sony.tv.b2b.bravia-web-control-ui/extapp_installer.pkg
xxd assets/preinstall/*/extapp_installer.pkg | head -1
# 00000000: 4541 4950 0000 0100 ...        ← "EAIP" + version 256
```

## 5. Enable the chain's dependencies (order matters — the log tells you)

```bash
for p in com.sony.dtv.b2b.noderuntime.privilege \
         com.sony.dtv.b2b.noderuntime.normal \
         com.sony.dtv.b2b.noderuntimeextension.node_20_11_1 \
         com.sony.dtv.b2b.prosettings \
         com.sony.dtv.webapi.core; do
  adb -s $DEV shell pm enable $p
done
```

If you skip one, the chain fails with a precise signature (observed):

| Missing package | Failure log |
|---|---|
| prosettings | `Public key decryption fail. Old key is used as substitute.` → `AESDecryptByRSA = -1` |
| noderuntime.normal | `ActivityNotFoundException: ...noderuntime.normal/...PermissionActivity` (consent dialog crashes instantly) |
| webapi.core | `WebApiToken: ConnectException: Failed to connect to /127.0.0.1:80` (runtime crash-loop in recovery) |

## 6. Stage and fire

```bash
# stick must be FAT32, plugged in; find its volume:
adb -s $DEV shell sm list-volumes          # e.g. public:8,0 mounted 2218-68D6

# stage the package
adb -s $DEV push assets/preinstall/com.sony.tv.b2b.bravia-web-control-ui/extapp_installer.pkg \
  /storage/2218-68D6/extapp_installer.pkg

# fire: remount the volume through vold (a REAL mount event — or just replug the stick)
adb -s $DEV shell sm unmount public:8,0
sleep 3
adb -s $DEV shell sm mount public:8,0
```

**Watch the screen.** The Vewd consent UI appears
("sony bravia web control ui 1.1.8 is ready to install — OK / Cancel").
Tap **OK**. The TV installs, then force-reboots.

## 7. Verify

```bash
# node app auto-started at boot, as uid 10033:
adb -s $DEV shell "logcat -d | grep execNodeAsSharedlib"
#   NodeProcess:: execNodeAsSharedlib: auid:name = bravia-web-control-ui
adb -s $DEV shell "ps -A | grep NodeProcessService"

# nginx reverseproxy now owns port 80 (uid 2900):
adb -s $DEV shell "cat /proc/net/tcp | grep ':0050 '"

# the API, from any LAN machine:
curl -X POST http://<tv-ip>/sony/avContent -H 'Content-Type: application/json' \
  -d '{"method":"getCurrentExternalInputsStatus","params":[],"id":1,"version":"1.0"}'
# → {"result":[[{"uri":"extInput:hdmi?port=1","title":"HDMI 1", ... }]],"id":1}
```

Toggle or shut it all down with `scripts/webstack-toggle.sh`.

## What this does NOT give you

- Arbitrary package execution — crafting a new BPK needs Sony's RSA private key
  (body keys are RSA-wrapped; only replay of existing signed packages works).
- Root — see FINDINGS §6 and [KERNEL_TRIAGE.md](../KERNEL_TRIAGE.md) for the walls
  that held.
