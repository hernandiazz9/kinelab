# 31 — El fin del acompañamiento dentro de su repetición, la banda visible, y tres restos

Para correr: `/encargo 31` en una sesión nueva. Puede correr en paralelo con
el 32 (que sólo lee material y escribe en `banco/`). Leé antes
`docs/informes/2026-09-16-auditoria-primer-juicio.md` §1 (`follow_duration_ms`)
y §6 D-4, y los informes del 18 y del 29.

## Contexto

En `cortado3-lento` (rep 1: address 1052, top 1284, impacto 1364) el motor
pone `follow_end` en **1978**, que es la quietud previa al swing siguiente:
`follow_duration_ms` da 2556,7 ms y la auditoría lo declaró falso. Causa
medida: `stable_window_start` (`kinelab/events/primitives.py:154`) busca
desde `after=impact` **sin tope**, exige `follow_still_s` 0,3 s de quietud y
la pausa real del finish dura 50–56 cuadros a 240 fps (0,21–0,23 s), así que
pasa de largo hasta la quietud siguiente. El candidato de segmentación de la
rep 1 termina en **1765** (`candidatos.txt` de la auditoría); la rep 2 va de
2130 a 2970. Decisión del orquestador (D-4): **la cota de la búsqueda es el
fin de su propio candidato de segmentación**; ni el address ni el candidato
siguientes sacan la quietud 1946–2321. No se toca `follow_still_s` ni
`still_speed_max`: es n = 1. Qué es el finish para el entrenador (llegar a
la pose final o soltarla, ≈380 ms de diferencia) lo decide Hernán; hasta
entonces el motor marca el **inicio de la quietud** dentro del candidato y
lo dice en el `method`.

Leer: `sports/golf/events.py` (:47 `ORDER`, :54 `follow_still_s`, :256 la
llamada, :263 el evento), `kinelab/events/primitives.py:154`
(`stable_window_start`, sin `before`), `kinelab/events/segmentation.py` (de
dónde sale `c.end`), `kinelab/analysis.py:175,188` (la ventana de la
repetición), `kinelab/explore.py:164` (`swing_signals(pose, fps)` sin
deporte: el CSV y el overlay salen de la señal a peso igual mientras los
eventos salen de la pesada del 18), `kinelab/events/order.py` (huérfano desde
ADR-018), `kinelab/ingest/gate.py:21-22` (docstring falso desde el 17),
`DECISIONES.md:588` (ADR-019 cita «deriva 8–25 px»), `web/src/components/
TablaEventos.tsx` y `web/src/lib/api.ts` (dónde se muestra cada evento),
`tests/test_fase2.py`, `tests/test_eventos_senal.py`, `tests/data/README.md`.

## Encargo

1. `stable_window_start` gana `before: int | None`; `sports/golf/events.py`
   le pasa el fin del candidato de la repetición (que hoy no llega hasta
   ahí: llevalo por `GolfEventParams` o por la firma del detector, y decilo).
   Si no hay quietud de `follow_still_s` dentro del candidato, `follow_end`
   es `null` con razón («sin quietud de 0,3 s antes del fin de la
   repetición»), nunca el swing siguiente. `method` pasa a decir
   `stable_window_in_rep`.
2. `tol_frames` de cada evento llega a `datos-eventos.json` y a la tabla por
   evento de la pantalla (hoy no se ve: el ±4 del top de `vid1` sólo está en
   `analysis.json`). Una columna o una línea, sin rediseño.
3. `kinelab/explore.py:164`: la señal por cuadro usa el mismo
   `wrist_score_min` del deporte que los eventos, para que el CSV, el
   overlay y los eventos salgan de **una** señal. Los valores del CSV cambian
   donde una muñeca cae bajo el umbral: reportá cuántos cuadros en cada clip.
4. Tres restos: `git rm kinelab/events/order.py` (en el mismo comando que su
   commit); el docstring de `kinelab/ingest/gate.py:21-22` dice la verdad
   (los chequeos de la Fase 1 existen desde el 17 y los escribe
   `perception/run.py`); y bajo ADR-019 en `DECISIONES.md`, una nota fechada:
   la deriva en y es 26–30 px en el impacto de la rep 1 (5,9–6,7 cm, 2,1–2,4×
   el MDC de `lift`), medida por el 29; la conclusión no cambia.
5. Tests: swing sintético con dos repeticiones seguidas donde la primera no
   tiene quietud de 0,3 s antes del fin de su candidato → `follow_end` `null`
   con razón, no el address de la segunda; con quietud dentro → el cuadro
   correcto; el mocap 64_01 (`tests/data/`) no cambia (`follow_end` ya era
   `null`: el trial corta antes); `tol_frames` presente en
   `datos-eventos.json`. Bug inyectado: la cota ignorada → un test en rojo.

NO: no tocar `follow_still_s`, `still_speed_max`, `wrist_score_min`,
`top_band_sigmas` ni ningún umbral; no tocar address, top ni impact; no
tocar `kinelab/metrics/`, `sports/golf/metrics.py`, el schema (no entra ni
sale ningún campo de `analysis.json`), `service/`, `truth/`; no re-correr
percepción sobre la toma de `data/sessions/` (la auditoría lo pidió).

## Cómo se prueba

`.venv/bin/pytest` por exit code y conteo (hoy 381). `cd web && pnpm lint &&
pnpm build`. Corridas reales **desde el `pose.npz` guardado** (invariante 1):
`kinelab analyze` sobre `data/sessions/hernan/2026-09-15/driver/face_on/
take-01` con `--altura-m 1.75`, y `datos` sobre `~/Desktop/cortado.mp4`,
`~/Desktop/20260907_170638.mp4`, `data/incoming/vid1.mp4` y `vid2.mp4`.
Tabla antes/después: `follow_end`, `follow_duration_ms`, `tol_frames` de los
cuatro eventos, y cuántos cuadros del CSV cambiaron por el punto 3. En
`cortado3` la rep 1 tiene que dar `follow_end` ≤ 1765 o `null` con razón, y
la rep 2 lo que dé, dicho. Los demás eventos no se mueven; si alguno se
mueve, explicá por qué con la señal.

## Front

Lo prueba Hernán: la columna o línea de `tol_frames` en la tabla por evento
con `vid1` (top ±4). Dejá el comando y qué mirar.

## En paralelo

El 32 escribe sólo en `banco/` y en `data/incoming/*/` (imágenes), y lee
`kinelab/tools/camera_drift.py` y `kinelab/perception/`. Vos:
`sports/golf/events.py`, `kinelab/events/primitives.py`, `segmentation.py` si
hace falta, `kinelab/analysis.py`, `kinelab/explore.py`,
`kinelab/events/order.py` (baja), `kinelab/ingest/gate.py` (docstring),
`DECISIONES.md`, `web/src/components/TablaEventos.tsx`, `web/src/lib/api.ts`,
`web/src/lib/etiquetas.ts`, `tests/test_fase2.py`, `tests/test_eventos_senal.py`,
`ESTADO.md` (tu sección) y tu informe.
