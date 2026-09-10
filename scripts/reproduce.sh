#!/usr/bin/env bash
# reproduce.sh -- rebuild every number and check in this example, in order.
#
# When you fork this template onto a real project, keep the shape:
#   compute the registry -> run the correctness suite -> provenance gate
# and just grow each stage.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT"

echo "=== 1/3: recompute the registry (data/numbers.json) ==="
python scripts/compute_numbers.py
echo

echo "=== 2/3: run the correctness suite ==="
python scripts/checks.py
echo

echo "=== 3/3: provenance gate ==="
python scripts/check_provenance.py report/report.md
echo

echo "done."
