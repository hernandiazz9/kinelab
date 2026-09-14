# Plan

Última ronda: 2026-09-14 — Hernán no tiene el iPhone 17 Pro y pide subir
cualquier video, ver qué es y analizarlo con avisos. Decisión: caminos
declarados sin calibrar (ADR-016), encargo 06 después del 04; la pantalla
con ficha del archivo y selector es el 07. YouTube como material: no
(cementerio 1); GolfDB sigue siendo la única fuente externa, sólo para medir.

## Decisiones del orquestador

- 2026-09-14 · Un solo delta de PTS de arranque no es tasa variable. El gate
  y el motor usan `vfr_ratio` y `fps_playback` efectivos; los brutos quedan
  en `capture.json` (`*_raw`, `first_delta_s`, `fps_note`) y el chequeo dice
  cuándo difieren. Evidencia: informe del 03. Se aplica en el 04.

- 2026-09-14 · Caminos de captura declarados sin calibrar (ADR-016, lo
  escribe el 06): dispositivo y modo declarados, `fps_real` asumido igual al
  de reproducción con procedencia `sin_verificar`, nunca juicio, `slomo` sin
  cronómetro se rechaza. Sustituye en parte a ADR-003: Android entra como
  camino declarado; calibrado sólo con cronómetro. Evidencia: informe del 03
  (modo Video del S22 es CFR tras el delta de arranque).
- 2026-09-14 · Videos de YouTube u otras plataformas no son material: llegan
  recomprimidos, sin procedencia y sin poder calibrarse (cementerio 1 y 2 de
  `HERENCIA.md`). Excepción: GolfDB, con licencia para medir (encargo 09).

## Backlog, en orden

- [hecho] 02 impacto-subcuadro — `5ec9c2e`, `4350e08`. Sólo `face_on`; sin
  MDC; no distingue cuadro interpolado de medido.
- [hecho] 03 fps-truth-primer-delta — `f1a102e`, `db22fae`.
- [en curso] 04 gate-fps-efectivo — el gate, `capture.json` (1.1.0) y las
  dos líneas de `explore.py` pasan al fps efectivo; `CAPTURA.md` lo documenta.
- [en curso] 05 lamina-interpolada — `kinelab/tools/interpolar.py`: cuadros
  `minterpolate` rotulados, archivo aparte, lámina PNG con la marca 44,44
  para que Hernán mire. Paso 3 del pedido.
- [pendiente] 06 camino-declarado — ADR-016 en el motor y el contrato:
  `capture-paths.yaml` con `calibrated: false`, gate que avisa, procedencia
  `sin_verificar` en cada número, sin juicio; `datos --camino`. Después del
  04. Prompt escrito.
- [pendiente] 07 pantalla-ficha-y-selector — antes de analizar, la ficha del
  archivo (`PUT /api/fps-truth`: codec, tamaño, cuadros, fps efectivo, VFR,
  primer delta) y el selector de dispositivo y modo desde `capture-paths.yaml`
  (más "no sé"); en el resultado, el aviso del camino declarado y la lista de
  métricas que no se calculan a ese fps con su razón. Después del 06.
- [pendiente] 08 arnes-ganancia-y-subcuadro — en `truth/`: ganancia de
  velocidad angular pelvis→tórax→brazo con ratios conocidos desde las dos
  vistas (vive con MDC y vistas, o muere), y sesgo/MDC del instante
  sub-cuadro del impacto con el swing paramétrico (sería el primer evento con
  número medido). Fase 3.2/3.3 sin cerrar.
- [pendiente] 09 visor-desde-datos — esqueleto desde `pose.npz` sobre el
  video en el reproductor de exploración (ADR-014, invariante 10) con
  `master.mp4` H.264 CFR (4.2) como referencia de cuadros. Cierra la
  desviación de la cuarta sesión.
- [pendiente] 10 cola-con-cancelacion — trabajos cancelables, limpieza de
  `data/exploracion/` (~20 MB por clip), fotos por evento como JPEG (4.1).
- [bloqueado por Hernán] cronómetro y sesión con el S22 — ver Preguntas.
  Con eso: calibrar los caminos del S22 en `capture-paths.yaml` (0.7), ADR
  que cierre lo de Android con números, umbral de encuadre medido (1.3),
  intrínsecos con tablero (3.1), re-correr el arnés, pasar los clips por
  percepción y análisis.
- [pendiente] 11 golfdb-error-de-eventos — bajar el dataset (CC BY-NC, sólo
  para medir) y correr `kinelab.tools.golfdb_eval` (2.5). Después de decidir
  con Hernán si vale bajar 1400 videos ahora.
- [pendiente] Fase 5: repetibilidad primero, comparación de dos repeticiones
  (`compare.py` de la herencia). No antes de clips reales por el gate.

## Preguntas para Hernán

- ¿Qué viste de la pantalla del 02? La lista está al final de
  `docs/informes/2026-09-14-02-impacto-subcuadro.md` (el texto del impacto, el
  botón de los dos cuadros, y si aparece el aviso ámbar del seek).
- Filmar el cronómetro con el S22 Ultra (no hace falta el iPhone): un
  cronómetro con milésimas en pantalla, 10 s en Video FHD 60 y 10 s en Slow
  motion FHD 240, `Auto FPS` apagado, archivo crudo por cable desde
  `DCIM/Camera` (y aparte el mismo clip compartido desde Galería, para medir
  qué hace ese camino). Con eso se calibran los caminos del S22 y se sabe si
  el 240 sirve: ahí salen todas las métricas. Anotar cuánto mide el primer
  delta en cada modo. Detalle en `ESTADO.md` §"Lo que le toca filmar a Hernán".
- ¿Tenés o podés conseguir una GoPro? Es un camino de 240 fps real; entra con
  cronómetro y calibración de lente con tablero (3.1, ya en el plan).
- GolfDB son 1400 videos de YouTube (CC BY-NC, sólo para medir): ¿bajarlos
  ahora o después del material propio?

## Aparcado

- Instante sub-cuadro del top: no pedido. La primitiva de cruce no le sirve
  (el top es un cambio de dirección: habría que cruzar la velocidad
  proyectada por cero). Sólo si Hernán lo pide.
- Lámina interpolada en el front: no hasta que Hernán diga, mirando el PNG,
  que la interpolación sirve.
- Pádel: sólo cuando golf tenga MDC medidos (invariante 17).
- SynthPose como segundo estimador (1.5): necesita torch, sólo en `truth/`;
  después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra cuando la ingesta
  (4.3) exista en `web/`.
