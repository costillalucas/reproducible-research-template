# Fourier V1 · presentación editable

- `fourier_v1_editable.pptx`: 18 diapositivas 16:9, con textos, flechas, esquemas y curva editables. Imágenes PNG reutilizadas del HTML V1.
- `fourier_v1_editable.pdf`: vista previa exportada con LibreOffice.
- `generate_pptx.py`: generador reproducible; requiere `python-pptx`. Lee `../index.html` y no vuelve a simular la física.

Incluye captura, realce de campo oscuro, ventanas y cobertura en Fourier, solapamiento, inicialización, predicción, comparación, residual, corrección, actualización e iteraciones. Las fórmulas y precisiones científicas adicionales están en las notas del orador. La comparación final utiliza la referencia conocida de la V1 solo para visualizar.

Regeneración desde la raíz del repositorio, con python-pptx instalado:

```bash
python3 report/fourier_interactivo/presentacion/generate_pptx.py
```

Verificación: 18 diapositivas abiertas y exportadas con LibreOffice; revisión visual de todas las páginas; elementos dentro del área de diapositiva; paquete XML y curva editable comprobados. No se ha probado en Microsoft PowerPoint. Fuente: Liberation Sans (puede sustituirse al abrir en otro equipo).

Escalas heredadas de V1: amplitud 0–1; fase 0–1 rad, saturada fuera del rango; residual ±0,25. La fase global de las iteraciones se alinea para visualizar. Un buen ajuste de intensidades no garantiza exactitud del objeto. No incluye animaciones ni videos; el HTML conserva la interactividad.
