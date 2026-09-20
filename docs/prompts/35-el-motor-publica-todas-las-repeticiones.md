# 35 — El motor publica todas las repeticiones, no sólo la primera

Para correr: `/encargo 35` en una sesión nueva, **después del 34**, que ya
cerró y está en `main` (`59f6b0b`). Ninguno en paralelo.
Leé antes: `docs/informes/2026-09-20-33-una-sola-escala-en-la-pantalla.md`.

## Contexto

Toda la pantalla de exploración muestra **la repetición 1** y no hay forma de
ver otra. No es una limitación del front: el motor arma los datos con una sola
repetición —`kinelab/explore.py:428`, `rep = analysis["events"][0]`, y
`:474`, `rep1 = analysis["reps"][0]`— y de ahí salen los cuadros de los
eventos, las tolerancias, el subcuadro, la escala, las diferencias vs address,
las fotos por evento y los rótulos del overlay. El front sólo puede elegir lo
que el motor le mandó, y hoy le manda una. En `cortado3-lento` la repetición 2
tiene una escala **6 % distinta** (831,3 px contra 783,9) y es invisible.

Hernán decidió (20/9) que elegir una repetición cambie **toda** la pantalla.
Este encargo es la **mitad del motor**: publicar todo por repetición sin
tocar el front. El selector es el 36 y se escribe después de este informe.

**Corte, y por qué** (decisión del orquestador, mecánica): los campos de
primer nivel de `datos-eventos.json` **se quedan como están**, con los valores
de la repetición 1. Así el front sigue funcionando igual el día que esto
entre, y el 36 migra componente por componente contra datos que ya existen. Lo
nuevo va al lado, no en su lugar.

Leer: `kinelab/explore.py` (`explore()`:387, el bloque 424-500, `render`:~340,
`per_frame_table`:443), `kinelab/analysis.py` (`reps[]` se arma en :201, se
llena en :228 y :236), `service/exploracion.py:257` (la lista blanca
`ARCHIVOS`), `kinelab/tools/exportar_demo.py`, `CONTRATO.md` §Versionado y lo
que diga de `datos-eventos.json`.

## Qué existe ya

- Suite hoy: `.venv/bin/pytest -q` → **exit 0, 448 pasados, 0 fallados, 1
  salteado** (el salteado es el de los pesos de `models/`, que git ignora).
  Arnés: 43/0. Front: **pnpm**.
- `analysis.json` (2.1.0) **ya tiene todas las repeticiones**: `reps[]` con
  `rep`, `frame_start`, `frame_end`, `t_start`, `t_end`, `peak_speed_bh_s`,
  `scale_px`, `scale_source` y `metrics`. Y `events[]` tiene una entrada por
  repetición. **No hace falta recalcular nada del análisis**: lo que falta es
  que `explore.py` deje de quedarse con la primera.
- Claves de primer nivel de `datos-eventos.json` hoy: `aviso`, `video`,
  `camino`, `camino_calibrado`, `fps_provenance`, `fps_aviso`, `fps_archivo`,
  `cuadros`, `altura_m`, `gate_diria`, `eventos_frame`, `eventos_t_s`,
  `eventos_tol_frames`, `eventos_subcuadro`, `escala_px`, `escala_fuente`,
  `escala_cuadro`, `referencia_cuadro`, `referencia_fuente`,
  `repeticion_mostrada`, `repeticiones`, `duraciones`, `picos`,
  `en_cada_evento`, `diferencias_vs_address`, `calidad`, `columnas`.
- El CSV por cuadro **ya cubre todos los cuadros** y ya divide por la escala de
  la repetición de cada fila (encargo 33). Lo único atado a la rep 1 ahí es el
  `address` de referencia (`explore.py:444`).

## Encargo

1. **`repeticiones_detalle` en `datos-eventos.json`**: una entrada por
   repetición, en orden, cada una con lo que hoy es de la rep 1 —`rep`,
   `frame_start`, `frame_end`, `eventos_frame`, `eventos_t_s`,
   `eventos_tol_frames`, `eventos_subcuadro`, `escala_px`, `escala_fuente`,
   `escala_cuadro`, `referencia_cuadro`, `referencia_fuente`, `duraciones`,
   `picos`, `en_cada_evento`, `diferencias_vs_address`. Los nombres son los
   que ya existen arriba: no inventes otros ni traduzcas nada.
2. **Los campos de primer nivel no se mueven.** Siguen siendo los de la
   repetición 1 y siguen diciendo `repeticion_mostrada: 1`. Dejá un comentario
   de una línea que diga que son transitorios y que el 36 los retira.
3. **Las fotos por evento, de todas las repeticiones.** Hoy sólo se escriben
   las de la rep 1 (`evento-<id>.png`, `explore.py:376-379`). La repetición 1
   **conserva sus nombres actuales** —no rompas lo que ya anda— y las demás se
   escriben como `evento-r<N>-<id>.png`. Acordate de la lista blanca
   `ARCHIVOS` de `service/exploracion.py:257`: si no las agregás ahí, el
   servicio las devuelve 404.
4. **El overlay rotula los eventos de todas las repeticiones**, no sólo los de
   la primera (`render`, el `frame_events` de `explore.py:359` y el rótulo de
   `:367`). Que el rótulo diga de qué repetición es cada evento. **Un solo
   `overlay.mp4`**: no se renderiza un video por repetición.
5. **La demo estática sigue andando.** `kinelab/tools/exportar_demo.py` y
   `web/src/lib/retirados.verificar.mjs` comparan las claves **exactamente**
   contra `web/public/demo/`: si un campo nuevo los pone en rojo, arreglalo
   ahí. **No regeneres `data/exploracion/` ni la demo** (congelados por el
   plan): lo que tiene que seguir en verde es el verificador, no los datos.

Tests: que un trabajo con **dos o más** repeticiones escriba
`repeticiones_detalle` con una entrada por cada una y con los cuadros de sus
propios eventos (no los de la rep 1); que los campos de primer nivel sigan
valiendo exactamente lo mismo que antes del encargo; que las fotos de la rep 1
conserven su nombre y las de la 2 salgan como `evento-r2-<id>.png`; que el
servicio sirva las dos. **Revisá, no borres**, estos que fijan el formato o
asumen la rep 1: `tests/test_una_sola_escala.py:254` y `:267`
(`repeticion_mostrada == 1`), `tests/test_fase2.py:893` y `:1003`,
`tests/test_service.py:544` (compara el dict `eventos_frame` entero),
`tests/test_exportar_demo.py:107` (fixture escrito a mano),
`tests/test_camera_drift.py:343`.

NO: **no toques nada de `web/`** salvo `retirados.verificar.mjs` si se pone en
rojo — el selector es el 36 y otra sesión va a editar esos componentes. No
toques `kinelab/contract/schema.json` ni `analysis.json`: este encargo no
cambia el contrato de `analysis.json`, sólo la salida de exploración. No
recalcules eventos ni métricas: ya están todas en `analysis["events"]` y
`analysis["reps"]`. No toques `kinelab/metrics/` ni ningún umbral. No
regeneres `data/exploracion/` ni la demo. No corras pose sobre material nuevo.

## Cómo se prueba

```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/truth && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm lint && pnpm build
```

Exit code y conteo, no la palabra «passed»: motor exit 0 con ≥ 448 pasados y 0
fallados, arnés exit 0 con 43. Además, sobre material real: re-corré
exploración **a un directorio temporal** (no pises los trabajos que ya están)
desde el `pose.npz` de un trabajo que tenga **más de una repetición** —
`cortado3-lento` tiene al menos dos— y mostrá en el informe: cuántas entradas
salieron en `repeticiones_detalle`, los cuadros de los eventos de cada una, y
la escala de cada una (la 2 de `cortado3-lento` tiene que dar ≈831,3 px contra
≈783,9 de la 1). Listá los archivos `evento-*` que quedaron.

## Front

**No lo toca este encargo.** Lo único que tiene que quedar en verde es
`pnpm lint`, `pnpm build` y el verificador de retirados. **No abras un
navegador.**

## En paralelo

Ninguno. Archivos que este encargo puede tocar: `kinelab/explore.py`,
`service/exploracion.py`, `kinelab/tools/exportar_demo.py`,
`web/src/lib/retirados.verificar.mjs`, `CONTRATO.md`, `tests/`, `ESTADO.md` y
`docs/informes/`.
