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
duración real conocida. Por eso:

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

- El atleta ocupa **80–90% del alto del cuadro**: 900+ px de cuerpo a 1080p.
  El prototipo anterior trabajó con 116–135 px (11–16%) y ahí dos píxeles de
  error en el codo son grados. El umbral exacto del gate se fija midiendo en
  la Fase 1.
- Trípode. Cámara a **altura de cintura a pecho**.
- Dos vistas, cada una su propia sesión:
  - **`face_on`**: cámara perpendicular a la línea de tiro, mirando al pecho
    del golfista. Da giro, forward/side bend, sway, lift, cabeza.
  - **`down_the_line`**: cámara detrás del golfista, sobre la línea de tiro,
    a ~3,5 m. Da thrust e inclinación aparente de columna. Desde acá la
    columna "parece" inclinada por combinación de giro y side bend, no por
    flexión — por eso las métricas declaran vista.
- Fondo simple, sin otras personas en cuadro. Una persona.
- Cuerpo entero, incluidos pies y palo en el top.

---

## Transferencia

**Un solo camino permitido en producción: AirDrop del iPhone a la Mac, con
"Mantener originales" activo.**

Escalera de degradación reportada por terceros para un Slo-Mo de 240 fps (una
sola fuente, versión de macOS no declarada — **re-verificar con el cronómetro
antes de confiar**):

| Camino | fps que llega |
|---|---|
| AirDrop (Mantener originales) | 240 |
| Fotos → Edit with → QuickTime Player → guardar copia | 240 |
| **Arrastrar el clip desde Fotos** | **120** |
| **File → Export → Export 1 Video** | **30** |
| WhatsApp, Telegram, Drive, enlace de iCloud | recomprimido |

Los dos gestos más naturales son los dos peores.

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

## El gate de ingesta

Bloqueante. Cada chequeo tiene id, resultado, valor y una frase para el
entrenador. Orden de evaluación fijo; el primero que falla ya decide `reject`,
pero se reportan todos.

| id | Regla | Frase al fallar |
|---|---|---|
| `capture_path_known` | `capture_path_id` existe en `capture-paths.yaml` | "Este camino de captura no está calibrado. Filmá el cronómetro primero." |
| `codec_matches_path` | `codec == camino.codec_expected` | "El clip está en H.264 y el camino espera HEVC: pasó por 'Más compatible' o por un transcodificador." |
| `vfr_ratio_le_1_10` | `delta_max / delta_min ≤ 1,10` | "El video tiene tasa variable. Volvé a exportarlo desde el original." |
| `fps_matches_path` | `abs(fps_playback − camino.fps_playback) / camino.fps_playback ≤ 0,02` | "El clip reproduce a N fps y el camino declara M. Algo lo recomprimió, o vino por otro camino." |
| `fps_min_for_gesture` | `fps_real ≥ sports.<g>.fps_min` (golf: 100) | "A esta tasa no se pueden medir los tiempos del swing." |
| `duration_plausible` | 3 s ≤ duración ≤ 180 s | |
| `rotation_normalized` | rotación aplicada en `master.mp4`; ancho/alto reales | |
| `body_height_frac` (Fase 1) | `body_height_px / height ≥ umbral medido` | "El jugador ocupa X% del cuadro. Acercá la cámara." |
| `detection_rate` (Fase 1) | `≥ 0,90` | "Se perdió al jugador en el N% de los cuadros." |
| `single_subject` (Fase 1) | una sola persona de tamaño dominante | "Hay más de una persona en cuadro." |
| `view_declared` | `view ∈ sports.<d>.views` | |
| `gesture_known` | `gesture ∈ sports.<d>.gestures` | |

Un `reject` no borra nada: el clip queda en disco con su `capture.json` y sus
razones, para poder corregir y re-ingestar.

---

## Presupuesto de datos

| Modo | Tamaño por 30 s | Sesión de 20 clips |
|---|---|---|
| 1080p120 HEVC | ~85 MB | ~1,7 GB |
| 1080p240 HEVC | ~240 MB | ~4,8 GB |
| 4K120 | ~3,5 GB | descartado |

Cifras de un sitio comercial (HEVCut), no de Apple: **re-medir con el primer
clip real**.

---

## Lo que queda por verificar con el primer clip real

- La firma exacta de ffprobe sobre un `.MOV` de Slo-Mo real de iPhone (edit
  list, timestamps, metadata). No hay ninguno en esta Mac.
- Si AirDrop sigue conservando 240 fps en iOS/macOS actuales.
- Si el bug de 240 nominales → 114–227 reales sigue vivo en iPhone 17/18 Pro.
- Los bitrates reales de 1080p120 y 1080p240.
- Si el iPhone cambia campo de visión o estabilización entre modos: si lo
  hace, la calibración de un clip no es transferible a otro de la misma
  sesión.
