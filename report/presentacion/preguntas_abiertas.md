# Preguntas abiertas de Lucas (2026-09-23)

Guardadas sin responder, para trabajarlas después. Las dos últimas pueden cambiar
la slide 15 (próximos pasos), así que conviene resolverlas antes de aplicar la
tanda de cambios o, al menos, antes de la presentación final.

1. **¿Cuáles son las mejores métricas cuando SÍ hay ground truth?**
   (Hoy el repo usa `phase_correlation`, `phase_rmse_rad`, `amplitude_correlation`,
   `amplitude_rmse` en `src/ptyco_full_simulator/metrics.py`, con la fase envuelta y
   demediada. Revisar qué conviene realmente y qué se está midiendo mal —ver el techo
   de π— antes de contestar.)

2. **¿Cuáles son las mejores métricas cuando NO hay ground truth?**
   (Hoy: residuo de datos por LED, `convergence_summary`, correlación contra una
   referencia externa —que resultó ciega—, y la validación cruzada dejando LEDs afuera,
   que fue lo más informativo. Pregunta abierta: qué más se puede medir sin verdad.)

3. **Propuesta de Lucas: usar imágenes de esferas de ~5 µm (tamaño conocido) en lugar
   del target USAF.** ¿Sirven como muestra patrón para el test decisivo?

4. **Si se conoce la muestra patrón, ¿no es más fácil ajustar la geometría?**
   (Es decir: usar un objeto conocido para calibrar centro, z, NA y aumento en vez de
   buscar la geometría a ciegas contra los datos, que fue lo que dio el paisaje plano.)

---

## Datos que vamos a usar (indicados por Lucas, 2026-09-23)

`/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-07-08/organizado`, los
directorios `13x13_recortada_400` de `red`, `green` y `blue`.

Lo que se ve sin correr nada:

- **169 archivos por canal** (13 × 13 = 169), `filaNN_colNN.tiff`, ~53 MB por canal.
- Índices: **filas 11–23, columnas 9–21** → el LED central de la grilla es
  **(17, 15)**, el mismo centro nominal que la captura de 2025-12-12.
- Imágenes de **400 × 400, uint16**; en la del centro, valores 227–597 (media 418):
  muy poco rango, hay que mirar el nivel de oscuro antes de nada.
- **No hay JSON de exposiciones** en esa fecha, y las carpetas por tiempo
  (`1ms` … `1000ms`, 38 por canal) están **vacías**. Es decir: no se sabe todavía
  con qué exposición se tomó cada LED de este set, y la normalización por exposición
  fue justo uno de los tres bugs de la campaña anterior. **Hay que preguntarle al
  laboratorio o deducirlo** antes de usar estos datos para cualquier ajuste.
- Existen además `13x13` (sin recortar), `13x13_bis`, y recortes a 200 px.

Pendiente de confirmar con Lucas: que ésta sea la muestra de **esferas de ~5 µm**.

### Lo que aportó Lucas sobre este set (2026-09-23)

- **El centro del arreglo parece ser (fila 18, col 15)**, no el centro geométrico de la
  grilla (17, 15). Es decir, ~1 LED de corrimiento en fila. Verificable con un análisis
  de intensidades (el mismo método que dio 17.45 ± 0.1 / 14.65 ± 0.1 en la captura de
  2025-12-12: radiancia media por LED, transición campo claro / campo oscuro).
  **Importa mucho**: en sintético medio LED de error lleva el residuo de 0.035 a 0.22.
- **Todas las imágenes están tomadas con 1 ms de exposición** (según entiende Lucas;
  conviene confirmarlo). Si es así, este set **no necesita normalización por exposición**:
  desaparece por construcción uno de los tres bugs de la campaña anterior, y sólo queda
  restar el nivel de oscuro (~188 cuentas medidas en la otra cámara/sesión; hay que
  medirlo para ésta).
  Eso también explica el rango chico visto en la imagen del centro (227–597 cuentas):
  con 1 ms fijo, los LEDs de campo oscuro van a estar muy cerca del piso, y hay que
  revisar si tienen señal por encima del ruido de lectura antes de confiar en ellos.
   (Es decir: usar un objeto conocido para calibrar centro, z, NA y aumento en vez de
   buscar la geometría a ciegas contra los datos, que fue lo que dio el paisaje plano.)
