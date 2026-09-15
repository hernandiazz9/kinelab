# top-desde-down-the-line — 2026-09-15

**Encargo:** cambiar la regla del top —de "el último cambio de sentido" a "el
cambio de sentido en el que las manos están más lejos del address"—, escribirla
como ADR-017, y probarla con el mocap 64_01 desde las dos vistas, el swing
sintético, un caso construido y un bug inyectado.

## Hecho

- **`kinelab/events/primitives.py`**: `direction_change` (devolvía el último
  cambio de sentido) se parte en dos. `direction_changes(pos_axis, before,
  after)` **enumera** los cambios, y `direction_change_farthest(pos_axis,
  excursion, ...)` elige el de **mayor excursión**. La vieja no queda en el
  motor: una regla reabierta que sigue a mano vuelve sola.
- **`sports/golf/events.py`**: el top usa el selector nuevo con la excursión =
  `dist`, la distancia de las manos a su posición de address en el plano de
  imagen — **la misma señal cuyo mínimo ya elegía el impacto**. Una señal, dos
  eventos. El `method` del evento dice `direction_change_farthest`, y el
  `detector` de la definición de GolfDB también.
- **ADR-017 en `DECISIONES.md`**, citando ADR-008, con la tabla de las dos
  vistas y lo que la regla **no** arregla (abajo).
- **Un borde que la corrida real destapó**: el primer segmento (de `after` a
  `after + 1`) no cuenta como cambio de sentido — devolvería el propio cuadro
  del address. Sin eso, el segundo candidato de `vid1.mp4` inventaba una
  repetición con top = address = 862 y backswing de 0 ms, donde antes se
  rechazaba con `sin_top`. Tiene su test.
- **Fixture nuevo en `tests/data/`** (184 KB): el `pose.npz` del mocap CMU
  64_01 en las dos vistas, con su `README.md` (sha256, atribución de CMU, y el
  comando para regenerarlo). Va como archivo y no se genera en el test porque
  `kinelab_truth` vive en `truth/`, con **su propio entorno a propósito**
  (invariante 14), y la suite del motor no lo importa.
- Address, impacto, follow_end, umbrales y filtrado: **sin tocar**.

Commits: `0f8f18e` (la regla, los tests, el fixture y ADR-017) y el de cierre
con `ESTADO.md` y este informe.

## Probado

**Suite del motor: 264 en verde** (38,8 s) al momento de commitear la regla —
las 261 de antes más las 3 nuevas—, y **272 en verde** (39,9 s) al cerrar la
sesión, con el trabajo sin commitear de las sesiones 12, 13 y 14 en el mismo
árbol. El arnés no se tocó y da **29 en verde** (lo está ampliando el 13).

**Bugs inyectados** (los tres, uno por vez, con la suite corriendo después):

| bug | tests en rojo |
|---|---|
| elegir el **más cercano** (`min` en vez de `max`) | 2 |
| elegir el **último** (la regla vieja) | 2 |
| incluir el primer segmento (el top puede caer en el address) | 1 |

**Mocap CMU 64_01 y 64_02, las dos vistas, 120 fps.** La verdad son las curvas
3-D del propio mocap (`events_3d`, criterio `top_far`), que no pasan por la
cámara:

| trial · vista | address | top antes | **top después** | verdad 3-D | impacto | backswing (ms) | downswing (ms) |
|---|---|---|---|---|---|---|---|
| 64_01 `face_on` | 141 | 270 | **270** | 269 | 329 | 1075,0 | 491,7 |
| 64_01 `down_the_line` | 146 | 327 | **263** | 269 | 332 | 1508,3 → **975,0** | 41,7 → **575,0** |
| 64_02 `face_on` | 172 | 305 | **305** | 306 | 373 | 1108,3 | 566,7 |
| 64_02 `down_the_line` | 196 | 373 | **304** | 306 | 376 | 1475,0 → **900,0** | 25,0 → **600,0** |

Verdad 3-D de las duraciones: 1033,3 / 508,3 ms en 64_01 y 1033,3 / 558,3 en
64_02. **Desde `down_the_line` el error del top pasa de +58 y +67 cuadros a −6
y −2** (de +483 y +558 ms a −50 y −17 ms), y el downswing deja de ser una
ficción de 5 y 3 cuadros. Desde `face_on` no se mueve ni un cuadro: ahí las dos
reglas eligen el mismo cambio.

**Los cuatro clips reales del Galaxy S22, todos `face_on`**, re-analizados
desde su `pose.npz` (invariante 1: no se volvió a correr el modelo para esto):

| clip | fps | address | top antes | **top después** | impacto | referencia (ver abajo) |
|---|---|---|---|---|---|---|
| `cortado.mp4` | 30,0 | 7 | 39 | **33** | 44 | 36 |
| `20260907_170638.mp4` | 30,0 | 111 | 141 | **137** | 147 | 139 |
| `vid1.mp4` | 60,0 | 672 | 726 | **722** | 741 | 722 |
| `vid2.mp4` | 60,0 | 58 | 115 | **115** | 134 | 114 |
| `vid3.mp4` | 60,0 | — | — | — | — | 0 repeticiones, igual que antes |

**Tres de los cuatro `face_on` se movieron, y la causa no es la regla.** La
señal del motor es el **centro de las dos muñecas**, y en los dos clips del 7/9
la muñeca izquierda se pierde justo en el top: confianza 0,34–0,35 y saltos de
hasta 300 px entre cuadros consecutivos (`cortado.mp4`, cuadros 32–38: x de la
muñeca izquierda 414 → 435 → 356 → **672** → 486 → 491 → 497 → 331). La derecha,
en los mismos cuadros, va suave y con confianza ≥ 0,53.

La columna "referencia" de la tabla es **la muñeca derecha sola**, como segunda
señal independiente: ahí hay **un solo** cambio de sentido y las dos reglas dan
**el mismo cuadro** en los cuatro clips — 36, 139, 722 y 114. Contra ella:

| | cortado | 20260907 | vid1 | vid2 |
|---|---|---|---|---|
| error de la regla vieja | +3 | +2 | +4 | +1 |
| error de la regla nueva | −3 | −2 | **0** | +1 |

Empate en los dos clips del 7/9 (que son el mismo swing: `cortado` son los
cuadros 103–178 del otro), mejor en vid1, igual en vid2. **Donde la señal está
limpia las dos reglas coinciden; donde no, ninguna de las dos es una medición.**

**Y en vid1 la elección es frágil**: los tres cambios de sentido del centro de
manos están a 590,3 / 587,0 / 587,7 px del address — **3,3 px entre el primero y
el último**, en una señal cuyo ruido por cuadro el propio motor estima en
**2,27 px** en ese mismo clip (`subframe.components.noise_px`). Gana el 722 por
2,6 px: poco más de un σ. En `vid2` y en el
mocap la diferencia es de cientos de píxeles y no hay duda posible; acá, la
regla decide con una diferencia del orden del ruido. ADR-008 ya tiene una regla
para este caso en otro lugar —dos picos a menos de 2 cuadros se reportan
`indeterminado`—; acá no hay ninguna. Queda como pregunta abajo.

**Lo que se mueve con el top.** Todo lo anclado ahí (altura declarada 1,75 m en
los cuatro, la misma antes y después):

| métrica (cm) | cortado | 20260907 | vid1 | vid2 |
|---|---|---|---|---|
| `pelvis_sway_top_cm` | 0,7 → **−5,2** | −0,7 → −4,6 | −1,5 → −3,5 | −5,8 |
| `pelvis_lift_top_cm` | −3,4 → −0,3 | −2,0 → −0,3 | −11,0 → −10,3 | −1,2 |
| `thorax_sway_top_cm` | 1,4 → −1,5 | 0,5 → −0,8 | −1,6 → −2,4 | −2,3 |
| `head_sway_top_cm` | 3,7 → 2,7 | 4,1 → 3,2 | −7,1 → −8,1 | −2,8 |
| `tempo_ratio` | `null` (fps) | `null` (fps) | 3,6 → **2,63** | 3,0 |

El mayor cambio son los 5,9 cm de `pelvis_sway_top_cm` en `cortado`, contra un
MDC de 2,87 cm (`sports/golf/mdc.yaml` de hoy; el encargo 13 está rehaciendo
esa tabla mientras escribo). Las duraciones siguen en `null` en los cuatro
(`fps_min` 120) y ninguna métrica quedó con `judgment_allowed` verdadero: los
cuatro vienen de caminos declarados, `sin_verificar` (ADR-016).

**De punta a punta con el CLI**, no sólo desde la pose guardada:

```
.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75
  76 cuadros a 29.999 fps · eventos {'address': 0.233, 'top': 1.1, 'impact': 1.467}
  duraciones {'address_to_top_ms': 866.7, 'top_to_impact_ms': 366.7, 'tempo_ratio': 2.36}
```

Cuadro 33, el mismo que da el re-análisis desde el `pose.npz` guardado: correr
el modelo otra vez sobre el mismo clip devuelve los mismos cuadros. En
`evento-top.png` el palo está arriba del todo y las manos al 103 % de la altura
del cuerpo; en el 39 —el top viejo— ya venían 73 px más abajo que en el 33, y
86 px por debajo de su punto más alto (el cuadro 34).

**El swing sintético no se movió**: tops idénticos con las dos reglas a 60, 120
y 240 fps, con y sin ruido de 2 px. Su arco de bajada no vuelve sobre sí mismo,
así que nunca tuvo un tercer cambio de sentido. Por eso el caso de
`down_the_line` necesita el mocap y no se puede escribir con trigonometría.

## Queda abierto

1. **La señal de manos, no la regla, es lo que limita el top en `face_on`.** El
   centro de las dos muñecas hereda la muñeca que el modelo pierde en el top
   (confianza 0,34). Un promedio pesado por confianza, o quedarse con la muñeca
   más confiable por cuadro, cambiaría los cuatro clips reales — y también el
   address y el impacto, que salen de la misma señal. Es un cambio de
   `kinelab/events/signal.py` (`hands_center`) que el prompt no autorizaba
   («no tocar address ni impact»). **Decisión del orquestador.**
2. **ADR-008 dice que el top se detecta por inflexión de la segunda derivada de
   la velocidad filtrada; el código detecta el cambio de sentido** (cero de la
   velocidad proyectada), que es lo que dice la definición de GolfDB. No es de
   esta sesión y no se tocó: ADR-017 sólo elige cuál de los cambios de sentido
   es el top. Queda anotado en el ADR. La primitiva `d2_inflection` existe y
   hoy no la usa ningún evento.
3. **El error del top sigue sin medirse contra GolfDB** (ESPECIFICACION 2.5).
   Dos trials de un sujeto de mocap y cuatro clips de un golfista no son una
   tabla; son lo que había.
4. **`data/examples/analysis.example.json` quedó con `"method":
   "direction_change"`** en sus tres eventos top. Es de `data/examples/`, que
   toca el encargo 14: no lo edité. El schema no valida el contenido de
   `method` (es `{"type": "string"}`), así que no rompe ningún test; queda
   desactualizado hasta que alguien regenere el ejemplo.
5. **Las tomas ya analizadas conservan su top viejo** hasta que se re-analicen
   (invariante 18). En `data/exploracion/` hay 11: las **nueve** subidas del 12
   al 14/9 (con top 39 o 141, según el clip) y los **dos ejemplos de mocap** del
   encargo 07 — el de `down_the_line` con el top en 327, que es justo el caso
   que este encargo arregla. No los rehice: el ejemplo lo escribe
   `kinelab_truth.mocap`, que está siendo editado por el encargo 14. Se rehacen
   con el comando del informe del 07, ~7 s cada uno.

## Preguntas para el orquestador

- **¿`hands_center` pesado por confianza?** (punto 1). Es el cambio con más
  efecto medido sobre los clips reales que hay, y toca los tres eventos.
- **¿Se re-analizan las tomas de `data/exploracion/` ahora, o se dejan con su
  top viejo hasta que alguien las mire?** Invariante 18 permite las dos; hoy
  ninguna se re-analizó.
- **¿Vale la pena `d2_inflection` para el top** (punto 2), o ADR-008 se corrige
  para decir lo que el código hace y lo que GolfDB define?
- **¿Hace falta una regla de empate?** Cuando dos cambios de sentido están a
  pocos píxeles (vid1: 2,6 px de ventaja sobre 2,27 px de ruido), elige igual y no
  lo dice. ADR-008 marca `indeterminado` cuando dos picos caen a menos de 2
  cuadros; podría haber el equivalente acá, o el top podría llevar su propia
  banda. Hoy no la tiene: sólo el `tol_frames` de 1.

## Para que pruebe Hernán

No hay front en este encargo (no se abrió ni se tocó `web/` ni `service/`). Si
querés ver el cambio con los ojos, en la terminal:

```bash
.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75
```

1. En la salida, `eventos {'address': 0.233, 'top': 1.1, 'impact': 1.467}`: el
   top es **1,100 s** (cuadro 33). Antes decía 1,300 s (cuadro 39).
2. Abrí `~/Desktop/cortado.kinelab/evento-top.png`: el palo tiene que estar
   arriba del todo, no bajando.
3. En `~/Desktop/cortado.kinelab/datos-eventos.json`, `duraciones`:
   backswing 866,7 ms y downswing 366,7 ms (antes 1066,7 y 166,7). Un downswing
   de 166 ms era más rápido que el de un profesional.
