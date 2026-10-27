# MoonGlass_Integration — Agent brief (canonical)

You are assembling / wiring a chip design from **YAML contracts**, not inventing a new integration product.

Working title was sometimes misspelled *MoonGlass_Intergration*; the real name is **MoonGlass_Integration**.

## What you do

1. **Read schemas** under `schemas/` (`ip_interface`, `subsystem`, `soc_top`).
2. **Read / edit YAML** under the chip repo (or `examples/` here): IP interfaces → subsystems → SoC top.
3. **Validate** with `tools/validate.py` (or the same checks) before claiming done.
4. **Elaborate** top RTL / wrappers / glue **only to satisfy the YAML contracts**.
5. Natural language from the human is an **intent**; YAML is the **truth**.

## What you must not do

- Do **not** invent ports, widths, protocols, or address windows that contradict YAML.
- Do **not** treat this pack as a heavyweight integration engine. One-off helper scripts are fine; shipping a permanent “integrator product” is out of scope.
- Do **not** silently widen buses or change polarities to “make it compile”. Change the YAML (with human OK if policy requires), then regenerate.

## Workflow

```
NL request → match phrases in rules/nl_field_map.md (连连看 M1–M13)
          → identify targets (ip | subsystem | soc)
          → edit the smallest YAML set that expresses the intent (Must fields first)
          → validate (schema + connection sanity)
          → generate/update RTL wrappers / top / decode as needed
          → list evidence (files changed + validator output)
```

**连连看（减少瞎猜）：** 意图模糊或多段时，先打开 [`rules/nl_field_map.md`](rules/nl_field_map.md)：左列人话（中/英）↔ 右列必填/可选字段路径 ↔ Done。起手：[`prompts/scenario_match.md`](prompts/scenario_match.md)。细则场景卡仍见 `rules/scenarios.md`。

### Connection legality (summary)

- `from` / `to` endpoints: `instance.port` | `instance.port[N]` | `instance.port[M:N]` | `instance.bundle:<id>` | `clock:<name>` | `reset:<name>` | `pad:<name>` | `const:<value>`.
- Widths must match on **effective** width (full port or bit-slice width).
- Protocol tags on both ends should agree when both are set (e.g. `apb3`↔`apb3`).
- `port.role` = signal within protocol (`psel`/`pready`/`txd`); `port.bus_role` = `initiator`|`target`|`monitor`|`passthrough` (optional; do not overload `role`).
- Optional port attrs: `bundle`, `clock_domain`, `cdc` (`none`|`crossing`|`async_handshake`|`unknown`); connections may set `kind`: `port`|`bundle`. Bundle endpoints: `instance.bundle:<id>`. Scenarios: `rules/scenarios.md`.
- Cross-file resolve (validation only): `ref`/`ip` search order = referring dir → `--root` / `MOONGLASS_INTEGRATION_ROOTS` → pack `examples/`. Used for bundle closure + pairing — not an integrator.
- `bus_role` pairing **strategy A**: both ends filled in `{initiator,target}` → must be complementary; either omitted → OK.
- Reset polarity must match the sink IP/subsystem contract.
- Address map windows must not overlap unless marked intentional (document in `note` / `description`).
- Optional SoC `fabric[]` (`kind: decode_mux`): address windows + `ready_merge` / `rdata_merge` intent; validation only.
- Optional SoC `adapters[]` (`partial_map`|`width_remap`|`bridge`) referenced from `fabric.slaves[].adapter` for heterogeneous slaves.

Full rules: `rules/integration_rules.md`. 连连看: `rules/nl_field_map.md`. Scenarios: `rules/scenarios.md`. Starters: `prompts/scenario_match.md`, `prompts/integrate.md`.

## Evidence checklist (definition of done)

- [ ] Relevant YAML updated and still schema-valid
- [ ] `python tools/validate.py` exits 0 (or documented equivalent)
- [ ] Generated / edited RTL file list reported
- [ ] No port invented outside YAML; any contract change called out explicitly
- [ ] Address / clock / reset intent reflected in `soc_top` (or subsystem) YAML

## Where MoonGlass fits

MoonGlass may later **host / check** these descriptions and status. **This pack does not perform SoC wiring inside MoonGlass.** Any coding agent (Claude Code, Workbuddy, DeepSeek harness, Pi, Cursor, …) may execute integration by following these rules.

## 外部工具文本约束的对照（仅参考，非照搬）

业界 SoC 装配工具（IP-XACT、Synopsys coreTools、Vivado IP Integrator、Arm Socrates、LiteX/Diplomacy 等）的公开「文本约束」形态已整理在 `references/`（总览：`references/vendor_text_constraints.md`）。**商用格式可能涉及专利与知识产权；禁止复制其 schema/专有字段，也禁止宣称与某工具兼容。** 那些材料只作 prior-art 意识与对照，用来提醒「接口 / 地址窗 / 时钟复位 / 连线」等**通用意图**；本包真源永远是自研的 `schemas/` YAML。执行集成时不要改去迁就外部格式。
