#!/bin/bash
# Continúa el estudio tras el reinicio: lanza SOLO los B20 que faltan (correr_B.sh saltea los que ya tienen resumen.txt)
# y rehace la comparación (tabla.csv, resultados.json, figuras). No vuelve a elegir partículas: usa seleccion.json tal cual.
# Al 20/11 17:35 faltaban 4: P08 (596,685), P10 (627,672), P12 (639,742), P15 (678,731)  ~2 min cada uno, 3 en paralelo.
# Opcional (no corrido): B40 de las 15 ->  ./codigo/correr_B.sh 40 3  y después  python3 codigo/comparar2.py .
set -e
cd ~/Documents/AleYLu/reconstrucciones/2026-11-20/aislar_vs_recortar
# corrida a medio hacer (sin resumen.txt) -> se borra para que se rehaga
for d in B20/f*_c*; do [ -d "$d" ] && [ ! -f "$d/resumen.txt" ] && { echo "borro corrida incompleta $d"; rm -rf "$d"; }; done
./codigo/correr_B.sh 20 3 2>&1 | tee -a B20_continuar.log
python3 codigo/comparar2.py . 2>&1 | grep -v -i axes3d | tee comparar.log
