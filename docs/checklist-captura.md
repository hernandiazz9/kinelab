# Checklist de captura — kinelab

Para imprimir y llevar al campo. Derivado de `CAPTURA.md`; si algo de acá
contradice a ese archivo, manda `CAPTURA.md`. Cada casilla se marca antes de
seguir. Lo que no se marcó, no se filmó.

**Esta hoja es del protocolo iPhone.** El teléfono que hay hoy es un Galaxy
S22 Ultra, y su guía —en castellano llano, para quien filma— es
`docs/filmacion-s22.md`. Con ese teléfono, además, **ningún modo Video llega a
los 100 fps que pide golf**: la única llave es el cronómetro en Slow motion
FHD 240 (`CAPTURA.md` §Lo que queda por verificar).

---

## A. El teléfono (una vez; después no se toca)

iPhone 17 Pro / 18 Pro. Con otro modelo, el cronómetro (sección C) decide qué
modos sirven.

- [ ] **Ajustes → Cámara → Formatos → Alta eficiencia (HEVC).**
      "Más compatible" (H.264) deshabilita 240 fps sin avisar y el gate lo rechaza.
- [ ] **Ajustes → Cámara → Grabar video → 1080p a 120 fps.**
      Modo Video normal, no Slo-Mo. No 4K.
- [ ] **Ajustes → Fotos → Transferir a Mac o PC → Mantener originales.**
      "Automático" autoriza al teléfono a transcodificar al transferir.
- [ ] **Ajustes → Pantalla → Bloqueo automático → Nunca** (durante la sesión).
- [ ] Editor de Fotos → Velocidad de reproducción: **no tocar nunca**.
      Compartir después de cambiarla hornea la velocidad elegida.
- [ ] Batería > 50 % y espacio libre > 5 GB (una sesión de 20 clips 1080p120 son ~1,7 GB).

## B. El equipo

- [ ] Trípode.
- [ ] Cronómetro con **milésimas** visibles (app de cronómetro en otro
      teléfono o tablet sirve).
- [ ] Un solo golfista, dispuesto a pegar 10–20 swings por vista.
- [ ] Lugar al aire libre, de día, sin contraluz. Fondo simple.
      A 240 fps la exposición está topeada; la única palanca contra el
      desenfoque es la luz. Objetivo: obturador ≤ 1/1000 s → ≤ 5 px de barrido
      en la mano.

## C. Calibrar con cronómetro (antes del primer clip real)

Por **cada** combinación de modo y camino de transferencia que se vaya a usar.
Con el protocolo por defecto es una sola: Video 1080p120 + AirDrop.

- [ ] Cronómetro llenando el cuadro, en marcha, milésimas legibles.
- [ ] Filmar **10 s** en el modo a calibrar.
- [ ] Transferir por el camino a calibrar (sección E).
- [ ] Anotar los segundos entre la **primera** y la **última** lectura del
      cronómetro que se ven nítidas en el clip: `______ s`.
- [ ] Correr:

      ```
      .venv/bin/python -m kinelab.tools.fps_truth CLIP.MOV --duracion-real <segundos> --nominal 120
      ```

- [ ] Veredicto `CFR_A_TASA_DE_CAPTURA`, codec `hevc`, ratio de deltas ≤ 1,10.
      Cualquier otra cosa: **no filmar la sesión**; revisar A y E.
- [ ] Copiar a `data/capture-paths.yaml` (ejemplo campo por campo en
      `data/examples/capture-paths.example.yaml`): `fps_real`, `fps_playback`,
      `stretch_factor`, codec, ratio de deltas, fecha, quién.
- [ ] Si se va a usar Slo-Mo 1080p240 para un bloque de impacto: repetir
      **todo C** con ese modo. Es otro camino.

## D. Encuadre (por vista, con el trípode fijo)

- [ ] El trípode, **lo más cerca que permita tener los pies y el palo del top
      adentro del cuadro**. Esa es la regla operativa; el 80–90 % del alto es
      el **objetivo** y en vertical con la lente principal no se alcanza a una
      distancia usable (`CAPTURA.md` §Encuadre). Los cuatro clips reales
      salieron al 28–42 % y hace falta más.
- [ ] Anotar cuánto ocupó el cuerpo, que lo dice la exploración: ______ %.
      **No hay umbral fijado todavía**: sale del barrido de tamaño del arnés.
- [ ] Cámara a altura de **cintura a pecho**, horizontal.
- [ ] **`face_on`**: cámara perpendicular a la línea de tiro, mirando al pecho.
- [ ] **`down_the_line`**: cámara detrás, sobre la línea de tiro, a la
      distancia que fija la primera casilla (antes decía ~3,5 m).
- [ ] Una sola persona en cuadro. Nadie cruza por detrás.
- [ ] El trípode **no se toca** entre swings de la misma vista.

## E. Filmar

Una vista = una sesión = un clip con N swings.

- [ ] App Cámara nativa, modo **Video** (no Slo-Mo, salvo bloque de impacto calibrado).
- [ ] Confirmar en pantalla: **1080p · 120**.
- [ ] Un clip por vista: 10–20 swings seguidos.
- [ ] **Antes de cada swing, 2–3 s quieto en address.** El motor define el
      address como el último cuadro de una ventana estable; sin ventana no
      hay cero para sway, lift ni cabeza.
- [ ] Entre 3 s y 180 s por clip. Más largo, se rechaza; cortar en dos clips.
- [ ] Vista `face_on`: ____ swings · Vista `down_the_line`: ____ swings.
- [ ] Clip **deliberadamente malo** para probar el gate: uno de los swings
      exportado desde Fotos con File → Export → Export 1 Video.

## F. Transferir

**En iPhone, un solo camino: AirDrop a la Mac, con "Mantener originales".**

- [ ] Fotos → seleccionar los clips → Compartir → AirDrop → la Mac.
- [ ] Extensión `.MOV`, codec `hevc` (se verifica en G).
- [ ] **Nunca**: arrastrar desde Fotos (llega a 120 → recomprimido), File →
      Export (llega a 30), **WhatsApp como video**, Telegram, Drive, enlace de
      iCloud.
- [ ] Android (S22 Ultra): cable desde `DCIM/Camera` es el camino de
      referencia. **WhatsApp como documento** también llega intacto —medido,
      informe del 11— y es un camino aparte en `capture-paths.yaml`, con su
      propio cronómetro.

## G. Verificar cada clip en la Mac

Por cada clip, antes de cualquier otra cosa:

```
.venv/bin/python -m kinelab.tools.fps_truth CLIP.MOV
```

- [ ] `hevc`, cuadros ≈ 120 × segundos filmados, reproducción ≈ 120 fps, ratio ≤ 1,10.

Después, ingestar (escribe `capture.json`; código de salida 0 = pasó, 2 = rechazado):

```
.venv/bin/python -m kinelab.ingest CLIP.MOV --atleta <slug> --gesto driver --vista face_on \
    --camino iphone17pro-video-1080p120-airdrop
```

- [ ] `gate: OK` en los clips buenos.
- [ ] `gate: RECHAZADO` con razón legible en el clip exportado de E. Si lo
      acepta, el gate está roto: avisar antes de seguir.
- [ ] Anotar el tamaño real en MB de un clip de 1080p120 de 30 s: ______ MB
      (el presupuesto de `CAPTURA.md` viene de un sitio comercial y hay que re-medirlo).
