# scripts/

Analysis + operations tooling for the XBR-55X800H campaign. All Python scripts are
**host-side** (run on your Mac against the cached artifacts) and assume the artifact
layout from [docs/REPRODUCE.md](../docs/REPRODUCE.md) — adjust the `APK_DIR` /
analysis-dir constants at the top of each file to match your machine.

| Script | What it does |
|---|---|
| `audit_manifests.py` | Parse every cached APK's `AndroidManifest.xml` (aapt xmltree) and list exported components with/without permission guards. This found the 35 unguarded system-uid components. |
| `sweep_components.py` | Same audit across all APKs, joined with per-package **uid** from a `dumpsys package` snapshot — the `*** UID=1000 ***` view that ranks targets. |
| `dump_actions.py` | Dump each exported component's intent-filter **actions** — the entry protocol for every receiver we later triggered. |
| `sweep_secrets.py` | Unzip + regex sweep for credentials/keys across all APKs (result on this build: clean; Sony build-redacts private keys). |
| `webstack-toggle.sh` | **Operations**: enable/disable/status for the installed web-control stack (node runtimes + prosettings + webapi.core → nginx + Sony JSON-RPC API on port 80). |

## Requirements

- `aapt` + `dexdump` (old build-tools work fine; we used android-14-era binaries)
- `jadx` (`brew install jadx`) for decompilation
- `unzip`, `strings`, standard shell
- Network ADB to the TV (`~/google-glasses/tools/platform-tools/adb` or any adb ≥ 30)

## Typical flow

```bash
# 1. snapshot package state from the TV
adb -s 10.0.0.178:5555 shell dumpsys package > pkg_dump_now.txt

# 2. audit the cached APKs for exported-unguarded components, by uid
python3 sweep_components.py

# 3. read the winner's entry protocol
python3 dump_actions.py

# 4. decompile and read the code
jadx -d out/ --no-res path/to/target.apk
```
