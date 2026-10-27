# Integration rules

## Naming

| Layer | Pattern | Example |
|-------|---------|---------|
| IP `name` | `^[a-z][a-z0-9_]*$` | `uart_apb` |
| Instance `id` | same | `uart0` |
| SoC `name` | same | `demo_soc` |
| Ports | HDL-safe identifiers | `psel`, `uart_txd` |
| `bundle` / `clock_domain` | `^[a-z][a-z0-9_]*$` | `apb_s`, `pclk` |

File layout suggestion (chip repo):

```
ip/<name>.yaml
subsys/<name>.yaml
soc/<name>.yaml
```

## Ref resolution (cross-file, validation only)

`instance.ref` (SoC) / `instance.ip` (subsystem) are resolved in this order:

1. **Same directory** as the referring YAML: `<dir>/<ref>.yaml|.yml`, then `<dir>/{ip,subsys,soc}/<ref>.yaml|.yml`
2. Each **`--root`** (CLI, repeatable) and each entry in **`MOONGLASS_INTEGRATION_ROOTS`** (`os.pathsep`-separated): same patterns
3. Pack **`examples/`** fallback (`examples/{ip,subsys,soc}/`) — for demos; disable with `--no-examples-fallback`

Explicit relative paths (`subdir/name.yaml`) are tried relative to the referring dir, then each root. Missing file, kind mismatch, name≠ref, or load cycles → error. This resolve exists **only** so the validator can check bundle closure and pairing — it does **not** generate glue HDL.

## Connection legality

1. Every `connections[].from` / `to` (and subsystem `links`) must resolve to a known endpoint after elaboration:
   - `instance.port` / `instance.port[N]` / `instance.port[M:N]` — instance exists; port exists; slice within width
   - `instance.bundle:<id>` — whole bundle (no bit-slice)
   - `clock:<name>` / `reset:<name>` — declared in `clock_tree` / `reset_tree`
   - `pad:<name>` — declared in `pads`
   - `const:<value>` — only as `from` (tie-off)
2. Width on the connection (if set) must equal both **effective** endpoint widths (after bit-slice).
3. If both ends declare `protocol`, they must be equal (case-sensitive tags).
4. `role` on a port is the **signal** within a protocol (e.g. `psel`, `pready`, `txd`). Do **not** put initiator/target there. Use optional `bus_role`: `initiator` | `target` | `monitor` | `passthrough`. Ports that share one logical bus should use the same `bus_role`. **Pairing strategy A (validator):** when **both** ends of a connection/link resolve and both have `bus_role` in `{initiator,target}`, require complementary `initiator`↔`target`. If either end omits `bus_role` → **no error**. `monitor` may attach to either side; `passthrough` is a bridge — neither false-fails pairing.
5. Reset polarity of a `reset:` source must match the sink reset contract.
6. Do not leave required clocks/resets of an instance undriven unless the YAML marks them optional (default: required).
7. Optional `connections[].kind` / `links[].kind`: `port` (default) or `bundle`.
   - `port` — single endpoint pair (`instance.port`).
   - `bundle` — wire a whole group. Prefer endpoints `instance.bundle:<id>` (local bundle id on each side may differ, e.g. `apb_m`↔`apb_s`). Validator loads child YAML (see **Ref resolution** below) and checks sink members are covered by matching source members (by `role` then by port `name`), with width/protocol agreement. Incomplete coverage is an error when `kind: bundle` is used.

## Clock domains and CDC

1. Optional `port.clock_domain` tags which domain a port belongs to (often equal to a `clocks[].name` or SoC `clock_tree` name).
2. Within one `bundle` (or one `protocol` group when `bundle` is unset), prefer a **single** `clock_domain` when set. Mixed domains inside one bundle without CDC marks are illegal.
3. Optional `port.cdc`: `none` | `crossing` | `async_handshake` | `unknown`.
   - Same `clock_domain` on both ends → `cdc` should be `none` or omitted.
   - Differing `clock_domain` (or clearly async path) → set `cdc` to `crossing`, `async_handshake`, or `unknown`, and document intent (`description` / connection `note`). Untagged cross-domain links are errors.
4. `cdc: crossing` / `async_handshake` means the agent must elaborate synchronizers / handshake glue — do not silently treat as a plain wire.

## Address maps

- Subsystem `address_map` offsets are relative to the parent window.
- SoC `address_map` bases are absolute (int or `0x…` string).
- Overlaps require an explicit `description` / `note` explaining intent; otherwise treat as error when checking.


## Fabric decode / mux (SoC)

Optional `fabric[]` declares **inline address decode + ready/rdata merge intent** without generating HDL:

| Field | Meaning |
|-------|---------|
| `kind` | `decode_mux` (only value in 0.1.x) |
| `master` | `instance.port` or `instance.bundle:<id>` |
| `select` | `address` |
| `addr_role` | Role on master used for decode (e.g. `addr`, `paddr`) |
| `ready_merge` | `or` \| `priority` \| `onehot` \| `unknown` |
| `rdata_merge` | `mux_by_select` \| `priority` \| `unknown` |
| `slaves[]` | `id`, `target` (instance id), `match.base`/`size_bytes`, optional `adapter`, `note` |

Overlapping slave windows in the same fabric need a `note`. This is **not** a permanent interconnect elaborator.

## Adapters (heterogeneous slaves)

Optional `adapters[]` + `fabric.slaves[].adapter`:

| `kind` | Use |
|--------|-----|
| `partial_map` | Subset of master roles → slave ports |
| `width_remap` | Same + width change (`width_from` → `width_to`, narrowing only in validator) |
| `bridge` | Free-form Agent glue; `maps` are hints |

`omit_from_roles` lists master roles intentionally absent on the slave. Validator checks `to_port` exists on the target IP and role/width consistency when the master resolves — still no HDL.

## Bit-slice endpoints

`cpu.irq[5]`, `cpu.irq[7:5]`, optional `pad:name[N]`. Slice must fit the port/pad width; connection compares effective widths. Not allowed on `bundle:` / `clock:` / `reset:` / `const:`.

## How NL maps to YAML edits

| Human says | Prefer editing |
|------------|----------------|
| “Add a UART” | new/reuse `ip/*.yaml` + instance in subsystem or SoC |
| “Put UART+GPIO in one island” | `subsys/*.yaml` instances + `address_map` + `exports` |
| “Connect UART TX to pad” | `soc` `connections` + `pads` |
| “Map peripherals at 0x4000_0000” | `soc.address_map` |
| “Change FIFO depth” | instance `parameters` (must exist on IP) |
| “Connect the APB bundle” | `port.bundle` + `connections.kind: bundle` (or per-bit `kind: port`) |
| “Mark CDC on this IRQ” | `clock_domain` + `cdc: crossing` / `async_handshake` |
| “Decode mem bus to slaves” | SoC `fabric` + optional `adapters` |
| “Wire irq_5 into irq[5]” | `pad:irq_5` → `cpu.irq[5]` |

Prefer **smallest** change. Do not regenerate unrelated YAML.

Scenario walkthroughs: `rules/scenarios.md`.

## What “done” means

1. Schema validation passes for every touched YAML.
2. Connection / address / CDC / bundle sanity checks pass (validator or equivalent).
3. Agent reports:
   - YAML paths changed
   - RTL / wrapper / script paths generated or updated
   - validator exit code and summary
4. No ports exist in RTL that are absent from YAML (except pure implementation internals not on the contract boundary).

## Agent freedom

After protocols and structure are clear, any coding agent may invent **one-off** glue (decode snippets, wrappers, CDC cells). Do **not** productize a permanent integrator inside this pack. Optional later: MoonGlass hosts/checks these descriptions — it does not replace the agent elaborator.
