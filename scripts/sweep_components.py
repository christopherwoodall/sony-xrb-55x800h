import subprocess, re, os

AAPT = "/Users/agent/google-glasses/tools/android-14/aapt"
APK_DIR = "/Users/agent/sony-xrb-55x800h-analysis/device-fs"
ELEM = re.compile(r'E: (activity|service|receiver|provider|activity-alias|intent-filter) \(line=\d+\)')
ANYATTR = re.compile(r'\s*A: ([\w:.]+)\((0x[0-9a-f]+)\)(.*)$')

# uid map from dumpsys
uid_map = {}
txt = open("/Users/agent/sony-xrb-55x800h-analysis/pkg_dump_now.txt").read()
for block in re.split(r'\n  Package \[', txt):
    name = block.split(']')[0].strip()
    m = re.search(r'userId=(\d+)', block)
    if m:
        uid_map[name] = m.group(1)

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
    pm = re.search(r'A: package="([^"]+)"', out)
    manifest_pkg = pm.group(1) if pm else "?"
    findings = []
    state = {"kind": None, "attrs": {}, "has_filter": False}

    def flush():
        k = state["kind"]
        if not k:
            return
        a = state["attrs"]
        exported = a.get("exported")
        if exported is None and state["has_filter"] and k != "provider":
            exported = "true"
        if k == "provider" and exported is None:
            exported = "true"
        if exported == "true":
            guard = a.get("permission") or a.get("readPermission") or a.get("writePermission")
            findings.append((k, a.get("name", "?"), guard or "", [a2 for a2 in state.get("actions", [])][:4]))
        state.update(kind=None, attrs={}, has_filter=False, actions=[])

    for ln in out.splitlines():
        m = ELEM.search(ln)
        if m:
            what = m.group(1)
            if what == "intent-filter":
                if state["kind"]:
                    state["has_filter"] = True
                    state.setdefault("actions", [])
                continue
            flush()
            state["kind"] = what
            continue
        am = ANYATTR.match(ln)
        if am and state["kind"]:
            key, val = am.group(1).replace("android:", ""), parse_val(am.group(3))
            if key == "name" and "name" not in state["attrs"]:
                state["attrs"]["name"] = val
            elif key == "action" and state["has_filter"]:
                state["actions"].append(val)
            elif key in ("permission", "readPermission", "writePermission", "exported"):
                state["attrs"][key] = val
    flush()
    return manifest_pkg, findings

rows = []
for root, dirs, files in os.walk(APK_DIR):
    for f in files:
        if f.endswith(".apk"):
            rows.append(os.path.join(root, f))

by_uid = {}
for apk in sorted(rows):
    try:
        mpkg, finds = audit(apk)
    except Exception as e:
        print("ERR " + apk + ": " + str(e))
        continue
    uid = uid_map.get(mpkg, "?")
    unguarded = [x for x in finds if x[2] == ""]
    by_uid.setdefault((uid, mpkg), (apk, unguarded, len(finds)))

print("=== EXPORTED-UNGUARDED components by owning uid (gold = 1000/0) ===")
for (uid, mpkg), (apk, unguarded, total) in sorted(by_uid.items(), key=lambda kv: (kv[0][0] != "1000", kv[0][0])):
    if not unguarded:
        continue
    star = " *** UID=" + uid + " ***" if uid in ("1000", "0") else ""
    print(f"\n{mpkg} [uid={uid}] {len(unguarded)}/{total} exported-unguarded{star}")
    for kind, name, guard, actions in unguarded:
        acts = ("  actions: " + "; ".join(actions)) if actions else ""
        print(f"   {kind} {name}{acts}")
