# mascara-del-sujeto — 2026-09-20

Resumen: la máscara clásica **compra el palo en el top y nada más**. Con fondo estabilizado
+ mediana temporal + umbral por MAD, en `cortado3-lento` la recta ajustada al shaft en los
**10 cuadros del top** coincide con la etiqueta a ojo en **0,9° de mediana y 1,6° de máximo,
10 de 10 por debajo de 5°**; en los **10 del impacto** el error es **66° de mediana** y
**0 de 8** bajan de 5°. La causa no es el método: **a 240 fps el shaft del impacto ya es un
borrón que a ojo tampoco se puede marcar** (2 de 10 cuadros ni siquiera tienen etiqueta), y
en `vid1` (UHD 60) **no se ve en ninguno de los 5**. El cuerpo entero no lo compra: la
cobertura del bbox es 0,38 / 0,42 / 0,18 en los tres clips y los keypoints adentro de la
máscara 62 % / 77 % / 27 %, porque **el golfista nunca se corre del lugar y detrás de él no
hay fondo** (1,9 % del cuadro sin modelo en `cortado3-lento`, 6,1 % en `cortado`). La escala
tampoco: la extensión vertical da **1,165–1,181** contra la cadena cuando de coronilla a
suela daría 1,044 — **12 % de más**, y el pie que no se mueve directamente no entra en la
máscara. Cuesta **68 ms/cuadro en FHD y 407 en UHD**, más 27–72 s de modelo de fondo.
**Recomendación: no abrir un encargo de producto del shaft como evento.** Lo que falta no es
un modelo de segmentación —ninguno inventa píxeles que el obturador no registró— sino un
obturador más corto, que es lo que `CAPTURA.md` §Luz ya pide y nadie midió todavía.

Encargo: medir, en vez de discutir, qué compra y qué cuesta una máscara del sujeto: la
silueta, el palo contra etiquetas a ojo, la escala en cm, y la robustez en dos clips más.
Todo en `banco/`, sin tocar el motor y sin instalar nada.

## Hecho

- **`banco/mascara_sujeto.py`** (nuevo, 1 archivo, ~1.050 líneas con su docstring). Script de
  banco: nada de `kinelab/` lo importa, no escribe en `analysis.json` ni en `pose.npz`, y no
  corre pose sobre nada. **Reusa** `kinelab.tools.camera_drift` (`mascara`, `estimar`,
  `alto_cuerpo_px`, `primer_cuadro_con_pose`, `Params`) en vez de copiarla, más
  `perception.video.iter_frames` y `perception.posestore.load_pose`.
- El método, en cuatro piezas: **estabilizar** cada cuadro contra el de referencia con la
  homografía del fondo del 29; **mediana temporal por píxel** descartando de cada muestra los
  píxeles donde la pose dice que está el sujeto; **umbral por píxel**
  `max(12, 3 · 1,4826 · MAD)` con el MAD temporal del propio modelo; y **dos máscaras** del
  mismo umbral: la del sujeto (con cierre) y la **fina** (lo que no sobrevive a una apertura
  del grosor de un brazo, menos la silueta de la pose).
- **El palo** se busca con una **Hough anclada en las muñecas** —el ángulo que junta más
  píxeles finos en una banda que pasa por la mano— y se refina con `cv2.fitLine` (Huber) en
  tres vueltas, re-eligiendo los inliers con la recta ya suelta. Anclar es lo que aguanta que
  el shaft salga punteado; soltar después es lo que recupera la punta: sin las tres vueltas el
  largo ajustado en los diez cuadros del top (fondo local) daba **118–177 px** contra los
  **383–421** que da con ellas, sobre un shaft de ~360 px etiquetados.
- **Dos modelos de fondo, y los dos hacen falta**: el **global** (64 cuadros de todo el clip,
  con el sujeto enmascarado) y el **local** (±0,5 s alrededor del evento, **sin** enmascarar,
  así el cuerpo casi quieto entra al modelo y lo único que queda de primer plano es lo rápido).
- **Todas las etiquetas a ojo son `estimacion`**, hechas por la sesión mirando los PNG, con su
  precisión declarada (±10 px por extremo) y su convención escrita en el JSON. No se las llama
  medición en ningún lado.
- Salidas en `data/incoming/<clip>.kinelab/mascara/` (ignorado por git): `mascara.json` con
  todos los números, `etiquetas.json`, `fondo-global.png`, `sin-fondo.png`,
  `palo-{global,local}-<cuadro>.png` con las dos rectas dibujadas, `escala-<cuadro>.png` y
  `recorte-<cuadro>.png` con grilla para etiquetar.

Commits: el del script, y el de cierre con `ESTADO.md` y este informe.

## Probado

**Suite del motor**: `.venv/bin/pytest -q` → **390 pasados, 0 fallados, exit 0** (sin cambios:
no se tocó `kinelab/`, `sports/`, `service/`, `web/` ni `truth/`).

### 1. La máscara clásica, los tres clips

```bash
.venv/bin/python banco/mascara_sujeto.py data/incoming/cortado3-lento.mp4 \
  --pose data/sessions/hernan/2026-09-15/driver/face_on/take-01 --cada 10 \
  --palo 1284 --palo 1364 --palo-n 10 --escala 1584 --escala 1593 --escala 1594 \
  --escala 1595 --escala 1604 --scale-px 783.9 --recortes \
  --etiquetas data/incoming/cortado3-lento.kinelab/mascara/etiquetas.json \
  --salida data/incoming/cortado3-lento.kinelab/mascara
```

| clip | modo | cuadros · cuerpo | **sin fondo** | **cobertura del bbox** med/mín/máx | **keypoints en la máscara** med/mín | agujeros med/máx (área) | **ms/cuadro** med/máx | fondo global |
|---|---|---|---|---|---|---|---|---|
| `cortado3-lento` / `take-01` | Slow motion FHD 240 | 2977 · 688 px | **1,93 %** (39.998 px) | **0,378** / 0,256 / 0,515 | **62 %** / 42 % | 6 / 113 (6,4 %) | **68** / 126 | 64 cuadros, 27 s |
| `vid1` | Video UHD 60 | 1066 · 1104 px | **0,58 %** (47.818 px) | **0,422** / 0,274 / 0,514 | **77 %** / 62 % | 1 / 7 (1,7 %) | **407** / 513 | 48 cuadros, 72 s |
| `cortado` | Video FHD 30 | 76 · 869 px | **6,09 %** (152.470 px) | **0,182** / 0,146 / 0,238 | **27 %** / 15 % | 2 / 7 (3,8 %) | **98** / 110 | 48 cuadros, 19 s |

Cobertura evaluada cada 10 cuadros (cada 2 en `cortado`): 321, 114 y 42 cuadros. **Ninguna
homografía falló** en los tres clips, ni para el fondo ni para la evaluación. Total de punta a
punta: 148 s, 287 s y 43 s.

**El número que manda es «sin fondo»**, y es el que explica todo lo demás: son los píxeles
donde **ninguna** de las 48–64 muestras mostró la escena sin el sujeto encima. Un golfista no
se corre del lugar, así que detrás de su tronco y sus piernas **no hay fondo que restar, y no
lo va a haber nunca en ese clip**. En `cortado` —76 cuadros, 2,5 s— eso es el 6,1 % del cuadro
y la máscara colapsa (27 % de los keypoints). En `cortado3-lento` son 12,4 s reales, el sujeto
barre más superficie, y baja al 1,9 %.

**Dos decisiones del método quedaron medidas, y las dos tienen su control en el script.**

**(a) La ocupación del sujeto se dibuja desde la pose, no con el `bbox`** (`--ocupacion`, mismas
64 muestras y todo lo demás igual, `cortado3-lento`):

| `--ocupacion` | **sin fondo** | mediana del fondo |
|---|---|---|
| **`silueta`** (el método: huesos engrosados + tronco relleno + disco de cabeza) | **1,93 %** (39.998 px) | 27 s |
| `bbox` (el `bbox` de `pose.npz`, sin dilatar) | **7,76 %** (160.956 px) | 33 s |
| `bbox-y-palo` (ídem + el disco del palo del encargo 29) | **10,53 %** (218.405 px) | 51 s |

El `bbox` cuadriplica la zona sin fondo y el disco del palo la duplica otra vez, porque los dos
tapan mucho más que el sujeto. El palo **no** hace falta taparlo acá: pasa por cada píxel en uno
o dos cuadros de la muestra y la mediana no lo ve.

**(b) El modelo va en color** (`--gris` como control, `--cada 20`, mismos umbrales):

| | cobertura del bbox med | keypoints med | área de agujeros | ms/cuadro | mediana del fondo |
|---|---|---|---|---|---|
| **color** | **0,383** | **62 %** | 7,2 % | 68 ms | 30,4 s |
| `--gris` | 0,309 | 50 % | 10,9 % | 56 ms | **7,1 s** |

El color compra 7,4 puntos de cobertura y 12 de keypoints, y cuesta 4× el tiempo del modelo de
fondo. En UHD además cuesta memoria: 48 muestras en color son 1,2 GB de pila.

### 2. El palo, contra etiquetas a ojo

Rep 1 de `cortado3-lento`: 10 cuadros alrededor del top (1284) y 10 alrededor del impacto
(1364). Las etiquetas son `estimacion`, puestas por la sesión sobre los recortes con grilla
(`--recortes --recorte-radio 0.68 --recorte-zoom 1.6`), con la convención escrita en
`etiquetas.json`: **mango** = donde el shaft sale del guante, **punta** = donde entra en la
cabeza del palo. Precisión declarada ±10 px por extremo, que sobre un shaft de 360 px son
±1,6°.

| grupo | modelo de fondo | n | **error de ángulo mediano** | máximo | **< 5°** |
|---|---|---|---|---|---|
| **top** (1279–1288) | **local** | 10 | **0,9°** | **1,6°** | **10 / 10** |
| top | global | 10 | 1,0° | 83,2° | 8 / 10 |
| **impacto** (1359–1368) | local | 8 | **66,0°** | 84,4° | **0 / 8** |
| impacto | global | 8 | 72,6° | 84,0° | 0 / 8 |

En el top, con etiqueta entera (n = 10): **punta a 37 px** (máx 44), **perpendicular a 13 px**,
y el largo ajustado **+48 px** más que la etiqueta — que no es error del ajuste: la etiqueta
termina en el hosel y la recta sigue hasta la punta de la cabeza, que también está en la
máscara fina. Se ve en `palo-local-1284.png`.

Por cuadro, el top con fondo local: 177,1 · 177,7 · 178,4 · 178,8 · 178,4 · **179,0** · 179,0 ·
179,6 · 180,0 · 0,7 grados, contra 177,9 · 177,8 · 178,4 · 178,4 · 179,2 · **0,0** · 0,3 · 1,0 ·
1,6 · 1,9 a ojo. El largo ajustado va de 383 a 421 px sobre un shaft de ~360 px etiquetados.

**Los dos cuadros que el fondo global pierde son el 1281 y el 1282** (80,7° y 81,7° contra
178,4° a ojo): ahí el shaft cruza justo por la franja que el modelo global no tiene, y la recta
se va al brazo. El fondo local no los pierde. Es el argumento de tener los dos.

**En el impacto no hay nada que ajustar, y no es culpa del ajuste.** Las etiquetas a ojo lo
dicen antes que los números: en **2 de los 10 cuadros (1367, 1368) no se distingue ningún
shaft**, y en los otros 8 sólo se ve **un tramo pegado a la mano** —por eso están marcados
`parcial`— con la cabeza del palo deshecha en el borrón. El ajuste devuelve rectas de
**41–104 px** en nueve de los diez cuadros (y una de 331 en el 1365) donde el shaft proyectado
mide del orden de 400, y el ángulo que sale es el de otra cosa: el brazo, el borde del short.

### 3. La escala

Cuadro de `quality.scale_px` de la toma (**1594**, cadena 783,9 px) y cuatro vecinos. Si la
extensión vertical de la máscara fuera de coronilla a suela, el cociente contra la cadena
tendría que dar **1,044** — el +4,4 % que el encargo 14 dejó como residual geométrico.

| cuadro | máscara | cociente | sobra arriba del punto `head` | sobra abajo del tobillo |
|---|---|---|---|---|
| 1584 | 926 px | **1,1813** | +37 px | **+121 px** |
| 1593 | 926 px | 1,1813 | +42 px | +119 px |
| **1594** | **913 px** | **1,1647** | +27 px | **+117 px** |
| 1595 | 924 px | 1,1787 | +38 px | +119 px |
| 1604 | 920 px | 1,1736 | +31 px | +122 px |

**Repetible pero sesgada.** Los cinco cuadros caen en 913–926 px (±0,7 %), así que la medición
no es ruidosa: es que **no mide de coronilla a suela**. Sobra **+12 puntos** sobre 1,044, y el
sobrante está abajo: el borde inferior queda 117–122 px por debajo de los tobillos, que con la
escala de la toma (448 px/m) son **26–27 cm**.

`escala-1594.png` muestra qué es, y es peor que una sombra: **el zapato que no se mueve no
entra en la máscara**. Uno de los dos pies —el que se desplaza en el follow-through— sale
enmascarado con su halo y marca el borde inferior; el otro, blanco y quieto desde el address, no
entra en la máscara en absoluto, por la misma razón que el tronco. En
`vid1` pasa lo mismo con otros números: cociente **1,099–1,104** y +129 a +134 px por debajo
del tobillo. **La máscara no arregla el +4,4 %: lo cambia por un +12 % (o +6 %) que depende de
qué pie se movió.**

### 4. Robustez, los dos clips más

Los indicadores del punto 1 están en la tabla de arriba. Para el palo, 5 cuadros alrededor del
impacto de cada uno:

- **`vid1`** (UHD 60, la deriva de +119 px del 29): **el shaft no se ve a ojo en ninguno de los
  5 cuadros**, así que hay **0 comparaciones**. La pelota sigue en el tee en el 741 y del palo
  sólo queda un borrón claro de ~150 px pegado a la mano. El ajuste igual devuelve rectas
  (169,5° · 150,5° · sin recta · 139,8° · 162,2° con fondo global), y ninguna tiene contra qué
  compararse. **La deriva no molestó**: 0 homografías fallidas y la cobertura del bbox es la
  mejor de los tres (0,422), porque la estabilización la absorbe.
- **`cortado`** (FHD 30, 76 cuadros): el shaft **sí** se ve, porque el fondo es cemento y
  cartel oscuro. Con fondo global el error de ángulo es **6,5° de mediana, 2 de 5 por debajo de
  5°** (cuadro 44: 108,5° ajustado contra 110,6° a ojo, **2,1°**; cuadro 45: 4,2°), y con fondo
  local empeora a 18,4°, porque en 2,5 s de clip la ventana local (±0,5 s) son 35 de los 76
  cuadros y el cuerpo entra igual al modelo. Los dos que fallan son el 42 (41,9°) y el 46
  (14,2°), los dos con el palo cruzando el cartel.
  **Pero la silueta de ese clip no sirve**: 0,182 de cobertura, 27 % de keypoints, y la escala
  da 0,28 y 0,65 —el componente que contiene al sujeto **no llega a las piernas**—. Es el clip
  con 6,09 % del cuadro sin fondo.

### 5. Modelos de segmentación: las tres preguntas de ADR-010

Se incluye porque lo clásico **no** separa el palo donde importa (el impacto). Nada de esto se
instaló ni se corrió: es la tabla de licencias, y **dos de las seis filas no tienen respuesta a
la tercera pregunta**, que por invariante 12 ya es el veredicto.

| pieza | código | pesos | datos de entrenamiento | dónde correría | veredicto |
|---|---|---|---|---|---|
| **U²-Net vía `rembg`** | `rembg` MIT · U²-Net **Apache-2.0** (verificado en el repo) | el repo **no declara** licencia de los `.pth`; `rembg` redistribuye un `.onnx` derivado | **DUTS-TR, sin licencia declarada** (no la publica el sitio del dataset) | onnxruntime / CoreML | **no**: la tercera pregunta no tiene respuesta. Y segmenta «objeto saliente», no persona ni palo |
| **MediaPipe Selfie / Multiclass** | `mediapipe` Apache-2.0 | la página del modelo **no declara** licencia del archivo | **no publicado** en la model card | tflite — **fuera del stack de ADR-015** | **no**: dos preguntas sin respuesta, y está entrenado para selfies (torso cerca), no para un cuerpo de 690 px |
| **RTMDet-Ins (COCO)** | mmdetection **Apache-2.0** | OpenMMLab **Apache-2.0** | **COCO** (anotaciones CC BY 4.0; las imágenes, con su licencia de origen — el caveat de siempre) | **onnxruntime + CoreML, el mismo runtime que RTMPose** | **el único viable**… y segmenta *personas*: el palo no es una clase de COCO |
| **SAM 2** | Apache-2.0 | Apache-2.0 | **SA-1B es research-only**; SA-V es CC BY 4.0 | torch → sólo `truth/` | **no para producto**. Sí serviría en `truth/` para fabricar etiquetas |
| YOLO-seg (Ultralytics) | **AGPL-3.0** | AGPL-3.0 | COCO | — | **no**, ya vetado por ADR-010 |
| detectores por defecto de `rtmlib` | Apache-2.0 | — | **Human-Art, CC BY-NC-SA 4.0** | — | **no**, ya vetado por ADR-010 |

Procedencia de la tabla: `medido_aqui` sólo en lo que se leyó del repo o de la página oficial
(U²-Net Apache-2.0; MediaPipe sin licencia de modelo ni datos declarados; SA-1B research-only);
el resto, `sin_verificar`.

**Y ninguno cambia la conclusión.** Un segmentador de instancias mejor daría una silueta mejor
del **cuerpo**, que es lo que menos falta hace: lo que falta es el **palo en el impacto**, y ahí
no hay modelo que ayude porque **la información no está en el archivo**. A 240 fps la exposición
está topeada en 1/240 s y la cabeza del palo barre decenas de píxeles durante ese tiempo; lo que
el sensor grabó es una estela. Es exactamente lo que `CAPTURA.md` §Luz pide arreglar con
obturador, no con modelo.

### 6. Las tres líneas del cierre

- **Qué compra**: el **shaft en el top**, medido — 0,9° de mediana y 1,6° de máximo contra la
  etiqueta a ojo, 10 de 10 bajo 5°, con un largo de 383–421 px sobre ~360 etiquetados. Eso
  alcanzaría para un **top del palo** y para abaratar etiquetas humanas en la mitad lenta del
  swing.
- **Qué cuesta**: 68 ms/cuadro en FHD y 407 en UHD, más 27–72 s de modelo de fondo por clip; un
  modelo de fondo **por toma** (no se puede reusar entre tomas: cambia la escena); y la
  dependencia de que el sujeto se corra del lugar, que es justo lo que un golfista no hace.
- **¿Vale un encargo de producto?** **No.** El evento que el motor mide peor es el **impacto**
  (4–16 cuadros de diferencia entre manos y palo), y ahí la máscara no ve el palo en ninguno de
  los tres clips. Un «top del palo» solo no arregla el par que importa, y agregaría al motor un
  camino de dos minutos por toma que depende de la escena. Lo que sí vale es **anotar que a
  240 fps con el obturador de la cámara nativa el shaft del impacto no está en el archivo**, y
  que esa es una pregunta de `CAPTURA.md`, no de visión.

## Queda abierto

- **Desviación del prompt, una: el fondo local.** El prompt pedía «mediana temporal de los
  cuadros donde el sujeto no está»; eso es el fondo **global**, y está hecho. Pero el palo en el
  impacto vive encima del propio cuerpo, que es justo donde ese modelo no tiene fondo, así que
  se agregó un segundo modelo con una ventana de **±0,5 s sin enmascarar**: el cuerpo casi
  quieto entra a la mediana y lo único que queda de primer plano es lo rápido. Es la misma
  mediana con otra ventana, no otro algoritmo, los dos se reportan por separado, y sin él el
  fondo global además perdía **2 de los 10 cuadros del top**. **Del contrato no hay
  desviación**: no entra ni sale ningún campo de ningún schema y ningún valor del motor cambia.
- **El obturador, que es lo que bloquea todo esto, nunca se midió.** `CAPTURA.md` §Luz calcula
  21,2 px de barrido a 1/240 s y pide 1/1000 s o más corto, pero ningún clip del repo tiene el
  obturador medido ni declarado. Antes de gastar un encargo en segmentación conviene saber si el
  S22 en *Slow motion* está dando 1/240 o 1/1000: se lee de los metadatos del original crudo, que
  es otra cosa que falta (`CAPTURA.md` §Lo que queda por verificar).
- **La máscara no se probó en `down_the_line`**, porque no hay ningún clip de esa vista. Ahí el
  shaft apunta a la cámara buena parte del swing y es de esperar que sea peor, no mejor.
- **Los umbrales son `estimacion`**: `--umbral 12`, `--k-mad 3`, los grosores y radios en altos
  de cuerpo. Salen del orden de lo medido acá, no de un barrido. Un barrido sólo tendría sentido
  si el orquestador decidiera seguir con esto.
- **La máscara fina resta la silueta de la pose** antes de buscar el palo, así que el tramo de
  shaft que pasa por delante del cuerpo se pierde por construcción. En el top no molesta (el
  palo está contra el cielo) y en el impacto no llegó a molestar, porque ahí no hay shaft. Si
  alguien retoma esto, es lo primero a revisar.
- **`cortado` tiene una segunda persona en cuadro** (el golfista del box de al lado, con su
  palo visible en varios cuadros). No rompió nada acá —la máscara del sujeto se elige por los
  keypoints— pero es material que el gate `single_subject` debería estar mirando.
- **No se tocó** `kinelab/`, `sports/`, `service/`, `web/`, `truth/`, ningún `analysis.json`,
  ningún `pose.npz` ni ningún umbral del motor. **No se corrió pose sobre cuadros enmascarados**,
  no se estimó el palo desde el antebrazo, no se compensó la deriva en ninguna métrica y no se
  instaló nada. El front no se abrió (el prompt no tenía front).

## Para que mire Hernán

No hay front. Lo que sí conviene que mires vos, porque la pregunta del encargo era «¿el palo que
ve él es el que ajustó el script?»:

```bash
open data/incoming/cortado3-lento.kinelab/mascara/palo-local-1284.png \
     data/incoming/cortado3-lento.kinelab/mascara/palo-local-1364.png \
     data/incoming/cortado3-lento.kinelab/mascara/escala-1594.png
```

1. **`palo-local-1284.png`** (el top). **Magenta** = la recta ajustada, **amarillo** = la
   etiqueta que puse a ojo, **verde** = la máscara fina, **rojo** = la máscara del sujeto. Las
   dos rectas tienen que verse casi encimadas sobre el shaft; la magenta llega un poco más lejos
   porque sigue hasta la punta de la cabeza y la amarilla corta en el hosel.
2. **`palo-local-1364.png`** (el impacto). Acá la pregunta es la contraria: **¿ves vos el palo?**
   Yo marqué una estela tenue y en los cuadros 1367 y 1368 no marqué nada. Si vos lo ves y yo no,
   el número del punto 2 cambia y hay que rehacerlo.
3. **`escala-1594.png`**: las dos líneas amarillas son los extremos de la máscara y las blancas
   el punto `head` y los tobillos. Mirá el pie de adelante: **el zapato blanco no está
   enmascarado**, porque no se movió en todo el clip.

Y si querés recorrer los 20 cuadros etiquetados, están todos en esa carpeta como
`recorte-<cuadro>.png`, con la grilla en coordenadas del cuadro entero.

## Preguntas para el orquestador

1. **¿Se cierra el tema «máscara» con este informe?** La recomendación es sí: el shaft en el top
   está medido y anda, el del impacto no existe en el archivo, y el cuerpo y la escala no mejoran.
   Lo que quedaría abierto no es un encargo de visión sino **medir el obturador** de los clips
   que hay.
2. **¿Vale un encargo chico de `CAPTURA.md` sobre obturador?** Leer `exposure_time` /
   `ShutterSpeedValue` de los originales crudos del S22 y anotarlo al lado de los 21,2 px
   teóricos de §Luz. Es barato y decide si el impacto es recuperable con la cámara que hay.
3. **La segunda persona en `cortado`**: el gate declara `single_subject` con un límite de 0,10 y
   ese clip tiene un golfista entero al lado con su palo. ¿Se mide qué da ese chequeo ahí?
4. **¿Alguna de las etiquetas a ojo del impacto te parece equivocada?** Son el piso de la
   comparación del punto 2 y son `estimacion` mías: si el palo se ve mejor de lo que yo vi, el
   veredicto del impacto cambia.
