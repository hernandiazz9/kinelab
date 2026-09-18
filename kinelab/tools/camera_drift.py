"""Cuánto se corre la imagen durante el gesto. Se MIDE; no se compensa.

Un desplazamiento en píxeles de la cámara entra derecho en todo lo que el motor
mide como desplazamiento del cuerpo: si la imagen se corre 20 px entre el
address y el impacto, los siete desplazamientos en cm de esa repetición se
mueven 20 px / `scale_px` × estatura, sin que nada lo delate. La auditoría del
16/9 lo midió en `cortado3-lento.mp4` con tres métodos independientes: **+14 a
+23 px en x en la repetición 1 y −8 a −25 px en la 2**, por encima del MDC de
esas métricas (2,4–4,5 cm). Y `quality.camera_motion_px` no lo ve: es la
mediana del corrimiento entre muestras tomadas cada 120 cuadros reducidas a
320 px (`kinelab/perception/video.py`), que mide sacudones, no deriva lenta.

Esta herramienta mide la deriva y la deja en un archivo aparte. **No escribe en
`analysis.json` ni en `pose.npz`, y ninguna métrica la lee**: compensar dentro
de las métricas es otra decisión y necesita su propia validación.

Es agnóstica al deporte: recibe un video y su `pose.npz`, y no sabe qué gesto
hay adentro. De `analysis.json`, si existe, lee sólo los cuadros de `address`,
`top` e `impact` para poder restar dos derivas; los nombres de esos eventos son
los del contrato, no los de golf.

## El método

Para cada cuadro muestreado se estima el movimiento del **fondo** respecto de un
cuadro de referencia:

1. **Enmascarar al sujeto**, que es lo único que tiene que moverse: el `bbox`
   de `pose.npz` dilatado (`--dilatacion`), más un disco centrado en las
   muñecas de radio `--palo-radio` × el alto del cuerpo, que cubre el palo
   —el bbox no lo incluye—. Cada imagen se enmascara con la máscara de **su**
   cuadro: un punto de fondo que el sujeto tapa en uno de los dos no llega a
   emparejarse.
2. **SIFT** en las dos imágenes enmascaradas, emparejamiento por fuerza bruta
   con el ratio test de Lowe (`--ratio`), y **homografía por RANSAC**
   (`--ransac-px`). La homografía va del cuadro de referencia al muestreado:
   `dx` positivo quiere decir que el fondo se corrió hacia la derecha.
3. **Evaluar el modelo en cuatro filas** de la imagen —caderas, hombros,
   cabeza y pies del sujeto en el cuadro de referencia— sobre la columna del
   sujeto. Son cuatro y no una porque el movimiento no es una traslación pura:
   medido en `cortado3-lento.mp4`, entre la fila de la cabeza y la de los pies
   hay 8–9 px de diferencia en el mismo cuadro.

## `no_rigido`: por qué el residuo solo no alcanza

`residuo_px` es la mediana del error de reproyección **de los inliers**, que es
lo que se suele reportar — y es un detector flojo de no-rigidez, porque RANSAC
declara inlier a lo que cae por debajo de `--ransac-px` y después reajusta
sobre ese subconjunto: el número está acotado por construcción. Medido sobre
los fondos sintéticos de `tests/test_camera_drift.py`, una deformación que
ninguna homografía puede seguir sube ese residuo de 0,00 a 1,98 px, mientras
que la **fracción de inliers** cae de 1,00 a 0,76. Lo que delata que una parte
de la escena no sigue al modelo —paralaje entre el suelo cercano y el fondo
lejano, rolling shutter, algo que se movió— es que RANSAC tenga que descartar
gente, no que le quede mal lo que se quedó.

Por eso `no_rigido` se marca cuando **cualquiera** de las dos se cumple:
`residuo_px > --umbral-no-rigido` o `inliers_frac < --umbral-inliers`. El campo
`no_rigido_por` dice cuál. Los dos umbrales son procedencia `estimacion`: no
salen de ningún barrido, se eligieron del orden de lo medido acá.

`residuo_global_px` —la mediana sobre **todos** los emparejamientos que pasaron
el ratio test— viaja al lado como dato; no decide nada.

Uso:
    python -m kinelab.tools.camera_drift VIDEO --pose POSE.npz \
        [--cada 10] [--ref FRAME] [--out camera-drift.json]

Los índices de cuadro son los del motor: se lee con el mismo `iter_frames` que
la percepción, así que el cuadro 1052 de acá es el 1052 de `pose.npz`.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np

from kinelab.perception.keypoints import H
from kinelab.perception.posestore import POSE_FILE, PoseData, finite_or_none, load_pose
from kinelab.perception.video import iter_frames
from kinelab.tools.fps_truth import FfprobeError, probe_declared
from kinelab.tools.interpolar import ascii_para_quemar

# Las cuatro filas, y con qué keypoints se define cada una. La cadera y la
# cabeza predichas por la red (índices 19 y 17 de Halpe26) no son centros
# articulares; para las caderas se usa el par real (11, 12) y para la cabeza sí
# el punto 17, que es el que anclan las métricas de cabeza. Acá son filas de la
# imagen donde evaluar un modelo, no medidas anatómicas.
FILAS: dict[str, tuple[int, ...]] = {
    "caderas": (H.LEFT_HIP, H.RIGHT_HIP),
    "hombros": (H.LEFT_SHOULDER, H.RIGHT_SHOULDER),
    "cabeza": (H.HEAD,),
    "pies": (H.LEFT_ANKLE, H.RIGHT_ANKLE),
}
# La columna donde se evalúan las cuatro filas: la mediana de x del tronco.
COLUMNA = (H.LEFT_SHOULDER, H.RIGHT_SHOULDER, H.LEFT_HIP, H.RIGHT_HIP)
EVENTOS = ("address", "top", "impact")
REGIONES = ("todo", "superior", "inferior")

DILATACION = 0.20            # el bbox del sujeto, dilatado esta fracción
PALO_RADIO_FRAC = 0.65       # radio del disco del palo, en altos de cuerpo
RATIO = 0.75                 # ratio test de Lowe
RANSAC_PX = 5.0              # umbral de inlier de RANSAC
UMBRAL_NO_RIGIDO_PX = 1.5    # procedencia: estimacion
UMBRAL_INLIERS_FRAC = 0.80   # procedencia: estimacion
MIN_INLIERS = 12
NFEATURES = 2000


class DriftError(RuntimeError):
    """El clip o la pose no se pueden leer, o el cuadro de referencia no existe."""


@dataclass(frozen=True)
class Params:
    dilatacion: float = DILATACION
    palo_radio_frac: float = PALO_RADIO_FRAC
    con_palo: bool = True
    region: str = "todo"
    ratio: float = RATIO
    ransac_px: float = RANSAC_PX
    umbral_no_rigido_px: float = UMBRAL_NO_RIGIDO_PX
    umbral_inliers_frac: float = UMBRAL_INLIERS_FRAC
    min_inliers: int = MIN_INLIERS
    nfeatures: int = NFEATURES

    def __post_init__(self) -> None:
        if self.region not in REGIONES:
            raise ValueError(f"--region tiene que ser una de {REGIONES}; llegó {self.region!r}")
        if not 0.0 < self.ratio < 1.0:
            raise ValueError("--ratio va entre 0 y 1 (el ratio test de Lowe)")
        if self.ransac_px <= 0 or self.umbral_no_rigido_px <= 0:
            raise ValueError("los umbrales en px tienen que ser positivos")
        if not 0.0 < self.umbral_inliers_frac <= 1.0:
            raise ValueError("--umbral-inliers es una fracción entre 0 y 1")
        if self.min_inliers < 4:
            raise ValueError("hacen falta al menos 4 inliers para una homografía")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["procedencia_umbrales_no_rigido"] = "estimacion"
        d["regla_no_rigido"] = "residuo_px > umbral_no_rigido_px o inliers_frac < umbral_inliers_frac"
        return d


# `eq=False` porque lleva arrays de numpy adentro: el `__eq__` generado los
# compararía elemento a elemento y levantaría "truth value is ambiguous".
@dataclass(frozen=True, eq=False)
class Modelo:
    """La homografía del fondo entre dos cuadros, con su calidad."""

    matriz: np.ndarray
    inliers: int
    coincidencias: int
    residuo_px: float
    residuo_global_px: float
    fuente: np.ndarray  # (n,2) puntos del cuadro de referencia, sólo inliers
    destino: np.ndarray  # (n,2) los mismos en el cuadro muestreado

    @property
    def inliers_frac(self) -> float:
        return self.inliers / self.coincidencias if self.coincidencias else 0.0

    def desplazamiento(self, columna: float, fila: float) -> tuple[float, float]:
        """`(dx, dy)` que el modelo induce en el punto `(columna, fila)`."""
        p = np.float32([[[columna, fila]]])
        q = cv2.perspectiveTransform(p, self.matriz)[0, 0]
        return float(q[0] - columna), float(q[1] - fila)

    def no_rigido(self, p: Params) -> tuple[bool, str | None]:
        """Si el fondo no se movió como un solo plano rígido, y por qué."""
        por = [n for n, mal in (("residuo", self.residuo_px > p.umbral_no_rigido_px),
                                ("inliers", self.inliers_frac < p.umbral_inliers_frac)) if mal]
        return bool(por), "+".join(por) or None


@dataclass(frozen=True)
class Muestra:
    frame: int
    filas: dict[str, dict[str, float | None]] | None
    residuo_px: float | None
    residuo_global_px: float | None
    inliers: int | None
    coincidencias: int | None
    inliers_frac: float | None
    no_rigido: bool | None
    no_rigido_por: str | None = None
    null_reason: str | None = None

    def dx(self, fila: str) -> float | None:
        return None if self.filas is None else self.filas[fila]["dx_px"]

    def dy(self, fila: str) -> float | None:
        return None if self.filas is None else self.filas[fila]["dy_px"]


@dataclass(frozen=True)
class Deriva:
    video: str
    pose: str
    frames: int
    ref: int
    ref_metodo: str
    columna_px: float
    alto_cuerpo_px: float
    filas_ref: dict[str, dict[str, float | str | None]]
    params: Params
    muestras: tuple[Muestra, ...]
    eventos: tuple[dict, ...]
    libre_frac_mediana: float
    segundos: float
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def con_modelo(self) -> tuple[Muestra, ...]:
        return tuple(m for m in self.muestras if m.filas is not None)

    def en(self, frame: int) -> Muestra | None:
        for m in self.muestras:
            if m.frame == frame:
                return m
        return None

    def resumen(self) -> dict:
        ok = self.con_modelo
        res: dict = {
            "cuadros_muestreados": len(self.muestras),
            "cuadros_con_modelo": len(ok),
            "cuadros_sin_modelo": len(self.muestras) - len(ok),
            "cuadros_no_rigidos": sum(1 for m in ok if m.no_rigido),
            "residuo_mediano_px": float(np.median([m.residuo_px for m in ok])) if ok else None,
            "residuo_global_mediano_px": float(np.median([m.residuo_global_px for m in ok])) if ok else None,
            "inliers_mediana": float(np.median([m.inliers for m in ok])) if ok else None,
            "inliers_frac_minima": float(min(m.inliers_frac for m in ok)) if ok else None,
            "libre_frac_mediana": self.libre_frac_mediana,
        }
        for eje, get in (("dx", Muestra.dx), ("dy", Muestra.dy)):
            peor: tuple[float, int, str] | None = None
            for m in ok:
                for nombre in FILAS:
                    v = get(m, nombre)
                    if v is not None and (peor is None or abs(v) > abs(peor[0])):
                        peor = (v, m.frame, nombre)
            res[f"max_abs_{eje}_px"] = (
                None if peor is None else {"value": peor[0], "frame": peor[1], "fila": peor[2]}
            )
        return res

    def to_dict(self) -> dict:
        return {
            "herramienta": "kinelab.tools.camera_drift",
            "video": self.video,
            "pose": self.pose,
            "frames": self.frames,
            "ref": self.ref,
            "ref_metodo": self.ref_metodo,
            "unidad": "px del cuadro como se ve (image_px, y hacia abajo)",
            "convencion": (
                "dx/dy es lo que la homografía del FONDO mueve el punto entre el cuadro de "
                "referencia y el muestreado: positivo = el fondo se corrió hacia la derecha / hacia abajo. "
                "Un desplazamiento del cuerpo medido en ese cuadro lleva esta deriva adentro."
            ),
            "procedencia_deriva": "medido_aqui",
            "columna_px": self.columna_px,
            "alto_cuerpo_px": self.alto_cuerpo_px,
            "filas_ref": self.filas_ref,
            "params": self.params.to_dict(),
            "resumen": self.resumen(),
            "eventos": list(self.eventos),
            "muestras": [asdict(m) for m in self.muestras],
            "segundos": self.segundos,
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------- máscara

def alto_cuerpo_px(pose: PoseData) -> float:
    """Alto del cuerpo en píxeles: mediana de cabeza → tobillos sobre el clip.

    Es una escala para el radio del palo, no la escala de las métricas en cm
    (ésa es `stature_chain_px`, CONTRATO §La escala). Si la cabeza o los
    tobillos no están en ningún cuadro, cae a la altura del `bbox`.
    """
    k = pose.keypoints
    tobillos = np.nanmean(k[:, [H.LEFT_ANKLE, H.RIGHT_ANKLE], 1], axis=1)
    alto = np.asarray(tobillos - k[:, H.HEAD, 1], dtype=float)
    alto = alto[np.isfinite(alto) & (alto > 0)]
    if alto.size:
        return float(np.median(alto))
    caja = np.asarray(pose.bbox[:, 3] - pose.bbox[:, 1], dtype=float)
    caja = caja[np.isfinite(caja) & (caja > 0)]
    if caja.size:
        return float(np.median(caja))
    raise DriftError("la pose no tiene ningún cuadro con alto de cuerpo medible")


def mascara(shape: tuple[int, int], pose: PoseData, frame: int, alto_px: float, p: Params) -> np.ndarray:
    """255 donde se buscan puntos de fondo, 0 donde no. Lo que se tapa es el
    sujeto (bbox dilatado) y el palo (disco sobre las muñecas)."""
    alto, ancho = shape[:2]
    m = np.full((alto, ancho), 255, np.uint8)
    caja = np.asarray(pose.bbox[frame], dtype=float)
    if np.isfinite(caja).all():
        cx, cy = (caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2
        hw, hh = (caja[2] - caja[0]) / 2 * (1 + p.dilatacion), (caja[3] - caja[1]) / 2 * (1 + p.dilatacion)
        cv2.rectangle(m, (int(np.floor(cx - hw)), int(np.floor(cy - hh))),
                      (int(np.ceil(cx + hw)), int(np.ceil(cy + hh))), 0, -1)
    if p.con_palo:
        muneca = np.nanmean(np.asarray(pose.keypoints[frame, [H.LEFT_WRIST, H.RIGHT_WRIST], :], dtype=float), axis=0)
        if np.isfinite(muneca).all():
            cv2.circle(m, (int(round(muneca[0])), int(round(muneca[1]))), int(round(p.palo_radio_frac * alto_px)), 0, -1)
    if p.region == "superior":
        m[alto // 2:] = 0
    elif p.region == "inferior":
        m[: alto // 2] = 0
    return m


# ---------------------------------------------------------------- modelo

def estimar(
    gris_ref: np.ndarray,
    mask_ref: np.ndarray,
    gris: np.ndarray,
    mask: np.ndarray,
    p: Params,
    *,
    sift: cv2.SIFT | None = None,
    ref_precomputado: tuple[Sequence, np.ndarray | None] | None = None,
) -> tuple[Modelo | None, str | None]:
    """La homografía del fondo de `gris_ref` a `gris`, o `(None, razón)`."""
    sift = sift or cv2.SIFT_create(nfeatures=p.nfeatures)
    kr, dr = ref_precomputado if ref_precomputado is not None else sift.detectAndCompute(gris_ref, mask_ref)
    ks, ds = sift.detectAndCompute(gris, mask)
    if dr is None or ds is None or len(kr) < 2 or len(ks) < 2:
        return None, f"SIFT encontró {0 if dr is None else len(kr)} y {0 if ds is None else len(ks)} puntos de fondo"
    # Ratio test de Lowe: un emparejamiento vale si el mejor candidato está
    # bastante más cerca que el segundo. Sin él, cada punto encuentra alguno.
    buenos = [par[0] for par in cv2.BFMatcher().knnMatch(dr, ds, k=2)
              if len(par) == 2 and par[0].distance < p.ratio * par[1].distance]
    if len(buenos) < p.min_inliers:
        return None, f"{len(buenos)} emparejamientos pasaron el ratio test y hacen falta {p.min_inliers}"
    src = np.float32([kr[a.queryIdx].pt for a in buenos]).reshape(-1, 1, 2)
    dst = np.float32([ks[a.trainIdx].pt for a in buenos]).reshape(-1, 1, 2)
    matriz, inl = cv2.findHomography(src, dst, cv2.RANSAC, p.ransac_px)
    if matriz is None or inl is None:
        return None, f"RANSAC no encontró homografía con {len(buenos)} emparejamientos"
    dentro = inl.ravel().astype(bool)
    if int(dentro.sum()) < p.min_inliers:
        return None, f"{int(dentro.sum())} inliers y hacen falta {p.min_inliers}"
    err = np.linalg.norm(cv2.perspectiveTransform(src, matriz) - dst, axis=2).ravel()
    return Modelo(
        matriz=matriz,
        inliers=int(dentro.sum()),
        coincidencias=len(buenos),
        residuo_px=float(np.median(err[dentro])),
        residuo_global_px=float(np.median(err)),
        fuente=src.reshape(-1, 2)[dentro],
        destino=dst.reshape(-1, 2)[dentro],
    ), None


def filas_de(pose: PoseData, frame: int) -> dict[str, dict[str, float | str | None]]:
    """La fila de imagen de cada parte en `frame`, o `null` con su razón."""
    out: dict[str, dict[str, float | str | None]] = {}
    for nombre, idx in FILAS.items():
        ys = np.asarray(pose.keypoints[frame, list(idx), 1], dtype=float)
        if np.isfinite(ys).all():
            out[nombre] = {"y_px": float(np.mean(ys)), "null_reason": None}
        else:
            out[nombre] = {"y_px": None, "null_reason": f"keypoints {idx} sin valor en el cuadro de referencia {frame}"}
    return out


def columna_de(pose: PoseData, frame: int) -> float | None:
    xs = np.asarray(pose.keypoints[frame, list(COLUMNA), 0], dtype=float)
    xs = xs[np.isfinite(xs)]
    if xs.size:
        return float(np.median(xs))
    caja = np.asarray(pose.bbox[frame], dtype=float)
    return float((caja[0] + caja[2]) / 2) if np.isfinite(caja).all() else None


def primer_cuadro_con_pose(pose: PoseData) -> tuple[int, str]:
    """El cuadro por defecto de `--ref`: el primero con `bbox` y las cuatro filas."""
    caja_ok = np.isfinite(np.asarray(pose.bbox, dtype=float)).all(axis=1)
    for i in np.flatnonzero(caja_ok):
        if all(v["y_px"] is not None for v in filas_de(pose, int(i)).values()):
            return int(i), "primer cuadro con bbox y las cuatro filas"
    if caja_ok.any():
        return int(np.flatnonzero(caja_ok)[0]), "primer cuadro con bbox (alguna fila queda en null)"
    raise DriftError("la pose no tiene ningún cuadro con bbox: no hay cuadro de referencia posible")


# ---------------------------------------------------------------- eventos

def leer_eventos(path: Path | None) -> tuple[tuple[dict, ...], str | None]:
    """`events[]` de un `analysis.json`, sólo `address`, `top` e `impact`."""
    if path is None or not path.is_file():
        return (), None
    try:
        datos = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return (), f"no se pudo leer {path}: {e}"
    reps: list[dict] = []
    for ev in datos.get("events") or []:
        fila = {"rep": ev.get("rep")}
        for nombre in EVENTOS:
            v = ev.get(nombre)
            fila[nombre] = v.get("frame") if isinstance(v, dict) else None
        reps.append(fila)
    return tuple(reps), None


def _resta(a: Muestra | None, b: Muestra | None) -> tuple[dict | None, str | None]:
    """`deriva(b) − deriva(a)` por fila: cuánto se corrió la imagen entre los dos."""
    if a is None or b is None:
        return None, "uno de los dos cuadros del evento no está muestreado"
    if a.filas is None or b.filas is None:
        sin = a if a.filas is None else b
        return None, f"sin modelo en el cuadro {sin.frame}: {sin.null_reason}"
    out: dict[str, dict[str, float | None]] = {}
    for nombre in FILAS:
        dxa, dxb, dya, dyb = a.dx(nombre), b.dx(nombre), a.dy(nombre), b.dy(nombre)
        out[nombre] = {
            "dx_px": None if dxa is None or dxb is None else dxb - dxa,
            "dy_px": None if dya is None or dyb is None else dyb - dya,
        }
    return out, None


def entre_eventos(deriva_muestras: dict[int, Muestra], reps: Iterable[dict]) -> tuple[dict, ...]:
    out = []
    for rep in reps:
        a, t, i = rep.get("address"), rep.get("top"), rep.get("impact")
        fila = dict(rep)
        for clave, hasta in (("address_a_top", t), ("address_a_impacto", i)):
            if a is None or hasta is None:
                fila[clave], fila[f"{clave}_null_reason"] = None, "la repetición no tiene los dos eventos"
                continue
            valor, razon = _resta(deriva_muestras.get(a), deriva_muestras.get(hasta))
            fila[clave], fila[f"{clave}_null_reason"] = valor, razon
        out.append(fila)
    return tuple(out)


# ---------------------------------------------------------------- corrida

def _pose_dir(pose: Path) -> Path:
    return pose.parent if pose.name == POSE_FILE else pose


def _leer(video: Path, rotacion: int, display: tuple[int, int], quiero: set[int], hasta: int | None = None) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    tope = max(quiero) if hasta is None else hasta
    for i, f in iter_frames(video, rotation_deg=rotacion, display_size=display):
        if i in quiero:
            out[i] = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if f.ndim == 3 else f
        if i >= tope:
            break
    return out


def correr(
    video: Path,
    pose_path: Path,
    *,
    cada: int = 10,
    ref: int | None = None,
    params: Params | None = None,
    analisis: Path | None = None,
    sin_analisis: bool = False,
    dibujar: Sequence[int] = (),
    out_dir: Path | None = None,
    progreso=None,
) -> tuple[Deriva, list[Path]]:
    p = params or Params()
    t0 = time.time()
    pose_dir = _pose_dir(Path(pose_path))
    pose = load_pose(pose_dir)
    total = int(pose.keypoints.shape[0])
    if cada < 1:
        raise DriftError("--cada tiene que ser 1 o más")
    try:
        d = probe_declared(video)
    except FfprobeError as e:
        raise DriftError(str(e)) from e
    warnings: list[str] = []

    if ref is None:
        ref, ref_metodo = primer_cuadro_con_pose(pose)
    else:
        ref_metodo = "pedido con --ref"
        if not 0 <= ref < total:
            raise DriftError(f"--ref {ref} queda fuera de los {total} cuadros de la pose")

    if sin_analisis:
        reps, aviso = (), None
    else:
        reps, aviso = leer_eventos(analisis if analisis is not None else pose_dir / "analysis.json")
    if aviso:
        warnings.append(aviso)

    cuadros_evento = {f for rep in reps for f in (rep.get(n) for n in EVENTOS) if isinstance(f, int) and 0 <= f < total}
    pedidos = {f for f in dibujar if 0 <= f < total}
    muestreo = sorted({*range(0, total, cada), ref, *cuadros_evento, *pedidos})

    alto_px = alto_cuerpo_px(pose)
    columna = columna_de(pose, ref)
    if columna is None:
        raise DriftError(f"el cuadro de referencia {ref} no tiene columna del sujeto (ni keypoints ni bbox)")
    filas_ref = filas_de(pose, ref)
    for nombre, v in filas_ref.items():
        if v["y_px"] is None:
            warnings.append(f"la fila «{nombre}» queda en null: {v['null_reason']}")

    display = d.display_size
    grises_ref = _leer(video, d.rotation_deg, display, {ref})
    if ref not in grises_ref:
        raise DriftError(f"{video}: el cuadro de referencia {ref} no se pudo decodificar")
    gris_ref = grises_ref[ref]
    if gris_ref.shape[:2] != (display[1], display[0]):
        warnings.append(f"el cuadro decodificado mide {gris_ref.shape[1]}x{gris_ref.shape[0]} y el contenedor declara {display[0]}x{display[1]}")
    mask_ref = mascara(gris_ref.shape, pose, ref, alto_px, p)
    sift = cv2.SIFT_create(nfeatures=p.nfeatures)
    ref_pre = sift.detectAndCompute(gris_ref, mask_ref)

    muestras: list[Muestra] = []
    libres: list[float] = []
    dibujos: list[Path] = []
    salida_dir = out_dir or pose_dir
    pendientes = set(muestreo)
    hecho = 0
    for i, frame in iter_frames(video, rotation_deg=d.rotation_deg, display_size=display):
        if i not in pendientes:
            continue
        pendientes.discard(i)
        gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        m = mascara(gris.shape, pose, i, alto_px, p)
        libres.append(float(m.mean()) / 255.0)
        modelo, razon = estimar(gris_ref, mask_ref, gris, m, p, sift=sift, ref_precomputado=ref_pre)
        if modelo is None:
            muestras.append(Muestra(i, None, None, None, None, None, None, None, None, razon))
        else:
            filas = {
                nombre: dict(zip(("dx_px", "dy_px"), modelo.desplazamiento(columna, float(v["y_px"]))))
                if v["y_px"] is not None else {"dx_px": None, "dy_px": None}
                for nombre, v in filas_ref.items()
            }
            flojo, por = modelo.no_rigido(p)
            muestras.append(Muestra(
                frame=i, filas=filas, residuo_px=modelo.residuo_px, residuo_global_px=modelo.residuo_global_px,
                inliers=modelo.inliers, coincidencias=modelo.coincidencias, inliers_frac=modelo.inliers_frac,
                no_rigido=flojo, no_rigido_por=por, null_reason=None,
            ))
        if i in pedidos:
            dibujos.append(_dibujar(salida_dir, video, gris, m, modelo, muestras[-1], columna, filas_ref, ref, p))
        hecho += 1
        if progreso is not None:
            progreso(hecho, len(muestreo))
        if not pendientes:
            break
    if pendientes:
        warnings.append(f"{len(pendientes)} cuadro(s) del muestreo no se decodificaron (el clip entregó menos cuadros que la pose): {sorted(pendientes)[:5]}…")

    por_cuadro = {m.frame: m for m in muestras}
    deriva = Deriva(
        video=str(video), pose=str(pose_dir / POSE_FILE), frames=total, ref=ref, ref_metodo=ref_metodo,
        columna_px=columna, alto_cuerpo_px=alto_px, filas_ref=filas_ref, params=p,
        muestras=tuple(muestras), eventos=entre_eventos(por_cuadro, reps),
        libre_frac_mediana=float(np.median(libres)) if libres else 0.0,
        segundos=time.time() - t0, warnings=tuple(warnings),
    )
    return deriva, dibujos


# ---------------------------------------------------------------- dibujo

def _dibujar(
    out_dir: Path, video: Path, gris: np.ndarray, mask: np.ndarray, modelo: Modelo | None,
    muestra: Muestra, columna: float, filas_ref: dict, ref: int, p: Params,
) -> Path:
    """El cuadro con el fondo enmascarado a la vista y los inliers dibujados.

    Es para mirar, no para medir: el desplazamiento de las cuatro filas se
    dibuja amplificado ×10 porque 20 px en un cuadro de 1920 no se ven.
    """
    img = cv2.cvtColor(gris, cv2.COLOR_GRAY2BGR)
    img[mask == 0] = (img[mask == 0] * 0.35).astype(np.uint8)
    if modelo is not None:
        for (x0, y0), (x1, y1) in zip(modelo.fuente, modelo.destino):
            cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)), (120, 240, 120), 1, cv2.LINE_AA)
            cv2.circle(img, (int(x1), int(y1)), 2, (60, 220, 60), -1, cv2.LINE_AA)
    amp = 10
    for nombre, v in filas_ref.items():
        if v["y_px"] is None or muestra.filas is None:
            continue
        y = float(v["y_px"])
        dx, dy = muestra.filas[nombre]["dx_px"], muestra.filas[nombre]["dy_px"]
        cv2.line(img, (0, int(y)), (img.shape[1], int(y)), (200, 120, 255), 1, cv2.LINE_AA)
        cv2.arrowedLine(img, (int(columna), int(y)), (int(columna + amp * dx), int(y + amp * dy)),
                        (255, 80, 255), 3, cv2.LINE_AA, tipLength=0.25)
        _rotulo(img, f"{nombre} dx {dx:+.1f} dy {dy:+.1f} px (flecha x{amp})", 10, int(y) - 8, (255, 80, 255))
    cabecera = [
        f"{video.name} · cuadro {muestra.frame} vs ref {ref} · region {p.region}",
        (f"inliers {muestra.inliers}/{muestra.coincidencias} · residuo {muestra.residuo_px:.2f} px · "
         f"no_rigido {muestra.no_rigido}")
        if modelo is not None else f"sin modelo: {muestra.null_reason}",
        "verde: fondo usado · lo oscuro esta enmascarado",
        "para mirar, no para medir",
    ]
    # La escala sale de la línea más larga: una cabecera cortada no sirve.
    fs = _escala_al_ancho(cabecera, img.shape[1] - 20)
    alto_linea = int(cv2.getTextSize("Hg", cv2.FONT_HERSHEY_SIMPLEX, fs, 1)[0][1] * 2.0)
    for j, linea in enumerate(cabecera):
        _rotulo(img, linea, 10, alto_linea * (j + 1), (255, 255, 255), fs)
    destino = out_dir / f"camera-drift-{muestra.frame}.png"
    if not cv2.imwrite(str(destino), img):
        raise DriftError(f"no se pudo escribir {destino}")
    return destino


def _escala_al_ancho(lineas: Sequence[str], ancho: int) -> float:
    """La escala de fuente más grande con la que la línea más larga entra."""
    largo = max((cv2.getTextSize(ascii_para_quemar(t), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 1)[0][0] for t in lineas), default=1)
    return float(max(0.35, min(1.2, ancho / largo if largo else 1.0)))


def _rotulo(img: np.ndarray, texto: str, x: int, y: int, color, fs: float | None = None) -> None:
    t = ascii_para_quemar(texto)
    fs = fs if fs is not None else max(0.5, img.shape[0] / 1800.0)
    cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, color, 1, cv2.LINE_AA)


# ---------------------------------------------------------------- CLI

def format_human(d: Deriva) -> str:
    r = d.resumen()
    lin = [
        d.video,
        f"  pose {d.pose} · {d.frames} cuadros · referencia {d.ref} ({d.ref_metodo})",
        f"  columna del sujeto {d.columna_px:.1f} px · alto de cuerpo {d.alto_cuerpo_px:.0f} px · "
        f"fondo libre {100 * d.libre_frac_mediana:.1f} % del cuadro · region {d.params.region}",
        f"  {r['cuadros_con_modelo']}/{r['cuadros_muestreados']} cuadros con modelo · "
        f"inliers mediana {r['inliers_mediana']} · residuo inliers {r['residuo_mediano_px']:.2f} px · "
        f"global {r['residuo_global_mediano_px']:.2f} px · no_rigido en {r['cuadros_no_rigidos']}"
        if r["cuadros_con_modelo"] else "  ningun cuadro con modelo",
    ]
    for eje in ("dx", "dy"):
        v = r[f"max_abs_{eje}_px"]
        lin.append(f"  max |{eje}| {v['value']:+.2f} px en el cuadro {v['frame']}, fila {v['fila']}" if v else f"  max |{eje}|: sin datos")
    for ev in d.eventos:
        for clave, rot in (("address_a_top", "address→top"), ("address_a_impacto", "address→impacto")):
            val = ev.get(clave)
            if val is None:
                lin.append(f"  rep {ev['rep']} {rot}: null — {ev.get(clave + '_null_reason')}")
            else:
                partes = " · ".join(
                    f"{n} {val[n]['dx_px']:+.1f}/{val[n]['dy_px']:+.1f}" if val[n]["dx_px"] is not None else f"{n} null"
                    for n in FILAS
                )
                lin.append(f"  rep {ev['rep']} {rot} (dx/dy px): {partes}")
    for w in d.warnings:
        lin.append(f"  aviso: {w}")
    lin.append(f"  {d.segundos:.1f} s")
    return "\n".join(lin)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m kinelab.tools.camera_drift",
        description="Cuánto se corre la imagen durante el gesto, medido sobre el fondo con el sujeto enmascarado. No compensa nada.",
    )
    ap.add_argument("video", type=Path)
    ap.add_argument("--pose", type=Path, required=True, help="pose.npz (o la carpeta que lo contiene)")
    ap.add_argument("--cada", type=int, default=10, help="muestrear un cuadro cada N (por defecto 10)")
    ap.add_argument("--ref", type=int, default=None, help="cuadro de referencia (por defecto el primero con pose)")
    ap.add_argument("--out", type=Path, default=None, help="archivo JSON de salida (por defecto camera-drift.json junto a la pose)")
    ap.add_argument("--dilatacion", type=float, default=DILATACION, help=f"cuánto se dilata el bbox del sujeto (por defecto {DILATACION})")
    ap.add_argument("--palo-radio", type=float, default=PALO_RADIO_FRAC, help=f"radio del disco del palo, en altos de cuerpo (por defecto {PALO_RADIO_FRAC})")
    ap.add_argument("--sin-palo", action="store_true", help="no enmascarar el palo (control: cuánto cambia el número)")
    ap.add_argument("--region", choices=REGIONES, default="todo", help="mitad de la imagen donde buscar fondo (control de paralaje)")
    ap.add_argument("--ratio", type=float, default=RATIO, help=f"ratio test de Lowe (por defecto {RATIO})")
    ap.add_argument("--ransac-px", type=float, default=RANSAC_PX, help=f"umbral de inlier de RANSAC en px (por defecto {RANSAC_PX})")
    ap.add_argument("--umbral-no-rigido", type=float, default=UMBRAL_NO_RIGIDO_PX, help=f"px de residuo de los inliers por encima del cual se marca no_rigido (procedencia estimacion; por defecto {UMBRAL_NO_RIGIDO_PX})")
    ap.add_argument("--umbral-inliers", type=float, default=UMBRAL_INLIERS_FRAC, help=f"fracción de inliers por debajo de la cual se marca no_rigido (procedencia estimacion; por defecto {UMBRAL_INLIERS_FRAC})")
    ap.add_argument("--min-inliers", type=int, default=MIN_INLIERS, help=f"inliers mínimos para aceptar una homografía (por defecto {MIN_INLIERS})")
    ap.add_argument("--nfeatures", type=int, default=NFEATURES, help=f"tope de puntos SIFT por imagen (por defecto {NFEATURES})")
    ap.add_argument("--analisis", type=Path, default=None, help="analysis.json del que leer los eventos (por defecto el que está junto a la pose)")
    ap.add_argument("--sin-analisis", action="store_true", help="no leer eventos de ningún analysis.json")
    ap.add_argument("--dibujar", type=int, action="append", default=[], metavar="FRAME", help="escribir camera-drift-FRAME.png con el fondo enmascarado y los inliers (repetible)")
    args = ap.parse_args(argv)

    if not args.video.exists():
        print(f"no existe: {args.video}", file=sys.stderr)
        return 2

    def progreso(i: int, total: int) -> None:
        print(f"\r  cuadro {i}/{total}", end="", flush=True)

    try:
        p = Params(
            dilatacion=args.dilatacion, palo_radio_frac=args.palo_radio, con_palo=not args.sin_palo,
            region=args.region, ratio=args.ratio, ransac_px=args.ransac_px,
            umbral_no_rigido_px=args.umbral_no_rigido, umbral_inliers_frac=args.umbral_inliers,
            min_inliers=args.min_inliers, nfeatures=args.nfeatures,
        )
        salida = args.out or _pose_dir(args.pose) / "camera-drift.json"
        d, dibujos = correr(
            args.video, args.pose, cada=args.cada, ref=args.ref, params=p, analisis=args.analisis,
            sin_analisis=args.sin_analisis, dibujar=args.dibujar, out_dir=salida.parent, progreso=progreso,
        )
    except (DriftError, FileNotFoundError, ValueError) as e:
        print(f"\nerror: {e}", file=sys.stderr)
        return 2
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(finite_or_none(d.to_dict()), indent=2, ensure_ascii=False), encoding="utf-8")
    print("\r" + format_human(d))
    print(f"  {salida}")
    for x in dibujos:
        print(f"  {x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
