"""Modo exploración: un video → toda la data del cuerpo, dibujada y en tablas.

Sin gate y sin juicio: sirve para MIRAR lo que el modelo ve y todo lo que se
puede derivar de eso, a cualquier fps. Cada archivo lleva la advertencia. El
producto sigue siendo el visor sobre datos (ADR-014); esto es la lupa.

    python -m kinelab datos VIDEO.mp4 --altura-m 1.75 [--vista face_on] [--camino ID] [--out DIR] [--cpu]

El camino de captura (`--camino`, por defecto `desconocido-video`) no habilita
nada acá: deja escrito con qué se dice que se filmó y que la tasa de cuadros es
un supuesto, no una medición (ADR-016). Va al `capture.json`, al `header` del
`analysis.json`, a cada métrica, a `datos-eventos.json` y quemado en el overlay.

También se puede arrancar de un `pose.npz` YA calculado, sin video y sin
estimador (`explore(..., pose_npz=…)`): es lo que usa el ejemplo de mocap de
`kinelab_truth.mocap`. De ahí para abajo el camino es el mismo — eventos,
ángulos, CSV, JSON, overlay —, con dos diferencias: la toma no tiene
`original.<ext>` y el overlay se dibuja sobre fondo liso, y el aviso de dónde
sale el eje del tiempo lo pone quien llama (`nota_fuente`), porque no hay
archivo que reproduzca ni cronómetro que filmar.

Deja en DIR (por defecto <video>.kinelab/):
    overlay.mp4          el video con los palitos, ángulos y los eventos de TODAS las
                         repeticiones rotulados con la suya (`R2 IMPACT`). Uno solo, no uno por repetición
    evento-<id>.png      una foto por evento de la repetición 1, con el esqueleto y los números
    evento-r<N>-<id>.png lo mismo para las repeticiones 2, 3, …
    datos-por-cuadro.csv una fila por cuadro: 26 puntos (px, score), ángulos, alturas, desplazamientos, velocidades
    datos-eventos.json   todo eso en cada evento, más diferencias respecto del address, duraciones,
                         la tolerancia en cuadros de cada evento (`eventos_tol_frames`)
                         y el instante sub-cuadro del impacto (`eventos_subcuadro`)
    analysis.json, pose.npz, capture.json   lo mismo que produce el motor

`datos-eventos.json` publica **todas** las repeticiones en `repeticiones_detalle`:
una entrada por repetición con sus eventos, sus tolerancias, su sub-cuadro, su
escala, sus duraciones, sus picos y sus diferencias respecto de SU address. Los
campos de primer nivel siguen siendo los de la repetición 1 (`repeticion_mostrada`)
y son **transitorios**: el encargo 36 los retira cuando la pantalla sepa elegir.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from kinelab.analysis import build_analysis, swing_signals
from kinelab.events.signal import butterworth_lowpass, cutoff_for_fps, fill_nan_linear
from kinelab.ingest.capture_paths import GENERIC_VIDEO_ID, CapturePaths, resolve_path_id
from kinelab.ingest.gate import CaptureJson, Check, Gate, declared_reason, fps_calibration_for, slomo_declared_reason
from kinelab.ingest.session import sha256_file
from kinelab.perception.estimator import EstimatorConfig
from kinelab.perception.gaps import interpolate_gaps
from kinelab.perception.keypoints import HALPE26_LIMBS, HALPE26_NAMES, H, LEFT_RIGHT_PAIRS
from kinelab.perception.plausibility import angle_deg
from kinelab.perception.posestore import POSE_FILE, finite_or_none, load_pose
from kinelab.perception.run import run_perception
from kinelab.perception.video import ffmpeg_bin, iter_frames
from kinelab.sport import SportConfig
from kinelab.tools.fps_truth import analyze as fps_analyze, first_delta_note
from kinelab.tools.interpolar import ascii_para_quemar

AVISO = "EXPLORACIÓN: sin gate, sin MDC, tasa de cuadros del archivo sin calibrar. Números descriptivos para mirar, no para juzgar."
EVENT_ORDER = ("address", "top", "impact", "follow_end")
LEFT = {H.LEFT_EYE, H.LEFT_EAR, H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST, H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE, H.LEFT_BIG_TOE, H.LEFT_SMALL_TOE, H.LEFT_HEEL}
RIGHT = {r for _, r in LEFT_RIGHT_PAIRS}


def prepare_take(video: Path, out_dir: Path, *, view: str, camino: str = GENERIC_VIDEO_ID, capture_paths: CapturePaths | None = None, athlete: str = "exploracion") -> Path:
    """Arma una toma sin pasar por el gate: `capture.json` con el camino declarado,
    la tasa que corresponda y el aviso.

    El camino sale de `data/capture-paths.yaml` igual que en la ingesta (ADR-016):
    acá no habilita nada, pero deja escrito bajo qué supuesto se midió el tiempo.
    En exploración la procedencia es SIEMPRE `sin_verificar`, aunque el camino
    esté calibrado: el gate no corrió, así que nadie verificó que este archivo
    vino por ese camino. Un `slomo` sin calibrar no se puede explorar: sin
    cronómetro el factor de estiramiento es desconocido."""
    path = resolve_path_id(camino, capture_paths)
    if not path.calibrated and path.mode == "slomo":
        raise ValueError(slomo_declared_reason(path))
    out_dir.mkdir(parents=True, exist_ok=True)
    original = out_dir / f"original{video.suffix.lower()}"
    if not original.exists() or sha256_file(original) != sha256_file(video):
        shutil.copy2(video, original)
    t = fps_analyze(original)
    c, d = t.counted, t.declared
    # La tasa EFECTIVA, no la bruta: un solo delta de arranque no es tasa
    # variable y contamina `(n-1)/span` (medido en el S22: 29,436 en vez de
    # 29,998, todos los tiempos 1,9 % largos). Los brutos quedan al lado.
    fps_playback = c.fps_playback_effective
    if path.calibrated:
        # Los números del cronómetro son lo mejor que hay para ese camino:
        # descartarlos daría tiempos ×8 mal en un Slo-Mo. La procedencia, no.
        fps, stretch = float(path.fps_real), float(path.stretch_factor)
        fuente = f"capture-paths.yaml:{path.id}"
    else:
        fps, stretch = fps_playback, 1.0
        fuente = f"declarado:{path.id}"
    # Un solo hash del original: va al `capture.json` y decide `fps_calibration`.
    sha = sha256_file(original)
    cj = CaptureJson(
        athlete=athlete, gesture="driver", view=view, capture_path_id=path.id,
        capture_path_calibrated=path.calibrated, fps_provenance="sin_verificar",
        fps_real=round(fps, 3), fps_playback=round(fps_playback, 3), fps_playback_raw=round(c.fps_playback, 3), stretch_factor=stretch,
        fps_source=f"{fuente} · {AVISO}", codec=d.codec, width=d.display_size[0], height=d.display_size[1], rotation_deg=d.rotation_deg,
        frames_decoded=c.frames_decoded, duration_s=round(c.frames_decoded / fps, 3), duration_playback_s=round(c.playback_span_s, 3),
        vfr_ratio=round(c.vfr_ratio_effective, 3), vfr_ratio_raw=round(c.vfr_ratio, 3), first_delta_s=round(c.delta_first_s, 6),
        fps_note=first_delta_note(c), recorded_at=d.creation_time, sha256_original=sha, original_name=video.name,
        fps_calibration=fps_calibration_for(path, sha),
        gate=Gate(verdict="ok", checks=[Check(id="exploracion", passed=None, value=path.id, reason=f"{AVISO} Camino: {declared_reason(path) if not path.calibrated else fuente}")], reasons=[]),
    )
    (out_dir / "capture.json").write_text(cj.model_dump_json(indent=2), encoding="utf-8")
    return out_dir


def prepare_take_from_pose(pose_npz: Path, out_dir: Path, *, view: str, note: str, camino: str = GENERIC_VIDEO_ID, capture_paths: CapturePaths | None = None, athlete: str = "exploracion") -> Path:
    """Arma una toma desde un `pose.npz` ya calculado: no hay video, no se corre
    el estimador y no hay tasa de cuadros que medir de un archivo.

    El `fps_real` sale de la `provenance` del propio `.npz`, que es quien sabe a
    qué tasa se generaron esos puntos. La procedencia sigue siendo
    `sin_verificar` (ADR-016: sólo el cronómetro filmado da `medido_aqui`), y
    `note` es la frase que explica de dónde sale el eje del tiempo en este caso
    —la escribe quien llama, porque el motor no sabe qué produjo la pose—. Va al
    `fps_source`, al registro del chequeo y a `warnings[0]`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = resolve_path_id(camino, capture_paths)
    target = out_dir / POSE_FILE
    if pose_npz.resolve() != target.resolve():
        shutil.copy2(pose_npz, target)
    pose = load_pose(out_dir)
    prov = pose.provenance
    fps = float(prov.get("fps_real") or 0.0)
    if fps <= 0:
        raise ValueError(f"{pose_npz}: la provenance del pose.npz no dice `fps_real`; sin eje de tiempo no hay nada que calcular.")
    w, h = prov.get("frame_size") or [0, 0]
    T = int(pose.keypoints.shape[0])
    cj = CaptureJson(
        athlete=athlete, gesture="driver", view=view, capture_path_id=path.id,
        capture_path_calibrated=path.calibrated, fps_provenance="sin_verificar",
        fps_real=fps, fps_playback=fps, fps_playback_raw=fps, stretch_factor=1.0,
        fps_source=f"pose.npz:{prov.get('source') or 'desconocido'} · {note}",
        codec="ninguno", width=int(w), height=int(h), rotation_deg=int(prov.get("rotation_deg") or 0),
        frames_decoded=T, duration_s=round(T / fps, 3), duration_playback_s=round(T / fps, 3),
        vfr_ratio=1.0, vfr_ratio_raw=1.0, first_delta_s=round(1.0 / fps, 6), fps_note=prov.get("fps_note"),
        recorded_at=prov.get("captured_on"), sha256_original=str(prov.get("source_sha256") or ""), original_name=str(prov.get("source_name") or pose_npz.name),
        # Acá no hay video: el sha es el que la `provenance` del `.npz` haya
        # guardado del archivo de origen, o "" si no guardó ninguno. Con "" la
        # comparación da `False`, que es lo correcto: lo que no se puede
        # afirmar no se afirma.
        fps_calibration=fps_calibration_for(path, str(prov.get("source_sha256") or "")),
        gate=Gate(verdict="ok", checks=[Check(id="exploracion", passed=None, value=path.id, reason=f"{AVISO} {note}")], reasons=[]),
    )
    (out_dir / "capture.json").write_text(cj.model_dump_json(indent=2), encoding="utf-8")
    return out_dir


def _ang(k, a, b, c):
    return angle_deg(k[:, a], k[:, b], k[:, c])


def _line_deg(k, i, j):
    """Ángulo de la línea i→j respecto de la horizontal de la imagen, en grados (y hacia abajo: positivo = j más abajo que i)."""
    d = k[:, j] - k[:, i]
    return np.degrees(np.arctan2(d[:, 1], d[:, 0]))


def _vs_vertical_deg(k, i, j):
    """Ángulo del vector i→j respecto de la vertical hacia abajo, con signo (positivo = hacia la derecha de la imagen)."""
    d = k[:, j] - k[:, i]
    return np.degrees(np.arctan2(d[:, 0], d[:, 1]))


def _scale_per_frame(bh: np.ndarray, reps: list[dict] | None) -> np.ndarray:
    """El divisor en píxeles de cada cuadro: `(T,)`, `NaN` donde no hay ninguno.

    Sin `reps` es `body_height_px` del cuadro, que es la convención anterior. Con
    `reps`, es la escala de la repetición que contiene al cuadro — la misma que
    dividió a sus métricas en cm— y `NaN` afuera de todas. Ver `per_frame_table`
    y `CONTRATO.md` §La escala."""
    if reps is None:
        return np.asarray(bh, dtype=float)
    out = np.full(len(bh), np.nan)
    for r in reps:
        lo = max(0, int(r.get("frame_start", 0)))
        hi = min(len(bh) - 1, int(r.get("frame_end", len(bh) - 1)))
        if hi < lo:
            continue
        v = r.get("scale_px")
        # `stature_chain_rep` con su número: un solo divisor para toda la
        # repetición. Cualquier otro caso —la caída a `body_height_px` del
        # cuadro, o un trabajo sin escala publicada— usa la altura de cuerpo
        # cuadro a cuadro, que es lo que hizo `px_to_cm`.
        if r.get("scale_source") == "stature_chain_rep" and isinstance(v, (int, float)) and np.isfinite(v) and v > 0:
            out[lo : hi + 1] = float(v)
        else:
            out[lo : hi + 1] = np.asarray(bh, dtype=float)[lo : hi + 1]
    return out


def per_frame_table(pose, fps: float, height_m: float | None, address: int | None, *, wrist_score_min: float = 0.0, reps: list[dict] | None = None) -> tuple[list[str], list[dict]]:
    """Una fila por cuadro. `wrist_score_min` es el umbral del DEPORTE por debajo del
    cual una muñeca no entra al centro de manos: lo pasa `explore()` desde
    `sport.events.params`, igual que `build_analysis`.

    Antes no se pasaba, y el CSV, el overlay y los eventos salían de dos señales de
    manos distintas: los eventos, de la pesada con umbral (encargo 18); el CSV y el
    dibujo, de la pesada a peso igual. En los cuadros en que una muñeca cae bajo el
    umbral —justo donde el modelo la pierde, que es el top— las dos difieren, y el
    overlay mostraba un centro de manos que no era el que había elegido el evento.
    Default 0,0 = sin umbral, la firma anterior (la usa el arnés, que no tiene
    deporte).

    **`reps` es la escala.** Son las repeticiones de `analysis.json`, cada una con
    su `scale_px` y su `scale_source` (CONTRATO.md §La escala). Con ellas, cada
    fila divide por la escala de la repetición que la contiene, que es la misma que
    usaron las métricas: hasta el encargo 33 esta tabla convertía con el
    `body_height_px` **de cada cuadro** y las métricas con la escala de la
    repetición, así que la misma pantalla mostraba dos números en cm distintos para
    el mismo evento y ninguno decía cuál había usado.

    - repetición con `scale_source: stature_chain_rep` → todas sus filas dividen por
      ese único número;
    - repetición con `scale_source: body_height_px_frame` → la cadena no se pudo
      medir y las métricas cayeron a la altura de cuerpo del cuadro: la tabla hace
      lo mismo, cuadro a cuadro;
    - **cuadro fuera de toda repetición → no hay cm**, porque no hay ninguna escala
      que sea la suya. Antes había un número, y era el de una escala que no usaba
      nadie más.
    - `reps=None` → la conversión de antes (`body_height_px` por cuadro, en todos
      los cuadros). Es la firma anterior, y la columna `escala_px` lo declara fila
      por fila en lugar de dejarlo a la imaginación.
    """
    k = interpolate_gaps(pose.keypoints, 5).astype(float)
    sig = swing_signals(pose, fps, wrist_score_min=wrist_score_min)
    bh = sig.body_height
    T = k.shape[0]
    mid_hip = (k[:, H.LEFT_HIP] + k[:, H.RIGHT_HIP]) / 2
    mid_sh = (k[:, H.LEFT_SHOULDER] + k[:, H.RIGHT_SHOULDER]) / 2
    ankle_y = np.nanmean(np.stack([k[:, H.LEFT_ANKLE, 1], k[:, H.RIGHT_ANKLE, 1]]), axis=0)
    hands = sig.hands_raw
    escala = _scale_per_frame(bh, reps)
    with np.errstate(divide="ignore", invalid="ignore"):
        cm = (height_m * 100.0 / escala) if height_m else None  # cm por píxel, por cuadro
    ref = address if address is not None else 0
    cols: dict[str, np.ndarray] = {
        "frame": np.arange(T), "t_s": pose.timestamps_s, "plausibility_flags": pose.plausibility.astype(int), "body_height_px": bh,
        # El divisor de las columnas en cm de ESTA fila, en píxeles. Está en la
        # tabla y no sólo en la cabecera porque con dos repeticiones son dos
        # números distintos, y porque un cm sin su divisor no se puede auditar
        # (cementerio 6 y 8 de HERENCIA.md). Vacío = esta fila no tiene cm.
        "escala_px": escala,
        "elbow_left_deg": _ang(k, H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST), "elbow_right_deg": _ang(k, H.RIGHT_SHOULDER, H.RIGHT_ELBOW, H.RIGHT_WRIST),
        "knee_left_deg": _ang(k, H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE), "knee_right_deg": _ang(k, H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE),
        "hip_left_deg": _ang(k, H.LEFT_SHOULDER, H.LEFT_HIP, H.LEFT_KNEE), "hip_right_deg": _ang(k, H.RIGHT_SHOULDER, H.RIGHT_HIP, H.RIGHT_KNEE),
        "shoulder_left_deg": _ang(k, H.LEFT_ELBOW, H.LEFT_SHOULDER, H.LEFT_HIP), "shoulder_right_deg": _ang(k, H.RIGHT_ELBOW, H.RIGHT_SHOULDER, H.RIGHT_HIP),
        "trunk_lean_deg": -_vs_vertical_deg(np.stack([mid_hip, mid_sh], axis=1), 0, 1) + 180.0 * 0,  # tronco: cadera→hombro respecto de la vertical
        "shoulder_line_deg": _line_deg(k, H.RIGHT_SHOULDER, H.LEFT_SHOULDER), "hip_line_deg": _line_deg(k, H.RIGHT_HIP, H.LEFT_HIP),
        "arm_left_vs_vertical_deg": _vs_vertical_deg(k, H.LEFT_SHOULDER, H.LEFT_WRIST), "arm_right_vs_vertical_deg": _vs_vertical_deg(k, H.RIGHT_SHOULDER, H.RIGHT_WRIST),
        "hands_x_vs_hip_bh": (hands[:, 0] - mid_hip[:, 0]) / bh, "hands_height_pct": (ankle_y - hands[:, 1]) / bh * 100.0,
        "hands_speed_bh_s": sig.speed,
    }
    # Las tres columnas de velocidad angular de una línea (hombros, caderas, brazo)
    # NO están más: el arnés midió que son un artefacto del largo proyectado del
    # segmento —11110 °/s contra 139,6 verdaderos en la línea de caderas desde
    # `down_the_line`— y el front las mostraba como «rotación aparente». ADR-018.
    # el tronco: ángulo cadera→hombro respecto de la vertical hacia ARRIBA, positivo = hombros hacia la derecha de la imagen
    d = mid_sh - mid_hip
    cols["trunk_lean_deg"] = np.degrees(np.arctan2(d[:, 0], -d[:, 1]))
    for name, pt in (("pelvis", mid_hip), ("thorax", mid_sh), ("head", k[:, H.HEAD]), ("hands", hands)):
        dx, dy = pt[:, 0] - pt[ref, 0], -(pt[:, 1] - pt[ref, 1])  # dy positivo = sube
        cols[f"{name}_dx_vs_address_pct"], cols[f"{name}_dy_vs_address_pct"] = dx / bh * 100.0, dy / bh * 100.0
        if cm is not None:
            cols[f"{name}_dx_vs_address_cm"], cols[f"{name}_dy_vs_address_cm"] = dx * cm, dy * cm
    if cm is not None:
        cols["hands_speed_cm_s"] = sig.speed * bh * cm
    for j, name in enumerate(HALPE26_NAMES):
        cols[f"{name}_x"], cols[f"{name}_y"], cols[f"{name}_score"] = pose.keypoints[:, j, 0], pose.keypoints[:, j, 1], pose.scores[:, j]
    names = list(cols)
    rows = [{n: (None if (isinstance(v := cols[n][i], float) and not np.isfinite(v)) else (float(v) if isinstance(v, (float, np.floating)) else int(v))) for n in names} for i in range(T)]
    return names, rows


#: Los sufijos de las columnas que se miden CONTRA UN CUADRO DE REFERENCIA. La
#: tabla por cuadro las calcula todas contra un solo cuadro —el address de la
#: repetición 1—, así que para otra repetición hay que restarle el valor de SU
#: address: la referencia se cancela y queda el desplazamiento verdadero de esa
#: repetición. Ver `_rebasar`.
_VS_ADDRESS = ("_vs_address_pct", "_vs_address_cm")


def _rebasar(row: dict, base: dict | None) -> dict:
    """La fila de un evento, medida contra el address de SU repetición.

    Las columnas `*_vs_address_*` de `per_frame_table` son `pt[i] − pt[ref]` con
    un único `ref` para toda la tabla. Restarle la fila del address de esta
    repetición cancela ese `ref` y deja `pt[i] − pt[address_de_esta_rep]`, que es
    exactamente lo que la columna dice medir. Las dos filas caen dentro de la
    misma repetición —el address es su primer cuadro— así que se dividieron por
    la misma escala y la resta es legítima.

    `base=None` quiere decir «esta fila ya está medida contra el cuadro que
    corresponde»: es el caso de la repetición cuyo address ES el `ref` de la
    tabla, donde restar sería restar ceros. La fila se devuelve tal cual, sin
    tocar un solo float."""
    if base is None:
        return row
    return {k: ((None if (v is None or base.get(k) is None) else v - base[k]) if k.endswith(_VS_ADDRESS) else v) for k, v in row.items()}


def _en_cada_evento(rows: list[dict], events: dict[str, int], base: dict | None) -> dict[str, dict]:
    return {name: _rebasar(rows[f], base) for name, f in events.items()}


def _diferencias_vs_address(at: dict[str, dict], names: list[str]) -> dict[str, dict]:
    """Cuánto cambió cada ángulo entre el address y cada evento. Sólo columnas en
    grados: no dependen del cuadro de referencia, así que la resta vale igual."""
    deltas: dict[str, dict] = {}
    if "address" not in at:
        return deltas
    for name, r in at.items():
        if name == "address":
            continue
        deltas[f"{name}_vs_address"] = {k: round(r[k] - at["address"][k], 2) for k in names if k.endswith("_deg") and r.get(k) is not None and at["address"].get(k) is not None}
    return deltas


def _duraciones(events: dict[str, int], fps: float) -> dict[str, float]:
    d: dict[str, float] = {}
    for a, b in zip(EVENT_ORDER, EVENT_ORDER[1:]):
        if a in events and b in events:
            d[f"{a}_to_{b}_ms"] = round((events[b] - events[a]) / fps * 1000.0, 1)
    if "address" in events and "top" in events and "impact" in events and events["impact"] > events["top"]:
        d["tempo_ratio"] = round((events["top"] - events["address"]) / (events["impact"] - events["top"]), 2)
    return d


def _picos(rows: list[dict], names: list[str], lo: int = 0, hi: int | None = None) -> dict[str, float | None]:
    """El pico de las dos velocidades de manos entre `lo` y `hi` inclusive.

    Sin ninguna repetición no hay escala, así que `hands_speed_cm_s` queda entero
    en `None` y la lista sale vacía: el pico es `None`, no un aviso de numpy.
    `max` sobre la lista ya filtrada evita el `nanmax` de un eje todo NaN."""
    tramo = rows[lo : (len(rows) if hi is None else hi + 1)]
    return {k: (round(float(max(vs)), 2) if (vs := [r[k] for r in tramo if r[k] is not None and np.isfinite(r[k])]) else None) for k in ("hands_speed_bh_s", "hands_speed_cm_s") if k in names}


# Las tres líneas de texto más anchas que puede haber: el tamaño de la fuente se fija
# con ellas, no con el texto de cada cuadro, para que no cambie de un cuadro al otro.
# El rótulo del evento lleva la repetición delante (`R12 FOLLOW_END`) desde que el
# overlay marca las de todas las repeticiones y no sólo las de la primera.
_TEXT_TEMPLATES = ("9999  t=999.999s   R99 FOLLOW_END", "manos 99.99 bh/s  altura manos 999%", "tronco -180  hombros -180  caderas -180")


def _font_scale(w: int, h: int, th: int, margin_px: int | None = None) -> float:
    """Escala de la fuente: por el alto (h / 1400) y acotada por el ancho, para que la
    línea más ancha entre en `w` menos los márgenes. En un video vertical de
    1080×2320 el alto solo daba 1,66 y la tercera línea se salía por la derecha."""
    margin = 10 * th if margin_px is None else margin_px
    by_height = h / 1400.0
    widest = max(cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 1.0, th)[0][0] for t in _TEXT_TEMPLATES)
    by_width = max(0.3, (w - 2 * margin) / widest) if widest > 0 else by_height
    return float(min(by_height, by_width))


def _draw(frame: np.ndarray, kp: np.ndarray, sc: np.ndarray, row: dict, label: str | None, t_s: float, banner: str | None = None) -> np.ndarray:
    img = frame.copy()
    h = img.shape[0]
    th = max(2, h // 400)
    for a, b in HALPE26_LIMBS:
        if np.isfinite(kp[a]).all() and np.isfinite(kp[b]).all() and sc[a] > 0.3 and sc[b] > 0.3:
            color = (80, 220, 80) if (a in LEFT or b in LEFT) else (60, 140, 255) if (a in RIGHT or b in RIGHT) else (255, 255, 255)
            cv2.line(img, tuple(np.round(kp[a]).astype(int)), tuple(np.round(kp[b]).astype(int)), color, th, cv2.LINE_AA)
    for j in range(kp.shape[0]):
        if np.isfinite(kp[j]).all() and sc[j] > 0.3:
            cv2.circle(img, tuple(np.round(kp[j]).astype(int)), th + 2, (0, 0, 255) if sc[j] < 0.5 else (255, 255, 255), -1, cv2.LINE_AA)
    fs = _font_scale(img.shape[1], h, th)
    def put(text, x, y, color=(255, 255, 255)):
        cv2.putText(img, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), th + 2, cv2.LINE_AA)
        cv2.putText(img, text, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)
    for key, j in (("elbow_left_deg", H.LEFT_ELBOW), ("elbow_right_deg", H.RIGHT_ELBOW), ("knee_left_deg", H.LEFT_KNEE), ("knee_right_deg", H.RIGHT_KNEE)):
        v = row.get(key)
        if v is not None and np.isfinite(kp[j]).all():
            put(f"{v:.0f}", kp[j, 0] + 8 * th, kp[j, 1] - 4 * th, (0, 255, 255))
    y0 = int(30 * fs * 1.5)
    lines = [f"{row['frame']}  t={t_s:.3f}s" + (f"   {label.upper()}" if label else ""), f"manos {row['hands_speed_bh_s'] or 0:.2f} bh/s  altura manos {row['hands_height_pct'] or 0:.0f}%", f"tronco {row['trunk_lean_deg'] or 0:+.0f}  hombros {row['shoulder_line_deg'] or 0:+.0f}  caderas {row['hip_line_deg'] or 0:+.0f}"]
    for i, text in enumerate(lines):
        put(text, 10 * th, y0 * (i + 1), (0, 255, 255) if (label and i == 0) else (255, 255, 255))
    if banner:
        # El camino y la procedencia del fps, quemados en el cuadro (ADR-016): el
        # overlay se comparte suelto y tiene que decir bajo qué supuesto se midió
        # el tiempo. Escala propia, más chica y acotada al ancho, para no encoger
        # las tres líneas de arriba; es constante en todo el clip (texto fijo).
        w_banner = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX, 1.0, th)[0][0]
        fsb = min(fs * 0.7, (img.shape[1] - 20 * th) / w_banner) if w_banner > 0 else fs * 0.7
        cv2.putText(img, banner, (10 * th, int(y0 * 3 + 30 * fsb * 1.6)), cv2.FONT_HERSHEY_SIMPLEX, fsb, (0, 0, 0), th + 2, cv2.LINE_AA)
        cv2.putText(img, banner, (10 * th, int(y0 * 3 + 30 * fsb * 1.6)), cv2.FONT_HERSHEY_SIMPLEX, fsb, (0, 200, 255), th, cv2.LINE_AA)
    return img


def capture_banner(capture: CaptureJson) -> str:
    """La línea que se quema en el overlay. ASCII a propósito: `cv2.putText` no
    dibuja acentos (lección del encargo 05), y estos tres datos no los necesitan."""
    return f"camino {capture.capture_path_id} | fps {capture.fps_real:g} | {capture.fps_provenance}"


# Gris oscuro parejo para las tomas que no tienen video (mocap): que se note que
# el fondo no es una imagen, y que los palitos blancos y verdes se lean encima.
FONDO_LISO = (32, 32, 32)


def _frames(take_dir: Path, capture: CaptureJson, progress_cb=None):
    """Los cuadros sobre los que se dibuja: los del video si la toma tiene uno,
    y si no —una pose que no vino de un video— un fondo liso del tamaño
    declarado en el `capture.json`."""
    original = next(take_dir.glob("original.*"), None)
    if original is not None:
        yield from iter_frames(original, rotation_deg=capture.rotation_deg, display_size=(capture.width, capture.height), progress_cb=progress_cb)
        return
    fondo = np.full((capture.height, capture.width, 3), FONDO_LISO, np.uint8)
    for i in range(capture.frames_decoded):
        yield i, fondo.copy()
        if progress_cb is not None and (i + 1) % 10 == 0:
            progress_cb(i + 1)


def foto_de_evento(rep: int, evento: str) -> str:
    """El nombre del PNG de un evento. La repetición 1 conserva el nombre de
    siempre (`evento-top.png`) y las demás llevan la suya delante
    (`evento-r2-top.png`): la pantalla, la demo y la lista blanca de
    `service/exploracion.py` ya conocen los cuatro primeros y no se rompen."""
    return f"evento-{evento}.png" if rep == 1 else f"evento-r{rep}-{evento}.png"


def render(take_dir: Path, pose, rows: list[dict], events_por_rep: list[tuple[int, dict[str, int]]], fps: float, capture: CaptureJson, progress_cb=None, banner: str | None = None) -> tuple[Path, list[Path]]:
    """Un solo `overlay.mp4` —no uno por repetición— con los eventos de **todas**
    las repeticiones rotulados, y una foto por cada uno.

    `events_por_rep` es `[(rep, {evento: cuadro})]` en orden. Hasta el encargo 35
    esto recibía los eventos de la repetición 1 y nada más: en un clip de dos
    swings el overlay marcaba cuatro cuadros de casi 3000 y los otros cuatro
    pasaban sin nombre. Las repeticiones no se solapan (`build_analysis` descarta
    la que empieza antes de que termine la anterior), así que ningún cuadro puede
    ser evento de dos."""
    frame_events: dict[int, tuple[int, str]] = {}
    for rep, events in events_por_rep:
        for name, f in events.items():
            frame_events[int(f)] = (rep, name)
    out = take_dir / "overlay.mp4"
    banner = ascii_para_quemar(banner or capture_banner(capture))
    proc = None
    snaps: list[Path] = []
    try:
        for i, frame in _frames(take_dir, capture, progress_cb):
            if i >= len(rows):
                break
            marca = frame_events.get(i)
            # El rótulo dice de qué repetición es el evento: en un clip de dos
            # swings, «IMPACT» a secas no distingue el primero del segundo.
            label = f"r{marca[0]} {marca[1]}" if marca else None
            img = _draw(frame, pose.keypoints[i], pose.scores[i], rows[i], label, float(pose.timestamps_s[i]), banner)
            if proc is None:
                hh, ww = img.shape[:2]
                # `-g 12`: GOP corto, como el master.mp4 de la Fase 4. Con el GOP por defecto (250),
                # retroceder un cuadro en el navegador decodifica hasta 250 cuadros por paso.
                proc = subprocess.Popen([ffmpeg_bin(), "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ww}x{hh}", "-r", f"{fps:.4f}", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-g", "12", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
            proc.stdin.write(img.tobytes())
            if marca:
                p = take_dir / foto_de_evento(marca[0], marca[1])
                cv2.imwrite(str(p), img)
                snaps.append(p)
    finally:
        if proc is not None:
            proc.stdin.close()
            proc.wait(timeout=600)
    return out, snaps


def explore(video: Path | None, out_dir: Path, sport: SportConfig, *, height_m: float | None, view: str = "face_on", camino: str = GENERIC_VIDEO_ID, capture_paths: CapturePaths | None = None, cpu: bool = False, progress=None, estimator=None, stage=None, pose_npz: Path | None = None, nota_fuente: str | None = None, banner: str | None = None) -> dict:
    """`progress(i)` recibe el índice del cuadro que se está procesando (en la pose y
    después en el dibujo); `stage(nombre, info)` avisa el cambio de etapa:
    `detectando_pose` (info: total de cuadros), `calculando`, `dibujando` (total).

    Con `pose_npz` la toma arranca de una pose ya calculada: no hay video, no se
    corre el estimador, y `nota_fuente` (la frase de dónde sale el eje del
    tiempo) y `banner` (la línea que se quema en cada cuadro) los pone quien
    llama. `video` puede ser `None` en ese caso."""

    def _stage(name: str, **info) -> None:
        if stage is not None:
            stage(name, info)

    if pose_npz is not None:
        take = prepare_take_from_pose(pose_npz, out_dir, view=view, note=nota_fuente or "", camino=camino, capture_paths=capture_paths)
    else:
        take = prepare_take(video, out_dir, view=view, camino=camino, capture_paths=capture_paths)
        _stage("detectando_pose", total=CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8")).frames_decoded)
        cfg = EstimatorConfig(providers=("CPUExecutionProvider",)) if cpu else EstimatorConfig()
        run_perception(take, sport, cfg, overwrite=True, progress_cb=progress, estimator=estimator)
    _stage("calculando")
    capture = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
    gate_notes = [c.reason for c in capture.gate.checks if c.passed is False and c.reason]
    pose = load_pose(take)
    analysis = build_analysis(take, capture, pose, sport, height_m=height_m)
    if nota_fuente:
        # El aviso que arma `build_analysis` habla de un camino declarado y de un
        # archivo que reproduce; con una pose que no vino de un video las dos
        # cosas son falsas. Se reemplaza por la frase de quien la produjo, que
        # sigue yendo PRIMERO: el supuesto del eje del tiempo se lee antes que
        # cualquier número (ADR-016).
        analysis["warnings"] = [nota_fuente, *(w for w in analysis["warnings"] if not w.startswith("Tasa de cuadros sin verificar"))]
    analysis["warnings"] = [AVISO, *gate_notes, *analysis["warnings"]]
    from kinelab.contract.write import write_analysis

    write_analysis(take, analysis)
    fps = float(capture.fps_real)
    events: dict[str, int] = {}
    subframes: dict[str, dict] = {}
    tolerancias: dict[str, int] = {}
    rep = analysis["events"][0] if analysis["events"] else None
    if rep:
        events = {k: rep[k]["frame"] for k in EVENT_ORDER if rep.get(k)}
        # La tolerancia de CADA evento, en cuadros (CONTRATO.md §events[]): es de
        # donde sale la banda de toda métrica anclada a él (invariante 8) y no es
        # siempre 1 —el top de `vid1.mp4` sale con 4—. Hasta hoy sólo estaba en
        # `analysis.json` y la pantalla no la mostraba.
        tolerancias = {k: rep[k]["tol_frames"] for k in EVENT_ORDER if rep.get(k)}
        # El instante entre dos cuadros, donde el deporte lo defina (hoy: sólo el
        # impacto). El cuadro entero de arriba no cambia: esto lo acompaña.
        subframes = {k: rep[k]["subframe"] for k in EVENT_ORDER if rep.get(k) and rep[k].get("subframe")}
    # La tabla por cuadro divide por la escala de la repetición que contiene a cada
    # cuadro: la MISMA que usaron las métricas de `analysis.json` (CONTRATO.md §La
    # escala). Antes dividía por el `body_height_px` de cada cuadro y los dos
    # números en cm del mismo evento no coincidían, sin que nada lo dijera.
    names, rows = per_frame_table(
        pose, fps, height_m, events.get("address"),
        wrist_score_min=float(getattr(sport.events.params, "wrist_score_min", 0.0) or 0.0) if sport.events is not None else 0.0,
        reps=analysis["reps"],
    )
    with (take / "datos-por-cuadro.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=names)
        w.writeheader()
        w.writerows(rows)
    # `ref` es el cuadro contra el que `per_frame_table` midió TODAS las columnas
    # `*_vs_address_*`: el address de la repetición 1, o el 0 si no hay ninguna.
    # La repetición cuyo address es ese cuadro lee sus filas tal cual; las demás
    # tienen que restarle el suyo (`_rebasar`).
    ref = events.get("address") if events.get("address") is not None else 0
    at = _en_cada_evento(rows, events, None)
    deltas = _diferencias_vs_address(at, names)
    durations = _duraciones(events, fps)
    peaks = _picos(rows, names)
    # De dónde sale cada cm y contra qué cuadro se mide cada «vs address», dicho.
    rep1 = analysis["reps"][0] if analysis["reps"] else None
    # El cuadro del máximo de la cadena sólo se publica con UNA repetición: con
    # varias, el que trae `quality.scale_px` es el de la repetición que aportó la
    # mediana, que puede no ser ésta. Mostrar ese cuadro al lado de esta escala
    # sería mandar a mirar un cuadro que no la produjo. Publicarlo por repetición
    # pide un campo más en `reps[]` de `analysis.json`, o sea otro bump de
    # contrato: no es de este encargo.
    escala_cuadro = analysis["quality"]["scale_px"]["frame"] if len(analysis["reps"]) == 1 else None
    # `explore.py` cae al cuadro 0 cuando no hay address (`ref` arriba). El valor no
    # cambia; lo que cambia es que ahora se dice cuál fue, porque «vs address» sin
    # address no es «vs address».
    tiene_address = events.get("address") is not None
    referencia_cuadro = events.get("address") if tiene_address else (0 if rows else None)
    referencia_fuente = "address" if tiene_address else ("cuadro 0 (sin address)" if rows else None)

    # Una entrada por repetición, con TODO lo que hasta el encargo 35 existía sólo
    # para la primera. El front del encargo 36 elige una y cambia la pantalla
    # entera con esto; hasta entonces nada la lee y nada se rompe. Los nombres son
    # los mismos que los de primer nivel a propósito: es el mismo dato, una
    # repetición más abajo.
    repeticiones_detalle: list[dict] = []
    for r, rep_ev in zip(analysis["reps"], analysis["events"]):
        ev_f = {k: rep_ev[k]["frame"] for k in EVENT_ORDER if rep_ev.get(k)}
        addr = ev_f.get("address")
        base = None if (addr is None or addr == ref) else rows[addr]
        at_r = _en_cada_evento(rows, ev_f, base)
        repeticiones_detalle.append({
            "rep": r["rep"], "frame_start": r["frame_start"], "frame_end": r["frame_end"],
            "eventos_frame": ev_f, "eventos_t_s": {k: round(f / fps, 3) for k, f in ev_f.items()},
            "eventos_tol_frames": {k: rep_ev[k]["tol_frames"] for k in EVENT_ORDER if rep_ev.get(k)},
            "eventos_subcuadro": {k: rep_ev[k]["subframe"] for k in EVENT_ORDER if rep_ev.get(k) and rep_ev[k].get("subframe")},
            "escala_px": r["scale_px"], "escala_fuente": r["scale_source"], "escala_cuadro": escala_cuadro,
            "referencia_cuadro": addr if addr is not None else (0 if rows else None),
            "referencia_fuente": "address" if addr is not None else ("cuadro 0 (sin address)" if rows else None),
            "duraciones": _duraciones(ev_f, fps),
            # El pico DENTRO de la repetición, no el del clip entero: el de primer
            # nivel es el máximo de todos los cuadros y en un clip de dos swings
            # no es de ninguno de los dos en particular.
            "picos": _picos(rows, names, r["frame_start"], r["frame_end"]),
            "en_cada_evento": at_r, "diferencias_vs_address": _diferencias_vs_address(at_r, names),
        })

    summary = {"aviso": AVISO, "video": capture.original_name, "camino": capture.capture_path_id, "camino_calibrado": capture.capture_path_calibrated,
               "fps_provenance": capture.fps_provenance, "fps_aviso": nota_fuente or next((w for w in analysis["warnings"] if w.startswith("Tasa de cuadros sin verificar")), None),
               # TRANSITORIOS: de acá hasta `columnas`, todo lo que habla de eventos,
               # escala y referencia es la repetición 1, y está repetido en
               # `repeticiones_detalle[0]`. Lo retira el encargo 36, cuando el front
               # lea la repetición elegida.
               "fps_archivo": fps, "cuadros": len(rows), "altura_m": height_m, "gate_diria": gate_notes, "eventos_frame": events, "eventos_t_s": {k: round(f / fps, 3) for k, f in events.items()}, "eventos_tol_frames": tolerancias, "eventos_subcuadro": subframes,
               "escala_px": rep1["scale_px"] if rep1 else None, "escala_fuente": rep1["scale_source"] if rep1 else None, "escala_cuadro": escala_cuadro,
               "referencia_cuadro": referencia_cuadro, "referencia_fuente": referencia_fuente,
               "repeticion_mostrada": rep1["rep"] if rep1 else None, "repeticiones": len(analysis["reps"]),
               "duraciones": durations, "picos": peaks, "en_cada_evento": finite_or_none(at), "diferencias_vs_address": deltas,
               "repeticiones_detalle": repeticiones_detalle,
               "calidad": analysis["quality"], "columnas": names}
    (take / "datos-eventos.json").write_text(json.dumps(finite_or_none(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    _stage("dibujando", total=len(rows))
    eventos_por_rep = [(d["rep"], d["eventos_frame"]) for d in repeticiones_detalle]
    overlay, snaps = render(take, pose, rows, eventos_por_rep, fps, capture, progress_cb=progress, banner=banner)
    summary["archivos"] = [str(take / "datos-por-cuadro.csv"), str(take / "datos-eventos.json"), str(overlay), *map(str, snaps)]
    return summary
