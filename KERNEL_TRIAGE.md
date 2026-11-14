# Kernel CVE triage — LinPEAS-style baseline (2026-11-13)

Target: Linux 4.19.75 SMP PREEMPT armv8l (32-bit userland), built 2026-04-08 by Sony,
SPL 2026-02-01. Evidence: `config-4.19.75` (full /proc/config.gz), lsmod, getprop,
sysctl probes, cached modules in `device-fs/vendor/lib/modules/`.

## IMPORTANT: sublevel ≠ patch status

Sony backports fixes into their own 4.19.75 base without bumping the sublevel
(4.19.75 = ~Sep-2019 upstream numbering, binary built Apr 2026). The vendor claim to
test against is SPL 2026-02-01 (all Android Security Bulletins through Feb 2026
presumably applied). Any CVE fixed upstream AFTER Feb 2026 is a live candidate.

## Primitive availability (from /proc/config.gz)

| Primitive | Status | Consequence |
|---|---|---|
| CONFIG_USERFAULTFD | **not set** | userfaultfd-race LPE class dead |
| CONFIG_SYSVIPC | **not set** | SysV sem/shm primitives dead |
| CONFIG_FUSE | **not set** | FUSE-class dead |
| CONFIG_DEVMEM/DEVKMEM/PROC_KCORE | **not set** | no memory-disclosure shortcuts |
| CONFIG_KEXEC / KEXEC_SIG | **not set** | no kexec path |
| CONFIG_CHECKPOINT_RESTORE | not set | no memfd/prctl tricks |
| CONFIG_MAGIC_SYSRQ | not set | — |
| CONFIG_BPF_SYSCALL=y, BPF_JIT=y | **present** | eBPF reachable IF unprivileged |
| CONFIG_PERF_EVENTS=y | present | perf_event_paranoid=3 → unprivileged perf fully locked |
| CONFIG_COMPAT=y | present | 32-bit compat syscall surface open (userspace IS 32-bit) |
| CONFIG_MODULES=y | present | insmod needs CAP_SYS_ADMIN — not reachable from shell |
| AF_ALG (CRYPTO_USER_API) | **not set** | CVE-2025-39964 / Copy-Fail (CVE-2026-31431) dead |
| AF_RXRPC | **not set** | DirtyFrag (CVE-2026-43284/43500) / DirtyDecrypt (CVE-2026-31635) dead |
| NET_ACT_PEDIT | **not set** | pedit COW (CVE-2026-46331) dead |

Note on the 2026 COW/zero-copy LPE wave (Copy Fail, DirtyFrag, Fragnesia,
DirtyDecrypt, pedit COW, DirtyClone): every public PoC also pivots on corrupting the
page cache of a setuid `su` — this TV has ZERO setuid binaries, and root-executed code
lives on dm-verity partitions (corrupted page cache triggers verity errors). Even with
a working primitive, the classic finisher does not apply.

## Hardening (all present)

RANDOMIZE_BASE (KASLR), ARM64_SW_TTBR0_PAN (emulated PAN), STACKPROTECTOR_STRONG,
REFCOUNT_FULL, HARDENED_USERCOPY, STRICT_KERNEL_RWX, STRICT_MODULE_RWX, SELinux
(enforcing), SECCOMP+FILTER. Sysctl reads themselves are SELinux-denied to shell
(kptr/dmesg/unprivileged_bpf) — hardened state disclosure.

## Ranked leads (next session)

1. **Custom Sony/MTK drivers** — `dtv_driver.ko` (13.6MB, loaded [permanent], 19 users),
   `sony_pqctrl`/`sony_aqctrl`/`sony_bootlockctrl` (NO .ko reachable — loaded from
   outside Android; live /proc/driver/sony_pqctrl + /sys/module interfaces). Zero
   public audit history. Biggest unaudited surface on the device.
2. **mali_kbase r21p0** (Bifrost, 458KB, used by 14) — Mali has a rich public LPE CVE
   history; cross-reference r21p0 against Arm advisory tables (CVE-2021-39793 and
   neighbours — verify affected-version ranges before believing any hit).
3. **eBPF verifier** — BPF_SYSCALL=y, JIT on; unprivileged_bpf_disabled status UNKNOWN
   (sysctl read denied). If unprivileged BPF is allowed, the 4.19-era verifier bug
   class (e.g. CVE-2021-3444 — full LPE on 4.19.19) becomes testable; SPL 2026-02
   suggests patched, but only a live bpf() probe (needs an armv7 test binary / NDK)
   confirms. Also BPF_JIT not ALWAYS_ON.
4. **Post-Feb-2026 upstream 4.19 regressions** — monitor 4.19.x stable for LPE fixes
   disclosed after SPL 2026-02-01; anything not backported by Sony is live.
5. **Root native daemons** (binaries SELinux-denied to shell — need root or a firmware
   dump to audit): airplayptp, idds, iddd, precisiontime, crashlog,
   vendor.mediatek.tv.* services.
6. **compat (32-bit) syscall layer** — armv8l userspace means every syscall enters via
   compat paths; historically softer than native arm64.

## Method notes

- sysctl reads: SELinux-denied to shell (can't even read kptr_restrict).
- dmesg: klogctl denied. /proc/kallsyms: denied. kptr+klog hidden = no symbol leaks.
- World-writable /sys/module/*/parameters: none found.
- No setuid binaries → 2026 COW-class finisher (corrupt su page cache) inapplicable.
