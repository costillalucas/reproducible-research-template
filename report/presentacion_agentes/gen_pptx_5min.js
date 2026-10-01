// PPTX editable de la charla de 5 minutos (6 slides + apéndice), a partir del mismo contenido que gen_slides_5min.py.
// Textos como cajas de texto nativas, tarjetas y etiquetas como formas nativas, figuras como imágenes de
// report/informe/img/, esquema del montaje con formas nativas. Notas del orador: leídas de notas_del_orador_5min.txt
// (correr antes gen_slides_5min.py). Fuentes: Cambria (títulos) y Calibri (texto) en lugar de Source Serif 4 e
// IBM Plex Sans, que PowerPoint no trae.
// Uso (pptxgenjs no está en el repo; instalarlo en cualquier carpeta y apuntar NODE_PATH ahí):
//   NODE_PATH=<carpeta>/node_modules node report/presentacion_agentes/gen_pptx_5min.js
//   -> report/presentacion_agentes/presentacion_5min.pptx
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const HERE = __dirname;
const IMG = path.join(HERE, "..", "informe", "img");
const C = { DARK: "14213D", LIGHT: "FBFBF8", INK: "14213D", BODY: "3D4A5C", MUTED: "6A7382", ACC: "D9692B", ACC2: "2F6FB0",
            LINE: "DDDBD2", PEACH: "F6D9C6", WHITE: "FFFFFF", SUB: "BFD0E6" };
const SERIF = "Cambria", SANS = "Calibri";
// El deck HTML mide 1920 x 1080 px; LAYOUT_WIDE mide 13.333 x 7.5 in. 1 px = 13.333/1920 in; fuente: 1 px = 0.5 pt.
const X = (v) => (v * 13.333) / 1920;
const F = (v) => v * 0.5;

// Notas del orador por id de slide
const notas = {};
{
  const t = fs.readFileSync(path.join(HERE, "notas_del_orador_5min.txt"), "utf8").split(/\n\n+/);
  for (const b of t) {
    const m = b.match(/^\S+\. (\w+)(?: \(\d+ s\))?\n([\s\S]*)$/);
    if (m) notas[m[1]] = m[2].trim();
  }
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Agentes de IA en microscopía (5 min)";
pres.author = "Lucas Costilla";

function txt(s, text, x, y, w, h, o = {}) {
  s.addText(text, Object.assign({ x: X(x), y: X(y), w: X(w), h: X(h), fontFace: SANS, fontSize: F(34), color: C.BODY,
    margin: 0, valign: "top", isTextBox: true, paraSpaceAfter: 0 }, o));
}
function box(s, x, y, w, h, o = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, Object.assign({ x: X(x), y: X(y), w: X(w), h: X(h), rectRadius: 0.12,
    fill: { color: C.WHITE }, line: { color: C.LINE, width: 0.75 } }, o));
}
function bar(s, x, y, h, color) { // borde izquierdo de color, como en el deck HTML
  s.addShape(pres.shapes.RECTANGLE, { x: X(x), y: X(y + 6), w: X(9), h: X(h - 12), fill: { color }, line: { color, width: 0 } });
}
function tag(s, t, color = C.ACC) {
  const w = 60 + t.length * 22;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(128), y: X(112), w: X(w), h: X(52), rectRadius: 0.2,
    fill: { color: C.LIGHT }, line: { color, width: 1.5 } });
  txt(s, t.toUpperCase(), 128, 112, w, 52, { fontSize: F(26), bold: true, color, align: "center", valign: "middle", charSpacing: 2 });
}
function title(s, t, y = 180, h = 90, color = C.INK) {
  txt(s, t, 128, y, 1664, h, { fontFace: SERIF, fontSize: F(66), bold: true, color, valign: "top" });
}
function foot(s, t, color = C.MUTED) { txt(s, t, 128, 990, 400, 34, { fontSize: F(24), color }); }
function img(s, name, x, y, w, h) { s.addImage({ path: path.join(IMG, name), x: X(x), y: X(y), w: X(w), h: X(h) }); }
function imgFit(s, name, x, y, w, h, iw, ih) { // mantiene la proporción, centrado en la caja
  const r = Math.min(w / iw, h / ih), ww = iw * r, hh = ih * r;
  img(s, name, x + (w - ww) / 2, y + (h - hh) / 2, ww, hh);
}
function newSlide(id, bg = C.LIGHT) {
  const s = pres.addSlide();
  s.background = { color: bg };
  if (notas[id]) s.addNotes(notas[id]);
  return s;
}
const run = (t, o = {}) => ({ text: t, options: o });

// 1. Portada
{
  const s = newSlide("portada", C.DARK);
  txt(s, "PROYECTO DE MICROSCOPÍA COMPUTACIONAL", 128, 330, 1664, 50, { fontSize: F(32), bold: true, color: C.ACC, charSpacing: 2 });
  txt(s, "Un mes con agentes de IA en un problema de Pticografía de Fourier", 128, 400, 1500, 360,
      { fontFace: SERIF, fontSize: F(104), bold: true, color: C.LIGHT, valign: "top" });
  txt(s, "Qué se resolvió y qué no", 128, 770, 1664, 60, { fontSize: F(44), color: C.SUB });
  txt(s, "Lucas Costilla · semana del 28/09/2026", 128, 940, 1664, 44, { fontSize: F(30), color: C.SUB });
}

// 2. Problema / pregunta
{
  const s = newSlide("problema");
  tag(s, "Problema / pregunta");
  title(s, "Ver más detalle que lo que permite el objetivo y recuperar la fase de una muestra", 180, 170);
  const P = { fontSize: F(34), color: C.BODY };
  txt(s, [run("Un microscopio no separa detalles menores a un límite: con nuestro objetivo, "), run("~3,8 µm", { bold: true }), run(".")], 128, 390, 1080, 100, P);
  txt(s, [run("FPM", { bold: true }), run(": una foto por LED, cada una con la iluminación desde otro ángulo; un programa las combina para bajar, en teoría, a "),
          run("0,5–1 µm", { bold: true }), run(" y además recuperar la "), run("fase", { italic: true }), run(" (cuánto se retrasa la luz).")], 128, 500, 1080, 170, P);
  txt(s, [run("El programa siempre devuelve una imagen: "), run("¿Es la muestra en alta resolución o lo inventó?", { bold: true })], 128, 690, 1080, 100, P);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(128), y: X(810), w: X(1080), h: X(130), rectRadius: 0.1, fill: { color: C.PEACH }, line: { color: C.PEACH, width: 0 } });
  txt(s, "¿Qué pudieron resolver los agentes de IA en este problema, y qué no?", 160, 810, 1020, 130, { fontSize: F(34), bold: true, color: C.INK, valign: "middle" });
  // esquema del montaje (viewBox 620 x 700 del SVG, escalado a 520 px de ancho)
  const ox = 1272, oy = 380, k = 520 / 620, P2 = (v) => v * k;
  for (let i = 0; i < 9; i++) {
    const on = i === 6;
    s.addShape(pres.shapes.OVAL, { x: X(ox + P2(70 + i * 60 - 16)), y: X(oy + P2(70 - 16)), w: X(P2(32)), h: X(P2(32)),
      fill: on ? { color: C.ACC } : { color: C.LIGHT }, line: { color: on ? C.ACC : C.MUTED, width: 1.5 } });
  }
  s.addShape(pres.shapes.LINE, { x: X(ox + P2(330)), y: X(oy + P2(90)), w: X(P2(100)), h: X(P2(240)), flipH: true, line: { color: C.ACC, width: 2.5 } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(ox + P2(150)), y: X(oy + P2(330)), w: X(P2(320)), h: X(P2(30)), rectRadius: 0.03,
    fill: { color: C.PEACH }, line: { color: C.MUTED, width: 1 } });
  s.addShape(pres.shapes.TRAPEZOID, { x: X(ox + P2(230)), y: X(oy + P2(400)), w: X(P2(160)), h: X(P2(80)), rotate: 180,
    fill: { color: C.LIGHT }, line: { color: C.INK, width: 1.5 } });
  s.addShape(pres.shapes.LINE, { x: X(ox + P2(310)), y: X(oy + P2(480)), w: 0, h: X(P2(80)), line: { color: C.INK, width: 1.5 } });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(ox + P2(230)), y: X(oy + P2(560)), w: X(P2(160)), h: X(P2(90)), rectRadius: 0.06,
    fill: { color: C.LIGHT }, line: { color: C.INK, width: 1.5 } });
  const L = { fontSize: F(26), color: C.BODY };
  txt(s, "Matriz de LEDs", ox + P2(20), oy + P2(105), 260, 36, L);
  txt(s, "Muestra", ox + P2(480), oy + P2(327), 160, 36, L);
  txt(s, "Objetivo", ox + P2(400), oy + P2(425), 160, 36, L);
  txt(s, "Cámara", ox + P2(400), oy + P2(590), 160, 36, L);
  foot(s, "2 / 6");
}

// 3. Resultado principal
{
  const s = newSlide("rgb_b");
  tag(s, "Resultado principal", C.ACC2);
  title(s, "Reconstrucción con imágenes tomadas en el laboratorio en 3 canales RGB", 180, 170);
  imgFit(s, "fig_rgb_2809b_es.png", 128, 370, 870, 575, 1170, 774);
  txt(s, "QUÉ SUGIRIERON LOS AGENTES PARA LAS CAPTURAS", 1046, 375, 746, 40, { fontSize: F(22), bold: true, color: C.MUTED, charSpacing: 1 });
  const items = [
    ["Varios tiempos por LED: corto en luz directa, largo en luz inclinada", "24/09: 131 de 169 LEDs con señal útil (señal/ruido > 3)"],
    ["Fotos a oscuras para restar el fondo del sensor", "Repetidas cuando salieron saturadas"],
    ["El tiempo de cada LED, calculado de la captura anterior", "Mapa de exposición por LED y por color"],
    ["Alejar la matriz de 74 a ~98 mm", "Más solapamiento entre LEDs vecinos: de 31 % a 46 %"],
    ["Cada color en su propio foco", "Con un solo foco, solo el color enfocado se parecía a la muestra"]];
  const hs = [118, 118, 118, 88, 88];
  let y = 430;
  items.forEach(([t, d], i) => {
    txt(s, String(i + 1), 1046, y, 40, 50, { fontFace: SERIF, fontSize: F(36), bold: true, color: C.ACC2 });
    txt(s, t, 1102, y, 690, hs[i] - 40, { fontSize: F(28), bold: true, color: C.INK });
    txt(s, d, 1102, y + hs[i] - 38, 690, 34, { fontSize: F(23), color: C.MUTED });
    y += hs[i] + 6;
  });
  foot(s, "3 / 6");
}

// 4. Validación
{
  const s = newSlide("validacion");
  tag(s, "Validación", C.ACC2);
  title(s, "¿Cómo decidimos si confiar?");
  imgFit(s, "fig_fase_2809b.png", 128, 300, 760, 352, 1210, 561);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(128), y: X(680), w: X(760), h: X(170), rectRadius: 0.1, fill: { color: C.PEACH }, line: { color: C.PEACH, width: 0 } });
  txt(s, [run("Recuperamos la "), run("fase", { bold: true }), run(" de la muestra real (la reconstrucción predice fotos que no usó). "),
          run("Ganar resolución todavía no está demostrado.", { bold: true })], 156, 680, 704, 170, { fontSize: F(29), color: C.INK, valign: "middle" });
  const tests = [
    ["1", "¿Funciona donde conocemos la respuesta?", "Funciona", C.ACC2, "Simulación: amplitud 0,997 · fase 0,64 con la matriz a 75 mm", "Fase 0,97 a 100 mm (más solapamiento). 1 = igual a la muestra inventada", 190],
    ["2", "¿Predice las fotos que no usó?", "Pasa", C.ACC2, "Error 0,46–0,62 (0 = perfecto; sin reconstruir: 0,98)", "Se apartan LEDs, se reconstruye sin ellos y se compara la foto predicha con la medida", 200],
    ["3", "¿Dos reconstrucciones independientes ven el mismo detalle fino?", "No alcanza", C.ACC, "0,043–0,099 (1 = idénticas): de 5 a 14 veces el azar; umbral 0,143", "Cada una con la mitad de los LEDs; se compara el detalle más fino que el objetivo", 210]];
  let y = 290;
  for (const [k, q, v, col, val, how, h] of tests) {
    box(s, 928, y, 864, h); bar(s, 928, y, h, col);
    txt(s, k, 956, y + 16, 40, 44, { fontFace: SERIF, fontSize: F(34), bold: true, color: col });
    txt(s, q, 996, y + 18, 590, 76, { fontSize: F(25), bold: true, color: C.INK });
    txt(s, v, 1590, y + 18, 180, 40, { fontSize: F(27), bold: true, color: col, align: "right" });
    const yv = y + 98;
    txt(s, val, 956, yv, 816, 36, { fontSize: F(23), color: C.INK });
    txt(s, how, 956, yv + 40, 816, h - (yv - y) - 44, { fontSize: F(22), color: C.MUTED });
    y += h + 12;
  }
  txt(s, [run("Criterios y umbrales escritos "), run("antes", { bold: true }), run(" de mirar los datos reales.")], 928, y + 4, 864, 36, { fontSize: F(25), color: C.MUTED });
  foot(s, "4 / 6");
}

// 5. Experiencia / aprendizaje
{
  const s = newSlide("aprendizaje");
  tag(s, "Experiencia / aprendizaje");
  title(s, "Pasar todas las pruebas no alcanza");
  imgFit(s, "fig_congelado.png", 128, 300, 760, 286, 1430, 539);
  const P = { fontSize: F(27), color: C.BODY };
  txt(s, "El programa mejora la imagen de a poco: compara las fotos que predice con las medidas y la corrige un poco en cada vuelta.", 932, 290, 860, 80, P);
  txt(s, [run("Esas correcciones eran "), run("~8.000 veces", { bold: true }), run(" más chicas de lo debido: después de cientos de vueltas devolvía casi la foto original, "),
          run("y aun así pasaba cientos de pruebas", { bold: true }), run(", hechas con imágenes chiquitas (16–32 píxeles).")], 932, 385, 860, 120, P);
  txt(s, "Lo encontró un agente que investigaba otra cosa. Los agentes también se equivocaron: supusieron mal el hardware.", 932, 520, 860, 80, P);
  const rules = [["Probar con datos reales", "Del tamaño y el tipo reales, no solo casos chicos"],
                 ["Criterio escrito antes", "Qué cuenta como éxito, antes de ver el resultado"],
                 ["Verificación independiente", "Otro agente, con otro código, rehace cada número"],
                 ["Alguien que conozca el equipo", "Los agentes no saben lo que no se les dice"]];
  const w = (1664 - 3 * 20) / 4;
  rules.forEach(([t, d], i) => {
    const x = 128 + i * (w + 20);
    box(s, x, 640, w, 250);
    txt(s, String(i + 1), x + 26, 662, 60, 50, { fontFace: SERIF, fontSize: F(44), bold: true, color: C.ACC });
    txt(s, t, x + 26, 722, w - 52, 76, { fontSize: F(28), bold: true, color: C.INK });
    txt(s, d, x + 26, 800, w - 52, 76, { fontSize: F(24), color: C.BODY });
  });
  foot(s, "5 / 6");
}

// 6. Cierre
{
  const s = newSlide("cierre", C.DARK);
  title(s, "En resumen", 112, 90, C.LIGHT);
  const steps = [["Los agentes: más útiles para auditar que para juzgar resultados reales", "Aportan volumen, auditoría y diseño de experimentos; fallan en el mundo físico y por exceso de confianza"],
                 ["Ya medido: el foco de cada color pesa más que el solapamiento", "Provisional: el modelo todavía no incluye el desenfoque"],
                 ["Próximo: una placa de calibración con líneas de ancho conocido", "Decide si el método gana detalle en nuestro montaje"],
                 ["Próximo: combinar verde y azul con la dispersión conocida, en datos reales", "En simulación funciona; con datos reales todavía no se probó"]];
  let y = 240;
  for (const [t, d] of steps) {
    txt(s, t, 128, y, 1664, 52, { fontSize: F(38), bold: true, color: C.LIGHT });
    txt(s, d, 128, y + 56, 1664, 44, { fontSize: F(28), color: C.SUB });
    y += 142;
  }
  txt(s, "Informe completo: https://claude.ai/code/artifact/de7eab31-d9e0-4828-a62d-285ba0d46a98", 128, 900, 1664, 44, { fontSize: F(28), color: C.ACC });
  foot(s, "6 / 6");
}

// Apéndice: separador
{
  const s = newSlide("apendice", C.DARK);
  txt(s, "APÉNDICE", 128, 380, 1664, 50, { fontSize: F(32), bold: true, color: C.ACC, charSpacing: 2 });
  txt(s, "Para preguntas", 128, 450, 1664, 130, { fontFace: SERIF, fontSize: F(96), bold: true, color: C.LIGHT });
  txt(s, "Control de los agentes · quién hizo qué · reconstrucción conjunta · foco o solapamiento", 128, 610, 1664, 60, { fontSize: F(36), color: C.SUB });
}

function card(s, x, y, w, h, t, lines, color, size = 26) {
  box(s, x, y, w, h);
  txt(s, t, x + 32, y + 26, w - 64, 44, { fontSize: F(30), bold: true, color });
  const body = [];
  lines.forEach((l, i) => body.push(...(Array.isArray(l) ? l : [run(l)]).map((r, j, a) =>
    ({ text: r.text, options: Object.assign({}, r.options, j === a.length - 1 && i < lines.length - 1 ? { breakLine: true } : {}) }))));
  txt(s, body, x + 32, y + 80, w - 64, h - 100, { fontSize: F(size), color: C.BODY, paraSpaceAfter: 6 });
}

// A1
{
  const s = newSlide("a_control");
  tag(s, "Apéndice", C.MUTED);
  title(s, "¿Cómo controlamos a los agentes?");
  const w = (1664 - 24) / 2, h = 250;
  card(s, 128, 300, w, h, "Cada número con su fuente", [[run("El resumen tiene "), run("41", { bold: true }), run(" números marcados; un script verifica que cada uno coincide con el registro (69 entradas).")],
       "El registro lo escribe solo un programa, no una persona ni un agente."], C.ACC2);
  card(s, 128 + w + 24, 300, w, h, "Pruebas que el agente no puede editar", ["En la reconstrucción conjunta, la prueba de aceptación tenía su hash fijado.",
       "Criterios y umbrales fijos: no se cambian después de ver resultados."], C.ACC2);
  const extra = process.env.TESTS_OK ? [`Suite de pruebas automáticas: ${process.env.TESTS_OK} pasan`] : [];
  card(s, 128, 574, w, h, "Un verificador independiente", ["Otro agente rehace cada número con su propio código.", "Ej.: gradiente 1,03e-8; el verificador obtuvo 6,0e-9."], C.ACC2);
  card(s, 128 + w + 24, 574, w, h, "Criterios escritos antes", ["Cada experimento largo tiene un plan en docs/ con los criterios de éxito, escrito antes de correr."].concat(extra), C.ACC2);
  foot(s, "A1");
}

// A2
{
  const s = newSlide("a_quien");
  tag(s, "Apéndice", C.MUTED);
  title(s, "¿Quién hizo qué?");
  const w = (1664 - 32) / 2, h = 300;
  card(s, 128, 290, w, h, "La persona (Lucas)", ["Armó el montaje y tomó las capturas en el laboratorio",
       "Dio los datos reales del hardware: objetivo, cámara, altura de la matriz", "Decidió qué probar y tuvo el criterio final"], C.ACC, 28);
  card(s, 128 + w + 32, 290, w, h, "Los agentes (Claude)", [[run("El código del simulador y de la reconstrucción: "), run("97 de 99", { bold: true }), run(" commits con Claude como coautor")],
       "Análisis, diagnóstico de errores e informes", "Sugerencias de captura y esta presentación"], C.ACC2, 28);
  txt(s, "Los agentes no hacen commits por su cuenta: solo cuando la persona lo pide.", 128, 614, 1664, 40, { fontSize: F(28), color: C.MUTED });
  txt(s, "Una ronda de un equipo de agentes", 128, 700, 1664, 40, { fontSize: F(26), bold: true, color: C.MUTED });
  const pills = [["Persona: la pregunta", 300], ["Agente líder", 200], ["Trabajadores", 210], ["Verificador", 190], ["Persona decide", 240]];
  let x = 128;
  pills.forEach(([t, w2], i) => {
    const main = t === "Verificador";
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(x), y: X(756), w: X(w2), h: X(76), rectRadius: 0.1,
      fill: { color: main ? C.PEACH : C.WHITE }, line: { color: main ? C.ACC : C.LINE, width: 1.5 } });
    txt(s, t, x, 756, w2, 76, { fontSize: F(26), bold: true, color: C.INK, align: "center", valign: "middle" });
    x += w2;
    if (i < pills.length - 1) {
      s.addShape(pres.shapes.LINE, { x: X(x + 12), y: X(794), w: X(40), h: 0, line: { color: C.MUTED, width: 1.5, endArrowType: "triangle" } });
      x += 64;
    }
  });
  foot(s, "A2");
}

// A3
{
  const s = newSlide("a_conjunta");
  tag(s, "Apéndice", C.MUTED);
  title(s, "Reconstruir los tres colores juntos: pasó las pruebas y no sirve", 180, 170);
  imgFit(s, "fig_conjunta_verdad_vs_conjunta.png", 128, 380, 880, 390, 1118, 495);
  const stats = [["Ajuste de las fotos", "0,97 × el piso de ruido", "Mejor que la muestra verdadera", C.ACC2],
                 ["Espesor contra el verdadero", "−0,09", "Correlación (1 = perfecto). Más épocas, peor: −0,04 → −0,09", C.ACC],
                 ["La cadena simple", "0,945", "Verde + azul por separado, con la dispersión conocida", C.ACC2]];
  let y = 380;
  for (const [l, v, d, col] of stats) {
    box(s, 1052, y, 740, 150); bar(s, 1052, y, 150, col);
    txt(s, l, 1082, y + 18, 690, 32, { fontSize: F(24), color: C.MUTED });
    txt(s, v, 1082, y + 52, 690, 44, { fontSize: F(34), bold: true, color: col });
    txt(s, d, 1082, y + 102, 690, 34, { fontSize: F(24), color: C.BODY });
    y += 166;
  }
  txt(s, "En simulación; no se pasó a datos reales. La prueba de aceptación pasó: solo exigía los entregables.", 128, 900, 1664, 40, { fontSize: F(25), color: C.MUTED });
  foot(s, "A3");
}

// A4
{
  const s = newSlide("a_foco");
  tag(s, "Apéndice", C.MUTED);
  title(s, "¿Qué limita más: el foco o el solapamiento?");
  const hd = (t) => ({ text: t, options: { bold: true, fontSize: F(26), color: C.INK, fill: { color: C.LIGHT } } });
  const c = (t, b = false, col = C.INK) => ({ text: t, options: { bold: b, fontSize: F(30), color: col } });
  s.addTable([
    [hd("Rojo, matriz a 98 mm"), hd("Error en fotos no usadas (sin reconstruir ~0,98)"), hd("Mitades (detalle fino)")],
    [c("En su propio foco", true), c("0,46", true, C.ACC2), c("0,083", true, C.ACC2)],
    [c("Con el foco del verde"), c("0,81"), c("0,021")],
    [c("Con el foco del azul"), c("0,86"), c("0,024")]],
    { x: X(128), y: X(290), w: X(1664), colW: [X(760), X(520), X(384)], fontFace: SANS, color: C.INK, margin: 0.08,
      border: { type: "solid", color: C.LINE, pt: 0.75 }, fill: { color: C.WHITE }, rowH: [X(80), X(62), X(62), X(62)] });
  const w = (1664 - 48) / 3;
  card(s, 128, 620, w, 230, "Solo el foco", ["Mitades ×3,5 a ×4 al enfocar cada color"], C.ACC2, 28);
  card(s, 128 + w + 24, 620, w, 230, "Solo la geometría", ["Verde en foco, de 74 a 98 mm: mitades 0,024 → 0,043 (×1,8)"], C.INK, 28);
  card(s, 128 + 2 * (w + 24), 620, w, 230, "Provisional", ["El modelo no incluye el desenfoque: uno que lo incluya podría recuperar parte"], C.MUTED, 28);
  foot(s, "A4");
}

pres.writeFile({ fileName: path.join(HERE, "presentacion_5min.pptx") }).then((f) => console.log(f));
