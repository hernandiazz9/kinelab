# 03 — `fps_truth`: el primer delta de PTS no es tasa variable

Para correr: `/encargo 03` en una sesión nueva.

## Contexto

Medido en la quinta sesión (`ESTADO.md`, sección de arriba, "Falsa alarma de
VFR en Android"): el original del Galaxy S22 Ultra
(`~/Desktop/20260907_170638.mp4`, 265 cuadros) tiene 263 deltas de PTS de
0,0333 s y UNO de 0,2015 s, el primero (arranque de la cámara). `fps_truth` lo
declara `VFR` (ratio 6,04) y calcula `fps_playback = 29,436` con `(n−1)/span`;
`explore` usa ese número y todos los `t_s` y duraciones del original quedan
1,9 % largos. Un cronómetro filmado con este teléfono va a tener el mismo
primer delta, así que esto afecta a la calibración de `capture-paths.yaml`
cuando llegue.

Leer: `kinelab/tools/fps_truth.py`, `tests/test_fps_truth.py`, y de
`CAPTURA.md` las secciones del cronómetro y del gate (`vfr_ratio_le_1_10`,
`fps_matches_path`).

## Qué existe ya

- `.venv/bin/python -m kinelab.tools.fps_truth CLIP [--duracion-real S]
  [--nominal N]`: cuadros decodificados, tasa efectiva, `delta_max/delta_min`,
  codec y veredicto. Tests con tres clips sintéticos generados con ffmpeg en
  el propio test (240 real, 240 estirado con `setpts`, 30 remuestreado con
  `-r`).
- El gate (`kinelab/ingest/gate.py`) consume `vfr_ratio` y `fps_playback`.
  **No se toca** en este encargo.

## Encargo

1. `fps_truth` reporta, además del ratio bruto, el ratio **excluyendo el
   primer delta** y el fps de reproducción calculado sin él (o desde la
   mediana de deltas: elegí y justificá en dos líneas del informe), y lo dice
   en una nota legible: "el primer delta es 0,2015 s (arranque de la cámara);
   sin él, ratio 1,00". Los campos brutos se conservan con su significado:
   nadie pierde información.
2. Cuál de los dos números usa `capture.json` / el gate es una decisión de
   `CAPTURA.md`, no de este encargo: proponela en el informe con los números
   de los dos clips, sin cambiar el gate. Si `explore` toma solo el fps
   corregido por leer la salida de `fps_truth`, decilo; si necesitaría un
   cambio en `explore.py`, no lo hagas (lo toca el encargo 02) y anotalo.
3. Test nuevo: un clip sintético con el primer delta largo y el resto CFR
   tiene que dar fps de reproducción exacto (30,00, no 29,4) y la nota; el
   clip realmente VFR de los tests existentes tiene que seguir dando `VFR`.

NO: no tocar el gate, `explore.py` ni `CAPTURA.md`. No cambiar el
significado de los campos existentes.

## Cómo se prueba

- `.venv/bin/pytest -q` en verde con el test nuevo.
- `.venv/bin/python -m kinelab.tools.fps_truth ~/Desktop/20260907_170638.mp4`
  y lo mismo con `~/Desktop/cortado.mp4`: en el informe, para cada uno, ratio
  bruto, ratio sin el primer delta, fps de reproducción antes y después.

## En paralelo

El encargo 02 (impacto sub-cuadro) toca `sports/golf/events.py`,
`kinelab/explore.py`, `tests/test_fase2.py`, `tests/helpers/synth_swing.py`,
`service/` y `web/`. No toques nada de eso.
