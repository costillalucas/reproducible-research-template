"""Recorte, sin reprocesar, de la fila de arriba de docs/resultados_2026-09-29/conjunta/figs/fig3_mapas_t.png
(verdad de la simulación contra la reconstrucción conjunta A1_D1 a 240 épocas), para el apéndice de la charla de 5 minutos.
Solo recorta píxeles: no cambia datos ni escala. Correr desde la raíz del repo:
  python3 report/informe/make_fig_conjunta_recorte.py -> report/informe/img/fig_conjunta_verdad_vs_conjunta.png"""
from PIL import Image
im = Image.open("docs/resultados_2026-09-29/conjunta/figs/fig3_mapas_t.png")
w, h = im.size
im.crop((0, 45, w, 540)).save("report/informe/img/fig_conjunta_verdad_vs_conjunta.png")
print(im.size, "->", (w, 540 - 45))
