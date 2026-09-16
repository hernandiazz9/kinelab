# 28 — La pantalla deja de decir cosas falsas

Para correr: `/encargo 28` en una sesión nueva. Leé antes
`docs/informes/2026-09-16-auditoria-primer-juicio.md` §1 (el último párrafo) y
§3 (el encargo 2), y el informe del 18.

> Verificado contra HEAD `f866c77` por siete agentes antes de commitearlo: los
> archivos, líneas, datos de la demo y comandos de abajo están confirmados.

## Contexto

La auditoría del 16/9 verificó que ningún `judgment_allowed: true` llegó a la
pantalla. Pero hay cosas **falsas que sí se ven**, en la demo pública
incluida. Los tres trabajos de `web/public/demo/` (vid1 y los dos ejemplos del
mocap) tienen `analysis.json` **1.2.0**, anteriores al contrato 2.0.0, y lo
mismo pasa con todo `data/exploracion/` (1.0.0 y 1.2.0).

- **`web/src/components/Metricas.tsx:42`** escribe «±1 cuadro:» fijo. El motor
  escribe la tolerancia real en `uncertainty.method`
  (`kinelab/metrics/core.py:241`, «±N cuadro(s) en cada evento ancla…»). En un
  vid1 re-analizado con HEAD (`data/incoming/vid1.kinelab/analysis.json`, 2.0.0)
  el top tiene `tol_frames` 4 y el método dice ±4, pero la pantalla seguiría
  diciendo ±1. En la demo el dato dice ±1 y el rótulo va a seguir diciéndolo,
  porque es lo que dice el dato.
- **`Metricas.tsx:54`** muestra «se puede comparar» cuando `judgment_allowed` es
  `true`. Ya depende del dato, pero la frase promete una comparación que la
  pantalla no hace.
- **Las columnas que ADR-018 retiró se siguen viendo en tres lugares.** La
  tabla de picos (`TablaEventos.tsx:142-147`, con `PICOS[k] ?? k`), el
  desplegable «Todas las variables en cada evento» de la misma tabla (que
  recorre `resumen.columnas`) y `TablaCuadros.tsx` (todas las columnas del CSV).
  En la demo de vid1 el pico de `hip_line_rate_deg_s` sale como **3.662**; en
  los dos del mocap, 4.202 y 3.244. Es la «rotación aparente» que el arnés midió
  como artefacto: 80 veces el valor real.
- **El ± del sub-cuadro se lee como el error del instante.** Aparece en
  `web/src/app/page.tsx:321` (`uncertainty_s`) y en `textoSubcuadro` de
  `web/src/lib/etiquetas.ts:107-113` (`uncertainty_frames`), que se usa en
  `page.tsx:317` y `:354` y en la cabecera de `TablaEventos.tsx`. Es la
  precisión **interna** del cruce: no incluye el sesgo contra el contacto con la
  pelota.

Leer: `web/src/components/Metricas.tsx`, `Avisos.tsx`, `TablaEventos.tsx`,
`TablaCuadros.tsx`, `web/src/app/page.tsx`, `web/src/lib/api.ts`,
`web/src/lib/etiquetas.ts`, `web/src/lib/pose3d.verificar.mjs` (el patrón de
verificación sin framework de tests), `kinelab/explore.py:343-379` (sólo
lectura: de dónde salen `aviso`, `fps_aviso` y `gate_diria`),
`kinelab/tools/publicar.py` (sólo lectura: `armar_salida` y el despliegue),
`DECISIONES.md` ADR-018 (las claves retiradas, por nombre, en :482 y :506-508),
y los tres `analysis.json` y `datos-eventos.json` de `web/public/demo/`.

## Encargo

1. **La banda dice de dónde sale.** En `Metricas.tsx`, el rótulo de la
   incertidumbre es `uncertainty.method` tal como lo escribe el motor. Si no
   viene, se muestra el rango sin rótulo: no se inventa uno.
2. **El juicio sin frases.** En `Metricas.tsx:54`: con `judgment_allowed: false`,
   «descriptiva»; con `true`, «juicio habilitado (judgment_allowed)». La cadena
   «se puede comparar» desaparece.
3. **Los avisos, una sola vez y tal cual.** Hoy `Avisos.tsx` **no** lee
   `analysis.json`: muestra `resumen.aviso`, `resumen.fps_aviso` y
   `resumen.gate_diria` de `datos-eventos.json`. Los tres son copias de entradas
   de `analysis.warnings` (`explore.py:345` arma
   `[AVISO, *gate_notes, *warnings]`; `:378-379` sacan los otros dos de ahí).
   - Cuando el trabajo tiene `analysis.json`, el bloque de avisos de arriba
     muestra `analysis.warnings` **completo, en orden, tal cual**. Reemplaza a
     `aviso`, `fps_aviso` y `gate_diria`; no se suma a ellos.
   - `fps_note`, que viene de `capture.json` y no está en `warnings`, queda como
     está.
   - Sin `analysis.json`, el comportamiento de hoy.
   - `analysis.json` hoy lo baja sólo `Metricas.tsx`, que va abajo: bajalo a
     nivel de `page.tsx`.
   - Verificá sobre los tres trabajos de la demo que **ninguna frase sale dos
     veces**. El 27 agrega dos avisos nuevos y la pantalla no tiene que conocer
     su texto.
4. **Lo retirado no se muestra como medición.**
   - Una lista **en un solo lugar** de `web/src/lib/`, con los nombres de
     ADR-018: `hip_line_rate_deg_s`, `shoulder_line_rate_deg_s` y
     `arm_left_rate_deg_s`. Sumá `gain` y `sequence_order`, que hoy no se
     muestran, para que no aparezcan si alguien los agrega.
   - Se aplica en los tres lugares de arriba: los picos, «Todas las variables en
     cada evento» y `TablaCuadros`.
   - **No** se oculta lo desconocido en general: el principio del encargo 01 es
     que todo lo que el motor mide se muestra.
   - Si un trabajo trae campos retirados, una línea arriba dice: «este trabajo
     se calculó con un contrato anterior y trae campos que ya no son una
     medición; no se muestran».
5. **Trabajos viejos.** Si `analysis.json` tiene `schema_version` menor a 2.0.0,
   una línea arriba del resultado dice eso y que se corrige re-analizando. Hoy
   sale en los tres trabajos de la demo. Para probar el caso ≥ 2.0.0 sin aviso,
   usá `data/examples/analysis.example.json`.
6. **El sub-cuadro con su nombre.** En `page.tsx:321` y en `textoSubcuadro`
   (`etiquetas.ts:107-113`), el ± se rotula como **precisión interna del
   cruce**. Una línea explica que ese ± no incluye el sesgo contra el contacto
   con la pelota, que no está medido en general. **Sin números**: el único que
   existe salió de un informe, no del motor.
7. **La demo se corrige sin regenerar datos.** El arreglo es sólo de código.
   Dejá verificado todo lo que no sea `vercel`, y escribí en el informe este
   comando para Hernán, desde la raíz del repo:
   ```bash
   cd web && NEXT_PUBLIC_KINELAB_MODO=demo pnpm build && cd .. && .venv/bin/python -c 'from kinelab.tools.publicar import armar_salida, raiz_repo; print(armar_salida(raiz_repo()))' && cd web && (test -f .vercel/project.json || npx --yes vercel link --yes --project kinelab --scope hernandiazz9s-projects) && npx --yes vercel deploy --prebuilt --prod --yes
   ```
   - **No uses `python -m kinelab.tools.publicar <id>`**: re-exporta el trabajo a
     `web/public/demo/`, que este encargo no regenera.
   - Confirmá que `armar_salida` y `raiz_repo` existen con esos nombres. Si no,
     corregí el comando y decilo.
   - `data/publicados.json` marca los tres trabajos con despliegue `null`, pero
     el sitio vivo existe: lo desplegó el orquestador a mano el 15/9. Anotalo.
   - **No despliegues.**

NO: no tocar `kinelab/`, `sports/`, `service/`, `truth/` ni ningún
`analysis.json`; no regenerar `data/exploracion/` ni `web/public/demo/`; no
componer ni mostrar ningún número que no venga de los datos; no agregar
dependencias ni framework de tests (ADR-015); no abrir el navegador; no
desplegar.

## Cómo se prueba

- `cd web && pnpm lint`, el build local y el build de demo, los tres limpios.
- **Verificador sin framework**, como `pose3d.verificar.mjs`: un
  `web/src/lib/retirados.verificar.mjs` que importe la lista y la función de
  filtro de un `.ts` sin alias `@/`. Tiene que comprobar, sobre los
  `datos-eventos.json` y los encabezados de `datos-por-cuadro.csv` de los tres
  trabajos de `web/public/demo/`, que salen **exactamente** las columnas
  retiradas y nada más. Se corre con
  `cd web && node --experimental-strip-types src/lib/retirados.verificar.mjs`, y
  la salida va al informe.
- **Grep sobre el build, antes y después.** Las cadenas de los componentes
  quedan en los chunks de JS y no en el HTML, y el compilador escribe «±» como
  `\xb1`. Sobre `web/out/_next/static/chunks/`:
  - **antes** del cambio, `grep -rl '1 cuadro: '` y `grep -rl 'se puede
    comparar'` tienen que encontrar algo; si no encuentran nada, la prueba no
    sirve y hay que buscar otra;
  - **después**, no tienen que encontrar nada.
  - No se grepea `web/out/demo/`: sus `analysis.json` traen «±1 cuadro en cada
    evento ancla…» en `uncertainty.method`, que es dato del motor y es lo que se
    tiene que mostrar.
- **Para Hernán**, qué mirar en la demo después de desplegarla con el comando:
  - en los tres trabajos, las dos líneas de arriba (contrato anterior y campos
    retirados);
  - en vid1, la tabla de picos y el desplegable de todas las variables, sin las
    tres `*_rate_deg_s`;
  - el rótulo de la banda de `tempo_ratio`, que ahora es la frase del motor;
  - los avisos sin repetirse;
  - el ± del impacto rotulado como precisión interna.

## En paralelo

El **27** toca `kinelab/`, `sports/`, los documentos base, `pyproject.toml`,
`tests/` y `data/examples/`. Vos: sólo `web/`, tu informe y tu sección de
`ESTADO.md`. **`ESTADO.md` lo edita también el 27:** antes de commitearlo,
`git diff ESTADO.md` tiene que mostrar sólo tu sección. Si trae líneas del 27
sin commitear, no lo commitees: dejá el texto de tu sección en tu informe y
avisalo.
