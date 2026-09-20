# 34 — De dónde sale la calibración del fps

Para correr: `/encargo 34` en una sesión nueva, **después del 33**, que ya
cerró y está en `main`. Ninguno en paralelo.
Leé antes: `docs/informes/2026-09-15-26-lo-que-enseno-el-cronometro.md` y
`docs/informes/2026-09-18-17-gate-encuadre-en-px.md`.

## Contexto

El fps del archivo miente y el proyecto lo sabe: la tasa real es
**configuración del camino de captura**, calibrada una vez con un cronómetro
filmado, nunca inferida del contenedor (`AGENTS.md` §Cosas que muerden,
ADR-016). Pero hoy **nada dice de qué clip salió esa calibración**:
`capture-paths.yaml` declara un `fps_real` y hay que creerle. El único camino
calibrado del repo (`s22ultra-slomo-fhd240-recorte-mac`,
`data/capture-paths.yaml:112`) ya se usó con **dos clips distintos**, y nada
en el trabajo lo dice. La sesión de validación de la Fase 0 va a calibrar tres
cronómetros más: que entren sin trazabilidad es lo que después hace imposible
saber qué número salió de dónde.

**Dos decisiones del orquestador (2026-09-20, reversibles).** Ajustalas sólo
si el código las contradice, y decilo.

- **La procedencia se registra, no se exige.** Un camino sin
  `calibration_clip_sha256` sigue siendo válido y sigue analizando; lo que
  cambia es que se dice. Prohibirlo dejaría sin usar el único camino calibrado
  que existe (n = 1) y no hay material para reemplazarlo.
- **Por eso el campo nuevo va *fuera* de `_CALIBRATION_FIELDS`**, como opcional
  dentro de la calibración. Verificado el 20/9: `_calibration_is_all_or_nothing`
  exige los seis campos cuando `calibrated: true`, así que meterlo en la lista
  tumbaría el camino real del repo, el fixture `capture_paths_yaml`
  (`tests/conftest.py:137`) y con él centenares de tests de `test_gate`,
  `test_perception`, `test_fase2`, `test_una_sola_escala` y `test_service`.

Leer: `kinelab/ingest/capture_paths.py` (`CAPTURE_PATHS_FILE`:40,
`_CALIBRATION_FIELDS`:34, `_calibration_is_all_or_nothing`:66,
`default_capture_paths_file`:129-138, `resolve_path_id`:146),
`kinelab/ingest/gate.py` (`CAPTURE_SCHEMA_VERSION`:44, `CaptureJson`:84-100,
`build_capture_json`:370-422, `CHECK_ORDER`), `kinelab/ingest/session.py:43`
(`sha256_file`), `kinelab/tools/fps_truth.py:430-453`,
`kinelab/analysis.py:283`, `service/exploracion.py` (`ficha_de_captura`),
`kinelab/tools/exportar_demo.py:441` (`ficha_de_captura_min`), `CONTRATO.md`
§Versionado y la sección de `capture.json`/`capture-paths`.

## Qué existe ya

- Suite hoy, con el 33 integrado: `.venv/bin/pytest -q` → **exit 0, 398
  pasados, 0 fallados, 0 salteados**. Arnés: 43/0. Front: **pnpm**, no npm.
- Versiones de hoy: `capture-paths` **1.1.0** (`data/capture-paths.yaml:20`,
  `CONTRATO.md:53` y `:692`), `capture.json` **1.2.0**
  (`CAPTURE_SCHEMA_VERSION`). `kinelab/contract/schema.json` valida **sólo
  `analysis.json`** (2.1.0 desde el 33): los otros dos esquemas viven en el
  código, en `capture_paths.py` y en `gate.py`. No te confundas de lugar.
- **`same_file` sale casi gratis**: `capture.json` ya guarda `sha256_original`
  y `build_capture_json` **ya lo recibe como parámetro**. Comparar es una
  línea, sin hash extra.
- **Nadie compara versiones de schema**: `schema_version` es un `str` libre en
  `CapturePaths` y en `CaptureJson`. Lo viejo carga solo con un campo nuevo con
  default. Lo que sí rechaza es `extra="forbid"` (código viejo leyendo un
  archivo nuevo).
- El 33 tocó `kinelab/explore.py`, `kinelab/analysis.py`, `web/src/lib/api.ts`
  y `CONTRATO.md`: **partí de `main`, no de un recuerdo**.

## Encargo

1. **`calibration_clip_sha256` en `capture-paths`, schema 1.2.0** (minor).
   Campo opcional, **fuera** de `_CALIBRATION_FIELDS` (ver decisión). Sube
   `schema_version` en `data/capture-paths.yaml` y en
   `data/examples/capture-paths.example.yaml`. Un archivo 1.1.0 sigue
   cargando.
2. **`fps_calibration.same_file` en `capture`, schema 1.3.0** (minor).
   Booleano: `true` si `sha256_original` de esta toma coincide con el
   `calibration_clip_sha256` del camino; `false` si no; **`null`** cuando el
   camino no declara sha. Se escribe en `build_capture_json`. Es un dato de
   procedencia, **no** un chequeo que rechace.
3. **El aviso, por el canal que el entrenador ve de verdad.** En exploración el
   gate **no corre** (`explore.py` escribe un `Check` con `passed=None`) y la
   frase que llega a la pantalla sale de `analysis.warnings`
   (`kinelab/analysis.py:283`). Usá ese canal. Con `same_file: false`, decí de
   qué clip salió el fps que se está usando; con `null`, que el camino no lo
   declara. Si además agregás un `Check` al gate, acordate de `CHECK_ORDER`
   (`tests/test_gate.py:97` y `:251` lo comparan entero).
4. **`fps_truth` emite el sha.** Al terminar,
   `python -m kinelab.tools.fps_truth` imprime el `sha256` del clip que midió,
   en el formato exacto que hay que pegar en `capture-paths.yaml`. Reusá
   `sha256_file` (`kinelab/ingest/session.py:43`), no escribas otro hasher.
   Hoy hay que calcularlo aparte, y eso es lo que hace que nadie lo declare.
5. **Declarar el sha del único camino calibrado, si está.** El clip que lo
   calibró es `Cortado-lenta` según las `notes` del propio camino; su sha
   completo está en `data/incoming/Cortado-lenta.kinelab/capture.json`, que
   **no va a git**. Si ese archivo está en la máquina, leé el sha de ahí y
   declaralo (no es inventarlo: es leerlo). Si no está, dejá el campo sin
   declarar y decilo en el informe.
6. **El front muestra la procedencia** donde ya muestra el fps. El fps con su
   procedencia aparece hoy en **cuatro** lugares —
   `web/src/components/FichaArchivo.tsx:46-47` y `:61`,
   `web/src/app/page.tsx:327`, `web/src/components/Metricas.tsx:116`,
   `web/src/components/ListaTrabajos.tsx:53` — más el mapa `PROCEDENCIA` de
   `web/src/lib/etiquetas.ts`. Elegí **uno** (la ficha del archivo es el
   natural) y dejá los otros como están; decí en el informe cuál elegiste. Si
   el motor no lo mandó (trabajo viejo), no se inventa: no se muestra.
7. **Las dos fichas tienen que seguir siendo la misma.**
   `service/exploracion.py` (`ficha_de_captura`) y
   `kinelab/tools/exportar_demo.py:441` (`ficha_de_captura_min`) son copias
   paralelas y hoy **nada testea que coincidan**. Si agregás el campo en una,
   agregalo en la otra, y dejá un test que falle si divergen en los campos de
   calibración.
8. **`CAPTURE_PATHS_FILE` en vez del literal.** `kinelab/ingest/__main__.py:103`
   escribe `"capture-paths.yaml"` a mano; usá la constante. **Ojo: el bug que
   suponía el plan no existe** — verificado el 20/9, `__main__.py:103` y
   `service/exploracion.py:277` resuelven **la misma** ruta para el mismo
   `--data`, y `default_capture_paths_file()` **no toma argumentos** (caería al
   `data/` del cwd o del repo, ignorando `--data`: sería una regresión). No la
   uses acá. Decilo en el informe: el plan tenía mal la premisa.

Tests: que un `capture-paths.yaml` 1.1.0 sin sha siga cargando; que uno 1.2.0
con sha valide; que un camino calibrado **sin** sha siga siendo válido; que
`same_file` no salga `true` con shas distintos ni con sha ausente; el de las
dos fichas del punto 7. **Revisá, no borres**, estos que queman versiones:
`tests/test_gate.py::test_hevc120_on_calibrated_path_is_ok_end_to_end`
(línea 100, `"1.2.0"`) y
`tests/test_capture_paths.py::test_repo_capture_paths_yaml_is_valid`
(línea 160, `"1.1.0"`).

**Lo que se espera que pase el día uno, y está bien:** en cuanto declares el
sha, `cortado3-lento` y varios trabajos de exploración quedan en
`same_file: false`, porque los filmó el mismo camino pero no son el clip que lo
calibró. El aviso tiene que aparecer, y el informe tiene que decir en cuántos
trabajos apareció.

NO: no tocar `kinelab/contract/schema.json` ni nada del contrato de
`analysis.json`. No convertir la procedencia en un chequeo que rechace tomas.
No meter el campo nuevo en `_CALIBRATION_FIELDS`. No usar
`default_capture_paths_file()` en `__main__.py`. No tocar `kinelab/metrics/`
ni ningún umbral ni el 717. No regenerar `data/exploracion/` ni la demo
(congelados). No correr pose. No arreglar el bug de `--data` de `explore()`
que anota `ESTADO.md:2889`: es otro encargo; si lo ves, va al informe.

## Cómo se prueba

```bash
cd /Users/heralc/Desktop/HDDev/kinelab && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/truth && .venv/bin/pytest -q
cd /Users/heralc/Desktop/HDDev/kinelab/web && pnpm lint && pnpm build
```

Exit code y conteo, no la palabra «passed»: motor exit 0 con ≥ 398 pasados y 0
fallados, arnés exit 0 con 43. Además: re-ingestá por CLI un clip real de
`data/incoming/` **a un directorio temporal** (no pises los trabajos que ya
están) y mostrá el bloque `fps_calibration` del `capture.json` que sale, con
`same_file` puesto.

## Front

**Lo prueba Hernán.** Dejalo listo con `pnpm lint` y `pnpm build` en verde, el
comando exacto para levantarlo, y una lista corta de qué mirar: dónde aparece
la procedencia del fps, qué dice cuando la toma **no** es la que calibró el
camino, qué dice cuando el camino no declara sha, y qué se ve en un trabajo
viejo. **No abras un navegador.**

## En paralelo

Ninguno. Archivos que este encargo puede tocar:
`kinelab/ingest/capture_paths.py`, `kinelab/ingest/gate.py`,
`kinelab/ingest/__main__.py`, `kinelab/tools/fps_truth.py`,
`kinelab/tools/exportar_demo.py`, `kinelab/analysis.py` (sólo el warning del
punto 3), `service/exploracion.py`, `data/capture-paths.yaml`,
`data/examples/capture-paths.example.yaml`, `CONTRATO.md`, `CAPTURA.md`,
`web/src/lib/api.ts`, `web/src/lib/etiquetas.ts`,
`web/src/components/FichaArchivo.tsx`, `tests/`, `ESTADO.md` y
`docs/informes/`.
