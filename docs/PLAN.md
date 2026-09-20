# Plan

Última ronda: 2026-09-20 (noche) — **cerró el 36** (`196e3a4`, `e9e2f6e`,
`a2cded3`, `3483cd9`): la pantalla deja elegir repetición y toda la pantalla
la sigue. El respaldo para trabajos viejos vive en un solo lugar,
`web/src/lib/repeticiones.ts`, que además concentra la frase «repetición N de
M» (antes en tres componentes desde dos fuentes) y busca en `analysis.reps`
por número y no por índice. `analysis.json` **2.2.0** con `reps[].scale_frame`
—el cuadro de donde salió la escala de cada repetición— y con él las cuatro
cosas que arrastra el bump. **Los 4,84 cm del 35 ahora se ven**: al pasar a la
repetición 2 de `cortado3-lento` la escala va de 783,9 px (cuadro 1594) a
831,3 (cuadro 2970) y `pelvis_sway_top_cm` de +3,7 a −7,1 cm. Motor
**462/0** (+4), arnés 43/0, front en verde, verificador de retirados 0 fallas.
**La sesión lo verificó en el navegador** (excepción pedida por Hernán) y
encontró algo que el prompt no tenía: con el respaldo, `picos` es el máximo
del clip y el encabezado decía «máximo en esta repetición»; corregido en
`a2cded3`. Un trabajo viejo (`vid1`) sigue viéndose igual, sin selector.
**Diferencia declarada con el prompt**: en un trabajo viejo no se puede
cumplir a la vez «las tres frases dicen lo mismo» y «se ve exactamente como
hoy»; la sesión eligió lo segundo. Tres preguntas en su informe, todas para
Hernán.

Ronda anterior, 2026-09-20 (noche) — **cerró el 35** (`4cb85a5`, `3114f86`,
`5730219`, `9aa699d`): `datos-eventos.json` publica todas las repeticiones en
`repeticiones_detalle`, el overlay rotula las de todas (`R2 IMPACT`) y las
fotos de la 2 en adelante salen como `evento-r<N>-<id>.png`. Los 27 campos de
primer nivel valen exactamente lo mismo que antes, medido contra el código de
`f95875c` con la misma pose. **El número que destapa: la repetición 2 de
`cortado3-lento` tenía sus desplazamientos medidos contra el address de la
1** — `pelvis_dx_vs_address_cm` en su top daba −2,21 cm y da −7,05 bien
medido, **4,84 cm contra un MDC de 2,42**. Y el pico de manos publicado arriba
(4,85 bh/s) es el de la repetición **2**, en una pantalla que dice
«repetición 1». Motor **457/0/1** (+9), arnés 43/0, front en verde, mutación
7 de 7 en rojo. Cuatro preguntas en su informe, todas para Hernán.

Ronda anterior, 2026-09-20 (tarde) — **cerró el 34** (`b94e1be`, `b4a981e`,
`a54718e`, integrado en `59f6b0b`): el fps de una toma dice de qué clip salió
su calibración. `capture-paths` **1.2.0** con `calibration_clip_sha256`
(opcional, fuera de los seis campos del cronómetro), `capture.json` **1.3.0**
con `fps_calibration {clip_sha256, same_file}`, el aviso por
`analysis.warnings` y **sin `Check` nuevo** —`CHECK_ORDER` intacto—, y el sha
del único camino calibrado declarado y verificado. De los 26 `capture.json`
del repo: **2 en `false` con aviso, 1 en `true`, 23 en `null`**. Motor 448/0
(+51), arnés 43/0, front en verde. El agente se colgó una vez por un watchdog
del harness con todo sin commitear y se reanudó con `SendMessage`, con su
contexto intacto: terminó completo. **Lo que el 34 deja a la vista y no puede
arreglar: el único clip que se calibró a sí mismo es el que el gate rechaza
por durar 2,49 s.** Falta que Hernán mire el front del 33 y el del 34.

Ronda anterior, 2026-09-20 (tarde) — el 33 quedó integrado en `main` (`2b0ed1b`)
y `scripts/integrar`, que usaba `flock` —que macOS no tiene—, está arreglado y
probado. El **34 se relanza limpio**: su primer intento quedó a medias y su
trabajo está salvado en el commit `WIP:` `5423deb` de la rama
`worktree-agent-ad505eed8bc47c798` (78 líneas en `capture_paths.py` y
`gate.py`, sin probar, sin revisar, sin el canal del aviso). No se reanuda
porque la sesión que lo escribió ya no existe: era un agente dentro de la
sesión orquestadora anterior, que se cerró, así que su contexto —el porqué de
esas 78 líneas— se fue con ella. Heredarlas significaría auditar código ajeno
sin su razonamiento, que cuesta más que reescribirlo, y el prompt del 34 ya
está completo y verificado contra el código. La rama queda como registro; no
se borra.

Desde esta ronda, **ninguna decisión del proyecto es del orquestador**: se le
preguntan todas a Hernán, incluidas las reversibles. Al orquestador le quedan
el orden del trabajo, el corte de los encargos y qué archivos toca cada uno.
Las decisiones de proyecto ya anotadas abajo siguen vigentes hasta que él las
revise.

Última ronda: 2026-09-20 — cerraron el 31 (`follow_end` acotado a su
repetición; `vid1` también estaba mal y nadie lo había visto; 390 tests) y el
32 (la máscara compra el palo en el top con 0,9° de error y nada más: en el
impacto a 240 fps el shaft no existe en el archivo). **Primera ronda con la
cadena**: el orquestador lanza el encargo con `Agent` en worktree y lo integra
con `scripts/integrar`, sin chip. Escrito el **33** (una sola escala en la
pantalla, y dicha), verificado contra el código antes de lanzarlo: la
verificación encontró seis supuestos falsos del borrador —`scale_px` no es
importable (es un método de `MetricContext`), `quality.scale_px` publicado es
la mediana **entre** repeticiones y no el divisor de ninguna fila,
`per_frame_table` no conoce las reps y tres tests la llaman posicional, matar
el fallback rompe `CONTRATO.md` §La escala, el selector de repetición cascadea
a `explore.py:366`, y el front es pnpm— y el prompt se reescribió entero.

Ronda anterior, 2026-09-19 — cerraron el 30 (el abort era la telemetría de
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

- 2026-09-20 · **Decisión de Hernán: el retiro de los campos de primer nivel
  de `datos-eventos.json` espera a R10**, el encargo que regenera todo de una
  vez después de la sesión de validación. Retirarlos antes dejaría muda la
  pantalla de los 19 trabajos de `data/exploracion/` y de la demo publicada,
  que son pre-33 y no tienen `repeticiones_detalle`; regenerar ahora gastaría
  la única regeneración permitida, que él decidió guardar. Mientras tanto el
  front lee con respaldo. Apoyo: verificación del prompt 36 (20/9).
- 2026-09-20 · **Delegada por Hernán en el orquestador: el pico del encabezado
  es el de la repetición elegida.** Una pantalla que dice «repetición 2» con
  el número de otra es lo que arreglaron el 28 y el 33. No se pierde nada: el
  `picos` de primer nivel es el del **clip entero**, no el de la repetición 1
  (`explore.py:599`), y se sigue publicando. Reversible.
- 2026-09-20 · **Decisiones de Hernán, tomadas con el 34 cerrado.** (a) Elegir
  una repetición cambia **toda** la pantalla, no sólo la tabla. (b) La
  procedencia del fps **sigue siendo registro y no chequeo**: el gate no
  rechaza una toma que heredó la tasa (cierra la pregunta 1 del informe 34).
  (c) **La única regeneración permitida de `data/exploracion/` y la demo no se
  gasta ahora**: la deriva en el análisis va a mover el schema otra vez
  después de la sesión de validación (cierra la pregunta 2 del 34). (d) El
  front del 35/36 **lo prueba la sesión**, por esta vez.
- 2026-09-20 · **Decisión de Hernán: la pregunta 9 se cierra.** Miró
  `palo-local-1364.png` y la marca del palo no arranca en la mano y el ángulo
  está torcido. El impacto queda como está y no se abre encargo del shaft. Con
  esto la decisión del 32 (abajo) deja de ser reversible-pendiente.
- 2026-09-20 · **La procedencia de la calibración se registra, no se exige**, y
  `calibration_clip_sha256` va **fuera** de `_CALIBRATION_FIELDS` (34).
  Exigirlo dejaría sin cargar el único camino calibrado del repo y el fixture
  `tests/conftest.py:137`, y con él centenares de tests; y con n = 1 no hay
  material para reemplazarlo. Se deshace el día que haya tres caminos
  calibrados. Apoyo: verificación del prompt 34 (20/9).
- 2026-09-20 · **El fallback de `px_to_cm` no se mata, se declara.** Del 33:
  hay tres escalas conviviendo (la cadena de estatura de la repetición, el
  `body_height_px` del cuadro en la tabla, y el mismo `body_height_px` como
  fallback silencioso de `core.py:167-172`). Matar el fallback cambiaría
  valores publicados por `null` y eso es del dominio; declarar la procedencia
  de cada cm es lo que el proyecto ya exige a cualquier número, no cambia un
  valor y se deshace. Apoyo: verificación del prompt 33 contra el código
  (20/9) — el único consumidor del fallback es `generic.py:42`, o sea todas
  las métricas en cm, y `CONTRATO.md` §La escala lo documenta como convención.
- 2026-09-20 · **Del 32: no se abre encargo de producto del shaft como
  evento.** La recomendación del informe se acepta: lo que falta no es un
  modelo de segmentación sino un obturador más corto, que `CAPTURA.md` §Luz ya
  pide y nadie midió. Reversible: si la pregunta 9 se contesta y Hernán ve el
  shaft donde la sesión no lo vio, se rehace el número del impacto y se
  reabre. Nada de esto traba el 33 ni el 34.
- 2026-09-20 · **El selector de repetición sale del 33 y es encargo propio.**
  Toda la pantalla es la repetición 1 porque el motor la arma así
  (`explore.py:366`, `analysis["events"][0]`), no sólo el front
  (`Metricas.tsx:92`): un `<select>` desincronizaría métricas, eventos,
  overlay y tabla. El 33 la **dice**; elegirla cambia el formato de
  `datos-eventos.json` y va aparte.
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
- **R5** · [hecho] **31** follow-end-en-su-repeticion — `513194c`, `6bea1fb`,
  `e6fa101`. `follow_end` acotado a su candidato; `vid1` pasa de 931 a `null`
  por el mismo bug, sin que nadie lo hubiera visto; `tol_frames` en la
  pantalla; tres restos; 390 tests ∥ [hecho] **32** mascara-del-sujeto —
  `83338ca`, `99acf16`. La máscara compra **el palo en el top** (0,9° de
  mediana contra etiquetas a ojo, 10 de 10 bajo 5°) y **nada más**: en el
  impacto 66° y 0 de 8, porque a 240 fps el shaft ya es un borrón que a ojo
  tampoco se marca; el cuerpo entero no (cobertura 0,18–0,42) porque el
  golfista no se corre y detrás no hay fondo; la escala da 12 % de más. Cuesta
  68 ms/cuadro en FHD, 407 en UHD. **Nada entra al motor.**
- **R6** · [hecho] **33** una-sola-escala-en-la-pantalla — `9f8c008`,
  `5c469e9`, `e4c44d2`, integrado en `2b0ed1b`. Junta la «una-sola-escala» del
  inventario del 16/9 con «escala-y-altura-trazables»: eran lo mismo. **Los
  dos cm del mismo evento diferían de 1,66 a 4,39 cm** —`pelvis_sway_impact_cm`
  de `cortado3-lento`: 22,6 en las métricas contra 26,99 en la tabla, con un
  MDC de 2,42— y ahora difieren ≤ 0,046 cm, que es el redondeo.
  `reps[].scale_px` y `scale_source` en `analysis.json` (schema **2.1.0**),
  cada cm con su procedencia, un cuadro fuera de toda repetición sin cm (en
  `vid1`, 903 de 1066 filas), «repetición 1 de N» dicha. **Ninguna métrica de
  `analysis.json` se movió.** 398 tests; mutación manual 8 de 8 en rojo.
  Falta que Hernán mire el front (la celda «pelvis vs address» en el top:
  −3,5 cm, antes −4,6).
- **R8** · [hecho] **35** el-motor-publica-todas-las-repeticiones — la
  mitad del motor de «repeticion-elegible». Verificado con tres subagentes
  antes de lanzarlo: **la premisa del plan estaba mal**, no es
  `explore.py:366` sino `:428` (`analysis["events"][0]`) y `:474`
  (`analysis["reps"][0]`); y el hallazgo que parte el encargo en dos es que
  **el front no puede elegir nada** —overlay, fotos por evento y
  `datos-eventos.json` los arma el motor con la rep 1—, así que un selector
  solo de front era imposible. `analysis.json` ya tiene todas las
  repeticiones: no hay que recalcular nada. Los campos de primer nivel quedan
  como están para no romper el front, y el 36 los retira.
- **R8** · [hecho] **36** selector-de-repeticion — el front, con respaldo
  al formato viejo, y `scale_frame` en `reps[]` (analysis **2.2.0**).
  Verificado con tres subagentes: encontraron que **ningún trabajo en disco
  tiene `repeticiones_detalle`** (los 19 de `data/exploracion/` y los 3 de la
  demo son pre-33, `analysis.json` 1.2.0), que el `picos` de primer nivel es
  **del clip** y no de la repetición 1, que `eventos_frame` de primer nivel lo
  leen también `service/exploracion.py:151` (la lista de trabajos) y
  `exportar_demo.py:162`, que el bump de versión arrastra `retirados.ts:57`,
  el verificador y `data/examples/analysis.example.json`, y que cuatro
  estados internos del front se quedan pegados al cambiar de repetición. Seis
  de las líneas de tests que citaba el borrador estaban mal. Antes: siete
  componentes
  (`page.tsx`, `Metricas.tsx`, `TablaEventos.tsx`, `TablaCuadros.tsx`,
  `Reproductor.tsx`, `DosCuadros.tsx`, `Avisos.tsx`), sin contexto de React:
  todo baja por props desde `page.tsx`, así que la repetición elegida es un
  `useState` ahí. **Lo prueba la sesión en el navegador** (decisión de Hernán,
  20/9, excepción a su regla de siempre).
- **R7** · [hecho] **34** fuente-de-la-calibracion — `b94e1be`, `b4a981e`,
  `a54718e`, integrado en `59f6b0b`. Relanzado limpio; el intento anterior
  quedó en `5423deb` (rama `worktree-agent-ad505eed8bc47c798`), descartado.
  Cuatro preguntas en su informe §Preguntas, todas para Hernán. — `calibration_clip_sha256`
  en capture-paths 1.2.0, `fps_calibration.same_file` en capture 1.3.0, el
  aviso por `analysis.warnings`, y `fps_truth` emitiendo el sha. **La premisa
  del plan estaba mal**: no hay divergencia entre `ingest/__main__.py:103` y
  `service/exploracion.py:277` — resuelven la misma ruta, y
  `default_capture_paths_file()` no toma argumentos, así que usarla ahí
  ignoraría `--data`. Queda sólo cambiar el literal por la constante.
  Front: lo prueba Hernán.
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

9. ~~Del 32: ¿se ve el shaft en 1364?~~ **Contestada el 20/9 por Hernán, con
   la imagen a la vista.** No lo ve: la marca de la máscara «está muy cerca
   pero no del todo bien — no arranca desde la mano y el ángulo no es
   correcto». Confirma los 66° y el 0 de 8 del 32. **El número del impacto no
   se rehace y el shaft no se abre como encargo**; lo que falta es obturador
   más corto (`CAPTURA.md` §Luz), no un modelo mejor. Decisión de Hernán, no
   del orquestador.

## Aparcado

- Pádel (invariante 17). SynthPose (1.5) después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra con la ingesta 4.3.
- Instante sub-cuadro del top; lámina interpolada en el front.
