#!/bin/bash
# (B) un recorte chico (TAM px crudos, centrado en cada partícula de seleccion.json) reconstruido solo, uno por partícula.
# Mismas opciones que A (2048 ms, NA 0.0747, 160 épocas, --validar). P corridas en paralelo, --nucleos 1 cada una.
# Carpeta de salida por posición: B<TAM>/f<fila>_c<col> (esquina del recorte en px del ROI). Las ya hechas se saltean.
# Uso: correr_B.sh 20 [P]     (o 40)
TAM=${1:-20}; P=${2:-3}
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
OUT=~/Documents/AleYLu/reconstrucciones/2026-11-20/aislar_vs_recortar
mkdir -p $OUT/B$TAM
python3 -c "import json;[print('%d,%d'%tuple(d['rec$TAM'])) for d in json.load(open('$OUT/seleccion.json'))['elegidas']]" |
  xargs -P $P -I{} bash -c '
  rec={}; d='$OUT'/B'$TAM'/f${rec/,/_c}
  [ -f $d/resumen.txt ] && { echo "ya está $d"; exit 0; }
  I=~/Documents/AleYLu/imagenes_tomadas; C=~/Documents/AleYLu/chequeos
  echo "=== $(date +%H:%M:%S) --recorte $rec --tam '$TAM'"
  python3 scripts/reconstruir.py $I/2026-11-18.2048ms --flat $I/2026-11-18.2048ms-sinmuestra --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark \
    --dark $I/2026-11-18.2048ms-dark --centro $C/2026-11-18.2048ms-prueba-0959/centro.json \
    --na 0.0747 --recorte $rec --tam '$TAM' --epocas 160 --validar --nucleos 1 --salida $d > $d.log 2>&1
  echo "=== $(date +%H:%M:%S) $rec fin (código $?)"'
