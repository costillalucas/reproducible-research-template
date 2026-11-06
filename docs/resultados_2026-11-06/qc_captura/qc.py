import glob,os,numpy as np,tifffile,json
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/'
for z in ['a.1','a.2','b','c','d','e','f','sinmuestra']:
    d=B+'2026-11-06-'+z
    c=json.load(open(d+'/captura.json'))
    print('==',z,c['fecha'],c['roi']['offset_x'],c['roi']['offset_y'],c['exposiciones_ms'])
    for led in sorted(glob.glob(d+'/fila*')):
        for t in sorted(os.listdir(led)):
            fs=sorted(glob.glob(f'{led}/{t}/*.tiff'))
            im=tifffile.imread(fs[0]).astype(float)
            print(f'  {os.path.basename(led)[:11]} {t:>8} n={len(fs)} mean={im.mean():7.1f} p99.9={np.percentile(im,99.9):6.0f} sat%={100*(im>=4095).mean():.3f}')
    dd=d+'-dark'
    for t in sorted(os.listdir(dd+'/fila17_col15_colorr')):
        fs=sorted(glob.glob(f'{dd}/fila17_col15_colorr/{t}/*.tiff'))
        print('  dark',t,len(fs),round(tifffile.imread(fs[0]).mean(),1))
