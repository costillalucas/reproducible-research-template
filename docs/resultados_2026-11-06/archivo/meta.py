import json, os, sys, glob
I='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas'
out={}
for line in open(sys.argv[1]):
    n,c,f,d,df=line.strip().split('|')
    p=os.path.join(I,c); cj=os.path.join(p,'captura.json')
    m=dict(captura=c, flat=f)
    if os.path.exists(cj):
        j=json.load(open(cj)); m.update(fecha=j.get('fecha'), roi=[j['roi']['offset_x'],j['roi']['offset_y']], exps=j.get('exposiciones_ms'))
    else:
        m.update(fecha=None, roi=None, exps=None)
    m['t_1715']=sorted(os.listdir(os.path.join(p,'fila17_col15_colorr')))
    if f!='SELF' and os.path.exists(os.path.join(I,f,'captura.json')):
        jf=json.load(open(os.path.join(I,f,'captura.json'))); m['roi_flat']=[jf['roi']['offset_x'],jf['roi']['offset_y']]
    out[n]=m
for n in ['2026-11-06-a.1','2026-11-06-a.2','2026-11-06-b','2026-11-06-c','2026-11-06-d','2026-11-06-e','2026-11-06-f']:
    j=json.load(open(os.path.join(I,n,'captura.json')))
    out[n]=dict(captura=n,flat='2026-11-06-sinmuestra',fecha=j.get('fecha'),roi=[j['roi']['offset_x'],j['roi']['offset_y']],exps=j.get('exposiciones_ms'),t_1715=sorted(os.listdir(os.path.join(I,n,'fila17_col15_colorr'))))
json.dump(out,open(sys.argv[2],'w'),indent=1)
for k,v in out.items(): print(k, v.get('fecha'), v.get('roi'), v.get('roi_flat'), v.get('exps'), v['t_1715'])
