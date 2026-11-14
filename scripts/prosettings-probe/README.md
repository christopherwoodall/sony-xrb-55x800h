# prosettings-probe

Binds to `com.sony.dtv.b2b.prosettings/.ProSettingsService` — the exported system-uid
(uid 1000) admin service guarded only by `android.permission.WRITE_SECURE_SETTINGS`
(an adb-grantable development permission) — and exercises its interface:
`decryptPhrase` (the BPK MasterKey path), `getConfiguredWifiNetworks`,
`getIpControlPSK`, `getDeviceId`, `getSoftwareVersionDisplay`, `getMtkHotelMode`,
`getIpControlAuthentication`.

## Build

```bash
# 1. Extract the three Sony AIDL interfaces from the device (not redistributed here):
#    jadx-decompile the ProSettings APK (see ../../docs/REPRODUCE.md), then:
cp <analysis>/decompiled/ProSettings/sources/com/sony/dtv/b2b/prosettings/IProSettingsService.java \
   <analysis>/decompiled/ProSettings/sources/com/sony/dtv/b2b/prosettings/IProSettingsCallback.java \
   <analysis>/decompiled/ProSettings/sources/com/sony/dtv/b2b/prosettings/IProSettingsCallbackBytes.java \
   src/com/sony/dtv/b2b/prosettings/
# (If building against an API-19 android.jar, strip the ProxyInfo/getHttpProxy
#  method — binder transaction codes are explicit constants, safe to remove.)

# 2. Build (Glass-toolchain recipe):
./build.sh        # → PSProbe.apk
```

## Install + run

```bash
adb -s 10.0.0.178:5555 install -r PSProbe.apk
adb -s 10.0.0.178:5555 shell pm grant com.hermes.prosettingsprobe \
  android.permission.WRITE_SECURE_SETTINGS
adb -s 10.0.0.178:5555 shell am start -n com.hermes.prosettingsprobe/.ProbeActivity
adb -s 10.0.0.178:5555 shell logcat -d | grep PSProbe
```

## Verified results (2026-11-13, hardware)

- `bindService -> true`; `BOUND to ProSettingsService` — an adb-installed untrusted
  app binds to the uid-1000 service using the shell-granted permission.
- `getConfiguredWifiNetworks` → full saved-network list (SSIDs, WPA config,
  randomized MACs, association counts; PSKs masked by `toString()`).
- `getIpControlPSK` → empty (no PSK configured); `getDeviceId` → device MAC;
  `getSoftwareVersionDisplay` → `PKG6.6230.0725NAA`; `getMtkHotelMode` → off.
- `decryptPhrase("MasterKey", …)` → `{"success":false}` — the native `b2bcmd
  decrypt_phrase` invocation refused (semantics under investigation).

## Cleanup

```bash
adb shell pm revoke com.hermes.prosettingsprobe android.permission.WRITE_SECURE_SETTINGS
adb uninstall com.hermes.prosettingsprobe
```
