#!/usr/bin/env bash
# reconstruir.sh -- reconstrucción FPM de una captura 15x15, sin escribir rutas (mismo estilo que chequeo.sh).
#
# Uso (desde cualquier lado):
#   ./reconstruir.sh                              la carpeta de muestra más reciente de imagenes_tomadas
#   ./reconstruir.sh 2026-10-21.500               una carpeta por nombre (o una ruta completa)
#   ./reconstruir.sh 2026-10-21.500 --validar     además valida con 2 mitades de LEDs (mismo tiempo, usa 3 núcleos)
#   ./reconstruir.sh 2026-10-21.500 --recorte 140,560      recorte de 400 px con esquina sup. izq. en fila 140, col 560 del ROI
#   ./reconstruir.sh 2026-10-21.500 --recorte auto         recorte sugerido (evita manchas oscuras, saturados y polvo)
#   ./reconstruir.sh 2026-10-21.500 --epocas 40            más rápido (~3 min); por defecto 160 (~12-14 min)
#   ./reconstruir.sh --validar                    opciones sin carpeta = la más reciente
# Otras opciones: --tam 400 (lado del recorte en px), --color r|g|b (solo el rojo está calibrado), --nucleos 3,
#   --offset-roi X,Y (OffsetX,OffsetY del ROI de esa toma; por defecto se lee de <carpeta>/captura.json con scripts/leer_offset.py).
#
# Busca los darks (<carpeta>-dark, si no <fecha>-dark) y el flat (<carpeta>-sinmuestra, si no <fecha>-sinmuestra);
# los darks del flat son los <fecha>-dark. Resultados en ~/Documents/AleYLu/reconstrucciones/<carpeta>_<HHMM>/.

set -u
IMAGENES="${IMAGENES:-$HOME/Documents/AleYLu/imagenes_tomadas}"
SALIDA_BASE="${SALIDA_BASE:-$HOME/Documents/AleYLu/reconstrucciones}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REC="$REPO/scripts/reconstruir.py"
export PYTHONWARNINGS=ignore

# carpetas que no son de muestra
es_auxiliar() { [[ "$1" =~ (dark|sinmuestra|sinluz|visionpoint|chequeo) ]]; }

# 1) qué carpeta reconstruir (el primer argumento, si no empieza con --)
if [[ $# -ge 1 && "$1" != --* ]]; then
    if [[ -d "$1" ]]; then CARPETA="$(cd "$1" && pwd)"; else CARPETA="$IMAGENES/$1"; fi
    shift
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
    echo "No encuentro la carpeta de imágenes ('${CARPETA:-la más reciente}' en $IMAGENES)."
    echo "Uso: ./reconstruir.sh   o   ./reconstruir.sh <nombre de carpeta> [--validar] [--recorte F,C] [--epocas N]"
    exit 1
fi
NOMBRE="$(basename "$CARPETA")"
FECHA="${NOMBRE:0:10}"

# 2) darks y flat: primero los propios de la carpeta, después los del día
DARK=""; DARKF=""; FLAT=""
for c in "$IMAGENES/$NOMBRE-dark" "$IMAGENES/$FECHA-dark" "$IMAGENES"/"$FECHA"*muestrasinluz* "$IMAGENES"/"$FECHA"*dark*; do
    [[ -d "$c" ]] && { DARK="$c"; break; }
done
for c in "$IMAGENES/$NOMBRE-sinmuestra" "$IMAGENES/$FECHA-sinmuestra" "$IMAGENES"/"$FECHA"*luzsinmuestra* "$IMAGENES"/"$FECHA"*sinmuestra*; do
    [[ -d "$c" && "$c" != "$CARPETA" ]] && { FLAT="$c"; break; }
done
for c in "${FLAT%-sinmuestra}-dark" "$IMAGENES/$FECHA-dark" "$IMAGENES"/"$FECHA"*muestrasinluz* "$DARK"; do
    [[ -n "$c" && -d "$c" ]] && { DARKF="$c"; break; }
done
if [[ -z "$DARK" ]]; then
    echo "  [CORREGIR] No hay carpeta de darks para $NOMBRE ($NOMBRE-dark o $FECHA-dark): tomá darks (luz apagada)."; exit 1
fi
if [[ -z "$FLAT" ]]; then
    echo "  [CORREGIR] No hay flat ($FECHA-sinmuestra): tomarlo sin muestra, con las mismas LEDs."; exit 1
fi

SALIDA="$SALIDA_BASE/${NOMBRE}_$(date +%H%M)"; mkdir -p "$SALIDA"
LOG="$SALIDA/registro.txt"

{
echo "=================================================================="
echo " Reconstrucción de: $NOMBRE   $(date '+%d/%m %H:%M')"
echo " darks muestra: $DARK"
echo " darks flat:    $DARKF"
echo " flat:          $FLAT"
echo " opciones:      ${*:-(por defecto: recorte de 400 px sobre el eje óptico, 160 épocas, sin validar)}"
echo "=================================================================="
python3 "$REC" "$CARPETA" --flat "$FLAT" --dark "$DARK" --dark-flat "$DARKF" --salida "$SALIDA" "$@"
echo "CODIGO_SALIDA $?"
} 2>&1 | tee "$LOG"

echo
echo "=================== RESUMEN ==================="
if ! grep -q "CODIGO_SALIDA 0" "$LOG"; then
    echo "  ! La reconstrucción NO terminó. Mirá el mensaje de error de arriba (también en $LOG)."
    grep -E "ERROR|Error" "$LOG" | tail -3 | sed 's/^/    /'
    exit 1
fi
if grep -q "\[AVISO\]\|\[SUGERENCIA\]" "$LOG"; then
    echo "  Avisos:"
    grep "\[AVISO\]\|\[SUGERENCIA\]\|^     - " "$LOG" | sed 's/^ *\[\(AVISO\|SUGERENCIA\)\] */    - /'
fi
grep -E "^(ROI cámara|R de ajuste|C1 R held-out|    -> C1|C3 )" "$LOG" | sed 's/^ */  /'
echo "  Resultados en: $SALIDA"
echo "    reconstruccion.png  la figura: crudo vs amplitud vs fase (arriba el recorte entero, abajo zoom del centro)"
echo "    resumen.txt         parámetros usados, tiempos y métricas explicadas"
echo "    objeto_complejo.npy el objeto reconstruido (complejo)"
