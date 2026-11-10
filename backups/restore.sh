#!/usr/bin/env bash
# Restore script for Sony BRAVIA 4K UR3 (XBR-55X800H) cleanup.
# Reverts rounds 1-4 and the Private DNS ad-blocking.
#
# Usage:
#   ./backups/restore.sh              # restore everything (rounds 1-4 + dns)
#   ./backups/restore.sh --round1     # re-install the 9 round-1 removed packages
#   ./backups/restore.sh --round2     # re-enable round-2 disabled packages + reset animations
#   ./backups/restore.sh --round3     # re-enable round-3 packages (Sony launcher skin, SELECT, tvx, homekit)
#   ./backups/restore.sh --round4     # re-enable the round-4 bloat/telemetry packages
#   ./backups/restore.sh --dns-only   # only reset Private DNS
#   ./backups/restore.sh --pkgs-only  # alias for --round1
#
# Round 1 (2026-07-23): 9 packages removed via `pm uninstall -k --user 0` (APKs kept;
#   restored with `pm install-existing`).
# Round 2 (2026-07-23): 12 packages disabled via `pm disable-user --user 0` (kept
#   installed; restored with `pm enable`) + animation scales reset to 1.0.
#   NOTE 2026-11-10: com.vewd.core.service must STAY enabled — disabling it crash-loops
#   the persistent com.sony.dtv.airplayapp (see CLEANUP_REPORT.md round 3).
# Round 3 (2026-11-10): Sony launcher skin + SELECT + tvx + homekit disabled
#   (`pm enable` to revert). airplayapp/homekit auto-reinstall at boot on this firmware;
#   they only need `pm enable`, never re-install.
# Round 4 (2026-11-10): 33 bloat/telemetry packages disabled (`pm enable` to revert).
set -euo pipefail

DEV="${TV_ADB:-10.0.0.178:5555}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ADB="$HERE/platform-tools/adb"
if [ ! -x "$ADB" ] || ! "$ADB" version >/dev/null 2>&1; then
  # bundled copy is linux-x86_64; fall back to a host adb (macOS universal at this path)
  for CAND in "$HOME/google-glasses/tools/platform-tools/adb" "$(command -v adb || true)"; do
    [ -n "$CAND" ] && [ -x "$CAND" ] && "$CAND" version >/dev/null 2>&1 && ADB="$CAND" && break
  done
fi

MODE="${1:-all}"

# Round 1: removed via `pm uninstall -k --user 0` -> restore with `pm install-existing`
PKGS=(
  tv.samba.ssm
  com.sony.dtv.promos
  com.sony.dtv.demosupport
  com.sony.dtv.demosystemsupport
  com.sony.dtv.multiscreendemo
  com.sony.dtv.sonybugreportsys
  com.google.android.tv.bugreportsender
  com.google.android.feedback
  com.sony.dtv.sonyloglevelsettingsys
)

# Round 2: disabled via `pm disable-user --user 0` -> restore with `pm enable`
# vewd deliberately EXCLUDED (must stay enabled; see CLEANUP_REPORT.md round 3)
PKGS_ROUND2=(
  com.google.android.tv.assistant
  com.sony.dtv.assistantadapter
  com.sony.dtv.voicerecognitionconfirmation
  com.google.android.katniss
  com.google.android.tvrecommendations
  com.google.android.apps.mediashell
  com.sonyericsson.dlna
  com.sony.huey.dlna.module
  com.sony.huey.dlna.renderersettings
  com.google.android.play.games
  com.google.android.videos
)

# Round 3 (2026-11-10): launcher skin + sponsored content + tvx + homekit
PKGS_ROUND3=(
  com.sony.dtv.tvlaunchercustomizer
  com.sony.dtv.tvlaunchercustomizer.overlay.apporder
  com.sony.dtv.sonyselect
  com.sony.dtv.tvx
  com.sony.dtv.homekit
)

# Round 4 (2026-11-10): 33 bloat/telemetry packages
PKGS_ROUND4=(
  com.sony.dtv.customersupport
  com.sony.dtv.customersupport.provider.res
  com.sony.dtv.eulaviewer
  com.sony.dtv.helpguidecontents
  com.sony.dtv.smarthelp
  com.sony.dtv.privacypolicy
  com.sony.dtv.softwarelicense
  com.sony.dtv.bivlinfo
  com.sony.dtv.livingfit
  com.sony.dtv.notificationcenter
  com.sony.dtv.usercontext
  com.sony.dtv.seeds.iot
  com.sony.dtv.seeds.iot.remotestart
  com.sony.dtv.b2b.adminpassword
  com.sony.dtv.b2b.deviceadminsettings
  com.sony.dtv.b2b.frameworkextension
  com.sony.dtv.b2b.hotelmode
  com.sony.dtv.b2b.importexport
  com.sony.dtv.b2b.noderuntime.normal
  com.sony.dtv.b2b.noderuntime.privilege
  com.sony.dtv.b2b.noderuntimeextension.node_20_11_1
  com.sony.dtv.b2b.prosettings
  com.sony.dtv.b2b.webappruntimedrm
  com.sony.dtv.networkapp.wifidirect
  com.sony.dtv.homenetwork
  com.sony.dtv.webapi.core
  com.sony.dtv.interactivetvutil
  com.sony.dtv.interactivetvutil.output
  com.sony.dtv.tvpositionscreen
  com.sony.dtv.seconddispsetting
  com.sony.dtv.hddmgr
  com.sony.dtv.quicksetup
  com.sony.dtv.QuickSetupCustomizer
)

echo "Connecting to $DEV ..."
"$ADB" connect "$DEV" || true

restore_pkgs() {
  echo "=== Re-installing round-1 removed packages for user 0 ==="
  for p in "${PKGS[@]}"; do
    out="$("$ADB" -s "$DEV" shell pm install-existing "$p" 2>&1 | tr -d '\r')"
    printf "%-45s -> %s\n" "$p" "$out"
  done
}

restore_round2() {
  echo "=== Re-enabling round-2 disabled packages for user 0 (vewd excluded) ==="
  for p in "${PKGS_ROUND2[@]}"; do
    out="$("$ADB" -s "$DEV" shell pm enable "$p" 2>&1 | tr -d '\r')"
    printf "%-45s -> %s\n" "$p" "$out"
  done
  echo "=== Resetting animation scales to 1.0 ==="
  for k in window_animation_scale transition_animation_scale animator_duration_scale; do
    "$ADB" -s "$DEV" shell settings put global "$k" 1.0
    echo -n "  $k="; "$ADB" -s "$DEV" shell settings get global "$k"
  done
}

restore_round3() {
  echo "=== Re-enabling round-3 packages (Sony launcher skin, SELECT, tvx, homekit) ==="
  for p in "${PKGS_ROUND3[@]}"; do
    out="$("$ADB" -s "$DEV" shell pm enable "$p" 2>&1 | tr -d '\r')"
    printf "%-45s -> %s\n" "$p" "$out"
  done
  echo "NOTE: airplayapp/homekit re-install themselves at boot; they only need 'pm enable'."
}

restore_round4() {
  echo "=== Re-enabling round-4 bloat/telemetry packages ==="
  for p in "${PKGS_ROUND4[@]}"; do
    out="$("$ADB" -s "$DEV" shell pm enable "$p" 2>&1 | tr -d '\r')"
    printf "%-45s -> %s\n" "$p" "$out"
  done
}

restore_dns() {
  echo "=== Resetting Private DNS to original (off) ==="
  "$ADB" -s "$DEV" shell settings put global private_dns_mode off
  "$ADB" -s "$DEV" shell settings delete global private_dns_specifier
  echo -n "  private_dns_mode = ";      "$ADB" -s "$DEV" shell settings get global private_dns_mode
  echo -n "  private_dns_specifier = "; "$ADB" -s "$DEV" shell settings get global private_dns_specifier
}

case "$MODE" in
  --dns-only)                 restore_dns ;;
  --round1|--pkgs-only)       restore_pkgs ;;
  --round2|--enable-pkgs)     restore_round2 ;;
  --round3)                   restore_round3 ;;
  --round4)                   restore_round4 ;;
  all|*)                      restore_pkgs; restore_round2; restore_round3; restore_round4; restore_dns ;;
esac

echo "Done. A factory reset also fully restores everything."
