# 06 — Caminos de captura declarados sin calibrar (ADR-016)

Para correr: `/encargo 06` en una sesión nueva, **después de que el 04 haya
cerrado** (tocan los mismos archivos). Leé su informe en `docs/informes/`.

## Contexto

Hernán no tiene el iPhone 17 Pro para el que están escritos `CAPTURA.md` y
ADR-003. Tiene un Galaxy S22 Ultra, y todavía no filmó el cronómetro. Hoy el
gate rechaza todo clip sin camino calibrado (`capture_path_known`), y el modo
exploración analiza cualquier cosa sin decir bajo qué supuestos. Hernán pide
poder subir un video, ver qué es, y analizarlo con la configuración que
corresponda, avisando que el resultado depende del material.

Lo que el archivo dice de sí mismo (codec, tamaño, rotación, cuadros, tasa de
reproducción efectiva, VFR, primer delta) ya lo mide `fps_truth`. Lo que no
puede decir (si reproduce a la velocidad a la que capturó) no se infiere: se
declara como supuesto visible, o se mide con cronómetro. El registro de
métricas ya degrada por `fps_min` y `views` con `null` y razón: eso no cambia.

Decisión del orquestador, a escribir como ADR-016 en `DECISIONES.md` (texto
abajo; ajustalo si el código te muestra algo que lo contradiga, y decilo).

Leer: `kinelab/ingest/capture_paths.py`, `gate.py`, `session.py`,
`__main__.py`; `kinelab/contract/schema.json`, `validate.py`, `write.py`;
`kinelab/metrics/registry.py` (la regla de `judgment_allowed`);
`kinelab/explore.py` (`prepare_take`: cómo arma un take sin gate);
`sports/golf/config.py` (fps mínimo del gesto); `data/capture-paths.yaml`;
`tests/test_capture_paths.py`, `tests/test_gate.py`; ADR-003 en
`DECISIONES.md`; `CAPTURA.md` §capture-paths y §gate; `CONTRATO.md`
§capture-paths.yaml, §capture.json y §sextuplo; invariante 2 de `CONTEXTO.md`.

## Texto de ADR-016 (para `DECISIONES.md`, al final)

> **ADR-016 · Caminos de captura declarados sin calibrar**
> **Decisión.** `capture-paths.yaml` admite caminos con `calibrated: false`:
> dispositivo y modo declarados por el usuario, sin cronómetro. Sólo
> `mode: video`. Para ellos `fps_real` se asume igual al `fps_playback`
> efectivo (`stretch_factor` 1,0) con procedencia `sin_verificar`, y esa
> procedencia viaja a `capture.json`, al `header` de `analysis.json` y a cada
> métrica: ninguna métrica de un camino sin calibrar puede ser juicio
> (`judgment_allowed` lo exige), y el informe lo dice antes de cualquier
> número. Un camino `slomo` sin calibrar se rechaza con razón: sin cronómetro
> el factor de estiramiento es desconocido y cualquier tiempo es ficción.
> Existe un camino genérico `desconocido-video` para "no sé con qué se
> filmó". Filmar el cronómetro del mismo dispositivo y modo convierte el
> camino en calibrado, y los clips se re-analizan (invariante 18) sin volver
> a correr el modelo (invariante 1).
> **Por qué.** El entrenador no tiene el iPhone de `CAPTURA.md`; tiene un
> Galaxy S22 Ultra. ADR-003 dejó Android fuera por la ralentización horneada
> del modo slow motion; el modo Video no la tiene (medido en el original de
> 9 s: 265 cuadros CFR a 29,998 fps tras el delta de arranque, informe del
> 03). Lo que el archivo dice de sí mismo se usa; lo que no puede decir se
> declara como supuesto visible, nunca se infiere. Sustituye en parte a
> ADR-003: Android entra como camino declarado; como camino calibrado, sólo
> con cronómetro. Invariante 2 queda: "calibrada con cronómetro, o declarada
> sin calibrar con procedencia `sin_verificar` y sin juicio (ADR-016)".

## Encargo

1. `capture-paths.yaml`: campo `calibrated` (los caminos existentes, si
   hubiera, son `true`); para `false`, `fps_real`, `fps_method`,
   `calibrated_on` y `calibrated_by` pueden ser `null`. Agregar al archivo del
   repo, comentados como declarados: `desconocido-video`,
   `s22ultra-video-fhd60-cable`, `s22ultra-video-fhd30-cable`. Ningún camino
   `slomo` sin calibrar. Validación con tests.
2. Gate: `capture_path_known` pasa con un camino declarado y lo dice
   ("camino declarado sin cronómetro: los tiempos asumen que el archivo
   reproduce a la velocidad de captura"); `fps_matches_path` queda `null` con
   razón (no hay contra qué comparar); `codec_matches_path` compara si el
   camino declara codec, si no `null`. `slomo` sin calibrar → `reject` con la
   frase para el entrenador. `capture.json`: `capture_path_calibrated`,
   `fps_provenance` (`medido_aqui` | `sin_verificar`), `fps_source` que diga
   `declarado:<id>`. `schema_version` de `capture.json` minor.
3. Contrato: `header.source.fps_provenance` en `analysis.json`;
   `judgment_allowed` exige `fps_provenance == "medido_aqui"`; el sextuplo
   de cada métrica anclada a tiempo lleva la procedencia del fps en su
   `uncertainty.method` o en un campo `fps_provenance` (elegí, documentá en
   `CONTRATO.md`, minor de schema, test del validador). Un `warnings[]`
   legible cuando el camino es declarado.
4. `python -m kinelab datos VIDEO --camino ID` (default `desconocido-video`):
   `datos-eventos.json` lleva `camino`, `fps_provenance` y el mismo aviso;
   el overlay lo quema en una línea. `python -m kinelab.ingest … --camino
   s22ultra-video-fhd30-cable` sobre el original del S22 tiene que pasar el
   gate por primera vez, con el aviso.
5. Documentar en `CAPTURA.md` (§capture-paths, tabla del gate) y
   `CONTEXTO.md` (invariante 2, una frase con "ADR-016").

NO: no tocar `web/` ni `service/` (eso es el 07, con tus nombres de campo);
no cambiar la lógica de eventos ni de métricas; no inferir nunca el
`stretch_factor` del contenedor; no hacer que un camino declarado permita
juicio "mientras tanto".

## Cómo se prueba

- `.venv/bin/pytest -q` en verde con los tests nuevos (yaml declarado válido
  e inválido; gate con camino declarado `video` pasa y con `slomo` rechaza;
  `judgment_allowed` falso con `sin_verificar` aunque haya MDC y fps; el
  validador acepta el `analysis.json` nuevo y rechaza uno sin
  `fps_provenance`).
- Ingesta real del original del S22 con `s22ultra-video-fhd30-cable` en un
  directorio de datos aparte: `capture.json` y el veredicto en el informe.
  Después percepción y análisis sobre ese take: qué métricas salen, cuáles
  quedan `null` y con qué razón (a 30 fps las duraciones deberían morir por
  `fps_min`), y ningún `judgment_allowed` verdadero.
- `python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75`: mismos
  números que antes más los campos nuevos; verificarlo comparando el JSON.

## En paralelo

El 05 (lámina interpolada) toca sólo `kinelab/tools/interpolar.py` y
`tests/test_interpolar.py`. No toques esos.
