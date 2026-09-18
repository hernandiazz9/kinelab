# deriva-de-camara-censo — 2026-09-18

Resumen: existe `kinelab/tools/camera_drift.py`, que mide cuánto se corre la imagen
durante el gesto y **no compensa nada**. En `cortado3-lento.mp4` reproduce la auditoría
del 16/9 en x: rep 1 **+13,5 a +22,2 px** contra su rango +14 a +23 (el mínimo queda
0,5 px afuera, dentro de los ±3 px de aceptación) y rep 2 **−10,1 a −22,1 px** contra
−8 a −25 — **aceptado**. Lo que la auditoría subestimó es la **y**: dice «unos 10 px» y
son **−26,3 a −29,8 px** en el impacto de la rep 1, o sea **5,9–6,7 cm** con la
`scale_px` de esa toma, **2,1–2,4×** el MDC de `pelvis_lift_top_cm` (2,769 cm). El censo
de los 8 clips va de ≤5,2 px (`cortado`, 76 cuadros) a **+119 px** (`vid1`): la deriva
no es una rareza de un clip. Los controles descartan la fuga de máscara (el número no
crece con el movimiento del sujeto) y la dependencia del cuadro de referencia (≤0,4 px),
y dejan **sin separar** la causa: la mitad superior y la inferior de la imagen coinciden
en la rep 1 y difieren 13–17 px en la rep 2, pero la superior tiene un tercio de los
inliers y evaluarla en la fila de los pies es extrapolar 800 px. `no_rigido` se marcó
**1 vez en 9 clips**. Decisión abierta: qué se hace con `quality.camera_motion_px`, que
sigue dando 1,347 en la toma que deriva 43 px.

Encargo: una herramienta agnóstica al deporte que mida la deriva de cámara sobre el fondo
con el sujeto enmascarado, el censo de los ocho clips reales, dos controles que separen
causas, y tests con bugs inyectados. Medir, no compensar.

Hecho (commits `83c152f` el código y sus tests, y el de cierre con `ESTADO.md` y este informe):

- **`kinelab/tools/camera_drift.py`** (nuevo, 1 archivo). Homografía del fondo entre un
  cuadro de referencia y cada cuadro muestreado: SIFT con el sujeto enmascarado (`bbox`
  de `pose.npz` dilatado 20 % + un disco sobre las muñecas de radio 0,65 altos de cuerpo,
  que cubre el palo), ratio test de Lowe y RANSAC. Del modelo salen `dx`/`dy` en **cuatro
  filas** —caderas, hombros, cabeza, pies del cuadro de referencia— sobre la columna del
  sujeto. Cuatro y no una está medido: en `cortado3-lento` hay **8,7 px** entre la fila de
  la cabeza (+22,2) y la de los pies (+15,3) en el mismo cuadro.
- **Escribe `camera-drift.json` al lado de la pose y nada más.** No toca `analysis.json`
  ni `pose.npz` (hay un test que lo verifica por hash de bytes), ninguna métrica lo lee, y
  no se cambió `camera_motion_px` ni ninguna métrica.
- **`no_rigido` mira dos cosas y no una.** El residuo de los inliers está acotado por
  `--ransac-px` por construcción, así que casi no puede pasar un umbral: medido sobre los
  fondos sintéticos del test, una deformación que ninguna homografía puede seguir lo sube
  de **0,00 a 1,98 px** mientras la **fracción de inliers cae de 1,00 a 0,76**. La regla
  es `residuo_px > 1,5` **o** `inliers_frac < 0,80`, las dos procedencia `estimacion`, y
  `no_rigido_por` dice cuál fue. Es la única desviación del prompt (ver §Queda abierto).
- **Controles que la herramienta soporta**, porque son parte del encargo: `--region
  superior|inferior`, `--sin-palo`, `--dilatacion`, `--palo-radio`, `--ref`, y `--dibujar
  FRAME`, que escribe el cuadro con el fondo enmascarado a la vista y los inliers
  dibujados.
- **`tests/test_camera_drift.py`** (nuevo, 18 tests). Todo contra transformaciones
  construidas en el propio test (una traslación de 3,0/1,5 px, una rotación con zoom, un
  fondo quieto, una deformación no rígida), nunca contra números de una corrida anterior.
- **`data/incoming/cartado2-lenta.kinelab/`**: se corrió `datos` porque era el único clip
  sin pose. No tiene eventos (es el clip del cronómetro detenido; 0 repeticiones).

## Probado

**Suites.** Motor **381 pasados, 0 fallados, 0 errores, 0 saltados, exit 0** (eran 363:
+18 tests, ninguna aserción existente tocada). Arnés **43 pasados, 0 fallados, exit 0**
—no se tocó `truth/`; se corrió para confirmar que el arreglo del 30 sigue en pie—.

**Mutación manual: 7 bugs inyectados, 7 en rojo, control en verde.** Los dos que pedía el
prompt y cinco más:

| bug inyectado | tests en rojo |
|---|---|
| **máscara invertida** (`m = 255 − m`) | **9** de 18 |
| **homografía evaluada en la fila equivocada** (ignora `fila`) | **5** |
| homografía al revés (`src`/`dst` cambiados) | 6 |
| la resta entre eventos vuelta suma | 1 |
| `no_rigido` sólo por residuo | 2 |
| el disco del palo no se dibuja | 1 |
| `dx` y `dy` intercambiados | 5 |
| **control, sin mutar** | **0** (18 en verde) |

Dos huecos que la mutación encontró y se taparon: con el `address` sintético en el cuadro
de referencia su deriva era cero y **restar o sumar daba lo mismo** (la mutación pasaba en
verde) — el `address` del clip de test se movió al cuadro 4; y el disco del palo no lo
defendía ningún test de resultado, porque apagarlo mueve la deriva ≤ 0,81 px — se agregó
un test de la **geometría** de la máscara.

### El censo, `--cada 10`, parámetros por defecto, referencia = primer cuadro con pose

```
python -m kinelab.tools.camera_drift <video> --pose <dir>/pose.npz --cada 10
```

| clip | cuadros | muestras | fondo libre | max \|dx\| | max \|dy\| | residuo | inliers med | frac mín | `no_rigido` | s |
|---|---|---|---|---|---|---|---|---|---|---|
| `Cortado-lenta` | 598 | 63 | 87 % | +15,3 (c 580) | +21,7 (c 590) | 0,31 | 849 | 0,99 | 0 | 7 |
| `cartado2-lenta` | 292 | 30 | 83 % | +10,2 (c 290) | −6,3 (c 290) | 0,25 | 710 | 0,99 | 0 | 4 |
| `cortado3-lento` | 2977 | 304 | 66 % | **−43,1** (c 2930) | **−41,0** (c 2970) | 0,39 | 162 | 0,91 | 0 | 33 |
| `vid1` | 1066 | 110 | 80 % | −46,7 (c 150) | **+119,4** (c 190) | 0,42 | 660 | 0,98 | 0 | 56 |
| `vid2` | 292 | 33 | 78 % | +30,8 (c 120) | −46,3 (c 180) | 0,27 | 954 | 0,99 | 0 | 18 |
| `vid3` | 189 | 19 | 76 % | −17,7 (c 180) | +23,4 (c 180) | 0,24 | 773 | 1,00 | 0 | 11 |
| `cortado` | 76 | 11 | 53 % | −4,4 (c 70) | −5,2 (c 60) | 0,29 | 267 | 0,93 | 0 | 2 |
| `20260907_170638` | 265 | 30 | 49 % | −30,0 (c 260) | **−135,0** (c 260) | 0,25 | 250 | **1** | 1 | 4 |
| `take-01` (`data/sessions/`) | 2977 | 304 | 66 % | −43,1 | −41,0 | 0,39 | 162 | 0,91 | 0 | 32 |

`take-01` es el mismo `cortado3-lento` y da **exactamente los mismos números**, que es lo
que tenía que pasar: la pose es la misma.

**Desplazamiento entre eventos**, rango sobre las cuatro filas (px):

| clip | rep | address→top, dx | address→impacto, dx | address→impacto, dy |
|---|---|---|---|---|
| `cortado3-lento` / `take-01` | 1 | **+13,5 a +21,9** | **+15,3 a +22,2** | **−29,8 a −26,3** |
| `cortado3-lento` / `take-01` | 2 | −12,2 a −10,1 | **−22,1 a −16,1** | −10,2 a −6,5 |
| `Cortado-lenta` | 1 | +3,8 a +7,6 | +6,5 a +9,6 | +12,2 a +13,1 |
| `vid1` | 1 | +14,2 a +16,2 | +27,9 a +31,3 | +25,2 a +26,3 |
| `vid2` | 1 | +24,5 a +27,2 | +21,2 a +25,1 | −28,0 a −27,1 |
| `cortado` | 1 | −1,3 a −0,4 | −0,1 a +1,0 | −3,2 a −3,1 |
| `20260907_170638` | 1 | −0,9 a +0,0 | +0,7 a +2,0 | −2,7 a −2,4 |
| `cartado2-lenta`, `vid3` | — | sin eventos | | |

### Contra la auditoría: aceptado en x, y la y era más grande

El criterio del prompt es estar dentro de ±3 px de los rangos de la auditoría.

| | auditoría | medido acá | ¿entra? |
|---|---|---|---|
| rep 1, x | +14 a +23 px | **+13,5 a +22,2** | sí (el mínimo, 0,5 px afuera) |
| rep 2, x | −8 a −25 px | **−10,1 a −22,1** | sí, entero |
| y | «unos 10 px» | **−26,3 a −29,8** en el impacto de la rep 1 | **no** |

**El x se reproduce; la y de la auditoría se queda corta por un factor 2,5–3.** Con la
`scale_px` de esa toma (783,9 px para 1,75 m, o sea 4,479 px/cm):

| | px | cm | MDC de la métrica que contamina | veces el MDC |
|---|---|---|---|---|
| rep 1, address→impacto, x | +15,3 a +22,2 | **3,4 a 5,0** | `pelvis_sway_impact_cm` 2,416 | 1,4–2,1× |
| rep 1, address→impacto, y | −26,3 a −29,8 | **−5,9 a −6,7** | `pelvis_lift_top_cm` 2,769 | 2,1–2,4× |
| rep 1, address→top, x | +13,5 a +21,9 | 3,0 a 4,9 | `pelvis_sway_top_cm` 2,841 | 1,1–1,7× |
| rep 2, address→impacto, x | −16,1 a −22,1 | −3,6 a −4,9 | `pelvis_sway_impact_cm` 2,416 | 1,5–2,0× |

Y el motor no lo ve: `quality.camera_motion_px` de esa misma toma es **1,347**.

### Los dos controles que separan causas

**(a) Mitad inferior (suelo) contra mitad superior (fondo lejano).**

| | fondo libre | cuadros con modelo | inliers med | rep 1, impacto, caderas | rep 2, impacto, caderas |
|---|---|---|---|---|---|
| `todo` | 66 % | 304/304 | 162 | **+18,5** | **−19,3** |
| `--region inferior` | 34 % | 304/304 | 121 | +17,8 | −18,6 |
| `--region superior` | 32 % | **237/304** | **53** | +17,9 | **−2,1** |

- **En la rep 1 las tres coinciden dentro de 0,7 px.**
- **En la rep 2 la mitad superior da −2,1 donde las otras dos dan −19.** 17 px de
  diferencia, y en el top −11,0 contra +2,0.
- **No alcanza para concluir paralaje.** La mitad superior tiene un tercio de los inliers,
  falla en 67 cuadros, y el sujeto ocupa de y=551 a y=1512 en un cuadro de 1920: su fondo
  útil es casi todo y<551, así que evaluar su modelo en la fila de los pies (y=1326) es
  **extrapolar ~800 px** fuera del soporte. Lo delata que su `max |dy|` sea **+904,7 px**
  en el cuadro 1380, que no es una medición de nada.
- Lo que sí queda dicho: **el número de `todo` es esencialmente el de la mitad inferior**
  (0,7 px de diferencia, y 121 de sus 162 inliers están ahí). La deriva que hoy se reporta
  es la del **suelo**, no la del fondo lejano.

**(b) Address (sujeto quieto) contra downswing (sujeto rápido).** Rep 1, referencia = el
address 1052, deriva de la fila de caderas cuadro a cuadro, residuo rms contra una recta:

| ventana | n | velocidad de manos | rango de dx | residuo rms x / y | inliers med |
|---|---|---|---|---|---|
| address 992–1052, quieto | 16 | 1,3 px/cuadro | −3,1 a 0,0 | **0,10** / 0,12 | 544 |
| backswing 1060–1284 | 19 | 3,0 | +0,9 a +17,7 | 0,53 / 2,42 | 267 |
| downswing 1288–1364 | 20 | **8,8** | +16,8 a +18,4 | **0,23** / 1,25 | 184 |
| follow 1368–1460 | 24 | 8,2 | +15,7 a +18,5 | 0,29 / 0,62 | 428 |

**La máscara no deja pasar al sujeto:** las manos van 6,8× más rápido en el downswing que
en el address y el residuo en x pasa de 0,10 a 0,23 px. (El 2,42 del backswing es la
curvatura de la propia deriva sobre una ventana de 225 cuadros ajustada con una recta, no
ruido.) Dos confirmaciones más, cuadro a cuadro sobre el downswing:

- **apagar el disco del palo** (`--sin-palo`, 75 % de fondo libre, 570 inliers contra 185)
  mueve la deriva **≤ 0,81 px**;
- **agrandarla** a `--dilatacion 0.60 --palo-radio 0.95` (33 % libre, **21 inliers**)
  agrega ±5 px de dispersión, y con `1.0 / 1.2` (18 % libre) los cuadros de address se
  quedan **sin modelo**. Eso es acondicionamiento, no fuga.

**(c) Control extra, no pedido: el cuadro de referencia no manda.** Con `--ref 1052` en
vez del cuadro 0, los ocho números de eventos de `cortado3` cambian **≤ 0,4 px**
(rep 1 impacto caderas +18,5 → +18,4; rep 2 −19,3 → −19,2). Cada homografía se estima
contra la referencia por separado, así que la resta no cancela nada por construcción: que
coincida es una medición.

### Lo demás que apareció en el censo

- **`vid1` tiene la deriva más grande del repo y es real**: `dy` sube suave de 0 a
  **+119,4 px** entre los cuadros 0 y 190 y vuelve, con **366–1058 inliers** y residuo
  0,27–0,67 px. Un fondo que se mueve así con mil inliers de acuerdo es la cámara, no un
  artefacto.
- **`20260907_170638` cuadro 260** es el único `no_rigido` de los nueve clips: `dy`
  −129 px, `inliers_frac` 0,80 — el final del clip, con el teléfono ya moviéndose.
- **`cortado.mp4` es el recorte de `20260907_170638.mp4`** y los dos dan la misma deriva
  del swing: address→impacto `dy` −3,1 contra −2,4 px. Es el clip más quieto del repo.
- **`Cortado-lenta` y `cortado3-lento` son del mismo día y el mismo modo** y derivan
  distinto: +6,5/+9,6 px contra +15,3/+22,2 en x. El trípode no se comporta igual entre
  tomas.

## Queda abierto

- **La causa no está separada, y era el objetivo del control (a).** Lo que hoy se puede
  afirmar es que el fondo se mueve, que el modelo de un solo plano le ajusta bien
  (residuo 0,24–0,42 px con 162–954 inliers en los nueve clips) y que el número publicado
  es el del suelo. Si es estabilización electrónica, trípode o paralaje lo tiene que
  separar la sesión de validación, con la toma de escena vacía y el objeto fijo en el
  suelo que pide `docs/filmacion-s22.md` §7.
- **El residuo no rígido de 10–12 px que reportó la auditoría en la rep 2 no aparece acá.**
  Con el sujeto enmascarado, una sola homografía ajusta el fondo con **0,39 px** de
  mediana sobre 162 inliers. O la auditoría medía otra cosa (la discrepancia entre sus
  tres métodos era 3–6 px), o vive en la mitad de la imagen que este método no puede
  evaluar sin extrapolar.
- **Desviación del prompt, una: `no_rigido` mira dos condiciones y no una.** El prompt
  pedía «una bandera `no_rigido` cuando el residuo supera un umbral». El residuo de los
  inliers no sirve solo para eso —RANSAC lo acota por construcción— y está medido arriba.
  Se dejó el residuo como primera condición, como pedía el prompt, y se le sumó la
  fracción de inliers, que es la que separa. Las dos son `estimacion` y las dos se pueden
  cambiar por CLI. **Del contrato no hay desviación**: no entra ni sale ningún campo de
  ningún schema, ningún valor cambia.
- **`quality.camera_motion_px` no se tocó** (lo prohibía el prompt). Sigue dando **1,347**
  en la toma que deriva 43 px, y no está mal: mide otra cosa —la mediana del corrimiento
  entre muestras cada 120 cuadros a 320 px—. El problema es el **nombre**: quien lee
  `camera_motion_px: 1.347` concluye que la cámara está quieta. Recomendación abajo.
- **El `--cada 10` por defecto sobre 2977 cuadros son 304 muestras y 33 s.** Para el
  análisis fino hay que bajarlo (el control (b) usó 2 y 4). No se propone cambiar el
  default.
- **No se tocó** `kinelab/perception/`, `kinelab/analysis.py`, `kinelab/metrics/`,
  `sports/`, `service/`, `web/`, `truth/`, ningún `analysis.json` ni ningún umbral. **No
  se compensó nada en ninguna métrica** y **no se volvió a correr el modelo de pose** salvo
  en `cartado2-lenta.mp4`, que no tenía (lo autorizaba el prompt). El front no se abrió.

## Para que mire Hernán

No hay front. Si querés ver de qué se está hablando, dos imágenes de `cortado3-lento`,
las dos ya escritas en disco:

```bash
open data/incoming/cortado3-lento.kinelab/camera-drift-1052.png data/incoming/cortado3-lento.kinelab/camera-drift-1364.png
```

- **`camera-drift-1052.png`** es el address de la rep 1 contra sí mismo: las cuatro flechas
  miden **+0,0 / +0,0 px** y 1181 de 1181 emparejamientos son inliers. Es el control: si
  ahí saliera algo distinto de cero, todo lo demás sería ruido.
- **`camera-drift-1364.png`** es el impacto. Lo oscurecido es lo enmascarado —vas a ver
  que el disco del palo lo cubre entero—, las líneas verdes son los emparejamientos de
  fondo que se usaron (**492 de 494**), y las flechas magenta son el desplazamiento de
  cada fila **amplificado ×10**: cabeza +22,0/−28,2 px, pies +15,0/−29,1 px. Que las
  cuatro flechas no sean iguales es el punto: la imagen no se corrió en bloque.

Y el número que importa mirar: **el fondo de ese cuadro está corrido 22 px respecto del
address, o 4,9 cm de cuerpo, y `analysis.json` dice `camera_motion_px: 1.347`.**

## Preguntas para el orquestador

1. **`quality.camera_motion_px`: ¿muere, se renombra, o se queda con la deriva al lado?**
   Medido: 1,347 en una toma que deriva 43 px. No miente —mide sacudones entre muestras
   cada 120 cuadros— pero su nombre afirma lo contrario de lo que pasa. Recomiendo
   **renombrarlo a `camera_jitter_px`** y que el campo de deriva entre en el mismo bump
   (2.2.0) que ya tiene encargo propio. Renombrar un campo es **major** por §Versionado,
   así que la decisión es del orquestador y no de una sesión.
2. **¿Se corrige la auditoría del 16/9 en la y?** Su §1 dice «unos 10 px en y» y son
   26–30 px en el impacto de la rep 1, o sea 5,9–6,7 cm, **2,1–2,4× el MDC** de las
   métricas de `lift`. La conclusión de la auditoría —ningún juicio resiste— no cambia; el
   número sí, y está citado en `DECISIONES.md` ADR-019 como «la imagen deriva 8–25 px».
3. **La regla de `no_rigido` con dos condiciones**: ¿se confirma como quedó, o se quiere
   una sola? Los números que la justifican están arriba.
4. **El control (a) quedó sin concluir por falta de fondo lejano utilizable**, no por el
   método. Para separar paralaje de estabilización hace falta la toma de escena vacía de
   `docs/filmacion-s22.md` §7 — **y conviene agregarle un objeto fijo alto**, no sólo el
   del suelo, o la mitad superior va a seguir sin tener con qué.
