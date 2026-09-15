# captura-docs — 2026-09-15

**Encargo:** meter en los documentos de captura lo que midieron el 07 y el 11
—4K desaconsejado, el 80–90 % de encuadre inalcanzable en vertical, WhatsApp
documento limpio, ningún modo Video del S22 llega a 100 fps— y arreglar el test
de `service/` que caducaba por fecha. Sólo documentos y un test; ni motor, ni
`service/`, ni `web/`, ni umbrales del gate.

## Hecho

- **`CAPTURA.md`**, cuatro secciones:
  - **§Presupuesto de datos**: dos filas medidas nuevas (UHD 60 HEVC del S22
    **desaconsejado**, y Video FHD 30 H.264 como referencia), columna
    `Procedencia` en la tabla, y una subsección **«UHD 60 está desaconsejado, y
    está medido por qué»** con los tres números.
  - **§Encuadre**: el 80–90 % pasa a **objetivo** con la nota medida del 07
    (focal de 3078 px, ~2,1× la lente principal; con un celular habría que
    estar a ~0,8 m) y los cuatro valores reales del 11 (28,2 / 28,7 / 29,5 % en
    UHD, 41,9 % en FHD). Regla de campo: lo más cerca que permita tener pies y
    palo del top adentro. **Sin umbral fijado**: sale del barrido de tamaño del
    arnés (encargo 13).
  - **§Transferencia**: la fila de WhatsApp de la tabla de terceros pasa a
    «**WhatsApp como video**», y se agrega una tabla **medida** del S22 con tres
    filas —cable (referencia), WhatsApp documento (intacto), WhatsApp video
    (recomprimido, no medido acá)—, cada una con su procedencia.
  - **§Lo que queda por verificar**: se parte en «Con el Galaxy S22 Ultra» y
    «Con el iPhone». El bloque nuevo dice que ningún modo Video del S22 llega a
    100 fps y que el cronómetro en Slow motion FHD 240 es la única llave.
- **`docs/filmacion-s22.md`** reescrita entera (la guía que recibe quien filma).
  Cinco líneas de qué dice ahora, al pie.
- **`docs/checklist-captura.md`**: sincronizado en los tres puntos donde quedaba
  contradiciendo a `CAPTURA.md` (encuadre, WhatsApp, distancia fija de 3,5 m) y
  con una cabecera que dice que es la hoja del protocolo iPhone y que la del
  S22 es `docs/filmacion-s22.md`.
- **`tests/test_service.py`**: la fecha del ejemplo de
  `test_datos_lista_un_ejemplo_de_otro_proceso` es ahora `now + 1 min`, no
  `"2026-09-14T12:00:00+00:00"`. Dos líneas y un `import datetime as dt`.

Commits: ver al cierre.

## Probado

- **`.venv/bin/pytest -q tests/test_service.py`: 55 en verde, 23,0 s.** Antes
  de tocarlo: 54 verdes y 1 rojo
  (`test_datos_lista_un_ejemplo_de_otro_proceso`,
  `assert ['subida', 'ejemplo'] == ['ejemplo', 'subida']`). Reproducido en rojo
  primero, arreglado después.
- **Suite entera del motor: 264 en verde, 40,6 s.** Arnés (`truth/`): **13 en
  verde**. Los dos números incluyen trabajo sin commitear de las sesiones 13,
  14 y 15, que estaban corriendo en paralelo sobre `kinelab/metrics/core.py`,
  `kinelab/events/primitives.py`, `sports/golf/events.py`, `tests/test_fase2.py`
  y `truth/`. Lo único que toqué yo de código es el test de arriba, y su archivo
  no lo tocó nadie más (verificado con `git diff tests/test_service.py`).
- **Los tamaños de la tabla de presupuesto los medí acá**, con `ffprobe` sobre
  los dos clips reales, porque el 11 no los había puesto en MB:

  | | tasa del contenedor | por 30 s | 20 clips |
  |---|---|---|---|
  | `vid1.mp4` — UHD 60 HEVC | 43,9 Mb/s | **165 MB** | ~3,3 GB |
  | `20260907_170638.mp4` — FHD 30 H.264 | 18,2 Mb/s | **68 MB** | ~1,4 GB |

  **Eso da 2,4× de disco, no 3,4×.** El informe del 11 reportó 3,4× y no se
  reproduce: 97.860.899 B / 17,852 s contra 20.455.993 B / 9,002 s son 2,41×, y
  la tasa de video sola (43,10 contra 17,42 Mb/s) da 2,47×. Los demás números
  del 11 que entraron a los documentos —2,15× por cuadro, 4,29× por segundo de
  movimiento real, bbox 1340 px en FHD y 1466–1550 en UHD contra los 256 px de
  entrada, los cuatro porcentajes de encuadre— se reprodujeron sin cambio.
  `CAPTURA.md` lleva **2,4×**, con la aclaración de que la comparación no es a
  igualdad de todo (HEVC a 60 contra H.264 a 30) y una nota de una línea de que
  el 11 había dicho 3,4×.
- **Los tres documentos leídos de punta a punta al terminar**, y contra
  `CAPTURA.md` fila por fila. De ahí salieron tres arreglos que el prompt no
  pedía pero que eran contradicciones abiertas: el `~3,5 m` de `down_the_line`
  (en `CAPTURA.md` §Encuadre y en el checklist) chocaba con la regla nueva de
  acercar el trípode; el encabezado de §Transferencia decía «un solo camino:
  AirDrop del iPhone» justo arriba de una tabla del S22; y el checklist decía
  «Nunca: … WhatsApp» sin distinguir los dos modos.

### Qué dice ahora la guía, en cinco líneas

1. **Lo más importante de la hoja es el cronómetro en Cámara lenta FHD 240**,
   y está dicho en el segundo párrafo: sin ese clip el programa rechaza todo,
   porque el teléfono no pasa de 60 fps y hacen falta 100.
2. **Filmá en FHD 60, no en 4K**, con el porqué en una línea: el programa achica
   el recorte del cuerpo a 256 px igual, así que 4K sólo pesa y tarda más del
   doble.
3. **El cronómetro es el paso 1** (Cámara lenta FHD 240) **y el paso 2** (Video
   FHD 60), cada uno con su lista: 10–15 s, sin editar ni recortar en Galería,
   el archivo entero, y **por el mismo camino por el que después van los
   swings**.
4. **El encuadre ya no se mide en metros**: lo más cerca que permita tener los
   pies y el palo del top adentro. Los tres clips salieron al 28 % del alto y
   hace falta bastante más; los 3 y 3,5 m que decía antes quedaron afuera.
5. **Mandar los archivos: cable primero; WhatsApp como documento, sí** —medido,
   no toca el archivo—; **WhatsApp como video, nunca**, ni Telegram ni Drive
   desde la app de fotos.

## Queda abierto

- **La pregunta 1 del informe del 11 sigue abierta y no era mía**: con este
  teléfono, o se filma el cronómetro de Slow motion FHD 240, o se baja el
  `fps_min` de golf con una decisión escrita. Los documentos ahora **dicen el
  hecho** (ningún modo Video llega a 100; Slow motion 240 es la única llave) y
  **no deciden nada**: no toqué `sports/golf/`.
- **Tres lugares fuera de mis cuatro archivos siguen diciendo el 80–90 % o los
  3,5 m sin la nota medida.** No los toqué (no son míos, y hay sesiones en
  paralelo):
  - `DECISIONES.md:42` (ADR-002) — «el cuerpo puede ocupar 80–90% del cuadro»,
    como argumento de por qué golf antes que pádel. Con la medición del 07 el
    argumento se debilita pero no se cae: el golfista quieto sigue permitiendo
    acercar la cámara mucho más que un jugador de pádel. Lo toca el encargo 15.
  - `ARRANQUE.md:80` — «trípode a 3,5 m detrás».
  - `truth/kinelab_truth/harness.py:32` — el comentario de `distance_m` cita el
    80–90 % como «el protocolo». Lo toca el encargo 13.
- **`docs/checklist-captura.md` sigue siendo la hoja del iPhone**, con un clip
  de 1080p120 + AirDrop que en esta Mac no existe. Le puse la cabecera que
  manda a la guía del S22, pero no la reescribí: no estaba en el encargo, y
  reescribirla ahora la dejaría desactualizada de nuevo apenas se sepa en qué
  modo se filma de verdad (depende del cronómetro de 240).
- No verifiqué en el teléfono el camino de menú de WhatsApp («Adjuntar →
  Documento»): eso lo dijo Hernán y lo confirmó la medición del archivo, no una
  pantalla.

## Para que pruebe Hernán

Nada de front. Dos cosas:

```bash
.venv/bin/pytest -q tests/test_service.py
```
55 en verde. Antes de este encargo daba 1 rojo, y el rojo volvía solo cada día
que pasaba.

Y lo otro es leer `docs/filmacion-s22.md` con ojos de quien va a filmar: es la
hoja que se le manda a esa persona. Lo que hay que mirar, en orden: (1) que el
párrafo de arriba deje claro que **el cronómetro en Cámara lenta es lo único
imprescindible**; (2) que la sección 2 se pueda seguir sin saber nada del
proyecto; (3) que la regla de encuadre («lo más cerca que permita tener los
pies y el palo adentro») sea ejecutable con un trípode en un driving range; y
(4) que el paso de WhatsApp como documento esté descripto como está el menú de
tu teléfono.

## Preguntas para el orquestador

1. **El 3,4× de disco del informe del 11 queda corregido a 2,4×** en
   `CAPTURA.md`, con la nota. Si preferís que la corrección vaya también al
   informe del 11 o a `docs/PLAN.md` (que lo repite en la línea 21), decilo:
   no toco informes ajenos ni el plan.
2. **El checklist iPhone**: ¿se reescribe como checklist del S22 cuando esté el
   cronómetro de 240, o se lo deja como está y la hoja operativa pasa a ser
   `docs/filmacion-s22.md`? Hoy son dos documentos para el mismo trabajo, con
   dos teléfonos distintos.
3. **ADR-002 cita el 80–90 % de encuadre como una de las cinco razones de
   «golf primero».** Con el 07 medido, ese 80 % no es alcanzable en vertical con
   la lente principal. No creo que cambie la decisión —el resto de las razones
   aguantan y el golfista quieto sigue dejando acercar la cámara—, pero el
   número que cita el ADR ya no es el que dice `CAPTURA.md`.
