#!/bin/bash
# Lote 13/11: todas las tomas rojas 21x21, flat del mismo día (fondo); vistas 15x15 (filas 10-24, col 8-22) porque el solver tiene la geometría fija en 15x15, config igual al 12/11 (160 ép, --validar)
R=/home/chanoscopio/Documents/LucasC/reproducible-research-template
I=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
V=/home/chanoscopio/Documents/AleYLu/reconstrucciones/lote_2026-11-13/vistas15
O=/home/chanoscopio/Documents/AleYLu/reconstrucciones/lote_2026-11-13
cd $R
for c in 2026-11-13.a 2026-11-13 2026-11-13.med1 2026-11-13.med2 2026-11-13.med3 2026-11-13.med4 2026-11-13.med5 2026-11-13.med6 2026-11-13.med7 2026-11-13.med8 2026-11-13.med9 2026-11-13.med10 2026-11-13.med11 2026-11-13.zonarojo; do
  [ -f $O/$c/resumen.txt ] && continue
  echo "== $c $(date +%H:%M)"
  python3 scripts/reconstruir.py $V/$c --flat $V/2026-11-13.fondo --dark $I/$c-dark --dark-flat $I/2026-11-13.fondo-dark \
     --color r --epocas 160 --guardar-cada 0 --validar --nucleos 3 --salida $O/$c < /dev/null > $O/$c.log 2>&1
  grep -h "C1 R held-out\|^C2\|tiempo:" $O/$c/resumen.txt 2>/dev/null || tail -3 $O/$c.log
done
echo FIN $(date +%H:%M)
