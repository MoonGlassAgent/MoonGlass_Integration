# References — 外部工具「文本约束」调研索引

本目录只做**调研与对照整理**，供上层 coding agent 参考。  
调研正文不复制厂商 schema。字段吸收见 `ABSORBED.md`；真源仍是本包 `schemas/` YAML。  
**专利 / IP：** 禁止复制商用 schema 或宣称兼容；详见总览文首与 **「自研原则」** 节。

| 文件 | 内容 |
|------|------|
| [`vendor_text_constraints.md`](vendor_text_constraints.md) | 商用 + 开源 SoC/芯片集成相关工具的文本约束形态总览（推荐先读） |
| [`vendors/`](vendors/) | 按厂商/项目拆分的短摘要（与总览互补；字段以总览为准） |
| [`ABSORBED.md`](ABSORBED.md) | 通用意图 → 本包字段/文件映射（自研，非厂商克隆） |

## 覆盖范围（本轮）

**商用：** Synopsys DesignWare / coreTools（coreBuilder · coreConsultant · coreAssembler）、Cadence 侧 IP-XACT / Interconnect Workbench（及与 Magillem/Arteris 的公开协作语境）、**AMD Vivado IP Integrator**（Block Design；任务里常称 “IP Integrator”，见总览命名说明）、Siemens Questa VIP（接口/协议约束，偏验证）、Arm Socrates（IP-XACT SoC 装配）。

**开源：** Chisel / Diplomacy（+ FIRRTL 背景）、SpinalHDL、LiteX、Amaranth SoC、PicoSoC；附 FuseSoC（`.core` YAML）与 IP-XACT 开放 schema。

## 怎么用

1. 读 `vendor_text_constraints.md` 的「规则类型」与「与本包对照」表。  
2. 需要某工具细节时进 `vendors/` 或总览对应小节。  
3. Agent 执行集成时仍以根目录 `AGENTS.md` + `schemas/` 为准；本目录**不是**第二套 schema。

## 调研方法说明

- 优先公开主文档 / Accellera / GitHub / 厂商产品页与用户指南摘要。  
- **未在公开页看到的专有 schema 字段一律不编造**；不确定处标 *uncertain* / *paywalled*。  
- 日期口径：调研写入时（仓库内 `0.1.0-draft` 阶段）。
