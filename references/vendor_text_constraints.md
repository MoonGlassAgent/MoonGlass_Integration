# 外部工具文本约束对照（仅参考，非照搬）

> **用途：** 了解业界「文本约束」长什么样，方便 MoonGlass_Integration **自研**更简单可用的 YAML 契约。  
> **不是：** 兼容层、迁移工具、或对任何厂商格式的产品级支持声明。  
> **专利 / IP：** 商用工具的具体 schema、专有字段与装配算法可能受专利与许可保护。**禁止**把本文或 `references/` 当作可复制的模板去克隆厂商 XML/TCL/专有 DSL；也**禁止**对外宣称「兼容 XX 工具」。只做 prior-art 意识与对照。

调研来源均为公开网页 / Accellera / 开源仓库文档；未在公开页看到的字段不编造。标 *uncertain* / *paywalled* 处需再核实。

---

## 自研原则（MoonGlass_Integration）

1. **我们定义自己的 YAML 契约**（`schemas/`：`ip_interface` / `subsystem` / `soc_top`）。厂商与开源格式是**对照样本**，不是要克隆的模板。
2. **只吸收通用意图**，跳过冗余：VLNV/GUI 布局元数据/工具版本矩阵/二进制 coreKit 等，对本包「Agent 读 YAML → 连线」无用则不抄。
3. **字段宁少勿全**：时钟、复位极性、端口宽向、协议标签、地址窗、连线端点——够 Agent 校验与精炼即可。
4. **不宣称互操作产品特性**：不说「兼容 IP-XACT / Vivado BD / coreKit」；若将来做导入器，那是另立任务与法务评审，不在本包默认范围。
5. **GUI = 文本的视图**：业界共性是「人改图画，工具写回文本」。我们没有 GUI；自然语言 + Agent 直接改 YAML，等价于跳过画布那一层。

### 哪些是「行业通用」vs「厂商/项目特有」

| 模式 | 归类 | 对本包可学的点（意图层） | 应跳过 / 勿照搬 |
|------|------|--------------------------|-----------------|
| 总线接口分组（一组信号 = 一个 interface） | **通用** | `ports` + 可选 `protocol` 标签 | 厂商 busDefinition VLNV 目录 |
| 主从 / initiator-target 角色 | **通用** | 可选 `bus_role`: initiator\|target\|monitor\|passthrough（**勿**占用 `port.role`） | IP-XACT mirrored* 全套枚举 |
| 地址空间 / memory map 窗 | **通用** | `base`/`size`/`name` 不重叠 | 完整 register bitfield 电子手册（除非另开寄存器包） |
| 时钟 / 复位作为一等公民 | **通用** | `clocks`/`resets` + 极性 | SDC/时序约束全文（合成域） |
| 参数化 RTL（parameter/generic） | **通用** | `parameters` 简单类型 | 配置 GUI 依赖图、互斥规则引擎 |
| VLNV（vendor:library:name:version） | **通用（IP-XACT 生态）** | 我们已有 `name`+`version` 即可 | 强制四段 VLNV |
| IP-XACT XML + TGI 生成器 | **标准 + 工具链** | 「组件 / 设计 / 连接」分层 | 整份 XSD、TGI API |
| Synopsys coreKit 二进制知识库 | **厂商特有** | 「配置后吐出 XML 视图」这一思路 | coreKit 格式、batch TCL 专有命令 |
| Vivado `.bd` / `write_bd_tcl` | **厂商特有（AMD）** | 地址赋值 = 主空间←从 segment | BD 画布坐标、XCI 全家桶 |
| Cadence IWB / Magillem 装配流 | **厂商/产品特有** | IP-XACT 作交换面 | 产品内部 schema |
| Arm Socrates 配置目录 + CLI | **厂商特有** | 配置→IP-XACT/Verilog 输出 | Socrates 专有工程模型（细节常 *paywalled*） |
| Questa VIP Configurator | **厂商特有（验证）** | 协议宽度/时钟复位要显式 | UVM VIP 类库与 Configurator 工程 |
| Chisel Diplomacy `:=` 图协商 | **开源项目特有** | 连接前参数协商的思想 | Scala 节点图 API |
| LiteX `mem_map` / CSR Python | **开源项目特有** | SoC 字典式地址图 | Migen/LiteX 运行时对象模型 |
| FuseSoC `.core` CAPI2 | **开源通用（构建）** | fileset + 参数；**偏编译不偏连线** | 当作 SoC 连线真源 |
| PicoSoC 硬编码 mmap + `iomem_*` | **示例级** | 极简外设挂接约定 | 当作可扩展装配框架 |

---

## 一、跨工具「文本约束」规则类型（抽象）

不论厂商如何命名，公开材料里反复出现的**意图类**约束大致是：

1. **接口描述**：端口名、方向、位宽；可选地打成 bus interface；协议/abstraction 标签。  
2. **连接规则**：谁连谁（instance.interface 或 instance.port）；是否允许自动按 interface 类型配对。  
3. **地址映射**：slave segment / address block → master address space 的 offset+range；禁止重叠（或显式 remap）。  
4. **时钟域 / 复位**：时钟名、（有时）频率；复位极性；跨 clock 的同步器策略多在 SDC/方法论，不在装配 XML 里写死。  
5. **参数**：模块 parameter 默认值与实例覆盖。  
6. **文件集 / 视图**：RTL、约束、文档路径（构建与交付，非连线语义本身）。

GUI 的共性映射：**画布上的 IP 块 / 连线 / Address Editor ≈ 上述文本对象的可视化编辑器**；导出或保存时写回 XML / Tcl / 源码 DSL。

---

## 二、商用与标准生态

### 2.1 IP-XACT（IEEE 1685 / Accellera）— 行业交换面

- **文本形态：** XML，schema 公开（如 1685-2022：`component` / `busInterface` / `memoryMap` / `design` / `designConfig` / `constraints` 等）。  
- **关键意图字段（通用，非抄 schema）：**  
  - 组件标识（常称 VLNV）  
  - `busInterface`：总线类型引用、initiator/target（或历史 master/slave）模式、portMap  
  - `addressSpace` / `memoryMap` / addressBlock / register（电子手册级，偏重）  
  - `fileSet`、componentInstantiation、parameters  
  - `design`：componentInstance + `interconnection` / `adHocConnection`  
- **连接：** design 层描述实例与接口互联；地址窗由 topology + memoryMap 推导。  
- **GUI：** 各厂商装配器编辑后生成/更新 IP-XACT；IP-XACT **本身不做**任何事，靠工具解释。  
- **来源：** Accellera IP-XACT schema 索引、User Guide PDF、IEEE 1685 标准页。  
- **对我们：** 分层（IP 契约 vs SoC design）与「接口+地址图」是通用教训；**整份 XSD 与 register 细节不是本包要抄的。**

### 2.2 Synopsys DesignWare / coreTools（coreBuilder · coreConsultant · coreAssembler）

- **文本形态（公开所述）：**  
  - 打包时 GUI 或 **TCL batch** 捕获源码、可配置参数、接口、约束、TB、文档等。  
  - 交付可走 **coreKit**（公开材料称含知识的**二进制包**，超 IP-XACT 能力）或生成 **IP-XACT XML 视图**。  
  - coreConsultant 配置单核并生成 IP-XACT；coreAssembler 做多核基于接口/规则的装配，并再吐 IP-XACT 等。  
- **连接 / 地址：** 公开文强调「按已定义 interface 自动连接」（如 APB manager–bus–subordinate 示例）；寄存器/memory map 写入 IP-XACT 供验证/文档。  
- **GUI→文本：** GUI 操作可存成可编辑的 TCL batch；配置结果再生 IP-XACT。  
- **来源：** Synopsys 公开文章 *Building an IP-XACT Design & Verification Environment*；coreBuilder/coreConsultant 产品页；coreTools datasheet PDF。  
- **厂商特有勿照搬：** coreKit 内部格式、专有 TCL 命令集、与 Galaxy/Discovery 的内建钩子。  
- **对我们可学的意图：** 「配置状态的 canonical 文本视图」；参数边界在打包时声明。不必引入二进制知识库。

### 2.3 「Cadence IP Integrator」命名说明 + Cadence 公开相关面

- **命名：** 公开资料里 **「IP Integrator / Block Design」** 通常指 **AMD（Xilinx）Vivado IP Integrator**（见下节）。Cadence 产品线公开更多谈的是 **IP-XACT 方法论**、**Interconnect Workbench（IWB）**（读元数据+VIP 做互连/性能 TB），以及历史上与 **Magillem**（现 Arteris Magillem Packaging/Connectivity）的 IP-XACT 装配协作。  
- **文本形态：** 交换面仍以 **IP-XACT XML** 为主（公开博客）；IWB 消费元数据而非另立公开 SoC-wiring schema（细节 *uncertain / 产品文档偏闭源*）。  
- **对我们：** 记「元数据驱动验证装配」；**不**假设存在可复制的 Cadence 专用连线 schema。若口语继续说 Cadence IP Integrator，先澄清是否实指 Vivado。

### 2.4 AMD Vivado IP Integrator（Block Design）— 常被称作 IP Integrator

- **文本形态：**  
  - 工程内 Block Design（`.bd` 等，工具私有结构化数据）。  
  - **Tcl：** `create_bd_cell` / `connect_bd_intf_net` / `connect_bd_net` / `assign_bd_address` / `create_bd_addr_seg`；`write_bd_tcl` 把 GUI 设计导出为可回放脚本。  
  - 寻址概念对齐 IP-XACT 思路：slave **address segment**、master **address space**、赋值后的 master segment（offset+range）。  
- **连接规则：** 接口级连接 + Address Editor / `assign_bd_address`；固定 offset 的 slave segment、aperture 等规则见 UG994。  
- **GUI→文本：** 画布与 Address Editor ↔ BD 对象；File→Export Block Design ≈ `write_bd_tcl`（可选 layout）。  
- **来源：** AMD UG994、UG835 Tcl、UG912 `BD_ADDR_SEG` 属性说明。  
- **厂商特有勿照搬：** `.bd` 二进制/专有结构、画布 layout、XCI IP 定制全家桶。  
- **对我们可学的意图：** 「地址赋值」显式写成 master 视角的窗；接口网与标量网分开。

### 2.5 Siemens Questa / Questa VIP（相关处）

- **范围：** **验证 IP**，不是 SoC RTL 装配器。  
- **文本形态：** Configurator GUI 配置总线宽度、协议特性、时钟复位等，**生成** UVM TB / netlist / 脚本；运行时用 SystemVerilog + `uvm_config_db` 传 virtual interface。协议细节在各 VIP User Guide（常 *paywalled*）。  
- **对我们：** 提醒「协议属性、时钟复位要写进契约」；**不要**把 VIP Configurator 工程当 SoC YAML 模板。

### 2.6 Arm Socrates

- **公开所述能力：** IP Catalog、配置与校验、生成 **IP-XACT 与 Verilog**；支持 CLI / script API。  
- **Arm IP-XACT 实践（公开参考手册摘要）：** 组件 / bus definition / design 文档；**刻意不用** IP-XACT 内 timing 类约束，改推 **SDC**；AMBA bus definition 建议用公开 AMBA 定义。  
- **GUI→文本：** 配置 UI / Project Explorer → 构建输出 IP-XACT + RTL。  
- **来源：** Arm Socrates User Guide「About Socrates」；*IP-XACT Components Reference Manual*（公开 PDF 片段）。完整 UI 字段表多 *paywalled*。  
- **对我们：** 「装配元数据与时序约束分家」值得保持；不复制 Socrates 工程模型。

---

## 三、开源与示例

### 3.1 Chisel / Diplomacy（+ FIRRTL）

- **文本形态：** **Scala 源码**即约束：`LazyModule` 上 `Node` 与运算符 `:=` / `:=*` / `:*=` / `:*=*` 建图；参数在 elaborate 前协商；FIRRTL 为编译中间相。  
- **连接：** Diplomacy 边 = 协议参数协商 + 后级 Bundle 连接；非单独 YAML。  
- **GUI：** 基本无；「文本」就是生成器代码。  
- **来源：** Chipyard Diplomacy Connectors；chipsalliance/diplomacy；rocket-chip 文档。  
- **可学意图：** 连接前协商宽度/边数；**勿**引入 Scala 图 API 作为本包真源。

### 3.2 SpinalHDL

- **文本形态：** Scala DSL；`BusSlaveFactory` 在代码里声明 `read`/`write`/`drive` 与 **address/bitOffset**（APB/AXI-lite 等）。总线库另有 crossbar 类设施。  
- **GUI：** 无。  
- **来源：** SpinalHDL 官方 Bus Slave Factory 文档。  
- **可学意图：** 寄存器映射与总线从设备描述共置；本包若只做集成可不做到 bitfield 级。

### 3.3 LiteX

- **文本形态：** **Python**：`SoC` / `mem_map`（如默认 CSR 区基址）、`add_constant`、`add_csr`、CSRBank 分配；CSR 总线信号极简（adr/we/dat_w/dat_r），再桥到 Wishbone/AXI。  
- **连接：** Python 里 add 外设与寄存器；构建时生成 CSR 头文件与互连。  
- **来源：** LiteX `soc/integration/soc.py`、Wiki *CSR Bus*。  
- **可学意图：** 一份字典式 memory map + 外设注册；跳过 LiteX 运行时对象细节。

### 3.4 Amaranth SoC

- **文本形态：** Python：`MemoryMap.add_resource` / `add_window`（addr、size、alignment、sparse/dense 翻译）；CSR `Register`/`Field`。  
- **连接：** wiring + MemoryMap 层次窗。  
- **来源：** amaranth-soc / ChipFlow memory map 文档。  
- **可学意图：** 地址对齐与 window 翻译；本包用扁平 address windows 即可起步。

### 3.5 PicoSoC（PicoRV32 示例）

- **文本形态：** Verilog 顶层 + **文档中的 memory map 表**；用户外设挂 `iomem_*` 并在 `0x03000000+` 解码。参数如 `MEM_WORDS` 等在 RTL。  
- **连接：** 手工 decode，无独立装配 DSL。  
- **来源：** `picosoc/README.md`（YosysHQ/picorv32）。  
- **可学意图：** 最小外设约定可以极少字段；扩展性靠文档纪律而非框架。

### 3.6 FuseSoC（附）

- **文本形态：** YAML **`.core`**，CAPI=2；VLNV `name`；`filesets` / `depend` / `parameters`（vlogparam 等）/ `targets`。  
- **定位：** **构建与依赖**系统，**不是** SoC 接口连线真源。  
- **来源：** FuseSoC 用户指南 *Writing core files*。  
- **对我们：** 可与「RTL 文件清单」类字段对照；连线仍看本包 `soc_top` connections。

---

## 四、与 MoonGlass_Integration 的对照（意图层，非兼容表）

| 意图 | 常见外部表达 | 本包（自研 YAML） |
|------|--------------|----------------------------|
| IP 接口契约 | IP-XACT component / BD cell / Spinal Component | `ip_interface` YAML：`ports`（`role`=信号、`bus_role`=主从）/`clocks`/`resets`/`parameters` |
| 子系统聚合 | design hierarchy / LiteX 模块树 | `subsystem` YAML |
| 顶层结构与连线 | IP-XACT design / BD Tcl nets / Diplomacy `:=` | `soc_top` YAML connections |
| 地址窗 | addressSpace / assign_bd_address / mem_map | YAML memory map / address windows |
| 校验 | 各工具 checker / SCR | `tools/validate.py` |
| 执行集成 | coreAssembler / Socrates / 生成器 / Agent | **任意 coding agent** 读 `AGENTS.md` 精炼 RTL |

**刻意不做的：** 完整 register RAL、IP-XACT VLNV 目录、GUI layout、VIP/UVM、SDC 全集、与任何 EDA 的官方互操作声明。

---

## 五、缺口与文档墙

| 项 | 状态 |
|----|------|
| Synopsys coreKit 内部二进制 / 全量 TCL API | 未公开细 schema → 不推测 |
| Arm Socrates 完整字段与脚本 API | User Guide 深页常需账号 → *paywalled* |
| Cadence IWB / Magillem 内部模型 | 公开仅方法论与产品页 → 细字段 *uncertain* |
| Questa VIP 各协议 reference | 用户手册多需许可 → 仅记 Configurator 流程 |
| IEEE 1685 规范性全文 | 标准正文可能付费；XSD + Accellera User Guide 可公开对照 |
| 「Cadence IP Integrator」专名 | 易与 Vivado IPI 混淆 → 上文已拆开说明 |

---

## 六、主要公开来源（便于复核）

- Accellera IP-XACT 1685-2022 XSD 索引；IP-XACT User Guide PDF  
- Synopsys：IP-XACT DVE 文章；coreBuilder / coreConsultant 产品页；coreTools datasheet  
- AMD：UG994 IP Integrator；UG835 `assign_bd_address` / `write_bd_tcl`；UG912 BD_ADDR_SEG  
- Arm：Socrates About；IP-XACT Components Reference Manual（公开摘要）  
- Siemens：Questa VIP Configurator 介绍博文  
- FuseSoC CAPI2 文档；LiteX CSR Wiki；Amaranth-soc memory docs；SpinalHDL BusSlaveFactory；Chipyard Diplomacy Connectors；PicoSoC README  

*本文不包含任何厂商 schema 的逐字段复制，也不提供可粘贴的「兼容模板」。*
