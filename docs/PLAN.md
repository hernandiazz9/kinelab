# Plan

Última ronda: 2026-09-19 — cerraron el 30 (el abort era la telemetría de
onnxruntime, apagada al importar `kinelab.perception`; 381 tests) y el 29 (la
deriva se reproduce en x y en y es 26–30 px, 2× el MDC de `lift`; hasta
+119 px en `vid1`). Escritos el 31 (follow_end dentro de su repetición, la
banda visible, una señal en exploración, tres restos) y el 32 (experimento
de máscara del sujeto, a pedido de Hernán: el palo, la escala, las
etiquetas). Corren en paralelo.

Ronda anterior, 2026-09-18 (noche) — el método pasó a una skill genérica en
`~/.claude/skills/orquestador` (plantillas, reglas de sesión, cementerio del
método, script de arranque) y el repo lleva su copia en `.claude/skills/`.
Cambios que aplican desde ya: el informe lleva un «Resumen» de diez líneas
arriba; el prompt lleva un campo «Front» que se le pregunta a Hernán; las
sesiones nunca terminan sin commitear y no queman fechas ni conteos en tests.
Se prueba la entrega por chip con el 29. El 17 cerró (ver R3). Sigue el 30, solo,
con dos cosas chicas del 17 sumadas; después el 29.

Ronda anterior, 2026-09-18 (tarde) — el 27 y el 28 cerraron: 0 de 21 juicios
con los 24 valores intactos, 357 tests; la pantalla sin las tres columnas
retiradas ni el «±1 cuadro» fijo. Escritos el 29 (deriva de cámara) y el 30
(exit 134); el 17 corre primero y solo. Decisión sobre el cronómetro: es
calibración del camino, una vez, nunca del usuario; en la sesión de
validación va sólo en la primera toma de cada vista (17 lo escribe en la
guía). Sin material nuevo todavía.

Ronda anterior, 2026-09-18 (mañana) — revisión de continuidad por el
orquestador de la sesión original, después de que otra sesión orquestadora llevó el proyecto del
16 al 26 y la auditoría. Nada corrió desde el 16/9: el árbol está limpio en
`dfbf4a7` y el 27 y el 28 siguen sin correr. Se confirma el plan de abajo con
un cambio de orden: Hernán filma la sesión de validación **ya**, sin esperar
a R2 y R3 (la guía cubre las hipótesis de la deriva); el código de R2–R6 hace
falta para analizarla, no para filmarla. Y se reduce la verificación previa de
prompts a dos o tres agentes por prompt: siete por prompt fue lo que encontró
los errores, pero cuesta más que el encargo.

Ronda anterior, 2026-09-16 — **auditoría del primer juicio**
(`docs/informes/2026-09-16-auditoria-primer-juicio.md`, 23 agentes). El 15/9
`cortado3-lento.mp4` pasó el gate 9 de 9 y dio los primeros 21
`judgment_allowed: true`. Reproducidos desde HEAD `f866c77`: **la aritmética es
exacta en los 21 y ninguno resiste como juicio** (follow_end en el swing
siguiente, deriva de cámara de 8–25 px, eventos de manos contra palo 4–16
cuadros, MDC de nivel 0 con cámara sin verificar, y una regla que habilitaba
juicio sin rango). Escritos 27 y 28; reescrito 17; postergado 21; corregida la
regla de commits de `/encargo`.

Regla de numeración: un ítem recibe número cuando se escribe su prompt; los
pendientes van sin número, en orden.

## Dónde está el proyecto, sin optimismo

**Fase 0 abierta.** Hay un camino calibrado (n = 1, un recorte de la Mac) y un
clip que pasa el gate, pero no la sesión que pide la aceptación: 10–20 swings
por vista, en las dos vistas, con cronómetro. Las Fases 1 a 3 están
construidas y en verde contra datos sintéticos; sus criterios que piden
material real siguen abiertos (`docs/informes/auditoria-2026-09-16/
estado-fases.md`). **Ningún número del proyecto es hoy un juicio válido.**

## Congelado hasta la sesión de validación

- La tabla del informe 26 §4 **no es una medición**. No se muestra `cortado3`
  ni ninguna SD entre repeticiones.
- Nada de Fase 5, del 21 ni de métricas nuevas.
- No se ajusta ningún umbral de eventos (`follow_still_s`, `wrist_score_min`,
  `still_speed_max`, `top_band_sigmas`) ni el 717 con `cortado3`: es n = 1.
- No se compensa la deriva de cámara dentro de las métricas.
- No se regenera `data/exploracion/` ni la demo más de una vez.

## Decisiones del orquestador

- 2026-09-18 · **El cronómetro nunca es del usuario.** Calibra un camino
  (teléfono + modo + transferencia) una vez y queda en `capture-paths.yaml`;
  quien filma después con ese camino lo elige en la pantalla y no filma nada
  más. Un reloj puesto por software no sirve: nada en el archivo registra el
  tiempo real, sólo algo en la imagen. En la sesión de validación el
  cronómetro va sólo en la primera toma de cada vista y en la escena vacía
  (para pasar de n = 1 a n = 3 y calibrar el archivo crudo de `DCIM`, no el
  recorte de la Mac). Después, para el S22 en Slow motion 240 por cable, no
  hace falta más.
- 2026-09-19 · Del 29: `quality.camera_motion_px` mide sacudones, no deriva;
  se **renombra** a `camera_jitter_px` en el encargo de deriva-en-el-análisis,
  que por §Versionado pasa a ser **3.0.0** (renombrar es major) y va después
  de la sesión. La auditoría subestimó la y: nota fechada bajo ADR-019 (31).
- 2026-09-19 · Del 30: el análisis **sigue** negándose sobre una toma con el
  gate en `reject` (sea de ingesta o de Fase 1); lo único re-corrible es la
  percepción. La cola de telemetría de onnxruntime en
  `~/Library/Application Support/Microsoft/DeveloperTools/.onnxruntime/` la
  borra Hernán si quiere; ya no crece.
- 2026-09-19 · Sacar el fondo del video para la pose: **no** (modelo
  entrenado con fondos; el error va por bbox y plausibilidad; y el fondo es
  la referencia de la deriva). Una máscara del sujeto se **mide** antes de
  decidir: el palo, la escala y las etiquetas (32). Nada entra al motor sin
  ese número.
- 2026-09-18 · Del 17: un rechazo de la Fase 1 tiene que poder re-correrse
  (`run.py` decide sólo con los chequeos de ingesta; va en el 30). El
  chequeo usa la **mediana** de `body_height_px`, no el peor cuadro; `min` y
  `max` viajan en el reporte por si hace falta mirarlos. Anotado y aparcado:
  el valor depende 1,2 px del `fps_real` declarado por la ventana de 1 s del
  suavizado. Ningún clip del repo pasa hoy el pipeline entero: los de Video
  no llegan al fps y los de Slow motion no llegan a los 717 px. Es lo que el
  umbral tiene que hacer.
- 2026-09-18 · Del 27: el aviso condicional está bien; `Registry.mdc_note`
  se queda; el `follow_end` 1978 de cortado3 se muestra con aviso propio
  cuando lo arregle el encargo de follow_end (R4), no antes. Del 28: el
  despliegue a mano tiene que quedar en `data/publicados.json`; entra en R10.

- 2026-09-16 · **ADR-019** (lo escribe el 27): juicio sólo con MDC validado en
  material real del camino (campo propio `mdc_validation: material_real`, **no**
  `medido_aqui`: la procedencia sigue diciendo de dónde sale un número, y el
  MDC del arnés sí es `medido_aqui`) **y** rango de referencia con procedencia
  fuerte (ni `estimacion` ni `sin_verificar`, por el invariante 12). Corrige `CONTRATO.md:390` y
  `registry.py:87-102`, que permitían juicio sin rango contra la definición de
  `CONTEXTO.md:49-51`. Hoy da 0 de 21; los valores no cambian; sin cambio de
  schema; `registry_version` 0.3.0.
- 2026-09-16 · **Los prompts 27, 28 y 17 se verificaron contra el código antes
  de commitearlos** (siete agentes, dos lentes por prompt y un cruce). Salieron
  más de veinte correcciones: once tests que el 27 iba a romper sin decirlo, el
  17 en paralelo con la deriva violando la regla de motor contra ediciones, y en
  el 28 una prueba que no probaba nada y un comando de despliegue que
  regeneraba la demo. Desde ahora, **todo prompt que toca código se verifica
  así antes de pasarlo a Hernán**.
- 2026-09-16 · **Proceso** (ya aplicado en `.claude/skills/encargo/SKILL.md`
  §5): commit sólo con `git commit -m … -- rutas`; `git diff --cached` vacío al
  empezar; `git mv`/`git rm` en el mismo comando que su commit; máximo dos
  sesiones; una sesión que corre el motor sobre material no coincide con otra
  que edita `kinelab/` o `sports/`; tests por exit code y conteo. Ningún prompt
  depende de un encargo sin informe.
- 2026-09-16 · **17**: se corre con el 717 y archivos corregidos
  (`framing.py`, `sport.py`, `config.py`; no `gate.py`); se re-decide el número
  con el σ por keypoint medido en material real. **21**: postergado hasta
  después de la sesión, con cinco ajustes anotados en su prompt.
- 2026-09-16 · **follow_end**: la cota es el fin de su propio candidato de
  segmentación; ni el address ni el candidato siguientes sacan la quietud. La
  definición (llegar a la pose final o soltarla) la decide Hernán.
- 2026-09-16 · **Deriva de cámara**: medir y censar antes de integrar; en el
  análisis, si |desplazamiento| ≤ |deriva| en el eje, null con razón; si no, la
  deriva entra a la banda con aviso. No compensar sin validación.
- 2026-09-16 · **Escala**: no cambiar la convención del 14; publicarla por
  repetición con marca de borde de ventana y la altura con su fuente. Se
  resuelve con la referencia de pie de la sesión.
- 2026-09-16 · **Calibración heredada**: hacerla visible por clip. No habilita
  juicio hasta tener al menos tres cronómetros dentro de 1σ (propuesta).
- 2026-09-16 · **GolfDB**: aparcado para validar eventos a 240 fps (es de
  30 fps); el error de eventos se mide con etiquetas propias.
- 2026-09-16 · Aparcado hasta tener error de eventos medido: el escalón de media
  empuñadura, la banda conjunta de eventos, la definición del address,
  `thorax_lift_top_cm` con el hombro tapado, `head_sway` como inclinación más
  traslación, y el sesgo de −11,3 ms del sub-cuadro contra la pelota.
- Anteriores, vigentes: ADR-016 caminos declarados · ADR-017 top por mayor
  excursión · ADR-018 mueren la ganancia y `sequence_order` · fps efectivo sin
  el delta de arranque · `fps_min` con tolerancia del 0,5 % · 4K desaconsejado
  · `duration_plausible` no se baja, se filma más largo · publicar es
  deliberado por trabajo y los datos publicados no van a git · 3D sólo del
  mocap, nunca reconstrucción monocular · nada de APIs de IA externas.

## Backlog, en rondas

Máximo dos sesiones a la vez, sin archivos compartidos. `CONTRATO.md` lo edita
una sola sesión por vez.

- **R1** · [hecho] **27** contencion-del-juicio — `843d1f4`, `4340a06` ∥
  [hecho] **28** pantalla-sin-falsedades — `9107e5b`, `e4acf3a`. Hernán
  despliega la demo con el comando del informe del 28 (¿hecho?).
- **R2** · [pendiente] **30** abort-al-salir, **solo** y primero: Hernán ve
  seguido el cartel «Python se ha cerrado inesperadamente»; es el teardown de
  CoreML con una sesión viva al salir (servidor con Ctrl-C, arnés, quizá
  `datos`). Diagnóstico por bisección y arreglo en la raíz
  (`kinelab/perception/estimator.py`, `__init__.py`, cierre en `explore`,
  `run` y el servidor), más un test por subproceso. Reescrito el 18/9: antes
  era sólo `truth/`.
- **R3** · [hecho] **17** gate-encuadre-en-px — `6bae365`, `faac07b`. 717 px;
  `cortado3` rechazado por 26 px (691); la guía con §7 «La sesión de
  validación» y el cronómetro sólo en la primera toma de cada vista. Corrió
  antes que el 30 porque ya estaba en marcha.
- **R2** · [hecho] **30** abort-al-salir — `db46aa4`, `23fba14`. Telemetría
  de onnxruntime; `truth/corridas.sh 10`; la percepción se re-corre tras un
  rechazo de Fase 1.
- **R4** · [hecho] **29** deriva-de-camara-censo — `83c152f`, `8faa9a6`.
  Aceptado contra la auditoría en x; en y 26–30 px; censo hasta +119 px.
- **R5** · [en curso] **31** follow-end-en-su-repeticion — la cota del
  candidato propio; `tol_frames` en `datos-eventos.json` y en la tabla; una
  señal en exploración; `git rm order.py`; docstring de `gate.py`; nota de la
  y bajo ADR-019 ∥ [en curso] **32** mascara-del-sujeto — experimento en
  `banco/`: máscara clásica estabilizada con el 29, el shaft contra etiquetas
  a ojo en 20 cuadros, la escala coronilla-suela contra la cadena, y la tabla
  de licencias sólo si lo clásico no alcanza.
- [pendiente] una-sola-escala-en-la-pantalla — la tabla por cuadro convierte
  a cm con `body_height_px` de cada cuadro y las métricas con
  `quality.scale_px`: dos números en cm para el mismo evento en la misma
  pantalla; y la repetición elegida (hoy siempre la 1, y sin address el cero
  es el cuadro 0) dicha o elegible. Inventario del 16/9.
- **R6** · [pendiente] escala-y-altura-trazables (analysis 2.1.0).
- **R7** · [pendiente] fuente-de-la-calibracion — `calibration_clip_sha256` en
  capture-paths 1.2.0, `fps_calibration.same_file` en capture 1.3.0, aviso, y
  `ingest/__main__.py:103` que lee `capture-paths.yaml` de `--data`.
- **Hernán filma la sesión de validación** (ver Preguntas). Puede filmar ya: la
  lista cubre las hipótesis de la deriva; el código de R2–R6 hace falta para
  **analizarla**, no para filmarla.
- **R7** · [pendiente] sesion-fase-0 — ingesta con cronómetro por toma y el
  rechazo de la toma por WhatsApp como video; pose y análisis; deriva por toma
  y en la escena vacía; escala contra la referencia de pie y la altura con
  cinta. Sin tocar código.
- **R8** · [pendiente] error-de-eventos-y-piso-de-ruido — etiquetas del palo a
  240 fps (Hernán confirma cinco), Bland–Altman por evento con n ≥ 20 por
  vista, σ por keypoint en quietud ∥ [postergado] **21** visor-desde-datos,
  re-emitido con sus ajustes.
- **R9** · [pendiente] deriva-en-el-analisis (analysis 2.2.0) — `camera.npz`
  aparte de `pose.npz`, `reps[i].camera_drift_px`, la regla de null/banda.
- **R10** · [pendiente] regenerar-una-vez — exploración y demo desde `pose.npz`
  al contrato vigente, con la tabla de cambios. Despliega Hernán.
- **Ronda del orquestador con evidencia** — ADRs de definición (finish, top,
  address), la banda, el 717, qué condiciones de ADR-019 cumple cada métrica, y
  si la Fase 5 arranca con descriptivos.
- [pendiente, sin ronda] `summary.metrics.hands_speed_curve_top_to_impact`
  (`kinelab/analysis.py:215`) no es una métrica del registro y no tiene las
  seis cosas de `AGENTS.md`: registrarla con las seis o sacarla del summary.
  Y el comentario de `web/src/components/TablaCuadros.tsx:4` dice 118 columnas:
  hoy son 115 con altura y 106 sin ella.
- [pendiente, sin ronda] pasada-barata-local; barrido de geometría de cámara
  para los ángulos del 23; archivar `docs/checklist-captura.md` (iPhone) cuando
  la sección de la sesión de validación exista.

## Hechos

01–15, 18–20, 22–26 (ver `docs/informes/`). El **01** y el **16** llevan
informe de arqueología, escrito el 20/9 desde el historial y marcado como tal:
el 01 es anterior al método (se hizo el 12/9; el formato de informes se
escribió ese mismo día, en `27fe21f`), y el 16 se commiteó en `03aea3f` por la
sesión del 18 sin dejar informe, con su punto 6 cerrado por el 27. Ninguno de
los dos dejó números propios, y los informes lo dicen. Demo pública:
`https://kinelab-qnm5fa60a-hernandiazz9s-projects.vercel.app` (sin protección,
`noindex`; el video de `vid1` es accesible con el enlace).

## Preguntas para Hernán

1. **Sobre `cortado3-lento` (15/9), de memoria:** ¿trípode? ¿sobre qué suelo?
   ¿lo tocaste entre swings? ¿había viento? ¿Super Steady apagado, y hay otra
   estabilización de video en Ajustes? ¿qué palo era (se declaró driver; dos
   agentes ven un hierro)? ¿cuánto medís con cinta? ¿editaste el tramo lento en
   Galería?
2. **Dos definiciones de entrenador**, que mueven los números más que el MDC:
   (a) el fin del follow: cuando llegás a la pose final, o justo antes de
   soltarla (≈380 ms de diferencia); (b) top y address: de las manos (lo que
   mide hoy el motor) o del palo (4–16 cuadros de diferencia).
3. **ADR-019**: hasta validar en material real, ninguna métrica es juicio.
   Decidido por el orquestador por ser conservador y reversible; si no estás de
   acuerdo, se reabre.
4. **La sesión de validación**: la lista está en el prompt del 17 §4 y en el
   mensaje del 16/9. Se puede filmar ya.
5. **La demo**: hasta desplegar el 28, no abrir la tabla de picos de `vid1`
   (muestra `hip_line_rate_deg_s 3662,0`), no mostrar `cortado3` ni ninguna SD.
6. Opcional: `git worktree remove` del worktree `wt16` de una sesión vieja
   (limpio, en `2e781be`, ya en main).
7. ~~¿El chip del 29 anduvo?~~ **Contestada el 20/9, medida.** Un chip de
   prueba abrió la sesión en el checkout principal, en `main`, con `.venv`,
   `truth/.venv`, `data/` y `web/node_modules` a mano; `import kinelab`
   funciona. El chip queda como forma de entrega por defecto y su prompt es
   `/encargo NN` a secas: el §0 nuevo de `/encargo` hace que la sesión se
   pare sola en la carpeta correcta, caiga en worktree o no.
8. **Dos definiciones de entrenador siguen sin respuesta** (punto 2): el 31
   acota el fin del acompañamiento a su repetición, pero qué es el finish lo
   tenés que decir vos.

9. **Del 32, y traba el número del impacto:** abrí
   `data/incoming/cortado3-lento.kinelab/mascara/palo-local-1364.png` y decí si
   ves el shaft. La sesión marcó una estela tenue y no marcó nada en 1367 y
   1368. Si vos lo ves y ella no, el impacto se rehace.

## Aparcado

- Pádel (invariante 17). SynthPose (1.5) después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra con la ingesta 4.3.
- Instante sub-cuadro del top; lámina interpolada en el front.
