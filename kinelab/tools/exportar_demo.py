"""La versión web de un trabajo de exploración: liviana, recortada al sujeto y
con la transformación declarada.

    python -m kinelab.tools.exportar_demo TRABAJO [TRABAJO...] --out web/public/demo

**Para qué.** El motor no se despliega: es onnxruntime con CoreML, `rtmlib`,
OpenCV y ffmpeg, con pesos de cientos de MB, y tarda 76 s en procesar un clip de
17,8 s. Lo que se puede desplegar es el visor con resultados **ya calculados**
en la Mac. Un trabajo tal como queda en `data/exploracion/` pesa 424 MB
(`overlay.mp4` 245 MB, `original.mp4` 93 MB y cuatro PNG de 18 MB): nada de eso
entra en un repo ni en un deployment. Esto produce la versión que sí entra.

**Qué hace, en una línea:** recorta el clip al tramo del gesto, lo recorta al
rectángulo que contiene al sujeto en todo ese tramo, lo reescala, y deja al lado
**cómo deshacer esas tres cosas**.

**Lo que NO hace: reescribir coordenadas.** Los keypoints que salen acá son los
del `pose.npz`, en `image_px` del cuadro como se ve (CONTEXTO.md §Sistemas de
coordenadas). Lo que cambia es el video, y el cambio viaja como una
transformación afín explícita en `transformacion.json`:

    x_demo = (x_origen − offset_x) · escala
    y_demo = (y_origen − offset_y) · escala
    cuadro_demo = cuadro_origen − cuadro_offset

El que dibuja aplica esa transformación. Si en vez de eso se reescribieran los
puntos, el `analysis.json` y el CSV hablarían de un marco y los puntos de otro,
y nada lo delataría (cementerio 6 y 8 de `HERENCIA.md`: una constante de
normalización mal elegida devuelve números plausibles multiplicados por un
factor).

**El tramo se calcula sin nombrar ningún evento.** El primero y el último de los
eventos que el deporte haya detectado, más un segundo de margen a cada lado. En
golf eso es «un segundo antes del address y uno después del follow_end»; acá no
se escribe ninguna de las dos palabras (invariante 13).

Deja en `<out>/<id>/`:

    video.mp4            el original recortado y reescalado, SIN palitos quemados
    overlay.mp4          el mismo recorte sobre el overlay ya dibujado (lo que
                         el reproductor muestra hasta que el visor dibuje desde datos)
    transformacion.json  el recorte, la escala y el offset de cuadros, declarados
    pose.json            los 26 puntos por cuadro del tramo, en image_px del origen
    datos-eventos.json · analysis.json · capture.json   tal cual
    datos-por-cuadro.csv recortado al tramo (los números de cuadro NO se tocan)
    evento-<id>.jpg      las fotos por evento, en JPEG al alto pedido; con varias
                         repeticiones también `evento-r<N>-<id>.jpg` (encargo 35).
                         Salen solas: `exportar_fotos` junta `evento-*.png` y no
                         tiene ninguna lista de nombres que actualizar
    pose3d.json          si el trabajo lo tiene (ejemplos de mocap)
    trabajo.json         lo que devolvería `GET /api/datos/<id>`, para el modo demo

y reescribe `<out>/index.json` con todos los trabajos que haya exportados.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from kinelab.perception.keypoints import HALPE26_LIMBS, HALPE26_NAMES
from kinelab.perception.posestore import POSE_FILE, finite_or_none, load_pose
from kinelab.perception.video import ffmpeg_bin

ESQUEMA_TRANSFORMACION = "kinelab.transformacion/1.0.0"
ESQUEMA_POSE2D = "kinelab.pose2d/1.0.0"
ESQUEMA_INDICE = "kinelab.demo/1.0.0"

VIDEO_LIMPIO = "video.mp4"
VIDEO_OVERLAY = "overlay.mp4"
TRANSFORMACION = "transformacion.json"
POSE_JSON = "pose.json"
INDICE = "index.json"

#: Margen del recorte, como fracción del **alto** de la caja que contiene al
#: sujeto en todo el tramo. El alto y no el ancho porque es la dimensión que
#: manda: en un swing la caja mide 1655 px de alto contra 809 de ancho (medido
#: en `vid1`). El 0,10 sale de mirar el cuadro del top de `vid1`: la cabeza del
#: palo llega a y≈976 px y el keypoint más alto del tramo está en 1123, o sea
#: 147 px más abajo — el palo no es un keypoint y hay que dejarle lugar.
MARGEN = 0.10

#: Segundos de video antes del primer evento y después del último.
MARGEN_S = 1.0

#: Alto del video exportado, en píxeles.
ALTO = 1080

#: `-crf` de libx264. 23 con `-preset slow` deja `vid1` (291 cuadros, 4,85 s)
#: bien por debajo del objetivo de 15 MB.
CRF = 23

#: GOP corto como el `master.mp4` de la Fase 4 (ESPECIFICACION 4.2): con el GOP
#: por defecto (250) retroceder un cuadro en el navegador decodifica hasta 250.
GOP = 12

#: Objetivo de peso por trabajo. No es un límite del formato: es lo que entra en
#: un repo y en un deployment (§Contexto del encargo 22).
MAX_MB = 15.0

#: Las fotos por evento, en JPEG. 88 baja un PNG de 18 MB a decenas de KB sin que
#: se note en un palito de 3 px de ancho.
JPEG_CALIDAD = 88

AVISO_DEMO = (
    "Demo estática: resultados YA calculados en la Mac del entrenador. El motor no se "
    "despliega (onnxruntime con CoreML, pesos de cientos de MB, 76 s por clip). Acá no se "
    "puede subir un video: esto es un visor de resultados."
)


class ExportError(RuntimeError):
    """El trabajo no se puede exportar, con la razón."""


# --- leer el trabajo ----------------------------------------------------------------


@dataclass
class Trabajo:
    """Lo que hace falta de un trabajo de `data/exploracion/<id>/` para exportarlo."""

    id: str
    dir: Path
    meta: dict[str, Any]  # trabajo.json
    captura: dict[str, Any]  # capture.json
    resumen: dict[str, Any]  # datos-eventos.json
    pose: Any  # PoseData
    cuadros: int
    fps: float
    tamano: tuple[int, int]  # (ancho, alto) del cuadro como se ve
    eventos: dict[str, int]

    @property
    def original(self) -> Path | None:
        return next(self.dir.glob("original.*"), None)


def cargar(trabajo_dir: Path) -> Trabajo:
    d = Path(trabajo_dir)
    if not d.is_dir():
        raise ExportError(f"{d}: no existe.")
    meta = _json(d / "trabajo.json", obligatorio=False) or {}
    if meta.get("estado") not in (None, "listo"):
        raise ExportError(f"{d.name}: el trabajo está en estado {meta['estado']!r}, no hay nada terminado que exportar.")
    captura = _json(d / "capture.json")
    resumen = _json(d / "datos-eventos.json")
    if not (d / POSE_FILE).is_file():
        raise ExportError(f"{d.name}: no tiene {POSE_FILE}.")
    pose = load_pose(d)
    eventos = {k: int(v) for k, v in (resumen.get("eventos_frame") or {}).items() if v is not None}
    if not eventos:
        raise ExportError(f"{d.name}: no tiene ningún evento detectado; no hay tramo que recortar (usá --tramo A-B).")
    return Trabajo(
        id=d.name, dir=d, meta=meta, captura=captura, resumen=resumen, pose=pose,
        cuadros=int(pose.keypoints.shape[0]), fps=float(captura["fps_real"]),
        tamano=(int(captura["width"]), int(captura["height"])), eventos=eventos,
    )


def _json(p: Path, *, obligatorio: bool = True) -> dict[str, Any] | None:
    if not p.is_file():
        if obligatorio:
            raise ExportError(f"{p.parent.name}: falta {p.name}.")
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# --- el tramo y el recorte ----------------------------------------------------------


def tramo(t: Trabajo, *, margen_s: float = MARGEN_S, pedido: str = "auto") -> tuple[int, int]:
    """El rango de cuadros `[a, b]` que se exporta, ambos inclusive.

    `auto`: del primer al último evento detectado, más `margen_s` a cada lado.
    Sin nombrar ninguno: el motor no conoce los eventos de ningún deporte
    (invariante 13). `A-B`: el rango tal cual, en cuadros del origen.
    """
    if pedido != "auto":
        try:
            a_s, b_s = pedido.split("-", 1)
            a, b = int(a_s), int(b_s)
        except ValueError as e:
            raise ExportError(f"--tramo {pedido!r}: se espera `auto` o `A-B` con dos enteros.") from e
        if a > b:
            raise ExportError(f"--tramo {pedido!r}: el primer cuadro es mayor que el último.")
    else:
        m = int(round(margen_s * t.fps))
        a, b = min(t.eventos.values()) - m, max(t.eventos.values()) + m
    a, b = max(0, a), min(t.cuadros - 1, b)
    if b <= a:
        raise ExportError(f"{t.id}: el tramo pedido queda vacío ({a}–{b} de {t.cuadros} cuadros).")
    return a, b


def caja_del_sujeto(t: Trabajo, a: int, b: int) -> tuple[float, float, float, float]:
    """`(x0, y0, x1, y1)` que contiene al sujeto en **todos** los cuadros de `[a, b]`.

    Unión de los keypoints finitos y del bbox del `pose.npz`. Los dos: el bbox es
    lo que vio el detector y los keypoints son lo que se dibuja; uno puede salirse
    del otro y lo que no puede quedar afuera es ninguno de los dos.
    """
    k = np.asarray(t.pose.keypoints[a : b + 1], dtype=float)
    bb = np.asarray(t.pose.bbox[a : b + 1], dtype=float)
    xs = np.concatenate([k[..., 0].ravel(), bb[:, 0], bb[:, 2]])
    ys = np.concatenate([k[..., 1].ravel(), bb[:, 1], bb[:, 3]])
    xs, ys = xs[np.isfinite(xs)], ys[np.isfinite(ys)]
    if xs.size == 0 or ys.size == 0:
        raise ExportError(f"{t.id}: no hay ni un punto finito en el tramo {a}–{b}.")
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def recorte(t: Trabajo, a: int, b: int, *, modo: str = "sujeto", margen: float = MARGEN) -> tuple[int, int, int, int]:
    """`(x, y, ancho, alto)` del recorte, en píxeles enteros y pares (yuv420p).

    `completo` devuelve el cuadro entero. `sujeto` toma la caja del sujeto en todo
    el tramo y le suma `margen · alto de la caja` en los cuatro lados — el palo no
    es un keypoint y el margen es lo que le deja lugar — acotado al cuadro.
    """
    W, Hh = t.tamano
    if modo == "completo":
        return 0, 0, _par(W), _par(Hh)
    if modo != "sujeto":
        raise ExportError(f"--recorte {modo!r}: se espera `sujeto` o `completo`.")
    x0, y0, x1, y1 = caja_del_sujeto(t, a, b)
    m = margen * (y1 - y0)
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    x = max(0, int(np.floor(x0)))
    y = max(0, int(np.floor(y0)))
    w = min(W - x, int(np.ceil(x1)) - x)
    h = min(Hh - y, int(np.ceil(y1)) - y)
    return x, y, _par(w), _par(h)


def _par(n: int) -> int:
    """Al entero par inmediatamente inferior: yuv420p submuestrea el croma 2×2."""
    return max(2, int(n) // 2 * 2)


def puntos_fuera_del_origen(t: Trabajo, a: int, b: int) -> dict[str, Any]:
    """Cuántos keypoints del tramo caen fuera del **cuadro del origen**.

    Ningún recorte los puede salvar: ya estaban afuera antes de recortar. Se
    cuentan y se declaran en vez de descubrirse mirando (invariante 5, el
    espíritu: lo que se pierde se cuenta y queda visible). Pasa en el ejemplo de
    mocap desde `down_the_line`, donde la cámara virtual proyecta las manos del
    top fuera del lienzo.
    """
    W, Hh = t.tamano
    k = np.asarray(t.pose.keypoints[a : b + 1], dtype=float)
    finito = np.isfinite(k).all(axis=2)
    dentro = (k[..., 0] >= 0) & (k[..., 0] <= W) & (k[..., 1] >= 0) & (k[..., 1] <= Hh)
    n = int((finito & ~dentro).sum())
    return {
        "n": n,
        "de": int(finito.sum()),
        "nota": (
            "keypoints del tramo que caen fuera del cuadro del ORIGEN: ningun recorte los "
            "puede incluir porque ya estaban afuera. El recorte si garantiza que todo lo que "
            "estaba adentro sigue adentro." if n else None
        ),
    }


def transformacion(t: Trabajo, a: int, b: int, rect: tuple[int, int, int, int], alto: int, *, modo: str, margen: float) -> dict[str, Any]:
    """La transformación afín del origen al video exportado, como dato.

    Declarada adentro del archivo y no en un comentario: es la única forma de
    dibujar bien sobre el video exportado, y el que la lee puede no ser este repo.
    """
    x, y, w, h = rect
    alto = _par(min(alto, h))  # nunca se agranda: reescalar para arriba no agrega información
    escala = alto / h
    ancho = _par(int(round(w * escala)))
    return {
        "schema": ESQUEMA_TRANSFORMACION,
        "generado": _ahora(),
        "trabajo": t.id,
        "reference_frame_origen": "image_px",
        "reference_frame_destino": "demo_px",
        "nota": (
            "x_demo = (x_origen - offset_x) * escala ; y_demo = (y_origen - offset_y) * escala ; "
            "cuadro_demo = cuadro_origen - cuadro_offset. Los keypoints NO se reescribieron: "
            "pose.json, analysis.json, datos-eventos.json y datos-por-cuadro.csv siguen en "
            "image_px y en cuadros del origen. Esta transformacion es lo unico que cambia."
        ),
        "offset_x": x,
        "offset_y": y,
        "escala": round(escala, 6),
        "cuadro_offset": a,
        "cuadros": b - a + 1,
        "fps": t.fps,
        "tamano_origen": [t.tamano[0], t.tamano[1]],
        "recorte": {"x": x, "y": y, "ancho": w, "alto": h},
        "tamano_destino": [ancho, alto],
        "modo_recorte": modo,
        "margen_recorte": margen if modo == "sujeto" else None,
        "cuadros_origen": t.cuadros,
        "tramo_origen": [a, b],
        "caja_sujeto": [round(v, 1) for v in caja_del_sujeto(t, a, b)],
        "puntos_fuera_del_origen": puntos_fuera_del_origen(t, a, b),
    }


def aplicar(tr: dict[str, Any], x: float, y: float) -> tuple[float, float]:
    """La transformación de `transformacion.json` aplicada a un punto. Es la
    referencia contra la que el TypeScript del front se verifica."""
    e = float(tr["escala"])
    return (x - tr["offset_x"]) * e, (y - tr["offset_y"]) * e


# --- escribir ------------------------------------------------------------------------


def exportar_video(src: Path, dst: Path, tr: dict[str, Any], *, crf: int = CRF, preset: str = "slow") -> int:
    """Un video del origen recortado al tramo, al rectángulo y a la escala de `tr`.

    `select` por número de cuadro y no un `-ss` por tiempo: el corte tiene que
    caer en el cuadro que dice el análisis, y un seek por PTS no lo garantiza.
    `setpts=N/FRAME_RATE/TB` regenera timestamps parejos después del `select`;
    nunca `-r` para «arreglar» el fps, que tira cuadros (AGENTS.md).
    """
    a, b = tr["tramo_origen"]
    x, y, w, h = (tr["recorte"][k] for k in ("x", "y", "ancho", "alto"))
    dw, dh = tr["tamano_destino"]
    vf = f"select='between(n\\,{a}\\,{b})',crop={w}:{h}:{x}:{y},scale={dw}:{dh}:flags=lanczos,setpts=N/FRAME_RATE/TB"
    cmd = [
        ffmpeg_bin(), "-y", "-v", "error", "-nostdin", "-i", str(src),
        "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-g", str(GOP),
        "-pix_fmt", "yuv420p", "-fps_mode", "cfr", "-r", f"{tr['fps']:.4f}",
        "-movflags", "+faststart", str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not dst.is_file():
        raise ExportError(f"ffmpeg falló sobre {src.name}: {r.stderr.strip()[:500]}")
    n = contar_cuadros(dst)
    if n != tr["cuadros"]:
        raise ExportError(f"{dst.name}: salieron {n} cuadros y el tramo son {tr['cuadros']}. El corte no cae donde dice el análisis.")
    return dst.stat().st_size


def contar_cuadros(video: Path) -> int:
    """Cuadros decodificados de verdad, no `nb_frames` del contenedor (CAPTURA.md:
    el contenedor no puede decir su propia verdad)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, timeout=600,
    )
    return int((r.stdout or "0").strip().splitlines()[0] or 0)


def exportar_fotos(t: Trabajo, out: Path, tr: dict[str, Any]) -> list[str]:
    """Las fotos por evento en JPEG, con el mismo recorte y la misma escala que el
    video: si no, el que las mira ve un encuadre y el reproductor otro."""
    x, y, w, h = (tr["recorte"][k] for k in ("x", "y", "ancho", "alto"))
    dw, dh = tr["tamano_destino"]
    nombres = []
    for p in sorted(t.dir.glob("evento-*.png")):
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            continue
        ih, iw = img.shape[:2]
        if (iw, ih) != t.tamano:
            raise ExportError(f"{p.name}: mide {iw}×{ih} y el capture.json dice {t.tamano[0]}×{t.tamano[1]}.")
        recortada = img[y : y + h, x : x + w]
        chica = cv2.resize(recortada, (dw, dh), interpolation=cv2.INTER_AREA)
        dst = out / (p.stem + ".jpg")
        cv2.imwrite(str(dst), chica, [cv2.IMWRITE_JPEG_QUALITY, JPEG_CALIDAD])
        nombres.append(dst.name)
    return nombres


def exportar_csv(t: Trabajo, out: Path, a: int, b: int) -> str | None:
    """El CSV por cuadro recortado al tramo. Los números de la columna `frame` **no
    se tocan**: son los del origen, como todo lo demás."""
    src = t.dir / "datos-por-cuadro.csv"
    if not src.is_file():
        return None
    dst = out / src.name
    with src.open(newline="", encoding="utf-8") as f, dst.open("w", newline="", encoding="utf-8") as g:
        r = csv.DictReader(f)
        w = csv.DictWriter(g, fieldnames=r.fieldnames or [])
        w.writeheader()
        for fila in r:
            if a <= int(float(fila["frame"])) <= b:
                w.writerow(fila)
    return dst.name


def exportar_pose(t: Trabajo, out: Path, a: int, b: int) -> str:
    """`pose.json`: los 26 puntos por cuadro del tramo, para que el visor dibuje
    desde datos (ADR-014, invariante 10).

    La fila `i` es el cuadro `cuadro_offset + i` del origen, y sus coordenadas
    están en `image_px` del **origen**: la misma regla que el video, escrita acá
    también porque este archivo se lee suelto. Un decimal en los puntos y dos en
    los scores: el ruido del modelo es de píxeles enteros (0,23–0,32 px de
    diferencia entre proveedores, AGENTS.md) y guardar más es guardar ruido.

    El formato es el que el encargo 21 va a servir por `GET /api/datos/<id>/pose`;
    si ese encargo lo cambia, cambia acá también.
    """
    k = np.asarray(t.pose.keypoints[a : b + 1], dtype=float)
    s = np.asarray(t.pose.scores[a : b + 1], dtype=float)
    doc = {
        "schema": ESQUEMA_POSE2D,
        "trabajo": t.id,
        "reference_frame": "image_px",
        "nota": (
            "Coordenadas en pixeles del cuadro del ORIGEN como se ve (rotacion aplicada), "
            "tal como salen del pose.npz. Para dibujar sobre el video exportado hay que "
            "aplicar transformacion.json. La fila i es el cuadro cuadro_offset + i del origen."
        ),
        "fps": t.fps,
        "tamano_origen": [t.tamano[0], t.tamano[1]],
        "cuadro_offset": a,
        "cuadros": int(k.shape[0]),
        "nombres": list(HALPE26_NAMES),
        "huesos": [[int(i), int(j)] for i, j in HALPE26_LIMBS],
        "eventos_frame": dict(t.eventos),
        "keypoints": np.round(k, 1).tolist(),
        "scores": np.round(s, 2).tolist(),
        "plausibility": [int(v) for v in t.pose.plausibility[a : b + 1]],
        "provenance": t.pose.provenance,
    }
    dst = out / POSE_JSON
    dst.write_text(json.dumps(finite_or_none(doc), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return dst.name


def ficha_de_captura_min(c: dict[str, Any]) -> dict[str, Any]:
    """La ficha del archivo que el front espera en `Trabajo.archivo`, armada desde
    el `capture.json`. Los mismos campos que `service.exploracion.ficha_de_captura`,
    que acá no se puede importar sin arrastrar FastAPI al motor.

    Son dos copias paralelas y tienen que seguir siendo la misma:
    `tests/test_fichas_de_captura.py` falla si divergen.
    """
    vfr = float(c.get("vfr_ratio") or 1.0)
    cal = c.get("fps_calibration") or {}
    return {
        "codec": c.get("codec"), "ancho": c.get("width"), "alto": c.get("height"),
        "rotacion_deg": c.get("rotation_deg"), "cuadros": c.get("frames_decoded"),
        "duracion_s": c.get("duration_s"), "duracion_reproduccion_s": c.get("duration_playback_s"),
        "fps_real": c.get("fps_real"), "fps_reproduccion": c.get("fps_playback"),
        "fps_reproduccion_bruto": c.get("fps_playback_raw"), "stretch_factor": c.get("stretch_factor"),
        "vfr_ratio": vfr, "vfr_ratio_bruto": c.get("vfr_ratio_raw"),
        "tasa_variable": vfr > 1.10, "vfr_ratio_max": 1.10,
        "primer_delta_s": c.get("first_delta_s"), "fps_note": c.get("fps_note"),
        "camino": c.get("capture_path_id"), "camino_calibrado": c.get("capture_path_calibrated"),
        "fps_provenance": c.get("fps_provenance") or "sin_verificar",
        "calibracion_clip_sha256": cal.get("clip_sha256"),
        "calibracion_mismo_archivo": cal.get("same_file"),
        "original": c.get("original_name"), "grabado": c.get("recorded_at"),
    }


@dataclass
class Resultado:
    id: str
    dir: Path
    transformacion: dict[str, Any]
    archivos: dict[str, int] = field(default_factory=dict)  # nombre → bytes

    @property
    def bytes(self) -> int:
        return sum(self.archivos.values())


def exportar(trabajo_dir: Path, out_root: Path, *, alto: int = ALTO, modo: str = "sujeto", pedido: str = "auto", margen: float = MARGEN, crf: int = CRF, preset: str = "slow", max_mb: float = MAX_MB) -> Resultado:
    """Un trabajo → `<out_root>/<id>/`. Devuelve qué se escribió y cuánto pesa."""
    t = cargar(trabajo_dir)
    a, b = tramo(t, pedido=pedido)
    rect = recorte(t, a, b, modo=modo, margen=margen)
    tr = transformacion(t, a, b, rect, alto, modo=modo, margen=margen)

    out = out_root / t.id
    out.mkdir(parents=True, exist_ok=True)
    for viejo in out.iterdir():  # sin restos de una corrida anterior con otro tramo
        viejo.unlink() if viejo.is_file() else shutil.rmtree(viejo)

    archivos: dict[str, int] = {}
    original = t.original
    if original is not None:
        archivos[VIDEO_LIMPIO] = exportar_video(original, out / VIDEO_LIMPIO, tr, crf=crf, preset=preset)
        tr["video_limpio"] = VIDEO_LIMPIO
        tr["video_limpio_null_reason"] = None
    else:
        tr["video_limpio"] = None
        tr["video_limpio_null_reason"] = (
            "esta toma no tiene original: la pose no vino de un video (kinelab.explore, "
            "modo pose_npz). El unico video que hay es el overlay dibujado sobre fondo liso."
        )
    if (t.dir / VIDEO_OVERLAY).is_file():
        archivos[VIDEO_OVERLAY] = exportar_video(t.dir / VIDEO_OVERLAY, out / VIDEO_OVERLAY, tr, crf=crf, preset=preset)
    tr["overlay"] = VIDEO_OVERLAY if VIDEO_OVERLAY in archivos else None
    tr["palitos_quemados_en_overlay"] = True

    (out / TRANSFORMACION).write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
    archivos[TRANSFORMACION] = (out / TRANSFORMACION).stat().st_size

    for n in ("datos-eventos.json", "analysis.json", "capture.json", "pose3d.json"):
        if (t.dir / n).is_file():
            shutil.copy2(t.dir / n, out / n)
            archivos[n] = (out / n).stat().st_size
    if (n := exportar_csv(t, out, a, b)):
        archivos[n] = (out / n).stat().st_size
    n = exportar_pose(t, out, a, b)
    archivos[n] = (out / n).stat().st_size
    for n in exportar_fotos(t, out, tr):
        archivos[n] = (out / n).stat().st_size

    (out / "trabajo.json").write_text(json.dumps(_trabajo_json(t, out.name, archivos), ensure_ascii=False, indent=2), encoding="utf-8")
    archivos["trabajo.json"] = (out / "trabajo.json").stat().st_size

    r = Resultado(id=t.id, dir=out, transformacion=tr, archivos=archivos)
    if r.bytes > max_mb * 1e6:
        print(f"  ¡ojo! {t.id} pesa {r.bytes / 1e6:.1f} MB y el objetivo es {max_mb:g} MB. Subí --crf o bajá --alto.", file=sys.stderr)
    return r


def _trabajo_json(t: Trabajo, id_demo: str, archivos: dict[str, int]) -> dict[str, Any]:
    """Lo que devolvería `GET /api/datos/<id>` para este trabajo, con las URLs
    apuntando a `/demo/<id>/`. Así el modo demo del front lee el mismo tipo que
    el modo local y la diferencia queda en un solo lugar de `api.ts`."""
    m = t.meta
    return {
        "id": id_demo,
        "estado": "listo",
        "origen": m.get("origen") or "subida",
        "etiqueta": m.get("etiqueta"),
        "camino": m.get("camino") or t.captura.get("capture_path_id"),
        "archivo": ficha_de_captura_min(t.captura),
        "progreso": m.get("progreso") or {"cuadros": t.cuadros, "total": t.cuadros},
        "error": None,
        "video": m.get("video") or t.captura.get("original_name") or id_demo,
        "altura_m": m.get("altura_m"),
        "vista": m.get("vista") or t.captura.get("view") or "face_on",
        "creado": m.get("creado"),
        "terminado": m.get("terminado"),
        "segundos": m.get("segundos"),
        "archivos": {n: f"/demo/{id_demo}/{n}" for n in sorted(archivos)},
        "resumen": t.resumen,
    }


def escribir_indice(out_root: Path) -> Path:
    """`index.json` con todos los trabajos que hay exportados, del más nuevo al más
    viejo. Se rehace entero cada vez: el disco manda, igual que en
    `service.exploracion.listar()`."""
    filas = []
    for d in sorted(p for p in out_root.iterdir() if p.is_dir()):
        tj, tr = d / "trabajo.json", d / TRANSFORMACION
        if not (tj.is_file() and tr.is_file()):
            continue
        j = json.loads(tj.read_text(encoding="utf-8"))
        r = j.get("resumen") or {}
        f = j.get("archivo") or {}
        filas.append({
            "id": j["id"], "estado": "listo", "origen": j.get("origen"), "etiqueta": j.get("etiqueta"),
            "video": j.get("video"), "altura_m": j.get("altura_m"), "vista": j.get("vista"),
            "creado": j.get("creado"), "terminado": j.get("terminado"), "segundos": j.get("segundos"),
            "error": None, "camino": j.get("camino") or f.get("camino"),
            "fps_provenance": f.get("fps_provenance"), "fps_archivo": r.get("fps_archivo"),
            "cuadros": r.get("cuadros"), "eventos_frame": r.get("eventos_frame"),
            "avisos": [r.get("aviso"), r.get("fps_aviso"), *(r.get("gate_diria") or [])],
        })
    filas.sort(key=lambda f: (f.get("creado") or "", f["id"]), reverse=True)
    for f in filas:
        f["avisos"] = [a for a in f["avisos"] if a]
    doc = {"schema": ESQUEMA_INDICE, "generado": _ahora(), "aviso": AVISO_DEMO, "trabajos": filas}
    p = out_root / INDICE
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _ahora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# --- CLI ------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m kinelab.tools.exportar_demo", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trabajos", nargs="+", type=Path, help="carpetas de data/exploracion/ a exportar")
    ap.add_argument("--out", type=Path, default=Path("web/public/demo"), help="carpeta destino (default: web/public/demo)")
    ap.add_argument("--recorte", choices=("sujeto", "completo"), default="sujeto")
    ap.add_argument("--alto", type=int, default=ALTO, help=f"alto del video exportado, en px (default: {ALTO})")
    ap.add_argument("--tramo", default="auto", help="`auto` (los eventos + 1 s a cada lado) o `A-B` en cuadros del origen")
    ap.add_argument("--margen", type=float, default=MARGEN, help=f"margen del recorte, fracción del alto de la caja (default: {MARGEN})")
    ap.add_argument("--crf", type=int, default=CRF)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--max-mb", type=float, default=MAX_MB)
    a = ap.parse_args(argv)

    a.out.mkdir(parents=True, exist_ok=True)
    total = 0
    for d in a.trabajos:
        try:
            r = exportar(d, a.out, alto=a.alto, modo=a.recorte, pedido=a.tramo, margen=a.margen, crf=a.crf, preset=a.preset, max_mb=a.max_mb)
        except ExportError as e:
            print(f"✗ {d}: {e}", file=sys.stderr)
            return 2
        tr = r.transformacion
        total += r.bytes
        print(f"✓ {r.id}  {r.bytes / 1e6:6.2f} MB  cuadros {tr['tramo_origen'][0]}–{tr['tramo_origen'][1]} ({tr['cuadros']})  "
              f"recorte {tr['recorte']['ancho']}×{tr['recorte']['alto']} en ({tr['offset_x']},{tr['offset_y']})  "
              f"escala {tr['escala']:.4f}  destino {tr['tamano_destino'][0]}×{tr['tamano_destino'][1]}")
        for n, b in sorted(r.archivos.items(), key=lambda kv: -kv[1]):
            print(f"    {b / 1e6:8.3f} MB  {n}")
    p = escribir_indice(a.out)
    print(f"\n{p} · {total / 1e6:.2f} MB en {len(a.trabajos)} trabajo(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
