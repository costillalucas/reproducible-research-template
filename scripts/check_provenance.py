#!/usr/bin/env python3
r"""check_provenance.py -- the gate: nothing in the deliverable may be invented.

Two layers, both enforced.

1. Tag layer -- inside the deliverable itself.

     \src{key}            (LaTeX)   /  [src:key]            (markdown/html)
         "this statement is backed by registry entry `key`." Existence
         only: the entry must be well-formed and its `reproduce` path must
         exist on disk.

     \srcnum{key}{value}   (LaTeX)   /  [srcnum:key:value]   (markdown/html)
         "this literal number IS registry entry `key`." Existence, AND the
         displayed literal must agree with the registry's numeric value at
         the literal's own displayed precision (half a unit in its last
         displayed digit) -- the same rule pta-gwb-anisotropy's
         check_provenance.py uses for \dataref.

2. Argument-graph layer -- structure/, modeled directly on
   https://github.com/matiaszaldarriaga/pta-gwb-anisotropy:

     structure/claims.yaml    one record per load-bearing claim
     structure/scripts.yaml   registry of every critical-path script
     structure/outputs.yaml   every output artifact and the claims it supports

   Every cross-reference between these three files, and between them and
   data/numbers.json (the one registry, written solely by
   scripts/compute_numbers.py), must resolve.

Exit 0 and "all checks pass" iff nothing is flagged; nonzero and a list of
issues otherwise.

Run: python scripts/check_provenance.py [path/to/deliverable]
     (defaults to report/report.md)
"""
import glob
import json
import math
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
REGISTRY_PATH = os.path.join(ROOT, "data", "numbers.json")
STRUCTURE = os.path.join(ROOT, "structure")

# entry "type": for check/script/data, `reproduce` is a real repo path and
# is checked to exist; for source/derivation it is free text (a citation, a
# formula, a stdlib name) and is not.
PATH_TYPES = {"check", "script", "data"}
KNOWN_TYPES = PATH_TYPES | {"source", "derivation"}

TAG_SRC = (re.compile(r"\\src\{([^}]+)\}"), re.compile(r"\[src:([^\]]+)\]"))
TAG_SRCNUM = (
    re.compile(r"\\srcnum\{([^}]+)\}\{([^}]+)\}"),
    re.compile(r"\[srcnum:([^:\]]+):([^\]]+)\]"),
)

issues = []


def flag(msg):
    issues.append(msg)


def repo_exists(ref):
    return os.path.exists(os.path.join(ROOT, ref)) or bool(glob.glob(os.path.join(ROOT, ref)))


def displayed_tolerance(literal):
    """Half a displayed unit for a decimal or scientific numeric literal."""
    m = re.fullmatch(
        r"[+-]?(?:\d+(?:\.(\d*))?|\.([0-9]+))(?:[eE]([+-]?\d+))?", literal.strip()
    )
    if not m:
        raise ValueError(f"not a numeric literal: {literal!r}")
    decimals = len(m.group(1) if m.group(1) is not None else m.group(2) or "")
    exponent = int(m.group(3) or 0)
    return 0.5 * 10.0 ** (exponent - decimals)


def check_tags(text, registry):
    keys_used, numnum_used = set(), set()

    for rx in TAG_SRC:
        for match in rx.findall(text):
            for key in match.split(","):
                key = key.strip()
                if key:
                    keys_used.add(key)
    for key in sorted(keys_used):
        if key not in registry:
            flag(f"tag references unknown key {key!r}")
            continue
        entry = registry[key]
        for field in ("statement", "type", "reproduce"):
            if not str(entry.get(field, "")).strip():
                flag(f"registry entry {key!r} missing required field {field!r}")
        etype = str(entry.get("type", "")).strip()
        if etype and etype not in KNOWN_TYPES:
            flag(f"registry entry {key!r} has unknown type {etype!r}")
        if etype in PATH_TYPES:
            repro = str(entry.get("reproduce", "")).split("::", 1)[0].strip()
            if repro and not repo_exists(repro):
                flag(f"registry entry {key!r}: reproduce path not found: {repro!r}")

    for rx in TAG_SRCNUM:
        for key, literal in rx.findall(text):
            key = key.strip()
            numnum_used.add(key)
            if key not in registry:
                flag(f"numeric tag references unknown key {key!r}")
                continue
            entry = registry[key]
            if "value" not in entry:
                flag(f"registry entry {key!r} is used numerically but has no 'value'")
                continue
            try:
                displayed = float(literal)
                tol = displayed_tolerance(literal)
                actual = float(entry["value"])
            except (TypeError, ValueError) as e:
                flag(f"srcnum {key!r}: cannot compare {literal!r}: {e}")
                continue
            slack = 8 * math.ulp(max(abs(actual), abs(displayed), 1e-300))
            if abs(actual - displayed) > tol + slack:
                flag(
                    f"srcnum {key!r}: displayed {literal} does not match "
                    f"registry {actual} at tolerance {tol:g}"
                )

    for key in registry:
        if key not in keys_used and key not in numnum_used:
            print(f"WARN: registry entry {key!r} is never referenced by a tag")

    return keys_used, numnum_used


def check_structure(registry):
    claim_ids = set()

    claims_path = os.path.join(STRUCTURE, "claims.yaml")
    if os.path.exists(claims_path):
        with open(claims_path) as fh:
            claim_list = (yaml.safe_load(fh) or {}).get("claims", [])
        claim_ids = {c["id"] for c in claim_list}
        for c in claim_list:
            for ev in c.get("evidence", []):
                for ref in ev.get("data_refs", []):
                    if not repo_exists(ref):
                        flag(f"claims.yaml [{c['id']}/{ev['id']}]: unresolved data_ref {ref!r}")
            for key in c.get("numbers", []):
                if key not in registry:
                    flag(f"claims.yaml [{c['id']}]: number key {key!r} not in numbers.json")
            for dep in c.get("depends_on", []):
                if dep not in claim_ids:
                    flag(f"claims.yaml [{c['id']}]: unknown depends_on {dep!r}")
    else:
        flag("missing structure/claims.yaml")

    scripts_path = os.path.join(STRUCTURE, "scripts.yaml")
    if os.path.exists(scripts_path):
        with open(scripts_path) as fh:
            script_list = (yaml.safe_load(fh) or {}).get("scripts", [])
        for s in script_list:
            if not repo_exists(s["path"]):
                flag(f"scripts.yaml [{s['id']}]: missing path {s['path']!r}")
    else:
        flag("missing structure/scripts.yaml")

    outputs_path = os.path.join(STRUCTURE, "outputs.yaml")
    if os.path.exists(outputs_path):
        with open(outputs_path) as fh:
            output_list = (yaml.safe_load(fh) or {}).get("outputs", [])
        for o in output_list:
            if not repo_exists(o["source"]):
                flag(f"outputs.yaml [{o['label']}]: missing source {o['source']!r}")
            if "file" in o and not repo_exists(o["file"]):
                flag(f"outputs.yaml [{o['label']}]: missing file {o['file']!r}")
            for cid in o.get("supports_claims", []):
                if cid not in claim_ids:
                    flag(f"outputs.yaml [{o['label']}]: supports_claims {cid!r} not in claims.yaml")
    else:
        flag("missing structure/outputs.yaml")

    return claim_ids


def main(argv):
    deliverable = argv[0] if argv else os.path.join(ROOT, "report", "report.md")
    if not os.path.exists(deliverable):
        print(f"ERROR: deliverable not found: {deliverable}")
        return 2
    with open(deliverable, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    if not os.path.exists(REGISTRY_PATH):
        print(f"ERROR: registry not found: {REGISTRY_PATH} -- run scripts/compute_numbers.py first")
        return 2
    with open(REGISTRY_PATH) as fh:
        registry = json.load(fh)
    if not isinstance(registry, dict):
        flag("data/numbers.json must be a JSON object of key -> entry")
        registry = {}

    keys_used, numnum_used = check_tags(text, registry)
    claim_ids = check_structure(registry)

    if issues:
        print(f"{len(issues)} issue(s):")
        for i in issues:
            print("  -", i)
        return 1
    print(
        f"all checks pass -- {len(keys_used)} \\src tag(s), {len(numnum_used)} "
        f"\\srcnum tag(s), {len(registry)} registry entry(ies), {len(claim_ids)} claim(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
