#!/usr/bin/env bash
# puntos.sh -- ¿los puntos finos de una reconstrucción son reales? (los busca en las dos mitades de LEDs)
#
# Uso:
#   ./puntos.sh                          la reconstrucción más reciente que tenga mitades (--validar)
#   ./puntos.sh 2026-10-21.d_1655        una, por nombre (carpeta en ~/Documents/AleYLu/reconstrucciones)
#   ./puntos.sh 2026-10-21.d_1655 --epoca 10    con los snapshots de esa época
#   --umbral 4                           sensibilidad (más bajo = más puntos, más ruido)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONWARNINGS=ignore python3 "$REPO/scripts/puntos.py" "$@"
