#!/usr/bin/env python3
"""grilla.py -- tamaño de la grilla de LEDs de una captura.

El tamaño se elige con UN número, N_LADO, en el script de captura (iluminacion_con_toma_de_imagene.py).
Ese script lo guarda en <carpeta>/captura.json ('n_lado', 'modo_prueba' True/False y 't_max_ms'), y de ahí lo leen
precaptura.py, reconstruir.py y chequeo.sh. Capturas anteriores al 13/11 no tienen 'n_lado': se asume 15.

Uso desde bash:  python3 grilla.py <carpeta>   ->  imprime "N_LADO MODO_PRUEBA"  (MODO_PRUEBA = 1, 0 o ?)
"""
import json
import os
import sys

N_DEFECTO = 15        # capturas viejas, sin 'n_lado' en captura.json
T_MAX_DEFECTO = 1025.0  # ms; capturas viejas, sin 't_max_ms' (tope del script de captura desde el 22/10)
Z_DEFECTO = 102.0       # mm; capturas viejas, sin 'z_mm' (valor que usaba el solver hasta el 17/11; la matriz estaba a ~99.5-102)


def info(carpeta):
    """(n_lado, modo_prueba) de la captura; modo_prueba es None si captura.json no lo dice."""
    try:
        with open(os.path.join(carpeta, 'captura.json')) as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    return int(d.get('n_lado', N_DEFECTO)), d.get('modo_prueba')


def t_max(carpeta):
    """Exposición máxima [ms] que acepta el script de captura (T_MAX_MS), según captura.json; 1025 si falta."""
    try:
        with open(os.path.join(carpeta, 'captura.json')) as f:
            return float(json.load(f).get('t_max_ms', T_MAX_DEFECTO))
    except (OSError, ValueError):
        return T_MAX_DEFECTO


def z_mm(carpeta):
    """Distancia matriz de LEDs - muestra [mm] de la captura ('z_mm' en captura.json; 102 si falta, tomas anteriores al 17/11)."""
    try:
        with open(os.path.join(carpeta, 'captura.json')) as f:
            return float(json.load(f).get('z_mm', Z_DEFECTO))
    except (OSError, ValueError):
        return Z_DEFECTO


def lado(carpeta):
    return info(carpeta)[0]


def leds(eje, n):
    """LEDs (fila, col) de la grilla n x n centrada en el eje (n impar)."""
    h = n // 2
    return [(r, c) for r in range(eje[0] - h, eje[0] + h + 1) for c in range(eje[1] - h, eje[1] + h + 1)]


if __name__ == '__main__':
    n, p = info(sys.argv[1])
    print(n, {True: 1, False: 0}.get(p, '?'))
