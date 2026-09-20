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
sirven. **El teléfono que hay es un Galaxy S22 Ultra y su configuración es
otra** —ningún modo *Video* suyo llega a los 100 fps de golf, así que el modo
por defecto ahí es *Slow motion* FHD 240 con el cronómetro en el cuadro—: la
hoja operativa de ese teléfono es `docs/filmacion-s22.md`.

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

  **La serie medida, en orden de aparición** — seis clips reales, todos del
  mismo teléfono, todos `face_on`:

  | clip | modo | cuerpo | % del alto | ¿pasa los 717 px? | informe |
  |---|---|---|---|---|---|
  | `vid1` · `vid2` · `vid3` | Video UHD 60 | 1104 · 1083 · 1132 px | **28,7 / 28,2 / 29,5 %** | sí · sí · sí | 11 |
  | `20260907_170638` | Video FHD 30 | 973 px | **41,9 %** | sí | 11 |
  | `Cortado-lenta` | Slow motion FHD 240 | 414 px | **21,6 %** — el peor | **no** | 24 |
  | `cortado3-lento` | Slow motion FHD 240 | **691 px** | **36,0 %** | **no**, por 26 px | 26 |

  El quinto es el peor de la serie y es justamente el que trajo la primera tasa
  de captura medida: el cronómetro se resolvió y el encuadre se perdió. El
  sexto, filmado una hora después en otro lugar, **recupera 14,4 puntos sin
  cambiar de modo** — 691 px de cuerpo contra 414. La regla de campo funciona
  cuando se aplica; lo que falta no es una lente, es el metro de trípode.

  **El umbral del gate son 717 px de cuerpo, y se mide en píxeles, no en
  fracción del cuadro.** Lo fijó el barrido de tamaño de sujeto del arnés
  (informe del 13, §3): con σ = 4,866 px —el mismo ruido absoluto que el
  nominal relativo al tamaño nominal de 811 px— `head_lift_top_cm` cruza su
  tolerancia de 5 cm a **717 px**, y es la métrica que manda porque la cabeza es
  el punto más ruidoso y su desplazamiento verdadero el más chico (3 cm). Le
  siguen `head_sway_top_cm` a 608 px y `thorax_sway_top_cm` a 552. Las cuatro
  duraciones, `tempo_ratio` y el sub-cuadro del impacto no cruzan nunca: su MDC
  es cuantización de cuadros, no tamaño.

  **Procedencia: `estimacion`.** Sale del arnés de **nivel 0** —una cadena
  cinemática proyectada con ruido gaussiano, sin estimador de pose— con la
  cámara virtual `iphone17pro-1080p120`, que no es el teléfono con el que se
  filma. Se revisa cuando haya σ por keypoint medido en material real. Que esté
  del lado conservador está medido: el jitter de la pose de `cortado3-lento`
  en HEAD es de **3,7 px en y**, con la deriva de la cabeza incluida, por debajo
  del σ nominal (auditoría del 16/9, §4).

  **La fracción sigue sirviendo para apuntar el trípode**, y por eso viaja
  dentro de la razón del chequeo: 717 px son el **37,3 % de 1920** en *Slow
  motion* FHD 240 (cuadro 1080×1920) y el **30,9 % de 2320** en *Video* FHD
  (cuadro 1080×2320). El mismo número de píxeles es una fracción distinta en
  cada modo, y ahí está por qué el umbral no puede ser una fracción: en 4K un
  28 % del alto son 1104 px, **más** que el 80 % de un 1080p (864 px). El
  80–90 % de esta sección queda como objetivo de campo.
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
- Fondo simple, sin otras personas en cuadro. Una persona. **Y nada más:**
  medido en `Cortado-lenta.mp4`, un carrito de golf parado a la derecha se
  detecta como persona en **8 de 598 cuadros** (0,0134 de la señal de
  multi-sujeto, contra un límite de 0,10). No rompió nada —el seguidor nunca lo
  siguió— pero es margen de `single_subject` gastado de gratis, y en un clip
  peor es el que elige el sujeto equivocado.
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

**Medido acá, sobre el Galaxy S22 Ultra** (las tres primeras filas, en los tres
clips de Video UHD 60 del informe del 11; la cuarta, en los tres clips de Slow
motion de los informes del 24 y del 26). El teléfono que hay no es un iPhone y
no tiene AirDrop:

| Camino | Qué llega | Procedencia |
|---|---|---|
| **Cable desde `DCIM/Camera`** | intacto: es una copia de archivo. **Es el camino de referencia** de este teléfono, y el original FHD 30 que llegó así es contra el que se comparó lo demás | informe del 03 |
| **WhatsApp como documento** | **intacto**: HEVC `hvc1` a 43–47 Mb/s, el `udta` de Samsung entero (1,02–1,10 MB) y el mismo orden de hijos del `moov` que un original por cable. WhatsApp en modo documento **no toca el archivo** | medido, informe del 11 |
| **WhatsApp como video** | recomprimido: H.264 de pocos Mb/s, sin `udta`, resolución bajada | **no medido acá**: es el comportamiento conocido del envío como video, `sin_verificar` |
| **Recorte hecho en la Mac** (QuickTime / Fotos) | **los cuadros parecen pasar sin recodificar** —los PTS son los del original, y los tres clips lentos comparten el mismo patrón de deltas hasta el décimo decimal (ratio 1,0027063599, los mismos 10 deltas distintos)— **pero se lleva todo lo demás**: el `udta` de Samsung de ~1 MB queda en 185 B (con él, `com.android.capture.fps` y las `com.samsung.*`), el handler pasa a `Core Media Video`, y un `elst` de QuickTime **esconde los primeros cuadros**: 14 de 612, 26 de 318, 4 de 2981 en los tres clips medidos | medido, informes del 24 y del 26 |

Que el modo documento salga limpio **no lo convierte en el camino de
producción**: es un camino distinto, con su propio `id` en
`capture-paths.yaml` (`s22ultra-video-uhd60-whatsapp-doc`), y su tasa real
sigue sin cronómetro como cualquier otro. El cable sigue siendo la referencia
porque no depende de que una app de terceros no cambie de criterio entre
versiones.

**Y el recorte en la Mac tampoco es un camino de producción, aunque hoy sea el
único calibrado.** Los tres clips lentos que existen llegaron recortados, así
que el cronómetro que se pudo leer calibró ese recorte y no el archivo del
teléfono: de ahí el `-recorte-mac` en el id del camino. Se recorta **después**
de ingestar el original, nunca antes.

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
5. Y pegar la última línea que imprime `fps_truth`,
   `calibration_clip_sha256: "…"`, que deja escrito **de qué clip salieron esos
   números**. Es opcional —un camino sin él sigue siendo válido— y es lo que
   después permite que cada toma diga si el fps que usa lo midió su propio
   archivo o lo heredó de otro. Hasta el 20/9 había que calcular ese sha
   aparte, y por eso nadie lo declaraba: el único camino calibrado del repo ya
   se había usado con **tres clips distintos** y nada lo decía.

Eso resuelve tres cosas de una vez: si el camino conserva los cuadros, si el
teléfono entregó de verdad lo que dice (hay reportes de 240 nominales grabando
114–227 reales), y cuál es el factor de estiramiento si el archivo viene
retimeado.

### El método preferido: el cronómetro DENTRO del cuadro del gesto

La toma aparte de los cuatro pasos de arriba tiene un supuesto escondido: que
el clip del cronómetro y el clip del swing salieron del **mismo** modo y del
mismo camino. Nadie lo verifica, y el archivo no puede decirlo (§Por qué el
archivo no puede decir su propio fps).

**Poner el cronómetro andando dentro del mismo cuadro que el gesto lo elimina:
el clip se calibra a sí mismo, porque el cronómetro y el gesto son el mismo
archivo.** Es el método por defecto en cualquier modo retimeado (`slomo`), y
la primera —y hasta hoy única— tasa de captura medida del proyecto salió así.

**Lo medido** (encargo 24, informe `docs/informes/2026-09-15-24-cronometro-y-swing-lento.md`;
clip `Cortado-lenta.mp4`, Galaxy S22 Ultra en *Slow motion* FHD, camino
`s22ultra-slomo-fhd240-recorte-mac`):

| | valor | cómo |
|---|---|---|
| `fps_real` (captura) | **240,15 fps ± 0,60** (1 σ) | ajuste por mínimos cuadrados sobre 39 lecturas del cronómetro; residuo rms 0,011 s |
| `fps_playback` (reproducción) | **30,0169 fps** | span de PTS, 598 cuadros en 19,8888 s |
| `stretch_factor` | **8,0005** | cociente de los dos: el slow motion está horneado ×8 |
| `vfr_ratio` | **1,0027** (CFR) | deltas de PTS |
| uniformidad | los tres tercios dan 238,38 / 239,66 / 242,73 fps, cada uno dentro de su propio 1 σ | y el residuo máximo de la recta acota a **1,3 cuadros de 598** cualquier tramo que hubiera sido capturado a velocidad normal |

Procedencia: `medido_aqui`. Es el único número del repo que habilita juicio
(ADR-016), y por eso está clavado en un test
(`tests/test_capture_paths.py::test_repo_has_the_calibrated_slomo_path_of_the_s22`).

**Tres cosas que hay que cuidar al filmarlo así**, las tres medidas en ese
mismo clip y escritas en `docs/filmacion-s22.md`:

- **El cronómetro tiene que estar ANDANDO.** El segundo clip del mismo día
  (`cartado2-lenta.mp4`, 292 cuadros) llegó con **00:00.00 en los 292 cuadros**:
  el cronómetro estaba reseteado y detenido, y no se pudo medir nada con él
  (encargo 26). Es el modo de falla más barato de cometer y el más caro de
  descubrir, porque el archivo se ve igual de bien.
- **A la distancia del golfista, plano y encarado, al brillo máximo.** En el
  clip que sí se pudo leer, el cronómetro estaba a ~20 cm del lente, la cámara
  enfocaba al golfista, los dígitos salieron de 35 px, desenfocados y girados
  23°, y hubo que alinear cuadro por cuadro para leerlos.
- **El refresco del cronómetro es el piso de ruido.** El de ese clip refrescaba
  **~15 veces por segundo**, no 100: cada meseta dura 10–22 cuadros y el valor
  salta 6 o 7 centésimas. Ahí está todo el ruido que quedó (2,7 cuadros de rms).
  Un cronómetro que refresque más rápido aprieta la medición.

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
| `calibration_clip_sha256` | **opcional**: de qué clip salió el cronómetro | prohibido: sin cronómetro no hay clip que lo mida |

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
| `duration_plausible` | 3 s ≤ duración **real** ≤ 180 s. **En un modo estirado, la duración real es la de reproducción dividida por el `stretch_factor`**: con el ×8 del S22, 3 s reales son 24 s de grabación (ver abajo) | "La toma dura N s reales; se esperan entre 3 y 180." |
| `rotation_normalized` | rotación aplicada en `master.mp4`; ancho/alto reales | |
| `body_height_px` (Fase 1) | `body_height_px ≥ sports.<d>.perception.body_height_px_min` (golf: **717**, procedencia `estimacion`; ver §Encuadre). **Píxeles, no fracción del cuadro.** La fracción viaja dentro de la razón, también cuando pasa — «691 px de cuerpo, 36 % del alto» | "El jugador mide N px de alto en el cuadro y hacen falta 717: acercá el trípode." |
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

**`duration_plausible` en cámara lenta: el umbral no se movió, y no se mueve.**
El primer clip con tasa calibrada (`Cortado-lenta.mp4`, encargo 24) pasó 8 de 9
chequeos y se rechazó por éste: 598 cuadros a 240,15 fps son **2,49 s reales**
contra los 3 que pide la regla. Con `stretch_factor` 8, llegar a 3 s reales
pide **≥ 721 cuadros, o sea ≥ 24 s de reproducción**. La salida fue **filmar
más largo, no bajar el número**: `docs/filmacion-s22.md` pide 25 s por toma, y
el clip siguiente del mismo modo y el mismo camino (`cortado3-lento.mp4`, 2977
cuadros, **12,40 s reales**) pasó **9 de 9** con `verdict: ok`. Bajar el mínimo
habría dado un número tan de ojo como el viejo; filmar diez segundos más costó
diez segundos.

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

**Contestado, y por eso ya no está en esta lista** (encargos 24 y 26):

- *Ningún modo* Video *del S22 llega a 100 fps, y Slow motion FHD 240 era la
  única llave.* Sigue siendo verdad y sigue escrito arriba (§Configuración,
  §Calibración); dejó de ser una pregunta el 15/9. El cronómetro se filmó,
  **Slow motion FHD 240 entrega 240,15 fps ± 0,60 de captura, uniforme,
  estirados ×8,0005**, y el camino `s22ultra-slomo-fhd240-recorte-mac` es el
  primer camino calibrado del repo (§Calibración con cronómetro).
- *Si el archivo es uniforme por tramos.* **Lo es**: los tres tercios caen
  dentro de su propio 1 σ y el residuo máximo de la recta acota a 1,3 cuadros
  de 598 cualquier tramo capturado a velocidad normal. El modo *Slow motion*
  (que no es *Super slow motion*) no mezcla velocidades.
- *Si un clip de este teléfono puede pasar el gate de ingesta entero.*
  **Puede.** Medido el 15/9 sobre `cortado3-lento.mp4` (2977 cuadros, 12,40 s
  reales, mismo modo y mismo camino): **9 de 9 chequeos, `verdict: ok`**, con
  `fps_provenance: medido_aqui` — el primer `capture.json` del proyecto que
  pasa.

  **Desde el 18/9 ya no pasa el gate completo, y el que falla es el encuadre.**
  Con `body_height_px_min = 717` puesto (encargo 17), la Fase 1 suma sus tres
  chequeos a ese mismo `capture.json` y el clip queda en **11 de 12**: 691 px de
  cuerpo contra 717, `verdict: reject`. Es el tercer umbral que este clip
  encuentra y el único que le falta: fps y duración ya los pasa. Lo que hay que
  mover sigue siendo el trípode, no el número. Lo único que había separado al clip anterior del gate era la duración:
  2,49 s reales contra los 3 que pide `duration_plausible`. **No se movió
  ningún umbral; se filmó más largo.** En ×8, 3 s reales son 24 s de
  grabación, y de ahí sale el mínimo de 25 s de `docs/filmacion-s22.md`.

  **Con una advertencia que conviene no perder: ese clip no trae cronómetro
  propio.** Pasó con la calibración del otro, y lo que el gate verifica de
  verdad es la **reproducción** (`fps_matches_path`: 30,0169 medidos contra
  30,0169 del camino, y los tres clips comparten el patrón de deltas hasta el
  décimo decimal). La **captura** no se verifica por clip: se hereda del camino
  que el usuario declaró. Es exactamente el supuesto que ADR-016 pide dejar
  escrito, y la única forma de eliminarlo es la de arriba — el cronómetro
  dentro del cuadro, en cada toma.

**Lo que sigue abierto:**

- **La tasa de captura sigue medida UNA sola vez, en UN solo clip.** El segundo
  clip lento del mismo día (`cartado2-lenta.mp4`) iba a ser la primera
  verificación independiente y **no pudo serlo: su cronómetro está detenido en
  00:00.00 en los 292 cuadros** (encargo 26). Lo que ese clip sí confirma es la
  tasa de **reproducción** —30,016952 contra los 30,0169 del camino, y el mismo
  patrón de deltas de PTS hasta el décimo decimal— pero la reproducción no es lo
  que el cronómetro mide. Hasta que haya un segundo clip con el cronómetro
  andando, los 240,15 fps son n = 1: la mejor medición del proyecto y, al mismo
  tiempo, la que menos veces se repitió.
- **El archivo ORIGINAL sin recortar**, de `DCIM/Camera`, del mismo modo y con
  el mismo cronómetro. Los tres clips lentos que hay son **recortes hechos en
  la Mac**, no lo que sale del teléfono: `udta` de Samsung de 1 MB → 185 B,
  handler `Core Media Video`, y un `elst` que esconde cuadros (14 en uno, 26 en
  otro, 4 en el tercero). El camino calibrado de hoy calibra ese recorte; el
  camino del teléfono crudo sigue sin calibrar. Con el original se puede además
  comparar los dos y ver si el recorte cambió algo.
- **Cuánto mide el delta de arranque en Slow motion FHD 240.** Sigue sin
  medirse, y por la misma razón: el recorte se lleva los primeros cuadros y con
  ellos el arranque de la cámara (el primer delta de los tres clips es
  0,033333 s, normal). Medido en los otros dos modos: **0,2015 s** en FHD 30
  (informe del 03) y **0,073–0,110 s** en UHD 60 (informe del 11); en los dos,
  el primero es el único delta fuera de lugar. Lo contesta el original.
- **Los cronómetros de *Video* FHD 60 y FHD 30.** Sus dos caminos
  (`s22ultra-video-fhd60-cable`, `s22ultra-video-fhd30-cable`) siguen
  declarados, con `fps_real` asumido y procedencia `sin_verificar`. No son
  urgentes —ninguno de los dos llega a los 100 fps que pide golf, así que un
  clip suyo se rechaza igual— pero mientras no se filmen, todo lo que se mida
  desde ellos es descriptivo y nunca juicio.
- **Si el S22 cambia campo de visión o estabilización entre modos**: si lo
  hace, la calibración de un modo no es transferible a otro.
- **La pista de audio de los tres clips lentos va a 12.000 Hz** (48.000/4), no
  a 48.000/8 como haría esperar un estiramiento ×8 parejo. No contradice nada
  de lo medido —el cronómetro mide el video— pero es una rareza del contenedor
  sin explicar (encargo 24).

### Con el iPhone, si alguna vez hay uno

- La firma exacta de ffprobe sobre un `.MOV` de Slo-Mo real de iPhone (edit
  list, timestamps, metadata). No hay ninguno en esta Mac.
- Si AirDrop sigue conservando 240 fps en iOS/macOS actuales.
- Si el bug de 240 nominales → 114–227 reales sigue vivo en iPhone 17/18 Pro.
- Los bitrates reales de 1080p120 y 1080p240.
- Si el iPhone cambia campo de visión o estabilización entre modos: si lo
  hace, la calibración de un clip no es transferible a otro de la misma
  sesión.
