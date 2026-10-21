#!/usr/bin/env python3
"""leer_offset.py <carpeta_captura> [proyecto.fgprj] -- imprime "OffsetX,OffsetY origen" del ROI de una captura.

Orden: <carpeta>/captura.json (lo escribe el script de captura con el ROI real de la cámara);
si no está, el proyecto de la cámara (Prueba3.fgprj, el ROI configurado ahora, que puede no ser el de esa toma);
si tampoco, el ROI bueno del 21/10 (4000,1942).
"""
import json
import os
import re
import sys

carpeta = sys.argv[1]
proyecto = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/Documents/LucasC/Prueba3.fgprj')
try:
    r = json.load(open(os.path.join(carpeta, 'captura.json')))['roi']
    print(f"{r['offset_x']},{r['offset_y']} captura.json")
    sys.exit()
except (OSError, KeyError, ValueError):
    pass
try:
    t = open(proyecto).read()
    x = re.search(r'"OffsetX":\s*\{[^}]*"value":\s*(\d+)', t).group(1)
    y = re.search(r'"OffsetY":\s*\{[^}]*"value":\s*(\d+)', t).group(1)
    print(f"{x},{y} proyecto_de_la_cámara_(no_hay_captura.json)")
except (OSError, AttributeError):
    print("4000,1942 valor_por_defecto_del_21/10")
