#!/usr/bin/env bash
# webstack-toggle.sh — turn the Sony web-control stack (installed via the USB BPK
# chain, see docs/FINDINGS.md) on or off.
#
# ON  = noderuntime.privilege/normal/extension + prosettings + webapi.core enabled
#       → node apps run, nginx reverseproxy serves 0.0.0.0:80, /sony/* API live
# OFF = all five disabled → node apps stop, nginx exits, API closes
#       (the installed bravia-web-control-ui stays on disk, inert)
#
# Usage: ./scripts/webstack-toggle.sh on|off|status
set -euo pipefail

ADB="${ADB:-$HOME/google-glasses/tools/platform-tools/adb}"
DEV="${TV_ADB:-10.0.0.178:5555}"
PKGS=(
  com.sony.dtv.b2b.noderuntime.privilege
  com.sony.dtv.b2b.noderuntime.normal
  com.sony.dtv.b2b.noderuntimeextension.node_20_11_1
  com.sony.dtv.b2b.prosettings
  com.sony.dtv.webapi.core
)

"$ADB" connect "$DEV" >/dev/null 2>&1 || true

case "${1:-status}" in
  on)
    for p in "${PKGS[@]}"; do
      "$ADB" -s "$DEV" shell pm enable "$p" | tr -d '\r'
    done
    echo "-- stack enabled; nginx + node apps start on next boot or USB event"
    ;;
  off)
    for p in "${PKGS[@]}"; do
      "$ADB" -s "$DEV" shell pm disable-user --user 0 "$p" | tr -d '\r'
    done
    echo "-- stack disabled; API port 80 closes within seconds"
    ;;
  status)
    echo "packages:"
    for p in "${PKGS[@]}"; do
      if "$ADB" -s "$DEV" shell pm list packages -d 2>/dev/null | tr -d '\r' | grep -q "$p"; then
        echo "  DISABLED  $p"
      else
        echo "  enabled   $p"
      fi
    done
    echo "port 80 listener: $("$ADB" -s "$DEV" shell "cat /proc/net/tcp 2>/dev/null | grep -c ':0050 .*0A'" | tr -d '\r') (nginx)"
    echo "node process:    $("$ADB" -s "$DEV" shell "ps -A | grep -c NodeProcessService" | tr -d '\r') running"
    curl -sm 3 -o /dev/null -w "avContent API:   HTTP %{http_code}\n" \
      -X POST "http://$(echo "$DEV" | cut -d: -f1)/sony/avContent" \
      -H 'Content-Type: application/json' \
      -d '{"method":"getCurrentExternalInputsStatus","params":[],"id":1,"version":"1.0"}' \
      || echo "avContent API:   unreachable (stack off?)"
    ;;
  *)
    echo "usage: $0 on|off|status" >&2; exit 1 ;;
esac
