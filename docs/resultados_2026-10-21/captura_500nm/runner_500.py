"""runner_500.py -- envoltorio de ../captura_2026-10-21/runner_2110.py (sin copiarlo) para la muestra 2026-10-21.500:
registra el dataset r500_red (este directorio) y la variante rojo_500 = rojo_centrado (z 102, lrpx 1.29, NA 0.0669, factor 3, sin
exclusiones) con el offset de filas del recorte 140:540 (centro 340, 220 px arriba del centro del ROI -> +0.374 mm); el offset en
columnas (-0.340 mm, recorte 560:960) está en r500_red/fpm_red.py. out/ queda en este directorio.
Uso: python3 runner_500.py one rojo_500 r500_red TAREA MAXEP"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "captura_2026-10-21"))
import runner_2110 as RR  # noqa: E402
RR.HERE = HERE
RR.IR.DATASETS["r500_red"] = (os.path.join(HERE, "r500_red"), 98.0, "red")
RR.VARIANTS["rojo_500"] = {**RR.VARIANTS["rojo_centrado"], "red": -3.0 + 0.0017 * 220}
# control de signo del offset en columnas (folds a 40 épocas; el valor real lo fija la env R500_XOFF en run_xoff.sh)
for _n in ("r500_x000", "r500_xp034"):
    RR.VARIANTS[_n] = dict(RR.VARIANTS["rojo_500"])
IR, VARIANTS = RR.IR, RR.VARIANTS   # para eval/comun.py y datos_cmp.py
if __name__ == "__main__":
    assert sys.argv[1] == "one"
    print(RR.run_task((sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))), flush=True)
