# CLEANUP_REPORT.md — moved

This document grew through twelve rounds of investigation and has been restructured.

- **Current device state + runbook** → [docs/OPERATIONS.md](docs/OPERATIONS.md)
- **Findings showcase** (USB BPK chain, dual-OS boundary, crash-loop forensics,
  Paramount+/Conviva, mic lockdown) → [docs/FINDINGS.md](docs/FINDINGS.md)
- **Full reproduction guide** (toolchain → cached artifacts → the USB BPK chain,
  end to end) → [docs/REPRODUCE.md](docs/REPRODUCE.md)
- **Kernel CVE triage** → [KERNEL_TRIAGE.md](KERNEL_TRIAGE.md)
- **The complete round-by-round history, verbatim** →
  [docs/history/ROUNDS.md](docs/history/ROUNDS.md)

The old filename is kept so existing links keep resolving; `git log --follow
docs/history/ROUNDS.md` shows the full lineage.
