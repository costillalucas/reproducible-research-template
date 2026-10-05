# Fourier interactivo · versión 2

Abrir `index.html` directamente en un navegador. El HTML incluye todas las imágenes y funciona sin conexión. La versión 1 permanece en `../fourier_interactivo/`; esta versión se genera de forma independiente.

## Recorrido

Catorce pantallas con navegación manual, cinco capítulos y un mapa del proceso. Cada panel tiene «¿Qué estoy viendo?». Las fórmulas permanecen en «Ver la matemática», cerrado al cambiar de pantalla. No se avanza automáticamente.

| Pantalla | Interacción | Idea |
| --- | --- | --- |
| 1. La muestra | Absorción, fase o ambas | Amplitud y fase son propiedades distintas |
| 2. Frecuencias | Tamaño y orientación de franjas | El detalle tiene una posición en Fourier |
| 3. Apertura | Cambiar el radio de pupila | El objetivo filtra el campo antes de medir intensidad |
| 4. Ángulo | LED central u oblicuo | El mismo objetivo admite otra región de frecuencias |
| 5. Capturas | Matriz de 49 LEDs, barrido con pausa, cobertura acumulada y contraste | Un LED sincroniza captura y ventana; campo claro y oscuro |
| 6. Solapamiento | LEDs vecinos o separados | Dos capturas dependen de frecuencias compartidas |
| 7. Pistas de fase | Activar solo una distribución de fase | La fase espacial puede influir en intensidades filtradas |
| 8. Inicialización | Comparación visual | La amplitud inicial se aproxima con √Icentral |
| 9. Predicción | Elegir LED → Simular foto → comparar tres parejas horizontales | La predicción sale del microscopio aplicado a la estimación |
| 10. Residual | Seleccionar un LED | La diferencia de módulos guía la corrección |
| 11. Fourier | Llevar residual a Fourier → sumar corrección; ambos pasos reversibles | El residual y la fase estimada producen una corrección en la ventana activa |
| 12. Efectos compartidos | Corregir con un LED; comparar las tres predicciones | Mejorar una captura puede empeorar otra |
| 13. Objeto | Antes/después | Un paso modifica amplitud y fase |
| 14. Iteración | Reproducir, pausar, deslizar y comparar opcionalmente con la muestra conocida | Examinar el ajuste y los errores que persisten |

Las tres muestras tienen sus propias 49 capturas y reconstrucciones de 30 iteraciones. La selección de la primera pantalla se mantiene en capturas y reconstrucción. Las franjas y la pantalla «La fase deja pistas» son ejemplos conceptuales separados, señalados en sus ayudas. La onda dibujada en la primera pantalla es un esquema.

El barrido opcional de captura usa 900 ms por LED, permite pausar y reiniciar, y se detiene en el último LED. Solo acumula ventanas efectivamente visitadas; cambiar manualmente de LED pausa el barrido. La captura y la ventana activa comparten siempre el LED.

La cabecera identifica la muestra y el LED del paso; los ejemplos independientes están rotulados. En móvil, la navegación vuelve al título. Los LEDs tienen blancos de pulsación de 30 × 30 px. Se conserva el foco al actualizar controles y el deslizador de iteración mantiene su nodo durante el arrastre.

La animación final usa 900 ms por subpaso; cada ciclo visual resume una iteración de 49 LEDs. El avance de las pantallas es siempre manual. Las flechas navegan cuando el foco está fuera de los controles. El movimiento ilustrativo respeta la preferencia de movimiento reducido.

## Modelo científico

- Muestra delgada, campo escalar, un LED coherente a la vez, sin ruido ni aberraciones.
- Grilla 128 × 128; FFT unitaria. Pupila de radio 18 bins y pasos de iluminación de 10 bins.
- En coordenadas del objeto, la ventana está centrada en −q. El dibujo de la luz directa en la pupila usa coordenadas del objetivo, con desplazamiento +q.
- La demostración angular usa franjas de frecuencia 26: el LED central no transmite los picos laterales; q = −10 permite pasar el término central y el pico +26. La intensidad adquiere contraste sin aumentar la apertura.
- Las máscaras discretas determinan el solapamiento; se informa intersección / área de una máscara. Dos LEDs sin intersección directa podrían estar conectados por otros LEDs en una adquisición completa.
- La muestra «solo fase» tiene amplitud uniforme de 0,86 y fase espacial variable; no tiene modulación espacial de absorción.

Se minimiza una pérdida de amplitud con descenso incremental de Wirtinger:

```text
z_j = A_j S
r_j = |z_j| - sqrt(I_j)
g_j = A_j† [r_j z_j / max(|z_j|, 1e-12)] = ∂L_j/∂S*
S_nuevo = S - μ g_j
```

Los pasos aislados usan μ = 0,3 desde la estimación inicial. Para cada uno se recalculan las predicciones de los tres LEDs de referencia. El ciclo completo empieza de nuevo desde la misma inicialización, recorre los 49 LEDs en orden del centro hacia afuera y usa μ_t = 0,8 (1 − exp(−0,3 t)), t = 1…30. La fórmula sigue la variante de amplitud del solver del proyecto; no es una reproducción de la pérdida de intensidad ni la relajación de ruido del WFP original de Bian. Sus escalas de paso no son intercambiables con las del solver de FFT no unitaria.

La fase del antes/después usa una referencia común. La fase global de la corrida completa se alinea con la muestra conocida para visualizar; la muestra conocida no se usa en el gradiente. Las pérdidas locales se dividen por la suma de intensidades de cada LED; la global usa la suma de todas las intensidades. Una pérdida cercana a cero no garantiza exactitud del objeto. No se muestran porcentajes de cambio sobre una base numéricamente nula.

## Escalas de visualización

- Amplitud: 0 a 1, negro a blanco.
- Fase: −1,5 a +1,5 rad; azul, oscuro en cero, naranja. Saturación fuera de rango.
- Residual: −0,25 a +0,25; misma paleta firmada.
- Espectro: log(1 + |S|), con igual escala antes/después de corregir.
- Corrección: módulo con contraste individual. Los puntos blancos señalan esquemáticamente el cambio; no son valores medidos ni una discretización del gradiente.
- Capturas: escala común, con realce individual opcional y rotulado.
- Predicciones comparadas: realce por LED, compartido entre medición, antes y después. No se comparan los brillos entre LEDs.

## Reproducir y verificar

```bash
python3 report/fourier_interactivo_v2/generate.py
node report/fourier_interactivo_v2/check_browser.cjs
```

El generador requiere NumPy y Pillow. La prueba del navegador requiere Node 22 o posterior y Chrome (`CHROME_BIN` permite cambiar su ejecutable); no requiere npm. Inicia Chrome sin interfaz y guarda capturas de verificación en `/tmp/fpm-v2-*.png`. Puede necesitar autorización fuera del sandbox.

El generador verifica el gradiente complejo por diferencias finitas, descenso local, soporte de la actualización, disminución del error global, ausencia/presencia de contraste en el ejemplo angular y solapamiento nulo/no nulo.

Resultados deterministas de la corrida: error relativo de amplitudes inicial → final (raíz de la pérdida global):

| Muestra | Inicial | Final |
| --- | ---: | ---: |
| Amplitud | 8,57 % | 2,34 % |
| Fase | 3,97 % | 0,53 % |
| Mixta | 9,15 % | 1,70 % |

La prueba de Chrome verifica las 14 pantallas, las tres muestras, predicción guiada, corrección en dos pasos, cobertura de 49 LEDs, pausa y parada, foco de teclado, deslizadores, etiqueta de repetición final y comparación con la referencia en iteraciones 0, 15 y 30. Comprueba navegación y ausencia de desbordamiento en escritorio y móviles de 390 y 320 px, retorno al título y movimiento reducido. Selecciona una pestaña de tipo `page` para evitar conectar con una extensión de Chrome.

Fuentes: [Zheng, Horstmeyer y Yang (2013)](https://www.nature.com/articles/nphoton.2013.187), [Bian et al. (2015)](https://doi.org/10.1364/OE.23.004856).
