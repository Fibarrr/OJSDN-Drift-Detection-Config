# Validation record

Validation run: 2026-10-29 (Asia/Jakarta)

| Check | Result | Evidence |
| --- | --- | --- |
| Containerlab deployment | Passed | Containerlab 0.82 `inspect` reported r1–r6 running on the Ubuntu WSL Docker Engine. |
| FRR access | Passed | `vtysh` returned FRR daemon and interface output on all six routers. |
| OSPF adjacency | Passed | Each router has two neighbors in `Full` state. |
| OSPF route learning | Passed | Each router has OSPF routes to the other five loopback `/32`s. |
| Inter-router connectivity | Passed | r1 pinged r4's loopback and r3 pinged r6's loopback: 3/3 replies for each, 0% packet loss. |
| Baseline collection and comparison | Passed | Collector wrote `artifacts/live_state.json` for six routers; detector reported zero drift. |
| Manual static-route drift smoke test | Passed | Added `203.0.113.0/24` via `10.0.23.1` on r3; detector reported one unexpected static-route object. The route was removed and a fresh collection returned zero drift. |
| Unit tests | Passed | 9 tests cover FRR JSON/config parsing, normalization, graph comparison, and drift detection. |

The manual route test changed only r3's live configuration and was reverted. `artifacts/live_state.json` is a local debugging snapshot and is ignored by Git.

## Notes and limits

- FRR's `vtysh` prints a warning because the image has no `/etc/frr/vtysh.conf`; the tested commands still return successfully and show live state.
- The previous partial lab remains in the separate Docker Desktop daemon (r1, r3, r5 running; r2, r4, r6 created). It was not stopped or removed. The validated six-router lab runs in the Ubuntu WSL Docker Engine.
- No drift remediation, automated rollback, multi-scenario experiments, or final research metrics were implemented or tested.
