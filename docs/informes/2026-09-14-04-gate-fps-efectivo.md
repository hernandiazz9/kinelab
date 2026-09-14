# gate-fps-efectivo — 2026-09-14

**Encargo:** que el gate y el motor dejen de usar el `fps_playback` y el
`vfr_ratio` brutos y pasen a los efectivos del encargo 03 (sin el primer delta
de PTS cuando el arranque de la cámara es la única anomalía), con los brutos a
la vista en `capture.json` y el chequeo diciendo cuándo difieren. Sin tocar
`sports/`, `web/`, `service/` ni la lógica de `fps_truth`.

## Hecho

- **`capture.json` en 1.1.0.** `fps_playback` y `vfr_ratio` son ahora los
  **efectivos** — los que evalúa el gate y los que usa el motor. Los brutos van
  a `fps_playback_raw` y `vfr_ratio_raw`, el delta de arranque a
  `first_delta_s`, y `fps_note` lleva la frase de `fps_truth` que explica la
  diferencia (`null` cuando no hay diferencia, que es el caso normal). Los
  cuatro campos son **opcionales**: un `capture.json` 1.0.0 sigue validando con
  ellos en `null`, y hay test.
- **El gate**: `vfr_ratio_le_1_10` y `fps_matches_path` evalúan los efectivos.
  Cuando el efectivo difiere del bruto, el chequeo lo dice en su propio
  `reason` **aunque pase** — y ese `reason` no entra en `gate.reasons`, que
  sigue llevando sólo lo que falló. Nunca una corrección en silencio.
- **`explore.py`**: `prepare_take` usa `fps_playback_effective` para `fps_real`,
  `fps_playback` y `duration_s`, y `vfr_ratio_effective` para `vfr_ratio`;
  además escribe los cuatro campos nuevos. Nada más de ese archivo.
- `fps_truth.first_delta_note()`: se extrajo la frase que `analyze()` ya
  componía, **sin cambiar el texto ni la lógica**, para que exista una sola
  redacción. La usan `analyze()` y el `fps_note` del gate.
- Documentado: `CONTRATO.md` §capture.json (sección nueva «El fps efectivo y el
  bruto»), §Versionado y §Desviaciones; `CAPTURA.md` §Por qué el archivo no
  puede decir su propio fps (párrafo con los números del S22) y la tabla del
  gate (las dos reglas dicen «efectivo», con un párrafo debajo).

Commits: `0cd5716` (código, tests y documentos) y el de cierre con `ESTADO.md`
y este informe.

## Probado

`.venv/bin/pytest -q`: **197 en verde** (193 antes, 4 nuevos), ~18 s. Arnés:
4 en verde. Ninguno existente cambió salvo el que fijaba
`schema_version == "1.0.0"`, que ahora fija `1.1.0` y además verifica que en un
CFR el bruto y el efectivo son el mismo número y `fps_note` es `null`.

Los 4 tests nuevos:

1. el gate sobre el fixture `first_delta30_h264` contra un camino de 30 fps:
   `vfr_ratio_le_1_10` pasa con 1,00 y `fps_matches_path` con 30,00; el mismo
   test verifica que **con los brutos los dos fallaban** (ratio 6,0 y 28,79 fps
   contra 30, 4 % de desvío), que los dos chequeos explican de dónde salió su
   número, y que lo único que falla es `fps_min_for_gesture`;
2. el `capture.json` de esa ingesta conserva bruto y efectivo, los dos;
3. un `capture.json` 1.0.0 sigue validando, con los cuatro campos en `null`;
4. `explore` sobre ese mismo fixture reporta `fps_archivo` **30,00** (con el
   bruto daría 28,79) y `duration_s` 4,000 s.
   Más el clip realmente VFR, que **sigue rechazado** y cuyo chequeo no
   menciona ningún arranque (aserción agregada al test que ya existía).

**Corrida real, `python -m kinelab datos VIDEO --altura-m 1.75`:**

| | `cortado.mp4` | original `20260907_170638.mp4` |
|---|---|---|
| `fps_archivo` | 29,999 → 29,999 | 29,436 → **29,998** |
| `impact.t_s` | 1,467 → 1,467 | 4,994 → **4,900** |
| `t_sub_s` | 1,481396 → 1,481396 | 5,008089 → **4,914264** |
| `fraction` | 0,4404 → 0,4404 | 0,4181 → 0,4181 |
| `address_to_top_ms` | 1066,7 → 1066,7 | 1019,2 → **1000,1** |
| `top_to_impact_ms` | 166,7 → 166,7 | 203,8 → **200,0** |

Sobre `cortado.mp4` el `datos-eventos.json` nuevo es **idéntico** al anterior
(diff vacío contra la corrida previa al cambio): el recorte arranca en el
cuadro 103 y su primer delta ya era normal. La `fraction` no se mueve en
ninguno de los dos porque va en cuadros; lo que se corrige es el segundo.

En el original, los 30 cuadros de backswing dan ahora **1000,1 ms** y los 6 de
downswing **200,0 ms**: los números redondos que tienen que salir a 30 fps.
Con el bruto salían 1019,2 y 203,8 — 1,9 % largos.

**Ingesta del original del S22** contra un camino de prueba (h264, 30 fps, sin
cronómetro, en un `data/` del scratchpad; **no se commiteó** ningún camino):

```
vfr_ratio_le_1_10 | passed True | value 1.0004 | expected <= 1.1
   → ratio 1.000 sin el primer delta de 0.201 s (arranque de la cámara); bruto 6.044.
fps_matches_path  | passed True | value 29.998 | expected 30.0
   → reproducción 29.998 fps sin el primer delta de 0.201 s (arranque de la cámara); bruto 29.436 fps.
```

Veredicto **`reject`** con una sola razón: `fps_min_for_gesture` — 30 fps de
captura contra los 100 que pide golf. Es lo correcto y es la respuesta que hoy
tiene que dar el gate para ese teléfono en ese modo. Antes de este cambio el
rechazo habría sido doble y la primera razón habría sido falsa («tasa
variable»). El `capture.json`: `fps_playback` 29,9983 · `fps_playback_raw`
29,4359 · `vfr_ratio` 1,0004 · `vfr_ratio_raw` 6,0444 · `first_delta_s`
0,201478 · `duration_s` 8,8333 · `duration_playback_s` 8,9686 · `fps_note` con
la frase completa.

## Queda abierto

- **`duration_playback_s` y `fps_playback` ya no son consistentes entre sí** en
  un clip con arranque largo: el primero sigue siendo el span de PTS medido
  (8,969 s en el original), el segundo la tasa efectiva (que da 8,834 s para
  265 cuadros). Es deliberado — el archivo de verdad dura 8,969 s — y está
  escrito en `CONTRATO.md`, pero conviene saberlo antes de restar los dos.
- **La exploración no avisa en pantalla que corrigió el fps.** El `fps_note`
  queda en `capture.json`, que se puede descargar, pero no entra en `warnings`
  ni en `datos-eventos.json` porque el prompt acotaba `explore.py` a
  `prepare_take`. La ficha del archivo del encargo 07 es el lugar natural: ahí
  el número corregido, el bruto y la frase se muestran juntos.
- El criterio sigue siendo «el primero y sólo el primero», medido en **un**
  teléfono y **un** modo. Sigue abierto del 03: anotar cuánto mide el primer
  delta en cada modo cuando se filme el cronómetro.
- `data/capture-paths.yaml` sigue vacío. El camino del S22 usado acá es de
  prueba y no se commiteó (lo prohibía el prompt, y con razón: no tiene
  cronómetro). Entra con el encargo 06.

## Para que pruebe Hernán

No hay front nuevo. Si querés verlo con tus ojos, dos comandos:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75
```

Tiene que decir **29,998 fps** (antes 29,436), backswing **1000,1 ms** y
downswing **200,0 ms** (antes 1019,2 y 203,8).

```bash
.venv/bin/python -c "import json;print(json.load(open('/Users/heralc/Desktop/20260907_170638.kinelab/capture.json'))['fps_note'])"
```

Tiene que imprimir la frase del arranque de la cámara. Sobre `cortado.mp4` no
cambia absolutamente nada: es el clip con el que venís mirando todo.

## Preguntas para el orquestador

1. **¿El `fps_note` sube a la pantalla ahora o espera al 07?** Hoy sólo está en
   `capture.json`. Un clip de esa cámara se analiza con un fps distinto del que
   declara el archivo, y la pantalla no lo dice en ningún lado. Son dos líneas
   en `explore()` (meter la nota en `warnings`), pero es el archivo que tocó el
   encargo 02 y el prompt lo acotaba.
2. **¿`duration_playback_s` queda como span medido?** Es lo que se hizo y está
   documentado; la alternativa sería `frames_decoded / fps_playback`, que es
   consistente con el resto pero miente sobre cuánto dura el archivo. No parece
   haber caso de uso todavía: nadie lo consume fuera de `capture.json`.
3. El gate del S22 en modo Video rechaza por `fps_min_for_gesture` (30 < 100) y
   va a seguir rechazando con cualquier arreglo de fps. Lo que decide si ese
   teléfono sirve es el cronómetro sobre FHD 60 y Slow motion FHD 240 — el
   pedido que sigue abierto con Hernán.
