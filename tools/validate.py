#!/usr/bin/env python3
"""MoonGlass_Integration schema validator (rules enforcement only — not an integrator).

Cross-file resolve is for validation/checks only: load referenced YAML to check
bundle closure, bus_role pairing, fabric decode windows, adapters, and bit-slice
endpoints. Does not generate glue HDL.
"""

from __future__ import annotations

import argparse
import re
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
EXAMPLES_DIR = ROOT / "examples"

KIND_TO_SCHEMA = {
    "ip": "ip_interface.schema.json",
    "subsystem": "subsystem.schema.json",
    "soc": "soc_top.schema.json",
}

BUS_ROLES = {"initiator", "target", "monitor", "passthrough"}
PAIR_ROLES = {"initiator", "target"}  # strategy A only enforces among these
CDC_VALUES = {"none", "crossing", "async_handshake", "unknown"}
CONN_KINDS = {"port", "bundle"}
LAYERS = ("ip", "subsys", "soc")
FABRIC_KINDS = {"decode_mux"}
FABRIC_SELECT = {"address"}
READY_MERGE = {"or", "priority", "onehot", "unknown"}
RDATA_MERGE = {"mux_by_select", "priority", "unknown"}
ADAPTER_KINDS = {"partial_map", "width_remap", "bridge"}
# Bit-slice on instance.port or after last segment: name[N] or name[M:N]
_SLICE_TAIL = re.compile(r"^(?P<base>.+)\[(?P<body>\d+(?::\d+)?)\]$")

# ---------------------------------------------------------------------------
# deps
# ---------------------------------------------------------------------------


def _die_deps() -> None:
    print(
        "Missing dependency. Install with:\n"
        "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
        "  # or: pip install pyyaml jsonschema",
        file=sys.stderr,
    )
    sys.exit(2)


try:
    import yaml
except ImportError:
    _die_deps()

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError  # noqa: F401
except ImportError:
    _die_deps()


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping at root")
    return data


def iter_default_examples() -> list[Path]:
    paths: list[Path] = []
    for sub in LAYERS:
        d = EXAMPLES_DIR / sub
        if d.is_dir():
            paths.extend(sorted(d.glob("*.yaml")))
            paths.extend(sorted(d.glob("*.yml")))
    return paths


def parse_roots(cli_roots: list[Path] | None, env_val: str | None) -> list[Path]:
    """Ordered search roots after the referring file's directory."""
    out: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        rp = p.resolve()
        if rp not in seen and rp.is_dir():
            seen.add(rp)
            out.append(rp)

    for r in cli_roots or []:
        add(r)
    if env_val:
        for part in env_val.split(os.pathsep):
            part = part.strip()
            if part:
                add(Path(part))
    return out


# ---------------------------------------------------------------------------
# Path resolution (9.1)
#
# Order for bare name / stem refs (instance.ref / instance.ip):
#   1. Same directory as the referring YAML
#      - <dir>/<ref>.yaml|.yml
#      - <dir>/{ip,subsys,soc}/<ref>.yaml|.yml
#   2. Each --root / MOONGLASS_INTEGRATION_ROOTS entry (same patterns)
#   3. Pack examples/ (ip|subsys|soc) — demo fallback
# Explicit relative paths (contain / or end with .yaml/.yml) are tried relative
# to the referring directory first, then each root.
# ---------------------------------------------------------------------------


def _candidates_for_stem(stem: str, base: Path) -> list[Path]:
    out: list[Path] = []
    for ext in (".yaml", ".yml"):
        out.append(base / f"{stem}{ext}")
        for layer in LAYERS:
            out.append(base / layer / f"{stem}{ext}")
    return out


def resolve_ref(
    ref: str,
    referring: Path,
    search_roots: list[Path],
    *,
    include_examples: bool = True,
) -> Path | None:
    """Return first existing path for ref, or None."""
    ref = ref.strip()
    if not ref:
        return None

    referring_dir = referring.resolve().parent
    looks_like_path = ("/" in ref) or ref.endswith(".yaml") or ref.endswith(".yml")

    ordered_bases: list[Path] = [referring_dir, *search_roots]
    if include_examples:
        ordered_bases.append(EXAMPLES_DIR.resolve())

    tried: list[Path] = []
    if looks_like_path:
        p = Path(ref)
        if p.is_absolute():
            if p.is_file():
                return p.resolve()
            return None
        for base in ordered_bases:
            cand = (base / p).resolve()
            tried.append(cand)
            if cand.is_file():
                return cand
            # allow stem without extension in a relative path
            if not (ref.endswith(".yaml") or ref.endswith(".yml")):
                for ext in (".yaml", ".yml"):
                    c2 = Path(str(cand) + ext)
                    tried.append(c2)
                    if c2.is_file():
                        return c2.resolve()
        return None

    # bare name
    for base in ordered_bases:
        for cand in _candidates_for_stem(ref, base):
            tried.append(cand)
            if cand.is_file():
                return cand.resolve()
    return None


class DocStore:
    """Load YAML by ref with cycle detection. Validation-only elaborator view."""

    def __init__(self, search_roots: list[Path], *, include_examples: bool = True):
        self.search_roots = search_roots
        self.include_examples = include_examples
        self.by_path: dict[Path, dict] = {}
        self._loading: set[Path] = set()

    def load_path(self, path: Path, errors: list[str], *, via: str = "") -> dict | None:
        path = path.resolve()
        if path in self.by_path:
            return self.by_path[path]
        if path in self._loading:
            errors.append(
                f"cycle while loading {path}" + (f" (via {via})" if via else "")
            )
            return None
        if not path.is_file():
            errors.append(f"missing file {path}" + (f" (via {via})" if via else ""))
            return None
        self._loading.add(path)
        try:
            doc = load_yaml(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: load error: {exc}")
            self._loading.discard(path)
            return None
        self.by_path[path] = doc
        self._loading.discard(path)
        return doc

    def load_ref(
        self,
        ref: str,
        referring: Path,
        errors: list[str],
        *,
        expect_kind: str | None = None,
        via: str = "",
    ) -> tuple[Path | None, dict | None]:
        path = resolve_ref(
            ref, referring, self.search_roots, include_examples=self.include_examples
        )
        if path is None:
            errors.append(
                f"{referring}: cannot resolve ref {ref!r}"
                + (f" ({via})" if via else "")
                + "; search: same-dir → --root/MOONGLASS_INTEGRATION_ROOTS"
                + (" → pack examples/" if self.include_examples else "")
            )
            return None, None
        doc = self.load_path(path, errors, via=via or ref)
        if doc is None:
            return path, None
        kind = doc.get("kind")
        if expect_kind and kind != expect_kind and expect_kind != "auto":
            errors.append(
                f"{referring}: ref {ref!r} resolved to {path} with kind={kind!r}, "
                f"expected {expect_kind!r}"
            )
            return path, None
        name = doc.get("name")
        # bare-name refs should match document name when present
        if "/" not in ref and not ref.endswith((".yaml", ".yml")) and name and name != ref:
            errors.append(
                f"{referring}: ref {ref!r} resolved to {path} but document name is {name!r}"
            )
            return path, None
        return path, doc


def ports_of(doc: dict) -> list[dict]:
    kind = doc.get("kind")
    if kind == "ip":
        return [p for p in (doc.get("ports") or []) if isinstance(p, dict)]
    if kind == "subsystem":
        exports = doc.get("exports") or {}
        if isinstance(exports, dict):
            return [p for p in (exports.get("ports") or []) if isinstance(p, dict)]
    return []


def clock_reset_names(doc: dict) -> tuple[set[str], set[str]]:
    """Clock/reset endpoint names visible on an IP or subsystem boundary."""
    kind = doc.get("kind")
    if kind == "ip":
        clocks = {
            c.get("name")
            for c in doc.get("clocks") or []
            if isinstance(c, dict) and c.get("name")
        }
        resets = {
            r.get("name")
            for r in doc.get("resets") or []
            if isinstance(r, dict) and r.get("name")
        }
        return clocks, resets
    if kind == "subsystem":
        exports = doc.get("exports") or {}
        clocks, resets = set(), set()
        if isinstance(exports, dict):
            clocks = {
                c.get("name")
                for c in (exports.get("clocks") or [])
                if isinstance(c, dict) and c.get("name")
            }
            resets = {
                r.get("name")
                for r in (exports.get("resets") or [])
                if isinstance(r, dict) and r.get("name")
            }
        return clocks, resets
    return set(), set()


def clocks_of(doc: dict) -> set[str]:
    kind = doc.get("kind")
    if kind == "ip":
        return {
            c.get("name")
            for c in doc.get("clocks") or []
            if isinstance(c, dict) and c.get("name")
        }
    if kind == "subsystem":
        exports = doc.get("exports") or {}
        if isinstance(exports, dict):
            return {
                c.get("name")
                for c in (exports.get("clocks") or [])
                if isinstance(c, dict) and c.get("name")
            }
    if kind == "soc":
        return {
            c.get("name")
            for c in doc.get("clock_tree") or []
            if isinstance(c, dict) and c.get("name")
        }
    return set()


def bundle_members(ports: list[dict], bundle_id: str) -> list[dict]:
    return [p for p in ports if p.get("bundle") == bundle_id]


def member_key(port: dict) -> str:
    """Stable id for reporting; pairing uses match_bundle_members()."""
    role = port.get("role")
    if role:
        return f"role:{role}"
    return f"name:{port.get('name', '?')}"


def match_bundle_members(
    from_ports: list[dict], to_ports: list[dict]
) -> tuple[dict[str, tuple[dict, dict]], list[str], list[str]]:
    """
    Pair sink members to source members.
    Prefer matching by role when the sink port has role and source has the same role;
    else match by port name. Returns (pairs_by_key, missing_sink_keys, extra_source_keys).
    """
    from_by_role = {p["role"]: p for p in from_ports if p.get("role")}
    from_by_name = {p.get("name"): p for p in from_ports if p.get("name")}
    to_by_role = {p["role"]: p for p in to_ports if p.get("role")}
    to_by_name = {p.get("name"): p for p in to_ports if p.get("name")}

    pairs: dict[str, tuple[dict, dict]] = {}
    used_from: set[int] = set()
    missing: list[str] = []

    for tp in to_ports:
        key = member_key(tp)
        sp = None
        role = tp.get("role")
        if role and role in from_by_role:
            sp = from_by_role[role]
        elif tp.get("name") in from_by_name:
            sp = from_by_name[tp.get("name")]
        elif role and role in from_by_name:
            # sink role label equals source port name (common when export omits role)
            sp = from_by_name[role]
        if sp is None:
            missing.append(key)
            continue
        used_from.add(id(sp))
        pairs[key] = (sp, tp)

    extra: list[str] = []
    for sp in from_ports:
        if id(sp) not in used_from:
            # also try: source role equals a sink name already paired — skip
            extra.append(member_key(sp))
    return pairs, missing, extra


# ---------------------------------------------------------------------------
# Structural checks (single-file attrs)
# ---------------------------------------------------------------------------


def _check_port_attrs(ports: list, path: Path, errors: list[str], *, where: str) -> None:
    by_proto: dict[str, set[str]] = {}
    by_bundle_domain: dict[str, set[str]] = {}
    by_bundle_bus: dict[str, set[str]] = {}

    for idx, port in enumerate(ports or []):
        if not isinstance(port, dict):
            continue
        loc = f"{where}[{idx}]"
        name = port.get("name", "?")

        br = port.get("bus_role")
        if br is not None and br not in BUS_ROLES:
            errors.append(f"{path}: {loc} ({name}): invalid bus_role {br!r}")

        cdc = port.get("cdc")
        if cdc is not None and cdc not in CDC_VALUES:
            errors.append(f"{path}: {loc} ({name}): invalid cdc {cdc!r}")

        proto = port.get("protocol")
        if proto and br:
            by_proto.setdefault(str(proto), set()).add(str(br))

        bundle = port.get("bundle")
        domain = port.get("clock_domain")
        if bundle:
            if domain:
                by_bundle_domain.setdefault(str(bundle), set()).add(str(domain))
            if br:
                by_bundle_bus.setdefault(str(bundle), set()).add(str(br))
            if cdc in {"crossing", "async_handshake"} and not domain:
                errors.append(
                    f"{path}: {loc} ({name}): cdc={cdc} should set clock_domain "
                    f"so the crossing is explicit"
                )

    for proto, roles in sorted(by_proto.items()):
        if len(roles) > 1:
            errors.append(
                f"{path}: protocol '{proto}' has mixed bus_role values {sorted(roles)}; "
                f"one logical bus should share one bus_role"
            )

    for bundle, domains in sorted(by_bundle_domain.items()):
        if len(domains) > 1:
            errors.append(
                f"{path}: bundle '{bundle}' has mixed clock_domain values {sorted(domains)}; "
                f"split bundles or mark CDC on the crossing ports"
            )

    for bundle, roles in sorted(by_bundle_bus.items()):
        if len(roles) > 1:
            errors.append(
                f"{path}: bundle '{bundle}' has mixed bus_role values {sorted(roles)}"
            )


def structural_ip_checks(doc: dict, path: Path, errors: list[str]) -> None:
    if doc.get("kind") != "ip":
        return
    clock_names = clocks_of(doc)
    _check_port_attrs(doc.get("ports") or [], path, errors, where="ports")
    for idx, port in enumerate(doc.get("ports") or []):
        if not isinstance(port, dict):
            continue
        cd = port.get("clock_domain")
        if cd and clock_names and cd not in clock_names:
            errors.append(
                f"{path}: ports[{idx}] ({port.get('name')}): clock_domain '{cd}' "
                f"not in clocks {sorted(clock_names)}"
            )


def structural_subsystem_checks(doc: dict, path: Path, errors: list[str]) -> None:
    if doc.get("kind") != "subsystem":
        return
    exports = doc.get("exports") or {}
    if isinstance(exports, dict):
        _check_port_attrs(exports.get("ports") or [], path, errors, where="exports.ports")

    export_ports = []
    if isinstance(exports, dict):
        export_ports = [p for p in (exports.get("ports") or []) if isinstance(p, dict)]
    bundles = {p.get("bundle") for p in export_ports if p.get("bundle")}

    for idx, link in enumerate(doc.get("links") or []):
        if not isinstance(link, dict):
            continue
        kind = link.get("kind", "port")
        if kind not in CONN_KINDS:
            errors.append(f"{path}: links[{idx}]: invalid kind {kind!r}")
        if kind == "bundle":
            note = link.get("note") or ""
            if not bundles and "bundle" not in note.lower():
                # May still resolve via child loads in cross-file pass
                pass


def structural_soc_checks_local(doc: dict, path: Path, errors: list[str]) -> None:
    """Local (no child load) SoC checks: endpoint shape, clocks/resets/pads, address overlap."""
    if doc.get("kind") != "soc":
        return
    instance_ids = {i.get("id") for i in doc.get("instances") or [] if isinstance(i, dict)}
    clocks = {
        c.get("name") for c in doc.get("clock_tree") or [] if isinstance(c, dict)
    }
    resets = {
        r.get("name") for r in doc.get("reset_tree") or [] if isinstance(r, dict)
    }
    pads = {p.get("name") for p in doc.get("pads") or [] if isinstance(p, dict)}

    pad_widths = {
        p.get("name"): int(p.get("width") or 1)
        for p in doc.get("pads") or []
        if isinstance(p, dict) and p.get("name")
    }

    def _validate_slice(sl: tuple[int, int] | None, width: int | None, loc: str) -> None:
        if sl is None:
            return
        msb, lsb = sl
        if msb < lsb:
            errors.append(f"{path}: {loc}: bad slice [{msb}:{lsb}] (msb < lsb)")
            return
        sw = msb - lsb + 1
        if width is not None:
            if msb >= int(width):
                errors.append(
                    f"{path}: {loc}: slice [{msb}:{lsb}] out of range for width {width}"
                )
            elif sw > int(width):
                errors.append(
                    f"{path}: {loc}: slice width {sw} > port/pad width {width}"
                )

    def check_endpoint(ep: str, side: str, idx: int) -> None:
        loc = f"connections[{idx}].{side}"
        if not isinstance(ep, str) or not ep:
            errors.append(f"{path}: {loc} empty")
            return
        special = parse_special_endpoint(ep)
        if special is not None:
            kind, name, sl = special
            if kind == "const":
                if side != "from":
                    errors.append(f"{path}: connections[{idx}]: const: only allowed on from")
                if sl is not None:
                    errors.append(f"{path}: {loc}: const: does not take a bit-slice")
                return
            if kind == "clock":
                if name not in clocks:
                    errors.append(f"{path}: {loc}: unknown clock '{name}'")
                if sl is not None:
                    errors.append(f"{path}: {loc}: clock: does not take a bit-slice")
                return
            if kind == "reset":
                if name not in resets:
                    errors.append(f"{path}: {loc}: unknown reset '{name}'")
                if sl is not None:
                    errors.append(f"{path}: {loc}: reset: does not take a bit-slice")
                return
            if kind == "pad":
                if name not in pads:
                    errors.append(f"{path}: {loc}: unknown pad '{name}'")
                else:
                    _validate_slice(sl, pad_widths.get(name), loc)
                return
        parsed = parse_inst_endpoint(ep)
        if parsed is None:
            errors.append(
                f"{path}: {loc}: expected instance.port[.slice], "
                f"instance.bundle:<id>, or clock:|reset:|pad:|const:"
            )
            return
        inst, ekind, name, sl = parsed
        if inst not in instance_ids:
            errors.append(f"{path}: {loc}: unknown instance '{inst}'")
            return
        if ekind == "bundle":
            if not name:
                errors.append(f"{path}: {loc}: empty bundle id")
            if sl is not None:
                errors.append(f"{path}: {loc}: bundle endpoints do not take a bit-slice")
            return
        # port — slice bounds checked cross-file when port width known
        if sl is not None:
            msb, lsb = sl
            if msb < lsb:
                errors.append(f"{path}: {loc}: bad slice [{msb}:{lsb}] (msb < lsb)")

    for idx, conn in enumerate(doc.get("connections") or []):
        if not isinstance(conn, dict):
            continue
        check_endpoint(conn.get("from", ""), "from", idx)
        check_endpoint(conn.get("to", ""), "to", idx)
        kind = conn.get("kind", "port")
        if kind not in CONN_KINDS:
            errors.append(f"{path}: connections[{idx}]: invalid kind {kind!r}")

    windows: list[tuple[int, int, str]] = []
    for am in doc.get("address_map") or []:
        if not isinstance(am, dict):
            continue
        base = am.get("base")
        size = am.get("size_bytes")
        region = am.get("region", "?")
        if size is None:
            continue
        if isinstance(base, str):
            try:
                base_i = int(base, 0)
            except ValueError:
                errors.append(
                    f"{path}: address_map region '{region}': bad base {base!r}"
                )
                continue
        elif isinstance(base, int):
            base_i = base
        else:
            continue
        end = base_i + int(size)
        for ob, oe, oregion in windows:
            if base_i < oe and ob < end:
                desc = am.get("description") or ""
                if not desc:
                    errors.append(
                        f"{path}: address_map overlap '{region}' vs '{oregion}' "
                        f"(add description if intentional)"
                    )
        windows.append((base_i, end, str(region)))

    # --- fabric (local) ---
    adapter_ids: set[str] = set()
    for aidx, ad in enumerate(doc.get("adapters") or []):
        if not isinstance(ad, dict):
            continue
        aid = ad.get("id")
        if not aid:
            errors.append(f"{path}: adapters[{aidx}]: missing id")
            continue
        if aid in adapter_ids:
            errors.append(f"{path}: adapters: duplicate id {aid!r}")
        adapter_ids.add(str(aid))
        ak = ad.get("kind")
        if ak not in ADAPTER_KINDS:
            errors.append(f"{path}: adapters[{aidx}] ({aid}): invalid kind {ak!r}")
        maps = ad.get("maps") or []
        if not maps:
            errors.append(f"{path}: adapters[{aidx}] ({aid}): maps must be non-empty")
        for midx, mp in enumerate(maps):
            if not isinstance(mp, dict):
                continue
            if not mp.get("from_role") or not mp.get("to_port"):
                errors.append(
                    f"{path}: adapters[{aidx}].maps[{midx}]: need from_role and to_port"
                )
            wf, wt = mp.get("width_from"), mp.get("width_to")
            if wf is not None and wt is not None and int(wt) > int(wf):
                errors.append(
                    f"{path}: adapters[{aidx}].maps[{midx}]: width_to {wt} > width_from {wf} "
                    f"(narrowing/remap only; widening needs explicit Agent note)"
                )

    fabric_ids: set[str] = set()
    for fidx, fab in enumerate(doc.get("fabric") or []):
        if not isinstance(fab, dict):
            continue
        fid = fab.get("id")
        if not fid:
            errors.append(f"{path}: fabric[{fidx}]: missing id")
            continue
        if fid in fabric_ids:
            errors.append(f"{path}: fabric: duplicate id {fid!r}")
        fabric_ids.add(str(fid))
        fk = fab.get("kind")
        if fk not in FABRIC_KINDS:
            errors.append(f"{path}: fabric[{fidx}] ({fid}): invalid kind {fk!r}")
        sel = fab.get("select", "address")
        if sel not in FABRIC_SELECT:
            errors.append(f"{path}: fabric[{fidx}] ({fid}): invalid select {sel!r}")
        rm = fab.get("ready_merge", "or")
        if rm not in READY_MERGE:
            errors.append(f"{path}: fabric[{fidx}] ({fid}): invalid ready_merge {rm!r}")
        rdm = fab.get("rdata_merge", "mux_by_select")
        if rdm not in RDATA_MERGE:
            errors.append(f"{path}: fabric[{fidx}] ({fid}): invalid rdata_merge {rdm!r}")
        master = fab.get("master", "")
        if not isinstance(master, str) or not master:
            errors.append(f"{path}: fabric[{fidx}] ({fid}): missing master")
        else:
            mp = parse_inst_endpoint(master)
            if mp is None:
                errors.append(
                    f"{path}: fabric[{fidx}] ({fid}): master must be "
                    f"instance.port or instance.bundle:<id>"
                )
            else:
                minst, mkind, mname, msl = mp
                if minst not in instance_ids:
                    errors.append(
                        f"{path}: fabric[{fidx}] ({fid}): unknown master instance '{minst}'"
                    )
                if msl is not None:
                    errors.append(
                        f"{path}: fabric[{fidx}] ({fid}): master must not use bit-slice"
                    )
        slave_ids: set[str] = set()
        fab_windows: list[tuple[int, int, str]] = []
        for sidx, slv in enumerate(fab.get("slaves") or []):
            if not isinstance(slv, dict):
                continue
            sid = slv.get("id")
            if not sid:
                errors.append(f"{path}: fabric[{fidx}].slaves[{sidx}]: missing id")
                continue
            if sid in slave_ids:
                errors.append(
                    f"{path}: fabric[{fidx}] ({fid}): duplicate slave id {sid!r}"
                )
            slave_ids.add(str(sid))
            tgt = slv.get("target")
            if tgt not in instance_ids:
                errors.append(
                    f"{path}: fabric[{fidx}].slaves[{sidx}] ({sid}): "
                    f"unknown target instance {tgt!r}"
                )
            adap = slv.get("adapter")
            if adap is not None and adap not in adapter_ids:
                errors.append(
                    f"{path}: fabric[{fidx}].slaves[{sidx}] ({sid}): "
                    f"unknown adapter {adap!r}"
                )
            match = slv.get("match") or {}
            base, size = match.get("base"), match.get("size_bytes")
            if size is None:
                continue
            try:
                if isinstance(base, str):
                    base_i = int(base, 0)
                elif isinstance(base, int):
                    base_i = base
                else:
                    continue
            except ValueError:
                errors.append(
                    f"{path}: fabric[{fidx}].slaves[{sidx}] ({sid}): bad match.base {base!r}"
                )
                continue
            end = base_i + int(size)
            for ob, oe, osid in fab_windows:
                if base_i < oe and ob < end:
                    note = slv.get("note") or ""
                    if not note:
                        errors.append(
                            f"{path}: fabric[{fidx}] ({fid}): slave windows '{sid}' vs "
                            f"'{osid}' overlap (add note if intentional)"
                        )
            fab_windows.append((base_i, end, str(sid)))




# ---------------------------------------------------------------------------
# Cross-file: instance table + endpoint resolve + bundle + pairing
# ---------------------------------------------------------------------------


def _instance_ref_field(inst: dict, parent_kind: str) -> tuple[str | None, str | None]:
    """Return (ref_string, expect_kind)."""
    if parent_kind == "soc":
        ref = inst.get("ref")
        expect = inst.get("kind") or "auto"
        return (str(ref) if ref else None, expect if expect != "auto" else None)
    # subsystem
    ip = inst.get("ip")
    return (str(ip) if ip else None, "ip")


def build_instance_table(
    doc: dict,
    path: Path,
    store: DocStore,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    """id -> {path, doc, ports, kind}."""
    table: dict[str, dict[str, Any]] = {}
    parent_kind = doc.get("kind")
    for inst in doc.get("instances") or []:
        if not isinstance(inst, dict):
            continue
        iid = inst.get("id")
        if not iid:
            continue
        ref, expect = _instance_ref_field(inst, parent_kind)  # type: ignore[arg-type]
        if not ref:
            errors.append(f"{path}: instance {iid}: missing ref/ip")
            continue
        child_path, child_doc = store.load_ref(
            ref,
            path,
            errors,
            expect_kind=expect,
            via=f"instance {iid}",
        )
        if child_doc is None:
            continue
        child_clocks, child_resets = clock_reset_names(child_doc)
        table[str(iid)] = {
            "path": child_path,
            "doc": child_doc,
            "ports": ports_of(child_doc),
            "clocks": child_clocks,
            "resets": child_resets,
            "kind": child_doc.get("kind"),
            "ref": ref,
        }
    return table


def parse_slice_suffix(token: str) -> tuple[str, tuple[int, int] | None]:
    """Split optional [N] or [M:N] from a port/pad token. Returns (base, slice_or_None)."""
    m = _SLICE_TAIL.match(token)
    if not m:
        return token, None
    body = m.group("body")
    base = m.group("base")
    if ":" in body:
        msb_s, lsb_s = body.split(":", 1)
        msb, lsb = int(msb_s), int(lsb_s)
    else:
        msb = lsb = int(body)
    return base, (msb, lsb)


def slice_width(sl: tuple[int, int] | None) -> int | None:
    if sl is None:
        return None
    msb, lsb = sl
    return msb - lsb + 1


def parse_inst_endpoint(
    ep: str,
) -> tuple[str, str, str, tuple[int, int] | None] | None:
    """
    Parse instance endpoint.
    Returns (instance_id, kind, name, slice) where kind is 'port' | 'bundle'.
    Slice is (msb, lsb) or None. Bundles do not take slices.
    """
    if not isinstance(ep, str) or "." not in ep:
        return None
    if ep.startswith(("clock:", "reset:", "pad:", "const:")):
        return None
    inst, rest = ep.split(".", 1)
    if rest.startswith("bundle:"):
        bid = rest.split(":", 1)[1]
        if "[" in bid:
            return None  # invalid — caller may flag separately
        return inst, "bundle", bid, None
    base, sl = parse_slice_suffix(rest)
    return inst, "port", base, sl


def parse_special_endpoint(
    ep: str,
) -> tuple[str, str, tuple[int, int] | None] | None:
    """Parse clock:|reset:|pad:|const: → (kind, name, slice). const has no slice."""
    if not isinstance(ep, str) or ":" not in ep:
        return None
    prefix, rest = ep.split(":", 1)
    if prefix not in {"clock", "reset", "pad", "const"}:
        return None
    if prefix == "const":
        return prefix, rest, None
    base, sl = parse_slice_suffix(rest)
    return prefix, base, sl


def resolve_endpoint_ports(
    ep: str,
    table: dict[str, dict[str, Any]],
    path: Path,
    loc: str,
    errors: list[str],
    *,
    bundle_hint: str | None = None,
) -> tuple[list[dict], str | None, tuple[int, int] | None]:
    """
    Resolve an instance endpoint to ports.
    Returns (ports, bundle_id_or_None, bit_slice_or_None).
    """
    parsed = parse_inst_endpoint(ep)
    if parsed is None:
        return [], None, None
    iid, ekind, name, sl = parsed
    if iid not in table:
        return [], None, None
    ports = table[iid]["ports"]
    if ekind == "bundle":
        members = bundle_members(ports, name)
        if not members:
            errors.append(
                f"{path}: {loc}: instance '{iid}' has no ports with bundle={name!r} "
                f"(loaded {table[iid]['path']})"
            )
        return members, name, None

    matched = [p for p in ports if p.get("name") == name]
    if matched:
        port = matched[0]
        bid = port.get("bundle")
        if bundle_hint and bid and bid != bundle_hint:
            errors.append(
                f"{path}: {loc}: port '{iid}.{name}' bundle={bid!r} != "
                f"connection bundle {bundle_hint!r}"
            )
        pw = port.get("width")
        if sl is not None and pw is not None:
            msb, lsb = sl
            if msb < lsb:
                errors.append(f"{path}: {loc}: bad slice [{msb}:{lsb}]")
            elif msb >= int(pw):
                errors.append(
                    f"{path}: {loc}: slice [{msb}:{lsb}] out of range for "
                    f"port '{name}' width {pw}"
                )
        return [port], (bid if isinstance(bid, str) else None), sl
    if name in table[iid].get("clocks", set()) or name in table[iid].get("resets", set()):
        if sl is not None:
            errors.append(f"{path}: {loc}: clock/reset '{name}' does not take a bit-slice")
        return [], None, None
    errors.append(
        f"{path}: {loc}: instance '{iid}' has no port/clock/reset '{name}' "
        f"(loaded {table[iid]['path']})"
    )
    return [], None, None


def effective_width(port: dict | None, sl: tuple[int, int] | None, fallback: int | None = None) -> int | None:
    """Width after optional bit-slice."""
    if sl is not None:
        return slice_width(sl)
    if port is not None and port.get("width") is not None:
        return int(port["width"])
    return fallback


def check_bundle_closure(
    path: Path,
    loc: str,
    from_ports: list[dict],
    to_ports: list[dict],
    bundle_id: str | None,
    errors: list[str],
) -> None:
    """Member coverage + width/protocol consistency for kind:bundle."""
    if not bundle_id:
        errors.append(
            f"{path}: {loc}: kind=bundle but could not determine bundle id "
            f"(use instance.bundle:<id> or ports with bundle set)"
        )
        return
    if not from_ports or not to_ports:
        return  # resolve errors already recorded

    pairs, missing, extra = match_bundle_members(from_ports, to_ports)
    if missing:
        errors.append(
            f"{path}: {loc}: bundle '{bundle_id}' incomplete on source vs sink; "
            f"sink members not on source: {missing}"
        )
    if extra:
        errors.append(
            f"{path}: {loc}: bundle '{bundle_id}' source has members not on sink: {extra}"
        )

    for key, (a, b) in sorted(pairs.items()):
        aw, bw = a.get("width"), b.get("width")
        if aw is not None and bw is not None and int(aw) != int(bw):
            errors.append(
                f"{path}: {loc}: bundle '{bundle_id}' member {key}: "
                f"width mismatch {aw} vs {bw}"
            )
        ap, bp = a.get("protocol"), b.get("protocol")
        if ap and bp and ap != bp:
            errors.append(
                f"{path}: {loc}: bundle '{bundle_id}' member {key}: "
                f"protocol mismatch {ap!r} vs {bp!r}"
            )


def complementary_bus_roles(a: str, b: str) -> bool:
    """True if roles are an allowed pair under strategy A."""
    if a == "monitor" or b == "monitor":
        return True  # monitor may attach to either side
    if a == "passthrough" or b == "passthrough":
        return True  # bridge — do not false-fail
    if a in PAIR_ROLES and b in PAIR_ROLES:
        return {a, b} == {"initiator", "target"}
    return True


def representative_bus_role(ports: list[dict]) -> str | None:
    roles = {p.get("bus_role") for p in ports if p.get("bus_role")}
    roles.discard(None)
    if not roles:
        return None
    if len(roles) > 1:
        return "__mixed__"
    return next(iter(roles))  # type: ignore[return-value]


def check_pairing_strategy_a(
    path: Path,
    loc: str,
    from_ports: list[dict],
    to_ports: list[dict],
    errors: list[str],
) -> None:
    """Strategy A: only when both ends have bus_role; require initiator↔target."""
    if not from_ports or not to_ports:
        return
    ra = representative_bus_role(from_ports)
    rb = representative_bus_role(to_ports)
    if ra == "__mixed__" or rb == "__mixed__":
        # same-bundle internal consistency already flagged elsewhere
        return
    if ra is None or rb is None:
        return  # strategy A: missing is OK
    if ra in PAIR_ROLES and rb in PAIR_ROLES:
        if not complementary_bus_roles(ra, rb):
            errors.append(
                f"{path}: {loc}: bus_role pairing failed: {ra}↔{rb} "
                f"(strategy A requires initiator↔target when both ends set "
                f"bus_role in {{initiator,target}})"
            )


def cross_file_connection_checks(
    doc: dict,
    path: Path,
    store: DocStore,
    errors: list[str],
) -> None:
    kind = doc.get("kind")
    if kind not in {"soc", "subsystem"}:
        return

    # Always attempt to resolve instances when present (needed for bundle/pairing).
    # Missing refs only hard-error when a connection/link needs them — load_ref
    # already records resolve failures; we still build the table.
    before = len(errors)
    table = build_instance_table(doc, path, store, errors)
    # If there are no connections needing children, drop pure "cannot resolve"
    # noise? Task: when kind:bundle needs children and missing → error.
    # For any instance.port / bundle endpoint we need the child. If all
    # connections are clock/reset/pad/const only, unused missing refs are
    # still useful warnings — keep as errors for honesty (broken ref graph).

    conn_key = "connections" if kind == "soc" else "links"
    for idx, conn in enumerate(doc.get(conn_key) or []):
        if not isinstance(conn, dict):
            continue
        loc = f"{conn_key}[{idx}]"
        ckind = conn.get("kind", "port")
        frm = conn.get("from", "")
        to = conn.get("to", "")

        needs_inst = False
        for ep in (frm, to):
            if isinstance(ep, str) and parse_inst_endpoint(ep) is not None:
                needs_inst = True

        if not needs_inst:
            continue

        # Infer bundle id from explicit endpoint or connection fields
        bundle_id = None
        for ep in (frm, to):
            parsed = parse_inst_endpoint(ep) if isinstance(ep, str) else None
            if parsed and parsed[1] == "bundle":
                bundle_id = parsed[2]
                break
        if bundle_id is None and ckind == "bundle":
            # allow protocol/note breadcrumb only as last resort — prefer ports
            note = conn.get("note") or ""
            # try protocol-named nothing; leave None and let resolve fill from ports
            _ = note

        from_ports, from_b, from_sl = resolve_endpoint_ports(
            frm, table, path, f"{loc}.from", errors, bundle_hint=bundle_id
        )
        to_ports, to_b, to_sl = resolve_endpoint_ports(
            to, table, path, f"{loc}.to", errors, bundle_hint=bundle_id
        )
        if bundle_id is None:
            bundle_id = from_b or to_b

        # pad:/const: bit-slice width (no ports list)
        from_eff = None
        to_eff = None
        fspecial = parse_special_endpoint(frm) if isinstance(frm, str) else None
        tspecial = parse_special_endpoint(to) if isinstance(to, str) else None
        if fspecial and fspecial[0] == "pad":
            # width from SoC pads — looked up via parent doc only in soc local;
            # re-check slice against pad list on soc
            if doc.get("kind") == "soc":
                for p in doc.get("pads") or []:
                    if isinstance(p, dict) and p.get("name") == fspecial[1]:
                        from_eff = effective_width(
                            {"width": p.get("width") or 1}, fspecial[2]
                        )
                        break
        if tspecial and tspecial[0] == "pad":
            if doc.get("kind") == "soc":
                for p in doc.get("pads") or []:
                    if isinstance(p, dict) and p.get("name") == tspecial[1]:
                        to_eff = effective_width(
                            {"width": p.get("width") or 1}, tspecial[2]
                        )
                        break

        if ckind == "bundle":
            if from_sl is not None or to_sl is not None:
                errors.append(
                    f"{path}: {loc}: kind=bundle cannot use bit-slice endpoints"
                )
            if from_ports and from_b and len(from_ports) == 1:
                iid = parse_inst_endpoint(frm)[0]  # type: ignore[index]
                from_ports = bundle_members(table[iid]["ports"], from_b)
                bundle_id = bundle_id or from_b
            if to_ports and to_b and len(to_ports) == 1:
                iid = parse_inst_endpoint(to)[0]  # type: ignore[index]
                to_ports = bundle_members(table[iid]["ports"], to_b)
                bundle_id = bundle_id or to_b
            if from_b and to_b and from_b != to_b:
                bundle_id = f"{from_b}->{to_b}"
            check_bundle_closure(path, loc, from_ports, to_ports, bundle_id, errors)

        # Strategy A pairing (port or bundle) — skip when bit-slice (partial bus)
        if from_sl is None and to_sl is None:
            check_pairing_strategy_a(path, loc, from_ports, to_ports, errors)

        # Width / protocol on single-port (or pad↔port) connections
        if ckind == "port":
            a = from_ports[0] if len(from_ports) == 1 else None
            b = to_ports[0] if len(to_ports) == 1 else None
            if from_eff is None and a is not None:
                from_eff = effective_width(a, from_sl)
            if to_eff is None and b is not None:
                to_eff = effective_width(b, to_sl)
            cw = conn.get("width")
            if from_eff is not None and to_eff is not None and from_eff != to_eff:
                errors.append(
                    f"{path}: {loc}: endpoint width mismatch {from_eff} vs {to_eff}"
                    + (" (after bit-slice)" if (from_sl or to_sl) else "")
                )
            if cw is not None:
                if from_eff is not None and int(cw) != int(from_eff):
                    errors.append(
                        f"{path}: {loc}: connection width {cw} != from effective width {from_eff}"
                    )
                if to_eff is not None and int(cw) != int(to_eff):
                    errors.append(
                        f"{path}: {loc}: connection width {cw} != to effective width {to_eff}"
                    )
            if a is not None and b is not None and from_sl is None and to_sl is None:
                ap, bp = a.get("protocol"), b.get("protocol")
                cp = conn.get("protocol")
                if ap and bp and ap != bp:
                    errors.append(
                        f"{path}: {loc}: protocol mismatch {ap!r} vs {bp!r}"
                    )
                if cp and ap and cp != ap:
                    errors.append(
                        f"{path}: {loc}: connection protocol {cp!r} != from {ap!r}"
                    )
                if cp and bp and cp != bp:
                    errors.append(
                        f"{path}: {loc}: connection protocol {cp!r} != to {bp!r}"
                    )

    # Fabric adapters: when a slave names an adapter, check to_port exists on target
    if kind == "soc":
        adapters_by_id = {
            a.get("id"): a
            for a in (doc.get("adapters") or [])
            if isinstance(a, dict) and a.get("id")
        }
        for fidx, fab in enumerate(doc.get("fabric") or []):
            if not isinstance(fab, dict):
                continue
            fid = fab.get("id", fidx)
            master = fab.get("master", "")
            mports, _, _ = resolve_endpoint_ports(
                master, table, path, f"fabric[{fidx}].master", errors
            )
            master_roles = {p.get("role") for p in mports if p.get("role")}
            for sidx, slv in enumerate(fab.get("slaves") or []):
                if not isinstance(slv, dict):
                    continue
                adap_id = slv.get("adapter")
                tgt = slv.get("target")
                if not adap_id or tgt not in table:
                    continue
                adap = adapters_by_id.get(adap_id)
                if not adap:
                    continue  # local check already flagged unknown
                tports = table[tgt]["ports"]
                tnames = {p.get("name") for p in tports}
                t_by_name = {p.get("name"): p for p in tports if p.get("name")}
                for midx, mp in enumerate(adap.get("maps") or []):
                    if not isinstance(mp, dict):
                        continue
                    to_port = mp.get("to_port")
                    from_role = mp.get("from_role")
                    if to_port and to_port not in tnames:
                        errors.append(
                            f"{path}: fabric[{fidx}] ({fid}) slave adapter {adap_id!r}: "
                            f"maps[{midx}] to_port {to_port!r} not on instance '{tgt}' "
                            f"(loaded {table[tgt]['path']})"
                        )
                    if from_role and mports and from_role not in master_roles:
                        # soft: master might be bundle with roles — warn as error for honesty
                        errors.append(
                            f"{path}: fabric[{fidx}] ({fid}) slave adapter {adap_id!r}: "
                            f"maps[{midx}] from_role {from_role!r} not on master "
                            f"{master!r} roles {sorted(r for r in master_roles if r)}"
                        )
                    # width_to vs target port width
                    wt = mp.get("width_to")
                    if to_port in t_by_name and wt is not None:
                        pw = t_by_name[to_port].get("width")
                        if pw is not None and int(wt) != int(pw):
                            errors.append(
                                f"{path}: fabric[{fidx}] ({fid}) adapter {adap_id!r} "
                                f"maps[{midx}]: width_to {wt} != target port "
                                f"'{to_port}' width {pw}"
                            )
                    wf = mp.get("width_from")
                    if from_role and wf is not None and mports:
                        for p in mports:
                            if p.get("role") == from_role and p.get("width") is not None:
                                if int(wf) != int(p["width"]):
                                    errors.append(
                                        f"{path}: fabric[{fidx}] ({fid}) adapter {adap_id!r} "
                                        f"maps[{midx}]: width_from {wf} != master role "
                                        f"{from_role!r} width {p['width']}"
                                    )
                                break
                for omit in adap.get("omit_from_roles") or []:
                    if mports and omit not in master_roles:
                        errors.append(
                            f"{path}: fabric[{fidx}] ({fid}) adapter {adap_id!r}: "
                            f"omit_from_roles has {omit!r} not on master"
                        )

    # If we failed to resolve any instance and there was a bundle connect, ensure
    # that showed up (build_instance_table already appended). Silence unused.
    _ = before


# ---------------------------------------------------------------------------
# validate entry
# ---------------------------------------------------------------------------


def validate_file(
    path: Path,
    schema_cache: dict[str, Draft202012Validator],
    store: DocStore,
) -> list[str]:
    errors: list[str] = []
    try:
        doc = load_yaml(path)
    except Exception as exc:  # noqa: BLE001
        return [f"{path}: load error: {exc}"]

    kind = doc.get("kind")
    schema_name = KIND_TO_SCHEMA.get(kind)  # type: ignore[arg-type]
    if not schema_name:
        return [f"{path}: unknown or missing kind {kind!r} (expected ip|subsystem|soc)"]

    if schema_name not in schema_cache:
        try:
            schema = load_schema(schema_name)
            schema_cache[schema_name] = Draft202012Validator(schema)
        except SchemaError as exc:
            return [f"{schema_name}: invalid schema: {exc}"]
        except OSError as exc:
            return [f"{schema_name}: {exc}"]

    validator = schema_cache[schema_name]
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{path}: {loc}: {err.message}")

    structural_ip_checks(doc, path, errors)
    structural_subsystem_checks(doc, path, errors)
    structural_soc_checks_local(doc, path, errors)
    cross_file_connection_checks(doc, path, store, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate MoonGlass_Integration YAML against JSON Schemas, "
            "with optional cross-file bundle closure and bus_role pairing "
            "(strategy A). Not an integrator."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="YAML files (default: examples/ip|subsys|soc/*.yaml)",
    )
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        default=[],
        help=(
            "Extra search root for instance.ref / instance.ip resolution "
            "(repeatable). Also reads MOONGLASS_INTEGRATION_ROOTS "
            f"({os.pathsep}-separated)."
        ),
    )
    parser.add_argument(
        "--no-examples-fallback",
        action="store_true",
        help="Do not fall back to pack examples/ when resolving refs.",
    )
    args = parser.parse_args(argv)
    paths = list(args.paths) if args.paths else iter_default_examples()
    if not paths:
        print("No YAML files to validate.", file=sys.stderr)
        return 1

    search_roots = parse_roots(
        args.root, os.environ.get("MOONGLASS_INTEGRATION_ROOTS")
    )
    store = DocStore(
        search_roots, include_examples=not args.no_examples_fallback
    )
    cache: dict[str, Draft202012Validator] = {}
    all_errors: list[str] = []
    ok = 0
    for path in paths:
        errs = validate_file(path, cache, store)
        if errs:
            all_errors.extend(errs)
            print(f"FAIL  {path}")
        else:
            ok += 1
            print(f"OK    {path}")

    print(f"\n{ok}/{len(paths)} files OK")
    if all_errors:
        print("\nErrors:")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
