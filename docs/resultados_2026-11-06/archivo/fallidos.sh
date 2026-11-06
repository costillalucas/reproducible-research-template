#!/bin/bash
A=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo; I=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas; cd $A
while pgrep -f "xargs -P 4" >/dev/null || pgrep -f correr_uno.sh >/dev/null; do sleep 10; done
while IFS='|' read n c f d df; do [ -f runs/$n/zonas.json ] && continue; echo "borde_solo $n"; python3 borde_solo.py $n $A/enlaces/$n $I/$d $A/runs > logs/$n.borde.log 2>&1 & done < jobs.txt; wait; echo fin; date
