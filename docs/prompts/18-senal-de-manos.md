# 18 — La señal de las manos pesada por confianza, la banda del top, y el MDC del sub-cuadro en el evento

Para correr: `/encargo 18` en una sesión nueva. Leé antes los informes del
15 y del 13 (§2) en `docs/informes/`.

## Contexto

El 15 midió que en `face_on` lo que limita el top no es la regla sino la
señal: el centro de las dos muñecas hereda la muñeca que el modelo pierde en
el top (confianza 0,34–0,35, saltos de hasta 300 px entre cuadros en
`cortado.mp4`, cuadros 32–38), mientras la otra muñeca va suave con
confianza ≥ 0,53. Con la muñeca derecha sola, las dos reglas coinciden en
los cuatro clips reales. Además en `vid1` los tres cambios de sentido están a
3,3 px entre sí con un ruido medido de 2,27 px: la regla decide dentro del
ruido y no lo dice. Y el 13 le midió MDC al instante sub-cuadro del impacto
(2,0–2,9 ms según fps, en `mdc.yaml` §events) que hoy no llega al evento.

Decisiones del orquestador: (a) el centro de manos se pesa por confianza
por cuadro, y una muñeca por debajo de un umbral de confianza no entra
(umbral parametrizado en `GolfEventParams`, procedencia `estimacion`); (b)
cuando la excursión que gana el top supera a otro candidato por menos de
2 σ_px (el ruido del clip que ya estima el motor), el top lleva `tol_frames`
igual a la distancia en cuadros entre esos candidatos, y las duraciones
propagan esa banda (invariante 8); (c) el sub-cuadro del impacto lee su MDC
de `mdc.yaml` y lo escribe en el evento, con procedencia `medido_aqui` para
el MDC y `estimacion` para el valor.

Leer: `kinelab/events/signal.py` (`hands_center`), `kinelab/events/
primitives.py` (`direction_changes`, `direction_change_farthest`,
`subframe_crossing`), `sports/golf/events.py` (los tres eventos, el
sub-cuadro, `GolfEventParams`), `sports/golf/mdc.yaml` §events,
`tests/test_fase2.py` (sólo lectura: tus tests van en archivo nuevo),
`tests/data/README.md` (el `pose.npz` del mocap en las dos vistas),
`tests/helpers/synth_swing.py`, `CONTRATO.md` §events[].

## Encargo

1. `hands_center` pesado por confianza con umbral; si las dos muñecas caen
   bajo el umbral en un cuadro, el punto queda `NaN` y lo rellena el mismo
   relleno acotado de la percepción, nunca una invención. Documentá en el
   docstring por qué (los números del 15).
2. La banda del top (decisión b), en el evento y propagada a
   `backswing_duration_ms` y `downswing_duration_ms`.
3. El MDC del sub-cuadro en `events[].impact.subframe.mdc` (el 16 deja el
   campo en el schema 2.0.0; si el 16 no cerró todavía, escribilo igual y
   validá contra el schema que haya, avisando en el informe).
4. Tests, en `tests/test_eventos_senal.py`: swing sintético con una muñeca
   ruidosa y de baja confianza en el top → el top no se mueve respecto del
   limpio; con las dos limpias → igual que antes; el mocap (scores 1,0) no
   cambia en ninguna vista; un caso con dos candidatos a menos de 2 σ →
   `tol_frames` igual a su distancia; el MDC del sub-cuadro aparece con su
   unidad. Bugs inyectados: pesar por 1 − confianza, y umbral en 0.

NO: no tocar la regla de ADR-017 ni los umbrales de address e impacto; no
tocar `kinelab/analysis.py`, el schema, `explore.py`, `service/`, `web/`,
`tests/test_fase2.py` (16). Si algo de eso hace falta, va en el informe.

## Cómo se prueba

`.venv/bin/pytest -q` en verde. Corridas reales desde el `pose.npz`
guardado (invariante 1) y de punta a punta con `datos`: los cuatro clips
del S22 (`cortado`, el original del 7/9, `vid1`, `vid2`) y el mocap 64_01 en
las dos vistas: address, top, impacto, `tol_frames` del top y duraciones
antes y después, en una tabla; y contra la muñeca derecha sola como
referencia, como hizo el 15.

## En paralelo

El 16 toca el contrato, `kinelab/analysis.py`, `kinelab/metrics/`,
`sports/golf/metrics.py`, `config.py`, `explore.py`, `web/`,
`tests/test_fase2.py`, `data/examples/`. Vos: `kinelab/events/`,
`sports/golf/events.py`, `tests/test_eventos_senal.py`, `tests/data/`.
