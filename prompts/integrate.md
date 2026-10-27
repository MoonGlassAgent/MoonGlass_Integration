# Starter prompt — description-driven SoC integrate

Copy into Claude Code / Workbuddy / DeepSeek harness / Pi / Cursor:

---

You are working with **MoonGlass_Integration** (rules pack, not an integration engine).

1. Read `AGENTS.md`, `rules/integration_rules.md`, and `schemas/*.schema.json`.
   If intent is fuzzy or multi-part: match `rules/nl_field_map.md` (连连看 M1–M13) or use `prompts/scenario_match.md` first.
2. Treat YAML under `ip/`, `subsys/`, `soc/` (or this pack’s `examples/`) as the contract truth.
3. My intent (edit me):

   > Integrate / wire: **…**  
   > Constraints: **…**

4. Edit the minimal YAML to express that intent. Do not invent ports that contradict YAML.
5. Elaborate only the RTL/wrappers needed to satisfy the contracts.
6. Run `python tools/validate.py` (use project `.venv` if present) and report evidence:
   - files changed
   - validator result
   - anything you could not satisfy without a contract change

Natural language = intent. YAML = truth. One-off helper scripts OK; do not build a heavyweight integrator.

---
