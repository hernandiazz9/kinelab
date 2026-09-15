# senal-de-manos — 2026-09-15

**Encargo:** pesar el centro de las manos por la confianza de cada muñeca con un
umbral, ponerle banda al top cuando dos candidatos no se distinguen del ruido, y
hacer llegar al evento el MDC que el arnés le midió al instante sub-cuadro del
impacto.

## Hecho

- **`kinelab/events/signal.py` · `hands_center` pesado por confianza.** Acepta
  los `scores` del modelo y un `min_score`: cada muñeca pesa lo que el modelo
  dice que vale en ese cuadro, y la que cae bajo el umbral **no entra**. Si se
  caen las dos, el punto queda `NaN` y lo rellena el **mismo relleno acotado de
  la percepción** (`interpolate_gaps`, rachas ≤ 5, sin extrapolar bordes). Sin
  `scores` pesan igual, que es lo que hacía antes.
- **`kinelab/events/primitives.py` · la banda.**
  `direction_change_farthest_band` no toca la regla de ADR-017 —gana la mayor
  excursión— y agrega los **rivales**: los candidatos cuya excursión está a menos
  de `margin` del ganador. `tol_frames` es la distancia en cuadros hasta el más
  lejano de ellos. Y `still_noise_px`, el σ de los residuos de una recta ajustada
  a la quietud del address, que es lo que el sub-cuadro del impacto ya hacía a
  mano y ahora comparten los dos.
- **`sports/golf/events.py`**: `wrist_score_min` = **0,55** y `top_band_sigmas` =
  **2,0** en `GolfEventParams` (procedencia `estimacion`, como el resto);
  `margin = 2 σ_px` con el σ del propio clip; y `events[].impact.subframe.mdc`
  leído de `sports/golf/mdc.yaml` §`events.impact.subframe` — **nunca escrito a
  mano** (ESPECIFICACION 3.3), con `provenance: medido_aqui` para el MDC y la
  `estimacion` del valor intacta al lado.
- **19 tests nuevos** en `tests/test_eventos_senal.py`.
- **Tres enganches los escribió el encargo 16**, dueño de esos archivos (ver
  §Desviaciones): el paso de `scores` y umbral en `kinelab/analysis.py`,
  `MetricContext.tolerances` + el `±tol_frames` de `evaluate` en
  `kinelab/metrics/core.py`, y el lugar de `subframe.mdc` en el schema 2.0.0.
  Se pidieron por escrito con el código exacto y se verificaron corriendo.

Commits: `c94c8d8` (los dos archivos del motor, verificados solos sobre una copia
limpia de HEAD) y el de `sports/golf/events.py` + los tests, que esperó a que el
schema 2.0.0 del 16 estuviera en HEAD: con el schema viejo, escribir `mdc` dentro
de `subframe` hace fallar la validación de **todo** `analysis.json`.

## Probado

**Suite del motor: 344 en verde** en el árbol compartido (los 19 nuevos y el
trabajo del 16 adentro). Los dos archivos del motor se verificaron **solos sobre
una copia limpia de HEAD** antes de commitearlos —`git archive HEAD` a /tmp, sin
tocar el árbol que comparten tres sesiones—: **320 en verde, cero rojos**. El
arnés no se tocó.

**Mutación manual: 8 de 8** ponen en rojo entre 1 y 9 tests, incluidos los dos
que pedía el prompt:

| bug inyectado | tests en rojo |
|---|---|
| pesar por **1 − confianza** | 7 |
| **umbral en 0** | 6 |
| el margen de la banda al revés (`>` por `<`) | 5 |
| la banda es el rival más **cercano** (`min` por `max`) | 2 |
| elegir el cambio de sentido más cercano (ADR-017 al revés) | 9 |
| el ruido como desvío de la **media** y no de la recta | 1 |
| la procedencia del MDC en `estimacion` | 1 |
| sin banda (`margin = None` siempre) | 1 |

### 1 · El umbral salió de un barrido, no de mirar una lista de scores

Los scores de las dos muñecas, sobre los cinco clips reales del S22 y el mocap:

| clip | izquierda (mín · p5 · mediana) | derecha (mín · p5 · mediana) |
|---|---|---|
| `cortado.mp4` | **0,354** · 0,400 · 0,639 | 0,565 · 0,615 · 0,710 |
| `20260907_170638.mp4` | **0,343** · 0,389 · 0,701 | 0,531 · 0,643 · 0,751 |
| `vid1.mp4` | 0,458 · 0,586 · 0,744 | 0,545 · 0,759 · 0,834 |
| `vid2.mp4` | 0,482 · 0,637 · 0,794 | 0,508 · 0,687 · 0,835 |
| `vid3.mp4` | 0,520 · 0,546 · 0,797 | 0,484 · 0,659 · 0,746 |
| mocap 64_01 (las dos vistas) | 1,000 en todos los cuadros | 1,000 |

En los dos clips del 7/9 la izquierda cae a 0,34–0,44 **justo en el top**
(`cortado`, cuadros 32–38: 0,35 · 0,36 · 0,40 · 0,40 · 0,43 · 0,51 · 0,39)
mientras la derecha no baja de 0,53 en todo el clip. En los otros tres no hay
muñeca perdida: ninguna baja de 0,458.

El barrido del umbral, con el top que sale en cada caso (referencia = la muñeca
derecha sola, la señal limpia que usó el 15):

| clip | 0,00 | 0,35 | 0,40 | 0,45 | **0,50** | **0,55** | 0,60 | 0,65 | referencia |
|---|---|---|---|---|---|---|---|---|---|
| `cortado.mp4` | 33 | 33 | 33 | 34 | 34 | **35** | 35 | 36 | 36 |
| `20260907_170638.mp4` | 137 | 138 | 137 | 139 | **139** | **139** | 139 | 139 | 139 |
| `vid1.mp4` | 722 | 722 | 722 | 722 | 722 | **722** | 722 | **570** | 722 |
| `vid2.mp4` | 115 | 115 | 115 | 115 | 115 | **115** | 115 | 115 | 114 |
| mocap `face_on` | 270 | 270 | 270 | 270 | 270 | **270** | 270 | 270 | 269 |
| mocap `down_the_line` | 263 | 263 | 263 | 263 | 263 | **263** | 263 | 263 | 269 |

**El número no se eligió por esa tabla** —elegir el umbral que más se acerca a la
referencia es ajustar al resultado—, sino por un criterio que no la mira: **el
mayor umbral con el que en ningún cuadro se caen las dos muñecas**, o sea el que
nunca deja al motor sin señal. Cuadros sin ninguna muñeca, por umbral:

| umbral | 0,40 | 0,45 | 0,50 | 0,55 | 0,60 | 0,65 |
|---|---|---|---|---|---|---|
| cuadros sin muñeca (los 5 clips) | 0 | 0 | 0 | **0** | 3 | 24 |
| racha más larga | 0 | 0 | 0 | **0** | 1 | **5** (`vid1`) |

De ahí **0,55**. En 0,65 la racha de 5 cuadros de `vid1` ya no se rellena y el
top se va a 570: el umbral tiene un techo medido, y está a dos décimas.

### 2 · Los cinco clips y el mocap: el peso y el umbral, separados

Recalculado desde el `pose.npz` guardado (invariante 1: no se volvió a correr el
modelo para esto) y confirmado de punta a punta con `datos` (§6). Tres columnas
porque **son dos cambios y hacen cosas distintas**: `igual` es como estaba (las
dos muñecas pesan lo mismo), `pesado` agrega el peso por confianza sin umbral, y
`umbral` es lo que queda hoy.

| clip · vista | address | top `igual` | top `pesado` | **top `umbral`** | referencia |
|---|---|---|---|---|---|
| `cortado.mp4` `face_on` | 7 | 33 | 33 | **35** | 36 |
| `20260907_170638.mp4` `face_on` | 111 | 137 | 137 | **139** | 139 |
| `vid1.mp4` `face_on` | 672 | 722 | 722 | **722** | 722 |
| `vid2.mp4` `face_on` | 58 | 115 | 115 | **115** | 114 |
| `vid3.mp4` | — | 0 repeticiones en los tres modos | | | — |
| mocap 64_01 `face_on` | 141 | 270 | 270 | **270** | 269 |
| mocap 64_01 `down_the_line` | 146 | 263 | 263 | **263** | 269 |

**El peso por confianza, solo, no mueve ningún top.** Ni uno, en ninguno de los
siete casos. Lo que mueve el top es el **umbral**, y tiene sentido: con 0,36
contra 0,67 la muñeca perdida todavía se lleva un 35 % del promedio, y un 35 % de
un salto de 300 px son 105 px. Pesar reparte; hace falta decidir.

**El error contra la señal limpia pasa de −3 / −2 / 0 / +1 a −1 / 0 / 0 / +1.**
`20260907` cae **exactamente** en el cuadro de la referencia.

**El `follow_end` es donde más se nota**, porque sale de la misma quietud:

| clip | `igual` | `pesado` | **`umbral`** | referencia |
|---|---|---|---|---|
| `20260907_170638.mp4` | 219 | 232 | **188** | 188 |
| `vid1.mp4` | 842 | 931 | **931** | 930 |

Los dos terminan en el cuadro de la señal limpia. En `20260907` eso son 31
cuadros —1,03 s— de follow-through que antes se contaban de más.

**El mocap no se mueve en ningún modo ni en ninguna vista.** Es el control del
cambio: sus scores valen 1,000 en todos los cuadros, así que pesar por confianza
y filtrar por umbral tienen que ser la identidad, y lo son hasta el último
cuadro. Si algo del mocap se hubiera movido, el peso estaría haciendo otra cosa
que pesar.

**Address e impacto no se movieron en ningún clip**, aunque salgan de la misma
señal. El instante **sub-cuadro** del impacto sí se corre, porque mira la
trayectoria cruda, pero **por debajo de su propio MDC en los cuatro clips**:

| | `cortado` | `20260907` | `vid1` | `vid2` |
|---|---|---|---|---|
| fracción `igual` → `umbral` | 0,4404 → 0,4508 | 0,4181 → 0,4201 | 0,2144 → 0,1782 | 0,9493 → 0,9046 |
| en ms | **0,35** | **0,07** | **0,60** | **0,74** |

Contra un MDC de 2,927 ms: el mayor es el 25 % de su mínimo detectable. La señal
cambió y el instante del impacto, en la práctica, no.

### 3 · La banda: `vid1` es el único clip que la enciende, y era el que había que agarrar

Los candidatos a top de cada clip, con su excursión desde el address, el ruido
medido del clip y el margen de 2 σ:

| clip | σ_px | 2σ | candidatos (cuadro: px desde el address) | gana | rivales | **tol** |
|---|---|---|---|---|---|---|
| `cortado.mp4` | 1,65 | 3,30 | 11: 21,0 · **35: 599,5** | 35 | — | 1 |
| `20260907` | 6,26 | 12,52 | 112: 3,1 · **139: 615,5** | 139 | — | 1 |
| **`vid1.mp4`** | **4,70** | **9,41** | 679: 28,5 · 681: 51,7 · **722: 590,9** · 725: 587,7 · 726: 588,5 | 722 | **725, 726** | **4** |
| `vid2.mp4` | 3,36 | 6,73 | 66: 30,4 · 69: 47,6 · **115: 665,9** | 115 | — | 1 |
| mocap `face_on` | 1,09 | 2,18 | 144: 1,3 · **270: 794,9** | 270 | — | 1 |
| mocap `down_the_line` | 0,84 | 1,68 | 158: 5,4 · **263: 756,2** · 327: 89,1 | 263 | — | 1 |

Es exactamente el caso que el 15 dejó abierto: en `vid1` el ganador se lleva el
top por **2,2 px** sobre el cuadro 726 y **3,2 px** sobre el 725, con 4,70 px de
ruido por cuadro. Antes eso salía con `tol_frames` 1, como si no hubiera duda.
Ahora sale con **4**, y se propaga:

| `vid1.mp4` | antes | después |
|---|---|---|
| `tempo_ratio` | 2,632 **[2,45 · 2,83]** | 2,632 **[2,0 · 3,6]** |

El resto de las duraciones de los clips reales siguen en `null` por `fps_min`
120 (ADR-016: los cinco vienen de caminos declarados), así que `tempo_ratio` de
`vid1` es hoy **el único número del proyecto donde la banda se ve**. En el mocap,
a 120 fps y con la elección clara, las duraciones no se movieron ni un dígito:
backswing 1075,0 [1066,7 · 1083,3] y downswing 491,7 [483,3 · 500,0] en
`face_on`.

**El σ no es el mismo número que citaba el 15** (2,27 px en `vid1`) por dos
razones, las dos comprobadas: aquél era `subframe.components.noise_px`, el σ a lo
largo de la dirección de viaje de las manos en el impacto, y éste es el mismo
estimador aplicado a los **dos ejes de imagen** y combinado en cuadratura, que es
lo que corresponde para comparar excursiones —una distancia, no una proyección—;
y además la señal ya no es la misma (con el centro a peso igual, `vid1` da
**2,274 px**, que reproduce exactamente el número del 15). Sale más grande, o sea
la banda es más ancha. Ante la duda, la banda ancha.

La banda **no depende del cambio de señal**: `vid1` da `tol_frames` 4 en los tres
modos de §2. Los dos cambios de este encargo son independientes.

### 4 · El MDC del sub-cuadro llegó al evento

`events[].impact.subframe.mdc` = `{value: 2.927, unit: "ms", provenance:
"medido_aqui", source: "sports/golf/mdc.yaml §events.impact.subframe (arnés,
nivel 0, 16 semillas)"}`, en los siete clips, **también cuando el cruce sale
`null`** (desde `down_the_line`, invariante 6): el MDC describe al estimador, no
a esta toma, y un campo esperado nunca se omite. El valor sigue con su
`provenance: estimacion` al lado: el MDC está medido, el número no.

Contra la banda que el motor declara por clip: 2,927 ms de MDC contra ±1 cuadro
entero, que a 30 fps son 33,3 ms (**11×**) y a 60 fps 16,7 (**5,7×**).

### 5 · Lo que el umbral cuesta, medido

Dejar una muñeca afuera no sólo saca su error: **cambia de estimador a mitad de
la señal**. El centro de las dos pasa a ser la otra sola, o sea un escalón de
**media empuñadura** mientras dura la racha. Aislado en el swing sintético
—muñeca izquierda intacta, sólo el score bajado a 0,36 durante 9 cuadros— el top
se corre **5 cuadros a 120 fps y 8 a 240**, con las muñecas a 12 px entre sí.

Con el daño posicional realista encima (corrimiento sostenido de 250 px más
ruido, que es el modo de falla medido en `cortado`), el umbral **siempre** gana:

| | top con umbral | top sin umbral |
|---|---|---|
| 120 fps | **−1** | −11 |
| 240 fps | **−9** | −15 |

El sintético lo exagera porque su top es una vuelta muy plana; sobre los clips
reales el efecto total fue de 1 a 2 cuadros y **siempre hacia** el cuadro que da
la muñeca limpia sola. Los dos números están fijados con tests, para que el
escalón no crezca sin que nadie se entere.

### 6 · De punta a punta, corriendo el modelo otra vez

`python -m kinelab datos` sobre los cinco clips: **los mismos cuadros** que el
recálculo desde el `pose.npz` guardado, en los cinco. `cortado` top 35 (1,167 s),
`20260907` top 139 (4,634 s) y follow_end 188 (6,267 s), `vid1` top 722 con
`tol_frames` 4, `vid2` top 115, `vid3` sin repeticiones. El `analysis.json` de
`vid1` sale con `uncertainty.method` = *"±4 cuadro(s) en cada evento ancla a
60.026 fps (sin_verificar)"*, que es la banda diciendo su propio nombre.

## Queda abierto

1. **El escalón de media empuñadura** (§5). Corregirlo sería estimar el medio
   vector de la empuñadura donde las dos muñecas están, e interpolarlo por la
   racha —el mismo relleno acotado, aplicado al vector y no a la posición—. No se
   hizo: es un estimador nuevo, el prompt no lo pedía, y ese medio vector es
   justo lo que más rota en el top, que es donde haría falta. **Decisión del
   orquestador.**
2. **`web/src/components/Metricas.tsx:42` rotula la banda como «±1 cuadro» en
   texto fijo.** Con el `tol_frames` 4 de `vid1` ese cartel **dice algo falso**:
   la banda que muestra al lado es de ±4. No es archivo de este encargo (ni del
   16, que también lo anotó) y el front no se abre. Es de una línea.
3. **`kinelab/events/order.py` (`sequence_order`) quedó huérfano**: el 16 borró
   `events[].sequence_order` del contrato y su único importador
   (`kinelab/metrics/generic.py`). El archivo está en mi directorio y **no lo di
   de baja**: borrarlo antes de que el 16 cerrara habría roto el árbol. Es un
   `git rm` y sacar su test de `tests/test_fase2.py`.
4. **La exploración por cuadro no usa la señal nueva.** `kinelab/explore.py:165`
   llama `swing_signals(pose, fps)` sin deporte, así que la columna
   `hands_x_vs_hip_bh` del CSV y el dibujo del overlay siguen con el centro a
   peso igual, mientras los eventos del mismo archivo salen de la señal pesada.
   Es `kinelab/explore.py`, del 16. Dos números que no coinciden en la misma
   pantalla es de las cosas que más caro se pagan después.
5. **El error del top sigue sin medirse contra GolfDB** (ESPECIFICACION 2.5).
   Cinco clips de un golfista y dos trials de un sujeto de mocap no son una
   tabla; la «referencia» de este informe es la muñeca derecha sola, que es una
   segunda señal, no una verdad.
6. **Las tomas ya analizadas conservan su top viejo** hasta que se re-analicen
   (invariante 18). Las 17 de `data/exploracion/` no se rehicieron.

## Preguntas para el orquestador

- **¿Se corrige el escalón de media empuñadura** (abierto 1), se deja medido y
  documentado, o se acota bajando el umbral? Hoy está medido en 5–8 cuadros en el
  sintético y 1–2 en los clips reales.
- **¿El `tol_frames` del top tiene que llegar al entrenador como banda visible**,
  además de a la incertidumbre de las métricas? Hoy el JSON lo lleva y la
  pantalla dice «±1 cuadro» en texto fijo (abierto 2).
- **¿La señal de la exploración por cuadro se unifica con la de los eventos**
  (abierto 4)? Es del 16, pero la decisión no es suya.
- **¿Alguien da de baja `kinelab/events/order.py`** (abierto 3)?

## Para que pruebe Hernán

No hay front en este encargo: no se abrió ni se tocó `web/` ni `service/`. En la
terminal:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/20260907_170638.mp4 --altura-m 1.75
```

1. En la salida, el **top tiene que dar el cuadro 139** (4,633 s). Antes era el
   137. Y el `follow_end`, el 188 y no el 232.
2. Abrí `~/Desktop/20260907_170638.kinelab/evento-top.png`: el palo arriba del
   todo. Y `evento-follow_end.png`, que antes agarraba al jugador ya quieto 1,5 s
   después de terminar.
3. En `~/Desktop/20260907_170638.kinelab/datos-eventos.json`, el impacto tiene
   ahora un `subframe.mdc` de **2,927 ms**: cuánto tiene que cambiar el instante
   del impacto entre dos tomas para que el cambio sea del jugador y no del
   instrumento.

Y el clip donde se ve la banda:

```bash
.venv/bin/python -m kinelab datos data/incoming/vid1.mp4 --altura-m 1.75
```

4. El top sigue en el cuadro 722, pero ahora dice `tol_frames: 4`: hay otros dos
   cambios de sentido a 2,2 y 3,2 px de excursión, contra 4,7 px de ruido. El
   motor elige igual, pero ya no finge que no había duda.
5. El `tempo_ratio` sale 2,632 con banda **[2,0 · 3,6]** en vez de [2,45 · 2,83].
   Esa es la banda del top propagada a la métrica.
