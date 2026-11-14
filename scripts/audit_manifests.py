import subprocess, re, os

AAPT = "/Users/agent/google-glasses/tools/android-14/aapt"
APK_DIR = "/Users/agent/.hermes/profiles/reverse-engineer/cache/scratch/apks"
ELEM = re.compile(r'E: (activity|service|receiver|provider|activity-alias|intent-filter) \(line=\d+\)')
NAMELINE = re.compile(r'\s*A: android:name\((0x[0-9a-f]+)\)(.*)$')
ANYATTR = re.compile(r'\s*A: ([\w:.]+)\((0x[0-9a-f]+)\)(.*)$')

def parse_val(rest):
    rest = rest.strip()
    if rest.startswith("="):
        rest = rest[1:]
    if rest.startswith('"'):
        return rest[1:].split('"')[0]
    m = re.match(r'\(type 0x[0-9a-f]+\)0x([0-9a-f]+)', rest)
    if m:
        h = m.group(1)
        return "true" if h == "ffffffff" else ("false" if h == "0" else "0x" + h)
    return rest

def audit(apk):
    out = subprocess.run([AAPT, "dump", "xmltree", apk, "AndroidManifest.xml"],
                         capture_output=True, text=True, timeout=60).stdout
    findings = []
    state = {"kind": None, "attrs": {}, "has_filter": False}

    def flush():
        k, a = state["kind"], state["attrs"]
        if k:
            exported = a.get("exported")
            if exported is None and state["has_filter"] and k != "provider":
                exported = "true"
            if k == "provider" and exported is None:
                exported = "true"
            if exported == "true":
                guard = a.get("permission") or a.get("readPermission") or a.get("writePermission")
                findings.append(("UNGUARDED" if not guard else "guarded", k,
                                 a.get("name", "?"), guard or ""))
        state.update(kind=None, attrs={}, has_filter=False)

    for ln in out.splitlines():
        m = ELEM.search(ln)
        if m:
            what = m.group(1)
            if what == "intent-filter":
                if state["kind"]:
                    state["has_filter"] = True
                continue
            flush()
            state["kind"] = what
            continue
        am = ANYATTR.match(ln)
        if am and state["kind"]:
            key, rest = am.group(1), am.group(3)
            key = key.replace("android:", "")
            val = parse_val(rest)
            # first value wins (nested action/data names must not overwrite component attrs)
            if key not in state["attrs"] or key in ("permission", "readPermission", "writePermission", "exported"):
                if val not in ("", None):
                    state["attrs"][key] = val
    flush()
    return findings

for f in sorted(os.listdir(APK_DIR)):
    if not f.endswith(".apk"):
        continue
    pkg = f[:-4]
    finds = audit(os.path.join(APK_DIR, f))
    hot = [x for x in finds if x[0] == "UNGUARDED"]
    print(f"\n{pkg}: {len(hot)} UNGUARDED exported / {len(finds)-len(hot)} guarded")
    for tag, kind, name, guard in finds:
        print(f"   [{tag}] {kind} {name} {guard}")
