# 27 — Contención del juicio (ADR-019): ninguna métrica es juicio hasta validarla en material real

Para correr: `/encargo 27` en una sesión nueva. Leé antes, completo,
`docs/informes/2026-09-16-auditoria-primer-juicio.md` (§1 y §6 D-2, D-3), y los
informes del 24 y del 26.

> Verificado contra HEAD `f866c77` por siete agentes antes de commitearlo: los
> archivos y líneas de abajo están confirmados, y la lista de tests que la
> regla rompe salió de simular el cambio.

## Contexto

El 15/9 `cortado3-lento.mp4` pasó el gate 9 de 9 y `analyze` dio los primeros
**21 `judgment_allowed: true`** del proyecto (11 en la repetición 1, 10 en la
2). El 16/9 una auditoría los reprodujo desde HEAD y los revisó uno por uno:
**la aritmética es exacta en los 21 y ninguno resiste como juicio**. Tres
causas, cada una verificada por métodos independientes: `follow_end` cae en la
quietud previa al swing siguiente; la imagen deriva 8–25 px durante cada swing
y contamina los desplazamientos en cm por encima de su MDC; y los eventos de
manos y los del palo difieren 4–16 cuadros.

Dos agujeros de fondo, que son los que este encargo cierra:

1. **El MDC no está validado en material real.** `sports/golf/mdc.yaml` es del
   arnés nivel 0: proyección y ruido gaussiano, sin estimador de pose, con la
   cámara `iphone17pro-1080p120` sin verificar. La regla sólo pregunta si el
   MDC existe.
2. **La regla habilita juicio sin rango.** `kinelab/metrics/registry.py:87-102`
   pasa con `ref is None or ref.range_width is None`, y `CONTRATO.md:390` dice
   lo mismo. Pero `CONTEXTO.md:49-51` define juicio como **comparar contra un
   rango**. Sin rango no hay contra qué juzgar.

**Decisión del orquestador, a escribir como ADR-019 en `DECISIONES.md`.** Cita
a ADR-007 (lo sustituye en parte: «MDC medido en el arnés» ya no alcanza),
ADR-012 y ADR-016, y cierra con una «Consecuencia» como la de ADR-016. Una
métrica es juicio sólo si, además de lo que ya se exige:

- (a) **su MDC está validado en material real**: medido con el estimador real,
  sobre material real, por el camino de captura de la toma, con los eventos
  contra etiquetas humanas, la deriva medida, la escala trazable y los
  intrínsecos del teléfono calibrados con tablero (auditoría §6 D-2). Un MDC
  del arnés, de cualquier nivel y aunque los intrínsecos estén calibrados,
  **no** está validado; y
- (b) **tiene un rango de referencia con procedencia fuerte** contra el cual
  comparar.

Hoy eso da **0 de 21**. Los valores no cambian.

**Por qué la validación va en un campo propio y no en `medido_aqui`.**
`CONTEXTO.md:61-63` define la procedencia como «de dónde sale un número». Con
esa definición, el MDC del arnés sí es `medido_aqui`: lo medimos nosotros. Así
lo usan ADR-007, `CONTRATO.md:322` y `truth/kinelab_truth/calibrate.py:44`, y en
`fps_provenance` el mismo valor significa «cronómetro filmado». Darle a
`medido_aqui` un significado más fuerte sólo para el MDC haría que un valor
del mismo enum (`PROVENANCES`, `registry.py:16`) diga tres cosas distintas. La
procedencia sigue diciendo de dónde sale un número; **si está validado es otra
pregunta, con su propio campo**. Ajustá el texto del ADR si el código muestra
algo que lo contradiga, y decilo.

Leer: `kinelab/metrics/registry.py` (`PROVENANCES`, `Reference` y su
`__post_init__` en :41-45, `Metric`, `judgment_allowed`, `null_metric`, el
`REGISTRY` genérico de :149), `kinelab/metrics/core.py` (`evaluate`),
`kinelab/metrics/generic.py:70-92` (repetibilidad), `kinelab/analysis.py:154`
(`build_analysis` acepta `registry=`) y `:190-262` (los `warnings`),
`kinelab/__main__.py:27`, `sports/golf/metrics.py` (`_m`,
`Registry(version="0.2.0")` en :72, las referencias en :51),
`sports/golf/events.py:100-118`, `kinelab/contract/schema.json`,
`tests/test_fase2.py`, `tests/test_eventos_senal.py:310-320`,
`tests/helpers/gen_analysis_example.py`, `CONTRATO.md` §El sextuplo, §summary,
§subframe y §Versionado, `CONTEXTO.md` §Vocabulario e invariantes 4 y 12, y
ADR-007, ADR-009, ADR-012, ADR-016 y ADR-018.

## Encargo

1. **La regla, con dos condiciones separadas en el código.** Cada una lleva su
   comentario y su test.
   - `Metric.mdc_validation: str = "sin_validar"`, con valores
     `"sin_validar" | "material_real"`. Validalo en `__post_init__` como ya se
     valida `level`. `judgment_allowed` exige `"material_real"`. Ninguna
     métrica de golf lo declara hoy.
   - `judgment_allowed` exige además `ref is not None`, `ref.kind == "range"` y
     `ref.provenance not in ("sin_verificar", "estimacion")`. El rango válido ya
     lo garantiza `Reference.__post_init__`. Excluir `estimacion` sale del
     invariante 12: ante la duda, el hueco. Todas las referencias de golf son
     hoy `Reference("descriptive", "estimacion", …)` sin rango
     (`sports/golf/metrics.py:51`).
   - La razón legible **no** va al sextuplo: `$defs/metric` tiene
     `additionalProperties: false` y este encargo no cambia el schema. Va a los
     avisos del punto 3.
   - `registry_version` 0.2.0 → **0.3.0** en `sports/golf/metrics.py:72`, con
     el comentario de por qué, como el que tiene el 0.2.0. El `REGISTRY`
     genérico de `registry.py:149` queda en 0.1.0.
2. **Los documentos alineados.**
   - `CONTRATO.md` §El sextuplo: la fórmula nueva, con las dos condiciones y una
     frase de por qué se corrige la línea 390.
   - `CONTRATO.md` §summary (:405-418): sin piso de ruido medido, la
     repetibilidad lleva `value: null` y `null_reason` (punto 5).
   - `CONTRATO.md` §subframe: una frase de que el MDC del cruce es del arnés y
     no está validado (ADR-019).
   - `CONTRATO.md` §Versionado (:598): el 0.3.0.
   - `CONTEXTO.md`, como «Consecuencia» de ADR-019: el vocabulario de :50-51
     dice «con MDC validado en material real y rango de referencia con
     procedencia», y el invariante 4 (:82-83) dice «Sin MDC validado en material
     real (ADR-019) y sin rango de referencia con procedencia no hay juicio; si
     el MDC es mayor que el ancho del rango, tampoco».
3. **Los avisos.** En `warnings[]`, siempre que haya al menos una métrica con
   valor, dos avisos redactados para un entrenador. Uno dice que **ninguna
   métrica es juicio hasta validarla en material real** (ADR-019). El otro dice
   que **el MDC sale de un arnés sin estimador y con la cámara sin verificar**.
   Se suman a los avisos de fps de ADR-016, no los reemplazan.
4. **El MDC del sub-cuadro** (`sports/golf/events.py:100-118`). Su
   `provenance` **queda en `medido_aqui`**: es literalmente cierto, lo midió el
   arnés, y el schema de `subframe.mdc` no admite campos nuevos. Lo que cambia
   es el `source`: tiene que decir que es del arnés nivel 0 (proyección y ruido,
   sin estimador), con la cámara sin verificar, y **no validado en material
   real (ADR-019)**. Conservá la mención a `mdc.yaml`, que la fija
   `tests/test_eventos_senal.py:318`.
5. **Repetibilidad sin piso de ruido no es una medición.** `generic.py:70-92`
   devuelve siempre `noise_floor: None` con un valor al lado. Mientras no haya
   piso medido, `value: null` y `null_reason` con la razón, dentro del mismo
   objeto (`summary.metrics` es un objeto libre en el schema, así que valida).
   `n` se conserva, en `repeatability_scalar` y en `repeatability_curves`.
   `kinelab/__main__.py:27` muestra la razón en vez de «SD None».
6. **Dos arreglos chicos que salieron de la auditoría:**
   - `pyproject.toml:46` saca `addopts = "-q"`: sumado al `-q` de la línea de
     comando da `-qq`, que no imprime el conteo.
   - `ESPECIFICACION.md` 3.2 (:144) y Fase 5 (:192) nombran la ganancia: una
     nota fechada de que ADR-018 la retiró, sin borrar el texto.
7. **Corridas reales, y el cierre del 16.**
   - Ingestá `data/incoming/cortado3-lento.mp4` a **`data/sessions/`** real, no
     a un scratch: `--atleta hernan --gesto driver --vista face_on --camino
     s22ultra-slomo-fhd240-recorte-mac`. Después `kinelab.perception` y
     `kinelab analyze --altura-m 1.75`. Es la primera toma que vive en su lugar
     definitivo.
   - `datos` sobre `~/Desktop/cortado.mp4` y `data/incoming/vid1.mp4` con
     `--altura-m 1.75`. Es el punto 6 del encargo 16, que quedó sin hacer.
     Reportá los siete valores en cm con los cuadros de eventos al lado, contra
     la columna «ahora» de la tabla del informe 14 §4. Esa columna ya tiene el
     top del 15 (33 en cortado, 722 en vid1). Contra ella, lo que puede mover
     los valores es el 18: la señal de manos pesada por confianza,
     `wrist_score_min` y la banda del top. Si algo se mueve por otra causa,
     decilo.
   - En tu sección de `ESTADO.md`: que **la tabla del informe 26 §4 no es una
     medición**, con la referencia a la auditoría, y que el punto 6 del 16 cerró
     acá.

NO: no tocar `web/` ni `service/` (el 28 corre en paralelo); no cambiar ningún
valor de ninguna métrica, ni umbrales de eventos, ni `follow_still_s`,
`wrist_score_min`, `still_speed_max`, `top_band_sigmas` ni el 717; no arreglar
`follow_end` ni la deriva, que son encargos propios; no agregar valores al enum
de `fps_provenance` ni de `PROVENANCES`; no editar `sports/golf/mdc.yaml` ni
`data/examples/analysis.example.json` a mano; no borrar ninguna aserción de un
test existente; no fijar como golden los valores de cortado3 ni los
«corregidos» de la auditoría.

## Cómo se prueba

- `.venv/bin/pytest` en verde, leído por **exit code y conteo** de pasados y
  fallados. `cd truth && .venv/bin/pytest` también. El arnés tiene un exit 134
  conocido al cerrar el intérprete, después del resumen: reportalo, no lo
  arregles.
- **La regla rompe once tests existentes, todos en `tests/test_fase2.py`.** Se
  adaptan sin perder lo que prueban y sin borrar ninguna aserción:
  - `:159` (`sway_cm`) y los casos `True` de `:180-201` (`_fps_metric`, la
    tolerancia NTSC) declaran `mdc_validation="material_real"` y un
    `Reference("range", …)` con procedencia fuerte.
  - `:318-319` es la prueba de punta a punta de ADR-016, y con golf ya no queda
    juicio que apagar. Le pasa a `build_analysis(..., registry=…)` un registro
    de prueba con al menos una métrica validada y con rango, para que el test
    siga demostrando que un camino declarado apaga el juicio.
  - `:451` y `:512` pasan a 0.3.0.
  - `:526` pasa a esperar `False` con el registro de golf.
  - `data/examples/analysis.example.json` se regenera con
    `.venv/bin/python tests/helpers/gen_analysis_example.py`.
- **Tests nuevos:**
  - MDC `sin_validar` con todo lo demás en orden da `false`.
  - `material_real` sin rango da `false`.
  - Rango con procedencia `estimacion` o `sin_verificar` da `false`.
  - Las dos condiciones cumplidas dan `true`.
  - La repetibilidad sin piso da `value: null` con razón.
  - Mutación manual: quitar cualquiera de las dos condiciones pone un test en
    rojo.
- **La prueba de punta a punta:** el `analysis.json` de cortado3 en
  `data/sessions/` da **0 de 21** `judgment_allowed`. Los **21 valores** son
  **idénticos** a los de
  `docs/informes/auditoria-2026-09-16/reproduccion.md`. `warnings[]` trae los dos
  avisos nuevos, y las repetibilidades salen en `null` con su razón.

## En paralelo

El **28** toca sólo `web/`. Vos: `kinelab/metrics/`, `kinelab/analysis.py`,
`kinelab/__main__.py`, `sports/golf/metrics.py`, `sports/golf/events.py`,
`DECISIONES.md`, `CONTRATO.md`, `CONTEXTO.md`, `ESPECIFICACION.md`,
`pyproject.toml`, `tests/test_fase2.py`, tus tests nuevos,
`data/examples/analysis.example.json` (regenerado) y `ESTADO.md`. **`ESTADO.md`
lo edita también el 28:** antes de commitearlo, `git diff ESTADO.md` tiene que
mostrar sólo tu sección. Si trae líneas del 28 sin commitear, no lo commitees:
dejá el texto de tu sección en tu informe y avisalo.
