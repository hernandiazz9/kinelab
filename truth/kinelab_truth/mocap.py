"""Un swing de mocap REAL (CMU) visto por la cámara virtual del arnés.

    python -m kinelab_truth.mocap 64_01 --vista face_on --out DIR

Nivel 1 de ADR-009: movimiento humano real, licencia libre, sin estimador de
pose en el medio. Lo que entra son los archivos ASF/AMC de
`data/examples/cmu-mocap/` (ver su `ATRIBUCION.md`); lo que sale es un
`pose.npz` con los 26 puntos Halpe26 en píxeles, como si una cámara vertical de
1080×1920 hubiera filmado al sujeto ocupando el 80 % del alto del cuadro.

**No es un video y no es una referencia.** Es un ejemplo para mirar la
herramienta andar sobre un swing que no es el de Hernán, y el primer dato con
el que comparar una métrica 2-D contra una verdad 3-D de un humano. Cada
archivo que sale de acá lo dice: en el `provenance` del `pose.npz`, en el
`fps_source` del `capture.json`, en `warnings[0]` del `analysis.json` y quemado
en cada cuadro del `overlay.mp4`.

Lo que hay que saber del formato (documentado por CMU en mocap.cs.cmu.edu):

- El ASF trae el esqueleto: por hueso, su dirección en la pose de reposo (en
  coordenadas de mundo), su largo, el sistema de ejes local (`axis`, Euler) y
  qué grados de libertad trae el AMC. El AMC trae, por cuadro, la traslación y
  rotación de la raíz y los ángulos de cada hueso, en grados.
- **Los largos están en pulgadas multiplicadas por `:units length` (0,45).**
  A metros: `× 0,0254 / 0,45`. Vale para los largos de hueso y para la posición
  de la raíz (FAQ de CMU).
- Mundo del ASF: **y hacia arriba**; en la pose de reposo el sujeto mira a +z y
  su izquierda es +x. Los ángulos de Euler van en orden X, Y, Z: la matriz es
  `Rz · Ry · Rx`.
- Cinemática directa, por hueso `b` con padre `p`:
  `L_b = L_p · C_b · R_b · C_b⁻¹` y `pos_b = pos_p + L_b · (dir_b · largo_b)`,
  donde `C_b` es el `axis` del hueso y `R_b` los ángulos del cuadro. La
  posición de un hueso es su **extremo**: `lfemur` termina en la rodilla.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from kinelab.perception.keypoints import H, HALPE26_NAMES, J

INCH_M = 0.0254
CMU_FPS = 120.0  # tasa de captura del sistema Vicon de CMU, declarada por ellos (no medida acá)
EXAMPLES = Path(__file__).resolve().parents[2] / "data" / "examples" / "cmu-mocap"


# --- ASF / AMC ---------------------------------------------------------------


@dataclass(frozen=True)
class Bone:
    """Un hueso del ASF. `direction` es unitario en el mundo de reposo; `length`
    en unidades del archivo; `axis_deg` son los ángulos del sistema local."""

    name: str
    direction: np.ndarray
    length: float
    axis_deg: np.ndarray
    dof: tuple[str, ...]


@dataclass
class Skeleton:
    units_length: float
    bones: dict[str, Bone]
    children: dict[str, list[str]] = field(default_factory=dict)

    @property
    def scale_m(self) -> float:
        """Unidades del archivo → metros (FAQ de CMU: pulgadas × `:units length`)."""
        return INCH_M / self.units_length


def _clean(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def parse_asf(text: str) -> Skeleton:
    """Esqueleto desde el texto de un `.asf`. Sólo lo que hace falta para la
    cinemática: unidades, huesos y jerarquía (los `limits` se ignoran a
    propósito: el AMC ya viene dentro de ellos y recortar sería inventar)."""
    lines = _clean(text)
    units_length = 1.0
    bones: dict[str, Bone] = {}
    children: dict[str, list[str]] = {}
    section = None
    cur: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if line.startswith(":"):
            section = line[1:].split()[0]
            continue
        if section == "units":
            k, *v = line.split()
            if k == "length":
                units_length = float(v[0])
        elif section == "bonedata":
            if line == "begin":
                cur = {}
            elif line == "end":
                bones[cur["name"]] = Bone(
                    name=cur["name"],
                    direction=np.asarray(cur["direction"], float),
                    length=float(cur["length"]),
                    axis_deg=np.asarray(cur["axis"], float),
                    dof=tuple(cur.get("dof", ())),
                )
            else:
                k, *v = line.split()
                if k == "name":
                    cur["name"] = v[0]
                elif k == "direction":
                    cur["direction"] = [float(x) for x in v[:3]]
                elif k == "length":
                    cur["length"] = float(v[0])
                elif k == "axis":
                    cur["axis"] = [float(x) for x in v[:3]]
                    order = v[3] if len(v) > 3 else "XYZ"
                    if order.upper() != "XYZ":
                        raise ValueError(f"{cur.get('name')}: orden de ejes {order}; este parser sólo hace XYZ")
                elif k == "dof":
                    cur["dof"] = [d.lower() for d in v]
        elif section == "hierarchy" and line not in ("begin", "end"):
            parent, *kids = line.split()
            children.setdefault(parent, []).extend(kids)
    if "root" not in children:
        raise ValueError("el ASF no declara jerarquía desde `root`")
    return Skeleton(units_length=units_length, bones=bones, children=children)


_FRAME_NO = re.compile(r"^\d+$")


def parse_amc(text: str) -> list[dict[str, list[float]]]:
    """Un dict por cuadro: nombre de hueso → sus ángulos (la raíz, 3 traslaciones
    y 3 rotaciones). Se exige que los números de cuadro sean 1, 2, 3…: un salto
    sería un hueco de tiempo y acá no hay forma de representarlo."""
    frames: list[dict[str, list[float]]] = []
    cur: dict[str, list[float]] | None = None
    for line in _clean(text):
        if line.startswith(":"):
            continue
        if _FRAME_NO.match(line):
            n = int(line)
            if n != len(frames) + 1:
                raise ValueError(f"el AMC salta del cuadro {len(frames)} al {n}: la línea de tiempo tiene un hueco")
            cur = {}
            frames.append(cur)
            continue
        if cur is None:
            continue  # encabezado (`#!OML:ASF …`)
        name, *vals = line.split()
        cur[name] = [float(v) for v in vals]
    if not frames:
        raise ValueError("el AMC no tiene ningún cuadro")
    return frames


def euler_xyz(rx: float, ry: float, rz: float) -> np.ndarray:
    """Matriz de los ángulos de Euler del ASF, en grados: `Rz · Ry · Rx`."""
    x, y, z = np.radians([rx, ry, rz])
    cx, sx, cy, sy, cz, sz = np.cos(x), np.sin(x), np.cos(y), np.sin(y), np.cos(z), np.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _bone_rotation(bone: Bone, values: list[float]) -> np.ndarray:
    """Los ángulos del cuadro para este hueso, en el orden de su `dof`."""
    ang = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
    if len(values) != len(bone.dof):
        raise ValueError(f"{bone.name}: el AMC trae {len(values)} valores y el ASF declara {len(bone.dof)} ({', '.join(bone.dof)})")
    for name, v in zip(bone.dof, values):
        if name not in ang:
            raise ValueError(f"{bone.name}: grado de libertad {name!r} no soportado (sólo rx, ry, rz)")
        ang[name] = v
    return euler_xyz(ang["rx"], ang["ry"], ang["rz"])


def forward_kinematics(skel: Skeleton, frames: list[dict[str, list[float]]]) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """`(posiciones, rotaciones)`: por hueso, el extremo en metros `(T,3)` y la
    matriz que lleva una dirección de la pose de reposo a la del cuadro `(T,3,3)`.

    `root` es la posición de la raíz (centro de la pelvis) y su rotación."""
    T = len(frames)
    names = ["root", *skel.bones]
    pos = {n: np.full((T, 3), np.nan) for n in names}
    rot = {n: np.full((T, 3, 3), np.nan) for n in names}
    scale = skel.scale_m
    C = {b.name: euler_xyz(*b.axis_deg) for b in skel.bones.values()}
    Cinv = {k: np.linalg.inv(v) for k, v in C.items()}
    for t, f in enumerate(frames):
        if "root" not in f or len(f["root"]) != 6:
            raise ValueError(f"cuadro {t + 1}: la raíz necesita 6 valores (TX TY TZ RX RY RZ)")
        pos["root"][t] = np.asarray(f["root"][:3], float) * scale
        rot["root"][t] = euler_xyz(*f["root"][3:])
        stack = [("root", n) for n in skel.children.get("root", ())]
        while stack:
            parent, name = stack.pop()
            bone = skel.bones[name]
            R = _bone_rotation(bone, f.get(name, [])) if bone.dof else np.eye(3)
            L = rot[parent][t] @ C[name] @ R @ Cinv[name]
            rot[name][t] = L
            pos[name][t] = pos[parent][t] + L @ (bone.direction * bone.length * scale)
            stack += [(name, k) for k in skel.children.get(name, ())]
    return pos, rot


# --- CMU → Halpe26 -----------------------------------------------------------

# Los 16 puntos que son la MISMA articulación en los dos esqueletos: el extremo
# del hueso de CMU es el centro articular que Halpe26 nombra.
DIRECT: dict[int, str] = {
    H.LEFT_HIP: "lhipjoint", H.RIGHT_HIP: "rhipjoint",
    H.LEFT_KNEE: "lfemur", H.RIGHT_KNEE: "rfemur",
    H.LEFT_ANKLE: "ltibia", H.RIGHT_ANKLE: "rtibia",
    H.LEFT_SHOULDER: "lclavicle", H.RIGHT_SHOULDER: "rclavicle",
    H.LEFT_ELBOW: "lhumerus", H.RIGHT_ELBOW: "rhumerus",
    H.LEFT_WRIST: "lradius", H.RIGHT_WRIST: "rradius",
    H.LEFT_BIG_TOE: "ltoes", H.RIGHT_BIG_TOE: "rtoes",
    H.HEAD: "head", H.NECK: "thorax",
}

# Los diez que NO existen en el esqueleto de CMU y se construyen. Cada
# aproximación está atada a una medida del propio sujeto (el largo del hueso de
# la cabeza, la distancia tobillo→planta), nunca a una constante en metros.
APPROX_NOTES: dict[str, str] = {
    "hip": "punto medio de las dos caderas. En un clip real este punto lo PREDICE la red y no es un centro articular (AGENTS.md); acá es el medio exacto, así que el ejemplo lo tiene mejor que un video.",
    "neck": "extremo del hueso `thorax`: la base del cuello, donde nacen las dos clavículas. Halpe26 lo predice entre los hombros.",
    "head": "extremo del hueso `head` de CMU: la coronilla. Es el punto con el que el motor mide la altura del cuerpo.",
    "cara": "nariz, ojos y orejas no existen en el esqueleto de CMU: se dibujan rígidos sobre el hueso de la cabeza, con su propio largo `hs` como escala (nariz 1,0·hs adelante; ojos 0,7·hs adelante y ±0,3·hs al costado; orejas ±0,7·hs al costado). Sirven para dibujar; ninguna métrica los usa.",
    "talones": "no existen: el talón queda detrás del tobillo, a 0,45 de la distancia horizontal tobillo→planta del pie, a la altura de la planta.",
    "puntas": "`ltoes`/`rtoes` dan la punta grande. La chica se corre 0,25 de esa distancia hacia AFUERA del cuerpo, en horizontal.",
}


def to_halpe26(pos: dict[str, np.ndarray], rot: dict[str, np.ndarray]) -> np.ndarray:
    """Los 26 puntos Halpe26 en metros `(T,26,3)`, en el mundo del ASF.

    Ver `APPROX_NOTES` por lo que no existe en CMU y se construye."""
    T = pos["root"].shape[0]
    P = np.full((T, J, 3), np.nan)
    for idx, bone in DIRECT.items():
        P[:, idx] = pos[bone]
    P[:, H.HIP] = (pos["lhipjoint"] + pos["rhipjoint"]) / 2.0
    # cara: marco rígido del hueso de la cabeza. En la pose de reposo del ASF el
    # sujeto mira a +z y su izquierda es +x, así que la rotación del hueso lleva
    # esos dos ejes a los del cuadro.
    head_base, head_top = pos["upperneck"], pos["head"]
    hs = np.linalg.norm(head_top - head_base, axis=1)[:, None]
    fwd = np.einsum("tij,j->ti", rot["head"], np.array([0.0, 0.0, 1.0]))
    lat = np.einsum("tij,j->ti", rot["head"], np.array([1.0, 0.0, 0.0]))  # +x = izquierda del sujeto
    P[:, H.NOSE] = head_base + 0.25 * (head_top - head_base) + 1.0 * hs * fwd
    P[:, H.LEFT_EYE] = head_base + 0.35 * (head_top - head_base) + 0.7 * hs * fwd + 0.3 * hs * lat
    P[:, H.RIGHT_EYE] = head_base + 0.35 * (head_top - head_base) + 0.7 * hs * fwd - 0.3 * hs * lat
    P[:, H.LEFT_EAR] = head_base + 0.30 * (head_top - head_base) + 0.7 * hs * lat
    P[:, H.RIGHT_EAR] = head_base + 0.30 * (head_top - head_base) - 0.7 * hs * lat
    up = np.array([0.0, 1.0, 0.0])
    mid_hip = P[:, H.HIP]
    for side, ankle, ball, toe, heel, small in (
        (1, "ltibia", "lfoot", H.LEFT_BIG_TOE, H.LEFT_HEEL, H.LEFT_SMALL_TOE),
        (-1, "rtibia", "rfoot", H.RIGHT_BIG_TOE, H.RIGHT_HEEL, H.RIGHT_SMALL_TOE),
    ):
        a, b = pos[ankle], pos[ball]
        step = b - a
        flat = step - (step @ up)[:, None] * up  # tobillo → planta, en horizontal
        n = np.linalg.norm(flat, axis=1)[:, None]
        fwd_foot = np.divide(flat, n, out=np.zeros_like(flat), where=n > 1e-9)
        drop = np.zeros_like(a)
        drop[:, 1] = b[:, 1] - a[:, 1]  # el talón apoya a la altura de la planta, no del tobillo
        P[:, heel] = a - 0.45 * n * fwd_foot + drop
        out = np.cross(up, fwd_foot)  # perpendicular horizontal; el signo se elige mirando al otro pie
        away = np.sign(np.sum(out * (a - mid_hip), axis=1))[:, None]
        away[away == 0] = 1.0
        P[:, small] = P[:, toe] + 0.25 * n * out * away
    return P


# --- del mundo del ASF al mundo del arnés ------------------------------------


# Cadena vertical de la estatura: del tobillo a la coronilla. La raíz queda por
# ENCIMA de las caderas (el hueso `lhipjoint` baja), así que su tramo se cuenta
# con la componente vertical de ese hueso en la pose de reposo.
STATURE_CHAIN = ("ltibia", "lfemur", "lowerback", "upperback", "thorax", "lowerneck", "upperneck", "head")


def stature_m(skel: Skeleton) -> float:
    """Estatura del sujeto de pie, desde los largos de hueso del ASF: altura del
    tobillo + tibia + fémur + (caderas→raíz) + columna + cuello + cabeza, todo
    puesto vertical.

    Sale del esqueleto y no del trial, así que no depende de qué cuadros entraron
    al clip. Queda un poco corta respecto de una estatura real: el modelo de CMU
    apoya el pie plano y deja el tobillo a ~4 cm del suelo, contra los ~7 cm de
    un tobillo humano. Es la **altura declarada** del atleta, la que el motor usa
    para pasar de píxeles a centímetros."""
    scale = skel.scale_m
    rest = [{"root": [0, 0, 0, 0, 0, 0], **{b.name: [0.0] * len(b.dof) for b in skel.bones.values() if b.dof}}]
    pos, _ = forward_kinematics(skel, rest)
    P = to_halpe26(pos, _)[0]
    ankle_height = float(P[H.LEFT_ANKLE, 1] - P[:, 1].min())
    hip_to_root = abs(float(skel.bones["lhipjoint"].direction[1]) * skel.bones["lhipjoint"].length * scale)
    return ankle_height + hip_to_root + sum(skel.bones[b].length for b in STATURE_CHAIN) * scale


def still_frame(P: np.ndarray, fps: float, window_s: float = 1.0) -> int:
    """El cuadro más quieto del primer `window_s`: de ahí sale la orientación de
    la cámara. Es **colocación de cámara**, no una medición: el address que
    cuenta lo detecta el motor sobre la proyección, como en cualquier clip."""
    hands = (P[:, H.LEFT_WRIST] + P[:, H.RIGHT_WRIST]) / 2.0
    v = np.linalg.norm(np.gradient(hands, axis=0), axis=1)
    n = min(P.shape[0], max(2, int(round(window_s * fps))))
    return int(np.argmin(v[:n]))


def to_harness_frame(P: np.ndarray, ref: int) -> tuple[np.ndarray, np.ndarray]:
    """Los puntos en el marco del arnés (`chain.py`): x hacia el objetivo, y
    arriba, z hacia la pelota; origen entre los tobillos, sobre el suelo.

    El eje x sale de la línea de caderas en el cuadro `ref`: para un golfista
    la cadera delantera (la izquierda, si es diestro) apunta al objetivo. `z` se
    completa como `x × y`, que es la dirección en la que mira el pecho.
    Devuelve `(puntos, R)`, con `R` la matriz que también sirve para llevar
    cualquier otro vector 3-D de CMU a este marco (la verdad del sway, por
    ejemplo)."""
    up = np.array([0.0, 1.0, 0.0])
    hips = P[ref, H.LEFT_HIP] - P[ref, H.RIGHT_HIP]
    x = hips - (hips @ up) * up
    n = np.linalg.norm(x)
    if n < 1e-6:
        raise ValueError("la línea de caderas es vertical en el cuadro de referencia: no hay eje de objetivo")
    x = x / n
    z = np.cross(x, up)
    R = np.stack([x, up, z])  # filas: lleva un vector de CMU a (x, y, z) del arnés
    origin = (P[ref, H.LEFT_ANKLE] + P[ref, H.RIGHT_ANKLE]) / 2.0
    Q = (P - origin) @ R.T
    Q[..., 1] -= float(np.nanmin(Q[..., 1]))  # el punto más bajo de todo el trial es el suelo
    return Q, R


def fit_intrinsics(points_m: np.ndarray, view: str, *, width: int, height: int, body_frac: float, distance_m: float, camera_height_m: float, iters: int = 6) -> tuple:
    """Intrínsecos de una cámara virtual vertical con el sujeto al `body_frac`
    del alto del cuadro. La focal se ajusta iterando (proyectar → medir la
    altura del cuerpo en px → corregir): sin distorsión la relación es lineal y
    converge en dos vueltas. La cámara apunta a la mitad del cuerpo para que
    entre centrado; eso es apuntar, no mover el punto principal."""
    from kinelab.perception.framing import body_height_px
    from kinelab_truth.camera import Intrinsics, project, view_extrinsics

    target = body_frac * height
    look_at = float(np.nanmax(points_m[..., 1]) / 2.0)
    extr = view_extrinsics(view, distance_m=distance_m, height_m=camera_height_m, look_at_height_m=look_at)
    f = 1000.0
    for _ in range(iters):
        intr = Intrinsics("mocap-virtual", width, height, f, f, width / 2.0, height / 2.0, (0.0,) * 5, "sin_verificar")
        px = project(points_m, intr, extr)
        bh = float(np.nanmedian(body_height_px(px, CMU_FPS)))
        if not np.isfinite(bh) or bh <= 0:
            raise ValueError("no se pudo medir la altura del cuerpo en la proyección")
        if abs(bh - target) < 0.5:
            break
        f *= target / bh
    return intr, extr, px, bh


# --- pose.npz ----------------------------------------------------------------


_CAPTURED_ON = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _captured_on(amc_text: str) -> str | None:
    r"""La fecha de captura que CMU dejó en la ruta del encabezado del AMC
    (`#!OML:ASF I:\golf\…\2002-09-07\Subject1.ASF`). None si no está."""
    head = amc_text.split("\n", 1)[0]
    m = _CAPTURED_ON.search(head)
    return m.group(1) if m else None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class MocapPose:
    keypoints_px: np.ndarray  # (T,26,2)
    points_m: np.ndarray  # (T,26,3) en el marco del arnés
    rotation_to_harness: np.ndarray  # (3,3)
    provenance: dict
    height_m: float
    body_height_px: float
    ref_frame: int


def build(trial: str, view: str, *, asf: Path | None = None, amc: Path | None = None, width: int = 1080, height: int = 1920, body_frac: float = 0.80, distance_m: float = 3.0, camera_height_m: float = 1.2) -> MocapPose:
    """De los archivos de CMU a los keypoints proyectados, con su procedencia."""
    subject = trial.split("_")[0]
    asf = asf or EXAMPLES / f"{subject}.asf"
    amc = amc or EXAMPLES / f"{trial}.amc"
    skel = parse_asf(asf.read_text(encoding="utf-8", errors="replace"))
    frames = parse_amc(amc.read_text(encoding="utf-8", errors="replace"))
    pos, rot = forward_kinematics(skel, frames)
    P = to_halpe26(pos, rot)
    ref = still_frame(P, CMU_FPS)
    Q, R = to_harness_frame(P, ref)
    intr, extr, px, bh = fit_intrinsics(Q, view, width=width, height=height, body_frac=body_frac, distance_m=distance_m, camera_height_m=camera_height_m)
    stature = stature_m(skel)
    head_to_ankle = float(Q[ref, H.HEAD, 1] - (Q[ref, H.LEFT_ANKLE, 1] + Q[ref, H.RIGHT_ANKLE, 1]) / 2.0)
    provenance = {
        "source": "cmu-mocap",
        "subject": subject,
        "trial": trial,
        "captured_on": _captured_on(amc.read_text(encoding="utf-8", errors="replace")),
        "asf": asf.name,
        "asf_sha256": _sha256(asf),
        "amc": amc.name,
        "amc_sha256": _sha256(amc),
        "source_name": amc.name,
        "source_sha256": _sha256(amc),
        "attribution": "The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217.",
        "keypoint_set": "halpe26",
        "model": None,
        "checkpoint_sha256": None,
        "detector": None,
        "provider": "kinelab_truth.mocap (proyección geométrica; sin estimador de pose)",
        "camera": {"id": intr.id, "provenance": "sin_verificar", "width": width, "height": height, "fx": round(intr.fx, 3), "fy": round(intr.fy, 3), "cx": intr.cx, "cy": intr.cy, "dist": list(intr.dist), "view": view, "distance_m": distance_m, "camera_height_m": camera_height_m, "body_frac_target": body_frac},
        "fps_real": CMU_FPS,
        "fps_note": "120 fps exacto por construcción (mocap CMU): es la tasa del sistema Vicon declarada por CMU, no una medición de esta Mac.",
        "frames": int(px.shape[0]),
        "frame_size": [width, height],
        "rotation_deg": 0,
        "reference_frame_idx": ref,
        "stature_m": round(stature, 4),
        "stature_note": "estatura de pie, de los largos de hueso del ASF (ver `stature_m`). Es la ALTURA DECLARADA con la que el motor pasa de px a cm.",
        "head_to_ankle_m_at_ref": round(head_to_ankle, 4),
        "body_height_px_median": round(bh, 1),
        "mapping_approximations": APPROX_NOTES,
        "no_es_video": "mocap CMU proyectado con la cámara virtual del arnés: no hay video, no hay estimador y no hay palo. No es una referencia ni un ideal.",
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    return MocapPose(keypoints_px=px.astype(np.float32), points_m=Q, rotation_to_harness=R, provenance=provenance, height_m=stature, body_height_px=bh, ref_frame=ref)


def write_pose(mp: MocapPose, take_dir: Path) -> Path:
    """`pose.npz` con las claves del contrato. `scores` en 1,0: los puntos no
    salen de un modelo, salen de una proyección — no hay confianza que informar
    y decirlo con un número menor sería inventar una duda que no existe."""
    from kinelab.perception.framing import framing_report
    from kinelab.perception.plausibility import plausibility_mask
    from kinelab.perception.posestore import PoseData, save_pose

    px = mp.keypoints_px
    T = int(px.shape[0])
    scores = np.ones((T, J), np.float32)
    mask, counts = plausibility_mask(px, scores, min_score=0.0)
    lo, hi = np.nanmin(px, axis=1), np.nanmax(px, axis=1)
    bbox = np.concatenate([lo, hi], axis=1).astype(np.float32)

    # `framing_report` pide un seguimiento; acá no hubo detección que pudiera
    # fallar, así que va con todo detectado y un solo candidato (duck typing,
    # igual que el arnés).
    track = SimpleNamespace(keypoints=px, scores=scores, detected_mask=np.ones(T, bool), candidates=np.ones(T, int), detection_rate=1.0)
    report = framing_report(track, CMU_FPS, mp.provenance["frame_size"][1], None)
    prov = {**mp.provenance, "plausibility_counts": counts, "camera_motion_px": 0.0, "framing": report.__dict__}
    take_dir.mkdir(parents=True, exist_ok=True)
    return save_pose(take_dir, PoseData(px, scores, bbox, np.arange(T) / CMU_FPS, mask, prov), overwrite=True)


# --- nivel 1: la métrica 2-D contra la verdad 3-D ----------------------------


def events_3d(points_m: np.ndarray, fps: float = CMU_FPS) -> dict[str, int]:
    """Address, top e impacto leídos sobre las curvas **3-D** del mocap.

    El criterio se fijó mirando las curvas y quedó escrito acá para que el
    número se pueda volver a sacar; no toca ningún umbral del motor y no lo
    mira. Es la verdad contra la que se compara lo que el motor saca de la
    proyección 2-D:

    - `address`: último cuadro de la quietud del arranque — la velocidad 3-D
      del centro de las muñecas, con mediana móvil de 0,1 s, bajo 0,15 m/s.
    - `impact`: el cuadro en que las manos vuelven **más cerca** de su posición
      3-D de address, después de haberse alejado más de 0,5 m. Es el mismo
      criterio geométrico del motor (mínima distancia al address), pero en 3-D.
    - `top_height`: máxima ALTURA de las manos entre address e impacto.
    - `top_far`: máxima DISTANCIA 3-D al address entre address e impacto. Son
      dos instantes distintos y los dos se informan: GolfDB define el top por el
      cambio de dirección del palo, que acá no existe, y la mano deja de subir
      y deja de alejarse en cuadros distintos.
    """
    hands = (points_m[:, H.LEFT_WRIST] + points_m[:, H.RIGHT_WRIST]) / 2.0
    v = np.linalg.norm(np.gradient(hands, axis=0), axis=1) * fps
    k = max(1, int(round(0.05 * fps)))
    vs = np.array([np.median(v[max(0, i - k) : i + k + 1]) for i in range(v.size)])
    address = 0
    while address + 1 < vs.size and vs[address + 1] < 0.15:
        address += 1
    d = np.linalg.norm(hands - hands[address], axis=1)
    if not (d > 0.5).any():
        raise ValueError("las manos nunca se alejan 0,5 m de la posición de address: no parece un swing completo")
    lejos = int(np.argmax(d > 0.5))
    impact = lejos + int(np.argmin(d[lejos : min(d.size, lejos + int(2 * fps))]))
    return {
        "address": address,
        "top_height": address + int(np.argmax(hands[address:impact, 1])),
        "top_far": address + int(np.argmax(d[address:impact])),
        "impact": impact,
    }


# Qué punto 3-D y qué eje del marco del arnés le corresponden a cada métrica de
# desplazamiento. El eje sale de la cámara de la vista: en `face_on` la x de la
# imagen es la línea de tiro (x del mundo) y en `down_the_line` es la dirección
# hacia la pelota (z del mundo); la y de la imagen es la altura en las dos.
L1_DISPLACEMENTS: dict[str, tuple[tuple[int, ...], int, str, str]] = {
    "pelvis_sway_top_cm": ((H.LEFT_HIP, H.RIGHT_HIP), 0, "address", "top"),
    "pelvis_sway_impact_cm": ((H.LEFT_HIP, H.RIGHT_HIP), 0, "address", "impact"),
    "pelvis_lift_top_cm": ((H.LEFT_HIP, H.RIGHT_HIP), 1, "address", "top"),
    "pelvis_thrust_top_cm": ((H.LEFT_HIP, H.RIGHT_HIP), 2, "address", "top"),
    "thorax_sway_top_cm": ((H.LEFT_SHOULDER, H.RIGHT_SHOULDER), 0, "address", "top"),
    "thorax_lift_top_cm": ((H.LEFT_SHOULDER, H.RIGHT_SHOULDER), 1, "address", "top"),
    "head_sway_top_cm": ((H.HEAD,), 0, "address", "top"),
    "head_lift_top_cm": ((H.HEAD,), 1, "address", "top"),
}
L1_DURATIONS: dict[str, tuple[str, str]] = {
    "backswing_duration_ms": ("address", "top"),
    "downswing_duration_ms": ("top", "impact"),
}


def level1_table(take_dir: Path, mp: MocapPose) -> dict:
    """Lo que el motor midió desde la proyección 2-D contra la verdad 3-D del
    mocap, para el **mismo** sujeto y el **mismo** instante.

    El sesgo se parte en dos a propósito: con los cuadros del motor sale el
    error de la MEDICIÓN sola (proyección + conversión a cm); con los cuadros
    leídos en 3-D sale el error total, con el de los EVENTOS adentro. Una fila
    con `motor_2d` en `null` sigue mostrando la verdad: es el caso de una
    métrica que la vista no habilita."""
    a = json.loads((take_dir / "analysis.json").read_text(encoding="utf-8"))
    rep = a["reps"][0]["metrics"]
    ev = {k: (a["events"][0][k] or {}).get("frame") for k in ("address", "top", "impact", "follow_end")}
    t3 = events_3d(mp.points_m)
    # `top_far` (la máxima distancia 3-D al address) es el análogo del cambio de
    # dirección que detecta el motor; `top_height` queda informado aparte.
    m3 = {"address": t3["address"], "top": t3["top_far"], "impact": t3["impact"]}
    P = mp.points_m
    filas = []

    def fila(mid: str, unidad: str, motor, v_motor: float | None, v_3d: float | None, dec: int) -> dict:
        return {
            "metrica": mid, "unidad": unidad, "motor_2d": motor,
            "verdad_3d_en_cuadros_del_motor": None if v_motor is None else round(v_motor, dec),
            "verdad_3d_en_cuadros_3d": None if v_3d is None else round(v_3d, dec),
            "sesgo_solo_medicion": None if (motor is None or v_motor is None) else round(motor - v_motor, dec),
            "sesgo_total": None if (motor is None or v_3d is None) else round(motor - v_3d, dec),
            "mdc": rep[mid]["mdc"], "null_reason": rep[mid]["null_reason"],
        }

    for mid, (joints, axis, zero, at) in L1_DISPLACEMENTS.items():
        if mid not in rep:
            continue
        pt = P[:, list(joints)].mean(axis=1)
        d = lambda f0, f1: 100.0 * float(pt[f1, axis] - pt[f0, axis])  # noqa: E731
        filas.append(fila(mid, "cm", rep[mid]["value"], d(ev[zero], ev[at]) if ev[at] is not None else None, d(m3[zero], m3[at]), 2))
    for mid, (zero, at) in L1_DURATIONS.items():
        if mid not in rep:
            continue
        ms = lambda f0, f1: (f1 - f0) / CMU_FPS * 1000.0  # noqa: E731
        filas.append(fila(mid, "ms", rep[mid]["value"], ms(ev[zero], ev[at]) if ev[at] is not None else None, ms(m3[zero], m3[at]), 1))
    ank = (P[ev["address"], H.LEFT_ANKLE, 1] + P[ev["address"], H.RIGHT_ANKLE, 1]) / 2.0
    return {
        "trial": mp.provenance["trial"], "vista": mp.provenance["camera"]["view"],
        "n_trials": 1, "n_sujetos": 1,
        "aviso": "Un solo trial de un solo sujeto: es una primera lectura, no una tabla. No sale de acá ningún MDC, ninguna referencia y ningún ideal.",
        "eventos_motor": ev, "eventos_3d": t3,
        "altura_declarada_m": round(mp.height_m, 4),
        "cabeza_a_tobillo_m_en_address": round(float(P[ev["address"], H.HEAD, 1] - ank), 4),
        "cociente_altura_declarada_sobre_cabeza_tobillo": round(float(mp.height_m / (P[ev["address"], H.HEAD, 1] - ank)), 4),
        "filas": filas,
    }


def write_trabajo(take_dir: Path, mp: MocapPose, view: str, etiqueta: str) -> Path:
    """El `trabajo.json` que hace de esta carpeta un **ejemplo** en la lista de
    la pantalla. La forma está documentada en el encabezado de
    `service/exploracion.py` (encargo 08): `estado` listo, `origen` ejemplo, y
    una `etiqueta` que es el rótulo que se muestra. El id del trabajo es el
    nombre de la carpeta, no un campo."""
    d = {
        "estado": "listo", "origen": "ejemplo", "etiqueta": etiqueta,
        "video": f"cmu-{mp.provenance['trial']}-{view}",
        "creado": mp.provenance["run_at"], "terminado": mp.provenance["run_at"],
        "altura_m": round(mp.height_m, 4), "vista": view,
        "progreso": {"cuadros": mp.provenance["frames"], "total": mp.provenance["frames"]},
        "error": None, "segundos": None,
    }
    p = take_dir / "trabajo.json"
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def banner_text(trial: str) -> str:
    return f"mocap CMU {trial} · cámara virtual · no es video"


def fps_note(trial: str) -> str:
    return f"fps 120 exacto por construcción (mocap CMU {trial}), cámara virtual, no es video: no hay archivo que reproduzca ni cronómetro que filmar, y por eso ninguna métrica puede ser juicio."


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m kinelab_truth.mocap", description="Un swing de mocap real (CMU) proyectado con la cámara virtual del arnés.")
    ap.add_argument("trial", help="id del trial, p. ej. 64_01 (el ASF se busca al lado: 64.asf)")
    ap.add_argument("--vista", default="face_on", choices=("face_on", "down_the_line"))
    ap.add_argument("--out", type=Path, required=True, help="carpeta de salida (la toma)")
    ap.add_argument("--asf", type=Path, default=None)
    ap.add_argument("--amc", type=Path, default=None)
    ap.add_argument("--solo-pose", action="store_true", help="escribir pose.npz y parar (sin eventos ni overlay)")
    ap.add_argument("--nivel1", action="store_true", help="además, la comparación 2-D contra la verdad 3-D (ADR-009 nivel 1)")
    ap.add_argument("--etiqueta", default=None, help="rótulo del trabajo.json del ejemplo; sin él no se escribe trabajo.json")
    ap.add_argument("--deporte", default="golf")
    args = ap.parse_args(argv)

    mp = build(args.trial, args.vista, asf=args.asf, amc=args.amc)
    pose_path = write_pose(mp, args.out)
    print(f"{pose_path}")
    print(f"  {mp.provenance['frames']} cuadros a {CMU_FPS:g} fps · estatura {mp.height_m:.3f} m · cuerpo {mp.body_height_px:.0f} px ({mp.body_height_px / mp.provenance['frame_size'][1] * 100:.1f} % del alto)")
    print(f"  cámara {args.vista} · f {mp.provenance['camera']['fx']:.1f} px · cuadro de referencia {mp.ref_frame}")
    if args.solo_pose:
        return 0

    from kinelab.explore import explore
    from sports import get_sport

    r = explore(None, args.out, get_sport(args.deporte), height_m=mp.height_m, view=args.vista, pose_npz=pose_path, nota_fuente=fps_note(args.trial), banner=banner_text(args.trial))
    print(f"  eventos {r['eventos_frame']} · {r['eventos_t_s']}")
    print(f"  duraciones {r['duraciones']}")
    for f in r["archivos"]:
        print(f"  {f}")
    if args.etiqueta:
        print(f"  {write_trabajo(args.out, mp, args.vista, args.etiqueta)}")
    if args.nivel1:
        tabla = level1_table(args.out, mp)
        (args.out / "nivel1-mocap.json").write_text(json.dumps(tabla, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  NIVEL 1 · {tabla['trial']} · {tabla['vista']} — {tabla['aviso']}")
        print(f"  eventos del motor {tabla['eventos_motor']}")
        print(f"  eventos leídos en 3-D {tabla['eventos_3d']}")
        print(f"  altura declarada {tabla['altura_declarada_m']} m · cabeza-tobillo en address {tabla['cabeza_a_tobillo_m_en_address']} m")
        print(f"  {'métrica':<24}{'motor 2D':>10}{'verdad 3D':>11}{'sesgo':>8}   {'verdad 3D':>10}{'sesgo':>8}   {'MDC':>7}")
        print(f"  {'':<24}{'':>10}{'(cuadros del motor)':>19}   {'(cuadros 3D)':>18}")
        for f in tabla["filas"]:
            print(f"  {f['metrica']:<24}{f['motor_2d']:>10}{f['verdad_3d_en_cuadros_del_motor']:>11}{f['sesgo_solo_medicion']:>8}   {f['verdad_3d_en_cuadros_3d']:>10}{f['sesgo_total']:>8}   {str(f['mdc']):>7}")
        print(f"  {args.out / 'nivel1-mocap.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
