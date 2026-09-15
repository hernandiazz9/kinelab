# kinelab — Captura

El protocolo de filmación y el gate de ingesta. El primero es para el humano;
el segundo lo hace cumplir el motor. La ventaja del golf — jugador quieto,
cámara repetible, dos vistas ortogonales — **existe sólo si el motor la exige
y rechaza la toma cuando no se cumple**. Si el gate acepta una toma de 60 fps
en una sola vista con el jugador al 15% del cuadro, se reproduce el prototipo
anterior con otro deporte.

---

## Por qué el archivo no puede decir su propio fps

Medido en esta Mac con ffprobe 9: un clip real de 240 fps (480 cuadros en
2,00 s) reporta `r_frame_rate=240`. El mismo clip con los timestamps
estirados ocho veces reporta `r_frame_rate=30/1`, `avg_frame_rate=30,05`,
`duration=15,97` — **y conserva los 480 cuadros**. Un tercer clip realmente
remuestreado a 30 fps reporta los mismos campos y tiene 62 cuadros. Los deltas
de PTS de los dos últimos son idénticos: 0,033333 s uniformes.

Ni `r_frame_rate`, ni `avg_frame_rate`, ni el histograma de deltas separan
"preservado pero lento" de "destruido". Sólo el conteo de cuadros contra una
duración real conocida.

**Y un solo delta de arranque no es tasa variable.** Medido en el original del
Galaxy S22 Ultra (265 cuadros): 263 deltas de 0,0333 s y **uno** de 0,2015 s,
el primero — la cámara tarda en entregar el segundo cuadro. Contado entero, el
clip daba ratio 6,04 y reproducía a 29,436 fps en vez de 29,998: los tiempos,
1,9 % largos, y el gate lo habría rechazado por tasa variable. Por eso el gate
y el motor trabajan con el ratio y el fps **efectivos** — sin el primer delta,
y sólo cuando ése es el único fuera de lugar —, guardan los brutos al lado en
`capture.json` (`vfr_ratio_raw`, `fps_playback_raw`, `first_delta_s`,
`fps_note`) y lo dicen en el registro del chequeo. En un clip realmente de tasa
variable, el efectivo es el bruto: no se perdona nada. Ver el informe
`docs/informes/2026-09-14-03-fps-truth-primer-delta.md`.

Por eso:

1. La tasa real de cada camino se mide **una vez** con un cronómetro filmado y
   se guarda en `capture-paths.yaml`.
2. El gate compara la tasa de reproducción del clip (de sus PTS) contra la
   `fps_playback` del camino declarado, con tolerancia de 2%, y usa el
   `stretch_factor` del camino para pasar a tiempo real.
3. Nunca se "repara" el fps con `-r`: tira cuadros. `setpts` los conserva.

---

## Configuración del teléfono (una vez; después no se toca)

Para iPhone 17 Pro / 18 Pro. Otros modelos: el cronómetro decide qué modos
sirven.

| Ajuste | Valor | Por qué |
|---|---|---|
| Cámara → Formatos | **Alta eficiencia (HEVC)** | "Más compatible" (H.264) **deshabilita 240 fps por completo**, sin aviso. |
| Cámara → Grabar video | **1080p a 120 fps** | Modo Video normal: CFR a tasa de captura, sin edit list, sin retiming. |
| Fotos → Transferir a Mac o PC | **Mantener originales** | "Automático" autoriza al teléfono a transcodificar durante la transferencia. |
| Pantalla → Bloqueo automático | Nunca (durante la sesión) | |
| Editor de Fotos → Velocidad de reproducción | **No tocar** | Compartir después de cambiarla hornea la velocidad elegida. |

**Modo por defecto: Video 1080p120.** Slo-Mo 1080p240 sólo para un bloque de
impacto marcado como tal en el nombre del clip; el cronómetro tiene que
haberlo calibrado también.

**4K120 está descartado por spec**, no por opinión: ~3,5 GB por clip de 30 s y
multiplica el tiempo de inferencia.

---

## Luz y obturador: el límite real

A 240 fps la exposición está topeada en 1/240 s; a 120, en 1/120 s. Con buen
encuadre (cuerpo de 918 px en un cuadro de 1080), el desplazamiento de la mano
durante la exposición, calculado:

| Velocidad de la mano | 1/240 s | 1/500 s | 1/1000 s | 1/2000 s |
|---|---|---|---|---|
| Golf, 10 m/s | 21,2 px | 10,2 px | 5,1 px | 2,6 px |
| Pádel, 20 m/s | 42,5 px | 20,4 px | 10,2 px | 5,1 px |

**Regla: obturador de 1/1000 s o más corto, o sea desenfoque ≤ 5 px.** La
cámara nativa no da control de obturador; la única palanca es la luz.

- **Golf al aire libre, de día, sin contraluz**: con ~20.000 lux el teléfono
  elige ~1/2000 s a ISO bajo. Sale gratis.
- **Si hace falta garantizarlo**: Blackmagic Camera (iOS, gratis) a 1080p120
  con ángulo de obturación bloqueado en ~20° (≈ 1/2160 s). No da 240 en iOS.
- **Pádel indoor a 500 lux**: llegar a 1/2000 s exige ISO ~3200 en un sensor
  de celular. No intentar 240 fps ahí; 1080p120 apuntando a 1/1000 s (ISO
  ~1600) y aceptar 120 Hz, o agregar luz.

Más fps con la muñeca borrosa es peor que menos fps con la muñeca nítida.

---

## Encuadre

- **Objetivo: el atleta ocupa 80–90% del alto del cuadro**, 900+ px de cuerpo
  a 1080p. El prototipo anterior trabajó con 116–135 px (11–16%) y ahí dos
  píxeles de error en el codo son grados.

  **Nota medida: en vertical, con la lente principal de un teléfono, ese 80% no
  es alcanzable a una distancia usable.** Poner el cuerpo al 80% de un cuadro
  de 1080×1920 a 3 m pide una focal de **3078 px**, ~2,1× la cámara principal
  de un celular (que a 1080 de ancho anda por 816 px): con esa lente habría que
  estar a ~0,8 m, o filmar horizontal (informe del 07, punto 6). Los cuatro
  clips reales del Galaxy S22 Ultra salieron muy por debajo: **28,2 / 28,7 /
  29,5%** del alto en Video UHD 60 y **41,9%** en Video FHD 30 (informe del
  11). El objetivo se mantiene como objetivo; la regla de campo mientras tanto
  es **acercar el trípode todo lo que permita tener los pies y el palo del top
  adentro del cuadro**.

  **El umbral del gate no está fijado, y no se fija a ojo.** Lo que el motor
  mide es `body_height_px` —altura del cuerpo en píxeles—, no la fracción del
  cuadro; el número que decide sale del barrido de tamaño de sujeto del arnés
  (`truth/`, encargo 13, en curso), que dice a partir de qué altura en píxeles
  la métrica deja de estar por encima de su piso de ruido. Hasta que ese
  barrido exista, `body_height_frac` (ESPECIFICACION 1.3) sigue sin umbral.
- Trípode. Cámara a **altura de cintura a pecho**.
- Dos vistas, cada una su propia sesión:
  - **`face_on`**: cámara perpendicular a la línea de tiro, mirando al pecho
    del golfista. Da giro, forward/side bend, sway, lift, cabeza.
  - **`down_the_line`**: cámara detrás del golfista, sobre la línea de tiro,
    a la distancia que fija la regla de arriba (esta sección decía ~3,5 m: con
    el teléfono vertical eso dio 28% del alto). Da thrust e inclinación
    aparente de columna. Desde acá la columna "parece" inclinada por
    combinación de giro y side bend, no por flexión — por eso las métricas
    declaran vista.
- Fondo simple, sin otras personas en cuadro. Una persona.
- Cuerpo entero, incluidos pies y palo en el top.

---

## Transferencia

**Un camino de referencia por dispositivo, y ninguno más en producción: en
iPhone, AirDrop a la Mac con "Mantener originales" activo; en el Galaxy S22
Ultra, el cable desde `DCIM/Camera`.**

Escalera de degradación reportada por terceros para un Slo-Mo de 240 fps (una
sola fuente, versión de macOS no declarada — **re-verificar con el cronómetro
antes de confiar**):

| Camino | fps que llega |
|---|---|
| AirDrop (Mantener originales) | 240 |
| Fotos → Edit with → QuickTime Player → guardar copia | 240 |
| **Arrastrar el clip desde Fotos** | **120** |
| **File → Export → Export 1 Video** | **30** |
| **WhatsApp como video**, Telegram, Drive, enlace de iCloud | recomprimido |

Los dos gestos más naturales son los dos peores.

**Medido acá, sobre el Galaxy S22 Ultra** (tres clips de Video UHD 60, informe
del 11). El teléfono que hay no es un iPhone y no tiene AirDrop:

| Camino | Qué llega | Procedencia |
|---|---|---|
| **Cable desde `DCIM/Camera`** | intacto: es una copia de archivo. **Es el camino de referencia** de este teléfono, y el original FHD 30 que llegó así es contra el que se comparó lo demás | informe del 03 |
| **WhatsApp como documento** | **intacto**: HEVC `hvc1` a 43–47 Mb/s, el `udta` de Samsung entero (1,02–1,10 MB) y el mismo orden de hijos del `moov` que un original por cable. WhatsApp en modo documento **no toca el archivo** | medido, informe del 11 |
| **WhatsApp como video** | recomprimido: H.264 de pocos Mb/s, sin `udta`, resolución bajada | **no medido acá**: es el comportamiento conocido del envío como video, `sin_verificar` |

Que el modo documento salga limpio **no lo convierte en el camino de
producción**: es un camino distinto, con su propio `id` en
`capture-paths.yaml` (`s22ultra-video-uhd60-whatsapp-doc`), y su tasa real
sigue sin cronómetro como cualquier otro. El cable sigue siendo la referencia
porque no depende de que una app de terceros no cambie de criterio entre
versiones.

Camino de auditoría, no de uso diario: `libimobiledevice` + `ifuse` + `rsync -a`
sobre `DCIM`. No probado en esta Mac.

---

## Calibración con cronómetro (antes del primer clip real)

Por **cada** combinación de modo y camino de transferencia:

1. Filmar 10 s de un cronómetro con milisegundos (o un LED a frecuencia
   conocida) llenando el cuadro.
2. Transferir por el camino a calibrar.
3. `python -m kinelab.tools.fps_truth clip.mov --duracion-real <segundos entre dos lecturas del cronómetro>`
4. Anotar en `capture-paths.yaml`: `fps_real` (captura), `fps_playback`
   (reproducción, de los PTS), `stretch_factor`, `delta_max/delta_min`, codec,
   fecha, quién. `fps_truth` imprime los cinco.

Eso resuelve tres cosas de una vez: si el camino conserva los cuadros, si el
teléfono entregó de verdad lo que dice (hay reportes de 240 nominales grabando
114–227 reales), y cuál es el factor de estiramiento si el archivo viene
retimeado.

---

## Caminos declarados sin calibrar (ADR-016)

El cronómetro es la única forma de saber la tasa de captura, y hasta que se
filme no hay ninguna. Lo que sí se puede hacer es **declarar** el camino:
`calibrated: false` en `capture-paths.yaml`, dispositivo y modo dichos por el
usuario, los seis campos del cronómetro (`fps_real`, `fps_playback`,
`stretch_factor`, `fps_method`, `calibrated_on`, `calibrated_by`) en `null`.

| | camino calibrado | camino declarado |
|---|---|---|
| `fps_real` | del cronómetro filmado | **se asume** igual al `fps_playback` efectivo |
| `stretch_factor` | medido (1,0 en video, 8,0 en un Slo-Mo de 240 a 30) | 1,0 por supuesto |
| `fps_provenance` | `medido_aqui` | `sin_verificar` |
| juicio | posible, si hay MDC | **nunca** |
| modos | `video` y `slomo` | sólo `video` |
| `nominal_fps`, `codec_expected` | obligatorios | opcionales (`null` = no se sabe) |

El supuesto es exactamente uno: **que el archivo reproduce a la velocidad a la
que capturó.** Es cierto en un modo Video normal y falso en cualquier cosa
retimeada, y el archivo no puede decir cuál de las dos es (§Por qué el archivo
no puede decir su propio fps). Por eso se declara y se muestra, no se infiere:
la frase viaja al registro del chequeo `capture_path_known`, al `capture.json`
(`fps_provenance`, `capture_path_calibrated`), al `header` del `analysis.json`,
a cada métrica, y a `warnings[]` antes de cualquier número.

Un camino `slomo` sin calibrar **se rechaza**: ahí el supuesto es falso por
construcción y el factor de estiramiento es desconocido, así que cualquier
tiempo sería ficción. No hay número que poner.

Hay un camino genérico, `desconocido-video`, para "no sé con qué se filmó". Es
el default del modo exploración (`python -m kinelab datos VIDEO`).

Declarar **no ablanda ningún umbral**. Medido en el original del Galaxy S22
Ultra con `s22ultra-video-fhd30-cable`: ocho de nueve chequeos pasan —por
primera vez `capture_path_known` entre ellos— y el clip se rechaza igual por
`fps_min_for_gesture`, 30 fps de captura contra los 100 que pide golf.

Filmar el cronómetro de ese dispositivo y ese modo convierte el camino en
calibrado; los clips ya ingestados se re-analizan (invariante 18) sin volver a
correr el modelo (invariante 1).

---

## El gate de ingesta

Bloqueante. Cada chequeo tiene id, resultado, valor y una frase para el
entrenador. Orden de evaluación fijo; el primero que falla ya decide `reject`,
pero se reportan todos.

| id | Regla | Frase al fallar |
|---|---|---|
| `capture_path_known` | `capture_path_id` existe en `capture-paths.yaml`. Calibrado pasa liso; **declarado pasa y lo dice** en su propio registro; un `slomo` declarado no pasa | "Este camino de captura no está en capture-paths.yaml. Declaralo (dispositivo y modo) o filmá el cronómetro." · "El camino es Slo-Mo y no está calibrado: sin cronómetro el factor de estiramiento es desconocido y cualquier tiempo sería ficción." |
| `codec_matches_path` | `codec == camino.codec_expected`; **`null` si el camino no declara codec** | "El clip está en H.264 y el camino espera HEVC: pasó por 'Más compatible' o por un transcodificador." |
| `vfr_ratio_le_1_10` | `delta_max / delta_min ≤ 1,10`, **efectivo** | "El video tiene tasa variable. Volvé a exportarlo desde el original." |
| `fps_matches_path` | `abs(fps_playback − camino.fps_playback) / camino.fps_playback ≤ 0,02`, con el `fps_playback` **efectivo**; **`null` en un camino declarado**: no hay reproducción medida contra la que comparar | "El clip reproduce a N fps y el camino declara M. Algo lo recomprimió, o vino por otro camino." |
| `fps_min_for_gesture` | `fps_real ≥ sports.<g>.fps_min` (golf: 100). En un camino declarado el `fps_real` es el **asumido**, y el chequeo lo dice pase o falle | "A esta tasa no se pueden medir los tiempos del swing." |
| `duration_plausible` | 3 s ≤ duración ≤ 180 s | |
| `rotation_normalized` | rotación aplicada en `master.mp4`; ancho/alto reales | |
| `body_height_frac` (Fase 1) | `body_height_px / height ≥ umbral medido` | "El jugador ocupa X% del cuadro. Acercá la cámara." |
| `detection_rate` (Fase 1) | `≥ 0,90` | "Se perdió al jugador en el N% de los cuadros." |
| `single_subject` (Fase 1) | una sola persona de tamaño dominante | "Hay más de una persona en cuadro." |
| `view_declared` | `view ∈ sports.<d>.views` | |
| `gesture_known` | `gesture ∈ sports.<d>.gestures` | |

**Efectivo** quiere decir sin el primer delta de PTS, y sólo cuando ése es el
único fuera de lugar (ver arriba). Cuando el efectivo difiere del bruto, los
dos chequeos lo dicen en su propio registro aunque pasen — *"ratio 1.000 sin el
primer delta de 0.201 s (arranque de la cámara); bruto 6.044"* —, y
`capture.json` guarda los dos números. Nunca una corrección en silencio.

Un `reject` no borra nada: el clip queda en disco con su `capture.json` y sus
razones, para poder corregir y re-ingestar.

---

## Presupuesto de datos

| Modo | Tamaño por 30 s | Sesión de 20 clips | Procedencia |
|---|---|---|---|
| 1080p120 HEVC | ~85 MB | ~1,7 GB | sitio comercial (HEVCut) |
| 1080p240 HEVC | ~240 MB | ~4,8 GB | sitio comercial (HEVCut) |
| 4K120 | ~3,5 GB | descartado | spec |
| **UHD 60 HEVC (S22 Ultra) — desaconsejado** | **165 MB** | **~3,3 GB** | **medido, encargo 12** |
| Video FHD 30 H.264 (S22 Ultra) | 68 MB | ~1,4 GB | medido, encargo 12 |

Las dos primeras filas son de un sitio comercial, no de Apple: **re-medir con
el primer clip real de iPhone**. Las dos últimas están medidas sobre los clips
reales del Galaxy S22 Ultra (`ffprobe`, tasa del contenedor: 43,9 Mb/s en UHD
60, 18,2 Mb/s en FHD 30).

### UHD 60 está desaconsejado, y está medido por qué

Tres números, de los tres clips del 14/9 (informe del 11):

1. **No agrega precisión.** El recorte del cuerpo entra a `rtmpose-m`
   reescalado a **192×256 px**. El bbox mide 1340 px de alto en el clip FHD
   —**5,24×** de reducción, ya sobredimensionado— y 1466–1550 px en los UHD
   (**5,7–6,0×**). Los píxeles de más se tiran antes de que el modelo los vea.
2. **Cuesta 2,15× por cuadro.** FHD: 5,46 s fijos + 30,8 ms/cuadro. UHD:
   5,82 s + 66,2 ms/cuadro. Por segundo de movimiento real, UHD 60 contra
   FHD 30, son **4,29×**: vid1 son 17,8 s de video en 76,4 s de proceso.
3. **Cuesta 2,4× de disco**: 43,9 contra 18,2 Mb/s, o 165 contra 68 MB por cada
   30 s. No es una comparación a igualdad de todo lo demás —el UHD es HEVC a
   60 fps y el FHD es H.264 a 30—, pero es la que hay con material real. (El
   informe del 11 reportó 3,4× de disco; recontado sobre los mismos dos
   archivos da 2,4×. El resto de sus números se reprodujo sin cambios.)

Consecuencia práctica: **filmar en FHD y acercar el trípode.** Son dos cosas
distintas y hay que hacer las dos. Bajar de UHD a FHD deja de pagar peso y
tiempo por píxeles que el modelo tira, pero no es lo que arregla el encuadre:
eso lo arregla la distancia. (Cuánto cambia la fracción del cuadro entre los
dos modos no está medido: en el S22 no tienen la misma relación de aspecto
—2320×1080 en FHD contra 3840×2160 en UHD— y los cuatro clips se filmaron a
distancias distintas.)

---

## Lo que queda por verificar con el primer clip real

### Con el Galaxy S22 Ultra, que es el teléfono que hay

- **Ningún modo *Video* del S22 Ultra llega a 100 fps.** El tope de Video es
  60: FHD 60 y UHD 60 (declarado por la lista de modos del teléfono; medido
  60,026 fps de reproducción en los tres clips UHD del 11 y 29,998 en el FHD
  del 03). Golf pide `fps_min` 100, así que **todo lo que se filme en Video se
  rechaza**, con el camino calibrado o declarado: declarar no ablanda ningún
  umbral.
- **El único modo que puede pasar de 100 fps es Slow motion FHD 240**, que en
  Android llega con la ralentización horneada (ADR-003) y que ADR-016 rechaza
  sin calibrar. De las dos cosas juntas sale la única conclusión operativa que
  hay hoy: **el cronómetro filmado en Slow motion FHD 240 es lo único que puede
  producir un clip de este teléfono que pase el gate.** No es un trámite
  pendiente; es la llave. La alternativa —mover el `fps_min` de golf— es una
  decisión escrita, no un ajuste.
- Cuánto mide el delta de arranque en Slow motion FHD 240, y si el archivo es
  uniforme por tramos. Medido en los otros dos modos: **0,2015 s** en FHD 30
  (informe del 03) y **0,073–0,110 s** en UHD 60 (informe del 11); en los dos,
  el primero es el único delta fuera de lugar.
- Si el S22 cambia campo de visión o estabilización entre modos: si lo hace, la
  calibración de un modo no es transferible a otro.

### Con el iPhone, si alguna vez hay uno

- La firma exacta de ffprobe sobre un `.MOV` de Slo-Mo real de iPhone (edit
  list, timestamps, metadata). No hay ninguno en esta Mac.
- Si AirDrop sigue conservando 240 fps en iOS/macOS actuales.
- Si el bug de 240 nominales → 114–227 reales sigue vivo en iPhone 17/18 Pro.
- Los bitrates reales de 1080p120 y 1080p240.
- Si el iPhone cambia campo de visión o estabilización entre modos: si lo
  hace, la calibración de un clip no es transferible a otro de la misma
  sesión.
