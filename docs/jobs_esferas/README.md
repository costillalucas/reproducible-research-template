# Briefs de los jobs de la campaña de esferas (2026-07-08)

Intents de agent-team usados o preparados en la sesión del 2026-09-23/24.
Se guardan acá porque el scratchpad de la sesión es temporal.

| Archivo | Estado |
|---|---|
| `j1_intent.txt` | **Corrido.** Job `2026-09-23_181330_derive-esferas-j1-sanity`, congelado, 3 rondas. Salida en `results/esferas_2026-07-08/sanity/`. |
| `j2_intent.txt` | **Corrido.** Job `2026-09-23_190840_derive-esferas-j2-geometria`, congelado, 2 rondas. Salida en `results/esferas_2026-07-08/geometria/`. |
| `j3_intent_base.txt` | **Sin correr, y desactualizado.** Asume 169 LEDs utilizables; la captura sólo tiene 12 con señal. Hay que reescribirlo contra la captura nueva. |
| `j4_intent_base.txt` | **Sin correr, y desactualizado.** Asume esferas monodispersas de 5 µm; en realidad los radios van de 1 a 10 µm con formas irregulares. |
| `j5_intent_base.txt` | **Sin correr.** Depende de J3 y J4. |

## Cuidado con dos cosas del `job` CLI

- El `budget_tokens` por defecto es 400.000, pero una ronda real gasta 5–10 M. El chequeo
  de presupuesto corre *entre* rondas, así que la ronda 1 siempre se ejecuta y después
  todo `job run`/`job resume` es un **no-op silencioso** (sale 0, sin mensaje). Pasar
  `--budget 25000000` al crear, o editar `jobs/<id>/spec.json` antes de reanudar.
- `job resume --say "@archivo"` **no expande el archivo**: guarda la ruta como texto.
  Para mandar un mensaje largo, agregarlo a mano a `jobs/<id>/inbox.jsonl` como
  `{"ts": ..., "text": ...}`. También funciona con el job corriendo.
