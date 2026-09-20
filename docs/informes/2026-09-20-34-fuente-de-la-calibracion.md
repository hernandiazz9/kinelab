# fuente-de-la-calibracion — 2026-09-20

Resumen: el fps de una toma ya dice **de qué clip salió**. `capture-paths.yaml`
va a **1.2.0** con `calibration_clip_sha256` (opcional, fuera de los seis campos
del cronómetro) y `capture.json` a **1.3.0** con `fps_calibration {clip_sha256,
same_file}`; los dos bumps son **minor** y **no hay desviación del contrato**.
Declarado el sha del único camino calibrado (`Cortado-lenta.mp4`,
`ff13415e0a1a…`, leído de su `capture.json` y verificado contra el archivo). Con
eso, **2 de los 26 `capture.json` del repo** quedan en `same_file: false` con
aviso, **1 en `true`** y **23 en `null` sin aviso** (son caminos declarados, de
los que ya avisa ADR-016) — el prompt esperaba «varios de exploración»: son dos,
porque casi toda la exploración corrió con `desconocido-video`. **No hay `Check`
nuevo y `CHECK_ORDER` no se movió**: es procedencia, no un chequeo. Corrida
real: `cortado3-lento` re-ingestado da **gate ok 9 de 9**, `same_file: false` y
el aviso como `warnings[0]`. Motor **448/0/1 salteado exit 0** (+51), arnés
**43/0 exit 0**, `pnpm lint` y `pnpm build` exit 0. Lo que sigue abierto es
material, no código: **el único clip que se calibró a sí mismo es el que el gate
rechaza por durar 2,49 s**.

Para Hernán: subí un video nuevo al front y mirá la línea **«de qué clip salió
ese fps»** en la ficha del archivo — los trabajos que ya están en la lista son
anteriores y no la muestran; comandos y qué esperar, abajo en «Para que pruebe
Hernán».

Encargo: registrar de qué clip sale la calibración del fps de un camino, decirlo
en cada toma y en la pantalla, sin convertirlo en un chequeo que rechace.

## Hecho

Commits: **`b94e1be`** (motor, datos, contrato, `CAPTURA.md` y tests),
**`b4a981e`** (front), y el de cierre con `ESTADO.md` y este informe.

- **`calibration_clip_sha256` en `capture-paths`, schema 1.2.0.** Opcional y
  **fuera de `_CALIBRATION_FIELDS`**, que son todo o nada: un camino calibrado
  que no lo declara sigue cargando, analizando y habilitando juicio. La
  procedencia **se registra, no se exige**. Un camino **declarado** no puede
  declararlo — sin cronómetro no hay clip que lo mida — y el sha tiene que tener
  forma de sha (64 hex en minúscula).
- **`fps_calibration` en `capture.json`, schema 1.3.0**, con `clip_sha256` y
  `same_file`. `true` = la toma se calibró a sí misma; `false` = hereda la tasa
  de otro archivo del mismo camino; `null` = no se puede saber. **`null` no es
  `false`.** Lo escribe `build_capture_json` y también las dos ramas de
  `explore.py`, que arman el `CaptureJson` por su cuenta — si no, ningún trabajo
  de exploración lo habría tenido, que es justo donde el prompt lo quería.
- **El aviso, por `analysis.warnings`.** Sin `Check` nuevo. Queda **junto al de
  ADR-016 y después de él**, que es el más fuerte, con un test que fija el orden.
- **`fps_truth` imprime el sha** al terminar, en la línea que se pega tal cual en
  el YAML, y en `--json`. Reusa `sha256_file`; se calcula en el CLI y no en
  `analyze()` para no releer 90 MB en cada ingesta.
- **El sha del camino real, declarado y verificado** (`shasum -a 256` contra el
  archivo, y contra el `capture.json` de su exploración: coinciden).
- **Las dos fichas de captura, con quien las vigile** (`test_fichas_de_captura.py`,
  14 tests): compara el conjunto entero de claves y todos los valores, en cuatro
  casos. Hasta hoy no las testeaba nada.
- **Front**: un solo lugar, la ficha del archivo. **`CAPTURE_PATHS_FILE`** en vez
  del literal en `kinelab/ingest/__main__.py`.

## Probado

**Suites.** Motor **448 pasados, 0 fallados, 1 salteado, exit 0** (base del
worktree: 397 + 1; **+51 tests**). El salteado es el de los pesos de `models/`,
que git ignora. Arnés **43 pasados, 0 fallados, exit 0**. `pnpm lint` exit 0 ·
`pnpm build` exit 0.

**La corrida real**, `cortado3-lento.mp4` re-ingestado por CLI a un directorio
temporal (ningún trabajo pisado):

```
schema_version   : 1.3.0
capture_path_id  : s22ultra-slomo-fhd240-recorte-mac
fps_real         : 240.15
sha256_original  : 6557e7b69d5e1f72de2c2bd2233e37830463f6c25c68d04ded1cdeb3436f4a81
fps_calibration  : {"clip_sha256": "ff13415e0a1a4fad…", "same_file": false}
gate             : ok · 9 de 9 chequeos  (los mismos nueve ids de CHECK_ORDER)
```

Y el aviso que sale, `warnings[0]` de 5:

> El fps de captura de esta toma (240.15 fps) NO lo midió este archivo: lo hereda
> del camino 's22ultra-slomo-fhd240-recorte-mac', que se calibró con otro clip
> (sha256 ff13415e0a1a…). Este archivo es sha256 6557e7b69d5e…. […]

**`Cortado-lenta.mp4`, el clip que calibró el camino, da `same_file: true`** — y
se rechaza igual por `duration_plausible` (2,49 s reales contra 3). La
procedencia no toca el veredicto, que es exactamente el punto.

**Censo de los 26 `capture.json` de `data/`** (leídos, no regenerados):

| estado | cuántos | cuáles |
|---|---|---|
| `same_file: false` → **aviso** | **2** | exploración de `cortado3-lento` · `sessions/hernan/2026-09-15/.../take-01` |
| `same_file: true` | 1 | exploración de `Cortado-lenta` |
| `null`, **sin** aviso | 23 | caminos declarados (`desconocido-video`, los del S22 por cable) |

**Mutación manual.** Sacarle una clave a **una sola** de las dos fichas pone
**13 de 14** en rojo en `test_fichas_de_captura.py` (el archivo se restauró y
`git diff` quedó limpio).

**Compatibilidad hacia atrás, con test.** Un `capture-paths` 1.1.0 sin el campo
carga; un `capture.json` 1.2.0 sin `fps_calibration` valida, con los dos campos
en `null` y sin que se mueva nada más.

## Queda abierto

- **El único clip que se calibró a sí mismo es el que el gate rechaza.**
  `Cortado-lenta` da `same_file: true` y dura 2,49 s reales; `cortado3-lento`
  pasa el gate y **hereda** la tasa. Este encargo hace visible ese hueco, no lo
  cierra: lo cierra el pedido que viene desde el 24 y el 26 — **una toma de 25 s
  con el cronómetro andando dentro del cuadro**. Y los 240,15 fps siguen siendo
  n = 1.
- **Los 26 `capture.json` en disco no se regeneraron** (congelados por el
  prompt): siguen en 1.2.0. Al re-analizarlos muestran el aviso de `null` hasta
  que se los re-ingeste. La frase está redactada para ser cierta también ahí:
  dice lo que sabe **la toma**, no lo que dice el YAML de hoy, porque
  `analysis.py` no vuelve a resolver el camino contra `capture-paths.yaml` — y no
  debería, el `capture.json` es lo que la ingesta escribió.
- **El front no se abrió** (regla de trabajo). Para ver los tres estados hay que
  subir un trabajo nuevo.
- **El bug de `--data` de `explore()`** que anota `ESTADO.md` sigue abierto: es de
  otro encargo, no se tocó.

## Para que pruebe Hernán

```bash
cd /Users/heralc/Desktop/HDDev/kinelab
.venv/bin/python -m service          # backend
cd web && pnpm dev                   # front
```

1. **Subí un video nuevo** (cualquiera sirve) y mirá la ficha **«El archivo»**.
   Los trabajos que ya están en la lista son anteriores al contrato 1.3.0 y **no
   muestran nada nuevo**: eso también es lo correcto y vale como prueba.
2. Con el camino por defecto (`desconocido-video`, **declarado**): la línea nueva
   **no aparece**. Ahí no hubo cronómetro y de eso ya avisa la procedencia del
   fps, que está justo arriba.
3. Con el camino **calibrado** (`s22ultra-slomo-fhd240-recorte-mac`) y un clip
   que **no** sea `Cortado-lenta.mp4` — por ejemplo `cortado3-lento.mp4`:
   aparece **«de qué clip salió ese fps → heredado de otro clip · lo calibró
   sha256 ff13415e0a1a… y este archivo es otro»**, en ámbar. Y el mismo texto,
   largo, arriba de todo en los avisos del análisis.
4. Con ese mismo camino y **`Cortado-lenta.mp4`**: **«de esta misma toma: el
   cronómetro está en este archivo»**, en verde, y **ningún aviso** de esto en el
   análisis. (Ese clip no pasa el gate por durar 2,49 s, así que esto se ve en
   exploración.)
5. El tercer estado —«el camino no declara con qué clip se lo calibró»— **no se
   puede ver hoy** sin editar el YAML: el único camino calibrado ya declara su
   clip. Si querés verlo, comentá la línea `calibration_clip_sha256` de
   `data/capture-paths.yaml` y volvé a subir.

Y una lectura, si te interesa: `CONTRATO.md` §De qué clip salió esa calibración.
Lo que hay que mirar es si la distinción entre **`false`** (heredado) y **`null`**
(no se sabe) se entiende sin explicación.

## Preguntas para el orquestador

1. **La pregunta 3 del informe del 26 queda contestada, y por (b).** Preguntaba
   si alcanzaba con dejar escrito el supuesto o si el gate debía distinguir
   «camino calibrado y verificado en este clip» de «camino calibrado y
   heredado». Ahora **se distingue**, pero **no en el gate**: es un campo de
   procedencia en `capture.json` y una frase en `warnings[]`, sin `Check` ni
   rechazo. Si preferías que fuera un chequeo, es un ADR.
2. **¿Se re-ingestan los trabajos de `data/exploracion/` y la demo?** Hoy siguen
   en 1.2.0 y muestran el aviso de `null`, que es cierto pero pobre. Regenerarlos
   estaba prohibido por este prompt; es un encargo chico y tiene la ventaja de
   dejar la demo publicada mostrando los tres estados.
3. **El id del camino sigue envejeciendo mal** (pregunta 4 del 24, 5ª del 26).
   Ahora hay **tres clips** bajo `…-recorte-mac`, y con este encargo el archivo
   dice cuál de los tres lo calibró — que era la mitad del problema. La otra
   mitad sigue: el camino del teléfono crudo no existe. No lo toqué.
4. **¿Vale la pena un chequeo de que el sha declarado corresponda a un archivo
   que exista?** Hoy nada verifica que `ff13415e…` sea un archivo alcanzable; si
   alguien borra `Cortado-lenta.mp4`, el camino sigue declarando un sha huérfano.
   No es urgente y no era de esta sesión.
