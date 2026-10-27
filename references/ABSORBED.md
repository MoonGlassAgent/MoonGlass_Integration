# Absorbed ideas → MoonGlass_Integration fields

Custom mapping only. **Not** a vendor clone; IP-XACT / Vivado / coreTools / Diplomacy / LiteX names below are prior-art *intent* labels.

| Industry / prior-art idea | Our field or file | Notes |
|---------------------------|-------------------|--------|
| Bus interface grouping (signal set = one interface) | `port.protocol` + optional `port.bundle` | Bundle id groups ports for `kind: bundle` wiring |
| Initiator / target (master/slave) mode | `port.bus_role`: `initiator`\|`target`\|`monitor`\|`passthrough` | **Not** `port.role` |
| Signal role inside protocol (PSEL, PREARDY, Txd…) | `port.role` | Signal-within-protocol only |
| Port direction / width | `port.dir`, `port.width` | |
| Clock as first-class | `clocks[]` (IP), `clock_tree` (SoC) | |
| Reset + polarity | `resets[]`, `reset_tree` + `polarity` | |
| Clock domain / CDC awareness | `port.clock_domain`, `port.cdc` | `cdc`: `none`\|`crossing`\|`async_handshake`\|`unknown` |
| Ad-hoc vs interface-level net | `connections[].kind`: `port`\|`bundle` | SoC + subsystem `links` |
| Design interconnection | `soc.connections`, `subsys.links` | Endpoints: `instance.port`, `clock:`, `reset:`, `pad:`, `const:` |
| Address map / segment | `memory_maps`, `subsys.address_map`, `soc.address_map` | Absolute vs relative offsets |
| Parameters / generics | `parameters` + instance overrides | |
| Component identity | `name` + `version` (+ `kind`) | No mandatory VLNV |
| Fileset / RTL hint | `hdl.module`, `hdl.files` | Build lists optional |
| Agent workflow / NL→edit | `AGENTS.md`, `rules/scenarios.md`, `rules/integration_rules.md` | |
| Validation | `tools/validate.py` + JSON Schemas | Not an integrator |
| Vendor survey (reference only) | `references/vendor_text_constraints.md`, `references/vendors/` | Do not copy schemas |

## Deliberately not absorbed

- Full register bitfield / RAL electronics handbook
- VLNV catalogs, GUI layout, BD canvas coordinates
- Binary coreKit / proprietary TCL command sets
- UVM VIP Configurator projects, SDC-as-assembly-truth
- Scala Diplomacy node APIs / LiteX runtime objects as YAML source of truth
- Claims of “compatible with IP-XACT / Vivado / …”

## Version

Fields absorbed in **0.1.1-draft**; cross-file bundle closure + pairing strategy A + multi-clock CDC demo in **0.1.2-draft**. See `CHANGELOG.md`.
