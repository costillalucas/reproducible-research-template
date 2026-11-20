# Pendiente al volver del reinicio (anotado 20/11 ~17:45)

1. Verificar que terminaron los 4 B20 que faltaban (P08, P10, P12, P15): `ls B20/*/resumen.txt | wc -l` debe dar 15
   y `comparar.log` debe tener la tabla con las 15. Si no: `./codigo/continuar.sh` (~4 min).
2. **Correr 40x40 (pedido de Lucas)** para las mismas 15 partículas (~15 min):
       cd ~/Documents/AleYLu/reconstrucciones/2026-11-20/aislar_vs_recortar
       ./codigo/correr_B.sh 40 3
       python3 codigo/comparar2.py .
   (comparar2.py agrega B40 solo si existe la carpeta B40/.)
3. Comparar B20 vs B40 vs A: ¿el fondo (0.24x en B20) se recupera a 40 px? ¿sube la correlación ρ_c hacia el control A–A' (0.87–0.97)?

## HECHO 20/11 18:46 (después del reinicio)
- B20 15/15 OK. B40 15/15 (código 0), comparar2.py → comparar_B40.log, tabla.csv, resultados.json, fig_grilla_B40.png.
- Medianas (N=15) B40 vs B20 [control A–A' N=2]: fondo 1.00 vs 0.24; |S| 0.98 vs 5.9; err_rel .051 vs .77 [.043];
  ρ_c .76 vs .49 [.92]; ρ_c_hp .68 vs .66 [.91]; Pearson amp .71 vs .02 [.83]; fase .77 vs .38; desplaz .06 vs .13 µm; C1_B .57 vs .57.
- Lectura: 40 px recupera fondo/bajas frecuencias; correlación pasa-altos NO mejora (.66→.68, lejos de .91). Sin interpretar con Lucas aún.
- Gotcha: watcher `pgrep -f "correr_B.sh 40"` se encontró a sí mismo (colgado); comparar corrido a mano.
