import json, datetime
DARK, LIGHT, LIGHT2, INK, BODY, MUTED, ACC, ACC2, LINE = "#14213D", "#FBFBF8", "#F1F0EA", "#14213D", "#3D4A5C", "#6A7382", "#D9692B", "#2F6FB0", "#DDDBD2"
SANS = "'IBM Plex Sans', Arial, sans-serif"; SERIF = "'Source Serif 4', Georgia, serif"
N = 11
def sec(id, body, notes, bg=LIGHT, fg=INK, n=None, extra=""):
    foot = f'<p style="position:absolute; left:128px; bottom:64px; width:600px; font-size:24px; color:{MUTED}">{n} / {N}</p>' if n else ""
    return (f'<section id="{id}" data-transition="fade" style="background:{bg}; color:{fg}; font-family:{SANS}; '
            f'padding:128px 128px 160px; display:flex; flex-direction:column; gap:48px{extra}">{body}{foot}<aside>{notes}</aside></section>')
def h2(t): return f'<h2 style="font-family:{SERIF}; font-size:72px; font-weight:600; line-height:1.1; color:{INK}">{t}</h2>'
def card(title, lines, color=INK, bg="#FFFFFF", border=LINE, size=30):
    inner = "".join(f'<p style="font-size:{size}px; line-height:1.35; color:{BODY}">{l}</p>' for l in lines)
    return (f'<div style="flex:1; display:flex; flex-direction:column; gap:16px; background:{bg}; padding:40px; '
            f'border:1px solid {border}; border-radius:16px"><h3 style="font-size:40px; font-weight:600; color:{color}">{title}</h3>{inner}</div>')
def ph(name, w, h, label):
    return (f'<img alt="{label} (archivo {name})" style="width:{w}px; height:{h}px; object-fit:contain; background:{LIGHT2}; '
            f'border:2px dashed {MUTED}; border-radius:12px">')
S = {}

S["portada"] = sec("portada",
  f'<div style="flex:1"></div>'
  f'<p style="font-size:32px; font-weight:600; color:{ACC}; letter-spacing:2px; text-transform:uppercase">Proyecto de microscopía computacional</p>'
  f'<h1 style="font-family:{SERIF}; font-size:104px; font-weight:600; line-height:1.05; color:{LIGHT}">Un mes con agentes de IA en un problema de microscopía</h1>'
  f'<p style="font-size:44px; color:#BFD0E6">Qué se resolvió y qué no</p>'
  f'<div style="flex:1"></div>'
  f'<p style="font-size:30px; color:#BFD0E6">Lucas Costilla · semana del 28/09/2026</p>',
  "Presentarse. Contar en una frase de qué se trata: durante un mes le pedimos a agentes de inteligencia artificial que trabajaran sobre un problema real de microscopía. La charla no es sobre la técnica sino sobre qué pudieron y qué no pudieron resolver.",
  bg=DARK, fg=LIGHT, extra="; justify-content:space-between")

S["respuesta"] = sec("respuesta",
  h2("La respuesta corta") +
  '<div style="display:flex; gap:32px; flex:1">' +
  card("Se logró", ["Un simulador del microscopio y un programa de reconstrucción que funcionan con datos simulados",
                    "Cinco errores de fondo encontrados; uno invalidaba todo lo hecho con datos reales",
                    "La geometría del montaje, medida desde las propias imágenes",
                    "Una receta de captura: de 12 a 129 ángulos de luz útiles"], color=ACC2) +
  card("No se logró", ["Una reconstrucción de una muestra real en la que podamos confiar",
                       "Demostrar que se gana resolución: la muestra actual no lo permite"], color=ACC) +
  '</div>',
  "Adelantar la conclusión para que todos sepan hacia dónde va la charla. Lo que se logró es sobre todo infraestructura y auditoría. Lo que no se logró es el objetivo científico final: una imagen real mejorada en la que confiemos.", n=2)

rig = ('<svg aria-label="Esquema del montaje: matriz de LEDs arriba, luz inclinada hacia la muestra, objetivo y cámara abajo" width="620" height="700" viewBox="0 0 620 700">'
       + "".join(f'<circle cx="{70+i*60}" cy="70" r="16" fill="{ACC if i==6 else "none"}" stroke="{ACC if i==6 else MUTED}" stroke-width="3"/>' for i in range(9))
       + f'<line x1="430" y1="90" x2="330" y2="330" stroke="{ACC}" stroke-width="5"/>'
       + f'<rect x="150" y="330" width="320" height="30" rx="6" fill="#F6D9C6" stroke="{MUTED}" stroke-width="2"/>'
       + f'<path d="M230 400 L390 400 L360 480 L260 480 Z" fill="none" stroke="{INK}" stroke-width="3"/>'
       + f'<line x1="310" y1="480" x2="310" y2="560" stroke="{INK}" stroke-width="3"/>'
       + f'<rect x="230" y="560" width="160" height="90" rx="10" fill="none" stroke="{INK}" stroke-width="3"/></svg>')
lab = lambda x, y, t, w=360: f'<p style="position:absolute; left:{x}px; top:{y}px; width:{w}px; font-size:26px; color:{BODY}">{t}</p>'
S["problema"] = sec("problema",
  h2("El problema en un minuto") +
  '<div style="display:flex; gap:64px; flex:1">'
  '<div style="flex:1; display:flex; flex-direction:column; gap:32px">'
  f'<p style="font-size:36px; line-height:1.35; color:{BODY}">Un microscopio no separa detalles menores a cierto límite: con nuestro objetivo, <b>~3,8 µm</b>.</p>'
  f'<p style="font-size:36px; line-height:1.35; color:{BODY}">La técnica FPM toma <b>169 fotos</b>, cada una con la luz desde otro ángulo, y un programa las combina para bajar a <b>~1 µm</b>.</p>'
  f'<p style="font-size:36px; line-height:1.35; color:{BODY}">Lo difícil: el programa tiene que conocer la geometría exacta y deducir algo que la cámara no registra, cuánto se retrasa la luz (la <i>fase</i>).</p>'
  '</div>'
  f'<div style="width:620px; position:relative">{rig}</div>'
  '</div>'
  + lab(1172, 356, "Matriz de LEDs", 300) + lab(1172, 590, "Muestra", 140) + lab(1172, 681, "Objetivo", 200) + lab(1172, 846, "Cámara", 200),
  "Explicar con la analogía del rompecabezas: cada ángulo de luz trae una pieza distinta del detalle fino. Enfatizar que el programa siempre devuelve una imagen; el problema es saber si esa imagen es la muestra o un artefacto. Esa es la pregunta que atraviesa toda la charla.", n=3)

pill = lambda t, main=False: (f'<p style="font-size:28px; font-weight:600; padding:20px 28px; border-radius:12px; text-align:center; '
                               f'background:{"#F6D9C6" if main else "#FFFFFF"}; border:2px solid {ACC if main else LINE}; color:{INK}">{t}</p>')
arrow = f'<x-connector style="width:56px; color:{MUTED}" head="end"></x-connector>'
S["como"] = sec("como",
  h2("Cómo trabajamos") +
  '<div style="display:flex; gap:32px">' +
  card("Sesión directa", ["Una persona y el asistente, paso a paso", "Decidir, revisar, tareas cortas"], size=28) +
  card("Agentes en paralelo", ["Copias del asistente, una tarea cada una", "Más de 20 auditorías en una semana"], size=28) +
  card("Equipos con verificador", ["Líder, trabajadores, verificador y redactor", "Para preguntas difíciles, por rondas"], color=ACC, size=28) +
  '</div>'
  f'<p style="font-size:30px; font-weight:600; color:{MUTED}">Una ronda de un equipo: el verificador rehace cada número antes de aceptarlo</p>'
  '<div style="display:flex; align-items:center; gap:12px">'
  + pill("Persona") + arrow + pill("Líder") + arrow + pill("Trabajadores") + arrow + pill("Verificador", True) + arrow + pill("Persona decide") +
  '</div>',
  "Tres modos de trabajo, de menos a más autonomía. El que más nos enseñó fue el tercero: un equipo donde un agente distinto rehace cada número con su propio código antes de aceptarlo. Las personas eligen la pregunta, fijan los criterios y deciden al final; los agentes no guardan cambios por su cuenta.", n=4)

big = lambda num, t, c=INK: (f'<div style="display:flex; flex-direction:column; gap:8px"><p style="font-family:{SERIF}; font-size:96px; font-weight:600; color:{c}; line-height:1">{num}</p>'
                             f'<p style="font-size:28px; color:{BODY}; line-height:1.3">{t}</p></div>')
S["simulado"] = sec("simulado",
  h2("Con datos simulados, funciona") +
  '<div style="display:flex; gap:64px; align-items:center; flex:1">' + ph("fig_sintetico.png", 1000, 740, "Muestra simulada y su reconstrucción") +
  '<div style="flex:1; display:flex; flex-direction:column; gap:48px">' +
  big("0,995", "coincidencia del brillo con la muestra original (1 = perfecta)", ACC2) +
  big("0,87–0,97", "coincidencia de la fase, que ninguna foto muestra", ACC2) +
  f'<p style="font-size:26px; color:{MUTED}">Misma geometría que nuestro montaje real</p></div></div>',
  "Se inventa una muestra, se simulan las 169 fotos y el programa reconstruye a partir de ellas. Como conocemos la respuesta, podemos medir cuánto acierta. Esto es la base: si no funcionara aquí, no tendría sentido probar con datos reales.", n=5)

S["congelado"] = sec("congelado",
  h2("El error más grave: con datos reales, el programa no hacía nada") +
  ph("fig_congelado.png", 1664, 420, "Foto cruda, algoritmo congelado y algoritmo corregido") +
  '<div style="display:flex; gap:48px">'
  f'<p style="flex:1; font-size:30px; line-height:1.35; color:{BODY}">Corregía la imagen en pasos <b>~8.000 veces</b> más chicos de lo debido: devolvía casi la foto original.</p>'
  f'<p style="flex:1; font-size:30px; line-height:1.35; color:{BODY}">Cientos de pruebas automáticas pasaban, porque usaban imágenes de 16 a 32 píxeles.</p>'
  f'<p style="flex:1; font-size:30px; line-height:1.35; color:{BODY}">Lo encontró un agente que investigaba otra cosa. Hubo que descartar todo lo anterior con datos reales.</p>'
  '</div>',
  "Analogía: bajar una montaña con pasos de una décima de milímetro; después de 100 pasos seguís donde empezaste. El programa entregaba la foto de partida como si fuera la reconstrucción. Lección: pasar todas las pruebas no garantiza que el código funcione en el caso real.", n=6)

rows = [("La imagen de referencia tenía menos detalle que una foto cruda", "Un agente rastreó su origen"),
        ("Las fotos no se corregían por su tiempo de exposición", "Un agente, al revisar los datos"),
        ("Las corridas reales usaban el objetivo equivocado", "La persona, al confirmar el hardware"),
        ("La explicación de un defecto, dada por el asistente, era falsa", "El verificador del tercer equipo")]
tbl = (f'<table style="font-size:28px; color:{BODY}"><tr><th style="width:62%">Error</th><th style="width:38%">Quién lo encontró</th></tr>'
       + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>")
S["errores"] = sec("errores",
  h2("Otros errores, incluidos los de los propios agentes") + tbl +
  f'<p style="font-size:30px; line-height:1.35; color:{BODY}; background:#F6D9C6; padding:28px 36px; border-radius:12px">'
  f'El asistente también supuso cosas del hardware que resultaron falsas: la cámara, el objetivo, la altura. <b>No saben lo que no se les dice.</b></p>',
  "Varios errores los habían introducido o pasado por alto los propios agentes, y los encontraron otros agentes al auditar con una pregunta distinta. El de la referencia es ilustrativo: la imagen con la que validábamos tenía menos detalle que una sola foto cruda, así que la mejor 'reconstrucción' era la foto sin procesar.", n=7)

snr = json.load(open("snr.json"))
cols = ["#E3ECF6", "#BCD0E8", "#86A9D4", "#4E7FBB", "#2F5C94", "#14213D"]
def col(v):
    for i, t in enumerate([2, 3, 5, 8, 12]):
        if v < t: return cols[i]
    return cols[5]
cells = "".join(f'<rect x="{(c-9)*44}" y="{(r-12)*44}" width="40" height="40" rx="4" fill="{col(v)}"/>' for r, c, v in snr)
heat = f'<svg aria-label="Mapa de 13 por 13 LEDs: la señal útil es máxima en el centro y cae hacia los bordes" width="572" height="572" viewBox="0 0 572 572">{cells}</svg>'
legend = "".join(f'<div style="display:flex; align-items:center; gap:12px"><div style="width:32px; height:32px; background:{c}; border-radius:4px"></div><p style="font-size:24px; color:{BODY}">{t}</p></div>'
                 for c, t in zip([cols[0], cols[1], cols[2], cols[5]], ["menos de 2", "2 a 3", "3 a 5", "más de 12"]))
S["captura"] = sec("captura",
  h2("La captura nueva: la receta funcionó") +
  '<div style="display:flex; gap:64px; flex:1">'
  f'<div style="display:flex; flex-direction:column; gap:16px">{heat}<p style="font-size:24px; color:{MUTED}">Señal útil por LED, sobre el ruido (verde, 100 ms)</p></div>'
  '<div style="flex:1; display:flex; flex-direction:column; gap:40px">' +
  big("129 de 169", "LEDs con señal útil (al menos 3 veces el ruido)", ACC2) + big("12", "en la captura de julio, antes de la receta", MUTED) +
  f'<div style="display:flex; flex-direction:column; gap:12px">{legend}</div>'
  '</div></div>',
  "Los agentes calcularon que la captura de julio tenía muy poca luz y propusieron repetirla con varios tiempos de exposición. El laboratorio la hizo el 24/09: 4.563 imágenes. El centro del mapa es luz directa; los bordes son ángulos grandes, con poca señal pero con la información de los detalles finos. También sirvió para medir la geometría: la matriz está a unos 80 mm. [Opcional: mostrar fig_crudas.png con las fotos crudas.]", n=8)

crit = lambda n_, t, r, c: (f'<div style="flex:1; display:flex; flex-direction:column; gap:8px; background:#FFFFFF; padding:24px 28px; border:1px solid {LINE}; border-left:8px solid {c}; border-radius:12px">'
                            f'<p style="font-size:26px; color:{BODY}">{n_}. {t}</p><p style="font-size:28px; font-weight:600; color:{c}">{r}</p></div>')
S["confianza"] = sec("confianza",
  h2("Por qué todavía no confiamos en la reconstrucción") +
  ph("fig_reconstruccion_real.png", 1664, 400, "Foto cruda y tres reconstrucciones con patrones en red") +
  '<div style="display:flex; gap:24px">' +
  crit(1, "Predice fotos que no vio", "Pasa", ACC2) + crit(2, "Una geometría equivocada se nota", "Falla", ACC) +
  crit(3, "Sin patrones que no están en la muestra", "Falla a la vista", ACC) + crit(4, "Aparece detalle nuevo", "No evaluable", MUTED) +
  '</div>',
  "Cuatro criterios escritos antes de mirar, para no acomodarlos después. El 2 es el central: si mover los LEDs medio paso casi no cambia nada, los datos no restringen al programa. El 3: el indicador numérico dijo que pasaba, pero al mirar las imágenes el patrón en red sigue ahí; el número lo subestimaba. El 4: las partículas están tan separadas que una foto cruda ya las distingue, así que no hay detalle nuevo que ganar.", n=9)

rule = lambda n_, t, d: (f'<div style="flex:1; display:flex; flex-direction:column; gap:12px; background:#FFFFFF; padding:32px; border:1px solid {LINE}; border-radius:16px">'
                         f'<p style="font-family:{SERIF}; font-size:56px; font-weight:600; color:{ACC}; line-height:1">{n_}</p>'
                         f'<h3 style="font-size:30px; font-weight:600; color:{INK}; line-height:1.2">{t}</h3><p style="font-size:26px; line-height:1.35; color:{BODY}">{d}</p></div>')
S["lecciones"] = sec("lecciones",
  h2("Lecciones para cualquier grupo que use agentes") +
  '<div style="display:flex; gap:24px; flex:1">' +
  rule(1, "Criterio antes de mirar", "Escribir qué cuenta como éxito antes del resultado") +
  rule(2, "Verificación independiente", "Otro agente, con otro código, rehace cada número") +
  rule(3, "Cada número con su fuente", "El archivo que lo produce, citado y revisable") +
  rule(4, "Primero lo simulado", "Donde se conoce la respuesta, en las mismas condiciones") +
  rule(5, "Una persona que conozca el equipo", "Las preguntas del hardware no las contesta el agente") +
  '</div>'
  f'<p style="font-size:30px; line-height:1.35; color:{BODY}"><b>Aportan:</b> volumen, auditoría, diseño de experimentos. <b>Fallan:</b> el mundo físico y el exceso de confianza.</p>',
  "Estas reglas no las teníamos al principio: cada una apareció después de ver fallar la versión sin ella. Un ejemplo de exceso de confianza: el asistente afirmó un 'sobreajuste' que tuvo que corregir mientras escribíamos el informe, al comparar con la simulación.", n=10)

step = lambda t, d: (f'<div style="display:flex; flex-direction:column; gap:8px"><h3 style="font-size:40px; font-weight:600; color:{LIGHT}">{t}</h3>'
                     f'<p style="font-size:30px; line-height:1.35; color:#BFD0E6">{d}</p></div>')
S["siguiente"] = sec("siguiente",
  f'<h2 style="font-family:{SERIF}; font-size:72px; font-weight:600; line-height:1.1; color:{LIGHT}">Próximos pasos</h2>'
  '<div style="display:flex; flex-direction:column; gap:40px; flex:1">' +
  step("1. Una placa de calibración con líneas de ancho conocido", "Decide si el método gana detalle en nuestro montaje") +
  step("2. Que el programa pese cada foto según su luz", "Decide si el patrón en red es un defecto del programa") +
  step("3. Terminar rojo y azul", "Una ronda más del equipo de agentes") +
  '</div>'
  f'<p style="font-size:30px; color:{ACC}">Informe completo: [enlace al informe]</p>',
  "Cerrar con el paso decisivo, que es de laboratorio: una muestra con detalles más finos que 3,8 µm. Invitar a preguntas.",
  bg=DARK, fg=LIGHT, n=11)

order = ["portada", "respuesta", "problema", "como", "simulado", "congelado", "errores", "captura", "confianza", "lecciones", "siguiente"]
for k in order: open(f"project/slides/{k}.html", "w").write(S[k])
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "title": "Un mes con agentes de IA en microscopía", "order": order,
        "sections": {"s1": {"description": "La respuesta corta y el problema", "start": "portada"},
                     "s2": {"description": "Cómo trabajamos y qué funcionó", "start": "como"},
                     "s3": {"description": "Errores encontrados", "start": "congelado"},
                     "s4": {"description": "La captura nueva y por qué no confiamos todavía", "start": "captura"},
                     "s5": {"description": "Lecciones y próximos pasos", "start": "lecciones"}},
        "cover": "portada",
        "faces": {"ibm-plex-sans": {"family": "IBM Plex Sans", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap"},
                  "source-serif-4": {"family": "Source Serif 4", "href": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600&display=swap"}},
        "designSystems": []}
json.dump(deck, open("project/deck.json", "w"), ensure_ascii=False, indent=1)
print({k: len(S[k]) for k in order})
