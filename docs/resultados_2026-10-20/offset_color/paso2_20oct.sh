#!/bin/bash
# 20/10: azul full con la geometría medida (z102_p129) y volumen de fase por color (vol_p129.py) contra base.
cd "$(dirname "$0")"
date; echo PASO2_START
nice python3 runner.py one z102_p129 b_blue real_A+init_z98.0_full 40 > logs/z102_p129_b_blue_full.log 2>&1
nice python3 vol_p129.py 40 > logs/vol_p129.txt 2>&1
date; echo PASO2_DONE
