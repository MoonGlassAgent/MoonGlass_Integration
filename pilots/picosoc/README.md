# PicoSoC pilot — MoonGlass_Integration

**目的 / Purpose:** 用本规则包的 YAML 契约**重描** [YosysHQ/picorv32](https://github.com/YosysHQ/picorv32) 的 `picosoc/` 顶层集成，并跑 `tools/validate.py`。  
这是对 **rules pack** 的实测，**不是**永久集成器，也**不**重新生成或替换原 Verilog。

## Source

| Item | Value |
|------|--------|
| Repo | https://github.com/YosysHQ/picorv32 (ISC) |
| Commit | `ef203c2b0a3fb793280f5114941416c425c5b461` (2026-09-07) |
| Focus | `picosoc/picosoc.v` + `picorv32.v`, `spimemio.v`, `simpleuart.v`, in-file `picosoc_mem` |

Do **not** copy large Verilog into this pack — only YAML + notes; cite GitHub paths in `hdl.files`.

## Layout

```
pilots/picosoc/
  ip/*.yaml                 # CPU / iomem / spimemio / uart / sram contracts
  soc/picosoc.yaml          # instances, connections, fabric, adapters, bit-slice IRQs
  README.md
  实测报告.html
```

## What this pilot exercises

| Feature | Where |
|---------|--------|
| **9.1** bundle closure | `cpu.bundle:mem_m` → `iomem0.bundle:mem_s` |
| **9.2** strategy A pairing | initiator ↔ target on that bundle |
| **9.3** multi-clock CDC | Not in PicoSoC (single `clk`); see pack `demo_soc` |
| **0.1.3 fabric** | `fabric: mem_decode` — RAM / flash / uart / iomem windows + ready/rdata merge intent |
| **0.1.4 adapters** | `mem_to_spimemio`, `mem_to_sram`, `mem_to_uart_reg` |
| **0.1.5 bit-slice** | `pad:irq_5` → `cpu.irq[5]` (and 6/7) |

## Validate

```bash
cd /path/to/MoonGlass_Integration
.venv/bin/python tools/validate.py --root pilots/picosoc --no-examples-fallback \
  pilots/picosoc/ip/*.yaml pilots/picosoc/soc/*.yaml
```

Expect `6/6 files OK`.

## Remaining limitations (honest)

- Fabric / adapters are **validation markup** — Agent still elaborates decode mux HDL.
- `spimem_cfg` slave has no adapter yet (cfgreg sideband noted only).
- Look-ahead / PCPI / trap still omitted; SRAM doc window vs physical size is prose.

See `实测报告.html` for before/after iterations.
