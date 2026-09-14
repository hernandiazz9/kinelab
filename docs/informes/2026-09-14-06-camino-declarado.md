# camino-declarado — 2026-09-14

**Encargo:** ADR-016. Que `capture-paths.yaml` admita caminos **declarados sin
cronómetro** (`calibrated: false`), que el gate los acepte diciendo bajo qué
supuesto, que la procedencia del fps (`medido_aqui` / `sin_verificar`) viaje al
`capture.json`, al `header` del `analysis.json` y a cada métrica impidiendo todo
juicio, que un `slomo` sin calibrar se rechace con una frase para el entrenador,
y que `python -m kinelab datos` tome `--camino`. Sin tocar `web/` ni `service/`.

## Hecho

- **`capture-paths.yaml` en 1.1.0**: campo `calibrated` (default `true`, así un
  archivo viejo no cambia de significado). Con `calibrated: true` los seis
  campos del cronómetro más `nominal_fps` y `codec_expected` son obligatorios;
  con `false` los seis tienen que estar en **`null`** —declarar no es medir— y
  `nominal_fps` / `codec_expected` son opcionales (`null` = no se sabe). El
  archivo del repo deja de estar vacío: entran `desconocido-video`,
  `s22ultra-video-fhd60-cable` y `s22ultra-video-fhd30-cable`, los tres
  declarados y los tres `mode: video`.
- **Gate**: `capture_path_known` pasa con un camino declarado y lo dice en su
  propio `reason` (que no entra en `gate.reasons`); `fps_matches_path` queda en
  `null` porque no hay reproducción medida contra la que comparar;
  `codec_matches_path` queda en `null` si el camino no declara codec;
  `fps_min_for_gesture` y `duration_plausible` se evalúan con la tasa de
  captura **asumida** y el chequeo dice que es asumida, pase o falle. Un
  `slomo` sin calibrar → `reject` en `capture_path_known` con la frase del
  factor de estiramiento desconocido, y los chequeos que necesitan tasa de
  captura quedan sin evaluar en vez de inventar un número.
- **`capture.json` en 1.2.0**: `capture_path_calibrated` (`true`/`false`/`null`)
  y `fps_provenance` (`medido_aqui`/`sin_verificar`), los dos opcionales con
  default conservador; `fps_source` empieza con `declarado:<id>` cuando el
  camino es declarado. Un `capture.json` 1.0.0 sigue validando.
- **Contrato**: `header.source.fps_provenance` y `fps_provenance` en **cada**
  métrica del sextuplo (elegí el campo y no sólo `uncertainty.method`: una
  métrica en `null` tiene `uncertainty: null` y la procedencia no se puede
  perder; la frase de `uncertainty.method` la repite igual para quien lee el
  JSON a ojo). `judgment_allowed` ahora exige `fps_provenance == "medido_aqui"`,
  en la función del registro, no a mano. `analysis.json` pasa a **1.2.0** y
  `warnings[0]` lleva el aviso cuando el camino es declarado.
- **`python -m kinelab datos VIDEO --camino ID`** (default `desconocido-video`):
  `datos-eventos.json` lleva `camino`, `camino_calibrado`, `fps_provenance` y
  `fps_aviso` (la frase completa), y el overlay quema una cuarta línea
  `camino <id> | fps <n> | <procedencia>` — ASCII, con escala propia acotada al
  ancho para no encoger las tres líneas que ya estaban.
- **Una precisión que el código obligó y que va en el ADR:** en exploración la
  procedencia es **siempre** `sin_verificar`, incluso con un camino calibrado,
  porque ahí el gate no corre y nadie verificó que el archivo vino por ese
  camino (eso lo hace `fps_matches_path`). Los números del cronómetro sí se usan
  si el camino los tiene —descartarlos daría tiempos ×8 mal en un Slo-Mo—, pero
  no habilitan juicio.
- Documentado: ADR-016 en `DECISIONES.md`; invariante 2 y el glosario en
  `CONTEXTO.md`; `CAPTURA.md` §Caminos declarados sin calibrar (con tabla
  calibrado/declarado) y las tres filas de la tabla del gate; `CONTRATO.md`
  §capture-paths.yaml, §capture.json (§La procedencia del fps), §sextuplo,
  §Versionado y §Desviaciones.

Commits: `4dc8b7f` (código, tests, YAML y documentos) y el de cierre con
`ESTADO.md` y este informe.

## Probado

`.venv/bin/pytest`: **240 en verde**, 26 s. Arnés: **4 en verde**. Los tres
archivos de test que toqué pasan de **103 a 131 casos**: 28 nuevos (el resto de
la diferencia contra los 206 del encargo 05 es del 08, que corrió en paralelo).
Ningún test existente cambió de sentido; los cinco que tocaba el cambio se
actualizaron (dos `schema_version`, el listado de caminos del fixture, la frase
de `capture_path_known` y la firma de `judgment_allowed`).

Tests nuevos de este encargo (28):

- `test_capture_paths.py`: declarado carga con los seis campos en `null`;
  puede declarar `nominal_fps` y `codec_expected`; **no** puede declarar
  ninguno de los seis del cronómetro (6 casos parametrizados); un calibrado
  necesita los ocho campos (8 casos); `calibrated` es `true` por default; un
  `slomo` declarado **carga** a propósito, para que la frase la diga el gate y
  no un error de parseo; el archivo del repo es válido y sus declarados son
  todos `video`; `resolve_path_id` nombra las alternativas.
- `test_gate.py`: camino declarado `video` **pasa** y dice el supuesto, con
  `fps_matches_path` y `codec_matches_path` en `null`; el declarado que sí
  declara codec lo compara igual (pasa con h264, rechaza con hevc); a 30 fps
  sigue rechazando por `fps_min_for_gesture`; `slomo` declarado rechaza con la
  frase; los dos `capture.json` (video y slomo) con sus campos nuevos; un
  `capture.json` 1.0.0 llega con `fps_provenance: sin_verificar`.
- `test_fase2.py`: `judgment_allowed` es `False` con `sin_verificar` aunque
  estén el MDC, el fps y la vista; **de punta a punta**: el mismo take, la misma
  pose y el mismo fps, cambiando sólo la procedencia en `capture.json`, da
  **los mismos valores** y **todos** los `judgment_allowed` en `False`, con el
  aviso primero en `warnings`; el validador rechaza un `analysis.json` sin
  `fps_provenance` (en el header y en una métrica) y con una procedencia fuera
  del enum.

**Ingesta real del original del S22** (`~/Desktop/20260907_170638.mp4`, 265
cuadros) con `--camino s22ultra-video-fhd30-cable`, en un `data/` del
scratchpad:

```
capture_path_known  | passed True  | 's22ultra-video-fhd30-cable' es un camino declarado sin
                                     cronómetro: los tiempos asumen que el archivo reproduce a la
                                     velocidad de captura (Samsung Galaxy S22 Ultra, modo video).
codec_matches_path  | passed True  | h264 == h264
vfr_ratio_le_1_10   | passed True  | 1.0004 (bruto 6.044, primer delta 0.201 s)
fps_matches_path    | passed None  | no evaluado: el camino no está calibrado y no declara fps de
                                     reproducción; no hay contra qué comparar
fps_min_for_gesture | passed False | 29.9983 contra >= 100. Tasa de captura asumida igual a la de
                                     reproducción.
duration_plausible  | passed True  | 8.834 s
rotation_normalized | passed True  | 90
view_declared       | passed True  | face_on
gesture_known       | passed True  | driver
```

Veredicto **`reject`**, una sola razón: `fps_min_for_gesture`. **Ocho de nueve
chequeos pasan, y `capture_path_known` entre ellos por primera vez** — antes el
gate moría en el primer chequeo con cualquier clip de ese teléfono. `capture.json`:
`capture_path_calibrated` false · `fps_provenance` `sin_verificar` · `fps_real`
29,9983 · `stretch_factor` 1,0 · `fps_source` `declarado:s22ultra-video-fhd30-cable`
· `schema_version` 1.2.0.

**Percepción y análisis sobre ese take: no se pudieron correr, y está bien.**
`run_perception` se niega a correr pose sobre una toma rechazada
(`kinelab/perception/run.py:74`), que es la regla correcta y es anterior a este
encargo. Para tener los números que pedía el prompt se corrió el mismo clip con
el mismo camino por el modo exploración, que es el camino real de un clip que
no puede pasar el gate:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75 \
    --camino s22ultra-video-fhd30-cable
```

- `header.source`: `fps_real` 29,998 · `fps_provenance` `sin_verificar` ·
  `capture_path_id` `s22ultra-video-fhd30-cable`.
- **Las 12 métricas en `null`** y **ningún `judgment_allowed` verdadero**. 11
  mueren por `fps_min` (`"fps_real 29.998 por debajo de fps_min 30"` para las de
  cm, 60 para el tempo, 120 para las duraciones) y `pelvis_thrust_top_cm` por
  vista (`down_the_line`).
- Eventos y tiempos idénticos a los del encargo 04: address 111, top 141,
  impacto 147 (sub-cuadro 147→148, `fraction` 0,4181, `t_sub_s` 4,914264),
  backswing 1000,1 ms, downswing 200,0 ms. ADR-016 **no movió ninguna
  medición**: sólo agregó de dónde sale el eje del tiempo.

**`python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75`** (camino por
defecto `desconocido-video`): `datos-por-cuadro.csv` **byte a byte idéntico** al
de antes del cambio, y el `datos-eventos.json` difiere **sólo** en los cuatro
campos nuevos (`camino`, `camino_calibrado`, `fps_provenance`, `fps_aviso`);
ningún número cambió. El `analysis.json` difiere en `schema_version`
(1.1.0→1.2.0), `capture_path_id` (`exploracion`→`desconocido-video`),
`fps_provenance` en el header y en las 12 métricas, y el warning nuevo. El
`pose_sha256` cambia porque la `provenance` del `.npz` incluye `run_at`; que los
keypoints son los mismos lo prueba el CSV idéntico.

## Queda abierto

- **A 29,998 fps se mueren también las métricas de `fps_min: 30.0`**, por dos
  milésimas. Es correcto según la regla (`fps_real >= fps_min`), pero la tabla
  del arnés escribió `30.0` pensando en "30 fps" y un teléfono real entrega
  29,998. Con un camino declarado el `fps_real` es siempre el medido del
  archivo, así que esto va a pasar con **todo** clip de 30 fps. Decisión del
  orquestador: tolerancia en la comparación, o `29.9` en `sports/golf/mdc.yaml`.
  No lo toqué: el prompt prohibía tocar la lógica de métricas, y `mdc.yaml` lo
  escribe el arnés.
- **El `fps_note` (la corrección del primer delta) sigue sin subir a la
  pantalla**, que era la pregunta 1 del informe del 04. Ahora el mecanismo
  existe: hay un warning al principio de `warnings[]` y un campo en
  `datos-eventos.json`. Meterlo es una línea en el mismo lugar; no lo hice
  porque el prompt del 06 listaba exactamente qué campos agregar.
- **`s22ultra-video-fhd60-cable` no declara codec** (`null`): no está medido en
  ese modo. El primer clip de FHD 60 lo resuelve; hasta entonces
  `codec_matches_path` queda sin evaluar para ese camino.
- **Nada de esto acerca el S22 a pasar el gate de golf.** 30 y 60 fps están
  debajo de 100. Lo que decide si ese teléfono sirve sigue siendo el cronómetro
  sobre los modos de más de 60 fps (FHD 240 slow motion), y un `slomo`
  declarado está rechazado a propósito: ahí el cronómetro no es opcional.
- **El front todavía no muestra nada de esto** (no se tocó `web/` ni
  `service/`, por encargo). Los campos que necesita el 07 ya están en
  `datos-eventos.json` y `GET /api/config` ya lista los caminos con su
  `calibrated`.
- Choque de sesiones paralelas: mi cambio de 4 líneas en
  `tests/test_service.py` (la lista de caminos del fixture creció) quedó
  commiteado por la sesión del encargo 08 en `cee7585`. No hay nada que
  arreglar; lo anoto para que no sorprenda en el historial.

## Para que pruebe Hernán

No hay front nuevo. Tres comandos:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75
```

La segunda línea tiene que decir `camino desconocido-video · fps sin_verificar
(declarado, sin cronómetro)`, y los números de siempre (76 cuadros a 29,999 fps,
backswing 1066,7 ms, downswing 166,7 ms). En `evento-impact.png` hay una cuarta
línea naranja abajo de las tres blancas: `camino desconocido-video | fps 29.999
| sin_verificar`.

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75 --camino s22ultra-video-fhd30-cable
```

Lo mismo con el original de 9 s, declarando que salió del S22 en modo Video 30.

```bash
.venv/bin/python -m kinelab.ingest ~/Desktop/20260907_170638.mp4 --atleta hernan --gesto driver --vista face_on --camino s22ultra-video-fhd30-cable --data /tmp/kinelab-prueba
```

Tiene que imprimir `gate: RECHAZADO` con **una** razón (30 fps contra 100) y
dejar `/tmp/kinelab-prueba/sessions/hernan/2026-09-07/driver/face_on/take-01/capture.json`
con `fps_provenance: "sin_verificar"` y el chequeo `capture_path_known` en
`true` con la frase del camino declarado.

## Preguntas para el orquestador

1. **¿`fps_min: 30.0` contra un teléfono que entrega 29,998?** Hoy no pasa
   ninguna métrica de 30 fps en ningún clip real de 30 fps. Las dos salidas son
   una tolerancia en la comparación (p. ej. 0,5 %) o bajar el número en la tabla
   del arnés. La segunda es más honesta con "el arnés escribe la tabla", pero
   hay que decidir quién la escribe: el barrido corre en fps enteros.
2. **¿El aviso del camino declarado sube al front en el 07 y en qué forma?**
   Está en `datos-eventos.json` como `fps_aviso` (frase completa) y
   `fps_provenance` (token), y en `analysis.json` como `warnings[0]`. La regla
   de ADR-016 es que se lea **antes** de cualquier número.
3. **¿Se aprueba la desviación del contrato?** `fps_provenance` es un campo
   **obligatorio** nuevo en un bump **minor** de `analysis.json` (1.2.0).
   Anotado en `CONTRATO.md` §Desviaciones con las tres razones: opcional
   permitiría escribir un análisis que esconda el supuesto, el validador sólo
   corre al escribir, y no hay `analysis.json` viejo fuera de lo que se
   regenera.
4. **¿La procedencia siempre `sin_verificar` en exploración es lo que querías?**
   Lo escribí en el ADR. La alternativa sería que un camino calibrado diera
   `medido_aqui` también sin gate, y entonces una métrica podría ser juicio sin
   que nadie haya comparado el archivo contra el camino.
