# AMD Vivado IP Integrator (Block Design)

- **归类：** 厂商特有。任务中「Cadence IP Integrator」口语常实际指此。
- **文本：** `.bd` + Tcl（`connect_bd_*` / `assign_bd_address`）+ `write_bd_tcl`
- **可学意图：** 主地址空间 ← 从 segment 的显式赋值
- **勿照搬：** BD/XCI 专有结构、画布 layout、兼容 Vivado 声明
- **详见：** [vendor_text_constraints.md §2.4](../vendor_text_constraints.md)
