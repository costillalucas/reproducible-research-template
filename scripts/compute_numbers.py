#!/usr/bin/env python3
"""compute_numbers.py -- SOLE WRITER of data/numbers.json.

Recomputes every number quoted in report/report.md from the code in
src/ptyco_full_simulator, with a fixed seed, and writes them to the single
registry file that scripts/check_provenance.py checks the report against.
Nothing else writes this file, and the report never writes a number by
hand -- it quotes this registry through the \\srcnum{} / [srcnum:] tags.

TODO: replace the placeholder registry entry below with your real numbers,
computed by calling into src/ptyco_full_simulator. See
examples/pi_estimator/compute_numbers.py for a fuller worked example.

Run: python scripts/compute_numbers.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "data", "numbers.json")


def main():
    registry = {
        "template_wired": {
            "value": 1,
            "statement": "placeholder: the provenance pipeline is wired end to end",
            "type": "derivation",
            "reproduce": "scripts/compute_numbers.py::main",
        },
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(registry, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(f"wrote {os.path.relpath(OUT, ROOT)} ({len(registry)} entries)")


if __name__ == "__main__":
    main()
