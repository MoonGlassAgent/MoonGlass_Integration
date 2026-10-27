# Starter — 连连看（NL → 必填字段）

Copy into Claude Code / Workbuddy / DeepSeek harness / Pi / Cursor when the human’s intent is fuzzy or multi-part:

---

You are working with **MoonGlass_Integration** (rules pack, not an integrator).

**Before editing YAML:**

1. Read `rules/nl_field_map.md` (连连看总表).
2. Split my intent into scenario phrases; match each to a row **M1–M13** (Chinese or English left column).
3. Fill only that row’s **Must** field paths; use **Optional** only if I asked.
4. Then follow `AGENTS.md` + `rules/integration_rules.md` + `schemas/`.
5. Run `python tools/validate.py` (project `.venv` if present).
6. Report: matched row IDs → files changed → validator summary → anything that needed a contract change.

My intent (edit me):

> …

Do **not** invent ports/widths/protocols outside YAML. Do **not** generate fabric/adapter HDL unless I explicitly ask for a one-off script. Natural language = intent; YAML = truth.

---

Quick pointer: full cards also in `rules/scenarios.md` (S1–S11). Entry brief: `AGENTS.md`.
