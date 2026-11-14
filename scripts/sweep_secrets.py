import subprocess, os, re, zipfile

APK_DIR = "/Users/agent/sony-xrb-55x800h-analysis/device-fs"
OUT = "/Users/agent/sony-xrb-55x800h-analysis/sweep"
os.makedirs(OUT + "/extracted", exist_ok=True)

SECRET_PATTERNS = [
    (r"psk=", "WIFI_PSK"),
    (r"password\s*[:=]\s*['\"]?[A-Za-z0-9!@#$%^&*]{6,}", "PASSWORD"),
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", "API_KEY"),
    (r"(?i)secret\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", "SECRET"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "PRIVATE_KEY"),
    (r"(?i)(authorization|basic)\s+basic\s+[A-Za-z0-9+/=]{16,}", "BASIC_AUTH"),
    (r"[a-z]+://[a-z0-9_.-]+:[^@\s]{4,}@[a-z0-9_.-]+", "URL_CREDS"),
    (r"(?i)client_secret\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", "CLIENT_SECRET"),
]
INTERESTING_ASSET = re.compile(r"\.(pem|jks|keystore|bks|p12|pfx|key|conf|properties|json|db|sqlite|xml)$", re.I)
SKIP_STRINGS = re.compile(r"(password_hint|PASSWORD_HINT|has_password|password_[a-z_]*color|wrong_password|prompt_password|set_password|no_password|password_toggle|icon_password|change_password|account_password|password_length|password_strength|invalid_password|password_required|enter_password|password_hint_text|password_don_t|recover_password|forgot|action_set_password|action_clear_password)", re.I)

hits_by_pkg = {}
asset_hits = {}

for root, dirs, files in os.walk(APK_DIR):
    for f in files:
        if not f.endswith(".apk"):
            continue
        apk = os.path.join(root, f)
        pkg = f[:-4]
        exd = os.path.join(OUT, "extracted", pkg)
        if not os.path.isdir(exd):
            try:
                with zipfile.ZipFile(apk) as z:
                    z.extractall(exd)
            except Exception as e:
                print(f"UNZIP-FAIL {pkg}: {e}")
                continue
        # grep extracted tree for secret patterns
        for dirpath, _, fnames in os.walk(exd):
            for fn in fnames:
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 30 * 1024 * 1024:
                        continue
                    data = open(p, "rb").read()
                except Exception:
                    continue
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                for pat, tag in SECRET_PATTERNS:
                    for m in re.finditer(pat, text):
                        s = m.group(0)
                        if tag in ("PASSWORD", "SECRET") and SKIP_STRINGS.search(s):
                            continue
                        rel = os.path.relpath(p, exd)
                        hits_by_pkg.setdefault(pkg, set()).add(f"{tag}: {s[:100]} ({rel})")
                if INTERESTING_ASSET.search(fn):
                    rel = os.path.relpath(p, exd)
                    sz = os.path.getsize(p)
                    if sz < 2 * 1024 * 1024 and fn.lower().endswith((".pem", ".jks", ".keystore", ".bks", ".p12", ".pfx", ".key")):
                        asset_hits.setdefault(pkg, set()).add(f"KEYSTORE/CERT FILE: {rel} ({sz}b)")

print("=== SECRET PATTERN HITS ===")
for pkg, hits in sorted(hits_by_pkg.items()):
    print(f"\n{pkg}:")
    for h in sorted(hits)[:12]:
        print("   " + h)
print("\n=== KEYSTORE/CERT FILES ===")
for pkg, hits in sorted(asset_hits.items()):
    for h in sorted(hits):
        print(f"{pkg}: {h}")
