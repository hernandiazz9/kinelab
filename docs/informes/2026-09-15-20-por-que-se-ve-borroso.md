# por-que-se-ve-borroso — 15 de septiembre de 2026

**Encargo:** `docs/prompts/20-por-que-se-ve-borroso.md`. Separar con números las
dos causas posibles de que las manos se vean borrosas en `vid1`: desenfoque de
movimiento real de la cámara, o pérdida de nitidez que agregamos nosotros al
reescribir el `overlay.mp4`. Y arreglar lo nuestro **sólo si** la medición
muestra que hay algo nuestro que arreglar.

## Hecho

- **Nada de código tocado.** El punto 6 del prompt (subir la calidad del
  overlay en `kinelab/explore.py`) **no se ejecutó**: el encargo 16 toca ese
  mismo archivo y **no cerró** (no tiene informe en `docs/informes/` ni commit
  en `main`). El cambio exacto queda escrito más abajo, con sus números, para
  que lo aplique quien tenga el archivo. El árbol estaba limpio al empezar y sigue
  limpio salvo lo de esta sesión.
- Medición sobre `data/incoming/vid1.mp4` y su `vid1.kinelab/overlay.mp4`, en
  seis cuadros: **672 (address, referencia quieta), 700, 710, 722 (top), 735 y
  741 (impacto)**.
- Cinco versiones de cada cuadro, todas a la misma resolución (no hace falta
  escalar nada: el overlay es 2160×3840 igual que el original, y el
  `scale=trunc(iw/2)*2` de `explore.py` es un no-op sobre dimensiones pares):
  **A** original decodificado sin recomprimir · **B** el `overlay.mp4` real
  (con el esqueleto quemado encima) · **C** el mismo tramo recodificado con
  **la receta exacta de `explore.py`** pero **sin dibujar nada** — es la única
  comparación limpia contra A, porque el esqueleto que el overlay quema sobre
  las manos sube los indicadores de nitidez en vez de bajarlos — · **D** el
  mismo tramo con más calidad (CRF 12, y después CRF 16 en dos presets, para la
  tabla de recetas) · **E** sin pérdida (`-qp 0 yuv444p`), como control del
  propio banco.
- Tres cajas, la misma en las cinco versiones de cada cuadro: **manos**
  (400×400 px centrada en el punto medio de las dos muñecas de `pose.npz`),
  **árbol** y **pasto** (fijas, sobre zonas quietas). Dos indicadores: varianza
  del laplaciano y fracción de energía de alta frecuencia (radio > 0,25 del
  Nyquist), más PSNR contra A.
- Obturador: no está en ningún metadato (ver abajo); se estimó midiendo el
  **largo del barrido** por ajuste de rampa sobre el borde del guante, con el
  cuadro rotado para que el movimiento quede horizontal.
- Figuras y scripts en `data/incoming/borron-20/` (ignorado por git, no se
  commitea).

Commits: ver al cierre.

## Probado

### La respuesta, en dos números

| | pierde de nitidez la caja de manos |
|---|---|
| **nuestra recompresión** (C contra A, media de los 6 cuadros) | **−5,9 %** de varianza del laplaciano |
| **el movimiento**, en el propio original (cuadro 741 contra el 672, **misma caja**) | **−53,2 %** de varianza del laplaciano y **−83,9 %** de alta frecuencia |

**El borrón es del obturador, no nuestro: nueve veces más grande.** Y la
prueba de que no es compresión está en el control: nuestra recompresión le
saca **tanta o más** nitidez al árbol quieto (−9,0 %) que a las manos
(−5,9 %). Si el culpable fuera el códec, el fondo caería igual que las manos
—y cae—; lo que **sólo** les pasa a las manos es el −53 %.

### La tabla, cuadro por cuadro

Varianza del laplaciano · fracción de alta frecuencia · PSNR contra A.
Caja de manos (400×400 px, centrada en las muñecas de ese cuadro):

| cuadro | v manos (px/cuadro) | A original | B overlay real | C crf20 sin dibujo | E sin pérdida |
|---|---|---|---|---|---|
| 672 address | 3,7 | 493,7 · 4,21 % | 1258,0 · 4,88 % · 14,0 dB | 444,5 · 3,78 % · 35,7 dB | 495,4 · 4,21 % · 53,6 dB |
| 700 | 19,7 | 384,6 · 5,25 % | 519,2 · 4,80 % · 20,6 dB | 361,6 · 4,85 % · 34,4 dB | 387,0 · 5,25 % · 53,8 dB |
| 710 | 25,2 | 640,4 · 6,66 % | 667,2 · 6,13 % · 20,8 dB | 568,7 · 6,32 % · 33,7 dB | 642,5 · 6,65 % · 53,7 dB |
| 722 top | 10,4 | 899,3 · 8,81 % | 1369,0 · 8,58 % · 15,5 dB | 825,9 · 8,21 % · 32,5 dB | 901,7 · 8,80 % · 53,9 dB |
| 735 | 65,3 | 518,3 · 7,03 % | 580,7 · 6,05 % · 19,9 dB | 523,9 · 6,86 % · 35,4 dB | 520,2 · 7,02 % · 53,8 dB |
| 741 impacto | 59,6 | 233,2 · 0,90 % | 770,0 · 1,63 % · 14,1 dB | 230,3 · 0,81 % · 36,1 dB | 234,6 · 0,90 % · 53,3 dB |

Tres lecturas:

1. **La columna B (el overlay real) no sirve para medir nitidez** y por eso
   existe la C: el esqueleto quemado *sube* el laplaciano —1258 contra 494 en
   el address— y hunde el PSNR a 14–21 dB. Lo que cambia sobre las manos en el
   overlay son los palitos y los puntos blancos que dibujamos, no la nitidez.
2. **La columna C vale 33–36 dB contra el original** y conserva el 94 % del
   laplaciano. Es una pérdida real, uniforme y chica.
3. **La columna E (sin pérdida) da 53,3–53,9 dB y no 99**: ése es el piso del
   propio banco, el redondeo del viaje `yuv420p → bgr24 → yuv`. Los
   indicadores coinciden con A dentro del 0,1 %, así que el método mide lo que
   dice medir.

Cajas de control, las dos quietas, C contra A (media de los 6 cuadros):

| caja | % del laplaciano del original que conserva C | PSNR |
|---|---|---|
| manos | **94,1 %** | 34,6 dB |
| árbol (fondo quieto) | **91,0 %** | 30,6–32,8 dB |
| pasto (fondo quieto) | **93,0 %** | 33,8–36,2 dB |

### Que el original ya viene barrido, con la misma caja dos veces

Las manos vuelven casi al mismo lugar en el impacto que en el address —centro
(1147, 1996) en el 672 y (1131, 1961) en el 741—, así que la **misma caja de
400×400 px** cubre la misma escena en los dos cuadros: el mismo guante, el
mismo palo, el mismo tronco y el mismo pasto detrás.

| | laplaciano | alta frecuencia |
|---|---|---|
| cuadro 672, manos a 3,7 px/cuadro | 493,7 | 4,21 % |
| cuadro 741, manos a 59,6 px/cuadro | 231,1 | 0,68 % |
| | **−53,2 %** | **−83,9 %** |

Y en esos **mismos dos cuadros**, un borde del fondo quieto (el tronco) medido
con el mismo ajuste de rampa da **2,0 px** en el 672 y **2,5 px** en el 741,
con el pico del gradiente en 49,5 y 50,0. **La cámara no se movió y el códec no
cambió; lo único que se barrió es el sujeto.**

**Lo que se ve en los PNG** (los miré, están en `data/incoming/borron-20/`):

- `address-vs-impacto.png` — las dos cajas al lado. En el address se leen el
  logo del guante, la esfera del reloj, las tres tiras del pantalón, los dedos
  y la corteza del tronco. En el impacto el guante es una mancha alargada
  horizontal con estrías, el palo es una banda traslúcida de varias posiciones
  superpuestas… **y el tronco de la derecha sigue igual de nítido que en el
  address, en el mismo cuadro.** Ésa es toda la discusión.
- `tira-original-x2.png` — 672, 710 y 741 al doble, sólo del original. En el
  710 (backswing, 25 px/cuadro) el guante ya perdió los dedos y es un borrón,
  **y la corteza del árbol detrás está nítida**. O sea: el borrón del backswing
  que ve Hernán está en el archivo del teléfono.
- `lamina-manos.png` — las tres versiones × los seis cuadros. Las filas A y C
  son indistinguibles a ojo; la fila B es la que tiene los palitos encima.

### El obturador: no está en ningún metadato, y estimado da 1/100–1/140 s

**No está declarado, verificado en tres lugares:** `ffprobe -show_frames` no
trae exposición; el `moov` sólo tiene `com.android.version`,
`com.android.capture.fps` (60.000000) y `com.samsung.android.utc_offset`; y la
miniatura embebida en el `udta` **sí trae un bloque Exif**, pero con seis
etiquetas (`ExifVersion`, `ComponentsConfiguration`, `FlashpixVersion`,
`ColorSpace`, `PixelXDimension` 1920, `PixelYDimension` 1080) y **ninguna es
`ExposureTime`**.

Estimado del barrido. Un escalón de intensidad barrido L px deja una rampa
lineal de ancho exactamente L: se ajusta por mínimos cuadrados, fila por fila,
el modelo (meseta, rampa de ancho L, meseta) al perfil de gris a lo largo de la
dirección de viaje, sobre el borde del guante, con el cuadro rotado para que el
movimiento quede horizontal. El mismo ajuste con el sujeto quieto da el ancho
óptico del borde, **2,5 px**, que se resta.

| cuadro | ancho de rampa | barrido | desplazamiento en un cuadro | fracción del cuadro expuesta | obturador |
|---|---|---|---|---|---|
| 672 (quieto) | 2,5 px | — | 3,7 px | — | — |
| 700 | 14,5 px | 12,0 px | 19,7 px | 0,61 | **1/98 s** |
| 710 | 13,5 px | 11,0 px | 25,2 px | 0,44 | **1/138 s** |
| 741 | 29,2 px | 26,8 px | 59,6 px | 0,45 | **1/134 s** |
| 735 | no medible | | 65,3 px | | |

El 735 queda afuera a propósito: ahí el borde del guante corre casi **a lo
largo** del movimiento y el ajuste no converge (8 px de mediana con recorrido
intercuartil de 6,0 a 12,8, incompatible con la estela que se ve en
`rot-735.png`). El método necesita un borde perpendicular al movimiento.

**El obturador está entre 1/100 y 1/140 s**, o sea entre el 44 % y el 61 % del
intervalo de cuadro de 1/60 s (ángulo de obturación de 160° a 220°).
Procedencia: `estimacion`. Los dos cuadros con el borde mejor elegido —el 710,
que miré en la imagen antes de poner la ventana, y el 741, que verifiqué
leyendo el perfil de intensidad a mano— coinciden en **0,44 y 0,45**, que es la
firma de una cámara de video eligiendo medio cuadro de exposición.

### Qué significa ese obturador

Escala del clip: la cadena de estatura de la repetición mide **1196,4 px** para
1,75 m declarados → **683,6 px/m**. Las manos en el impacto van a 3578 px/s =
**5,23 m/s** (el pico del clip que reporta el motor es 7,81 m/s).

| | barrido de la mano en el impacto |
|---|---|
| **el que hubo, 1/135 s** | **26,8 px medidos** (= 3,9 cm de recorrido de la mano) |
| 1/240 s (el tope a 240 fps) | 14,9 px |
| 1/500 s | 7,2 px |
| **1/1000 s (la regla de `CAPTURA.md` §Luz)** | **3,6 px** |

`CAPTURA.md` §Luz pide **≤ 5 px**, que en este clip son **1/716 s**: entre
**5 y 7 veces** más corto que lo que la cámara eligió. La tabla de `CAPTURA.md`
queda confirmada de paso: con su convención (cuerpo de 918 px, o sea 524,6
px/m) una mano a 10 m/s barre 21,9 px a 1/240 s, contra los 21,2 px que la
tabla declara.

**Y lo que la medición contradice es otra frase de esa misma sección:** *"Golf
al aire libre, de día, sin contraluz: con ~20.000 lux el teléfono elige
~1/2000 s a ISO bajo. Sale gratis."* Este clip **es** golf al aire libre de día
y el teléfono eligió **~1/135 s**, no 1/2000. No le faltó luz: en modo Video la
cámara mantiene el obturador cerca de medio cuadro —comportamiento
cinematográfico— y baja el ISO. **La luz no es la palanca; la palanca es una
app que deje fijar el obturador** (en el S22, el modo *Pro Video*, que sí lo
permite; `CAPTURA.md` ya nombra Blackmagic Camera para iOS con la misma idea).

Como el teléfono parece elegir ~45 % del cuadro pase lo que pase, subir el fps
**sí** ayuda, porque achica el cuadro: a 240 fps el mismo swing daría
3578 × 0,45/240 = **6,7 px** de barrido, y con el tope duro de 1/240 s,
**14,9 px**. Sigue sin llegar a los 5 px sin fijar el obturador a mano.

### Qué compraría subir la calidad del overlay (medido, no aplicado)

Mismo tramo de 111 cuadros (655–765), mismas cajas. `explore.py` usa hoy
`libx264 -preset veryfast -crf 20 -g 12`:

| receta | MB / 111 cuadros | ms/cuadro | manos | árbol | pasto | PSNR manos |
|---|---|---|---|---|---|---|
| **crf 20 veryfast (hoy)** | 26,6 | 19 | 94,1 % | 91,0 % | 93,0 % | 34,6 dB |
| crf 16 veryfast | 41,6 | 20 | **96,4 %** | 93,5 % | 95,0 % | 36,7 dB |
| crf 16 medium | 42,5 | 44 | 97,5 % | 95,6 % | 97,2 % | 37,2 dB |
| crf 12 slow | 63,5 | 145 | 97,8 % | 96,6 % | 97,2 % | 38,9 dB |

Extrapolado a los 1066 cuadros de `vid1` (el `overlay.mp4` de hoy pesa 257 MB
a 115,7 Mb/s, contra los 93,3 MiB a 43,1 Mb/s del original — ya gastamos 2,7×
los bits del archivo de cámara):

| receta | overlay de vid1 | codificación |
|---|---|---|
| crf 20 veryfast (hoy) | 255 MB | 20,3 s |
| **crf 16 veryfast** | **400 MB** | **21,3 s** |
| crf 16 medium | 408 MB | 46,9 s |

**Lo barato es `crf 16` con el mismo preset: +2,3 puntos de laplaciano y
+2,1 dB por +57 % de disco y 1 ms/cuadro** (dentro del ruido de medición: el
mismo `crf 20` dio 21 y 19 ms/cuadro en dos corridas). `medium` cuesta 2,2× el
tiempo por 1,1 punto más, y `crf 12 slow` 7,3× por 1,4. **Nada de esto arregla el borrón**, que es 9× más
grande y está en el archivo de la cámara.

**El cambio exacto, para cuando `explore.py` esté libre** (encargo 16). Es un
carácter, en la única llamada a `subprocess.Popen` de `render()`
(`kinelab/explore.py:298`, que es una sola línea larga): donde dice
`"-crf", "20"` tiene que decir `"-crf", "16"`.

No hace falta tocar nada más: **no hay reescalado que sacar** (el
`scale=trunc(iw/2)*2:trunc(ih/2)*2` no hace nada sobre 2160×3840, verificado
con `ffprobe` sobre el overlay) y el `-g 12` tiene que quedarse, que es del
visor.

### Lo que la interpolación del encargo 05 no tiene que ver, re-verificado

```
grep -rn "interpolado\|lamina\|lámina" service/ web/src/ kinelab/explore.py sports/
```
no devuelve nada. Igual que en el informe del 05.

### Un método que probé y no sirve, para que nadie lo repita

Medir la nitidez de la caja de manos **cuadro por cuadro** a lo largo del tramo
y correlacionarla con la velocidad de las manos **no contesta nada**:
correlación −0,15 sobre 109 cuadros, y los cuadros rápidos dan *más*
laplaciano que los quietos (539 contra 506). La razón es que la caja se mueve
con las manos y lo que domina el indicador es **qué hay detrás** —pasto liso,
corteza de árbol, el propio cuerpo—, no el barrido. Por eso las dos
mediciones que sí valen son la de **caja fija** (672 contra 741, misma escena)
y la del **borde** (que sólo mira el objeto que se mueve).

Del mismo modo, la caja de fondo quieto **no es una regla fina**: medida cada
20 cuadros sobre los 1066 del clip, su alta frecuencia oscila entre 24,5 % y
30,7 % (media 28,0 ± 1,7 % en los 44 cuadros con las manos quietas) por el
propio control de tasa del teléfono y el viento en las ramas. Sirve como
control **dentro de un mismo cuadro** —donde A y C son exactos— y no como
serie temporal.

### Suites

`.venv/bin/pytest -q` → **272 en verde en 28,8 s**. No se tocó código, así que
es la línea de base de HEAD; el test rojo que reportó el informe del 11
(`test_datos_lista_un_ejemplo_de_otro_proceso`) ya no falla.

## Queda abierto

- **El punto 6 del prompt no se ejecutó**: el encargo 16 toca `explore.py` y no
  cerró. El cambio de un carácter está arriba con sus números. Aplicarlo y volver a
  medir es media hora, y se mide con
  `data/incoming/borron-20/scripts/recetas.py`.
- **`quality.blur_estimate` del contrato está en `null`** en los cuatro clips
  reales, y esta sesión acaba de fabricar exactamente el número que ese campo
  pide. Ver las preguntas.
- **El obturador es `estimacion`, de tres bordes en tres cuadros de un clip.**
  Para que fuera `medido_aqui` haría falta filmar un objeto de velocidad
  conocida (el mismo cronómetro que falta, o un péndulo), o un clip del modo
  *Pro Video* con el obturador fijado y comparar el barrido predicho contra el
  medido. El arnés (`truth/`, barrido de desenfoque por promediado de
  sub-cuadros, ESPECIFICACION 3.1) ya tiene la maquinaria para el otro lado de
  la pregunta: cuántos grados de error mete un barrido de 27 px.
- **No se midió el efecto del barrido sobre los keypoints de este clip.** El
  banco heredado (`banco/degrade.py`) midió −2,5° en el codo con `rtmpose-m` y
  21 px de desenfoque; acá hay 26,8 px medidos sobre material real, pero
  comparar contra qué verdad es otro encargo.
- **Hay otra sesión trabajando en el mismo directorio.** Al cerrar aparecieron
  sin commitear `kinelab/tools/exportar_demo.py`, `tests/test_exportar_demo.py`
  y `web/public/`, que no son de este encargo: no se tocaron ni se commitearon.
- **No se abrió el front** (regla de trabajo). Queda una hipótesis **no
  medida** sobre la comparación que hizo Hernán: el original lo mira en un
  reproductor a pantalla completa y el overlay en el recuadro del navegador, y
  un 2160×3840 metido en un recuadro chico lo reescala el navegador con su
  propio filtro. Eso puede agregar blandura percibida **sin que el archivo
  cambie**. Se comprueba mirando el `overlay.mp4` en QuickTime a pantalla
  completa, al lado del original: si ahí las manos se ven igual de borrosas en
  los dos, el archivo está bien y lo que queda es la ventana.

## Para que pruebe Hernán

Nada de front. Tres cosas para mirar con tus ojos:

```bash
open data/incoming/borron-20/address-vs-impacto.png
```
La misma caja de 400×400 px del **archivo del teléfono sin recomprimir**, en el
address y en el impacto. Mirá el tronco del árbol de la derecha: está igual de
nítido en los dos. Mirá el guante: en el address se le lee el logo; en el
impacto es una mancha. Eso es el obturador.

```bash
open data/incoming/borron-20/tira-original-x2.png
```
Address, backswing (cuadro 710) e impacto, al doble, **sólo del original**. El
borrón del backswing que viste ya está acá, antes de que nosotros toquemos
nada.

```bash
open data/incoming/borron-20/lamina-manos.png
```
Tres filas: **A** original · **B** el `overlay.mp4` que te muestra la pantalla
· **C** el mismo tramo recodificado con nuestra receta pero sin dibujar. A y C
son indistinguibles; lo único que separa a B es el esqueleto que le quemamos
encima de las manos.

Y si querés cerrar la hipótesis de la ventana del navegador:

```bash
open data/incoming/vid1.kinelab/overlay.mp4 data/incoming/vid1.mp4
```
Los dos en QuickTime, a pantalla completa, parados en el mismo cuadro del
backswing. Si ahí se ven iguales de borrosos, el archivo está bien.

## Preguntas para el orquestador

1. **¿`crf 16` entra?** +57 % de disco (255 → 400 MB en `vid1`) por +2,3 puntos
   de laplaciano y +2,1 dB, a costo de tiempo cero. No arregla el borrón. Es
   una línea en `explore.py:298`, que hoy es del encargo 16. Mi recomendación:
   **sí, pero como cambio de higiene**, no como respuesta a esta pregunta — y
   avisando que el overlay ya pesa 2,7× el original y esto lo llevaría a 4,3×.
2. **`quality.blur_estimate` sigue en `null` y ahora hay cómo llenarlo.** El
   ajuste de rampa sobre el borde del sujeto da un largo de barrido en px por
   cuadro, y el cociente contra el desplazamiento de `pose.npz` da la fracción
   del cuadro expuesta. ¿Se construye como métrica de calidad —caro, un ajuste
   por cuadro— o se estima barato desde el desplazamiento de las manos y una
   fracción declarada por camino de captura? Y sobre todo: **¿llega a ser
   gate?** `CAPTURA.md` §Luz ya tiene el umbral escrito (≤ 5 px) y hoy no lo
   comprueba nadie; este clip lo viola por 5,4×.
3. **`CAPTURA.md` §Luz tiene una frase que la medición contradice** —que al
   aire libre el teléfono elige ~1/2000 s y "sale gratis"—. Medido: en modo
   Video, al aire libre, eligió ~1/135 s. La consecuencia operativa es fuerte y
   no es mía: **con la cámara nativa del S22 en modo Video no se llega a 5 px
   de barrido con ninguna luz**; hace falta el modo *Pro Video* con el
   obturador fijado, que es un camino de captura nuevo, con su propio `id` y su
   propio cronómetro. ¿Se escribe? (`CAPTURA.md` no es de este encargo.)
4. **El obturador y el fps ahora compiten por la misma decisión.** El informe
   del 11 dejó abierto si se pide el cronómetro de Slow motion FHD 240 o se
   baja el `fps_min` de golf. Este informe agrega un dato a esa cuenta: a
   240 fps el barrido bajaría de 26,8 a **6,7 px** (o 14,9 px con el tope duro
   de 1/240 s) **sin tocar el obturador**. O sea que el modo de 240 arregla dos
   cosas a la vez, y filmar en Video 60 no arregla ninguna.

## Las tres líneas del cierre

1. **No es nuestro.** Nuestra recompresión le saca **5,9 %** de nitidez a la
   caja de manos y **9,0 %** al árbol quieto del fondo: es uniforme, chica, y
   le pega igual a lo que se mueve y a lo que no.
2. **Es el obturador.** En el mismo cuadro en que el tronco del fondo mide
   2,5 px de borde, el guante mide **29,2 px**: un barrido de **26,8 px** que,
   contra los 59,6 px que la mano se mueve en un cuadro, dice que el
   obturador estuvo abierto **el 45 % del cuadro, ~1/135 s**. La caja de manos
   pierde **53 %** de laplaciano y **84 %** de alta frecuencia entre el address
   y el impacto, con la misma caja y la misma escena.
3. **Ningún cambio de software lo arregla.** `CAPTURA.md` pide ≤ 5 px, que acá
   son 1/716 s: 5 a 7 veces más corto que lo que eligió la cámara. Se arregla
   filmando distinto —obturador fijo, o 240 fps—, no codificando mejor.
