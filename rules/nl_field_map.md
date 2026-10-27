# NL ↔ 字段 连连看（scenario match）

**用途：** Agent 收到自然语言集成意图后，**先在本表左列匹配短语**，再只填右列「必填」字段；可选列按需。不要猜字段名。

**真源顺序：** 本表 → `rules/scenarios.md`（S1–S11 细则）→ `rules/integration_rules.md` → `schemas/`。  
**起手：** `prompts/scenario_match.md` / `prompts/integrate.md`。

**用法（Agent）：**

1. 把用户意图拆成 1–N 条「场景短语」。
2. 每条在下表左列找最近匹配（中/英均可）。
3. 编辑右列 **Must** 路径；**Optional** 仅在意图明确时写。
4. 跑 `tools/validate.py`；对照 **Done** 勾选。
5. 一条意图可同时命中多行（例如「APB 整组接到外设岛并映到 0x4000_0000」→ 单端口/bundle + 地址窗）。

端点语法速查：`instance.port` | `instance.port[N]` | `instance.port[M:N]` | `instance.bundle:<id>` | `clock:<name>` | `reset:<name>` | `pad:<name>` | `const:<value>`。

---

## 总表（连连看）

| ID | 人话意图（中 / EN） | Must（必填字段路径） | Optional | Done 检查 |
|----|---------------------|----------------------|----------|-----------|
| M1 | 单信号互连；把 A 的 xx 接到 B 的 yy / *wire port X to Y* | `connections[].from`, `connections[].to`；两端端口已在 IP/subsys `ports[]` | `connections[].kind: port`（默认）, `width`, `note` | 端点可解析；**有效位宽**一致；两端 `protocol` 若都填则相等 |
| M2 | 整组总线/接口互连；hook the APB slave bundle / *bundle connect* | 两端 `ports[].bundle: <id>`；`connections[]` 用 `kind: bundle` + `from`/`to` 为 `instance.bundle:<id>` | 同 bundle 内统一 `protocol` / `bus_role` / `clock_domain` | 跨文件 **bundle 闭包**：sink 侧该 bundle 成员全覆盖；宽度/protocol 一致；同 bundle 内 `bus_role` 不混 initiator+target |
| M3 | 地址映射；映到 0x… / *map at base* | SoC：`address_map[].region`, `base`, `size_bytes`, `target`；子系：`base_offset`, `size_bytes`, `instance` | `note`（故意重叠时必写） | 无未解释重叠；窗盖住子 map |
| M4 | 时钟/复位驱动岛 / *drive from sys_clk / sys_rstn* | `clock_tree[]` / `reset_tree[]`（`name`）；`connections`：`from: clock:<n>` 或 `reset:<n>` → 实例时钟/复位口 | `ports[].clock_domain` 与钟名对齐；复位 `polarity` | 极性匹配 sink；必需 clk/rst 不悬空；跨域见 M6 |
| M5 | 焊盘/IO；TX/RX 上 pad / *connect to pads* | `pads[].name`（+ `dir`/`width`）；`connections` 使用 `pad:<name>` | `pads[].protocol`, `note` | pad 方向与网意图一致；宽度匹配 |
| M6 | 跨时钟 / CDC 标记；IRQ 从 pclk 到 aon / *mark CDC crossing* | 两端 `ports[].clock_domain`（不同）；跨域口 `ports[].cdc`: `crossing` \| `async_handshake` \| `unknown` | connection `note`（同步器意图）；SoC 第二钟在 `clock_tree` | 异域且无 cdc∈{crossing,async_handshake,unknown} → 视为错；**非**签核级 CDC |
| M7 | 地址译码 fabric；ready OR / rdata mux / *decode_mux* | `fabric[].id`, `kind: decode_mux`, `master`, `slaves[].id`, `slaves[].target` 或等价端点, `slaves[].match.base`, `slaves[].match.size_bytes` | `select`, `addr_role`, `ready_merge` (`or`\|`priority`\|`onehot`\|`unknown`), `rdata_merge` (`mux_by_select`\|`priority`\|`unknown`), `slaves[].adapter`, `note`（重叠窗） | schema + fabric 检查过；重叠窗有 `note`；**不**声称生成 HDL |
| M8 | 异构从设备；24b 地址、无 wdata / *partial map adapter* | `adapters[].id`, `kind` (`partial_map`\|`width_remap`\|`bridge`)；`maps[].from_role` → `to_port`；`fabric.slaves[].adapter` = 该 id | `width_from`/`width_to`, `omit_from_roles`, `note` | `to_port` 在目标 IP 存在；宽度一致；故意省略列入 `omit_from_roles` |
| M9 | 位切片 IRQ/GPIO；接到 cpu.irq[5] / *bit-slice* | `connections[].from`/`to` 含 `[N]` 或 `[M:N]`；`width` = 有效位宽（常为 1） | `pad:name[N]` | 切片在端口/pad 宽度内；两端 **有效位宽** 相等；bundle/clock/reset/const **不可**切片 |
| M10 | 主从角色配对；initiator↔target / *bus_role strategy A* | 相关 `ports[].bus_role`: `initiator` \| `target`（需要强制时两端都填） | `monitor`, `passthrough`（不触发 A 失败） | **策略 A**：两端都在 {initiator,target} → 必须互补；任一端省略 → **不报错**；勿把 `role`（psel/pready）当成 `bus_role` |
| M11 | 加一个 IP / *add UART APB* | 新或复用 `ip/*.yaml`：`kind: ip`, `name`, `ports`/`clocks`/`resets`；SoC/subsys `instances[].id` + `ip`/`ref` | `parameters`, `bundle`, `bus_role`, `protocol` | 实例可解析；必需 clk/rst 在顶层有驱动（或注明故意） |
| M12 | 改参数；FIFO depth 32 / *override parameter* | IP `parameters.<NAME>` 已声明；实例 `parameters.<NAME>` | 类型/范围说明于 IP `description` | 无未知参数名；与 IP 契约类型兼容 |
| M13 | 单口 IRQ 线（非切片） / *wire IRQ* | IP `ports` 含 `protocol: irq`（或约定）；`connections`（+ 可选 `pads`） | `bundle`, `cdc`, `clock_domain` | 宽度默认 1；端点可解析；跨钟走 M6，切片走 M9 |

---

## 短语速查（左列索引）

| 听到这些… | 先打开 |
|-----------|--------|
| 接到、互连、wire、connect port | **M1** |
| 整组、bundle、APB slave 一接 | **M2** |
| 映到、地址窗、map、0x | **M3** |
| 时钟、复位、sys_clk、sys_rstn | **M4** |
| pad、焊盘、pin、TX/RX 出芯片 | **M5** |
| CDC、跨钟、crossing、aon_clk | **M6** |
| 译码、decode、ready OR、rdata mux、fabric | **M7** |
| 位宽不同、缺信号、adapter、partial、24-bit addr | **M8** |
| `[5]`、`[7:0]`、bit、切片 | **M9** |
| initiator、target、主从、bus_role | **M10** |
| 加一个 IP、instantiate | **M11** |
| 参数、FIFO、generic、override | **M12** |
| IRQ（整线、非 bit） | **M13** → 切片则 **M9** |

---

## 字段路径速记（右列索引）

| 路径 | 出现于 |
|------|--------|
| `connections[].from` / `.to` / `.kind` / `.width` / `.note` | M1 M2 M4 M5 M9 M13 |
| `ports[].bundle` / `instance.bundle:<id>` | M2 |
| `ports[].protocol` / `.role` / `.bus_role` | M1 M2 M10 M13 |
| `ports[].clock_domain` / `.cdc` | M4 M6 |
| `clock_tree[]` / `reset_tree[]` | M4 |
| `address_map[]`（`base` / `base_offset` / `size_bytes` / `target`） | M3 |
| `pads[]` / `pad:<name>` | M5 M9 |
| `fabric[].kind: decode_mux` / `master` / `slaves[].match.base` / `.size_bytes` / `ready_merge` / `rdata_merge` | M7 |
| `adapters[]` / `maps[]` / `omit_from_roles` / `fabric.slaves[].adapter` | M8 |
| `instance.port[N]` / `[M:N]` | M9 |
| `instances[]` / `ip` / `ref` / `parameters` | M11 M12 |

---

## 与 scenarios.md 对照

| 本表 | scenarios.md |
|------|----------------|
| M11 | S1 Add IP |
| M2 | S2 Bundle connect |
| M3 | S3 Address window |
| M4 | S4 Clock / reset |
| M13 | S5 IRQ |
| M5 | S6 Pad |
| M6 | S7 CDC |
| M12 | S8 Parameter |
| M7 | S9 Fabric decode |
| M8 | S10 Adapter |
| M9 | S11 Bit-slice |
| M1 | （贯穿各场景的 port 连线） |
| M10 | （规则策略 A；bundle/port 连接时叠加） |

---

## 有意不做（本表不引导）

- 自动生成译码 / adapter **HDL**
- 强制 `fabric` 与 `connections` 一一对应（未来可选）
- 连接方向静态度量（未来可选）
- 寄存器 bitfield / VLNV / 厂商互换 / GUI

