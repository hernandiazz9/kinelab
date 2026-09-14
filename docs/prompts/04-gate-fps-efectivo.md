# 04 — El gate y `explore` usan el fps efectivo, no el bruto

Para correr: `/encargo 04` en una sesión nueva.

## Contexto

El encargo 03 (`docs/informes/2026-09-14-03-fps-truth-primer-delta.md`) dejó
`fps_truth` reportando, junto a los brutos, `vfr_ratio_effective` y
`fps_playback_effective`: el corregido se usa sólo si el primer delta de PTS
es el único fuera de lugar (arranque de la cámara). Medido sobre el original
del S22 (`~/Desktop/20260907_170638.mp4`): ratio bruto 6,044 → efectivo
1,000; fps 29,436 → 29,998. Quedaron dos consumidores con el bruto: el gate
(`vfr_ratio_le_1_10` rechazaría cualquier clip de esa cámara, y
`fps_matches_path` contra 30,000 pasa por 1,88 % con tolerancia del 2 %) y
`explore.py` (`t_s` y duraciones 1,9 % largos en ese clip). Los encargos 02 y
03 lo anotaron los dos y no lo hizo ninguno, por el reparto de archivos.

Decisión del orquestador (anotada en `docs/PLAN.md`): un solo delta de
arranque no es tasa variable. El gate y el motor trabajan con los valores
efectivos; los brutos quedan visibles en `capture.json` y el chequeo dice
cuándo difieren. Nunca en silencio.

Leer: `kinelab/tools/fps_truth.py` (los campos nuevos y su criterio),
`kinelab/ingest/gate.py`, `kinelab/ingest/session.py` y `__main__.py` (quién
escribe `capture.json`), `tests/test_gate.py`, `tests/conftest.py` (fixture
`first_delta30_h264` y el clip realmente VFR), `kinelab/explore.py`
alrededor de las líneas 55–65 (`prepare_take`), `CAPTURA.md` §gate y §"Por
qué el archivo no puede decir su propio fps", `CONTRATO.md` §capture.json.

## Qué existe ya

- `Counted` de `fps_truth`: `vfr_ratio` y `fps_playback` (brutos),
  `delta_first_s`, `vfr_ratio_excl_first`, `fps_playback_excl_first`, y las
  propiedades `first_delta_is_the_only_outlier`, `vfr_ratio_effective`,
  `fps_playback_effective`. Todo viaja en `to_dict()`.
- Fixture `first_delta30_h264` (120 cuadros a 30 fps, primer delta de 0,2 s)
  y el clip realmente VFR de los tests. 193 tests en verde.

## Encargo

1. `capture.json`: `fps_playback` y `vfr_ratio` pasan a ser los **efectivos**
   (son los que usan el gate, `stretch_factor` y `duration_playback_s`). Los
   brutos van a campos nuevos `fps_playback_raw`, `vfr_ratio_raw` y
   `first_delta_s`, más `fps_note` con la nota legible de `fps_truth` (o
   `null`). `schema_version` de `capture.json` a 1.1.0. Documentarlo en
   `CONTRATO.md` §capture.json.
2. El gate: `vfr_ratio_le_1_10` y `fps_matches_path` evalúan los efectivos.
   Cuando el efectivo difiere del bruto, el chequeo lo dice en su propio
   registro ("ratio 1,000 sin el primer delta de 0,201 s; bruto 6,044"), así
   el entrenador lo ve. En `CAPTURA.md`, una línea en la tabla del gate y dos
   en §"Por qué el archivo no puede decir su propio fps" sobre el delta de
   arranque, citando el informe del 03.
3. `explore.py`: en `prepare_take`, `c.fps_playback` →
   `c.fps_playback_effective` (y el ratio, si lo usa). Nada más en ese
   archivo.
4. Tests: el gate con `first_delta30_h264` contra un camino de prueba a
   30 fps pasa los dos chequeos y `capture.json` conserva bruto y efectivo;
   el clip realmente VFR sigue rechazado; un CFR de punta a punta no cambia
   en nada; `explore` sobre `first_delta30_h264` reporta `fps_archivo`
   30,00.

NO: no tocar `sports/`, `web/`, `service/`, ni la lógica de `fps_truth`.
Nada de `explore.py` fuera de esas líneas. No commitear un camino sin
cronómetro en `data/capture-paths.yaml`.

## Cómo se prueba

- `.venv/bin/pytest -q` en verde con los tests nuevos.
- `python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75`:
  `fps_archivo` 29,998; en el informe, `impact.t_s` y `t_sub_s` antes y
  después (el 02 dio `t_sub_s` 5,008 s con 29,436 fps). Sobre
  `~/Desktop/cortado.mp4` no cambia nada: verificarlo comparando el
  `datos-eventos.json` anterior con el nuevo.
- Ingesta del original del S22 con un camino de prueba (h264, 30 fps) en un
  directorio de datos aparte: veredicto y el registro de los dos chequeos en
  el informe.

## En paralelo

El encargo 05 (lámina interpolada) crea `kinelab/tools/interpolar.py` y
`tests/test_interpolar.py`, y no toca nada de lo tuyo. No toques esos dos.
