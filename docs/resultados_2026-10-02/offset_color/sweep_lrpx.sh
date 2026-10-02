#!/bin/bash
cd "$(dirname "$0")"
date
nice python3 runner.py run z102_m250 3 40 b_red,b_green,b_blue full > logs/z102_m250.log 2>&1
nice python3 runner.py run z102_m242 3 40 b_red,b_green,b_blue full > logs/z102_m242.log 2>&1
date; echo SWEEP_DONE
