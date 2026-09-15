# visor-3d-del-mocap — 15 de septiembre de 2026

**Encargo:** `docs/prompts/19-visor-3d-del-mocap.md` — que `mocap.py` exporte el
swing en 3-D (`pose3d.json`, metros, marco del arnés, declarado adentro del
archivo), que la pantalla lo muestre girable con los mismos controles del
reproductor y sin dependencias nuevas, que dos botones lleven la cámara a los
extrínsecos exactos de `face_on` y `down_the_line`, que un indicador permanente
muestre el largo proyectado de las líneas de caderas y hombros, y que los
rótulos digan con todas las letras que esto sale de un mocap medido y **no** se
puede hacer con un clip de celular.

## Hecho

- **`truth/kinelab_truth/mocap.py`**: `write_pose3d` / `pose3d_doc` escriben
  `pose3d.json` (26 puntos en metros, 3 decimales, una línea por cuadro).
  Adentro del archivo, como **dato** y no como comentario: el marco
  (`HARNESS_FRAME`: origen, ejes, unidades, mano), el modelo de cámara
  (`PINHOLE_MODEL`, la receta para reproyectar desde afuera de Python), fps,
  cuadros, nombres, huesos, `APPROX_NOTES`, la estatura del ASF, los eventos del
  motor **y** los leídos en 3-D, el cero del suelo medido, los rótulos
  (`rotulos()`) y la definición del indicador (`indicador_lineas()`).
- **`camera_record`** y `MocapPose.cameras`: el archivo lleva **las dos** cámaras
  del protocolo, con posición y objetivo en metros. Los puntos 3-D no dependen
  de la vista, así que cualquier trabajo puede llevar la cámara a cualquiera de
  las dos.
- **`service/exploracion.py`**: `pose3d.json` en la lista blanca.
- **`web/src/components/Visor3D.tsx`** (nuevo): canvas 2-D, sin WebGL y sin
  librería 3-D (ADR-015). Esqueleto de 26 puntos y 27 huesos sobre grilla de
  suelo con regla de 0,5 m; arrastrar para girar, rueda para acercar; la misma
  línea de tiempo y los mismos controles del reproductor (reproducir, pausa,
  cuadro a cuadro, 0,1×–1×, ir a address / top / impacto); «ver como face_on» y
  «ver como down_the_line»; y el indicador permanente. Aparece **sólo** si el
  trabajo tiene `pose3d.json`.
- **`web/src/lib/pose3d.ts`** (nuevo): el tipo del archivo y la proyección, sin
  React y sin canvas. **`web/src/lib/pose3d.verificar.mjs`** (nuevo): la corrida
  que compara ese TypeScript contra el `pose.npz` del arnés, con node y sin
  navegador. Son los dos archivos que el prompt no preveía; ver Desviaciones.
- **`web/src/app/page.tsx`**: 7 líneas de punto de entrada.
- **`truth/tests/test_pose3d.py`** (nuevo): 8 tests, con la proyección rehecha a
  mano (sin `cv2`, sin `camera.py`) — el mismo código que hay en el visor.

Commits al pie.

## Probado

Arnés **37 en verde** (8 nuevos, 6,7 s). Motor **272 en verde** (27 s).
`cd web && pnpm lint && pnpm build`, limpios.

### 1 · El visor y el arnés son el mismo swing (la prueba que pedía el prompt)

Proyectar el `pose3d.json` con cada cámara del protocolo y comparar contra el
`pose.npz` de esa vista, 448 × 26 puntos por combinación:

| | peor error, distancia en el plano |
|---|---|
| ver como `face_on` (f 3077,7 px) | **0,855 px** |
| ver como `down_the_line` (f 3193,5 px) | **0,922 px** |

Las cuatro combinaciones (los dos archivos × las dos cámaras) dan lo mismo. El
residuo es el redondeo a milímetros del archivo y nada más: medio milímetro a
3 m con esa focal vale 0,51 px. Se mide **dos veces**: en Python, con la fórmula
escrita a mano desde los campos del archivo, y en el TypeScript que de verdad
corre en la pantalla —que además pasa por la vuelta azimut/elevación que usan
los botones, y no se pierde nada ahí—.

### 2 · La línea de caderas colapsa, y se ve girando

Largo proyectado en porcentaje del largo real, en el cuadro de address:

| desde | caderas | hombros |
|---|---|---|
| `face_on` | **99,6 – 99,9 %** | 100,0 % |
| `down_the_line` | **4,2 % / 8,9 %** | 6,3 % / 3,0 % |

Los dos valores de `down_the_line` son los dos trabajos (address 141 y 146: cada
vista detecta el suyo). En el **top**, con las caderas ya giradas, la misma línea
desde `down_the_line` vuelve a **75,9 %**: lo que colapsa es el ángulo, no la
línea. Es la misma geometría que el 13 midió en °/s (3,6 px de largo, 11110 °/s
contra 139,6 verdaderos), ahora sobre un humano y mirable en dos segundos.

### 3 · El indicador no depende del zoom

Con la focal × 0,3, 0,5, 1, 2 y 4 en un ángulo que no es de ningún protocolo
(az −37°, el 17°), la línea de caderas en el top da **97,9 %** en las cinco,
hasta 1e-9. Hay test en Python y chequeo en el TypeScript.

### 4 · Girar no saca al sujeto del cuadro

Barrido de 24 azimuts × 7 elevaciones con la focal del protocolo: el peor caso
deja **98,2 %** de los 448 × 26 puntos dentro del cuadro (az 60°, elevación 5°;
lo que se sale son las manos en el top). Con la rueda hacia abajo (0,3×) entra
el **100 %** en todos los ángulos.

### 5 · Los dos ejemplos regenerados

Con ADR-017 (encargo 15) y la escala del 14 ya aplicados:

| | `face_on` | `down_the_line` |
|---|---|---|
| address / top / impacto | 141 / 270 / 329 | 146 / **263** / 332 |
| backswing / downswing | 1075,0 / 491,7 ms | **975,0 / 575,0 ms** |

`down_the_line` tenía top 327 y un downswing de 41,7 ms: son exactamente los
números que ADR-017 predijo. Y con la escala nueva, `pelvis_sway_top_cm` del
ejemplo pasa de −19,4 a **−18,0** contra una verdad 3-D de −17,69: el sesgo de
la medición sola baja de −1,71 a **−0,31 cm**.

### 6 · Se sirve, y sólo donde tiene que estar

`curl` contra un backend propio en el 8766 (el del 8765 quedó como estaba, es de
otra sesión): `GET /api/datos/ejemplo-cmu-64_01-face_on/archivos/pose3d.json` →
**200**, `application/json`, **251.649 bytes**, y el JSON llega entero
(448 × 26 × 3). `GET .../archivos/pose.npz` sigue dando **404**: la lista blanca
no se ablandó. Un trabajo de celular (`cortado.mp4`) **no** lista `pose3d.json`
y pedirlo da 404 — el visor no aparece ahí, que es el punto.

### 7 · Mutación manual (ADR-011, invariante 15)

**5 de 5** en `mocap.py` hacen fallar al menos un test: el suelo con `argmax`
en vez de `argmin` (1 test), fps + 1 (2), x espejada al escribir los puntos (3),
redondeo a centímetros en vez de milímetros (3), y las dos cámaras siendo la de
`face_on` (2). **4 de 4** en el TypeScript rompen la verificación: grados por
radianes en la órbita, `d = r × f`, `r = (0,1,0) × f`, y la focal fija en el
indicador. **La cuarta no se cazaba** con la verificación original: pasa porque
en las dos vistas del protocolo la focal del zoom **es** la del archivo. Se
agregó el chequeo de invariancia al zoom —en las dos implementaciones— y ahí
falla.

## Queda abierto

1. **El suelo del visor es el cero del trial, no el piso anatómico.** `y = 0` es
   el punto más bajo de **todo** el trial (la punta del pie izquierdo en el
   cuadro 426, ya en el acompañamiento) y en el address los pies quedan
   **8,9 cm** por encima: el esqueleto de CMU no apoya la planta y deja el
   tobillo a ~15 cm del cero. Está medido y declarado dentro del archivo
   (`suelo`) y la pantalla lo dice. **No toqué `to_harness_frame`**: ese marco es
   el de todas las métricas en cm y moverlo movería todo. Se cruza con el
   +4,4 % residual de la escala que el PLAN ya tiene anotado.
2. **No hay test permanente del lado del navegador.** `pose3d.verificar.mjs` se
   corre a mano (`cd web && node --experimental-strip-types
   src/lib/pose3d.verificar.mjs`, previo volcado del `pose.npz` a JSON, que el
   propio script explica). Montar un runner en `web/` es ADR-015. El guardián
   permanente es el test de Python, que fija la fórmula que el TypeScript
   transcribe; el `.mjs` es lo que verifica la transcripción.
3. **La pantalla no se abrió** (regla de trabajo). Sin verla, lo que más puede
   fallar: el alto del recuadro vertical sumado a todo lo que ya hay arriba, y
   el foco del teclado (las flechas mueven el visor sólo con el recuadro
   enfocado; se maneja en el propio div con `stopPropagation` para no mover el
   reproductor de arriba a la vez).
4. **El visor no dibuja el palo** —el mocap no lo tiene— **ni una traza de las
   manos**, que es lo que haría ver el plano del swing en 3-D. No estaba pedido.
5. **Nada sincroniza el visor con el reproductor de arriba**: cada uno con su
   línea de tiempo y su cuadro.

## Para que pruebe Hernán

Los ejemplos ya están regenerados en `data/exploracion/`. Si hiciera falta:

```bash
cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista face_on --out ../data/exploracion/ejemplo-cmu-64_01-face_on --nivel1 --etiqueta "ejemplo · mocap CMU 64_01 · cámara virtual · no es video · fps 120 exacto por construcción"
```

El backend del 8765 es de otra sesión y **no tiene este código**: hay que
reiniciarlo, o el visor no va a aparecer (la lista blanca es del backend).

```bash
.venv/bin/python -m service
```

```bash
cd web && pnpm dev
```

1. **Abrí `ejemplo-cmu-64_01-face_on`** en «Trabajos anteriores y ejemplos».
   Abajo de las tres fotos por evento, antes de «Con este archivo», tiene que
   aparecer **«El swing en 3-D, para girarlo»**, con el recuadro verde arriba:
   de dónde sale, que no es un video ni tu swing, y en ámbar que **esto no se
   puede hacer con un clip de celular**.
2. **Girá**: arrastrá sobre la escena. Arriba a la derecha el azimut y la
   elevación; arranca en **0° / 5°**, que es `face_on`. Arriba a la izquierda,
   siempre, `mocap CMU 64_01 · marcadores ópticos · no es video`.
3. **El indicador, que es lo que hay que mirar.** Arranca en el address. Con el
   azimut en 0° tiene que decir **caderas ~100 % · hombros 100 %**. Girá hacia
   **−90°** (arrastrando a la derecha) y la línea de caderas tiene que **caer a
   ~4 %**, con el párrafo ámbar apareciendo debajo: desde ese ángulo esa línea no
   se puede medir. Volvé a 0° y sube de nuevo.
4. **«ver como down_the_line»** hace lo mismo de un clic y deja la cámara
   exactamente donde la pone el protocolo. Desde ahí, la escena tiene que
   parecerse al video con palitos del ejemplo `down_the_line` (está medido: los
   puntos caen a menos de 1 px de donde los midió el motor).
5. **Andá al top** (botón «top») y volvé a mirar el indicador desde
   `down_the_line`: ahora la línea de caderas da **~76 %**, porque ya giró. Eso
   es la explicación entera de por qué cada medición declara su vista.
6. **Los controles**: reproducir, pausa, ◀ ▶ cuadro a cuadro, velocidad (arranca
   en 0,25×), rueda para acercar, «1:1» para volver. Las flechas del teclado
   mueven el visor **sólo si hiciste clic en la escena** (si no, mueven el
   reproductor de arriba, que es lo que se quería).
7. Si al girar algo se sale del cuadro (las manos en el top, en algunos
   ángulos), la rueda hacia abajo lo trae: medido, con 0,3× entra todo en todos
   los ángulos.
8. Abrí después **`ejemplo-cmu-64_01-down_the_line`**: el visor es el mismo (los
   puntos 3-D no dependen de la vista) y **el top ya está bien**: 263, no 327, y
   el downswing 575,0 ms en vez de 41,7.
9. Y en un clip tuyo (`cortado.mp4`, `vid1.mp4`): el visor **no tiene que
   aparecer**. No es un olvido.

## Preguntas para el orquestador

1. **¿`pose3d.json` entra a `CONTRATO.md`?** Hoy es un archivo del arnés en una
   carpeta de exploración, con su propio `schema` declarado adentro, y el
   contrato no lo menciona. Si alguna vez un video produjera 3-D (dos cámaras
   calibradas, el camino que el PLAN ya dejó anotado), ahí sí habría que
   ponerlo en §Layout con su versionado.
2. **¿El visor y el reproductor se sincronizan?** Hoy son dos líneas de tiempo
   independientes. Un solo cuadro para los dos sería mejor para enseñar («mirá
   el video y ahora mirá lo mismo en 3-D»), y es trabajo en `page.tsx` y en
   `Reproductor.tsx`, que es de ADR-014.
3. **Los 8,9 cm entre los pies y el cero del suelo**: ¿se queda la grilla como
   «el cero del trial» (hoy, declarado y medido), o hace falta un punto de
   contacto con el suelo? Es la misma pregunta que el +4,4 % residual de la
   escala del 14, y la respuesta debería ser una sola.
4. **¿Traza de manos en 3-D?** Dejar dibujada la curva que recorren las manos en
   todo el swing es lo que haría ver el plano del swing. Son ~15 líneas y no
   inventa ningún dato, pero no estaba pedido.

## Commits

- `1240ebb` — `pose3d.json` en el arnés, la lista blanca, el visor y sus tests.
- el de cierre, con `ESTADO.md` y este informe.
