# MoonGlass_Integration

[![Comic intro](https://img.shields.io/badge/Comic-网站介绍-ff6b35?style=for-the-badge&logo=github)](https://moonglassagent.github.io/MoonGlass_Integration/)
[![GitHub Pages](https://img.shields.io/badge/Pages-docs%2F-4ecdc4?style=flat-square)](https://moonglassagent.github.io/MoonGlass_Integration/)

**漫画式介绍（公开站）:** [https://moonglassagent.github.io/MoonGlass_Integration/](https://moonglassagent.github.io/MoonGlass_Integration/) · 源文件 `docs/index.html`


**规则 / Schema / 约束包** —— 让任意 coding agent 靠 YAML 描述做 SoC 组装与连线。  
**不是**集成引擎，**不是** MoonGlass 产品内的接线功能。

**English (short):** A description-driven SoC assembly rules pack. Agents read IP / subsystem / SoC YAML contracts, validate, then elaborate top RTL. AI may invent one-off helpers; we do not ship a heavyweight integrator. Thin schema validator only.

## 是什么 / 不是什么

| 是 | 不是 |
|----|------|
| IP / Subsystem / SoC 的 JSON Schema + 约定 | FuseSoC / IP-XACT 替代品（刻意不做） |
| Agent 可读的 `AGENTS.md` / `CLAUDE.md` / `.cursorrules` | MoonGlass 里跑集成的功能模块 |
| 示例 YAML + 校验脚本 | 永久的“集成工具产品” |

协议与结构清楚之后，上层 Agent（Workbuddy、Claude Code、DeepSeek harness、Pi、Cursor…）自由度很大；需要时现场写 glue 即可。

## 怎么用

把本目录放到芯片仓库旁（或 submodule / 拷贝），用自然语言提集成意图。

| Harness | 入口 |
|---------|------|
| **Claude Code** | 读 `CLAUDE.md`（转 `AGENTS.md`） |
| **通用 / DeepSeek / Pi** | 系统 brief 指向 `AGENTS.md` |
| **Workbuddy / Cursor 类** | `.cursorrules` + `WORKBUDDY.md` |
| **起手 prompt** | `prompts/integrate.md` |
| **连连看（NL→字段）** | `rules/nl_field_map.md` + `prompts/scenario_match.md` |

```bash
cd /path/to/MoonGlass_Integration
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/validate.py          # 默认校验 examples/
.venv/bin/python tools/validate.py path/to/yaml…
.venv/bin/python tools/validate.py --root /path/to/chip_repo path/to/soc.yaml
# 可选环境变量：MOONGLASS_INTEGRATION_ROOTS（路径分隔同 os.pathsep）
# 关闭 examples/ 回退：--no-examples-fallback
```

校验器会按「引用文件同目录 → `--root` / 环境变量 → 本包 `examples/`」解析 `ref`/`ip`，用于 **bundle 闭包**、**bus_role 配对（策略 A）**、**fabric decode/mux**、**adapters**、**bit-slice**；不生成 glue HDL。

## 目录

```
schemas/     ip_interface | subsystem | soc_top
examples/    最小 APB 外设岛 demo
pilots/      开源 SoC 实测（picosoc/）— 规则包验证，非集成器
rules/       命名、连线合法性、NL→YAML、连连看 nl_field_map、「完成」定义
prompts/     可复制起手提示（含 scenario_match）
tools/       validate.py（规则执行，非集成器）
```

## 与 MoonGlass 的关系

MoonGlass 适合**托住**这类规则/描述与状态；**不适合**在本包里充当集成器。社区可先挂这套组建拉讨论与流量，和核心产品解耦。

## References

外部工具文本约束的**对照调研**（仅参考，非照搬）：见 [`references/`](references/)。自研原则与专利警示见该目录总览；**不**修改本包 `schemas/` 以迁就厂商格式。

## License

见 `LICENSE`：社区试用稿，目标对齐 MoonGlass 的 **PolyForm Noncommercial**；正式文案 TBD。非商业评估可用，勿默认可商业再分发。

## 文档

- [漫画介绍网站](https://moonglassagent.github.io/MoonGlass_Integration/) — `docs/index.html` 连环画式导览（GitHub Pages）
- [中文说明（HTML）](docs/MoonGlass_Integration说明.html) — 定位、架构、字段、场景、**连连看**、有意未做的缺口与原因
- [连连看 NL↔字段](rules/nl_field_map.md) — 人话意图 → 必填/可选 YAML 路径（Agent 先匹配再改文件）
- [PicoSoC pilot](pilots/picosoc/) — 用本包 YAML 重描开源 PicoSoC 顶层并校验；[实测报告](pilots/picosoc/实测报告.html)

## Version

见 `VERSION`（当前 `0.1.6-draft`）与 `CHANGELOG.md`。
