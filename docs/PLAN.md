# Plan

Última ronda: 2026-09-14 — leídos los informes del 02 (impacto sub-cuadro:
44,44 ± 0,11; 193 tests) y del 03 (`fps_truth` con fps efectivo; original
del S22 29,436 → 29,998). Los dos dejaron abiertas la línea de `explore.py` y
la decisión del gate: van juntas al 04. El paso 3 de Hernán va al 05.

## Decisiones del orquestador

- 2026-09-14 · Un solo delta de PTS de arranque no es tasa variable. El gate
  y el motor usan `vfr_ratio` y `fps_playback` efectivos; los brutos quedan
  en `capture.json` (`*_raw`, `first_delta_s`, `fps_note`) y el chequeo dice
  cuándo difieren. Evidencia: informe del 03. Se aplica en el 04.

## Backlog, en orden

- [hecho] 02 impacto-subcuadro — `5ec9c2e`, `4350e08`. Sólo `face_on`; sin
  MDC; no distingue cuadro interpolado de medido.
- [hecho] 03 fps-truth-primer-delta — `f1a102e`, `db22fae`.
- [en curso] 04 gate-fps-efectivo — el gate, `capture.json` (1.1.0) y las
  dos líneas de `explore.py` pasan al fps efectivo; `CAPTURA.md` lo documenta.
- [en curso] 05 lamina-interpolada — `kinelab/tools/interpolar.py`: cuadros
  `minterpolate` rotulados, archivo aparte, lámina PNG con la marca 44,44
  para que Hernán mire. Paso 3 del pedido.
- [pendiente] 06 arnes-ganancia-y-subcuadro — en `truth/`: ganancia de
  velocidad angular pelvis→tórax→brazo con ratios conocidos desde las dos
  vistas (vive con MDC y vistas, o muere), y sesgo/MDC del instante
  sub-cuadro del impacto con el swing paramétrico (sería el primer evento con
  número medido). Fase 3.2/3.3 sin cerrar.
- [pendiente] 07 visor-desde-datos — esqueleto desde `pose.npz` sobre el
  video en el reproductor de exploración (ADR-014, invariante 10) con
  `master.mp4` H.264 CFR (4.2) como referencia de cuadros. Cierra la
  desviación de la cuarta sesión.
- [pendiente] 08 cola-con-cancelacion — trabajos cancelables, limpieza de
  `data/exploracion/` (~20 MB por clip), fotos por evento como JPEG (4.1).
- [bloqueado por Hernán] material real — ver Preguntas. Con él: calibrar
  `capture-paths.yaml` (0.7) anotando el primer delta de cada modo, umbral de
  encuadre medido (1.3), intrínsecos con tablero (3.1), re-correr el arnés,
  pasar los clips por percepción y análisis.
- [pendiente] 09 golfdb-error-de-eventos — bajar el dataset (CC BY-NC, sólo
  para medir) y correr `kinelab.tools.golfdb_eval` (2.5). Después de decidir
  con Hernán si vale bajar 1400 videos ahora.
- [pendiente] Fase 5: repetibilidad primero, comparación de dos repeticiones
  (`compare.py` de la herencia). No antes de clips reales por el gate.

## Preguntas para Hernán

- ¿Qué viste de la pantalla del 02? La lista está al final de
  `docs/informes/2026-09-14-02-impacto-subcuadro.md` (el texto del impacto, el
  botón de los dos cuadros, y si aparece el aviso ámbar del seek).
- ¿Qué teléfono va a ser el de captura? `CAPTURA.md` y ADR-003 están escritos
  para iPhone 17 Pro; el único material real es del Galaxy S22 Ultra, que
  ADR-003 deja fuera. Si es el S22: cronómetro de 10 s en cada modo con más
  de 30 fps (FHD 60, Slow motion 240, ¿FHD 120?), por cable y por Galería, y
  con esos números un ADR nuevo que cite al 003. Al filmar, anotar cuánto
  mide el primer delta en cada modo (el 03 lo midió en uno solo: 0,2015 s).
  Detalle en `ESTADO.md` §"Lo que le toca filmar a Hernán".
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
