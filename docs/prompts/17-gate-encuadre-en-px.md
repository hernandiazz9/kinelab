# 17 — El chequeo de encuadre en píxeles, no en fracción del cuadro

Para correr: `/encargo 17` en una sesión nueva, **después de que cierre el
27**. Ese encargo edita `kinelab/` y corre el motor sobre material real, igual
que vos, y deja la toma de `cortado3-lento` en `data/sessions/`, que vos no
tenés que tocar. **No corre en paralelo con ninguna otra sesión** que edite
`kinelab/` o `sports/`, ni con una que corra el motor sobre material real
(skill `/encargo` §5). Leé antes el informe del 13 (§3), el del 26 (§5, la
serie de encuadre) y `docs/informes/2026-09-16-auditoria-primer-juicio.md` §4.

> Reescrito el 16/9 con las correcciones de la auditoría y verificado contra
> HEAD `f866c77` por siete agentes. La versión anterior nombraba `gate.py` como
> el lugar del chequeo, y el chequeo no vive ahí.

## Contexto

El chequeo de encuadre no tiene umbral desde la Fase 1: se reporta con
`passed: null` y razón «umbral sin medir». El arnés (13) mostró que con el
ruido relativo de la spec el MDC es invariante al tamaño (álgebra, no
casualidad) y que sólo un ruido absoluto en px da un umbral. Con σ = 4,9 px (el
nominal), **`head_lift_top_cm` cruza su tolerancia de 5 cm a 717 px** de
cuerpo; le siguen `head_sway_top_cm` a 608 y `thorax_sway_top_cm` a 552. La
fracción del cuadro engaña: en 4K un 28 % del alto son 1104 px, más que el 80 %
de un 1080p. La auditoría midió el jitter de la pose en HEAD en 3,7 px en y,
con la deriva de la cabeza incluida. Está por debajo del σ nominal, así que
**el 717 está del lado conservador**.

**Decisión del orquestador:** el chequeo mide **píxeles**,
`body_height_px_min = 717`, procedencia `estimacion` (arnés nivel 0, σ
nominal, sin estimador). Se revisa cuando haya σ por keypoint medido en
material real. La regla del 80–90 % de `CAPTURA.md` queda como objetivo de
campo.

**Dónde vive, verificado en HEAD:**

- El umbral es `PerceptionGates.body_height_frac_min` en `kinelab/sport.py:31`,
  con default `None`. Su validación en `:35-37` exige el rango (0, 1].
- El deporte lo instancia en `sports/golf/config.py:26` con
  `perception=PerceptionGates()`, sin valor. Las líneas 21-25 son un comentario
  que queda desactualizado.
- El chequeo es `framing_checks` en `kinelab/perception/framing.py:202`.
- `kinelab/perception/run.py:106-107` calcula el reporte y los chequeos, y
  `:126-130` los escribe en `capture.json` con `with_checks`.
  `kinelab/ingest/gate.py:423-433` recalcula el veredicto. **Lo evalúa la
  percepción, no la ingesta**, y el orden ya está resuelto.
- El modo exploración pasa por el mismo lugar: `kinelab/explore.py:332-345`
  junta las razones de los chequeos que fallan en `warnings[]` y en
  `gate_diria`, sin bloquear el análisis. Con 717, cualquier `datos` de un clip
  más chico va a sumar la frase nueva a sus avisos. Es esperado, y va en el
  informe.

Leer: `kinelab/sport.py`, `sports/golf/config.py`,
`kinelab/perception/framing.py` (`framing_report`, `framing_checks`),
`kinelab/perception/run.py`, `kinelab/ingest/gate.py:59-69` (`Check`, que no
admite campos extra) y `:423-433` (sólo lectura), `kinelab/explore.py:332-345`
(sólo lectura), `sports/golf/mdc.yaml` §framing (sólo lectura),
`tests/test_perception.py`, `CAPTURA.md` §Encuadre y la tabla del gate,
`CONTRATO.md` §capture.json, `docs/filmacion-s22.md`.

## Encargo

1. **El umbral en píxeles.**
   - `PerceptionGates.body_height_px_min: float | None = None` en
     `kinelab/sport.py`. La validación de `__post_init__` pasa a exigir `> 0`.
   - `sports/golf/config.py:26` pasa a
     `perception=PerceptionGates(body_height_px_min=717)`. El comentario de
     21-25 se reescribe con la procedencia: `estimacion`, arnés nivel 0,
     `head_lift_top_cm`, 16/9/2026.
   - El nombre `body_height_frac_min` desaparece del repo. Buscalo con `rg` en
     `kinelab/`, `sports/`, `tests/`, `truth/`, `service/`, `web/` y `docs/`.
2. **El chequeo** en `framing.py` pasa a llamarse `body_height_px`.
   - `value` es la mediana de `body_height_px` redondeada y `expected` es 717.
   - La fracción del cuadro va **dentro de `reason`**, también cuando pasa (por
     ejemplo, «691 px de cuerpo, 36 % del alto»). `Check` no admite campos
     extra y `gate.py` no se toca.
   - Frase para el entrenador cuando falla: «el jugador mide N px de alto en el
     cuadro y hacen falta 717: acercá el trípode».
   - Si el id del chequeo aparece en el contrato, `CONTRATO.md` §capture.json
     al día.
3. **`CAPTURA.md`.**
   - La fila del chequeo en la tabla del gate.
   - Una frase en §Encuadre con el número, su procedencia y la cuenta en los dos
     modos del S22: 717 px son el **37,3 % de 1920** en Slow motion FHD y el
     **30,9 % de 2320** en Video FHD.
   - En `CAPTURA.md:121` las fracciones de vid1 y vid2 están invertidas. Lo
     medido es **vid1 28,7 %, vid2 28,2 %, vid3 29,5 %** (informe 11:188).
     Corregilo.
4. **`docs/filmacion-s22.md`, sección nueva «La sesión de validación».** Sale de
   la auditoría del 16/9 y cubre las hipótesis sobre la deriva de cámara:
   - Trípode con peso, sin tocarlo durante la toma. Super Steady y toda
     estabilización de video apagadas.
   - Un objeto chico y contrastado fijo en el suelo, cerca de los pies y dentro
     del cuadro.
   - Al armar cada vista, 25 s de grabación de la escena vacía, con el trípode
     ya puesto.
   - Al empezar cada toma, 2 s de pie derecho, de frente, en el lugar del
     address.
   - El cuerpo en más del 37,3 % del alto en Slow motion FHD: un paso más cerca
     que `cortado3`, que dio 36 %.
   - 25 s por toma, en todas. El cronómetro andando dentro del cuadro va
     **sólo en la primera toma de cada vista y en la toma de la escena
     vacía**, no en cada toma (decisión del orquestador del 18/9: el
     cronómetro calibra el camino del teléfono, una vez; hoy n = 1 y desde un
     recorte de la Mac, y con esas dos tomas más una de `DCIM/Camera` queda
     n = 3 y el camino del teléfono crudo). Reconciliá con esto el §2 de la
     guía, que hoy dice «en cada toma», y dejá escrito en una línea que quien
     filme después con el mismo teléfono, modo y cable **no necesita
     cronómetro**: elige el camino en la pantalla y listo.
   - 10–20 swings `face_on` y 10–20 `down_the_line`, con pelota. En la mitad,
     sostener la pose final 1–2 s.
   - El palo declarado bien. La altura medida con cinta.
   - Los originales de `DCIM/Camera` por cable; de una toma, también el recorte
     de la Mac. Una toma mandada por WhatsApp **como video**, que tiene que salir
     rechazada.
5. **Tests** en `tests/test_perception.py`:
   - Una toma sintética con cuerpo de 600 px rechaza con la frase; una de 900 px
     pasa; sin sujeto falla con razón legible.
   - `test_framing_report_and_checks` (`:124-128`) cambia por el renombre.
   - **Ojo:** `test_run_perception_ok_and_timestamps` (`:250-253`) usa `GOLF`
     con un estimador falso de ~80 px de cuerpo y exige `verdict == "ok"`. Con
     717 se pone en rojo. **Se arregla en el test, no en el umbral**: pasale a
     `run_perception` un `dataclasses.replace(GOLF,
     perception=PerceptionGates())`, que queda sin umbral, o un estimador con un
     cuerpo de 717 px o más.

NO: no tocar `kinelab/ingest/gate.py` ni `sports/golf/mdc.yaml`, cuyo §framing
lo escribe el arnés y nunca se edita a mano; no re-correr `kinelab.perception`
sobre la toma de `cortado3-lento` en `data/sessions/`, porque quedaría en reject
y `analyze` la rechazaría; no cambiar el 717. Si el código muestra que está mal
medido, decilo en el informe y dejalo.

## Cómo se prueba

- `.venv/bin/pytest` en verde, por exit code y conteo.
- **Corrida real** sobre un `--data` de scratch, desde la raíz del repo:
  ```bash
  cp data/capture-paths.yaml $S/
  .venv/bin/python -m kinelab.ingest data/incoming/cortado3-lento.mp4 --atleta hernan --gesto driver --vista face_on --camino s22ultra-slomo-fhd240-recorte-mac --data $S
  .venv/bin/python -m kinelab.perception <take_dir que imprime la ingesta>
  ```
  `kinelab/ingest/__main__.py:103` lee `capture-paths.yaml` de `--data`: por eso
  la copia. La percepción tarda unos 100 s con CoreML (2977 cuadros).
  **Esperado:** exit code distinto de cero y `body_height_px` fallando con
  **691 px contra 717**. Ese rechazo es el resultado.
- **La tabla de los otros clips** sale de los reportes que ya existen, sin
  correr nada (fracción × alto): `20260907_170638` 973 px, `cortado` 869, `vid1`
  1104, `vid2` 1083, `vid3` 1132, `Cortado-lenta` 414, `cortado3-lento` 691.
  Decí cuáles pasarían.

## En paralelo

**Ninguno.** Vos: `kinelab/sport.py`, `sports/golf/config.py`,
`kinelab/perception/framing.py`, `tests/test_perception.py`, `CAPTURA.md`,
`docs/filmacion-s22.md`, `ESTADO.md`, y `CONTRATO.md` sólo si el id del chequeo
aparece ahí.
