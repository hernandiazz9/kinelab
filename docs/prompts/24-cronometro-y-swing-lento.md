# 24 — El cronómetro filmado: calibrar el camino y, por primera vez, un clip que pase el gate

Para correr: `/encargo 24` en una sesión nueva. Leé antes los informes del
03, 04, 06 y 11 en `docs/informes/`, y `CAPTURA.md` §Calibración con
cronómetro y §El gate de ingesta.

## Contexto

`~/Desktop/Cortado-lenta.mp4` es **lo que el proyecto venía esperando desde
la Fase 0**: un swing de golf filmado en cámara lenta con un cronómetro
corriendo **dentro del mismo cuadro** (un teléfono apoyado en el pasto, abajo
a la izquierda, se lee `00:05.27` en el primer cuadro). Eso resuelve de una
sola vez lo que ningún metadato puede: **a qué tasa capturó de verdad ese
archivo**.

Hasta hoy no hay ningún camino calibrado en `data/capture-paths.yaml`; los
tres que hay son declarados (ADR-016) y por eso **ninguna métrica del proyecto
pudo ser nunca un juicio**. Si este clip da una tasa uniforme y creíble, deja
de ser así.

Lo que se sabe del archivo, medido antes de escribir esto: HEVC, 1920×1080
con rotación (se ve vertical), **612 cuadros**, 19,907 s de duración de
contenedor, 7,58 Mb/s, creado el 15/9 a las 16:24. **No tiene las etiquetas
`com.android.capture.fps` ni `com.samsung.*`** que sí tenían los clips del
encargo 11: el nombre «Cortado» y esa ausencia dicen que es un **recorte**,
probablemente hecho en la Mac. Eso importa y está tratado abajo.

Leer: `kinelab/tools/fps_truth.py`, `kinelab/ingest/capture_paths.py`,
`gate.py`, `session.py`, `__main__.py`, `kinelab/metrics/registry.py` (la
regla de `judgment_allowed`), `kinelab/explore.py` (sólo para correr `datos`),
`sports/golf/config.py` (el `fps_min` del gesto), `data/capture-paths.yaml`,
`CONTRATO.md` §capture-paths.yaml y §capture.json, `CONTEXTO.md` invariante 2.

## Encargo

### 1 · Leer el cronómetro

1. Copiá el clip a `data/incoming/` sin tocar el original, con su sha256.
2. Extraé cuadros **por índice, no por tiempo** (`select=eq(n\,N)`), al menos
   estos: el primero legible, el último legible, y cuatro o cinco repartidos.
   **Miralos con `Read`** y anotá la lectura del cronómetro de cada uno, con
   el número de cuadro. Si un dígito no se lee con seguridad, decilo y usá
   otro cuadro: una lectura dudosa contamina todo lo que sigue.
3. Con la primera y la última: **`fps_real` = (cuadros entre ellas) /
   (segundos del cronómetro entre ellas)**. Con las intermedias, la tasa de
   cada tramo por separado.
4. **La pregunta que decide todo: ¿es uniforme?** El modo de cámara lenta de
   Samsung mezcla tramos a velocidad normal y a velocidad lenta dentro del
   mismo archivo. Si los tramos dan tasas distintas, **no se escribe ningún
   camino calibrado**: se reporta cada tramo con su tasa y se para ahí. Si
   dan la misma dentro de un 1 %, seguí.
5. Reportá también `fps_playback` (de los PTS, con y sin el primer delta,
   encargo 03) y **`stretch_factor` = `fps_real` / `fps_playback`**. Con 612
   cuadros y ~19,9 s de reproducción, si el cronómetro avanzó ~2,5 s la tasa
   real es ~245 fps y el estiramiento ~8×.

### 2 · El camino calibrado

Sólo si el punto 4 dio uniforme. En `data/capture-paths.yaml`, un camino con
`calibrated: true` y los seis campos del cronómetro llenos: `fps_real`,
`fps_playback`, `stretch_factor`, `fps_method` (las dos lecturas y el conteo
de cuadros, textual), `calibrated_on: 2026-09-15`, `calibrated_by`.

**El id tiene que decir la verdad sobre qué se calibró.** Este archivo es un
recorte y perdió las etiquetas del fabricante: lo medido es «S22 Ultra en
cámara lenta, recortado en la Mac», no el archivo tal como sale del teléfono.
Poné eso en el id y en `notes`, y **pedile a Hernán el archivo original sin
recortar** para calibrar el camino de verdad; anotá el pedido en el informe.
Si el original aparece durante la sesión, calibrá los dos y compará.

### 3 · El gate, de verdad

Ingestá el clip con ese camino:

```
.venv/bin/python -m kinelab.ingest data/incoming/Cortado-lenta.mp4 \
  --atleta hernan --gesto driver --vista face_on --camino <id> --data <scratch>
```

Reportá los nueve chequeos con su valor. Con `fps_real` sobre 100, por primera
vez **`fps_min_for_gesture` puede pasar**. Si el veredicto es `ok`, decilo con
todas las letras: es el primer clip del proyecto que pasa el gate.

### 4 · Percepción, análisis y el juicio

Si el gate pasó, corré `kinelab.perception` y después `kinelab analyze` sobre
esa toma, que es el camino que nunca se pudo recorrer con material real.
Reportá:

- Calidad: detección, altura del cuerpo en px y en fracción, plausibilidad,
  multi-sujeto (hay un carrito de golf a la derecha del cuadro: mirá si lo
  toma como persona).
- Eventos y duraciones, con el sub-cuadro del impacto y su incertidumbre.
- **Las doce métricas del registro, una por una**: cuáles tienen valor,
  cuáles quedan en `null` con su razón, y **cuáles tienen
  `judgment_allowed: true`**. Ese booleano es el entregable de este encargo:
  es la primera vez que puede ser verdadero, porque exige `fps_provenance ==
  "medido_aqui"`, MDC medido, fps suficiente y vista válida. Si sigue en
  `false` en todas, explicá cuál de las cuatro condiciones falla.
- Corré también `datos` sobre el mismo clip para tener el overlay y poder
  mirarlo, y decí en qué cuadro cae el impacto y si la pelota se mueve entre
  ese cuadro y el siguiente.

### 5 · Lo que este clip enseña sobre cómo filmar

En una sección corta del informe, para que Hernán lo lea: qué salió bien de
esta toma y qué conviene cambiar en la próxima (encuadre, dónde poner el
cronómetro para que se lea sin dudas, si el sol y el obturador alcanzaron a
esta tasa). No toques `CAPTURA.md` ni `docs/filmacion-s22.md`: proponé el
texto en el informe.

NO: no escribir un camino calibrado si los tramos no son uniformes; no
inferir la tasa de ningún metadato; no tocar `kinelab/` ni `sports/` ni
`web/` ni `service/`; no cambiar umbrales del gate para que este clip pase.
Si el gate lo rechaza, **el rechazo es el resultado** y hay que reportarlo
como tal.

## Cómo se prueba

- `.venv/bin/pytest -q tests/test_capture_paths.py` en verde si tocaste el
  YAML, y la suite entera también.
- Las lecturas del cronómetro en el informe, con el número de cuadro al lado
  de cada una, y las rutas de los JPG para que Hernán las mire.
- El `capture.json` de la ingesta, recortado a lo que importa.
- La tabla de las doce métricas con su `judgment_allowed`.

## En paralelo

El 16 toca `kinelab/` y el contrato; el 18 toca `kinelab/events/`; el 17 y el
21 están pendientes. Vos: `data/capture-paths.yaml`, `data/incoming/`,
`ESTADO.md` y tu informe. Ningún otro archivo.
