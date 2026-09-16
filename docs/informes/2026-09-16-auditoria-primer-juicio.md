> Auditoría hecha por un flujo de 23 agentes el 16/9/2026, pedida por el orquestador: reproducción desde HEAD `f866c77`, auditoría de los 21 `judgment_allowed: true` de `cortado3-lento.mp4` (un auditor y dos refutadores por grupo de métricas), inventario de deuda, estado de fases, cuatro planes y tres jueces. Las rutas del scratchpad que aparecen abajo (imágenes, `candidatos.py`) no se conservan; los anexos de texto sí, en `auditoria-2026-09-16/`.

# Síntesis — los primeros números con juicio, y qué sigue

Fecha: 2026-09-16 · HEAD `f866c77` (limpio) · material: `cortado3-lento.mp4`, 2 repeticiones.
Fuentes: la reproducción, las cuatro auditorías con sus dos verificadores, el inventario de deuda, el estado de
fases, los cuatro planes y los tres juicios. Todo lo que verifiqué yo en el repo, en modo sólo lectura, está
en la última sección. No modifiqué nada del repo.

## En una línea

Fase 0 sigue abierta. Ninguno de los 21 `judgment_allowed: true` resiste la auditoría. La aritmética es exacta
y los eventos de manos se reproducen, pero hay tres problemas: `follow_end` cae en el swing siguiente, la
imagen deriva 8–25 px durante cada swing y los eventos de manos quedan 4–16 cuadros antes o después de los
del palo.

Lo que sigue, en orden:

1. Apagar el juicio (ADR-019) y limpiar la demo, en paralelo.
2. Preparar la filmación: gate en px y censo de deriva.
3. Cerrar la repetición y dejar trazable la escala.
4. Filmar la sesión de validación.

---

## 1. Veredicto sobre los 21 `judgment_allowed: true`

Son 11 en la rep 1 y 10 en la rep 2. Hay tres cosas verificadas:

- **Aritmética:** 21 de 21 reproducidas exactas por tres implementaciones independientes (numpy, sin kinelab).
- **Eventos de manos:** top 1284/2548 e impacto 1364/2624, ±1 cuadro, reproducidos con señales propias.
- **Pose y gate:** la pose es determinista. El gate pasa 9/9, pero con una tasa prestada de otro clip (n = 1).

| métrica | rep 1 | rep 2 | veredicto | por qué |
|---|---|---|---|---|
| `follow_duration_ms` | 2556,7 ms | null | **falso / inestable** | El `follow_end` 1978 es el address del swing siguiente. El finish se ve hacia 1507 (≈595 ms), o termina la pose hacia ≈1598 (≈974 ms). La búsqueda no tiene tope (`sports/golf/events.py:251`): exige 72 cuadros quietos y la pausa dura 50–56. En la rep 2, null o 712–716 ms según cómo se pesen las muñecas. |
| `backswing_duration_ms` | 966,1 ms | 941,1 ms | **no** | El address cae en una meseta y se mueve 6–27 cuadros según la señal. Manos y palo difieren 4–16 cuadros. Con eventos de palo, la diferencia entre reps cambia de signo. El error es 2–3× el MDC (12,6 ms). |
| `downswing_duration_ms` | 333,1 ms | 316,5 ms | descriptivo, **no juicio** | Como tiempo de manos es robusto: 312–337 ms según la variante, dentro del MDC (13,0) en 2 de 3 lentes. Como tiempo de palo da +4,6 a +29 ms según el criterio del top. |
| `tempo_ratio` | 2,900 | 2,974 | **no** | Las variantes razonables dan 2,55–2,94 y 2,79–3,02, contra un MDC de 0,065. |
| `pelvis_sway_top_cm` | 3,7 | −7,1 | **no** | Compensando la cámara: −0,2…+1,0 y −4,3…−5,8. |
| `pelvis_sway_impact_cm` | 22,6 | 7,7 | **no** | Compensando: 18,5…19,4 y 10,6…12,8. El movimiento grande es real, pero está inflado o achicado más que el MDC (2,4). |
| `pelvis_lift_top_cm` | −4,3 | −5,5 | **no** | Compensando: −6,2…−8,2 (depende del modelo de cámara) y −5,6…−7,0. La y de la pose deriva ~10 px. |
| `thorax_sway_top_cm` | 3,5 | −5,1 | **no** | Compensando: −0,9 y −2,9. Los dos «sí» de los verificadores no midieron la cámara. |
| `thorax_lift_top_cm` | 5,0 | 2,4 | **no** | Compensando: +1,3…+2,5 y +1,4, bajo el MDC (2,8). La subida la pone sólo el hombro derecho tapado (+63 a +66 px). |
| `head_sway_top_cm` | 4,9 | −4,6 | **no** | Compensando: −0,3…+0,7 y −1,2…−2,3. Mezcla inclinación de cabeza con traslación. |
| `head_lift_top_cm` | −2,0 | −0,8 | **no** | Compensando: −3,8…−5,1 (la silueta da −4,4…−5,3) y −1,7…−2,7. En la rep 2 sigue valiendo que no hay cambio distinguible; el número no. |
| `summary` (SD entre reps) | — | — | **no** | n = 2 y `noise_floor` null. Es menor que la ambigüedad de los eventos. |

Detalles de los desplazamientos en cm:

- **La cámara.** Entre el address y el top o el impacto, la imagen se corre ≈ +14 a +23 px en x en la rep 1 y
  ≈ −8 a −25 px en la rep 2. Lo muestran tres métodos (zapatillas y parches, SIFT+RANSAC, homografía por
  filas) en cinco análisis independientes.
- **Lo que no lo detecta.** `quality.camera_motion_px` = 1,347 es la mediana del corrimiento entre muestras
  tomadas cada 120 cuadros a 320 px (`kinelab/perception/video.py:127-153`), así que no ve una deriva lenta.
- **El patrón de las reps.** Que las dos repeticiones vayan en sentidos opuestos coincide con el sentido de la
  deriva en cada una.
- **La escala.** La de la rep 2 sale del cuadro 2970, en el borde de la ventana (831,3 px contra 780,6 en
  2797, un 6 %). La altura de 1,75 m no queda escrita en el JSON.
- **Sobre los compensados.** Son rangos de auditoría, no verdad: los métodos difieren 3–6 px entre sí.

### Qué hacer con `judgment_allowed`

Hay que **apagarlo en todas las métricas ya**, con ADR-019, sin tocar el schema:

- **Hueco actual.** `judgment_allowed` se deriva en `kinelab/metrics/registry.py:87-102` y exige MDC, fps
  medido, vista y rango. Pero con una referencia descriptiva sin rango da `true`.
- **La tabla de MDC.** `sports/golf/mdc.yaml` es del arnés nivel 0: sin estimador y con la cámara
  `iphone17pro-1080p120` sin verificar. No cumple ni el nivel 0 de ADR-009 ni ESPECIFICACION 3.1, que piden
  intrínsecos **medidos** del teléfono real.
- **El cambio.** Una condición nueva, como hizo ADR-016: `Metric.mdc_provenance`, con default conservador
  `sin_verificar`. Juicio sólo con `medido_aqui`, entendido como MDC validado en material real del camino.
  Resultado: 0 de 21. Los valores no cambian, `metric_version` tampoco, y `registry_version` pasa a 0.3.0.
- **Dónde va la razón.** Como string en `warnings[]`, que el schema ya admite. La fórmula de CONTRATO
  §El sextuplo se actualiza.
- **Mientras tanto.** La tabla del informe 26 §4 no es una medición. No se muestra cortado3 ni ninguna SD.

Contexto que achica la urgencia visible, verificado: el juicio `true` **nunca llegó a la pantalla**. La lista
sólo muestra `data/exploracion/`, que por ADR-016 siempre es `sin_verificar`. En la demo pública, vid1 sólo
muestra tempo 2,632 como número: los cm salen null (sin altura) y las duraciones también (60 < 120 fps). Lo
falso que sí se ve es otra cosa: la tabla de picos con `hip_line_rate_deg_s 3662,0` y el rótulo fijo
«±1 cuadro».

---

## 2. Prioridad inmediata

1. **Ronda del orquestador, antes de cualquier código.**
   - PLAN.md al día (16 y 18 hechos) y la tabla del 26 §4 anotada como no válida.
   - Congelar el 21, Fase 5 y métricas nuevas.
   - Arreglar la regla de commits de `.claude/skills/encargo/SKILL.md` §5. Hoy permite
     `git add ruta && git commit -m`, que se lleva lo que otra sesión dejó staged: pasó en `eed337c`.
   - Decidir D-2 y D-3 (ADR-019).
   - Escribir los prompts del 1 y el 2.
   - Guardar esta síntesis como informe de texto en `docs/informes/`: el scratchpad no dura.
2. **En paralelo:** encargo 1 (contención del juicio) y encargo 2 (pantalla y demo, sólo web).
3. **Ya, a Hernán:** las respuestas sobre cortado3 (trípode, estabilización, palo, altura) y las dos
   definiciones (el finish; top y address de manos o de palo).

---

## 3. Secuencia

Máximo dos sesiones a la vez, sin archivos compartidos. `CONTRATO.md` se edita de a una sesión por vez.

| ronda | encargos | nota |
|---|---|---|
| R1 | **1** contención del juicio ∥ **2** pantalla y demo | el 2 es sólo web |
| R2 | **3** = 17 ajustado ∥ **4** herramienta y censo de deriva | después de R2 Hernán puede filmar |
| R3 | **5** follow_end dentro de la repetición ∥ **6** exit 134 del arnés | el 6 es sólo truth/ |
| R4 | **7** escala y altura trazables (2.1.0) | CONTRATO |
| R5 | **8** fuente de la calibración del fps | CONTRATO + ingesta |
| — | **Hernán filma** | con la sección nueva de la guía (encargo 3) |
| R6 | **9** sesión de Fase 0 (9a ingesta, 9b pose y análisis) | 9b sin sesiones editando kinelab/ |
| R7 | **10** error de eventos y piso de ruido ∥ **11** = 21 ajustado | |
| R8 | **12** deriva en el análisis (2.2.0) | |
| R9 | **13** regenerar exploración y demo, una sola vez | Hernán despliega |
| — | ronda del orquestador con evidencia | ADRs de definición, banda, 717, re-habilitar juicio, Fase 5 |

### Los encargos, en una línea cada uno

1. **Contención del juicio (ADR-019).**
   - Qué hace: `Metric.mdc_provenance` y `judgment_allowed` exige `medido_aqui`. El sub-cuadro deja de decir
     `medido_aqui`. Dos avisos (juicio apagado; cámara sin verificar). Repetibilidad null sin `noise_floor`.
     `addopts -q` fuera. Nota de ADR-018 en ESPECIFICACION.
   - Corrida real: cortado3 ingestado a `data/sessions/`. Además `datos` en cortado y vid1 contra los siete cm
     del 14, que cierra el punto 6 del 16.
   - Prueba: 0 de 21 juicios y los 21 valores iguales.
2. **Pantalla y demo.**
   - Qué hace: `Metricas.tsx:42` pasa a `uncertainty.method`. `:54` deja de decir «se puede comparar».
     `TablaEventos.tsx:144` y `TablaCuadros` sólo muestran claves conocidas (sin `*_rate_deg_s`). Aviso para
     trabajos con schema < 2.0.0. `page.tsx:321` rotula el ± del sub-cuadro como precisión interna.
   - Qué no hace: no regenera datos.
3. **17 ajustado.**
   - Archivos reales: `framing.py`, `sport.py`, `config.py`.
   - Corrida real: cortado3 en un scratch, con rechazo esperado (691 contra 717). Tabla de px de los otros
     clips.
   - Guía: sección «sesión de validación» en `docs/filmacion-s22.md`.
4. **Deriva de cámara: herramienta y censo.**
   - `kinelab/tools/camera_drift.py`: homografía del fondo con el sujeto enmascarado, deriva en las filas de
     caderas, hombros, cabeza y pies, más controles.
   - Censo de los 8 clips reales.
   - Aceptación: rangos de la auditoría ±3 px.
5. **follow_end dentro de su candidato.**
   - La cota es el fin del candidato propio (1765 en la rep 1). Ni el address siguiente (2322) ni el candidato
     siguiente (2130) sacan la quietud 1946–2321.
   - Además: `explore.py:164` con el `wrist_score_min` del deporte, `tol_frames` en `datos-eventos.json` y en
     la tabla, y `git rm order.py`.
6. **Exit 134 del arnés:** aislar el aborto al cerrar, o documentarlo y parar.
7. **Escala y altura trazables (2.1.0):** `reps[i].scale_px` con `at_window_edge`, altura y su fuente, y
   `quality.scale_px.method` sin «mediana» falsa. Sin cambiar la convención.
8. **Fuente de la calibración:** `calibration_clip_sha256` en capture-paths 1.2.0, `fps_calibration.same_file`
   en capture 1.3.0, aviso en el análisis, y arreglo de `ingest/__main__.py:103`. No se toca el enum de
   `fps_provenance`.
9. **Sesión de Fase 0.**
   - Ingesta, cronómetro por toma y rechazo de la toma por WhatsApp como video.
   - Pose y análisis, deriva por toma y en la escena vacía, escala contra la referencia de pie y la altura con
     cinta, revisión a ojo.
   - Sin tocar código.
10. **Error de eventos y piso de ruido.**
    - Hojas de cuadros y etiquetas del palo a 240 fps; Hernán confirma 5.
    - Bland–Altman por evento con n ≥ 20 por vista.
    - σ por keypoint en quietud, con la tendencia restada.
11. **21 ajustado:** ver abajo.
12. **Deriva en el análisis (2.2.0).**
    - `camera.npz` aparte de `pose.npz` y `reps[i].camera_drift_px`.
    - Si |desplazamiento| ≤ |deriva| en el eje: null con razón. Si no: la deriva se suma a la banda, con aviso.
    - `camera_drift_max_px` en quality. Sin compensar.
13. **Regenerar una vez:** exploración y demo desde `pose.npz` al contrato vigente, con la tabla de cambios.
    Despliega Hernán.

---

## 4. Los encargos 17 y 21 ya escritos

**17 → ajustar y correr como encargo 3 (R2, antes de filmar). El 717 no se toca.** Esto es lo que cambia:

1. **Archivos.** El chequeo no está en `gate.py`. Vive en `kinelab/perception/framing.py:202-245`
   (`framing_checks`), con el umbral en `kinelab/sport.py:31`, y lo escribe `kinelab/perception/run.py:106-117`
   con `with_checks` (`gate.py:423-433` recalcula el veredicto). El «NO» tiene que nombrar `framing.py`,
   `sport.py` y `config.py`.
2. **Orden.** Ya está resuelto en el código: se evalúa en la Fase 1 y se escribe en `capture.json`.
3. **Corrida real.** «Los cuatro clips reales pasan» no se puede correr por el camino con gate: vid1–3 y
   20260907 se rechazan por fps en la ingesta, y `run.py:74` no corre pose sobre un rechazo. La corrida real es
   cortado3-lento en un `--data` de scratch, con rechazo esperado a 691 px. La tabla sale de los reportes
   existentes (frac × alto): 20260907 973, cortado 869, vid1 1104, vid2 1083, vid3 1132, Cortado-lenta 414.
4. **Toma de cortado3.** No re-correr perception sobre la toma de `data/sessions`: queda en reject y
   `analyze_take` (`analysis.py:271`) la rechaza.
5. **`mdc.yaml`.** Su §framing lo escribe el arnés: no se edita a mano.
6. **Quién fija el número.** El 717 lo fija sólo `head_lift_top_cm`. Le siguen `head_sway_top_cm` con 608 px y
   `thorax_sway_top_cm` con 552.
7. **Guía.** Sección de la sesión de validación en `docs/filmacion-s22.md`. 717 px son 37,3 % de 1920;
   cortado3 dio 36,0 %.
8. **Tests.** En `tests/test_perception.py`.

**21 → ajustar y postergar a R7 (encargo 11, en paralelo con el 10).** Esto es lo que cambia:

1. **Dependencias.** «Después del 16, 19 y 20» pasa a «después del 2, el 5 y el 9, sin sesión de motor abierta
   en `analysis.py` ni `explore.py`».
2. **Cuadro y tiempo.** El cuadro sale del fps de **reproducción** del archivo servido: 30,0169 en el Slow
   motion del S22, estirado ×8,0005. Nunca de `timestamps_s` de `pose.npz`, que es n / 240,15.
3. **Material de prueba.** Probar también sobre cortado3-lento (HEVC, 2977 cuadros) y sobre una toma de la
   sesión, además de vid1 741.
4. **Hash del master.** Va en `header.source.master_sha256`, que ya existe en el schema 2.0.0 (hoy null): no
   hace falta cambiar el contrato.
5. **Juicio.** El front no calcula ni muestra juicio. Pinta lo que manda el motor: `uncertainty.method`,
   `null_reason` y `warnings`.

---

## 5. Para Hernán

1. **Contestar sobre cortado3-lento (15/9), de memoria:**
   - ¿Trípode? ¿Sobre qué suelo? ¿Lo tocaste entre swings? ¿Había viento?
   - ¿Super Steady estaba apagado? ¿Hay en Ajustes otra opción de estabilización de video, y estaba prendida?
     No verifiqué que exista en Slow motion.
   - ¿Qué palo era? Se declaró driver; dos verificadores ven una cabeza de hierro, sin verificar.
   - ¿Cuánto medís con cinta?
   - ¿Editaste el tramo lento en Galería?
2. **Decidir dos definiciones.** Son de entrenador y mueven los números más que el MDC:
   - (a) Fin del follow: cuando llegás a la pose final, o justo antes de soltarla. Hay ≈90 cuadros (≈380 ms)
     entre las dos.
   - (b) Top y address: de las manos, que es lo que mide hoy el motor, o del palo. Hay 4–16 cuadros de
     diferencia.
3. **Aceptar o no ADR-019:** hasta validar en material real, ninguna métrica es juicio; todas se muestran como
   descriptivas.
4. **Cliente, hasta que cierre el 2 y redespliegues:**
   - Mostrar: video, cuadro a cuadro, zoom, fotos por evento, «con este archivo» y el mocap 3D rotulado como
     mocap.
   - No abrir la tabla de picos: muestra `hip_line_rate_deg_s 3662,0`.
   - No mostrar cortado3, la tabla del 26 §4 ni ninguna SD.
   - El video de vid1 es público para quien tenga el enlace.
5. **Después del 2:** reconstruir y desplegar la demo vos. `data/publicados.json` marca 3 trabajos con
   despliegue null, así que mirá el sitio en vivo.
6. **Orden de las sesiones:** {1 ∥ 2} → {3 ∥ 4} → {5 ∥ 6} → 7 → 8. Máximo dos a la vez. Si una sesión ve en
   `git diff --cached` archivos que no son suyos, para.
7. **Opcional:** `git worktree remove /private/tmp/claude-501/-Users-heralc-Desktop-HDDev-kinelab/d38251b3-7977-4d99-a5cc-3f6440b3be81/scratchpad/wt16`.
   Verificado: está limpio, en detached `2e781be`, que ya está en main.
8. **Filmar la sesión de validación después del 3 y el 4**, con la guía más esto:
   - Trípode con peso, sin tocarlo durante la toma. Super Steady y toda estabilización apagadas.
   - Un objeto chico y contrastado fijo en el suelo, cerca de los pies y dentro del cuadro.
   - Al armar cada vista: 25 s de grabación de la escena vacía, con el trípode ya puesto.
   - Al empezar cada toma: 2 s de pie derecho, de frente, en el lugar del address.
   - Cuerpo ≥ 717 px, o sea más de 37,3 % del alto en FHD vertical. Un paso más cerca que cortado3.
   - Cronómetro andando dentro del cuadro en cada toma.
   - 10–20 swings face_on y 10–20 down_the_line, con pelota.
   - En la mitad de las tomas, sostener la pose final 1–2 s. En la otra mitad, terminar como siempre.
   - El palo, declarado bien.
   - Originales de `DCIM/Camera` por cable. De una toma, también el recorte de la Mac.
   - Una toma mandada por WhatsApp **como video**: tiene que salir rechazada.
   - La altura con cinta, en `data/athletes/hernan.yaml` (`altura_m`).

---

## 6. Decisiones del orquestador (con recomendación)

- **D-1 Congelar.**
  - El 26 §4 no es medición.
  - Nada de Fase 5, del 21 ni de métricas nuevas.
  - cortado3 no cuenta como validación.
- **D-2 ADR-019.**
  - Juicio sólo con MDC `medido_aqui`, validado en material real del camino.
  - Condiciones por familia:
    - eventos contra etiquetas humanas a la tasa del camino;
    - deriva medida por repetición;
    - escala y altura trazables;
    - intrínsecos con tablero;
    - error del estimador.
  - Sin cambio de schema; `registry_version` 0.3.0.
- **D-3 Juicio y rango.** Recomiendo alinear el código con CONTEXTO: sin rango con procedencia no hay juicio.
  «Cambio detectable entre tomas» es otro concepto, con su propio nombre, para Fase 5.
- **D-4 follow_end.**
  - La cota es el fin del candidato propio.
  - No tocar `follow_still_s` ni `wrist_score_min`.
  - La definición la decide Hernán; hasta entonces se documenta que el motor marca el inicio de la quietud.
- **D-5 Escala.**
  - No cambiar la convención: publicar por repetición, con el borde y la altura.
  - Los verificadores discrepan en cuál está sesgada (784 contra 831 px).
  - Se resuelve con la referencia de pie de la sesión.
- **D-6 Deriva.**
  - Medir y censar antes de filmar (4) e integrarla después de la sesión (12).
  - Si |desplazamiento| ≤ |deriva| en el eje: null con razón (CONTEXTO §piso de ruido). Si no: la deriva a la
    banda, con aviso.
  - No compensar sin validación.
- **D-7 17.** Ajustar y correr antes de filmar, con el 717. El jitter medido de HEAD (3,7 px en y, con la
  deriva de la cabeza incluida) queda por debajo del σ nominal de 4,9: el 717 está del lado conservador. Se
  re-decide con el σ del 10.
- **D-8 21.** Ajustar y postergar a después de la sesión.
- **D-9 Proceso.**
  - Commits:
    - Siempre `git commit -m … -- rutas`. `git add` sólo para archivos nuevos propios.
    - `git diff --cached --name-only` vacío antes de empezar y con sólo archivos propios al commitear.
    - `git mv` y `git rm` en el mismo comando que su commit.
    - `ESTADO.md` se edita en un solo paso al cierre.
  - Sesiones:
    - Máximo dos y sin archivos compartidos.
    - Una sesión que corre el motor sobre material no coincide con otra que edita `kinelab/` o `sports/`.
    - Sin worktrees por defecto: `models/`, `data/` y `web/public/demo/` están ignorados y faltarían.
  - Los tests se leen por exit code y conteo.
  - Ningún prompt depende de un encargo sin informe.
- **D-10 Persistir esta auditoría** como informe de texto en `docs/informes/`. Los rangos de aceptación van
  escritos en los prompts.
- **D-11 Informe del 16.** No gastar una sesión: el 1 cierra su punto 6 y lo anota.
- **D-12 GolfDB.** Aparcado para eventos a 240 fps; el 10 usa etiquetas propias.
- **D-13 Calibración heredada.** El 8 la hace visible. Si habilita juicio, se decide después del 9. Recomiendo
  que no, hasta tener n ≥ 3 cronómetros dentro de 1σ (propuesta, no medida).
- **D-14 Aparcado hasta tener la evidencia del 10:**
  - el escalón de media empuñadura (`signal.py:104-112`);
  - la banda conjunta (`core.py:219-241` mueve un evento por vez);
  - la definición del address;
  - `thorax_lift_top_cm` en face_on (hombro tapado);
  - `head_sway` como inclinación más traslación;
  - el sesgo de −11,3 ms del sub-cuadro contra la pelota.
- **D-15 Versiones.** analysis 2.1.0 (7) → 2.2.0 (12); capture 1.3.0 y capture-paths 1.2.0 (8); una sola
  regeneración (13).
- **D-16** `docs/checklist-captura.md` (iPhone): archivarla o marcarla obsoleta cuando exista la sección de
  la sesión de validación.
- **D-17 Después del 10 y el 12:** ronda con evidencia para las definiciones (finish, top, address), la banda,
  el 717, qué condiciones de ADR-019 cumple cada métrica, y si Fase 5 arranca con descriptivos.

---

## 7. Qué no hacer

- No usar ni mostrar la tabla del 26 §4 ni la SD entre repeticiones como medición.
- No ajustar `follow_still_s`, `wrist_score_min`, `still_speed_max`, `noise_factor`, `top_band_sigmas` ni el
  717 con cortado3. Es n = 1, y el 18 ya mostró el costo: `wrist_score_min` 0,55 arregló el top y rompió el
  `follow_end` de la rep 2.
- No acotar `follow_end` por el address o el candidato siguientes: no sacan la quietud 1946–2321.
- No compensar la deriva dentro de las métricas. Los métodos discrepan 3–6 px, el campo varía con la fila y la
  rep 2 tiene 10–12 px de residuo no rígido.
- No fijar como golden ni los valores actuales de cortado3 ni los «corregidos» de la auditoría. Los criterios
  van como rangos.
- No agregar valores al enum de `fps_provenance` (`[medido_aqui, sin_verificar]` en el schema).
- No correr el 21 ni Fase 5 antes de la sesión. No agregar métricas.
- No validar eventos a 240 fps con GolfDB a 30 fps.
- No re-correr perception sobre la toma de cortado3 en `data/sessions` después del 17.
- No regenerar exploración ni demo más de una vez. No desplegar desde una sesión.
- Commits y sesiones:
  - No usar `git add -A`, `git add` + commit pelado ni `git stash`.
  - No dejar `git mv` o `git rm` staged.
  - No poner dos sesiones sobre el mismo archivo.
  - No tener una sesión corriendo el motor mientras otra edita `kinelab/`.
- No leer «verde» en `pytest -q` sin conteo ni en el exit 134 del arnés.
- No agregar dependencias: opencv-contrib 4.14 con SIFT y ORB ya está.
- No levantar el front ni abrir el navegador.

---

## 8. Qué verifiqué en esta síntesis (sólo lectura) y qué no

Verificado:

- **Regla de juicio.** `registry.py:87-102`: con referencia descriptiva sin rango da `true`.
- **Schema.**
  - `judgment_allowed` es booleano requerido y `warnings` es un array de strings.
  - `fps_provenance` es el enum `[medido_aqui, sin_verificar]`.
  - La procedencia del MDC del sub-cuadro admite `sin_verificar`.
  - `header.source.master_sha256` existe (string o null).
  - `additionalProperties: false` en `reps`, `quality` y `header.source`.
  - `summary.metrics` no está restringido.
- **`mdc.yaml`.** Encabezado: nivel 0, cámara `iphone17pro-1080p120` sin verificar. En §framing, el 717 lo
  pone `head_lift_top_cm`.
- **Candidatos de segmentación** (`candidatos.txt`): rep 1 925–1765, rep 2 2130–2970.
- **Eventos y ventana.**
  - `events.py:251`: `stable_window_start` sin tope; `primitives.py:154` sin parámetro `before`.
  - `analysis.py:175`: la ventana termina en `follow_end` o `c.end`.
  - `analysis.py:104-106`: elige la escala más cercana a la mediana.
  - `analysis.py:271` y `run.py:74`: se niegan a correr si el veredicto no es ok.
- **Chequeo de encuadre.** Está en `framing.py:202-245` y `sport.py:31`; lo escribe `run.py:106-117` con
  `with_checks`.
- **Px de cuerpo por clip:** `frac_of_frame` × alto, de cada `capture.json`.
- **Demo.** `web/public/demo/72d91d03…/analysis.json` es 1.2.0 y sólo tiene tempo 2,632 como número.
- **Front.**
  - `Metricas.tsx:42` y `:54`, `TablaEventos.tsx:144` y `page.tsx:321`.
  - El servicio sólo lista `data/exploracion/`.
  - El front no muestra repetibilidad.
- **Proceso.**
  - La skill de encargo §5 permite `git add ruta && git commit -m`.
  - `.gitignore` ignora `models/`, `data/*` y `web/public/demo/`.
  - El worktree `wt16` está limpio y en un commit ancestro de main.
  - `pyproject.toml:46` tiene `addopts = "-q"`.
- **Stack.** cv2 4.14.0 con SIFT y ORB en `.venv`.
- **Datos de calibración.** `capture-paths.yaml` guarda el sha del clip del cronómetro sólo en un comentario
  (línea 103).
- **Informe 26 §1.** El cronómetro de cartado2-lenta se corre 38,6 px en x y 26,8 px en y. No está verificado
  si se movió la cámara o el cronómetro.

No verificado:

- la causa de la deriva (estabilización electrónica, trípode o suelo);
- si el Slow motion del S22 tiene una estabilización apagable;
- el palo y la altura real;
- la causa del exit 134 del arnés;
- el sitio en Vercel y la pantalla (regla del front);
- si una ingesta rechazada escribe `capture.json`;
- los MDC del arnés, que no recalculé.
