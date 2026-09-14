# lamina-interpolada — 14 de septiembre de 2026

**Encargo:** `docs/prompts/05-lamina-interpolada.md`. Una herramienta agnóstica
al deporte que fabrique con `minterpolate` de ffmpeg los cuadros que faltan
entre dos cuadros medidos, los etiquete como no medidos, y los deje en una
lámina en fila para decidir MIRANDO si sirven o si el shaft sale fantasma.
Ninguna métrica lee lo que produce.

## Hecho

- `kinelab/tools/interpolar.py`, nueva. Recibe **índices de cuadro**, no
  "impacto": `--entre A B`, `--factor`, `--contexto`, `--marca`,
  `--marca-texto`, `--marca-mas-menos`, `--recorte`, `--filtro`,
  `--fps-reproduccion`, `--out`. El texto de la marca lo pone quien llama; el
  motor no sabe qué evento es.
- Escribe dos archivos en `<video>.kinelab/`: `interpolado-A-B-x<factor>.mp4`
  (tramo `[A−contexto, B+contexto]`, H.264 `-g 12`, con el rótulo **quemado**
  en cada cuadro: verde `medido | 44`, naranja `cuadro interpolado, no medido |
  44,25`) y `lamina-A-B-x<factor>.png` (A, los intermedios y B en fila,
  recortados al bbox de la persona, con la marca vertical y su banda de ±).
- Los cuadros se leen con el mismo `iter_frames` de la percepción, **no** con
  `select=between(n,…)` de ffmpeg: la edit list de `cortado.mp4` (esconde 13
  muestras) corre los índices de ffmpeg y no los del motor. El cuadro 44 de la
  lámina es el 44 de `pose.npz`.
- Alineación exacta: a `minterpolate` se le entra a **1 fps** y se le pide
  `fps=factor`, así el cuadro de salida `k` cae en el índice `k/factor` sin
  redondeo de time base. Y como `minterpolate` emite `(n−1)·factor` cuadros y
  se queda sin el último, se le entrega el último **duplicado**: la salida tiene
  `(n−1)·factor + 1`, que es el tramo entero.
- `tests/test_interpolar.py`: 9 tests sobre el clip sintético de `conftest.py`.
- Commit: `d94dcfd`.

## Probado

**Suite:** `.venv/bin/pytest -q` → **206 en verde en 17,5 s** (9 nuevos; el
resto incluye lo del encargo 04, que corrió en paralelo). `truth/` no se tocó.

**Las dos corridas pedidas sobre `~/Desktop/cortado.mp4`** (1080×2320, 29,999
fps, cuadros 42–47 leídos):

| | factor 4 | factor 8 |
|---|---|---|
| cuadros de salida | 21 | 41 |
| tiempo | **7,6 s** | **14,5 s** |
| `interpolado-44-45-x*.mp4` | 954 KB · 120,00 fps · 0,175 s | 1787 KB · 239,99 fps · 0,171 s |
| `lamina-44-45-x*.png` | 6783 KB · 3215×1693 · 5 paneles | 12212 KB · 5775×1856 · 9 paneles |

Recorte de la lámina: `(227, 693, 842, 2019)`, el bbox de la persona en
`pose.npz` con margen. Marca en 44,44 con banda ±0,11.

**Nada lo lee, verificado:** `grep -rn "interpolado\|lamina\|lámina" service/
web/src/ kinelab/explore.py sports/` no devuelve nada. La lista blanca de
`service/exploracion.py` sigue con sus 9 nombres y ninguno es éste.

**Con qué configuración de `minterpolate` me quedé y por qué.** La del prompt,
`mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`, pero **dos de esas cuatro
opciones no hacen nada**, medido: con `mc_mode=obmc` y `vsbmc=0` la salida es
**byte a byte idéntica** en ffmpeg 9.0.1. La que sí mueve la aguja es
`me_mode`: `bidir` (que no es el default del filtro; el default es `bilat`)
reconstruye mejor.

La prueba: dejar fuera los cuadros **impares** de 38 a 50 y pedirle que los
reconstruya desde los pares — exactamente lo que se le pide acá (rellenar
entre muestras de 30 fps), pero a la mitad de resolución temporal, donde el
cuadro del medio **sí existe** para comparar. Error medio sobre una caja de
600×850 px alrededor de las manos y el palo en el impacto:

| | dB (cuadro entero) | dB (palo y manos) | error RMS sobre el palo |
|---|---|---|---|
| `mci` + `bidir` (el elegido) | 24,14 | 21,22 | **22,2 niveles** |
| `mci` + `bilat` (default de ffmpeg) | 23,79 | 20,49 | 24,1 |
| `blend` (crossfade liso) | 23,19 | 19,32 | 27,6 |
| `dup` (congelar el cuadro anterior) | 21,51 | 17,62 | 33,5 |

También medido y descartado: `search_param` 64/128 gana 0,1 dB sobre el 32 por
defecto y 256 lo pierde — agrandar la ventana de búsqueda no arregla nada;
`me=umh` cuesta **46 s en vez de 3,4 s** y sale peor; `mb_size=8` sale peor;
`scd=none` da igual.

**Lo que se ve en la lámina, sin decidir por Hernán.** El shaft sale
**fantasma**. En los intermedios no hay un palo en una posición intermedia: hay
dos palos translúcidos a la vez — el de 44 desvaneciéndose hacia abajo-izquierda
y el rojizo de 45 apareciendo hacia abajo-derecha — y en el medio del hueco
(44,38–44,62 a x8) ninguno de los dos se lee. El cuerpo también se dobla: en
esos cuadros la raya blanca del pantalón sale duplicada y las manos son una
mancha. Los dos extremos, 44 y 45, están intactos.

Los números dicen lo mismo: la compensación de movimiento se lleva **34 %** del
error de congelar el cuadro y **20 %** del de un crossfade liso; el error que
queda sobre el palo (22,2 niveles RMS) es **dos tercios** del cambio que tenía
que explicar (44 contra 45 difieren 36,3 niveles RMS sobre esa caja). Y el
cuadro 44,50 se parece a un crossfade 50/50 de 44 y 45 a 21,35 dB, más de lo
que 44 se parece a 45 (16,94 dB): está mucho más cerca de un promedio que de un
cuadro nuevo.

## Queda abierto

- **Si esto sirve o no, lo decide Hernán mirando.** La sesión mide y describe;
  no hay un criterio numérico de "sirve para mirar".
- El mp4 a `fps × factor` **dura 0,17 s**: no se puede mirar reproduciéndolo,
  hay que ir cuadro a cuadro. Existe `--fps-reproduccion` (probado a 6 fps:
  6,8 s de video) pero el default sigue siendo el que pedía el prompt.
- El recorte por defecto es el bbox de la persona, que a 615×1326 px por panel
  obliga a hacer zoom al 100 % para juzgar el palo. Un recorte fijo alrededor
  de las manos se ve mucho mejor y está probado (`--recorte x0,y0,x1,y1`),
  pero no es el que quedó en los dos archivos entregados.
- La herramienta **no dibuja pose ni eventos** sobre los cuadros interpolados,
  a propósito: correr pose sobre un cuadro fabricado era una de las cosas que
  el prompt prohibía.
- `Pillow` **no está** en el entorno, contra lo que suponía el prompt. Los
  rótulos se dibujan con `cv2.putText`, que sólo tiene ASCII: el texto se
  translitera al quemarlo (`é`→`e`, `·`→`|`, `±`→`+/-`). En el código y en la
  consola el español queda entero. No se agregó la dependencia (ADR-015).

## Preguntas para el orquestador

1. **¿El experimento se cierra acá o se vuelve a intentar con otra técnica?**
   Con ffmpeg no hay nada más que probar: el barrido está hecho y el techo es
   el de arriba. Lo que queda fuera (RIFE, FILM) está vetado por ADR-010. Si la
   respuesta a "quiero ver el contacto" tiene que ser sí, el camino es material
   a 120/240 fps, no software.
2. **¿La herramienta se queda en el repo?** Es 500 líneas que ninguna fase de
   `ESPECIFICACION.md` pide. Argumento para quedarse: sirve para cualquier par
   de cuadros de cualquier clip y deja la evidencia etiquetada. Argumento para
   borrarla: es un experimento contestado.
3. **`--recorte` por defecto:** ¿bbox de la persona (lo que hay) o un recorte
   fijo alrededor de las manos? Lo segundo se lee mejor para juzgar el palo,
   pero "manos" es una decisión de encuadre, no del motor.
