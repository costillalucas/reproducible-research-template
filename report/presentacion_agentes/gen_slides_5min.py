"""Versión CORTA (5 minutos) de la charla, en castellano. No toca el deck de 14 slides.

Formato pedido por los organizadores: Problema/pregunta, Resultado principal, Validación, Experiencia/aprendizaje.
Números: solo los que ya están en report/resumen/resumen.md y data/numbers.json (claves resumen_*).

Uso (desde cualquier carpeta):
  python3 report/presentacion_agentes/gen_slides_5min.py
      -> presentacion_5min.html, presentacion_5min.pdf (1920x1080, Chrome headless), notas_del_orador_5min.txt
  ONLINE=1 python3 report/presentacion_agentes/gen_slides_5min.py <carpeta>
      -> <carpeta>/project/deck.json y <carpeta>/project/slides/*.html, con recuadros punteados
         (alt "... (archivo NOMBRE.png)") en lugar de las figuras locales, como el deck online.
"""
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ONLINE = bool(os.environ.get("ONLINE"))
DARK, LIGHT, LIGHT2, INK, BODY, MUTED, ACC, ACC2, LINE = "#14213D", "#FBFBF8", "#F1F0EA", "#14213D", "#3D4A5C", "#6A7382", "#D9692B", "#2F6FB0", "#DDDBD2"
PEACH = "#F6D9C6"
SANS = "'IBM Plex Sans', Arial, sans-serif"; SERIF = "'Source Serif 4', Georgia, serif"
IMG = "file://" + os.path.normpath(os.path.join(HERE, "..", "informe", "img")) + "/"
N = 6


def sec(id, body, notes, bg=LIGHT, fg=INK, n=None, extra="", gap=48):
    lab = n if isinstance(n, str) else f"{n} / {N}"  # apéndice: rótulo "A1" en vez de "n / N"
    foot = f'<p style="position:absolute; left:128px; bottom:64px; width:600px; font-size:24px; color:{MUTED}">{lab}</p>' if n else ""
    return (f'<section id="{id}" data-transition="fade" style="background:{bg}; color:{fg}; font-family:{SANS}; '
            f'padding:112px 128px 160px; display:flex; flex-direction:column; gap:{gap}px{extra}">{body}{foot}<aside>{notes}</aside></section>')


def tag(t, color=ACC):  # etiqueta del tipo de slide pedido por los organizadores
    return (f'<p style="align-self:flex-start; font-size:26px; font-weight:600; letter-spacing:2px; text-transform:uppercase; '
            f'color:{color}; border:2px solid {color}; border-radius:999px; padding:8px 24px">{t}</p>')


def h2(t, color=INK): return f'<h2 style="font-family:{SERIF}; font-size:68px; font-weight:600; line-height:1.1; color:{color}; margin-top:-16px">{t}</h2>'
def p(t, size=34, color=BODY, extra=""): return f'<p style="font-size:{size}px; line-height:1.35; color:{color}{extra}">{t}</p>'


def ph(name, w, h, label):
    if ONLINE:  # el deck online no toma los archivos de imagen: recuadro punteado con el nombre del archivo a arrastrar
        return (f'<img alt="{label} (archivo {name})" style="width:{w}px; height:{h}px; object-fit:contain; background:{LIGHT2}; '
                f'border:2px dashed {MUTED}; border-radius:12px">')
    return f'<img src="{IMG}{name}" alt="{label}" style="width:{w}px; height:{h}px; object-fit:contain">'


def stat(label, value, sub, c):
    return (f'<div style="display:flex; flex-direction:column; gap:6px; background:#FFFFFF; padding:24px 28px; border:1px solid {LINE}; '
            f'border-left:8px solid {c}; border-radius:12px"><p style="font-size:24px; color:{MUTED}">{label}</p>'
            f'<p style="font-size:34px; font-weight:600; color:{c}; line-height:1.2">{value}</p>'
            f'<p style="font-size:24px; line-height:1.3; color:{BODY}">{sub}</p></div>')


S, NOTES, SECS = {}, {}, {}


# 1. Portada (~15 s)
NOTES["portada"] = ("[15 s] Soy Lucas Costilla. Durante un mes le pedimos a agentes de inteligencia artificial que trabajaran "
                    "sobre un problema real de microscopía. En cinco minutos: el problema, el mejor resultado, cómo lo "
                    "validamos y qué aprendimos trabajando con agentes.")
S["portada"] = sec("portada",
  f'<div style="flex:1"></div>'
  f'<p style="font-size:32px; font-weight:600; color:{ACC}; letter-spacing:2px; text-transform:uppercase">Proyecto de microscopía computacional</p>'
  f'<h1 style="font-family:{SERIF}; font-size:104px; font-weight:600; line-height:1.05; color:{LIGHT}">Un mes con agentes de IA en un problema de Pticografía de Fourier</h1>'
  f'<p style="font-size:44px; color:#BFD0E6">Qué se resolvió y qué no</p>'
  f'<div style="flex:1"></div>'
  f'<p style="font-size:30px; color:#BFD0E6">Lucas Costilla · semana del 28/09/2026</p>',
  NOTES["portada"], bg=DARK, fg=LIGHT, extra="; justify-content:space-between")

# 2. Problema / pregunta (~60 s)
rig = ('<svg aria-label="Esquema del montaje: matriz de LEDs arriba, luz inclinada hacia la muestra, objetivo y cámara abajo" width="520" height="594" viewBox="0 0 620 700">'
       + "".join(f'<circle cx="{70+i*60}" cy="70" r="16" fill="{ACC if i==6 else "none"}" stroke="{ACC if i==6 else MUTED}" stroke-width="3"/>' for i in range(9))
       + f'<line x1="430" y1="90" x2="330" y2="330" stroke="{ACC}" stroke-width="5"/>'
       + f'<rect x="150" y="330" width="320" height="30" rx="6" fill="{PEACH}" stroke="{MUTED}" stroke-width="2"/>'
       + f'<path d="M230 400 L390 400 L360 480 L260 480 Z" fill="none" stroke="{INK}" stroke-width="3"/>'
       + f'<line x1="310" y1="480" x2="310" y2="560" stroke="{INK}" stroke-width="3"/>'
       + f'<rect x="230" y="560" width="160" height="90" rx="10" fill="none" stroke="{INK}" stroke-width="3"/>'
       + "".join(f'<text x="{x}" y="{y}" font-family="IBM Plex Sans, Arial, sans-serif" font-size="28" fill="{BODY}">{t}</text>'
                 for x, y, t in [(20, 130, "Matriz de LEDs"), (480, 352, "Muestra"), (400, 450, "Objetivo"), (400, 615, "Cámara")])
       + '</svg>')
NOTES["problema"] = ("[60 s] Un microscopio no separa detalles más chicos que cierto límite; con nuestro objetivo, unos 3,8 micrones. "
                     "La pticografía de Fourier, FPM, lo ataca sin cambiar el objetivo: se toma una foto por cada LED de una matriz, "
                     "cada una con la iluminación desde otro ángulo, y un programa las combina. En teoría baja a 0,5 a 1 micrón, y además "
                     "recupera la fase, cuánto se retrasa la luz al atravesar la muestra, que la cámara no registra. "
                     "La trampa: el programa siempre devuelve una imagen, y hay que saber si es la muestra en alta resolución o si "
                     "lo inventó. Y nuestra pregunta de fondo: qué parte de este trabajo pudieron hacer agentes de IA, que "
                     "escribieron, corrieron y auditaron el código, y qué parte no.")
S["problema"] = sec("problema",
  tag("Problema / pregunta") + h2("Ver más detalle que lo que permite el objetivo y recuperar la fase de una muestra") +
  '<div style="display:flex; gap:64px; flex:1; align-items:center">'
  '<div style="flex:1; display:flex; flex-direction:column; gap:28px">'
  + p("Un microscopio no separa detalles menores a un límite: con nuestro objetivo, <b>~3,8 µm</b>.")
  + p("<b>FPM</b>: una foto por LED, cada una con la iluminación desde otro ángulo; un programa las combina para bajar, en teoría, a <b>0,5–1 µm</b> y además recuperar la <i>fase</i> (cuánto se retrasa la luz).")
  + p("El programa siempre devuelve una imagen: <b>¿Es la muestra en alta resolución o lo inventó?</b>")
  + f'<p style="font-size:34px; font-weight:600; line-height:1.35; color:{INK}; background:{PEACH}; padding:24px 32px; border-radius:12px">'
    '¿Qué pudieron resolver los agentes de IA en este problema, y qué no?</p>'
  '</div>'
  f'<div style="width:520px">{rig}</div>'
  '</div>',
  NOTES["problema"], n=2, gap=40)

# 3. Resultado principal (~75 s): captura 28/09 (b) y lo que sugirieron los agentes para llegar a ella
def sug(n_, t, d):
    return (f'<div style="display:flex; gap:20px; align-items:flex-start">'
            f'<p style="font-family:{SERIF}; font-size:36px; font-weight:600; color:{ACC2}; width:36px; line-height:1.1">{n_}</p>'
            f'<div style="flex:1; display:flex; flex-direction:column; gap:4px"><p style="font-size:27px; font-weight:600; line-height:1.25; color:{INK}">{t}</p>'
            f'<p style="font-size:23px; line-height:1.3; color:{MUTED}">{d}</p></div></div>')
NOTES["rgb_b"] = ("[75 s] El mejor resultado es la última captura, del lunes 28 a la noche: el mismo campo en rojo, verde y azul; "
                  "arriba la foto cruda de cada color, abajo la reconstrucción. Los tres colores reconstruyen las mismas partículas "
                  "en los mismos lugares, y cada reconstrucción predice fotos que no usó. "
                  "A esta captura se llegó con sugerencias de los agentes, a partir de lo que medían en cada captura anterior. "
                  "Julio tenía casi nada de luz en los ángulos grandes, así que propusieron varios tiempos por LED: corto para la "
                  "luz directa y largo para la inclinada; el 24/09, 131 de 169 LEDs ya tenían señal útil. Fotos a oscuras para "
                  "restar el fondo del sensor, y repetirlas cuando salieron saturadas. El tiempo de cada LED lo calcularon a partir "
                  "de la captura anterior. Alejar la matriz, de 74 a unos 98 milímetros, para que las fotos de LEDs vecinos se "
                  "solapen más. Y enfocar cada color por separado: con un solo foco, solo el color enfocado salía bien.")
S["rgb_b"] = sec("rgb_b",
  tag("Resultado principal", ACC2) + h2("Reconstrucción con imágenes tomadas en el laboratorio en 3 canales RGB") +
  '<div style="display:flex; gap:48px; flex:1; align-items:flex-start">'
  + ph("fig_rgb_2809b_es.png", 870, 575, "Porción de una muestra, cada canal en su foco, matriz a ~98 mm: foto cruda y reconstrucción de rojo, verde y azul, con las mismas partículas") +
  '<div style="flex:1; display:flex; flex-direction:column; gap:18px">'
  + f'<p style="font-size:26px; font-weight:600; color:{MUTED}; text-transform:uppercase; letter-spacing:1px">Qué sugirieron los agentes para las capturas</p>'
  + sug(1, "Varios tiempos por LED: corto en luz directa, largo en luz inclinada", "24/09: 131 de 169 LEDs con señal útil (señal/ruido &gt; 3)")
  + sug(2, "Fotos a oscuras para restar el fondo del sensor", "Repetidas cuando salieron saturadas")
  + sug(3, "El tiempo de cada LED, calculado de la captura anterior", "Mapa de exposición por LED y por color")
  + sug(4, "Alejar la matriz de 74 a ~98 mm", "Más solapamiento entre LEDs vecinos: de 31&nbsp;% a 46&nbsp;%")
  + sug(5, "Cada color en su propio foco", "Con un solo foco, solo el color enfocado se parecía a la muestra")
  + '</div></div>',
  NOTES["rgb_b"], n=3, gap=32)

# 4. Validación (~75 s)
def test(k, q, value, how, verdict, c):
    return (f'<div style="display:flex; flex-direction:column; gap:6px; background:#FFFFFF; padding:18px 26px; border:1px solid {LINE}; '
            f'border-left:10px solid {c}; border-radius:12px">'
            f'<div style="display:flex; gap:16px; align-items:baseline"><p style="font-family:{SERIF}; font-size:34px; font-weight:600; color:{c}">{k}</p>'
            f'<p style="flex:1; font-size:27px; font-weight:600; line-height:1.25; color:{INK}">{q}</p>'
            f'<p style="font-size:27px; font-weight:600; color:{c}">{verdict}</p></div>'
            f'<p style="font-size:25px; line-height:1.3; color:{INK}">{value}</p>'
            f'<p style="font-size:22px; line-height:1.3; color:{MUTED}">{how}</p></div>')
NOTES["validacion"] = ("[75 s] ¿Cómo decidimos si confiar? Tres pruebas, con criterios escritos antes de mirar los datos reales. "
                       "Uno: en simulación, donde conocemos la respuesta, la amplitud coincide 0,997 con la muestra inventada y la "
                       "fase 0,64 con la matriz a 75 milímetros, donde 1 es perfecto; alejándola a 100, con más solapamiento, la fase sube a 0,97. Dos: con datos reales, apartamos algunos LEDs, reconstruimos sin ellos y "
                       "comparamos las fotos que el programa predice con las medidas. El error va de 0,46 a 0,62, donde 0 es perfecto "
                       "y sin reconstruir da 0,98. Tres, la que decide la resolución: reconstruimos dos veces, cada una con la mitad "
                       "de los LEDs, y medimos cuánto coinciden en el detalle más fino que el objetivo. Da entre 0,04 y 0,10: de 5 a "
                       "14 veces más que por azar, pero debajo del umbral, 0,14. A la izquierda, en verde y en la misma zona, la foto cruda y la fase que recuperó el programa, que ninguna foto registra. "
                       "Las partículas grandes retrasan la luz varios radianes y las chicas muy poco; por eso casi no aparecen en la fase. "
                       "Conclusión honesta: recuperamos la fase de la muestra real, pero ganar resolución todavía no está demostrado.")
S["validacion"] = sec("validacion",
  tag("Validación", ACC2) + h2("¿Cómo decidimos si confiar?") +
  '<div style="display:flex; gap:40px; flex:1; align-items:flex-start">'
  '<div style="width:760px; display:flex; flex-direction:column; gap:20px">'
  + ph("fig_fase_2809b.png", 760, 352, "Verde: foto cruda y fase desenrollada de la misma porción de 128 µm que la figura de los tres canales")
  + f'<p style="font-size:29px; line-height:1.35; color:{INK}; background:{PEACH}; padding:22px 28px; border-radius:12px">'
    'Recuperamos la <b>fase</b> de la muestra real (la reconstrucción predice fotos que no usó). <b>Ganar resolución todavía no está demostrado.</b></p>'
  '</div>'
  '<div style="flex:1; display:flex; flex-direction:column; gap:16px">'
  + test(1, "¿Funciona donde conocemos la respuesta?", "Simulación: amplitud 0,997 · fase 0,64 con la matriz a 75 mm; 0,97 a 100 mm (más solapamiento)",
         "1 = igual a la muestra inventada", "Funciona", ACC2)
  + test(2, "¿Predice las fotos que no usó?", "Error 0,46–0,62 (0 = perfecto; sin reconstruir: 0,98)",
         "Se apartan LEDs, se reconstruye sin ellos y se compara la foto predicha con la medida", "Pasa", ACC2)
  + test(3, "¿Dos reconstrucciones independientes ven el mismo detalle fino?", "0,043–0,099 (1 = idénticas): de 5 a 14 veces el azar; umbral 0,143",
         "Cada una con la mitad de los LEDs; se compara el detalle más fino que el objetivo", "No alcanza", ACC)
  + p("Criterios y umbrales escritos <b>antes</b> de mirar los datos reales.", 25, MUTED)
  + '</div></div>',
  NOTES["validacion"], n=4, gap=32)

# 5. Experiencia / aprendizaje (~60 s)
def rule(n_, t, d):
    return (f'<div style="flex:1; display:flex; flex-direction:column; gap:10px; background:#FFFFFF; padding:26px; border:1px solid {LINE}; border-radius:16px">'
            f'<p style="font-family:{SERIF}; font-size:44px; font-weight:600; color:{ACC}; line-height:1">{n_}</p>'
            f'<h3 style="font-size:28px; font-weight:600; color:{INK}; line-height:1.2">{t}</h3><p style="font-size:24px; line-height:1.35; color:{BODY}">{d}</p></div>')
NOTES["aprendizaje"] = ("[60 s] Lo que más nos enseñó, y creo que sirve para cualquier grupo: pasar todas las pruebas no alcanza. "
                        "El programa mejora la imagen de a poco: compara las fotos que predice con las medidas y la corrige un poco "
                        "en cada vuelta. Con imágenes reales, esas correcciones eran unas 8.000 veces más chicas de lo debido: después "
                        "de cientos de vueltas devolvía casi la foto original. Y aun así pasaba cientos de pruebas automáticas, porque "
                        "estaban hechas con imágenes chiquitas, de 16 a 32 píxeles. Lo encontró un agente que investigaba otra cosa. "
                        "Los agentes también se equivocaron: supusieron mal datos del hardware y explicaron mal el ruido del sensor. "
                        "Cuatro consejos: probar con datos del tamaño real; escribir el criterio de éxito antes de ver el resultado; "
                        "que otro agente, con su propio código, rehaga cada número; y una persona que conozca el equipo, porque los "
                        "agentes no saben lo que no se les dice.")
S["aprendizaje"] = sec("aprendizaje",
  tag("Experiencia / aprendizaje") + h2("Pasar todas las pruebas no alcanza") +
  '<div style="display:flex; gap:44px; align-items:center">'
  + ph("fig_congelado.png", 760, 286, "Foto cruda, algoritmo congelado y algoritmo corregido") +
  '<div style="flex:1; display:flex; flex-direction:column; gap:16px">'
  + p("El programa mejora la imagen de a poco: compara las fotos que predice con las medidas y la corrige un poco en cada vuelta.", 27)
  + p("Esas correcciones eran <b>~8.000 veces</b> más chicas de lo debido: después de cientos de vueltas devolvía casi la foto original, "
      "<b>y aun así pasaba cientos de pruebas</b>, hechas con imágenes chiquitas (16–32 píxeles).", 27)
  + p("Lo encontró un agente que investigaba otra cosa. Los agentes también se equivocaron: supusieron mal el hardware.", 27)
  + '</div></div>'
  '<div style="display:flex; gap:20px">'
  + rule(1, "Probar con datos reales", "Del tamaño y el tipo reales, no solo casos chicos")
  + rule(2, "Criterio escrito antes", "Qué cuenta como éxito, antes de ver el resultado")
  + rule(3, "Verificación independiente", "Otro agente, con otro código, rehace cada número")
  + rule(4, "Alguien que conozca el equipo", "Los agentes no saben lo que no se les dice")
  + '</div>',
  NOTES["aprendizaje"], n=5, gap=30)

# 6. Cierre (~15 s)
NOTES["cierre"] = ("[15 s] En resumen: los agentes fueron más útiles para auditar que para juzgar resultados reales. Ya medimos qué "
                   "mejoró la última captura: sobre todo el foco de cada color, de forma provisional. Lo que sigue: una placa de "
                   "calibración con detalle conocido, y probar con datos reales la combinación de verde y azul. Gracias.")
step = lambda t, d: (f'<div style="display:flex; flex-direction:column; gap:8px"><h3 style="font-size:38px; font-weight:600; color:{LIGHT}; line-height:1.2">{t}</h3>'
                     f'<p style="font-size:28px; line-height:1.35; color:#BFD0E6">{d}</p></div>')
S["cierre"] = sec("cierre",
  h2("En resumen", LIGHT) +
  '<div style="display:flex; flex-direction:column; gap:34px; flex:1">'
  + step("Los agentes: más útiles para auditar que para juzgar resultados reales", "Aportan volumen, auditoría y diseño de experimentos; fallan en el mundo físico y por exceso de confianza")
  + step("Ya medido: el foco de cada color pesa más que el solapamiento", "Provisional: el modelo todavía no incluye el desenfoque")
  + step("Próximo: una placa de calibración con líneas de ancho conocido", "Decide si el método gana detalle en nuestro montaje")
  + step("Próximo: combinar verde y azul con la dispersión conocida, en datos reales", "En simulación funciona; con datos reales todavía no se probó")
  + '</div>'
  f'<p style="font-size:28px; color:{ACC}">Informe completo: https://claude.ai/code/artifact/de7eab31-d9e0-4828-a62d-285ba0d46a98</p>',
  NOTES["cierre"], bg=DARK, fg=LIGHT, n=6, gap=36)

# ---------------- Apéndice para preguntas (no cuenta en los 5 minutos) ----------------
# Fuentes de cada número, en el orden en que aparecen:
#  A1: 41 números marcados y 69 entradas: salida de `python3 scripts/check_provenance.py report/resumen/resumen.md`;
#      gradiente 1,03e-8 (verificador 6,0e-9): docs/resultados_2026-09-29/conjunta/INFORME.md §1;
#      pruebas: TESTS_OK (corrida local de pytest -q, ver abajo) o nada.
#  A2: 97 de 99 commits con Claude como coautor: git log (trailer Co-Authored-By).
#  A3: docs/resultados_2026-09-29/conjunta/INFORME.md §3-4 (S1 -0,0915; costo 0,969 x piso; S1 ép. 80 -0,037 -> 240 -0,0915;
#      cadena verde+azul 0,945); tests/test_acceptance_conjunta.py (7 pasan; exige entregables, no éxito).
#  A4: docs/resultados_2026-09-29/foco_vs_solapamiento/FOCO_VS_SOLAPAMIENTO.md.
pill = lambda t, main=False: (f'<p style="font-size:26px; font-weight:600; padding:18px 24px; border-radius:12px; text-align:center; '
                               f'background:{PEACH if main else "#FFFFFF"}; border:2px solid {ACC if main else LINE}; color:{INK}">{t}</p>')
ARROW = f'<p style="font-size:40px; color:{MUTED}">&#8594;</p>'
TESTS_OK = os.environ.get("TESTS_OK")  # número de pruebas que pasan en la última corrida local; sin él no se muestra


def card2(title, lines, color=INK, size=26):
    inner = "".join(f'<p style="font-size:{size}px; line-height:1.35; color:{BODY}">{l}</p>' for l in lines)
    return (f'<div style="flex:1; display:flex; flex-direction:column; gap:12px; background:#FFFFFF; padding:28px 32px; '
            f'border:1px solid {LINE}; border-radius:16px"><h3 style="font-size:30px; font-weight:600; line-height:1.2; color:{color}">{title}</h3>{inner}</div>')


NOTES["apendice"] = "Separador. No cuenta en los 5 minutos: slides para responder preguntas."
S["apendice"] = sec("apendice",
  f'<div style="flex:1"></div>'
  f'<p style="font-size:32px; font-weight:600; color:{ACC}; letter-spacing:2px; text-transform:uppercase">Apéndice</p>'
  f'<h1 style="font-family:{SERIF}; font-size:96px; font-weight:600; line-height:1.05; color:{LIGHT}">Para preguntas</h1>'
  f'<p style="font-size:36px; color:#BFD0E6">Control de los agentes · quién hizo qué · reconstrucción conjunta · foco o solapamiento</p>'
  f'<div style="flex:1"></div>',
  NOTES["apendice"], bg=DARK, fg=LIGHT, extra="; justify-content:space-between")

tests_line = [f"Suite de pruebas automáticas: {TESTS_OK} pasan"] if TESTS_OK else []
NOTES["a_control"] = ("Cuatro controles, cada uno nació de un error. Uno: cada número del resumen lleva una marca con su clave, y un "
                      "script comprueba que coincide con el registro de números, que solo escribe un programa; si alguien, persona o "
                      "agente, cambia un número a mano, la verificación falla. Dos: en la reconstrucción conjunta, la prueba de aceptación "
                      "tenía el hash fijado y el agente no la podía editar; los criterios y umbrales tampoco se pueden cambiar "
                      "después de ver resultados. Tres: un verificador independiente rehace cada número con su propio código; en "
                      "la reconstrucción conjunta el gradiente dio 1,03e-8 y el verificador obtuvo 6,0e-9. Cuatro: los planes "
                      "escriben los criterios antes de correr (carpeta docs).")
S["a_control"] = sec("a_control",
  tag("Apéndice", MUTED) + h2("¿Cómo controlamos a los agentes?") +
  '<div style="display:flex; gap:24px">'
  + card2("Cada número con su fuente", ["El resumen tiene <b>41</b> números marcados; un script verifica que cada uno coincide con el registro (69 entradas).",
                                        "El registro lo escribe solo un programa, no una persona ni un agente."], ACC2)
  + card2("Pruebas que el agente no puede editar", ["En la reconstrucción conjunta, la prueba de aceptación tenía su hash fijado.",
                                                    "Criterios y umbrales fijos: no se cambian después de ver resultados."], ACC2)
  + '</div><div style="display:flex; gap:24px">'
  + card2("Un verificador independiente", ["Otro agente rehace cada número con su propio código.",
                                           "Ej.: gradiente 1,03e-8; el verificador obtuvo 6,0e-9."], ACC2)
  + card2("Criterios escritos antes", ["Cada experimento largo tiene un plan en <code>docs/</code> con los criterios de éxito, escrito antes de correr."]
          + tests_line, ACC2)
  + '</div>',
  NOTES["a_control"], n="A1", gap=32)

NOTES["a_quien"] = ("La división del trabajo. Lucas armó el montaje y tomó todas las capturas en el laboratorio; confirmó los datos "
                    "del hardware, que los agentes no podían saber y a veces supusieron mal; decidió qué probar y tuvo la última "
                    "palabra. Los agentes escribieron casi todo el código: 97 de los 99 commits del repositorio tienen a Claude como "
                    "coautor. También hicieron los análisis, encontraron los errores, escribieron los informes, propusieron cómo "
                    "tomar las capturas y armaron esta presentación. Los agentes no hacen commits por su cuenta: solo cuando la "
                    "persona lo pide.")
S["a_quien"] = sec("a_quien",
  tag("Apéndice", MUTED) + h2("¿Quién hizo qué?") +
  '<div style="display:flex; gap:32px">'
  + card2("La persona (Lucas)", ["Armó el montaje y tomó las capturas en el laboratorio",
                                 "Dio los datos reales del hardware: objetivo, cámara, altura de la matriz",
                                 "Decidió qué probar y tuvo el criterio final"], ACC, 28)
  + card2("Los agentes (Claude)", ["El código del simulador y de la reconstrucción: <b>97 de 99</b> commits con Claude como coautor",
                                   "Análisis, diagnóstico de errores e informes",
                                   "Sugerencias de captura y esta presentación"], ACC2, 28)
  + '</div>'
  + p("Los agentes no hacen commits por su cuenta: solo cuando la persona lo pide.", 28, MUTED)
  + f'<p style="font-size:26px; font-weight:600; color:{MUTED}; margin-top:16px">Una ronda de un equipo de agentes</p>'
  + '<div style="display:flex; align-items:center; gap:12px">'
  + pill("Persona: la pregunta") + ARROW + pill("Agente líder") + ARROW + pill("Trabajadores") + ARROW
  + pill("Verificador", True) + ARROW + pill("Persona decide") + '</div>',
  NOTES["a_quien"], n="A2", gap=28)

NOTES["a_conjunta"] = ("Un ejemplo de por qué pasar las pruebas no alcanza. Probamos reconstruir los tres colores juntos, con un solo "
                       "espesor para la muestra. Todo en simulación, donde conocemos la respuesta. El gradiente estaba verificado y "
                       "la prueba de aceptación pasó, pero esa prueba solo exige que los entregables existan, no que el método "
                       "funcione. El ajuste reproduce las fotos mejor que la muestra verdadera: queda en 0,97 veces el piso de ruido. "
                       "Y sin embargo el espesor que encuentra no tiene nada que ver con el verdadero: correlación −0,09. Optimizar "
                       "más lo empeora: de −0,04 en la época 80 a −0,09 en la 240. Por la regla del plan, no se pasó a datos reales. "
                       "La cadena simple, verde y azul por separado con la dispersión conocida, da 0,945 en la misma simulación.")
S["a_conjunta"] = sec("a_conjunta",
  tag("Apéndice", MUTED) + h2("Reconstruir los tres colores juntos: pasó las pruebas y no sirve") +
  '<div style="display:flex; gap:44px; align-items:flex-start">'
  + ph("fig_conjunta_verdad_vs_conjunta.png", 880, 390, "Simulación: espesor verdadero y espesor de la reconstrucción conjunta a 240 épocas") +
  '<div style="flex:1; display:flex; flex-direction:column; gap:18px">'
  + stat("Ajuste de las fotos", "0,97 × el piso de ruido", "Mejor que la muestra verdadera", ACC2)
  + stat("Espesor contra el verdadero", "−0,09", "Correlación (1 = perfecto). Más épocas, peor: −0,04 → −0,09", ACC)
  + stat("La cadena simple", "0,945", "Verde + azul por separado, con la dispersión conocida", ACC2)
  + '</div></div>'
  + p("En simulación; no se pasó a datos reales. La prueba de aceptación pasó: solo exigía los entregables.", 25, MUTED),
  NOTES["a_conjunta"], n="A3", gap=24)

td = lambda v, b=False, c=INK: f'<td style="font-size:30px; color:{c}; {"font-weight:600;" if b else ""}">{v}</td>'
tbl = (f'<table style="font-family:{SANS}"><tr><th style="font-size:26px; width:46%">Rojo, matriz a 98 mm</th>'
       f'<th style="font-size:26px">Error en fotos no usadas<br>(sin reconstruir ~0,98)</th><th style="font-size:26px">Mitades<br>(detalle fino)</th></tr>'
       f'<tr>{td("En su propio foco", True)}{td("0,46", True, ACC2)}{td("0,083", True, ACC2)}</tr>'
       f'<tr>{td("Con el foco del verde")}{td("0,81")}{td("0,021")}</tr>'
       f'<tr>{td("Con el foco del azul")}{td("0,86")}{td("0,024")}</tr></table>')
NOTES["a_foco"] = ("En la última captura cambiamos dos cosas a la vez, así que después las separamos. Solo el foco: el rojo, la misma "
                   "noche y el mismo campo, en su foco o con el foco del verde o del azul. En su foco predice las fotos no usadas "
                   "con error 0,46; desenfocado, 0,81 a 0,86. Las mitades coinciden 0,083 contra 0,021 a 0,024: de 3,5 a 4 veces más. "
                   "Solo la geometría: el verde en foco, al pasar de 74 a 98 milímetros, sube de 0,024 a 0,043, 1,8 veces. "
                   "O sea, el foco pesa más. Es provisional: el modelo no incluye el desenfoque, y un modelo con el desenfoque de "
                   "cada color podría recuperar parte.")
S["a_foco"] = sec("a_foco",
  tag("Apéndice", MUTED) + h2("¿Qué limita más: el foco o el solapamiento?") + tbl +
  '<div style="display:flex; gap:24px">'
  + card2("Solo el foco", ["Mitades ×3,5 a ×4 al enfocar cada color"], ACC2, 28)
  + card2("Solo la geometría", ["Verde en foco, de 74 a 98 mm: mitades 0,024 → 0,043 (×1,8)"], INK, 28)
  + card2("Provisional", ["El modelo no incluye el desenfoque: uno que lo incluya podría recuperar parte"], MUTED, 28)
  + '</div>',
  NOTES["a_foco"], n="A4", gap=30)

order = ["portada", "problema", "rgb_b", "validacion", "aprendizaje", "cierre"]
APENDICE = ["apendice", "a_control", "a_quien", "a_conjunta", "a_foco"]

if ONLINE:
    out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else ".", "project")
    os.makedirs(os.path.join(out, "slides"), exist_ok=True)
    for k in order + APENDICE:
        open(os.path.join(out, "slides", f"{k}.html"), "w").write(S[k])
    deck = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
            "title": "Agentes de IA en microscopía (5 min)", "order": order + APENDICE,
            "sections": {"s1": {"description": "Problema y pregunta", "start": "portada"},
                         "s2": {"description": "Resultado principal y validación", "start": "rgb_b"},
                         "s3": {"description": "Aprendizaje y cierre", "start": "aprendizaje"},
                         "s4": {"description": "Apéndice para preguntas", "start": "apendice"}},
            "cover": "portada",
            "faces": {"ibm-plex-sans": {"family": "IBM Plex Sans", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"},
                      "source-serif-4": {"family": "Source Serif 4", "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600&display=swap"}},
            "designSystems": []}
    json.dump(deck, open(os.path.join(out, "deck.json"), "w"), ensure_ascii=False, indent=1)
    print(len(order + APENDICE), "slides online ->", out)
else:
    head = open(os.path.join(HERE, "head.html")).read().replace(
        "<title>Un mes con agentes de IA en microscopía</title>", "<title>Agentes de IA en microscopía (5 min)</title>")
    body = "".join(S[k].replace("<section ", '<section class="slide" ', 1) for k in order + APENDICE)
    html_path = os.path.join(HERE, "presentacion_5min.html")
    open(html_path, "w").write(head + "<body>" + body + "</body></html>")
    secs = {"portada": 15, "problema": 60, "rgb_b": 75, "validacion": 75, "aprendizaje": 60, "cierre": 15}
    notas = [f"Charla corta: 5 minutos en total ({sum(secs.values())} s). Entre corchetes, segundos por slide.\n"
             "El deck de 14 slides (presentacion_agentes_ia.pdf) queda como respaldo para las preguntas."]
    notas += [f"{i}. {k} ({secs[k]} s)\n{NOTES[k]}" for i, k in enumerate(order, 1)]
    notas += ["APÉNDICE PARA PREGUNTAS (no cuenta en los 5 minutos)"]
    notas += [f"{k if k == 'apendice' else 'A' + str(i)}. {k}\n{NOTES[k]}" for i, k in enumerate(APENDICE)]
    open(os.path.join(HERE, "notas_del_orador_5min.txt"), "w").write("\n\n".join(notas) + "\n")
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={os.path.join(HERE, 'presentacion_5min.pdf')}", f"file://{html_path}"],
                   check=True, stderr=subprocess.DEVNULL)
    print(len(order + APENDICE), "slides ->", os.path.join(HERE, "presentacion_5min.pdf"))
