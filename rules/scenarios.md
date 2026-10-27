# NL → YAML scenarios (coverage)

Agent brief: map natural-language integration intent to the **smallest** YAML edit, then validate. Full legality: `integration_rules.md`. Schemas: `schemas/`.

**连连看（优先）：** 模糊 / 多段意图先打开 [`nl_field_map.md`](nl_field_map.md) — 左列人话短语 ↔ 右列 Must/Optional 字段路径 ↔ Done。起手 prompt：[`prompts/scenario_match.md`](../prompts/scenario_match.md)。本文件 S1–S11 是同一套场景的展开说明。

## Done checks (every scenario)

1. Touched YAML still schema-valid (`tools/validate.py` exit 0).
2. No invented ports/widths/protocols outside YAML.
3. Report: files changed + validator summary (+ RTL/glue paths if generated).
4. Address / clock / reset / CDC intent reflected in YAML when the human asked for them.

---

## S1 — Add an IP

| | |
|--|--|
| **Human** | “Add a UART (APB).” |
| **Edit** | New or reuse `ip/<name>.yaml`; add `instances[]` entry in `subsys` or `soc`. |
| **Fields** | `kind: ip`, `ports`/`clocks`/`resets`/`parameters`; instance `id` + `ip`/`ref`. |
| **Done** | Instance resolves; required clocks/resets driven at SoC (or marked intentional). |

## S2 — Bundle connect

| | |
|--|--|
| **Human** | “Hook the whole APB slave bundle to the fabric.” |
| **Edit** | Ensure IP/export ports share `bundle: <id>` (e.g. `apb_s`); SoC/subsys `connections[]` with `kind: bundle` (or per-signal `kind: port`). |
| **Fields** | `port.bundle`, `connections[].kind: bundle` \| `port`. |
| **Example** | `demo_soc`: `host0.bundle:apb_m` → `periph0.bundle:apb_s` (`kind: bundle`); host IP `examples/ip/apb_host_stub.yaml`. |
| **Done** | Every port in that bundle on the sink is driven/exported; widths/protocols agree; same `bus_role` within the bundle; validator cross-file closure passes. |

## S3 — Address window

| | |
|--|--|
| **Human** | “Map peripherals at 0x4000_0000.” |
| **Edit** | `soc.address_map` (absolute `base`) and/or `subsys.address_map` (relative `base_offset`). |
| **Fields** | `region`/`base`/`size_bytes`/`target`; child `instance`/`base_offset`/`size_bytes`. |
| **Done** | No unexplained overlaps; window covers child maps. |

## S4 — Clock / reset

| | |
|--|--|
| **Human** | “Drive the island from sys_clk / sys_rstn.” |
| **Edit** | `soc.clock_tree` / `reset_tree` + `connections` from `clock:` / `reset:` to instance clock/reset ports. Optional `port.clock_domain` aligned with the clock name. |
| **Fields** | `clock_tree`, `reset_tree`, `connections`, `port.clock_domain`. |
| **Done** | Polarity matches sink; domains consistent unless `cdc` marks a crossing. |

## S5 — IRQ

| | |
|--|--|
| **Human** | “Wire UART IRQ to the pad / controller.” |
| **Edit** | Ensure IP has `protocol: irq` port; `soc.connections` (and `pads` if off-chip). |
| **Fields** | `ports` (+ optional `bundle`), `connections`, `pads`. |
| **Done** | Width 1 (unless specified); endpoint resolves. |

## S6 — Pad

| | |
|--|--|
| **Human** | “Connect UART TX/RX to pads.” |
| **Edit** | Declare `pads[]`; `connections` using `pad:<name>`. |
| **Fields** | `pads`, `connections.from`/`to`. |
| **Done** | Pad dirs match net intent; widths match. |

## S7 — CDC-marked path

| | |
|--|--|
| **Human** | “This IRQ crosses from pclk to aon_clk — mark CDC.” |
| **Edit** | Set `clock_domain` on both ends; set `cdc: crossing` or `async_handshake` on the crossing port(s) and/or note on the connection. |
| **Fields** | `port.clock_domain`, `port.cdc` (`none`\|`crossing`\|`async_handshake`\|`unknown`). |
| **Example** | `examples/soc/demo_soc.yaml` (`aon_clk` + `periph0.irq_uart` → `pad:irq_uart_aon`); source marks in `examples/subsys/periph_apb.yaml` / `examples/ip/uart_apb.yaml`. Intent markup only — **not** signoff-grade CDC. |
| **Done** | Differing domains without `cdc` in {`crossing`,`async_handshake`,`unknown`} → treat as error; intentional crossings documented. |


## S9 — Fabric address decode

| | |
|--|--|
| **Human** | “CPU mem bus decodes to RAM / flash / UART with ready OR.” |
| **Edit** | SoC `fabric[]` with `kind: decode_mux`, `master`, `slaves[].match`, `ready_merge` / `rdata_merge`. |
| **Fields** | `fabric`, optional `adapters` on slaves. |
| **Example** | `pilots/picosoc/soc/picosoc.yaml` (`mem_decode`); light demo in `examples/soc/demo_soc.yaml`. |
| **Done** | Schema + fabric checks pass; overlapping windows have `note`. No HDL claimed. |

## S10 — Heterogeneous slave adapter

| | |
|--|--|
| **Human** | “SPI flash is 24-bit addr, no wdata — don't fake a full mem bundle.” |
| **Edit** | `adapters[]` (`partial_map` / `width_remap` / `bridge`) + `fabric.slaves[].adapter`. |
| **Fields** | `maps.from_role` → `to_port`, `width_from`/`width_to`, `omit_from_roles`. |
| **Example** | PicoSoC `mem_to_spimemio` / `mem_to_sram` / `mem_to_uart_reg`. |
| **Done** | Target ports exist; widths consistent; intentional omissions listed. |

## S11 — Bit-slice IRQ / GPIO

| | |
|--|--|
| **Human** | “Wire pad irq_5 into cpu.irq[5].” |
| **Edit** | Connection `from: pad:irq_5` → `to: cpu.irq[5]` with `width: 1`. |
| **Fields** | Endpoint slice `[N]` or `[M:N]`. |
| **Done** | Slice in range; effective widths match. |

## S8 — Parameter override

| | |
|--|--|
| **Human** | “FIFO depth 32.” |
| **Edit** | Instance `parameters` in subsys/soc; key must exist on IP `parameters`. |
| **Fields** | IP `parameters.<NAME>`, instance `parameters`. |
| **Done** | No unknown parameter names; type-compatible with IP contract. |

---

## Quick index

| Intent | Primary file(s) |
|--------|-----------------|
| Add IP | `ip/*.yaml`, instance in `subsys`/`soc` |
| Bundle connect | `port.bundle` + `connections.kind` |
| Address window | `address_map` |
| Clk/rst | `clock_tree`/`reset_tree` + connections |
| IRQ / pad | `ports` + `connections` + `pads` |
| CDC | `clock_domain` + `cdc` |
| Param | instance `parameters` |
| Decode fabric | SoC `fabric` |
| Hetero adapt | `adapters` + fabric slave |
| Bit-slice | `port[N]` / `port[M:N]` |
