#!/usr/bin/env bash
# Restore script for Sony BRAVIA 4K UR3 (XBR-55X800H) cleanup.
# Reverts both rounds of changes and the Private DNS ad-blocking.
#
# Usage:
#   ./backups/restore.sh              # restore everything (round1 + round2 + dns)
#   ./backups/restore.sh --round1     # re-install the 9 round-1 removed packages
#   ./backups/restore.sh --round2     # re-enable 12 round-2 disabled packages + reset animations
#   ./backups/restore.sh --dns-only   # only reset Private DNS
#   ./backups/restore.sh --pkgs-only  # alias for --round1
#
# Round 1 (2026-07-23): 9 packages removed via `pm uninstall -k --user 0` (APKs kept;
#   restored with `pm install-existing`).
# Round 2 (2026-07-23): 12 packages disabled via `pm disable-user --user 0` (kept
#   installed; restored with `pm enable`) + animation scales reset to 1.0.
set -euo pipefail

DEV="${TV_ADB:-10.0.0.178:5555}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
ADB="$HERE/platform-tools/adb"
[ -x "$ADB" ] || { echo "adb not found at $ADB"; exit 1; }

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
  com.vewd.core.service
  com.google.android.play.games
  com.google.android.videos
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
  echo "=== Re-enabling round-2 disabled packages for user 0 ==="
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
  all|*)                      restore_pkgs; restore_round2; restore_dns ;;
esac

echo "Done. A factory reset also fully restores everything."
