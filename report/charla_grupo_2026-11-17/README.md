# Charla de grupo · 17/11/2026 · Pticografía de Fourier: minicurso y estado del proyecto

Charla de 40 minutos para todo el grupo (público mixto): unos 25 minutos de minicurso de FPM con tres preguntas al público y unos 13 minutos de resultados de nuestro equipo. Al final hay un anexo con las cuentas de geometría a Fourier y el redondeo en k.

- **Presentación (Slides, privada hasta compartirla):** https://claude.ai/artifact/H3y6cow9rFre3RpnhLkdTG
- **Demos interactivas (públicas):**
  - v2 "Ver, comparar, reconstruir": https://rawcdn.githack.com/costillalucas/reproducible-research-template/a4cdc6186c6efaa88031a97813e71960d90ad800/report/fourier_interactivo_v2/index.html
  - v1 "Una imagen, muchos ángulos": https://rawcdn.githack.com/costillalucas/reproducible-research-template/a4cdc6186c6efaa88031a97813e71960d90ad800/report/fourier_interactivo/index.html

## Contenido

| Carpeta | Qué tiene |
|---|---|
| `deck/project/` | Respaldo del deck tal como quedó publicado: `deck.json` (orden y secciones), `deck.css` y un HTML por slide, con las notas del orador en `<aside>`. Las imágenes se referencian como `/_blob/<id>`, es decir, como recursos del artifact; las mismas figuras están en `figuras/`. |
| `figuras/` | Las figuras usadas en la charla (PNG y el GIF del barrido realzado). |
| `scripts/` | Los scripts de matplotlib/numpy que generan cada figura. Leen datos de `AleYLu/` y de `docs/`/`results/` de este repo, con rutas absolutas de la PC del laboratorio. |
| `capturas_demo/` | Capturas de las demos v1 y v2 y el script de Chrome headless que las generó. |

## Orden de la charla

1. Portada, motivación (campo contra detalle) y mapa.
2. **Minicurso 1, bases:** un LED es un disco en Fourier (montaje con el cono de aceptación), ventanas que se solapan, la apertura manda; pregunta 1 (período mínimo y NA necesaria, en dos clics).
3. **Minicurso 2, iluminación y Fourier:** qué LEDs dan campo claro (sen θ contra NA), campo claro y oscuro, apertura sintética, barrido de 49 LEDs, demo; pregunta 2 (solapamiento: 47 % → 62 % al alejar la matriz).
4. **Minicurso 3, reconstrucción:** ciclo del algoritmo e iteraciones.
5. **Minicurso 4, validación:** pregunta 3 (objeto conocido, C1, C2 y nulo, de a uno) y FRC.
6. **Nuestro equipo:** equipo y criterios, línea de tiempo, bordes y pupila, primer C2 que pasa (0,185 contra 0,008 en el nulo), esferas de 0,5 µm (6,4 → ~5 µm por el campo claro, ~5 → ~3 µm por el campo oscuro, ganancia real ~1,6×), descartes con evidencia (2 slides) y árbol de descartes.
7. **Lo que sigue:** de cada duda, un experimento; próxima toma a z ≈ 143 mm; tres ideas para llevarse.
8. **Anexo:** el microscopio en Fourier con datos reales (FFT del LED (17,16): NA 0,072, sen θ 0,062), los tres pasos de la geometría a Fourier, la pregunta extra del LED de 6 mm, el redondeo en k y la bibliografía.

## Notas

- Las figuras se hicieron con agentes (modelo Fable) a partir de datos reales y simulaciones del repositorio; cada panel dice si es dato real o simulación.
- Corrección hecha durante la preparación: el sobreajuste en verde (entrenamiento baja, validación sube) viene del barrido de magnificación del 19–20/10, no de EPRY. EPRY en rojo da 0,529 contra 0,517 del mejor método sin EPRY (dentro del mismo método mejora de 0,554 a 0,529), y en verde empeora.
- La escala de la regla milimetrada (`AleYLu/regla_milimetrada.tif`) se volvió a medir sobre la imagen cruda: 77,6 px por cada 100 µm, o sea 1,289 µm/px.
