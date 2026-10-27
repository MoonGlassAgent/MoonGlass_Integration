# Changelog

## 0.1.7-draft — 2026-10-27

- **定位叙事：** 说明为什么「规则包 + Agent」可在工作方式上替代传统 SoC 集成工具——传统工具（IP-XACT / BD / coreAssembler 等）本质仍是信号关系的文本/结构化描述；本包用 YAML 契约说清同样关系，由 Agent 当场 elaborator，不必养永久 GUI/集成器。**不**声称法律/专利豁免；边界仍是「非永久集成器」。
- Comic site：新增第 6 格 punchline；说明 HTML / README 补短 callout；Pages 同步。

## 0.1.6-draft — 2026-10-27

- **连连看（NL ↔ fields）：** `rules/nl_field_map.md` — match-style table: Chinese/English intent phrases → Must/Optional YAML field paths → Done checks (M1–M13: port, bundle, address map, clk/rst, pads, CDC, fabric decode_mux, adapters, bit-slice, bus_role strategy A, add IP, params, IRQ).
- Agent starter: `prompts/scenario_match.md`. Wired from `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `prompts/integrate.md`, `README.md`, `WORKBUDDY.md`, `rules/scenarios.md`.
- Docs: HTML §「连连看」+ TOC; version bump. No schema/validator changes; examples + picosoc stay green. Future-only mentions (not implemented): spimem_cfg adapter hardening, connection direction check, fabric↔connections force.


## 0.1.5-draft — 2026-10-27

- **Bit-slice endpoints:** `instance.port[N]`, `instance.port[M:N]` (and optional `pad:name[N]`). Validator checks slice bounds vs port/pad width and matches **effective** widths on connections (e.g. `pad:irq_5` → `cpu.irq[5]`). Bundles / clock / reset / const do not take slices.
- PicoSoC pilot wires `irq_5/6/7` pads into `cpu.irq[5|6|7]`.
- Docs: AGENTS / rules / HTML 说明 / pilot 实测报告「迭代」节.

## 0.1.4-draft — 2026-10-27

- **Heterogeneous adapters:** SoC-level `adapters[]` with `kind`: `partial_map` | `width_remap` | `bridge`; `maps[]` (`from_role` → `to_port`, optional `width_from`/`width_to`); `omit_from_roles` for intentional asymmetry. Referenced from `fabric[].slaves[].adapter`.
- Validator: adapter id uniqueness; `to_port` must exist on target IP; `from_role` / widths checked against fabric master when resolvable. Still **no** glue HDL.
- PicoSoC pilot: `mem_to_spimemio`, `mem_to_sram`, `mem_to_uart_reg` adapters on decode slaves.

## 0.1.3-draft — 2026-10-27

- **Fabric decode/mux:** SoC-level `fabric[]` with `kind: decode_mux`, `master`, `select: address`, `addr_role`, `ready_merge` (`or`|`priority`|`onehot`|`unknown`), `rdata_merge` (`mux_by_select`|`priority`|`unknown`), and `slaves[]` with `match.base`/`size_bytes`. Validation/docs only — not an elaborator.
- Overlapping slave windows in one fabric require a `note`.
- Demo: `examples/soc/demo_soc.yaml` adds a single-slave `apb_decode` fabric. PicoSoC pilot declares `mem_decode` covering RAM / flash / uart / iomem windows.

## 0.1.2-draft — 2026-10-27

- **9.1 Cross-file bundle closure (validation only):** `tools/validate.py` resolves `instance.ref` / `instance.ip` and checks `kind: bundle` member coverage + width/protocol across files. Path order: referring YAML dir → `--root` / `MOONGLASS_INTEGRATION_ROOTS` → pack `examples/`. Endpoint form `instance.bundle:<id>` supported. Not an elaborator / no glue HDL.
- **9.2 bus_role pairing strategy A:** when **both** ends have `bus_role` in `{initiator,target}`, require complementary `initiator`↔`target`; omit on either end → no error; `monitor` / `passthrough` do not false-fail.
- **9.3 Multi-clock CDC example:** `demo_soc` adds `aon_clk`; UART IRQ marked `cdc: crossing` from `pclk` to pad `irq_uart_aon` (intent markup only).
- Demo: `examples/ip/apb_host_stub.yaml` + SoC `kind: bundle` connect `host0.bundle:apb_m` → `periph0.bundle:apb_s`.
- Docs: HTML §9 marks 9.1–9.3 done; 9.4 / 9.5 remain intentional gaps.
- **Pilot:** `pilots/picosoc/` — YAML re-description of YosysHQ PicoSoC (picorv32 `@ef203c2`) top; custom `picorv32_mem` bundle exercises 9.1/9.2; validate 6/6 OK. Findings: `pilots/picosoc/实测报告.html`. Tests the rules pack, not a re-integrator.

## 0.1.1-draft — 2026-10-27

- Absorb pass (custom fields only): optional `port.bundle`, `port.clock_domain`, `port.cdc` (`none`|`crossing`|`async_handshake`|`unknown`); keep `role` vs `bus_role` split.
- Connections / links: optional `kind` (`port`|`bundle`).
- Rules: `rules/scenarios.md` (NL→YAML coverage); expanded `rules/integration_rules.md` (domains, CDC, bundle completeness).
- `references/ABSORBED.md` maps prior-art ideas → our fields/files.
- Validator: enum/consistency checks for new attrs; examples lightly tagged (`apb_s` / `pclk` / `cdc: none`).

## 0.1.0-draft — 2026-10-27

- Initial rules / schema / constraints pack for description-driven SoC assembly.
- JSON Schemas for IP interface, subsystem, and SoC top; minimal APB peripheral demo; agent briefs and stdlib-friendly validator.
- Optional `bus_role` on IP/subsystem ports: `initiator` | `target` | `monitor` | `passthrough`. `port.role` remains signal-within-protocol (`psel`/`pready`/`txd`); demos mark APB as `target`.
