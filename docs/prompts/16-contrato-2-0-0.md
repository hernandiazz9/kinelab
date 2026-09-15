# 16 — Contrato 2.0.0: muere la ganancia y el orden de la secuencia, y entran las versiones y la escala que faltaban

Para correr: `/encargo 16` en una sesión nueva. Leé antes los informes del
13, 14 y 15 en `docs/informes/`.

## Contexto

El arnés (13) midió que `summary.gain` no es la ganancia de velocidad
angular: desde `down_the_line` la línea de caderas se proyecta a 3,6 px y su
giro aparente da 11110 °/s contra 139,6 verdaderos (80×); desde `face_on` la
línea de hombros salta 7,7× para un cambio verdadero de 2×. Muere en las dos
vistas. `sequence_order` sale de la misma función y del mismo artefacto, y
`CONTEXTO.md` ya lo dejaba fuera de alcance. Los dos son **requeridos** por el
schema: sacarlos es un bump **major**. Y el 14 dejó tres cosas del contrato
sin escribir porque los archivos eran de otro: `metric_version` no viaja al
`analysis.json`, la escala en px que multiplica a ocho métricas no queda
registrada, y los bumps de versión de `sports/golf/metrics.py`.

Decisión del orquestador: **ADR-018**, la ganancia y el orden mueren con la
evidencia del 13; `analysis.json` pasa a **2.0.0**. Con el schema abierto,
entran también lo del 14 y lo que el 13 dejó listo. No hay `analysis.json`
viejos fuera de lo que se regenera.

Leer: el informe del 13 (la tabla de archivos que tocan la ganancia, con
líneas), `kinelab/metrics/generic.py`, `kinelab/analysis.py`,
`kinelab/sport.py`, `kinelab/metrics/registry.py`, `kinelab/metrics/core.py`
(`scale_px`), `sports/golf/metrics.py`, `sports/golf/config.py`,
`kinelab/contract/schema.json`, `validate.py`, `write.py`,
`kinelab/explore.py` (columnas `*_line_rate_deg_s` y sus picos),
`web/src/lib/etiquetas.ts`, `web/src/components/TablaEventos.tsx`,
`tests/test_fase2.py`, `data/examples/analysis.example.json`,
`CONTRATO.md` §summary, §events[], §sextuplo, §La escala, §Versionado;
`DECISIONES.md` ADR-002, ADR-008, ADR-017.

## Encargo

1. **ADR-018** en `DECISIONES.md`: la ganancia y `sequence_order` mueren,
   con los números del 13 y la referencia a `CONTEXTO.md` §Fuera de alcance.
   Debajo de ADR-008, una nota fechada: el código detecta el top por cambio
   de sentido de la velocidad proyectada (definición de GolfDB), no por
   inflexión de la segunda derivada; ADR-017 eligió cuál. Debajo de ADR-002,
   una nota: el 80–90 % citado ya no es el número de `CAPTURA.md` (07, 11);
   la decisión no cambia.
2. **Borrar** la ganancia y el orden: `generic.py` (`line_angle_rate`,
   `gain`), `analysis.py`, `sport.py` (`gain_segments`), `sports/golf/`
   (`GAIN_SEGMENTS`), el schema (`summary.gain`, `events[].sequence_order`),
   las columnas `hip_line_rate_deg_s`, `shoulder_line_rate_deg_s`,
   `arm_left_rate_deg_s` y sus picos del CSV de exploración, y las etiquetas
   y filas del front que las mostraban como «rotación aparente». Nada queda
   "por si acaso".
3. **Schema 2.0.0**: además, `metric_version` en cada sextuplo (obligatorio),
   `quality.scale_px` con `{value, frame, method}` (la escala del 14, con el
   cuadro del máximo), y `events[].<evento>.subframe.mdc` opcional con su
   unidad (lo llena el 18; acá sólo el lugar y el validador). `CONTRATO.md`
   al día en cada sección tocada y §Versionado con el 2.0.0 justificado.
4. Los bumps del 14 en `sports/golf/metrics.py`: `metric_version` 1.1.0 en
   las ocho métricas en cm (`_m()` recibe el parámetro), `registry_version`
   0.2.0, y la `definition` de `pelvis_sway_top_cm` con el texto del informe
   del 14. `data/examples/analysis.example.json` regenerado desde el swing
   sintético (con `method: direction_change_farthest` en los top).
5. **Un aviso que dice algo falso, encontrado por el encargo 24.** Con un
   camino **calibrado**, `analysis.json` sale con
   `warnings[1] = "camino declarado sin cronómetro: los tiempos asumen que el
   archivo reproduce a la velocidad de captura (…, 240.15 fps asumidos)"`. El
   camino está calibrado y esa tasa está **medida**, no asumida:
   `kinelab/analysis.py:195` usa la nota de «declarado» para todo lo que no
   sea `medido_aqui`. Lo correcto es distinguir los dos casos: con camino
   calibrado y sin gate, el aviso tiene que decir que la **procedencia no se
   verificó porque el gate no corrió**, que es lo que ADR-016 dice de verdad.
   Con su test.
6. Tests: el validador rechaza un `analysis.json` con `summary.gain` o con
   `sequence_order`, y uno sin `metric_version` o sin `quality.scale_px`;
   `test_fase2.py` deja de esperar la clave; un `datos` real sobre
   `~/Desktop/cortado.mp4` y `data/incoming/vid1.mp4` sale con 2.0.0,
   sin las columnas, y con los mismos siete valores en cm que reportó el 14.

NO: no tocar `kinelab/events/`, `sports/golf/events.py`,
`kinelab/ingest/gate.py` ni `CAPTURA.md` (17 y 18). `cd web && pnpm lint &&
pnpm build` limpios; el front no se abre.

## Cómo se prueba

`.venv/bin/pytest -q` y `cd truth && .venv/bin/pytest -q` en verde (el arnés
importa el registro: si el `registry_version` o las filas cambian, sus
tests lo dicen). Las dos corridas reales con el JSON antes y después
(sólo las claves que cambian). Para Hernán: la tabla por evento ya no
muestra «rotación aparente de caderas/hombros».

## En paralelo

El 18 toca `kinelab/events/signal.py`, `sports/golf/events.py`,
`tests/test_eventos_senal.py` (nuevo) y `tests/data/`. El 17 espera a que
vos cierres. Vos: todo lo listado arriba y ningún archivo del 18.
