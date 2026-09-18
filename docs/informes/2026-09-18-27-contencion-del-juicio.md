# contencion-del-juicio — 2026-09-18

**Encargo:** escribir ADR-019 y llevarlo al código —ninguna métrica es juicio
hasta validar su MDC en material real, y sin rango de referencia con procedencia
no hay contra qué juzgar—, alinear los cuatro documentos, agregar los dos avisos,
poner la repetibilidad en `null` mientras no haya piso de ruido, sacar
`addopts = "-q"`, anotar ADR-018 en la spec, ingestar `cortado3-lento.mp4` a
`data/sessions/` real y cerrar el punto 6 del encargo 16. Sin tocar `web/` ni
`service/` (el 28 corre en paralelo), sin cambiar ningún valor ni ningún umbral.

## Hecho

- **ADR-019 en `DECISIONES.md`**, citando ADR-007 (al que sustituye en parte),
  ADR-012 y ADR-016, con su «Consecuencia».
- **`judgment_allowed` con dos condiciones nuevas e independientes**
  (`kinelab/metrics/registry.py`), cada una con su comentario y su test:
  `mdc_validation == "material_real"` y rango obligatorio con procedencia fuera
  de `estimacion`/`sin_verificar`.
- **`Metric.mdc_validation`**, enum de dos valores con default `sin_validar`,
  validado en `__post_init__`. **No es una procedencia**: ni `PROVENANCES` ni el
  enum de `fps_provenance` del schema se tocaron.
- **Registro de golf 0.2.0 → 0.3.0**; el genérico del motor queda en 0.1.0.
  `schema_version` sigue en 2.0.0 y ningún `metric_version` se movió.
- **Dos avisos en `warnings[]`** (§4), **repetibilidad en `null` con razón**,
  **`source` del MDC del sub-cuadro** diciendo que no está validado,
  **`pyproject.toml`** sin `addopts`, y las notas de ADR-018 en
  `ESPECIFICACION.md` 3.2 y Fase 5.
- **Documentos alineados:** `CONTRATO.md` §El sextuplo (la fórmula nueva y por
  qué se corrige la línea vieja), §summary, §subframe y §Versionado;
  `CONTEXTO.md` §Vocabulario e invariante 4.
- **`data/sessions/` existe por primera vez**: cortado3 ingestado, con
  percepción y análisis.

Commits: `843d1f4` (código, documentos y ejemplo regenerado) y el de cierre con
`ESTADO.md` y este informe.

## Probado

### 1 · La prueba de punta a punta: 0 de 21, con los valores intactos

```
.venv/bin/python -m kinelab.ingest data/incoming/cortado3-lento.mp4 --atleta hernan \
  --gesto driver --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac
.venv/bin/python -m kinelab.perception data/sessions/hernan/2026-09-15/driver/face_on/take-01
.venv/bin/python -m kinelab analyze  data/sessions/hernan/2026-09-15/driver/face_on/take-01 --altura-m 1.75
```

| | valor |
|---|---|
| gate | **OK, 9 de 9** · `fps_provenance: medido_aqui` · 2977 cuadros · 12,3964 s reales |
| percepción | detección **100,0 %** · cuerpo **691 px = 36 % del alto** · cámara 1,35 px |
| calidad | `confiable` · `scale_px` **783,9 px, cuadro 1594** |
| repeticiones | 2, 1 descartada `sin_address` |
| eventos rep 1 · rep 2 | 1052 · 1284 · 1364 · 1978 / 2322 · 2548 · 2624 · — |
| **`judgment_allowed: true`** | **0 de 21** (24 sextuplos: 21 con valor, 3 `null`) |
| **valores contra la auditoría** | **24 de 24 idénticos** |

Los 24 se compararon uno por uno contra
`docs/informes/auditoria-2026-09-16/reproduccion.md` §3: **cero diferencias**,
incluidos los tres `null` (`pelvis_thrust_top_cm` en las dos reps por vista, y
`follow_duration_ms` de la rep 2 por falta de `follow_end`). Mismos cuadros de
evento, misma escala, misma calidad. **La regla apaga la bandera y no toca un
número**, que es lo que el encargo pedía demostrar.

Las **13 repetibilidades** del `summary` salen en `value: null` con
`noise_floor: null` y su `null_reason`, conservando el `n` (2, salvo
`follow_duration_ms` con 1 y `pelvis_thrust_top_cm` con 0).

### 2 · Suites

| suite | pasados | fallados | exit |
|---|---|---|---|
| motor `.venv/bin/pytest` | **357** | **0** | **0** |
| arnés `cd truth && .venv/bin/pytest` | **43** | **0** | **0 / 134 / 0** |

- Motor: eran **345**. Entran **12 tests nuevos** y se adaptaron **11
  existentes**, todos en `tests/test_fase2.py`, sin borrar ninguna aserción.
- **El exit 134 del arnés es intermitente, no sistemático:** tres corridas
  seguidas dieron 0, 134 y 0, siempre con 43 pasados y el aborto
  (`libc++abi … recursive_mutex lock failed`) **después** del resumen. No se
  tocó. Es un dato nuevo respecto de la auditoría, que lo vio en 2 de 2.

**Los 11 tests que la regla rompía, y cómo quedaron.** `test_registry_rules_and_judgment`
y los **7 casos `True`** de la tolerancia NTSC declaran ahora
`mdc_validation="material_real"` y un `Reference("range", "pares", …)`: siguen
probando lo suyo —la vista, el fps, ADR-016, el MDC más ancho que el rango— con
todo lo demás en orden. `test_a_declared_path_keeps_the_numbers_and_kills_every_judgment`
pasó a correr con un **registro de prueba** con una métrica validada y con rango
(golf ya no tiene juicio que apagar), y se le agregó la otra mitad: con el mismo
take calibrado, **el registro de golf no enciende ninguno**.
`test_metric_version_travels…` y `test_repo_example_is_valid` pasan a 0.3.0, y
`test_metrics_in_analysis` cambió `judgment_allowed is (mdc is not None)` por
dos aserciones separadas: el MDC **sigue viajando** en el sextuplo, y el juicio
es `False`.

### 3 · Mutación manual: 5 de 5 en rojo

| mutación | rojos | cuáles |
|---|---|---|
| sin la condición (a) (`mdc_validation`) | **1** | `test_an_unvalidated_mdc_is_not_judgment…` |
| sin la condición (b) entera (vuelve `ref is None or …`) | **3** | el del rango ausente y los dos de procedencia floja |
| dejando pasar la procedencia floja | **2** | `…weak_provenance[estimacion]` y `[sin_verificar]` |
| `mdc_validation` con default `material_real` | **3** | el de arriba más `test_no_golf_metric_is_judgment_today` y el de los avisos |
| la repetibilidad volviendo a publicar la SD | **2** | `test_repeatability_without_a_noise_floor…` y `test_metrics_in_analysis` |

Cada condición tiene al menos un test que sólo ella pone en rojo, que era el
criterio del prompt. El archivo se restauró desde una copia y se verificó
idéntico (`diff` limpio) antes de seguir.

### 4 · Los dos avisos

```
Ninguno de estos números es un juicio: se muestran como descriptivos, con su banda, y no se
comparan contra ningún rango. Para que una métrica pueda juzgarse hay que validar su MDC sobre
material real —el mismo estimador, el mismo camino de captura, los eventos contra etiquetas
humanas, la deriva de cámara medida y la escala trazable— y tener un rango de referencia con
procedencia. Hasta entonces, comparar dos tomas es mirar, no medir (ADR-019).

El MDC que viaja con cada número todavía no está validado en material real: los midió el arnés de
verdad en su nivel 0 —un esqueleto proyectado con una cámara virtual más ruido, sin estimador de
pose en el medio— y con una cámara (iphone17pro-1080p120) que no es la que filmó y que nadie
verificó. Sirven para ordenar magnitudes; no describen todavía el error de este teléfono sobre un
swing real (sports/golf/mdc.yaml, ADR-019).
```

Van **después** de los de fps de ADR-016, que siguen primeros (hay test). Dos
decisiones de forma, las dos anotadas como desviación en `ESTADO.md`:

1. **El primero no se escribe si el archivo lo contradice.** Sale de recorrer
   los sextuplos: si alguna métrica tuviera `judgment_allowed: true`, la frase
   sería falsa. Con golf la condición se cumple siempre; el test prueba las dos
   ramas.
2. **El segundo lo declara el deporte, no el motor.** Nombra el arnés, su nivel
   y el modelo de cámara, y eso no puede vivir en `kinelab/` (invariante 13). El
   motor sólo transcribe `Registry.mdc_note`, que golf llena.

### 5 · El punto 6 del encargo 16, cerrado

`datos … --altura-m 1.75` sobre los dos clips, contra la columna **«ahora»** del
informe 14 §4. Los dos siguen en `sin_verificar` y en **0 de 12** juicios.

**`~/Desktop/cortado.mp4`** — 76 cuadros a 29,999 fps · eventos **7 · 35 · 44 ·
—** (tol 1 · 1 · 1) · escala **1089,6 px, cuadro 75** (la misma del 14).

| métrica | 14 «ahora» | hoy | Δ | MDC |
|---|---|---|---|---|
| `pelvis_sway_top_cm` | −5,2 | **−3,5** | +1,7 | 2,841 |
| `pelvis_sway_impact_cm` | 6,0 | **6,0** | 0,0 | 2,416 |
| `pelvis_lift_top_cm` | −0,3 | **−1,0** | −0,7 | 2,769 |
| `thorax_sway_top_cm` | −1,5 | **−0,2** | +1,3 | 3,388 |
| `thorax_lift_top_cm` | −3,9 | **−2,1** | +1,8 | 2,819 |
| `head_sway_top_cm` | 2,7 | **3,3** | +0,6 | 3,779 |
| `head_lift_top_cm` | −4,3 | **−4,8** | −0,5 | 4,382 |

**La causa es el encargo 18 y nada más: el top pasó de 33 a 35** (la señal de
manos pesada por confianza con `wrist_score_min` 0,55). Tres cosas lo confirman:
las seis que se mueven están todas ancladas al top; **`pelvis_sway_impact_cm`,
la única que no lo está, no se movió ni un decimal**; y la escala y el address
son idénticos a los del 14. **Los seis movimientos quedan por debajo de su
propio MDC** (el mayor, 1,8 cm contra 2,819).

**`data/incoming/vid1.mp4`** — 1066 cuadros a 60,026 fps · eventos **672 · 722 ·
741 · 931** (tol 1 · **4** · 1 · 2) · escala **1199,9 px, cuadro 876**.

| métrica | 14 «ahora» | hoy | Δ | MDC |
|---|---|---|---|---|
| `pelvis_sway_top_cm` | −3,5 | **−3,5** | 0,0 | 2,841 |
| `pelvis_sway_impact_cm` | 12,6 | **12,6** | 0,0 | 2,416 |
| `pelvis_lift_top_cm` | −10,3 | **−10,2** | +0,1 | 2,769 |
| `thorax_sway_top_cm` | −2,4 | **−2,4** | 0,0 | 3,388 |
| `thorax_lift_top_cm` | −6,5 | **−6,5** | 0,0 | 2,819 |
| `head_sway_top_cm` | −8,1 | **−8,1** | 0,0 | 3,779 |
| `head_lift_top_cm` | −7,2 | **−7,2** | 0,0 | 4,382 |

**El top no se movió (722) y los siete valores tampoco.** El único decimal que
cambia tiene causa medida y **también es del 18**: el `follow_end` pasó de 842 a
**931**, la ventana de la repetición se alargó y el máximo de la cadena de la
estatura se corrió de 1196,4 px (cuadro 818) a **1199,9 px (cuadro 876)**, un
**+0,29 %** que achica las siete métricas en la misma proporción — visible sólo
en la más grande. **Ninguna otra causa movió nada**, que es lo que el prompt
pedía verificar.

Y el `tol_frames` **4** del top de vid1 —la banda del 18— sigue ahí: es el único
lugar del proyecto donde la banda se ve.

## Queda abierto

- **Re-habilitar juicio es métrica por métrica**, con `mdc_validation` y un rango
  con procedencia, cada uno con su tabla. No hay bandera global, a propósito. Las
  condiciones por familia están en la auditoría §6 D-2.
- **`follow_end`, la deriva de cámara y las dos definiciones de entrenador**
  (fin del follow; top y address de manos o de palo) siguen abiertos y son
  encargos propios. El `follow_end` 1978 de la rep 1 de cortado3 sigue cayendo en
  la quietud previa al swing siguiente.
- **El exit 134 del arnés es intermitente** (0/134/0 en tres corridas). Sigue sin
  causa; es el encargo 6 de la secuencia.
- **`kinelab/events/order.py` sigue huérfano** desde ADR-018. No era archivo de
  este encargo.
- **El piso de ruido del pipeline no existe todavía**, y hasta que exista ninguna
  repetibilidad es una medición. Es el encargo 10.

## Para que pruebe Hernán

Nada de front. Tres comandos.

```bash
.venv/bin/pytest
```

**357 pasados, 0 fallados.** Ahora **imprime el conteo**: antes `pyproject.toml`
traía `addopts = "-q"` y, sumado al `-q` de la línea de comandos, daba `-qq`, que
se lo come. Es lo primero que hay que ver.

```bash
.venv/bin/python -m kinelab analyze data/sessions/hernan/2026-09-15/driver/face_on/take-01 --altura-m 1.75
```

Tiene que decir **`calidad: confiable`** y **2 repeticiones**, y donde antes
aparecía «SD None» ahora sale la razón por la que no hay repetibilidad. Los
números son los mismos de siempre: lo que cambió es que ninguno dice ya que se
puede comparar contra nada.

```bash
python3 -c "import json;d=json.load(open('data/sessions/hernan/2026-09-15/driver/face_on/take-01/analysis.json'));print(sum(1 for r in d['reps'] for m in r['metrics'].values() if m['judgment_allowed']),'juicios');[print('•',w) for w in d['warnings']]"
```

Tiene que decir **`0 juicios`** y listar los dos avisos. Eso es el encargo entero
en una línea: **0 de 21**, y los 24 valores exactamente iguales a los que la
auditoría reprodujo.

## Preguntas para el orquestador

1. **El aviso de la regla se apaga solo si algún juicio estuviera encendido.** Es
   una desviación chica del prompt, tomada para que la frase no pueda ser falsa.
   Si preferís que salga siempre, es una línea — pero entonces habría que
   reescribirla para que no afirme «ninguno».
2. **`Registry.mdc_note` es un campo nuevo del motor** (una frase que declara el
   deporte). Fue la única forma de que el aviso nombre el arnés y el modelo de
   cámara sin meter golf en `kinelab/`. Si preferís que esa frase viva en otro
   lado —`SportMetrics`, por ejemplo—, se mueve.
3. **El exit 134 del arnés resultó intermitente** (0/134/0). Cambia un poco el
   encargo 6: lo que hay que aislar es una condición de carrera al cerrar, no un
   aborto determinista.
4. **cortado3 ya vive en `data/sessions/`**, con el gate en `ok`. La auditoría
   pidió no re-correr percepción sobre esa toma después del encargo 17; queda
   escrito acá que la percepción **se corrió hoy**, antes del 17, sobre el take
   definitivo.
5. **El `follow_end` 1978 de la rep 1 sigue en el archivo publicado.** Es un
   número descriptivo hoy —2556,7 ms de follow-through— y la auditoría lo declaró
   falso. ¿Se muestra con un aviso propio hasta que el encargo 5 lo arregle, o se
   deja como está?
