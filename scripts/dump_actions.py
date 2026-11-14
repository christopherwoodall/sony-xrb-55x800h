import subprocess, re, os

AAPT = "/Users/agent/google-glasses/tools/android-14/aapt"
APK_DIR = "/Users/agent/.hermes/profiles/reverse-engineer/cache/scratch/apks"
TARGETS = ["com.sony.dtv.update", "com.sony.dtv.usbmsgservice", "mtktvapi.agent",
           "com.sony.dtv.preinappfiltering", "com.sonyericsson.idd.agent",
           "com.sony.dtv.remotecontrolsettings", "com.sony.dtv.sonysystemservice",
           "com.mediatek.agent"]
ELEM = re.compile(r'E: (activity|service|receiver|provider|activity-alias|intent-filter|action) \(line=\d+\)')
ANYATTR = re.compile(r'\s*A: ([\w:.]+)\((0x[0-9a-f]+)\)(.*)$')

def parse_val(rest):
    rest = rest.strip()
    if rest.startswith("="):
        rest = rest[1:]
    if rest.startswith('"'):
        return rest[1:].split('"')[0]
    return rest

for pkg in TARGETS:
    apk = os.path.join(APK_DIR, pkg + ".apk")
    if not os.path.exists(apk):
        continue
    out = subprocess.run([AAPT, "dump", "xmltree", apk, "AndroidManifest.xml"],
                         capture_output=True, text=True, timeout=60).stdout
    state = {"kind": None, "name": None, "in_filter": False, "actions": []}
    print("\n### " + pkg)

    def flush():
        k = state["kind"]
        if k and state["actions"]:
            print(f"  {k} {state['name'] or '?'}")
            for a in state["actions"]:
                print("      action: " + a)
        state.update(kind=None, name=None, in_filter=False, actions=[])

    for ln in out.splitlines():
        m = ELEM.search(ln)
        if m:
            what = m.group(1)
            if what == "intent-filter":
                state["in_filter"] = True
                state["actions"] = []
                continue
            if what == "action":
                continue
            flush()
            state["kind"] = what
            continue
        if state["in_filter"] and state["kind"] is None:
            continue
        am = ANYATTR.match(ln)
        if am:
            key, val = am.group(1).replace("android:", ""), parse_val(am.group(3))
            if key == "name" and not state["in_filter"]:
                state["name"] = val
            elif key == "name" and state["in_filter"]:
                state["actions"].append(val)
    flush()
