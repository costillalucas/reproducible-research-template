#!/usr/bin/env bash
# comparar.sh -- ¿qué época de una reconstrucción es la mejor? (lee los snapshots de ./reconstruir.sh)
#
# Uso:
#   ./comparar.sh                          la reconstrucción más reciente
#   ./comparar.sh 2026-10-21.d_1655        una, por nombre (carpeta en ~/Documents/AleYLu/reconstrucciones)
#   ./comparar.sh A B                      varias superpuestas
# La reconstrucción tiene que haberse corrido con --validar y --guardar-cada N.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONWARNINGS=ignore python3 "$REPO/scripts/comparar.py" "$@"
