# 36 — El selector de repetición

Para correr: `/encargo 36` en una sesión nueva, **después del 35**, que ya
cerró y está en `main`. Ninguno en paralelo.
Leé antes: `docs/informes/2026-09-20-35-el-motor-publica-todas-las-repeticiones.md`
y `docs/informes/2026-09-20-33-una-sola-escala-en-la-pantalla.md`.

## Contexto

El 35 hizo la mitad del motor: `datos-eventos.json` ya publica todas las
repeticiones en `repeticiones_detalle` (16 campos, `explore.py:585-599`), el
overlay rotula los eventos de todas y las fotos de la 2 en adelante existen.
Falta que la pantalla deje elegir cuál se ve, y que **toda** la pantalla
cambie con ella.

Por qué no es cosmético: el 35 midió que la repetición 2 de `cortado3-lento`
tenía sus desplazamientos contra el address de la **1** —4,84 cm contra un MDC
de 2,42— y que el pico de manos del encabezado (4,85 bh/s) es el de la **2**
en una pantalla que dice «repetición 1».

**Decisiones ya tomadas. No las reabras; ajustalas sólo si el código las
contradice, y decilo.**

- **Este encargo NO retira los campos de primer nivel** de
  `datos-eventos.json`, aunque dupliquen la repetición 1. Hernán decidió el
  20/9 que el retiro espera a R10, el encargo que regenera todo de una vez
  después de la sesión de validación: los 19 trabajos de `data/exploracion/`
  y los 3 de la demo son **anteriores al 33** (`analysis.json` 1.2.0) y no
  tienen `repeticiones_detalle`, así que hoy son lo único que los hace
  visibles.
- **Por eso el front lee con respaldo**: `repeticiones_detalle[i]` cuando
  está, y si no está, el primer nivel como una única repetición. Un trabajo
  viejo tiene que seguir viéndose exactamente como se ve hoy, sin selector.
- **El pico del encabezado pasa a ser el de la repetición elegida** (decisión
  delegada en el orquestador). **Ojo**: el `picos` de primer nivel **no es el
  de la repetición 1, es el del clip entero** (`explore.py:599` contra `:597`,
  y `ESTADO.md:85-87`), así que no se pierde: se sigue publicando y la tabla
  por repetición muestra el de cada una.
- **`escala_cuadro` deja de ser inútil.** Hoy se calcula una vez fuera del
  bucle y sólo sobrevive con una repetición (`explore.py:566`,
  `… if len(reps)==1 else None`). El dato existe por repetición:
  `MetricContext.scale_detail()` devuelve `frame` (`kinelab/metrics/core.py:158-172`)
  y `analysis.py:231-236` lo tira. Se publica como **`scale_frame`** —en
  inglés, como sus vecinos `scale_px` y `scale_source`— campo opcional nuevo
  en `reps[]`, `SCHEMA_VERSION` **2.1.0 → 2.2.0** (`kinelab/analysis.py:42`),
  minor. Es **nullable**: con el fallback de escala, `frame` es `None`
  (`core.py:170`), y por §Frontera un `null` se escribe, no se omite.

## Qué existe ya

- Suite hoy: `.venv/bin/pytest -q` → **exit 0, 457 pasados, 0 fallados, 1
  salteado** (el salteado es el de los pesos de `models/`). Arnés: 43/0.
  Front: **pnpm**.
- **No hay contexto de React ni store** (cero `createContext`), pero **no es
  cierto que todo baje por props**: `page.tsx:292-296` baja
  `transformacion.json`, `TablaCuadros.tsx:67-79` baja el CSV y
  `Visor3D.tsx:216` baja `pose3d.json`. Y `analysis` no es un `useState`
  plano: es `leidoAnalysis` `{url, valor, error}` (`page.tsx:180-192`). La
  repetición elegida es un `useState` nuevo en `page.tsx` que baja por props.
- **Estado interno que se queda pegado al cambiar de repetición**:
  `Reproductor.tsx:71` (`cuadro`, inicializado sólo al montar),
  `page.tsx:278` (`verDosCuadros`), `TablaCuadros.tsx:63-64` (`filtro`,
  `inicio`). Hace falta `key` o un reset explícito, o la pantalla miente.
- **No hay tests de front**: ni vitest, ni jest, ni playwright. Sólo
  `pnpm lint`, `pnpm build` y dos verificadores a mano. Agregar
  infraestructura de tests a `web/` cae bajo ADR-015: **no la agregues**.
- **El verificador de retirados se corre desde `$KLAB/web`**, no desde el
  worktree (`web/public/demo/` está en `.gitignore`).
- La frase «repetición N de M» ya existe en **tres** lugares y de **dos**
  fuentes: `Metricas.tsx:97-99` (de `analysis.reps`), `TablaEventos.tsx:121-126`
  y `TablaCuadros.tsx:55` (de `resumen.repeticion_mostrada`). Con el selector
  tienen que decir las tres lo mismo.
- Líneas verificadas hoy: `Metricas.tsx:70` (`analysis?.reps?.[0]`), `:98`,
  `:108`; `api.ts:97-138` (`Resumen`), `:272` (`Analysis.reps`), `:44`
  (`EscalaFuente`), `:420`, `:490`; `page.tsx:180-192`, `:258-442`,
  `:300-373`, `:305-306`, `:379-396`.

## Encargo

1. **El selector**, en la pantalla de resultado, antes que las métricas. Con
   una sola repetición no se muestra (la frase «repetición 1 de 1», sí). Con
   un trabajo viejo sin `repeticiones_detalle`, tampoco.
2. **Toda la pantalla lo sigue**: métricas (`analysis.reps[i]`, hoy `[0]`
   quemado en `Metricas.tsx:70`, `:98` y `:108` — cambia la firma del
   componente, no alcanza con pasarle datos), tabla por evento, tabla por
   cuadro (cabecera y el rango `frame_start`/`frame_end` marcado), el
   reproductor con los eventos de esa repetición, los dos cuadros del
   impacto, la barra de sub-cuadro, los avisos, el pico del encabezado y
   **las fotos por evento**: `evento-<id>` para la 1 y `evento-r<N>-<id>`
   para las demás, **en `.png` y en `.jpg`** — `page.tsx:305` cae a `.jpg`
   porque la demo exporta JPEG (`exportar_demo.py:46-48`).
3. **El respaldo para trabajos viejos**, en un solo lugar y explícito (una
   función que devuelva «las repeticiones de este trabajo», con el primer
   nivel como repetición única cuando no hay detalle). No lo repartas por los
   componentes.
4. **`scale_frame` en `reps[]`** (ver decisión): `analysis.py` deja de tirar
   `det["frame"]`, `schema.json` lo agrega en `properties` de `reps[]` —tiene
   `additionalProperties: false` en `:59`—, y `explore.py` lo copia a
   `escala_cuadro` de cada entrada del detalle en vez de calcularlo una vez
   fuera del bucle. **El bump a 2.2.0 arrastra cuatro cosas que hay que hacer
   en el mismo encargo o queda rojo**: `web/src/lib/retirados.ts:57`
   (`CONTRATO_VIGENTE = "2.1.0"`), `web/src/lib/retirados.verificar.mjs:137`
   (el borde `["2.1.0", false]`) y `:120-124`, regenerar
   `data/examples/analysis.example.json` con
   `tests/helpers/gen_analysis_example.py`, y los tres asserts de versión:
   `tests/test_fase2.py:578`, `:686`, `:857`, más
   `tests/test_una_sola_escala.py:184`.
5. **La demo estática sigue en verde**: `exportar_demo.py` y el verificador,
   corrido desde `$KLAB/web`. **No regeneres `data/exploracion/` ni la demo.**

Tests: que un trabajo con dos repeticiones ofrezca el selector y uno con una
no; que elegir la 2 cambie los cuadros de los eventos, la escala y las
diferencias vs address a los de la 2; que un trabajo **sin**
`repeticiones_detalle` siga leyéndose como una repetición única; que
`scale_frame` salga por repetición y valide con 2.2.0, y que un
`analysis.json` sin él también valide.

NO: **no retires los campos de primer nivel de `datos-eventos.json`** (es
R10, ver decisión). No agregues infraestructura de tests a `web/` (ADR-015).
No toques `kinelab/metrics/` ni ningún umbral ni el 717. No recalcules eventos
ni métricas. No regeneres `data/exploracion/` ni la demo. No corras pose sobre
material nuevo. No renombres `quality.camera_motion_px`: es del encargo de
deriva y es un major. No toques `service/app.py` ni rehagas la lista blanca
`_Servibles` que dejó el 35: quedó anotada aparte.

## Cómo se prueba

```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/truth && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm lint && pnpm build
cd /Users/heralc/Desktop/HDDev/kinelab/web && node --experimental-strip-types src/lib/retirados.verificar.mjs
```

Exit code y conteo, no la palabra «passed»: motor **exit 0, 0 fallados**, con
el número exacto de pasados dicho en el informe —hoy son 457 y este encargo
agrega tests, así que decí cuántos entraron; si alguno se retira, cuál y por
qué—. Arnés exit 0 con 43. El verificador de retirados, exit 0 y 0 fallas.

## Front

**Lo prueba la sesión** — excepción que pidió Hernán el 20/9 a su regla de
siempre. Levantá el front (`.venv/bin/python -m service` y
`cd web && pnpm dev`), subí `cortado3-lento`, elegí la repetición 2 y
verificá con capturas: que los cuadros de los eventos cambien, que la escala
pase de ≈783,9 a ≈831,3 px, que `pelvis_dx_vs_address_cm` en el top de la 2
dé ≈−7,05 cm y no −2,21, que las fotos por evento sean las `evento-r2-*`, y
que las tres frases de repetición digan «2 de N». Y abrí **un trabajo viejo**
de la lista para confirmar que se ve igual que hoy. Las capturas van al
informe.

## En paralelo

Ninguno. Archivos que este encargo puede tocar: todo `web/src/`,
`kinelab/explore.py`, `kinelab/analysis.py`, `kinelab/metrics/core.py` (sólo
si hace falta para exponer `frame`), `kinelab/contract/schema.json`,
`kinelab/tools/exportar_demo.py`, `data/examples/analysis.example.json`,
`tests/`, `CONTRATO.md`, `ESTADO.md` y `docs/informes/`.
