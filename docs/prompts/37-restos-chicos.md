# 37 — Cinco restos chicos

Para correr: `/encargo 37` en una sesión nueva, **después del 36**, que ya
cerró y está en `main`. Ninguno en paralelo.

## Contexto

Encargo de limpieza. Cinco cosas chicas, verificadas contra el código el
20/9: ninguna mueve un valor publicado, ninguna sube una versión de schema y
ninguna toca `kinelab/metrics/` ni un umbral. Si alguna resulta **no** ser
chica, paralá, hacé las otras y decilo en el informe — es preferible a
forzarla.

## Qué existe ya

Suite hoy: `.venv/bin/pytest -q` → **exit 0, 462 pasados, 0 fallados, 1
salteado** (el salteado es el de los pesos de `models/`). Arnés: 43/0.
Front: **pnpm**.

## Encargo

1. **La lista blanca del servicio, como estaba previsto.** El encargo 35 dejó
   `_Servibles` —un dict con `get` e `in` extendidos— en
   `service/exploracion.py:289-309` sólo porque `service/app.py` no estaba en
   su lista de archivos (`ESTADO.md:216-221`). Lo natural es una función
   `media_type(nombre)` en `exploracion.py` y las dos líneas de
   `service/app.py:330` y `:332` que la usan. Los tests son todos por HTTP
   (`tests/test_service.py:415-423` y `:426-454`) y no deberían cambiar: si
   alguno cambia, es que cambiaste el comportamiento y eso no era el encargo.
2. **`hands_speed_curve_top_to_impact` sale del summary.** Está en
   `kinelab/analysis.py:268`, inyectada a mano después del bucle del
   registro: **no está en el registro** (`sports/golf/metrics.py`), no tiene
   las seis cosas que exige `AGENTS.md` y su `mdc` es `null`. Decisión de
   Hernán (20/9): se saca. Verificado: `schema.json:77` declara
   `summary.metrics` como objeto libre, así que **no se toca el schema ni
   sube ninguna versión**; los únicos consumidores son
   `tests/test_fase2.py:715` y `:717`, y `data/examples/analysis.example.json`,
   que se regenera con `tests/helpers/gen_analysis_example.py` (swing
   sintético, no hace falta correr pose). El front no la lee. Si al sacarla
   `repeatability_curves` (`kinelab/metrics/generic.py:106`) queda sin uso
   salvo su test (`tests/test_fase2.py:528`), **dejala donde está** y decilo
   en el informe: borrar código de métricas no es de este encargo.
3. **Dos comentarios que mienten.** `kinelab/explore.py:37` dice que los
   campos de primer nivel «los retira el encargo 36»: el 36 ya está integrado
   y **no** los retiró — los retira R10, que es lo que dice bien
   `web/src/lib/api.ts:156-158`. Y `ESTADO.md:321` repite que hay un bug
   abierto de `--data` en `explore()`, que **no existe**: lo que describe
   `ESTADO.md:3227-3230` es un arreglo ya hecho, y hoy la cola pasa
   `capture_paths=` del `--data` (`service/exploracion.py:462-464`). Corregí
   los dos. **No reescribas informes ni prompts viejos**: son registro
   fechado, aunque repitan la afirmación equivocada.
4. **`CAPTURE_PATHS_FILE` en `service/app.py:160`**, que todavía escribe el
   literal `"capture-paths.yaml"`. Es el mismo arreglo que el encargo 34 hizo
   en `kinelab/ingest/__main__.py:103`. Una línea, sin cambio de
   comportamiento.
5. **Código muerto en `kinelab/explore.py:265`**: `trunk_lean_deg` se calcula
   ahí con `-_vs_vertical_deg(...) + 180.0 * 0` y se **pisa** doce líneas
   abajo, en `:276`. Borrá el primero. **Comprobá que ningún valor del CSV se
   mueve**: corré la tabla por cuadro de un `pose.npz` guardado antes y
   después y compará, y decí en el informe que dieron idénticas.

Tests: los que ya hay tienen que seguir en verde sin tocarlos, salvo los dos
asserts del punto 2. Si tenés que cambiar un test para que pase, pará y
decilo: en un encargo de limpieza eso significa que algo cambió de verdad.

NO: no toques `kinelab/metrics/` (salvo lo que diga el punto 2, que es *no*
tocarlo). No toques ningún umbral ni el 717. No retires los campos de primer
nivel de `datos-eventos.json` (es R10). No regeneres `data/exploracion/` ni
la demo. No corras pose sobre material nuevo. No toques `docs/PLAN.md`: es
del orquestador y lo está editando.

## Cómo se prueba

```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/truth && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm lint && pnpm build
```

Exit code y conteo, no la palabra «passed»: motor **exit 0, 0 fallados**, con
el número exacto dicho en el informe (hoy 462; este encargo no debería
agregar ni sacar tests salvo lo del punto 2). Arnés exit 0 con 43.

## Front

**No lo toca este encargo.** Sólo que `pnpm lint` y `pnpm build` sigan en
verde. **No abras un navegador.**

## En paralelo

Ninguno. Archivos que este encargo puede tocar: `service/exploracion.py`,
`service/app.py`, `kinelab/analysis.py`, `kinelab/explore.py`,
`data/examples/analysis.example.json`, `tests/`, `ESTADO.md` y
`docs/informes/`.
