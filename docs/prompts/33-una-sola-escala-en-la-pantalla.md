# 33 — Una sola escala en la pantalla, y dicha

Para correr: `/encargo 33` en una sesión nueva. Ninguno en paralelo.
Leé antes: `docs/informes/2026-09-18-28-pantalla-sin-falsedades.md` y
`docs/informes/2026-09-18-31-follow-end-en-su-repeticion.md`.

## Contexto

Hoy la misma pantalla muestra **dos números en cm para el mismo evento**. La
tabla por cuadro convierte con el `body_height_px` **de cada cuadro**
(`kinelab/explore.py:184`, aplicado en `:209` y `:211`, que alimenta también
`hands_speed_cm_s`) y las métricas convierten con la escala de la repetición
(`MetricContext.scale_px`, `kinelab/metrics/core.py:123-147`). Y hay una
**tercera**: `px_to_cm` (`core.py:158-173`) cae a `body_height_px` del cuadro
cuando la cadena de estatura no es medible, y lo usa `generic.py:42`, o sea
todas las métricas en cm. Ninguno de los tres números dice cuál usó. Es la
misma familia de falsedad que cerró el 28.

**Decisión del orquestador (2026-09-20, reversible):** el fallback **no se
mata** — matarlo cambiaría valores publicados por un `null` y eso es una
decisión del dominio, no de proceso. Lo que se hace es **declarar la
procedencia de cada cm**, que es lo que el proyecto ya exige a cualquier
número, y hacer que la tabla por cuadro divida por la **misma escala de la
repetición** que usan las métricas, para que los dos números coincidan cuando
los dos existen. Ajustala sólo si el código la contradice, y decilo.

Leer: `kinelab/explore.py:160-215` y `:360-400`, `kinelab/metrics/core.py:110-175`,
`kinelab/metrics/generic.py:30-45`, `kinelab/analysis.py:85-145`,
`CONTRATO.md` §La escala y §Versionado, `web/src/components/TablaCuadros.tsx`,
`web/src/components/TablaEventos.tsx:38-46`, `web/src/components/Metricas.tsx:85-95`,
`web/src/app/page.tsx`, `web/src/lib/api.ts`, `web/src/lib/etiquetas.ts`.

## Qué existe ya

- Suite hoy: `.venv/bin/pytest -q` → **exit 0, 390 pasados, 0 fallados**.
  Arnés: 43/0. El front es **pnpm** (`packageManager: pnpm@11.12.0`), no npm.
- **`scale_px` no es una función de módulo**: es un método de la dataclass
  `MetricContext` (`core.py:123`) y necesita el contexto entero (keypoints,
  fps, `frame_start`/`frame_end` de la repetición, `body_height_px`, eventos,
  `athlete_height_m`). Lo que sí es importable a nivel módulo es
  `stature_chain_px` (`core.py:65`).
- **`quality.scale_px` publicado es la mediana entre repeticiones**
  (`analysis.py:89-102`, `:138`), no el divisor de ninguna fila: con dos o más
  repeticiones no sirve de escala de la tabla. La escala **por repetición** no
  viaja hoy en `analysis.json`.
- `per_frame_table` (`explore.py:163`) recibe `(pose, fps, height_m, address)`
  y **no conoce las repeticiones**; las tiene el llamador (`explore.py:377`,
  vía `analysis["reps"]`). La llaman posicional y sin reps
  `tests/test_eventos_senal.py` (dos tests) y
  `truth/tests/test_angulos.py:145` (que sólo lee columnas `*_deg`).
- El 31 ya metió `eventos_tol_frames` en `datos-eventos.json` y en la cabecera
  de `TablaEventos`: copiá ese patrón para publicar la escala.

## Encargo

1. **La escala por repetición se publica.** `reps[i].scale_px` y
   `reps[i].scale_source` en `analysis.json`, con `scale_source` diciendo
   `stature_chain_rep` o `body_height_px_frame`. Son campos **agregados**:
   `kinelab/contract/schema.json` pasa a **2.1.0** (minor, por §Versionado) y
   `CONTRATO.md` §La escala lo documenta. El `quality.scale_px` agregado no
   cambia de valor; su texto pasa a decir que es la mediana **entre
   repeticiones**, que es lo que es.
2. **La tabla por cuadro usa la escala de la repetición del cuadro.**
   `per_frame_table` gana un parámetro **opcional** (`reps=None`, al final de
   la firma, para no romper las tres llamadas posicionales de arriba). Con
   reps, cada fila divide por la escala de la repetición que la contiene; sin
   reps, se comporta como hoy y **lo declara**. Un cuadro fuera de toda
   repetición no tiene cm.
3. **Cada cm dice de dónde sale.** `escala_px`, `escala_fuente`,
   `referencia_cuadro` y `referencia_fuente` en `datos-cuadros` y en
   `datos-eventos.json`; y la procedencia por métrica donde hoy cae el fallback
   de `px_to_cm`. El front los muestra en la cabecera de `TablaCuadros` y al
   lado de las métricas. Si el motor no los mandó (trabajo viejo), no se
   inventa nada: no se muestra.
4. **Sin address, «vs address» lo dice.** `explore.py:185` cae al cuadro 0 sin
   avisar (`ref = address if address is not None else 0`). Los valores **no
   cambian**: lo que cambia es que `referencia_fuente` dice `cuadro 0 (sin
   address)` y el front lo muestra junto a las ocho columnas
   `*_vs_address_*` de `TablaEventos.tsx:38-46`.
5. **La repetición que se muestra deja de ser un supuesto, sin selector.**
   `Metricas.tsx:92` usa `reps[0]` fijo, y el motor arma `datos-eventos.json`,
   el overlay y el `address` de la tabla con `analysis["events"][0]`
   (`explore.py:366`): toda la pantalla es la repetición 1. La pantalla lo
   **dice** («repetición 1 de N; todo lo de abajo es esa»). **No agregues
   selector**: elegir otra desincroniza motor y pantalla y es un encargo
   propio; anotá en el informe qué haría falta.
6. **Tabla antes/después** de todo número que se mueva, en los clips que ya
   tienen `pose.npz`, **sin volver a correr el modelo** (invariante 1). Lo
   esperado es que **sólo** se muevan las columnas en cm de la tabla por cuadro
   y `hands_speed_cm_s`; si se mueve una métrica de `analysis.json`, pará y
   decilo antes de seguir.
7. **El resto**: el comentario de `web/src/components/TablaCuadros.tsx:4` dice
   118 columnas (son CSVs congelados previos a ADR-018); hoy son 115 con altura
   y 106 sin ella. Corregilo.

Tests: uno que falle si la tabla por cuadro y las métricas dan dos cm distintos
para el mismo evento del mismo clip teniendo los dos escala; uno que falle si
un cm sale sin `escala_fuente`; uno del camino sin reps. **Estos tests de hoy
tocan lo que vas a cambiar y hay que revisarlos, no borrarlos**:
`tests/test_escala.py::test_sin_cadena_medible_cae_a_la_altura_de_cuerpo_del_cuadro`
(el fallback sigue vivo: debería pasar, ahora con su procedencia),
`tests/test_perception.py::test_explore_mode_writes_everything_even_without_a_person`
(exige `pelvis_dx_vs_address_cm` en `columnas` en un clip sin persona ni
repetición), `tests/test_eventos_senal.py` (dos, llaman posicional) y
`truth/tests/test_angulos.py`.

NO: no matar el fallback de `px_to_cm` ni cambiar ningún valor publicado de
`analysis.json`. No `metric_version` nuevo (la convención no cambia, se
declara) — `tests/test_fase2.py:627-629` quema `"1.1.0"` y tiene que seguir en
verde. No tocar `kinelab/ingest/` (lo toca el encargo que sigue). No ajustar
umbrales ni el 717. No regenerar `data/exploracion/` ni la demo (congelados).
No correr pose. No agregar selector de repetición.

## Cómo se prueba

```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/truth && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm lint && pnpm build
```

Exit code y conteo, no la palabra «passed»: motor exit 0 con ≥ 390 pasados y 0
fallados, arnés exit 0 con 43. La tabla del punto 6 sale de los `pose.npz` ya
guardados en `data/incoming/*.kinelab/`.

## Front

**Lo prueba Hernán.** Dejalo listo con `pnpm lint` y `pnpm build` en verde, el
comando exacto para levantarlo, y una lista corta de qué mirar: el cm de la
tabla por cuadro y el de las métricas para el mismo evento, la escala dicha en
la cabecera, el «repetición 1 de N», y qué se ve en un clip sin address.
**No abras un navegador.**

## En paralelo

Ninguno. Archivos que este encargo puede tocar: `kinelab/explore.py`,
`kinelab/metrics/core.py`, `kinelab/metrics/generic.py`, `kinelab/analysis.py`,
`kinelab/contract/schema.json`, `CONTRATO.md`, `web/src/app/page.tsx`,
`web/src/components/TablaCuadros.tsx`, `web/src/components/TablaEventos.tsx`,
`web/src/components/Metricas.tsx`, `web/src/lib/api.ts`,
`web/src/lib/etiquetas.ts`, `tests/`, `ESTADO.md` y `docs/informes/`.
