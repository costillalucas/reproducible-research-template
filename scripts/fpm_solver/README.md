# fpm_solver

Copias versionadas del solver que usa `scripts/reconstruir.py` (los originales viven en `results/`, que git ignora):

| archivo | original |
|---|---|
| `fpm_red.py` | `results/captura_2026-10-21_500/r500_red/fpm_red.py` (rojo_500 = rojo_centrado + offset del recorte) |
| `cv_common.py` | `results/captura_2026-09-24/j3/common/cv_common.py` |
| `iter_runner.py` | `results/iteraciones_2026-09-30/iter_runner.py` (= `docs/resultados_2026-09-30/iteraciones/iter_runner.py`) |

Solo cambian las rutas al repo (`REPO`/`_REPO`) y que `fpm_red.py` busca `cv_common.py` a su lado.
Verificado el 21/10: con las mismas entradas, `reconstruir.py` da el mismo objeto con estas copias que con los originales.
