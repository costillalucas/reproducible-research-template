"""Build every presentation figure into report/figures/.

    python3 report/make_figures.py            # all figures
    python3 report/make_figures.py fig05 fig10  # only these

Each report/figs_*.py module exposes FIGURES = {"figNN_name": callable}.
Sources: data/*.json (tracked) and results/** (NOT tracked -- figures that
read results/ need that local directory; see each function's docstring).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figstyle  # noqa: E402

MODULES = ["figs_synthetic", "figs_reference", "figs_real"]


def main(only: list[str]) -> int:
    figstyle.apply()
    failures = 0
    for mod_name in MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            print(f"skip {mod_name}: not written yet")
            continue
        for name, fn in mod.FIGURES.items():
            if only and not any(name.startswith(o) for o in only):
                continue
            try:
                path = fn()
                print(f"ok   {name} -> {path.relative_to(figstyle.REPO)}")
            except Exception as exc:  # keep building the rest
                failures += 1
                print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
