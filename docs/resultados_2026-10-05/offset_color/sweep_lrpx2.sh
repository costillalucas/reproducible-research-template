#!/bin/bash
# extensión del barrido lrpx (05/10): rojo primero, full, 40 épocas, como sweep_lrpx.sh
cd "$(dirname "$0")"
date
for v in z102_m258 z102_m267 z102_m276; do
  echo "nice python3 runner.py one $v b_red real_A+init_z98.0_full 40 > logs/${v}_red.log 2>&1"
done | xargs -P 3 -I{} bash -c "{}"
date; echo RED_DONE
