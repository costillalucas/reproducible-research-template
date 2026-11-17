#!/usr/bin/env bash
# Regenera las figuras de la charla en inglés -> ../figuras_en/
# Uso:  bash correr_en.sh            (todo)
#       bash correr_en.sh lab        (solo los que leen AleYLu/: correr en la PC del lab)
#       bash correr_en.sh local      (solo simulaciones: corre en cualquier PC)
cd "$(dirname "$0")" || exit 1
export FIG_LANG=en
# cono_reciclado recorta puente.png y valid_cartas reusa validacion.py: van después de esos dos
LOCAL="puente cono_reciclado montaje porque algoritmo resolucion ventanas validacion valid_cartas descartes figs_q figs_z q3_figs barrido_realzado bfdf"
LAB="exposicion fft_real descartes_figs"
case "${1:-todo}" in lab) S=$LAB;; local) S=$LOCAL;; *) S="$LOCAL $LAB";; esac
for s in $S; do echo "== $s"; python "$s.py" || echo "!! FALLÓ $s"; done
ls ../figuras_en
