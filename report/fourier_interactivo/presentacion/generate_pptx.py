"""Genera una presentación editable reutilizando los datos del HTML V1.
Requiere python-pptx. No recalcula las simulaciones.
"""
from pathlib import Path
from io import BytesIO
import base64
import json
import math
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_MARK
from pptx.chart.data import CategoryChartData
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

ROOT=Path(__file__).resolve().parent
html=(ROOT.parent/'index.html').read_text()
D=json.loads(html.split('const D=',1)[1].split(';\nconst $=',1)[0])
R=Presentation(); R.slide_width=Inches(13.333333); R.slide_height=Inches(7.5)
R.core_properties.title='Una imagen, muchos ángulos · Pticografía de Fourier'
R.core_properties.subject='Recorrido didáctico basado en el HTML interactivo V1'
R.core_properties.language='es-AR'
C={'bg':'0B1220','panel':'131F30','text':'E8EEF6','muted':'A0B3C9','green':'73E5B3','gold':'FFCC75','blue':'40A6FF','orange':'FF8C52','line':'36566B'}
def color(c):return RGBColor.from_string(C.get(c,c))
def text(s,t,x,y,w,h=.5,size=20,c='text',bold=False,align=None):
    sh=s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=sh.text_frame;tf.word_wrap=True
    tf.margin_left=tf.margin_right=0;tf.margin_top=tf.margin_bottom=0
    for i,line in enumerate(t.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line
        p.font.name='Liberation Sans';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color(c)
        p.space_after=Pt(7)
        if align is not None:p.alignment=align
    return sh

def shape(s,kind,x,y,w,h,fill=None,line='line',width=1):
    sh=s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:sh.fill.solid();sh.fill.fore_color.rgb=color(fill)
    else:sh.fill.background()
    if line:sh.line.color.rgb=color(line);sh.line.width=Pt(width)
    else:sh.line.fill.background()
    return sh

def line(s,x1,y1,x2,y2,c='green',width=2):
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2))
    sh.line.color.rgb=color(c);sh.line.width=Pt(width);return sh

def arrow(s,x,y,w=.65):
    return shape(s,MSO_SHAPE.RIGHT_ARROW,x,y,w,.28,'green',None)

def image(s,src,x,y,z,label=None):
    pic=s.shapes.add_picture(BytesIO(base64.b64decode(src.split(',',1)[1])),Inches(x),Inches(y),width=Inches(z),height=Inches(z))
    if label:text(s,label,x-.08,y+z+.12,z+.16,.65,16,'muted',align=PP_ALIGN.CENTER)
    return pic

def note(s,t):s.notes_slide.notes_text_frame.text=t

def slide(title,sub,chapter,notes=''):
    s=R.slides.add_slide(R.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=color('bg')
    text(s,chapter.upper(),.6,.32,11,.28,12,'green',True)
    text(s,title,.6,.82,12.1,.68,30,bold=True)
    text(s,sub,.6,1.52,12.1,.55,19,'muted')
    line(s,.6,6.95,12.72,6.95,'line',.7)
    text(s,'Pticografía de Fourier · simulación didáctica · V1',.6,7.08,10,.22,10,'muted')
    text(s,f'{len(R.slides):02d} / 18',11.7,7.06,1,.25,11,'muted',align=PP_ALIGN.RIGHT)
    note(s,notes)
    return s

def takeaway(s,t):text(s,t,.7,6.37,11.9,.45,20,'green',True)

def microscope(s,j,x=.8,y=2.28,w=5.4,estimated=False):
    a,b=D['leds'][j];cx=x+w*.39
    camera=y+.1;objective=y+1;sample=y+2;ledy=y+3.3
    line(s,cx,camera,cx,ledy,'line',1)
    shape(s,MSO_SHAPE.RECTANGLE,cx-.45,camera,.9,.25,'panel','line')
    shape(s,MSO_SHAPE.OVAL,cx-.55,objective,1.1,.20,'panel','green')
    line(s,cx-.7,sample,cx+.7,sample,'gold',5)
    for k in range(-3,4):shape(s,MSO_SHAPE.OVAL,cx+k*.27-.055,ledy,.11,.11,'green' if k==a else 'line',None)
    for k in [-1,0,1]:
        line(s,cx+a*.27+k*.10,ledy,cx+k*.10,sample,'green',1)
        line(s,cx,sample,cx+k*.42,objective+.1,'gold',1)
        line(s,cx+k*.42,objective+.1,cx+k*.15,camera+.25,'gold',1)
    for yy,t in [(camera,'Cámara'),(objective,'Objetivo'),(sample,'Muestra estimada' if estimated else 'Muestra')]:text(s,t,cx+.83,yy-.03,2,.4,16,'muted')
    text(s,f'LED ({a}, {b}) · proyección x–z',x,ledy+.36,w,.4,14,'muted')

def window(s,src,x,y,z,j,coverage=False):
    image(s,src,x,y,z)
    ids=range(49) if coverage else []
    for k in ids:
        a,b=D['leds'][k];shape(s,MSO_SHAPE.OVAL,x+z*(64-a*10-18)/128,y+z*(64-b*10-18)/128,z*36/128,z*36/128,None,'line',.45)
    a,b=D['leds'][j];shape(s,MSO_SHAPE.OVAL,x+z*(64-a*10-18)/128,y+z*(64-b*10-18)/128,z*36/128,z*36/128,None,'green',2)
    line(s,x+z*.47,y+z*.5,x+z*.53,y+z*.5,'gold',1)
    line(s,x+z*.5,y+z*.47,x+z*.5,y+z*.53,'gold',1)

G=D['guide'];g=G[1];J=[a['led'] for a in G];labels=['Central','Oblicuo · campo claro','Oblicuo · campo oscuro']
s=slide('Una imagen. Muchos ángulos.','Cómo la pticografía de Fourier recupera detalle y estima la fase.','Laboratorio visual', 'Presentación derivada de report/fourier_interactivo/index.html. Textos, flechas, esquemas y gráfico son editables; las imágenes son PNG del HTML. El HTML sigue siendo el complemento interactivo.')
text(s,'Capturar\nExplorar Fourier\nReconstruir',.9,2.65,5,2.2,29,'green',True)
image(s,D['truth']['amp'],6.5,2.45,2.5,'Amplitud de la muestra');image(s,D['truth']['phase'],9.4,2.45,2.5,'Fase de la muestra')
takeaway(s,'Una única muestra · 49 iluminaciones · una estimación compartida')
s=slide('Cambia la iluminación, no la muestra','Cada LED ilumina la misma región desde otro ángulo.','01 · Capturar','Modelo escalar de muestra delgada, iluminación monocromática por un LED a la vez y pupila circular ideal. El esquema es una proyección x–z; la coordenada y también puede inclinar la iluminación fuera del plano. No está a escala.')
microscope(s,J[1]);image(s,D['captures'][J[1]],8.1,2.35,3.1,'Intensidad en la cámara')
takeaway(s,'La cámara mide intensidad; la fase no se registra directamente.')
s=slide('Cada LED produce una foto distinta','Las tres capturas usan la misma escala de intensidad.','01 · Capturar')
for i,j in enumerate(J):image(s,D['captures'][j],1.05+i*4.05,2.42,3.1,labels[i])
takeaway(s,'Una foto oscura puede contener información de la muestra.')
s=slide('Campo oscuro: poca luz, información útil','La luz directa queda fuera de la apertura del objetivo.','01 · Capturar','Ambas imágenes corresponden a la misma captura. La imagen derecha está realzada con su máximo individual: sus brillos no son comparables con los de otros LEDs. El realce solo modifica la visualización.')
image(s,D['captures'][J[2]],2,2.38,3.1,'Escala común');arrow(s,6.25,3.7);image(s,D['enhanced'][J[2]],8.1,2.38,3.1,'Misma captura, realzada')
takeaway(s,'Realzar permite ver el detalle; no agrega información medida.')
s=slide('Cada ángulo abre una ventana en Fourier','El objetivo conserva su apertura; cambia la región accesible del objeto.','02 · Fourier','Fondo: log(1+|O|) de la muestra conocida, no una medición de la cámara. Ventanas en coordenadas del objeto: centro −q, radio 18 bins. Frecuencia de iluminación: pasos de 10 bins. Iq = |F⁻¹{P(f) O(f−q)}|². Los círculos de la derecha muestran todas las posiciones, sin simular una intensidad acumulada.')
for i,j in enumerate([J[0],J[2],48]):
    x=1.05+i*4.05;window(s,D['spectrum'],x,2.4,3.1,j,i==2);text(s,['LED central','LED oblicuo','Cobertura de los 49 LEDs'][i],x-.15,5.67,3.4,.55,17,'muted',align=PP_ALIGN.CENTER)
takeaway(s,'Más ángulos permiten acceder a frecuencias que un solo LED no transmite.')
s=slide('Las ventanas se solapan','Dos mediciones dependen de una región compartida del espectro.','02 · Fourier','Las máscaras tienen radio 18 bins y centros separados 10 bins para LEDs vecinos. El solapamiento aporta restricciones compartidas; no garantiza por sí solo una reconstrucción única o exacta.')
image(s,D['spectrum'],1.05,2.3,3.65)
for j,c in [(J[0],'green'),(J[1],'blue')]:
    a,b=D['leds'][j];z=3.65;shape(s,MSO_SHAPE.OVAL,1.05+z*(64-a*10-18)/128,2.3+z*(64-b*10-18)/128,z*36/128,z*36/128,None,c,3)
text(s,'Ventana A',5.4,2.65,5,.5,24,'green',True);text(s,'Ventana B',5.4,3.28,5,.5,24,'blue',True)
text(s,'La misma estimación debe ser\ncompatible con ambas capturas.',5.4,4.15,6.6,1.3,25)
takeaway(s,'Reconstruir exige hacer compatibles las mediciones entre sí.')
s=slide('Empezamos con una aproximación','Amplitud inicial = raíz de la intensidad de la captura central.','03 · Reconstruir / 1','La raíz de la captura central aproxima el módulo del campo filtrado; no es la amplitud verdadera de alta resolución. La fase cero es una hipótesis inicial. o₀ = √Icentral exp(i·0).')
image(s,D['captures'][0],.9,2.5,2.8,'Captura central · intensidad');arrow(s,4.02,3.7);text(s,'√I',4.12,3.07,.7,.4,24,'gold')
image(s,g['before']['amp'],5,2.5,2.8,'Amplitud inicial');image(s,g['before']['phase'],9.3,2.5,2.8,'Fase inicial = 0')
takeaway(s,'La fase inicial es una suposición, no una medición.')
s=slide('¿Qué foto produciría nuestra estimación?','Aplicamos el modelo del microscopio con un LED elegido.','03 · Reconstruir / 2','Se muestra la primera actualización aislada con el LED oblicuo de campo claro. La estimación se propaga con zⱼ=AⱼS; la foto predicha es |zⱼ|². No se utiliza la muestra verdadera para calcular la predicción.')
microscope(s,J[1],estimated=True);arrow(s,6.3,3.8);image(s,g['predicted'],8.1,2.4,3.1,'Foto predicha · campo claro')
takeaway(s,'Esta foto la calcula el modelo a partir del objeto estimado.')
s=slide('Medición y predicción: el mismo LED','La medición queda fija; la predicción depende de nuestra estimación.','03 · Reconstruir / 3','Las seis imágenes conservan la misma escala global de la V1. El campo oscuro puede verse tenue. Las imágenes de una columna pertenecen al mismo LED.')
text(s,'Medida',.65,2.82,1.4,.5,20,'green',True);text(s,'Predicha',.65,4.95,1.4,.5,20,'gold',True)
for i,j in enumerate(J):
    x=2.55+i*3.55;text(s,labels[i],x-.35,2.12,2.6,.4,15,'muted',align=PP_ALIGN.CENTER)
    image(s,D['captures'][j],x,2.62,1.75);image(s,G[i]['predicted'],x,4.5,1.75)
s=slide('La diferencia indica qué corregir','Comparamos módulos: raíz de intensidad medida y amplitud predicha.','03 · Reconstruir / 4','rⱼ = |zⱼ| − √Iⱼ. Lⱼ = Σ rⱼ². El residual usa escala fija ±0,25 con saturación. Naranja: exceso; azul: déficit; oscuro: acuerdo. Las otras dos imágenes muestran intensidades.')
for src,x,l in [(D['captures'][J[1]],.9,'Intensidad medida'),(g['predicted'],5,'Intensidad predicha'),(g['residual'],9.15,'Residual de amplitud')]:image(s,src,x,2.5,2.8,l)
text(s,'Naranja: sobra',4.9,6.3,3.2,.45,19,'orange');text(s,'Azul: falta',8.4,6.3,3,.45,19,'blue')
s=slide('Llevamos la corrección a Fourier','El residual y la fase estimada determinan una corrección compleja.','03 · Reconstruir / 5','gⱼ = Aⱼ†[(|zⱼ|−√Iⱼ) zⱼ/max(|zⱼ|,10⁻¹²)]. ΔS=−μgⱼ. El adjunto transporta al espectro el residual multiplicado por la fase estimada del campo. La imagen derecha muestra solo el módulo del cambio, realzado individualmente; su fase también participa.')
image(s,g['residual'],2,2.4,3.1,'Residual en la imagen');arrow(s,6.2,3.7);image(s,g['gradient'],8.1,2.4,3.1,'Corrección en Fourier · módulo')
takeaway(s,'La corrección puede modificar tanto la amplitud como la fase.')
s=slide('Sumamos la corrección a la estimación','El cambio se restringe a la ventana del LED elegido.','03 · Reconstruir / 5','S⁺=S−μgⱼ. Se muestran log(1+|S|) antes y después con la misma escala. Es una suma compleja, no una suma de los brillos de estas figuras. No se dibujan puntos esquemáticos sobre los datos.')
window(s,g['spectrumBefore'],2,2.4,3.1,J[1]);window(s,g['spectrumAfter'],8.1,2.4,3.1,J[1]);arrow(s,6.2,3.7)
text(s,'Antes',2,5.65,3.1,.4,18,'muted',align=PP_ALIGN.CENTER);text(s,'Después',8.1,5.65,3.1,.4,18,'muted',align=PP_ALIGN.CENTER)
takeaway(s,'Fuera de la ventana activa, el espectro permanece igual.')
s=slide('Actualizamos amplitud y fase','Volvemos del espectro al objeto: un paso puede producir cambios pequeños.','03 · Reconstruir / 6','o⁺=F⁻¹{S⁺}. Los estados antes y después usan la misma referencia de fase global. V1 representa fase de 0 a 1 rad, con saturación fuera del intervalo; cambios negativos pueden quedar ocultos en esta escala. La amplitud va de 0 a 1.')
for start,state,label in [(.85,g['before'],'Antes'),(7.3,g['after'],'Después')]:
    text(s,label,start,2.13,5.2,.45,23,'green',True,PP_ALIGN.CENTER)
    image(s,state['amp'],start,2.82,2.3,'Amplitud');image(s,state['phase'],start+2.75,2.82,2.3,'Fase')
takeaway(s,'La imagen actualizada debe explicar mejor las capturas.')
s=slide('Repetimos con los demás LEDs','Buscamos un solo objeto que explique todas las mediciones.','03 · Reconstruir / 7','Una iteración procesa 49 LEDs, en orden del centro hacia afuera. La corrida completa vuelve a partir de la inicialización: no continúa literalmente el paso aislado anterior. μₜ=0,8(1−exp(−0,3t)), t=1…30, con FFT unitaria.')
for i,t in enumerate(['Predecir','Comparar','Corregir','Otro LED']):
    x=.8+i*3.2;shape(s,MSO_SHAPE.ROUNDED_RECTANGLE,x,3,2.2,1.1,'panel','green');text(s,t,x+.12,3.31,1.96,.45,23,'green',True,PP_ALIGN.CENTER)
    if i<3:arrow(s,x+2.4,3.43,.55)
text(s,'49 LEDs = una iteración',2.2,4.95,9,.7,29,align=PP_ALIGN.CENTER)
takeaway(s,'La corrida completa empieza otra vez desde la estimación inicial.')
s=slide('¿Las capturas coinciden mejor?','La pérdida global compara las 49 capturas sobre el mismo estado.','03 · Iterar','Pérdida relativa de amplitud: Σⱼ |||AⱼS|−√Iⱼ||² / Σⱼ Iⱼ. Se evalúa después de cada iteración completa. Su raíz es el residual relativo de amplitud, no el error del objeto. La fase global se alinea con la referencia solo para visualizar.')
data=CategoryChartData();data.categories=list(range(31));data.add_series('Pérdida relativa',[r['loss'] for r in D['recon']])
chart=s.shapes.add_chart(XL_CHART_TYPE.LINE,Inches(.8),Inches(2.35),Inches(8),Inches(3.7),data).chart
chart.has_legend=False;chart.chart_style=13
chart.has_title=True;chart.chart_title.text_frame.text='Pérdida relativa'
for paragraph in chart.chart_title.text_frame.paragraphs:
    paragraph.font.size=Pt(16);paragraph.font.color.rgb=color('muted')
for parent in [chart._chartSpace,chart._chartSpace.chart.plotArea]:
    sp=parse_xml(f'<c:spPr {nsdecls("c","a")}><a:solidFill><a:srgbClr val="{C["panel"]}"/></a:solidFill><a:ln><a:noFill/></a:ln></c:spPr>')
    parent.insert_element_before(sp,'c:externalData','c:printSettings','c:extLst')
for axis in [chart.category_axis,chart.value_axis]:
    axis.tick_labels.font.size=Pt(13);axis.tick_labels.font.color.rgb=color('muted');axis.format.line.color.rgb=color('line')
chart.category_axis.tick_label_spacing=5;chart.value_axis.minimum_scale=0
chart.series[0].format.line.color.rgb=color('green');chart.series[0].format.line.width=Pt(2.5)
text(s,'Iteración',3.8,6.08,2,.3,14,'muted',align=PP_ALIGN.CENTER)
a,b=[100*math.sqrt(D['recon'][i]['loss']) for i in [0,-1]]
text(s,f'{a:.2f} % → {b:.2f} %',9.2,3,3.4,.7,28,'green',True)
text(s,'Residual relativo\nde amplitud\n(raíz de la pérdida)',9.2,3.9,3.3,1.7,20,'muted')
takeaway(s,'Una pérdida baja no garantiza que la fase sea exacta.')
s=slide('La estimación evoluciona','Amplitud y fase al finalizar distintas iteraciones completas.','03 · Iterar','La fase global de cada estado se alinea con la muestra conocida para visualizar. La referencia no interviene en el gradiente. Misma escala de amplitud y de fase en todas las imágenes.')
text(s,'Amplitud',.65,3,1.5,.45,18,'muted');text(s,'Fase',.65,5.03,1.5,.45,18,'muted')
for i,it in enumerate([0,5,30]):
    x=2.5+i*3.6;text(s,f'Iteración {it}',x-.15,2.15,2.4,.4,21,'green',True,PP_ALIGN.CENTER)
    image(s,D['recon'][it]['amp'],x,2.65,1.78);image(s,D['recon'][it]['phase'],x,4.6,1.78)
s=slide('Comparar el ajuste con la muestra conocida','La amplitud recupera detalle; la fase puede conservar errores.','04 · Interpretar','La referencia conocida se usa para esta comparación educativa y para alinear la fase global, nunca en el gradiente. V1 usa escala de fase de 0 a 1 rad; la saturación limita lo visible. No confundir un buen ajuste de datos con exactitud del objeto.')
for start,state,label in [(.85,D['recon'][30],'Reconstrucción · iteración 30'),(7.3,D['truth'],'Muestra conocida')]:
    text(s,label,start-.15,2.17,5.5,.6,21,'green',True,PP_ALIGN.CENTER)
    image(s,state['amp'],start,2.96,2.3,'Amplitud');image(s,state['phase'],start+2.75,2.96,2.3,'Fase')
takeaway(s,'La referencia permite ver errores que la curva de pérdida no muestra.')
s=slide('Modelo, límites y referencias','Una simulación ideal para entender el proceso.','Apéndice', 'Detalles del cálculo: FFT unitaria, grilla 128×128, radio de pupila 18 bins, pasos de iluminación de 10 bins, 49 capturas, 30 iteraciones. Pérdida de amplitud con descenso incremental de Wirtinger. No reproduce la pérdida de intensidad ni la relajación de ruido del WFP original. Los pasos no se trasladan directamente al solver con FFT no unitaria. HTML fuente: report/fourier_interactivo/index.html; modelo y escalas: README.md de esa carpeta.')
text(s,'Modelo óptico',.8,2.4,5.6,.5,23,'green',True)
text(s,'Muestra delgada y un LED a la vez.\nPupila circular ideal.\nSin ruido ni aberraciones.\n49 capturas · 30 iteraciones.',.8,3.08,5.6,2.7,21)
text(s,'Optimización y lectura',7,2.4,5.5,.5,23,'green',True)
text(s,'Descenso incremental con pérdida de amplitud.\n\nZheng et al. (2013)\nBian et al. (2015)',7,3.08,5.5,2.7,21)
for t,url,y in [('Zheng · Nature Photonics','https://www.nature.com/articles/nphoton.2013.187',5.5),('Bian · Optics Express','https://doi.org/10.1364/OE.23.004856',5.87)]:
    sh=text(s,t,7,y,5.5,.3,15,'gold');sh.click_action.hyperlink.address=url
takeaway(s,'El HTML V1 complementa la presentación con controles interactivos.')

assert len(R.slides)==18
for si,s in enumerate(R.slides,1):
    for sh in s.shapes:
        assert sh.left>=0 and sh.top>=0 and sh.left+sh.width<=R.slide_width+Inches(.01) and sh.top+sh.height<=R.slide_height+Inches(.01),(si,sh.name,'outside slide')
R.save(ROOT/'fourier_v1_editable.pptx')
print(f'PPTX guardado: {len(R.slides)} diapositivas, {(ROOT/"fourier_v1_editable.pptx").stat().st_size/1024/1024:.2f} MiB')
