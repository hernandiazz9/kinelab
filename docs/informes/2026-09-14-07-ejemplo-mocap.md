# ejemplo-mocap — 2026-09-14

**Encargo:** bajar los ASF/AMC del sujeto de golf de CMU, escribir en `truth/`
un `python -m kinelab_truth.mocap TRIAL --vista … --out DIR` que los parsee, los
mapee a Halpe26 y los proyecte con la cámara virtual del arnés a 1080×1920 con
el sujeto al 80 % del alto; hacer que `explore` pueda arrancar de ese `pose.npz`
y dejar el resultado como un ejemplo en la pantalla; y sacar el primer número de
nivel 1 (sway de pelvis 2-D contra la verdad 3-D, y las duraciones).

## Hecho

- **Sujeto 64 = golf, verificado en el índice del sitio.** Sus 30 tomas: 1–10
  «Swing», 11–15 «Putt», 16–30 poner el tee y la bola. Es el único sujeto de
  golf de la base. Bajados a mano (CMU pide no crawlear) `64.asf`, `64_01.amc`
  y `64_02.amc` a `data/examples/cmu-mocap/`, con `ATRIBUCION.md`: el texto
  textual que CMU pide, la licencia como la declara el sitio, el sha256 y el
  tamaño de cada archivo, y las tres preguntas de ADR-010 contestadas por
  separado (datos libres con atribución y sin reventa; código propio; pesos no
  hay, acá no interviene ningún modelo).
- **`truth/kinelab_truth/mocap.py`**, parser propio en numpy, **sin dependencia
  nueva** (ADR-015 intacto): ASF (unidades, huesos, ejes, grados de libertad,
  jerarquía) + AMC + cinemática directa `L_b = L_p·C_b·R_b·C_b⁻¹`. Los largos
  se pasan a metros con `× 0,0254 / :units length`, leyendo el 0,45 del propio
  archivo en vez de fijar la constante.
- **Mapeo a Halpe26**: 16 puntos son la misma articulación en los dos
  esqueletos (el extremo del hueso de CMU es el centro articular que Halpe
  nombra). Los otros 10 se construyen y cada aproximación queda escrita en
  `APPROX_NOTES`, que viaja dentro del `pose.npz`: `hip` (medio exacto de las
  dos caderas — **en un clip real ese punto lo predice la red y no es un centro
  articular, así que el ejemplo lo tiene mejor que un video**), `neck` (extremo
  del hueso `thorax`, la base del cuello), cara (nariz, ojos y orejas, rígidos
  sobre el hueso de la cabeza, escalados por su propio largo), talones (detrás
  del tobillo, a 0,45 de la distancia horizontal tobillo→planta, a la altura de
  la planta) y puntas chicas (0,25 de esa distancia hacia afuera).
- **Cámara virtual**: el mocap se lleva al marco del arnés (x al objetivo desde
  la línea de caderas, y arriba, z a la pelota; origen entre los tobillos sobre
  el suelo) y se proyecta con `camera.py`. La focal se ajusta iterando hasta que
  el cuerpo mida exactamente el 80 % del alto. La **altura declarada** del
  atleta sale de los largos de hueso del ASF (1,6405 m), no del trial.
- **`explore()` arranca de un `pose.npz`** (`prepare_take_from_pose`): sin
  video, sin estimador, con el `capture.json` armado desde la `provenance` del
  `.npz`. El overlay se dibuja sobre fondo liso cuando la toma no tiene
  `original.<ext>` (`_frames`), y la línea quemada la pone quien llama. La
  refactorización que el prompt permitía fue esa: extraer el origen de los
  cuadros de `render()`. **Camino de captura: el default `desconocido-video`,
  no se inventó ninguno.**
- **El aviso del eje del tiempo lo pone quien produjo la pose.** La frase que
  arma `build_analysis` para un camino declarado habla de «el archivo reproduce
  a la velocidad de captura» y de «filmá el cronómetro»: con mocap las dos son
  falsas. `explore` la reemplaza por `nota_fuente` —*"fps 120 exacto por
  construcción (mocap CMU 64_01), cámara virtual, no es video"*— que sigue yendo
  primero en `warnings[]` y también es el `fps_aviso` de `datos-eventos.json` y
  la `etiqueta` del trabajo. La procedencia sigue siendo `sin_verificar` y
  **ningún `judgment_allowed` es verdadero**.
- `_ascii` de `kinelab/tools/interpolar.py` pasa a `ascii_para_quemar`, pública:
  hay dos lugares que queman texto en un cuadro y la tabla de transliteración
  tiene que ser una sola.

Commits: `313acd5` (datos, módulo, tests y el cambio de `explore`) y el de
cierre con `ESTADO.md` y este informe.

## Probado

Motor **261 en verde** (~40 s), arnés **13 en verde** (2,6 s). Tests nuevos: 9
en `truth/tests/test_mocap.py` y 1 en `tests/test_perception.py` (21 en ese
archivo).

Los del arnés: el parser sobre un ASF/AMC mínimo escrito en el test, con la
cinemática verificada a mano (una torre de 10 unidades y un brazo de 5 que gira
90° en x); un AMC con un salto de cuadro se rechaza; `euler_xyz` es `Rz·Ry·Rx`
y no al revés; el mapeo da 26 puntos finitos con **los cuatro pares laterales
apuntando para el mismo lado** (si el mapeo cruzara izquierda y derecha en uno
solo, falla — invariante 15), `hip` en el medio exacto, la cadena vertical en
orden, talones detrás de las puntas y puntas chicas por fuera; el marco del
arnés deja el suelo en cero, `R` ortonormal con determinante +1 (no espeja) y la
cadera izquierda del lado del objetivo; la proyección de un punto conocido cae
a `f/d` px del centro; y desde `down_the_line` las dos caderas se enciman.

El del motor: `explore` arrancando de un `pose.npz` sintético — no copia ningún
video, el `capture.json` sale con 120 fps y `sin_verificar`, el aviso del camino
declarado se reemplaza por el de quien produjo la pose, ningún
`judgment_allowed`, los eventos salen donde el swing sintético dice, y el PNG
del impacto tiene una esquina con el fondo liso exacto y el rótulo quemado
arriba.

**Corrida real.** Un comando por vista, ~7 s cada uno:

```bash
cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista face_on \
  --out ../data/exploracion/ejemplo-cmu-64_01-face_on --nivel1 \
  --etiqueta "ejemplo · mocap CMU 64_01 · cámara virtual · no es video · fps 120 exacto por construcción"
```

| | `face_on` | `down_the_line` |
|---|---|---|
| carpeta | `data/exploracion/ejemplo-cmu-64_01-face_on/` | `…-down_the_line/` |
| cuadros · fps | 448 · 120,0 | 448 · 120,0 |
| cuerpo | 1536 px = **80,0 %** del alto | 1536 px = **80,0 %** |
| focal de la cámara virtual | 3077,7 px | 3193,5 px |
| address | **141** (1,175 s) | **146** (1,217 s) |
| top | **270** (2,250 s) | **327** (2,725 s) ← mal, ver abajo |
| impacto | **329** (2,742 s) | **332** (2,767 s) |
| sub-cuadro del impacto | 329→330, `fraction` 0,1419, ±0,089 cuadros | `null` por vista (encargo 02) |
| `follow_end` | `null`: el trial corta antes del finish quieto | `null` |
| backswing / downswing | 1075,0 / 491,7 ms · tempo 2,19 : 1 | 1508,3 / 41,7 ms ← mal |
| calidad | `confiable`, detección 1,0 | `confiable` |
| tamaño en disco | 4,5 MB | 4,5 MB |

Los dos se listan desde `service/exploracion.py` con `origen: ejemplo`, su
etiqueta, los ocho archivos de la lista blanca y los eventos en la fila. El
ejemplo de mentira del 08 (`ejemplo-a-mano-cortado-face_on`) está borrado.

### El primer número de nivel 1

Trial 64_01, `face_on`. El sesgo va partido en dos a propósito: con **los
cuadros del motor** sale el error de la medición sola (proyección + conversión a
cm); con **los eventos leídos sobre las curvas 3-D** sale el error total, con el
de los eventos adentro. Los eventos 3-D salen de un criterio geométrico escrito
en `events_3d()` (quietud de arranque; impacto = las manos vuelven más cerca de
su posición 3-D de address; top = máxima distancia 3-D al address), fijado
mirando las curvas y dejado en código para que se pueda repetir.

Eventos: motor 141 / 270 / 329 · 3-D **145 / 269 / 330**.

| métrica | motor 2-D | verdad 3-D (cuadros del motor) | sesgo | verdad 3-D (cuadros 3-D) | sesgo total | MDC del arnés |
|---|---|---|---|---|---|---|
| `pelvis_sway_top_cm` | **−19,4** | −17,69 | **−1,71** | −17,51 | −1,89 | 2,87 |
| `pelvis_sway_impact_cm` | 6,9 | 6,29 | +0,61 | 6,93 | −0,03 | 2,48 |
| `pelvis_lift_top_cm` | 0,7 | 0,69 | +0,01 | 0,83 | −0,13 | 2,82 |
| `thorax_sway_top_cm` | −10,9 | −9,37 | −1,53 | −9,56 | −1,34 | 3,46 |
| `thorax_lift_top_cm` | −2,9 | −2,58 | −0,32 | −2,38 | −0,52 | 2,89 |
| `head_sway_top_cm` | −10,7 | −8,45 | −2,25 | −8,69 | −2,01 | 3,82 |
| `head_lift_top_cm` | 2,3 | 1,64 | +0,66 | 1,76 | +0,54 | 4,50 |
| `backswing_duration_ms` | 1075,0 | 1075,0 | 0,0 | 1033,3 | **+41,7** | 12,6 |
| `downswing_duration_ms` | 491,7 | 491,7 | 0,0 | 508,3 | **−16,6** | 13,0 |

**Es un solo trial de un solo sujeto: una primera lectura, no una tabla.** De
acá no sale ningún MDC, ninguna referencia y ningún ideal. Tres cosas que sí se
leen:

1. **Todos los desplazamientos caen por debajo de su MDC**, con los dos juegos
   de cuadros. **Ninguna de las dos duraciones cae por debajo del suyo cuando el
   error de eventos entra**: +41,7 ms son 3,3 × el MDC del backswing. Con los
   cuadros del motor las duraciones dan sesgo cero por construcción (mismo
   `fps`, misma resta), así que el número que importa es el otro: **todo el
   error de las duraciones es error de eventos, no de medición.**
2. **El sesgo de los cm es sistemático y explicable.** El motor sobre-lee la
   magnitud del sway **+10,0 %**, y se descompone: **+12,7 % de la convención de
   altura** —`px_to_cm` divide por la altura cabeza→tobillos en px y multiplica
   por la estatura declarada, y en un golfista inclinado en address esas dos no
   son la misma cosa: 1,4554 m contra 1,6405 m, cociente 1,1272— y **−2,4 % de
   la proyección**. Medido en píxeles: 181,96 px de pelvis ÷ 1534,8 px de cuerpo
   × 1,6405 m = 19,45 cm; con la escala real (× 1,4554 m) = 17,25 cm; verdad
   3-D = 17,69 cm.
3. **Se repite en el segundo trial.** 64_02, `face_on`: sway top motor −19,5
   contra verdad 3-D −17,61 (sesgo −1,89; con los cuadros 3-D, −2,81); sway
   impacto +0,97; thorax sway −1,53; head sway −1,92; duraciones 0,0 con los
   cuadros del motor y +75,0 / +8,4 ms con los 3-D. Mismo signo, mismo orden de
   magnitud.

Lo que el mocap mide de este golfista, dicho sin adjetivos: la pelvis se corre
**17,7 cm** hacia el lado trasero entre address y top y vuelve **+6,3 cm** al
impacto, con 46,8° de giro de la línea de caderas y sin dar un paso (los
tobillos se mueven menos de 1 cm). El pico de velocidad del centro de las manos
es 3,79 m/s y cae **en el acompañamiento (cuadro 359), no en el impacto** — el
cementerio 7 de `HERENCIA.md`, ahora sobre un humano real.

## Queda abierto

1. **Desde `down_the_line` el detector de top falla, y está medido por qué.**
   El motor pone el top en 327 y el impacto en 332: 5 cuadros de downswing.
   ADR-008 define el top como el **último** cambio de signo de la velocidad de
   las manos proyectada sobre el eje principal de la trayectoria
   address→impact. Medido sobre este trial: en `face_on` el eje principal es
   `(−0,463, −0,886)` —63° de la vertical— y hay **dos** cambios de signo entre
   address e impacto, 145 y **270**: el último es el top y sale bien. En
   `down_the_line` el eje es `(−0,199, −0,980)` —casi vertical, porque el
   movimiento hacia el objetivo cae sobre el eje óptico— y hay **tres**: 158,
   **263** (el top de verdad) y **328**, que es el fondo del arco justo antes
   del impacto. Gana el 328. **El top sí está en la señal; lo pierde la regla
   del "último".** No lo toqué: el prompt prohibía mover umbrales de eventos, y
   esto es un cambio de definición, no un umbral. Address (146 contra 145) e
   impacto (332 contra 330) desde esa vista salen bien.
2. **La convención de `px_to_cm`** (punto 2 de arriba): dividir por
   cabeza→tobillos y multiplicar por la estatura declarada mete un +12,7 %
   sistemático en toda métrica en cm de un gesto agachado. El arnés no lo ve
   porque su swing sintético usa la misma convención en la verdad y en la
   medición. Las salidas que se me ocurren: declarar la altura cabeza→tobillos
   en vez de la estatura, o que la conversión use un factor por gesto. Es
   decisión del orquestador y toca `kinelab/metrics/core.py`.
3. **`hip_line_rate_deg_s` llega a 3244 °/s** en el ejemplo (la línea de
   hombros, 453 °/s, es plausible). Es la degeneración conocida: la línea de
   caderas mide 15,2 cm y al girar 90° su proyección se acorta hasta casi cero y
   su ángulo aparente salta. Es una columna descriptiva de exploración, no una
   métrica registrada, pero es la misma geometría que alimenta
   `summary.gain`, que ya estaba marcada como sospechosa en `ESTADO.md`.
4. **`follow_end` queda en `null`** en los dos trials: cortan antes de que el
   golfista se quede quieto en el finish. `follow_duration_ms` también, con su
   razón. No es un error, es el material.
5. **El rótulo quemado cae sobre la cabeza del sujeto.** Con el cuerpo al 80 %
   del alto, los keypoints van de y=14 a y=1917 en un cuadro de 1920: no hay
   margen. Es una consecuencia del encuadre que pide `CAPTURA.md`, no del
   mocap. Se lee igual (el texto va con contorno negro).
6. **La cámara virtual es un teleobjetivo.** Para poner el cuerpo al 80 % de un
   cuadro vertical de 1080×1920 a 3 m hacen falta 3078 px de focal, ~2,1 × la
   cámara principal de un teléfono (que a 1080 de ancho anda por 816 px). Con un
   teléfono real habría que estar a ~0,8 m, o filmar horizontal. La cámara está
   declarada `sin_verificar` y no pretende ser un teléfono, pero conviene saber
   que **el 80 % del alto en vertical no es alcanzable con un celular a una
   distancia usable**.
7. El swing de este sujeto es lento: downswing de ~500 ms y pico de manos de
   3,8 m/s, contra los 250–300 ms de un swing de torneo. Es un golfista real en
   un laboratorio, no un profesional. No cambia nada de lo medido, pero el
   ejemplo no se parece a un swing de tour.

## Para que pruebe Hernán

El ejemplo no se commitea (`data/exploracion/` está ignorado); se rehace con un
comando. Si ya lo tenés, saltá al paso 2.

```bash
cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista face_on --out ../data/exploracion/ejemplo-cmu-64_01-face_on --nivel1 --etiqueta "ejemplo · mocap CMU 64_01 · cámara virtual · no es video · fps 120 exacto por construcción"
```

1. Tiene que terminar en ~7 s y decir **448 cuadros a 120 fps · cuerpo 1536 px
   (80,0 %)**, eventos **address 141 · top 270 · impacto 329**, y abajo la tabla
   de nivel 1 con `pelvis_sway_top_cm −19,4` contra verdad 3-D `−17,69`.
2. En la pantalla, en «Trabajos anteriores y ejemplos», tienen que aparecer
   **`ejemplo-cmu-64_01-face_on`** y **`ejemplo-cmu-64_01-down_the_line`** con
   su rótulo. Abrí el de `face_on`.
3. **Mirá que ande el reproductor sobre un swing que no es el tuyo**: palitos
   sobre fondo gris liso, reproducir, frenar, ◀ ▶ cuadro a cuadro, 0,1× y
   0,25×, zoom con la rueda. Arriba de todo, en cada cuadro, la línea naranja
   **`mocap CMU 64_01 | camara virtual | no es video`**.
4. Las tres fotos por evento y los ángulos en la tabla: en address codo
   izq/der **158,7° / 179,3°**, rodillas **178,3° / 179,5°**, tronco **+0,3°**,
   altura de manos **56 %**.
5. **El aviso tiene que leerse antes que cualquier número**: *"fps 120 exacto
   por construcción (mocap CMU 64_01), cámara virtual, no es video…"*.
6. Abrí después el de `down_the_line` **sabiendo que el top está mal** (cae en
   el cuadro 327, a 5 del impacto). Eso es el punto 1 de «queda abierto», no un
   error de la pantalla; la etiqueta lo dice.

## Preguntas para el orquestador

1. **¿El top desde `down_the_line` entra como encargo propio?** Está medido de
   dónde sale (punto 1 de arriba). La regla del "último cambio de signo" es de
   ADR-008; cambiarla —por ejemplo, exigir que el top esté a más de N cuadros
   del impacto, o elegir el cambio de signo de mayor amplitud— es reabrir ese
   ADR, y no era de esta sesión. Mientras tanto, `down_the_line` no sirve para
   medir duraciones.
2. **¿Qué se hace con el +12,7 % de `px_to_cm`?** Toca `kinelab/metrics/core.py`
   y le cambia el valor a todas las métricas en cm. El arnés no puede
   detectarlo solo: su verdad y su medición comparten la convención.
3. **¿El ejemplo se regenera o se guarda?** Hoy `data/exploracion/` está
   ignorado y el ejemplo se rehace con un comando de 7 s desde los ASF/AMC, que
   sí viajan (1,5 MB). La alternativa sería exceptuar esas dos carpetas del
   `.gitignore` (9 MB, con `overlay.mp4` adentro, que el prompt prohibía
   commitear). Me quedé con regenerar.
4. **¿Hace falta un tercer trial?** Guardé dos (64_01 y 64_02) y el sesgo se
   repite en los dos. Hay diez swings del mismo sujeto disponibles; con más
   trials se podría dar un sesgo medio con límites de acuerdo, pero **de un solo
   sujeto**, que no es lo que hace falta para un MDC.
