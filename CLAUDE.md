# Claude Code — MoonGlass_Integration

Read **`AGENTS.md`** first, then `schemas/` and `rules/integration_rules.md`.

This repo is a **rules / schema pack** for description-driven SoC assembly. You wire from YAML; you are not an integration-tool product.

## Claude-specific tips

- Prefer editing YAML before RTL. If RTL and YAML disagree, YAML wins until the human changes the contract.
- After edits, run:  
  ` .venv/bin/python tools/validate.py `  
  (create venv once: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`)
- Keep diffs small: one intent → minimal YAML + matching wrapper/top changes.
- Use `prompts/integrate.md` as the user-facing starter if the session has no prior context.
- Fuzzy / multi-part NL intent: match rows in `rules/nl_field_map.md` first (or copy `prompts/scenario_match.md`). Fill **Must** fields only unless asked.

Defer all policy detail to **AGENTS.md** + schemas. Do not duplicate long rules here.
