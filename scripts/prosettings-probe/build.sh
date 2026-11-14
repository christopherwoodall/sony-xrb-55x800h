#!/bin/bash
# Build the ProSettings probe APK (adapts the HelloGlass recipe).
set -euo pipefail
export PATH="$(brew --prefix)/opt/openjdk@17/bin:$PATH"
ROOT="$HOME/google-glasses"
BT="$ROOT/tools/android-14"
PLAT="$ROOT/tools/android-4.4.2"
cd "$(dirname "$0")"

if [ ! -f probe.keystore ]; then
  keytool -genkeypair -keystore probe.keystore -alias probe -keyalg RSA -keysize 2048 \
    -validity 1000 -storepass android -keypass android \
    -dname "CN=PSProbe, O=Hermes, C=US"
fi

rm -rf build && mkdir -p build/classes
"$BT/aapt" package -f -M AndroidManifest.xml -I "$PLAT/android.jar" -F build/base.apk

javac --release 8 -classpath "$PLAT/android.jar" -d build/classes \
  $(find src -name '*.java')

find build/classes -name '*.class' > build/classlist.txt
"$BT/d8" --release --min-api 19 --lib "$PLAT/android.jar" --output build @build/classlist.txt
[ -f build/classes.dex ] || { echo "FATAL: no classes.dex"; exit 1; }

cp build/classes.dex ./classes.dex
"$BT/aapt" add build/base.apk classes.dex >/dev/null
rm classes.dex

"$BT/zipalign" -f 4 build/base.apk build/aligned.apk
"$BT/apksigner" sign --ks probe.keystore --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias probe --out PSProbe.apk build/aligned.apk
echo "=== BUILT ==="
ls -la PSProbe.apk
