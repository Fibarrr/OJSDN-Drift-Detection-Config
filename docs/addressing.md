# Ring topology addressing plan

The six FRR routers form one ring. Each point-to-point link uses a `/30` from `10.0.0.0/8`; router IDs and loopbacks use `10.255.0.0/24`. All links and loopbacks are advertised in OSPF area `0.0.0.0`. The Containerlab management interface `eth0` is outside the intended data-plane graph.

| Link | Prefix | Router endpoint | Address |
| --- | --- | --- | --- |
| r1–r2 | `10.0.12.0/30` | r1 `eth1` | `10.0.12.1/30` |
|  |  | r2 `eth1` | `10.0.12.2/30` |
| r2–r3 | `10.0.23.0/30` | r2 `eth2` | `10.0.23.1/30` |
|  |  | r3 `eth1` | `10.0.23.2/30` |
| r3–r4 | `10.0.34.0/30` | r3 `eth2` | `10.0.34.1/30` |
|  |  | r4 `eth1` | `10.0.34.2/30` |
| r4–r5 | `10.0.45.0/30` | r4 `eth2` | `10.0.45.1/30` |
|  |  | r5 `eth1` | `10.0.45.2/30` |
| r5–r6 | `10.0.56.0/30` | r5 `eth2` | `10.0.56.1/30` |
|  |  | r6 `eth1` | `10.0.56.2/30` |
| r6–r1 | `10.0.61.0/30` | r6 `eth2` | `10.0.61.1/30` |
|  |  | r1 `eth2` | `10.0.61.2/30` |

| Router | OSPF router ID | Loopback |
| --- | --- | --- |
| r1 | `10.255.0.1` | `10.255.0.1/32` |
| r2 | `10.255.0.2` | `10.255.0.2/32` |
| r3 | `10.255.0.3` | `10.255.0.3/32` |
| r4 | `10.255.0.4` | `10.255.0.4/32` |
| r5 | `10.255.0.5` | `10.255.0.5/32` |
| r6 | `10.255.0.6` | `10.255.0.6/32` |

Interface MTU follows the current Containerlab Linux-node default: `9500` on veth links and `65536` on loopbacks. These values are recorded in `intent/baseline.yml` and checked by the drift detector.
