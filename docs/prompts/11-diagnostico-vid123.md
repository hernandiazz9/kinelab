# 11 — Diagnóstico de tres clips nuevos: qué son, qué tasa tienen, qué dice el gate

Para correr: `/encargo 11` en una sesión nueva. Leé antes los informes del
03, 04 y 06 en `docs/informes/` y `docs/filmacion-s22.md` (la guía que
recibió quien filmó).

## Contexto

Hernán dejó tres clips en `~/Downloads/vid1.mp4`, `vid2.mp4` y `vid3.mp4`,
filmados el 14 de septiembre con el Galaxy S22 Ultra en modo **Video, UHD
(3840×2160) a 60 fps, lente 1×** según la captura de pantalla de la cámara
que mandó Hernán. No se sabe cómo llegaron a la Mac (cable, Quick Share,
Drive…): preguntáselo, y buscá en los metadatos si conservan el `udta` de
Samsung (el original del 7/9 lo tenía intacto, 557.940 bytes) o si algo los
recomprimió. Tampoco se sabe si alguno es el cronómetro que pide la guía.
Este encargo es de **diagnóstico y medición, no de código**: decir qué son,
a qué tasa capturaron de verdad, si alguno permite calibrar un camino de
captura, y qué dice el gate de cada uno. Regla de la casa: el archivo miente
sobre su fps; el metadato de Samsung (`com.android.capture.fps`) es una
pista con procedencia `fabricante`, nunca la verdad. La verdad es contar
cuadros contra una duración real leída en un cronómetro filmado.

Leer: `kinelab/tools/fps_truth.py` (qué reporta), `kinelab/ingest/__main__.py`
y `gate.py` (cómo se ingesta con `--camino` y `--data`),
`data/capture-paths.yaml` (los tres caminos declarados del S22),
`kinelab/explore.py` (sólo la firma y las salidas de `datos`), `CAPTURA.md`
§cronómetro y §gate, `CONTRATO.md` §capture-paths.yaml.

## Qué existe ya

- `.venv/bin/python -m kinelab.tools.fps_truth CLIP [--duracion-real S]`:
  cuadros decodificados, fps de reproducción bruto y efectivo, ratio VFR
  bruto y sin el primer delta, codec, veredicto, `stretch_factor` si le das
  la duración real.
- `ffprobe -show_format -show_streams -show_entries format_tags` para los
  metadatos del fabricante (en el original del S22 del 7/9: `com.android.
  capture.fps: 30`, `com.android.version: 16`).
- `.venv/bin/python -m kinelab.ingest CLIP --atleta hernan --gesto driver
  --vista face_on --camino ID --data DIR`: el gate completo, con
  `capture.json`.
- `.venv/bin/python -m kinelab datos CLIP --altura-m 1.75 --camino ID`:
  pose, eventos, overlay, CSV, JSON, sin gate. Deja `<clip>.kinelab/`.
- Podés mirar cuadros sueltos: `ffmpeg -ss T -i CLIP -frames:v 1 cuadro.png`
  y abrirlos con `Read`. Eso no es el front; está permitido.

## Encargo

1. Copiá los tres a `data/incoming/` (está en `.gitignore`), sin tocar los
   originales, y anotá el sha256 de cada uno.
2. **Ficha de cada uno**, en una tabla: tamaño, duración del contenedor,
   resolución y rotación, codec y perfil, `com.android.capture.fps` y el
   resto de las etiquetas de Samsung (modelo, versión), cuadros decodificados,
   fps de reproducción bruto y efectivo, ratio VFR bruto y sin el primer
   delta, primer delta. Y tu lectura: qué teléfono y qué modo parece
   (Video FHD 30/60, Slow motion 240, otro), y por qué.
3. **Qué hay adentro.** Extraé tres o cuatro cuadros de cada uno (principio,
   medio, fin) y decí qué es: un cronómetro, swings (cuántos, qué vista,
   cuánto ocupa el cuerpo en el alto del cuadro), otra cosa.
4. **Si alguno es un cronómetro**: leé la hora en el primer y en el último
   cuadro nítidos, y también en tres o cuatro puntos intermedios. Con eso:
   duración real, `fps_real` (cuadros entre las dos lecturas / segundos
   leídos), `stretch_factor`, y si la velocidad es **uniforme** en todo el
   clip o cambia por tramos (el slow motion de Samsung mezcla tramos a
   velocidad normal y lenta: lo delata la tasa a la que avanzan los dígitos
   entre cuadros consecutivos). Si es uniforme y el clip vino por cable,
   escribí el camino **calibrado** en `data/capture-paths.yaml` (id con
   dispositivo, modo y transferencia; `fps_method` con las dos lecturas y
   el conteo; `calibrated_on` 2026-09-14; `calibrated_by: hernan, lectura
   de la sesión 11`) y validalo con los tests. Si no es uniforme, **no** lo
   escribas: anotá los tramos con sus tasas y parás ahí; es una decisión.
5. **El gate, para cada clip de swings**: ingestá con el camino que
   corresponda (el calibrado si lo hay; si no, el declarado del S22 que
   coincida; si no, `desconocido-video`) en un `--data` del scratchpad.
   Reportá el veredicto y los nueve chequeos con su valor. No hay camino
   declarado para UHD 60: agregá `s22ultra-video-uhd60-cable` (o el
   transporte que Hernán diga) como declarado en `capture-paths.yaml`,
   con `nominal_fps` 60 y el codec que midas, y validalo con los tests.
   Esperá `reject` por `fps_min_for_gesture` (60 < 100): es lo correcto y
   hay que decirlo así.
6. **Exploración de cada clip de swings**: `datos` con ese mismo camino y
   altura 1,75 (si el sujeto no es Hernán, preguntá la altura o dejalo sin
   cm y decilo). Reportá eventos (address, top, impacto en cuadros y
   segundos; sub-cuadro del impacto), duraciones, tasa de detección, altura
   del cuerpo en px y en fracción del alto, y qué métricas del registro
   salen con valor y cuáles en `null` con su razón. Si un clip tiene varios
   swings, decí qué hizo `datos` con eso y qué daría `analyze` sobre el
   take ingestado si el gate lo dejó pasar.
7. Medí lo que cuesta UHD: tiempo de `datos` por clip y por cuadro contra
   el original FHD del 7/9 (ese tardó 11,5 s por 265 cuadros), y si el
   recorte del cuerpo que entra al modelo supera los 256 px de alto en FHD
   ya (si sí, UHD no agrega precisión, sólo peso; si no, decilo).
8. Cerrá con **tres líneas**: qué son los tres clips, cuál es el mejor y por
   qué, y qué le falta al material para pasar el gate (o que ya pasa).

NO: no toques código del motor ni de `service/` ni `web/` (si encontrás un
bug, va en el informe con el comando que lo reproduce); no infieras el
`stretch_factor` de los metadatos; no escribas un camino calibrado sin
cronómetro leído; no borres nada de `~/Downloads`.

## Cómo se prueba

Este encargo **es** la prueba. Todo número del informe con su comando al
lado. `.venv/bin/pytest -q tests/test_capture_paths.py` en verde si tocaste
el YAML. Copiá en el informe los `capture.json` de los que pasen el gate
(recortados a lo que importa) y las rutas de los `<clip>.kinelab/`.

## En paralelo

Corren el 07 (`truth/`, `data/examples/`, `kinelab/explore.py`), el 09
(`service/`, `web/`) y el 10 (`kinelab/metrics/registry.py`). Vos tocás
sólo `data/capture-paths.yaml`, `ESTADO.md` y tu informe. Commit con rutas
explícitas.
