#!/usr/bin/env bash
# chequeo.sh -- corre los chequeos de precaptura.py sobre la última carpeta de imágenes, sin escribir rutas.
#
# Uso (desde cualquier lado):
#   ./chequeo.sh                       la carpeta más reciente de imagenes_tomadas
#   ./chequeo.sh 2026-10-21.500        una carpeta por nombre (o una ruta completa)
#   OFFSET_MANUAL=4000,1942 ./chequeo.sh   forzar el offset del ROI (si no, lo lee de captura.json o del proyecto)
#
# Busca solo los darks y el flat: primero los propios (<carpeta>-dark, <carpeta>-sinmuestra), si no los del día.
# Si la carpeta tiene menos de 225 LEDs la toma como "de prueba": corre centrado y exposición.
# Si tiene la grilla completa corre además el control final (qc).
# Las figuras, el CSV y el registro quedan en ~/Documents/AleYLu/chequeos/<carpeta>/.

set -u
IMAGENES="${IMAGENES:-$HOME/Documents/AleYLu/imagenes_tomadas}"
SALIDA_BASE="${SALIDA_BASE:-$HOME/Documents/AleYLu/chequeos}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRE="$REPO/scripts/precaptura.py"
export PYTHONWARNINGS=ignore

# carpetas que no son de muestra
es_auxiliar() { [[ "$1" =~ (dark|sinmuestra|sinluz|visionpoint|chequeo) ]]; }

# 1) qué carpeta revisar
if [[ $# -ge 1 ]]; then
    if [[ -d "$1" ]]; then CARPETA="$(cd "$1" && pwd)"; else CARPETA="$IMAGENES/$1"; fi
else
    CARPETA=""
    for d in $(ls -td "$IMAGENES"/*/ 2>/dev/null); do
        n="$(basename "$d")"
        es_auxiliar "$n" && continue
        ls -d "$d"fila*_col* >/dev/null 2>&1 || continue
        CARPETA="${d%/}"; break
    done
fi
if [[ -z "$CARPETA" || ! -d "$CARPETA" ]]; then
    echo "No encuentro la carpeta de imágenes ('${1:-la más reciente}' en $IMAGENES)."
    echo "Uso: ./chequeo.sh   o   ./chequeo.sh <nombre de carpeta>"
    exit 1
fi
NOMBRE="$(basename "$CARPETA")"
FECHA="${NOMBRE:0:10}"

# 2) darks y flat del mismo día
DARK=""; FLAT=""
for c in "$CARPETA-dark" "$IMAGENES/$FECHA-dark" "$IMAGENES"/"$FECHA"*dark* "$IMAGENES"/"$FECHA"*muestrasinluz*; do
    [[ -d "$c" ]] && { DARK="$c"; break; }
done
for c in "$CARPETA-sinmuestra" "$IMAGENES/$FECHA-sinmuestra" "$IMAGENES"/"$FECHA"*luzsinmuestra* "$IMAGENES"/"$FECHA"*sinmuestra*; do
    [[ -d "$c" && "$c" != "$CARPETA" ]] && { FLAT="$c"; break; }
done
NLED=$(ls -d "$CARPETA"/fila*_col* 2>/dev/null | wc -l)

# 3) offset del ROI: el que guardó la captura (captura.json); si no hay, el del proyecto de la cámara
if [[ -n "${OFFSET_MANUAL:-}" ]]; then
    OFFSET="$OFFSET_MANUAL"; ORIGEN_OFFSET="indicado a mano"
else
    read -r OFFSET ORIGEN_OFFSET < <(python3 "$REPO/scripts/leer_offset.py" "$CARPETA")
    ORIGEN_OFFSET="${ORIGEN_OFFSET//_/ }"
fi

SALIDA="$SALIDA_BASE/$NOMBRE"; mkdir -p "$SALIDA"
LOG="$SALIDA/chequeo_$(date +%H%M).txt"

{
echo "=================================================================="
echo " Chequeo de: $NOMBRE   ($NLED LEDs)   $(date '+%d/%m %H:%M')"
echo " darks: ${DARK:-NO ENCONTRADOS}"
echo " flat:  ${FLAT:-no encontrado}"
echo " ROI:   OffsetX,OffsetY = $OFFSET  (de: $ORIGEN_OFFSET)"
echo "=================================================================="

echo; echo "---------- 1. CENTRADO ----------"
python3 "$PRE" centro "$CARPETA" --offset "$OFFSET" ${DARK:+--dark "$DARK"} --png "$SALIDA/centro.png"
[[ -f "$SALIDA/centro.json" ]] && cp "$SALIDA/centro.json" "$SALIDA_BASE/centro_actual.json"

echo; echo "---------- 2. EXPOSICIÓN ----------"
if [[ -n "$DARK" ]]; then
    python3 "$PRE" exposicion "$CARPETA" --dark "$DARK" --png "$SALIDA/exposicion.png"
    # solo la toma de prueba define el plan: con la grilla completa no se pisa, porque el flat tiene que
    # tomarse con las mismas exposiciones que la muestra (pasó el 22/10)
    if [[ -f "$SALIDA/exposicion.csv" && $NLED -lt 225 ]]; then
        cp "$SALIDA/exposicion.csv" "$SALIDA_BASE/plan_actual.csv"
        echo "  Plan de tiempos y frames guardado en $SALIDA_BASE/plan_actual.csv"
        echo "  (lo usa iluminacion_con_toma_de_imagene.py con USAR_PLAN = True)"
    elif [[ -f "$SALIDA/exposicion.csv" ]]; then
        echo "  Grilla completa: plan_actual.csv NO se actualiza (el flat usa el mismo plan que la muestra)."
        echo "  La sugerencia de arriba queda en $SALIDA/exposicion.csv por si se quiere para otra toma."
    fi
else
    echo "  [CORREGIR] No hay carpeta de darks para $FECHA: tomá darks (luz apagada) y volvé a correr."
fi

if [[ $NLED -ge 225 ]]; then
    echo; echo "---------- 3. CONTROL FINAL (qc) ----------"
    python3 "$PRE" qc "$CARPETA" ${FLAT:+--flat "$FLAT"} ${DARK:+--dark "$DARK"} --png "$SALIDA/qc.png"
    [[ -z "$FLAT" ]] && echo "  [CORREGIR] No hay flat ($FECHA-sinmuestra): tomarlo al final, sin muestra."
else
    echo; echo "  (toma de prueba: $NLED LEDs, el control final se corre con la grilla completa de 225)"
fi
} 2>&1 | tee "$LOG"

echo
echo "=================== RESUMEN: QUÉ HACER ==================="
if grep -q "CORREGIR" "$LOG"; then
    grep "CORREGIR" "$LOG" | sed 's/^ *\[CORREGIR\] */  - /'
else
    echo "  Todo OK. Se puede seguir con la toma."
fi
if grep -qi "Traceback\|Error" "$LOG"; then
    echo "  ! Hubo un error del script (ver arriba). Copiá el mensaje y consultalo."
fi
echo "  Figuras, tabla CSV y este registro en: $SALIDA"
