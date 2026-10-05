# Pticografía de Fourier: demo interactiva

Abrir `index.html` en un navegador. Es autónomo: no necesita servidor, conexión ni dependencias externas.

- **Capturar:** seleccionar LEDs, reproducir el barrido y comparar intensidades.
- **Fourier:** observar la ventana de frecuencias y la cobertura acumulada.
- **Reconstruir:** siete pantallas, una idea por pantalla, con avance manual mediante **Anterior / Siguiente**. Las ecuaciones están en **Ver la matemática**, cerrado por defecto y al cambiar de pantalla.

## Recorrido de reconstrucción

1. Imagen inicial: captura central → raíz cuadrada de intensidad → amplitud aproximada; fase inicial cero.
2. Elegir LED y pulsar **Simular foto**: esquema del microscopio con matriz de LEDs, muestra estimada, objetivo y cámara.
3. Comparar las tres fotos medidas y las tres predichas (central, campo claro, campo oscuro), en una fila horizontal por panel, con el mismo orden y escala de intensidad.
4. Localizar el residual: naranja sobra, azul falta, oscuro coincide.
5. Pulsar **Llevar corrección a Fourier** y después **Sumar corrección a la estimación**. Se ve el espectro antes/después, con igual escala logarítmica y la ventana activa señalada. La suma es compleja, no una suma de brillos. Al aplicarla aparecen puntitos blancos esquemáticos dentro de la ventana: señalan el cambio, no representan datos medidos ni valores exactos del gradiente.
6. Pulsar **Aplicar corrección** y comparar amplitud y fase antes/después. Se puede deshacer la visualización para repetirla.
7. Recién aquí aparecen la curva de pérdida, el deslizador de iteraciones y **Ver el ciclo completo**. La corrida usa 0,9 segundos por subpaso (antes 1,2; un 33 % más rápida). La reproducción es opcional, puede pausarse y se detiene al completar 30 iteraciones.

No hay avance automático de pantallas. Las flechas permiten recorrerlas cuando el foco está fuera de los controles. Los siete indicadores superiores también permiten navegar. Las animaciones de recorrido respetan la preferencia de movimiento reducido.

## Modelo y optimización

El modelo didáctico usa FFT unitaria, una muestra delgada de 128 × 128, ventanas circulares desplazadas de radio 18 bins, pasos de iluminación de 10 bins y 49 capturas ideales, sin ruido ni aberraciones. Implementa de forma autónoma la pérdida de amplitud y el descenso incremental descritos en `src/ptyco_full_simulator/reconstruction.py`:

```text
S = Fourier(objeto)
z_j = A_j S
r_j = |z_j| - sqrt(I_j)
L_j = sum(r_j²)
g_j = A_j† [r_j z_j / max(|z_j|, 1e-12)] = ∂L_j/∂S*
S_nuevo = S - μ g_j
μ_t = 0.8 (1 - exp(-0.3 t)), t = 1…30
```

Las pantallas 1–6 muestran una primera actualización aislada desde la inicialización, seleccionable entre tres LEDs. Se usa la misma referencia de fase cero antes/después. La pantalla 7 ilustra una corrida completa desde la misma inicialización, en orden del centro hacia afuera: no continúa literalmente el paso aislado. Cada vuelta animada resume una iteración de 49 LEDs. Los estados de la imagen y de la curva se actualizan juntos al completar una iteración. La fase global de esa corrida se alinea con el objeto conocido solo para visualizar; la referencia no interviene en el gradiente.

La FFT unitaria y el inicio de la rampa en t=1 difieren del solver del proyecto; no deben transferirse los valores de paso entre ambas convenciones. Esta demo no reproduce la pérdida de intensidad ni la relajación de ruido del WFP original de Bian.

El residual usa escala fija ±0,25, con saturación fuera del rango. El módulo del gradiente se realza individualmente. La amplitud se muestra de 0 a 1; la fase, de 0 a 1 rad (violeta a amarillo), con saturación fuera del rango. Un único paso puede producir cambios visuales pequeños.

El error relativo de amplitud baja aproximadamente de 8,83 % a 1,25 %. Su cuadrado es la pérdida global relativa graficada. No equivale al error del objeto ni garantiza recuperar la fase suave.

## Regeneración y validación

Desde la raíz del repositorio:

```bash
python3 report/fourier_interactivo/generate.py
```

Requiere NumPy y Pillow. `template.html` contiene la interfaz; el generador incorpora las imágenes al HTML final (~1,4 MiB). No usa capturas experimentales ni sustituye los pipelines del proyecto.

El generador verifica por diferencias finitas la derivada direccional compleja, la disminución de pérdida local en actualizaciones seleccionadas, la ausencia de cambios fuera de la ventana activa y la reducción del error global. La interfaz se verifica en Chrome: navegación manual, acciones guiadas, selección de LED, antes/después, matemática opcional, curva solo al final, reproducción y parada, y ancho móvil.

Referencias:

- Zheng et al. (2013): https://www.nature.com/articles/nphoton.2013.187
- Bian et al. (2015): https://doi.org/10.1364/OE.23.004856
