# fps-truth-primer-delta — 2026-09-14

**Encargo:** que `fps_truth` deje de declarar `VFR` por el delta de PTS del
arranque de la cámara, reporte el ratio y el fps de reproducción sin ese
primer delta, y lo diga en una nota legible. Sin tocar el gate, `explore.py`
ni `CAPTURA.md`.

## Hecho

- `Counted` lleva tres campos nuevos junto a los brutos, que no cambian:
  `delta_first_s`, `vfr_ratio_excl_first`, `fps_playback_excl_first`. Y tres
  propiedades derivadas: `first_delta_is_the_only_outlier`,
  `vfr_ratio_effective`, `fps_playback_effective`. Las tres viajan también en
  el JSON de `to_dict()`, así que el endpoint `PUT /api/fps-truth` las
  devuelve sin tocar `service/`.
- **Criterio:** el corregido se usa **sólo si el primer delta es el único
  fuera de lugar** (ratio bruto > 1,10 y ratio sin el primero ≤ 1,10). En un
  clip realmente VFR, el efectivo es el bruto: excluir el primer delta no
  perdona nada.
- **Método elegido: span sin el primer delta**, `(n−2) / (pts_último −
  pts_segundo)`, no la mediana de deltas. Razón: el span promedia el error de
  cuantización del time base sobre los 263 deltas del clip, mientras que la
  mediana lo hereda de un solo delta (con time base 1/90000 eso es ~3·10⁻⁴
  relativo contra ~10⁻⁵). Además el estimador es el mismo `(n−1)/span` que ya
  se usaba, con un cuadro menos.
- El veredicto, el `stretch_factor` y la nota de contraste con `r_frame_rate`
  se calculan ahora con el fps efectivo. Los campos brutos quedan intactos y
  se siguen imprimiendo.
- Nota legible, tal cual sale: *"el primer delta es 0.2015 s (arranque de la
  cámara); sin él, ratio 1.00 y reproducción 29.998 fps (con él: ratio 6.04,
  29.436 fps). El resto de los deltas es uniforme: no es tasa variable."*
  Cuando excluirlo no alcanza, la nota lo dice y el veredicto sigue `VFR`.
- Fixture sintético nuevo en `tests/conftest.py`: `first_delta30_h264`, 120
  cuadros a 30 fps con el primer delta de 0,2 s exactos (`setpts` sobre
  `real30_h264`; conserva los cuadros, no usa `-r`).

Commits: ver abajo.

## Probado

`.venv/bin/pytest -q`: **180 tests en verde** (173 antes, 7 nuevos), ~40 s.
Ninguno existente cambió.

Corrida real, `.venv/bin/python -m kinelab.tools.fps_truth <clip>`:

| clip | cuadros | primer delta | ratio bruto | ratio sin el 1º | fps antes | fps después |
|---|---|---|---|---|---|---|
| `~/Desktop/20260907_170638.mp4` (original S22) | 265 | 0,20148 s | 6,044 | 1,000 | 29,436 | 29,998 |
| `~/Desktop/cortado.mp4` | 76 | 0,03333 s | 1,000 | 1,000 | 29,999 | 29,999 |

El original pasa de `VFR` a `SIN_DURACION_REAL` (que es lo correcto: no hay
cronómetro todavía). El fps de reproducción corrige **1,91 %**. `cortado.mp4`
no cambia en nada: su primer delta ya era normal, porque el recorte empieza
en el cuadro 103.

Los 29,998 y no 30,000 exactos son la cuantización del time base del
contenedor Samsung, no un residuo del primer delta: `cortado.mp4`, que es una
copia bit a bit del mismo material, da 29,999 por lo mismo. En el clip
sintético, donde el time base es limpio, da 30,000 ± 0,01.

Los 7 tests nuevos, en `tests/test_fps_truth.py`:

1. el clip con el primer delta largo da ratio bruto 6,00 y fps bruto 28,79, y
   sin el primero 1,00 y **30,00 exactos**;
2. su veredicto ya no es `vfr` y la nota está, con el valor del delta y el fps;
3. con `--duracion-real 4` da `cfr_a_tasa_de_captura` y **stretch 1,00** (con
   el fps bruto daría 1,042: un clip normal parecería estirado un 4 %);
4. el JSON conserva bruto y corregido, los dos;
5. **el clip realmente VFR de los tests (120 fps y después 60) sigue dando
   `VFR`**, con ratio sin el primero de 2,0, y sin la nota del arranque;
6. un clip CFR de punta a punta no cambia en nada ni gana notas;
7. la salida de texto muestra las dos líneas, la bruta y la corregida.

## Queda abierto

- **El gate no se tocó** (así lo pedía el encargo) y sigue leyendo
  `c.vfr_ratio` y `c.fps_playback` **brutos**. Medido sobre el original del
  S22, si se ingestara hoy: `vfr_ratio_le_1_10` lo **rechaza** con 6,044;
  con el efectivo (1,000) pasaría. Y `fps_matches_path` contra un camino
  declarado de 30,000 fps da 1,88 % de desvío con el bruto contra 0,01 % con
  el efectivo: pasa por poco, dentro de la tolerancia del 2 %, o sea que un
  clip un poco más corto o con un arranque un poco más largo lo rompe.
- **`explore.py` NO toma el número corregido solo.** Usa `c.fps_playback` en
  `prepare_take()` (`kinelab/explore.py:59` y `:61`, cuatro usos entre
  `fps_real`, `fps_playback` y `duration_s`). Cambiarlo es reemplazar
  `c.fps_playback` por `c.fps_playback_effective` en esas dos líneas. **No se
  hizo**: el encargo 02 está tocando ese archivo. Mientras tanto, los `t_s` y
  las duraciones de `datos-eventos.json` sobre el original de 9 s siguen
  1,9 % largos. Sobre `cortado.mp4` (el clip con el que se mira todo hoy) no
  cambia nada.
- No hay desviación de `CONTRATO.md`: `capture.json` no cambió de forma ni de
  significado.

## Para que pruebe Hernán

Nada de front. Si querés verlo con tus propios ojos:

```bash
.venv/bin/python -m kinelab.tools.fps_truth ~/Desktop/20260907_170638.mp4
```

Tiene que decir `SIN_DURACION_REAL` (antes decía `VFR`), con una línea
`sin el 1er delta (0.20148 s): reproducción 29.998 fps · ratio 1.000  ← el
que se usa`.

## Preguntas para el orquestador

1. **¿El gate usa el bruto o el efectivo?** Es la decisión de `CAPTURA.md`
   que el encargo dejó explícitamente afuera. Con los números de arriba, la
   propuesta es: `vfr_ratio_le_1_10` y `fps_matches_path` pasan a usar
   `vfr_ratio_effective` y `fps_playback_effective`, y `capture.json` guarda
   los dos (el bruto en `vfr_ratio`, el corregido en un campo nuevo, que es
   minor de schema). Motivo: con el bruto, **cualquier** clip de esta cámara
   se rechaza por un delta que no es tasa variable, y la calibración con
   cronómetro de `capture-paths.yaml` arrancaría con un `fps_playback`
   1,9 % equivocado, que después se propaga a todos los clips del camino.
   Es un cambio a `CAPTURA.md` (la tabla del gate) más `gate.py`: entra como
   encargo propio.
2. **¿Quién actualiza `explore.py`?** Es una línea, pero el archivo está
   ocupado por el encargo 02. Puede ir pegado al 02 cuando cierre, o como
   parte del encargo del gate.
3. El delta de arranque se midió en **un** teléfono. Cuando Hernán filme el
   cronómetro (el pedido que sigue abierto), conviene anotar cuánto mide el
   primer delta en cada modo: si en 240 fps el arranque es de varios cuadros,
   el criterio "el primero y sólo el primero" puede quedar corto.
