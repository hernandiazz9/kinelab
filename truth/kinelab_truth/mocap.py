"""Un swing de mocap REAL (CMU) visto por la cámara virtual del arnés.

    python -m kinelab_truth.mocap 64_01 --vista face_on --out DIR
    python -m kinelab_truth.mocap 64 --escala            # la tabla de escala, todos los trials

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

from kinelab.perception.keypoints import H, HALPE26_LIMBS, HALPE26_NAMES, J
from kinelab.perception.plausibility import angle_deg

INCH_M = 0.0254
CMU_FPS = 120.0  # tasa de captura del sistema Vicon de CMU, declarada por ellos (no medida acá)
EXAMPLES = Path(__file__).resolve().parents[2] / "data" / "examples" / "cmu-mocap"

POSE3D_JSON = "pose3d.json"
# 1.1.0: `angulos`, `angulos_3d` y `angulos_proyectados` (encargo 23) y el
# rótulo `resumen`. Campos nuevos y opcionales, nada renombrado y ninguna
# unidad cambiada: minor, con el criterio de `CONTRATO.md` §Versionado. El visor
# tiene que seguir abriendo un archivo 1.0.0 —hay uno publicado en la demo— y lo
# hace sin la capa de ángulos, no con una pantalla en blanco.
POSE3D_SCHEMA = "kinelab.pose3d/1.1.0"
# Milímetros. A 3 m con la focal del protocolo (~3078 px), medio milímetro es
# medio píxel: el redondeo entra en la tolerancia de 1 px del test de ida y
# vuelta y el archivo pesa la mitad que con seis decimales.
POSE3D_DECIMALS = 3

# El marco va como DATO adentro del archivo, no como comentario en el código
# (CONTEXTO.md §Sistemas de coordenadas). Es el mismo marco del arnés (`chain.py`).
HARNESS_FRAME = {
    "id": "harness_world_m",
    "unidades": "m",
    "origen": "el punto medio entre los dos tobillos en el cuadro de referencia, bajado al suelo: y = 0 es el punto más bajo de todo el trial",
    "ejes": {
        "x": "hacia el objetivo (adonde va la pelota)",
        "y": "hacia arriba",
        "z": "hacia la pelota (sale del pecho del golfista en address)",
    },
    "mano": "derecha (z = x × y)",
}

# La receta para volver a proyectar los puntos 3-D desde afuera de Python. Es
# palabra por palabra lo que hace `camera.Extrinsics.rt()` + `camera.project()`
# con distorsión en cero, y un test la reconstruye a mano contra el `pose.npz`.
PINHOLE_MODEL = (
    "pinhole sin distorsión. f = normalizar(objetivo_m − posicion_m); "
    "r = normalizar(f × (0,1,0)); d = f × r; R = [r; d; f] (filas). "
    "p = R · (X − posicion_m); u = fx·p₀/p₂ + cx; v = fy·p₁/p₂ + cy. "
    "v crece hacia ABAJO: es el marco image_px del `pose.npz`."
)


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


VIEWS = ("face_on", "down_the_line")


def camera_record(points_m: np.ndarray, view: str, *, width: int = 1080, height: int = 1920, body_frac: float = 0.80, distance_m: float = 3.0, camera_height_m: float = 1.2) -> tuple[dict, np.ndarray]:
    """La cámara virtual de una vista como **dato**: lo justo para volver a
    proyectar los puntos 3-D desde afuera de Python, sin OpenCV y sin este
    módulo. Devuelve el registro y la proyección.

    Por eso van la posición y el objetivo en metros en vez de una matriz: la
    matriz se arma con la receta de `modelo`, que es la misma de
    `camera.Extrinsics.rt()`, y un test la reconstruye a mano y compara contra
    el `pose.npz` dentro de 1 px. Si el visor y el arnés no coinciden, uno de
    los dos miente."""
    intr, extr, px, bh = fit_intrinsics(points_m, view, width=width, height=height, body_frac=body_frac, distance_m=distance_m, camera_height_m=camera_height_m)
    rec = {
        "vista": view,
        "ancho": int(intr.width),
        "alto": int(intr.height),
        "fx": round(float(intr.fx), 6),
        "fy": round(float(intr.fy), 6),
        "cx": float(intr.cx),
        "cy": float(intr.cy),
        "dist": [float(d) for d in intr.dist],
        "posicion_m": [round(float(v), 6) for v in extr.position],
        "objetivo_m": [round(float(v), 6) for v in extr.target],
        "distancia_m": float(distance_m),
        "altura_camara_m": float(camera_height_m),
        "cuerpo_px": round(float(bh), 1),
        "cuerpo_frac_del_alto": round(float(bh) / float(intr.height), 4),
        "procedencia": intr.provenance,
        "modelo": PINHOLE_MODEL,
    }
    return rec, px


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
    # La cámara del protocolo de LAS DOS vistas, no sólo la de esta toma: los
    # puntos 3-D son los mismos para las dos (`to_harness_frame` no mira la
    # cámara), así que el visor puede llevar la cámara a cualquiera de las dos
    # y comparar contra el overlay de esa vista.
    cameras: dict[str, dict] = field(default_factory=dict)


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
    if view not in VIEWS:
        raise ValueError(f"vista desconocida: {view}; hay {', '.join(VIEWS)}")
    # Las dos cámaras, aunque esta toma use una: los puntos 3-D son los mismos
    # para las dos y el visor tiene que poder ir a cualquiera de ellas.
    cameras: dict[str, dict] = {}
    proyecciones: dict[str, np.ndarray] = {}
    for v in VIEWS:
        cameras[v], proyecciones[v] = camera_record(Q, v, width=width, height=height, body_frac=body_frac, distance_m=distance_m, camera_height_m=camera_height_m)
    px = proyecciones[view]
    cam = cameras[view]
    bh = cam["cuerpo_px"]
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
        "camera": {"id": "mocap-virtual", "provenance": cam["procedencia"], "width": width, "height": height, "fx": round(cam["fx"], 3), "fy": round(cam["fy"], 3), "cx": cam["cx"], "cy": cam["cy"], "dist": list(cam["dist"]), "view": view, "distance_m": distance_m, "camera_height_m": camera_height_m, "body_frac_target": body_frac},
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
    return MocapPose(keypoints_px=px.astype(np.float32), points_m=Q, rotation_to_harness=R, provenance=provenance, height_m=stature, body_height_px=bh, ref_frame=ref, cameras=cameras)


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


# --- pose3d.json: el swing en 3-D, para mirarlo desde donde uno quiera --------


def rotulos(trial: str) -> dict[str, str]:
    """Las frases que la pantalla muestra al lado del swing 3-D.

    Las escribe quien produjo el dato, no la pantalla: la misma regla que
    `nota_fuente` (informe del 07, "ninguna frase de aviso se compone en la
    pantalla"). Redacción para un entrenador, no para un ingeniero."""
    return {
        # La única línea que queda a la vista siempre: el resto del argumento va
        # detrás de un desplegable, porque el texto entero ocupaba más que la
        # figura y la tapaba (encargo 23, punto 6). Se escribe acá, no en la
        # pantalla: la pantalla no compone ninguna de estas frases.
        "resumen": f"Mocap del sujeto 64 de CMU, toma {trial}, medido con marcadores ópticos: no es un video y no es un swing de Hernán.",
        "fuente": f"Swing de laboratorio del sujeto 64 de la base de mocap de CMU, toma {trial}, medido con marcadores ópticos: la posición de cada articulación en el espacio está medida, punto por punto.",
        "no_es_video": "No es un video y no es un swing de Hernán. Es el único material con profundidad medida que hay en el proyecto, y está acá para mostrar qué se puede ver cuando la profundidad existe de verdad.",
        "no_con_un_celular": "Esto no se puede hacer con un clip de celular: una cámara sola no mide profundidad. De un video sale dónde está cada punto EN LA IMAGEN, no en el espacio, y la profundidad que falta no se deduce, se inventa. Para ver así un swing propio harían falta dos cámaras sincronizadas y calibradas, o marcadores como los de acá.",
        "para_que_sirve": "Girar la escena muestra por qué cada medición dice desde qué vista vale: hay ángulos desde los que una línea del cuerpo apunta a la cámara, y ahí en la imagen esa línea no mide casi nada.",
        "descriptivo": "Números para mirar, no para juzgar: acá no se compara nada contra ningún rango (ADR-012).",
    }


def indicador_lineas() -> dict:
    """Qué mide el indicador de líneas colapsadas, y con qué frases se lee.

    El umbral es de lectura, no de medición: decide cuál de las dos frases se
    muestra y nada más. Sale de lo medido en el encargo 13: desde
    `down_the_line` la línea de caderas baja a 3,6 px de 15,2 cm reales, o sea
    3 % de su largo; desde `face_on` se queda por encima del 90 %."""
    return {
        "que_mide": "cuánto mide una línea del cuerpo EN LA IMAGEN comparado con lo que mide de verdad, desde el ángulo y el cuadro que se están viendo",
        "unidad": "fracción del largo real (0 a 1)",
        "definicion": "largo proyectado en px × profundidad del punto medio ÷ (focal × largo real en m): es lo que mediría esa misma línea si estuviera de costado a la cámara, a la misma distancia. No depende de la focal ni del zoom, sólo del ángulo.",
        "umbral_colapso_frac": 0.25,
        "lineas": {"caderas": ["left_hip", "right_hip"], "hombros": ["left_shoulder", "right_shoulder"]},
        "texto": "100 % es la línea de costado a la cámara; 0 % es la línea apuntando a la cámara.",
        "texto_colapso": "Desde este ángulo esa línea casi no mide en la imagen: cualquier ángulo o velocidad que se saque de ella sale de la proyección y no del cuerpo. Por eso cada medición declara desde qué vistas vale.",
        "medido": "Encargo 13, sobre el swing sintético del arnés: desde down_the_line la línea de caderas se proyecta en 3,6 px y su giro aparente da 11110 °/s contra 139,6 verdaderos, 80 veces más. Es la misma geometría que se ve girando este mocap, con otro cuerpo.",
        "procedencia": "medido_aqui",
    }


# --- los ángulos: en el mocap son verdaderos ---------------------------------

# En 3-D un ángulo articular es el ángulo de verdad: tres puntos medidos en el
# espacio, sin proyección en el medio. Es la única parte del proyecto donde eso
# existe. Sirve de REFERENCIA, igual que la verdad 3-D del sway: `CONTRATO.md`
# §Niveles pone los ángulos absolutos de codo, rodilla y muñeca en nivel 3 —no
# se construyen como métrica del producto— y nada de esto entra al registro ni
# a `analysis.json`. Lo que sí hace es mostrar POR QUÉ están en nivel 3.

ANGULOS_DECIMALES = 2  # el punto está en milímetros: 0,01° ya es más de lo que informa


def angle3_deg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Ángulo en `b` formado por A-B-C, en grados, en [0, 180], **en 3-D**.

    Es la misma definición que mide el motor en el plano de imagen
    (`kinelab.perception.plausibility.angle_deg`: `arctan2(|v1 × v2|, v1 · v2)`,
    que no pierde precisión cerca de 0° ni de 180°), con el producto vectorial
    de 3 componentes en vez del escalar de 2. No se puede importar tal cual
    porque aquella indexa `[..., 0]` y `[..., 1]` y nada más; lo que garantiza
    que sigan siendo la misma es un test: con `z = 0` las dos tienen que dar el
    mismo número, y los ángulos proyectados de acá tienen que reproducir columna
    por columna los del motor (`test_angulos.py`).
    """
    v1 = np.asarray(a, float) - np.asarray(b, float)
    v2 = np.asarray(c, float) - np.asarray(b, float)
    cross = np.linalg.norm(np.cross(v1, v2), axis=-1)
    dot = np.einsum("...i,...i->...", v1, v2)
    n1 = np.linalg.norm(v1, axis=-1)
    n2 = np.linalg.norm(v2, axis=-1)
    return np.where((n1 == 0) | (n2 == 0), np.nan, np.degrees(np.arctan2(cross, dot)))


# Los ocho ángulos de tres puntos son **los mismos tres puntos** que dibuja el
# overlay plano (`kinelab/explore.py`, `per_frame_table`): si acá se cambiara
# uno, la comparación 3-D contra proyección dejaría de ser justa. El test
# `test_los_proyectados_son_los_del_motor` los compara contra las columnas del
# propio motor, cuadro por cuadro, así que un cambio de allá rompe acá.
_TRES_PUNTOS: dict[str, tuple[int, int, int]] = {
    "elbow_left_deg": (H.LEFT_SHOULDER, H.LEFT_ELBOW, H.LEFT_WRIST),
    "elbow_right_deg": (H.RIGHT_SHOULDER, H.RIGHT_ELBOW, H.RIGHT_WRIST),
    "knee_left_deg": (H.LEFT_HIP, H.LEFT_KNEE, H.LEFT_ANKLE),
    "knee_right_deg": (H.RIGHT_HIP, H.RIGHT_KNEE, H.RIGHT_ANKLE),
    "hip_left_deg": (H.LEFT_SHOULDER, H.LEFT_HIP, H.LEFT_KNEE),
    "hip_right_deg": (H.RIGHT_SHOULDER, H.RIGHT_HIP, H.RIGHT_KNEE),
    "shoulder_left_deg": (H.LEFT_ELBOW, H.LEFT_SHOULDER, H.LEFT_HIP),
    "shoulder_right_deg": (H.RIGHT_ELBOW, H.RIGHT_SHOULDER, H.RIGHT_HIP),
}

# Las dos líneas cuyo giro alrededor del eje vertical es directo en 3-D e
# imposible en 2-D. El par va (izquierda, derecha): el vector apunta al objetivo
# cuando el golfista está de frente a la pelota.
_GIROS: dict[str, tuple[int, int]] = {
    "hip_line_turn_deg": (H.LEFT_HIP, H.RIGHT_HIP),
    "shoulder_line_turn_deg": (H.LEFT_SHOULDER, H.RIGHT_SHOULDER),
}

_TRUNK = "trunk_lean_deg"


def _mid(P: np.ndarray, idx: tuple[int, ...]) -> np.ndarray:
    return P[:, list(idx)].mean(axis=1)


def angulos_3d(P: np.ndarray) -> dict[str, np.ndarray]:
    """Los once ángulos, cuadro por cuadro, sobre los puntos 3-D en metros.

    Son **verdaderos**: no hay proyección en el medio y por lo tanto no
    arrastran los 21–32° de error de la pose monocular que mide ADR-007. El
    marco es `HARNESS_FRAME`; los dos giros se miden ahí y nada más."""
    out: dict[str, np.ndarray] = {}
    for nombre, (a, b, c) in _TRES_PUNTOS.items():
        out[nombre] = angle3_deg(P[:, a], P[:, b], P[:, c])
    # tronco: ángulo en la cadera entre la vertical hacia arriba y la línea
    # cadera→hombro. Es el mismo ángulo de tres puntos, con un punto auxiliar un
    # metro por encima de la cadera. Sin signo: en 3-D el tronco se inclina en
    # dos direcciones a la vez y un solo número con signo mentiría.
    cadera, hombro = _mid(P, (H.LEFT_HIP, H.RIGHT_HIP)), _mid(P, (H.LEFT_SHOULDER, H.RIGHT_SHOULDER))
    arriba = cadera + np.array([0.0, 1.0, 0.0])
    out[_TRUNK] = angle3_deg(arriba, cadera, hombro)
    for nombre, (izq, der) in _GIROS.items():
        v = P[:, izq] - P[:, der]
        out[nombre] = np.degrees(np.arctan2(v[:, 2], v[:, 0]))
    return out


def angulos_proyectados(px: np.ndarray) -> dict[str, np.ndarray]:
    """Los mismos once, medidos sobre la proyección 2-D `(T,26,2)` en
    `image_px`: lo que el motor calcularía si el swing se hubiera filmado desde
    esa cámara.

    Los ocho de tres puntos y el tronco salen de `angle_deg`, **la función del
    motor**, con los mismos tres puntos. Los dos giros no: alrededor del eje
    vertical no hay ángulo que medir en la imagen, y lo único que se puede
    hacer es el estimado por acortamiento —`arccos(largo / largo máximo de la
    toma)`— que es exactamente el `shoulder_rotation_deg` que `HERENCIA.md`
    prohíbe portar. Va acá para medir cuánto se equivoca, no para usarlo: no
    recupera el signo (por eso se compara contra el valor absoluto del 3-D) y
    su procedencia es `estimacion`."""
    out: dict[str, np.ndarray] = {}
    for nombre, (a, b, c) in _TRES_PUNTOS.items():
        out[nombre] = np.asarray(angle_deg(px[:, a], px[:, b], px[:, c]), float)
    cadera, hombro = _mid(px, (H.LEFT_HIP, H.RIGHT_HIP)), _mid(px, (H.LEFT_SHOULDER, H.RIGHT_SHOULDER))
    arriba = cadera + np.array([0.0, -1.0])  # en image_px la y crece hacia ABAJO
    out[_TRUNK] = np.asarray(angle_deg(arriba, cadera, hombro), float)
    for nombre, (izq, der) in _GIROS.items():
        d = px[:, izq] - px[:, der]
        largo = np.hypot(d[:, 0], d[:, 1])
        ref = float(np.nanmax(largo))
        out[nombre] = np.degrees(np.arccos(np.clip(largo / ref, 0.0, 1.0))) if ref > 0 else np.full(px.shape[0], np.nan)
    return out


# Dónde va el número en la pantalla y qué mide cada uno. El punto de anclaje es
# el vértice del ángulo (para los giros, el medio de la línea): el visor dibuja
# el número al lado de ese punto y lo sigue al girar la cámara.
def angulos_doc() -> dict:
    """Las definiciones, con su unidad, su marco y su procedencia. Van como
    DATO adentro del archivo: la pantalla no compone ninguna de estas frases."""
    tres = {
        "elbow_left_deg": ("codo izquierdo", "hombro → codo → muñeca"),
        "elbow_right_deg": ("codo derecho", "hombro → codo → muñeca"),
        "knee_left_deg": ("rodilla izquierda", "cadera → rodilla → tobillo"),
        "knee_right_deg": ("rodilla derecha", "cadera → rodilla → tobillo"),
        "hip_left_deg": ("cadera izquierda", "hombro → cadera → rodilla"),
        "hip_right_deg": ("cadera derecha", "hombro → cadera → rodilla"),
        "shoulder_left_deg": ("hombro izquierdo", "codo → hombro → cadera"),
        "shoulder_right_deg": ("hombro derecho", "codo → hombro → cadera"),
    }
    defs: dict[str, dict] = {}
    for nombre, (a, b, c) in _TRES_PUNTOS.items():
        etiqueta, cadena = tres[nombre]
        defs[nombre] = {
            "etiqueta": etiqueta,
            "definicion": f"ángulo de tres puntos {cadena}, con el vértice en el punto del medio",
            "puntos": [HALPE26_NAMES[a], HALPE26_NAMES[b], HALPE26_NAMES[c]],
            "anclaje": [HALPE26_NAMES[b]],
            "respecto_de": "los tres puntos",
            "rango": [0, 180],
            "comparar": "valor",
            "proyectado": "el mismo ángulo de tres puntos medido sobre la proyección: es lo que calcula el motor en un video (`kinelab.perception.plausibility.angle_deg`).",
        }
    defs[_TRUNK] = {
        "etiqueta": "inclinación de tronco",
        "definicion": "ángulo en el medio de las caderas entre la vertical hacia arriba y la línea al medio de los hombros. Sin signo: es cuánto se aparta el tronco de la vertical, no hacia dónde.",
        "puntos": ["vertical", "hip_center", "shoulder_center"],
        "anclaje": ["left_hip", "right_hip"],
        "respecto_de": "la vertical del marco",
        "rango": [0, 180],
        "comparar": "valor",
        "proyectado": "el mismo ángulo con la vertical de la IMAGEN (y hacia abajo en `image_px`): coincide con el valor absoluto de `trunk_lean_deg` del motor, que además lleva signo.",
    }
    for nombre, (izq, der) in _GIROS.items():
        etiqueta = "giro de la línea de caderas" if nombre.startswith("hip") else "giro de la línea de hombros"
        defs[nombre] = {
            "etiqueta": etiqueta,
            "definicion": "ángulo de la línea izquierda→derecha proyectada sobre el plano horizontal, respecto de la línea de tiro: `atan2(z, x)` en el marco del arnés. 0° = la línea apunta al objetivo; positivo = gira hacia la pelota, que es el sentido del backswing de un diestro.",
            "puntos": [HALPE26_NAMES[izq], HALPE26_NAMES[der]],
            "anclaje": [HALPE26_NAMES[izq], HALPE26_NAMES[der]],
            "respecto_de": "la línea de tiro",
            "rango": [-180, 180],
            "comparar": "abs",
            "proyectado": "NO es el mismo ángulo: alrededor del eje vertical no hay ángulo que medir en la imagen. Es el estimado por acortamiento, `arccos(largo proyectado / largo proyectado máximo de la toma)`, el mismo `shoulder_rotation_deg` que HERENCIA.md prohíbe portar. No recupera el signo, así que se compara contra el valor absoluto del 3-D. Procedencia: `estimacion`.",
        }
    return {
        "unidad": "grados",
        "decimales": ANGULOS_DECIMALES,
        "marco_3d": HARNESS_FRAME["id"],
        "marco_proyectado": "image_px del `pose.npz` de esa vista (y hacia abajo)",
        "procedencia_3d": "medido_aqui",
        "procedencia_proyectado": "medido_aqui, salvo los dos giros, que son `estimacion`",
        "nota_respecto_de": "un ángulo `de los tres puntos` no cambia si se gira la escena entera: es del cuerpo y de nadie más. Los otros tres se miden contra un eje del marco —la vertical (la gravedad) y la línea de tiro— y giran con él, a propósito: sin un eje externo no hay inclinación ni giro que medir.",
        "definiciones": defs,
        "rotulo": "Estos ángulos son del mocap medido con marcadores ópticos: en 3-D son ángulos de verdad, sin proyección en el medio. Un video de celular no los puede dar —una cámara sola no mide profundidad— y la diferencia que aparece al girar hasta una de las dos vistas del protocolo es exactamente por qué.",
        "texto_comparacion": "arriba, el ángulo real medido en 3-D; abajo, lo que mediría una cámara puesta ahí, y la diferencia.",
        "nota_nivel": "CONTRATO.md §Niveles pone los ángulos absolutos de codo, rodilla y muñeca en nivel 3: no se construyen como métrica del producto. Estos son del mocap y son referencia; ninguno entra al registro de métricas ni a ningún `analysis.json`. Se muestran, no se juzgan (ADR-012).",
        "nota_diferencia": "la diferencia es `proyectado − 3-D` (contra el valor absoluto del 3-D en los dos giros, que el proyectado no puede firmar) y no se guarda: es la resta de las dos series que sí están.",
    }


def _serie_angulo(v: np.ndarray) -> list:
    """Una serie de ángulos lista para el JSON: redondeada y con los `NaN`
    convertidos a `null` (`CONTRATO.md` §Frontera Python ↔ JSON)."""
    return [None if not np.isfinite(x) else round(float(x), ANGULOS_DECIMALES) for x in np.asarray(v, float)]


def _diferencia(nombre: str, p: np.ndarray, t: np.ndarray, defs: dict) -> np.ndarray:
    """`proyectado − 3-D`, contra el valor absoluto del 3-D donde el proyectado
    no puede recuperar el signo (los dos giros)."""
    return p - (np.abs(t) if defs[nombre]["comparar"] == "abs" else t)


def angulos_resumen(P: np.ndarray, cameras: dict[str, dict], eventos: dict[str, int], ventana: tuple[int, int]) -> dict:
    """Cuánto se equivoca la proyección contra el 3-D, en **este** trial: la
    diferencia en cada uno de los tres eventos y en el peor cuadro de la
    ventana de la repetición. Un trial: la tabla de los diez está en
    `angles_table` y se corre con `--angulos`."""
    defs = angulos_doc()["definiciones"]
    t3 = angulos_3d(P)
    a, b = int(ventana[0]), int(ventana[1])
    out: dict[str, dict] = {}
    for vista, cam in cameras.items():
        px = _proyectar_con(P, cam)
        pr = angulos_proyectados(px)
        por_angulo = {}
        for nombre in defs:
            dif = _diferencia(nombre, pr[nombre], t3[nombre], defs)
            tramo = dif[a : b + 1]
            k = int(np.nanargmax(np.abs(tramo))) if np.isfinite(tramo).any() else 0
            por_angulo[nombre] = {
                **{ev: (None if f is None or not np.isfinite(dif[f]) else round(float(dif[f]), ANGULOS_DECIMALES)) for ev, f in eventos.items()},
                "peor_cuadro": a + k,
                "peor_dif": round(float(tramo[k]), ANGULOS_DECIMALES),
            }
        out[vista] = por_angulo
    return {
        "ventana": [a, b],
        "eventos": dict(eventos),
        "nota": "diferencia `proyectado − 3-D` en grados, en los cuadros de `eventos_3d` (los mismos para las dos vistas, así lo que se ve es sólo error de proyección) y en el peor cuadro de la ventana. Un trial de un sujeto.",
        "por_vista": out,
    }


def _proyectar_con(P: np.ndarray, cam: dict) -> np.ndarray:
    """(T,26,3) metros → (T,26,2) `image_px` con una cámara del archivo, usando
    `camera.project` (el mismo camino que arma el `pose.npz`)."""
    from kinelab_truth.camera import Extrinsics, Intrinsics, project

    intr = Intrinsics("mocap-virtual", int(cam["ancho"]), int(cam["alto"]), float(cam["fx"]), float(cam["fy"]), float(cam["cx"]), float(cam["cy"]), tuple(float(x) for x in cam["dist"]), str(cam["procedencia"]))
    extr = Extrinsics(position=np.asarray(cam["posicion_m"], float), target=np.asarray(cam["objetivo_m"], float))
    return project(P, intr, extr)


def _json_legible(doc: dict) -> str:
    """`json.dumps(indent=2)` pone cada número de una lista en su propia línea y
    el encabezado se vuelve ilegible (los 26 nombres, 27 pares de huesos y cinco
    coeficientes de distorsión son 300 líneas). Acá toda lista de escalares —o
    de listas de escalares— va en una sola línea y el resto queda indentado."""
    planas: dict[str, str] = {}

    def escalares(v: list) -> bool:
        return all(not isinstance(x, (list, dict)) for x in v)

    def marcar(v):
        if isinstance(v, dict):
            return {k: marcar(x) for k, x in v.items()}
        if isinstance(v, list):
            if escalares(v) or all(isinstance(x, list) and escalares(x) for x in v):
                clave = f"@@lista-{len(planas)}@@"
                planas[clave] = json.dumps(v, ensure_ascii=False)
                return clave
            return [marcar(x) for x in v]
        return v

    text = json.dumps(marcar(doc), ensure_ascii=False, indent=2)
    for clave, plano in planas.items():
        text = text.replace(f'"{clave}"', plano)
    if "@@lista-" in text:
        raise ValueError("el marcador de lista colisiona con el contenido del archivo")
    return text


def _n(v: float) -> str:
    """Un número del archivo: `POSE3D_DECIMALS` decimales y sin `-0.000`."""
    s = f"{v:.{POSE3D_DECIMALS}f}"
    return s.lstrip("-") if float(s) == 0.0 else s


def pose3d_doc(mp: MocapPose, *, events: dict[str, int] | None = None) -> dict:
    """El contenido de `pose3d.json` **sin** los puntos: todo lo que hay que
    saber para leerlos. Aparte para poder mirarlo en un test sin los 250 KB."""
    P = mp.points_m
    if not np.isfinite(P).all():
        raise ValueError("hay puntos no finitos en el 3-D: `NaN` no es JSON (CONTRATO.md §Frontera) y acá significa que el mapeo se rompió")
    prov = mp.provenance
    t3 = events_3d(P)
    bajo = np.unravel_index(int(np.argmin(P[..., 1])), P[..., 1].shape)
    pies = (H.LEFT_HEEL, H.RIGHT_HEEL, H.LEFT_BIG_TOE, H.RIGHT_BIG_TOE, H.LEFT_SMALL_TOE, H.RIGHT_SMALL_TOE)
    return {
        "schema": POSE3D_SCHEMA,
        "que_es": "los 26 puntos Halpe26 de un swing de mocap, en METROS y en 3-D, cuadro por cuadro. Es lo que la cámara virtual del arnés proyecta para armar el `pose.npz` de este mismo trabajo: los mismos puntos, antes de perder la profundidad.",
        "marco": HARNESS_FRAME,
        # Dónde cae ese cero en ESTE trial, medido: el esqueleto de CMU no apoya
        # la planta del pie, así que en el cuadro de referencia los pies quedan
        # por encima del cero y la grilla del visor no es un piso anatómico.
        "suelo": {
            "punto_mas_bajo": {"nombre": HALPE26_NAMES[bajo[1]], "cuadro": int(bajo[0])},
            "pies_sobre_el_cero_en_el_cuadro_de_referencia_m": round(float(P[mp.ref_frame, list(pies), 1].min()), 3),
            "tobillo_sobre_el_cero_en_el_cuadro_de_referencia_m": round(float(P[mp.ref_frame, [H.LEFT_ANKLE, H.RIGHT_ANKLE], 1].mean()), 3),
            "nota": "y = 0 es el punto más bajo de todo el trial, que no cae en el cuadro de referencia. El esqueleto de CMU no apoya la planta: el tobillo queda a ~15 cm de ese cero. La grilla del visor dibuja ese cero, no un piso anatómico, y por eso los pies del address quedan un poco por encima.",
            "procedencia": "medido_aqui",
        },
        "decimales": POSE3D_DECIMALS,
        "fps": float(prov["fps_real"]),
        "fps_nota": prov["fps_note"],
        "frames": int(prov["frames"]),
        "trial": prov["trial"],
        "sujeto": prov["subject"],
        "vista_del_trabajo": prov["camera"]["view"],
        "estatura_m": prov["stature_m"],
        "estatura_nota": prov["stature_note"],
        "cuadro_de_referencia": int(mp.ref_frame),
        "nombres": list(HALPE26_NAMES),
        "huesos": [[int(a), int(b)] for a, b in HALPE26_LIMBS],
        "puntos_construidos": APPROX_NOTES,
        "eventos": dict(events) if events else None,
        "eventos_nota": "los cuadros que detectó el motor sobre la proyección 2-D de esta vista: los mismos que muestra el reproductor. `null` cuando no se corrió el análisis.",
        "eventos_3d": t3,
        "eventos_3d_nota": "leídos sobre las curvas 3-D con el criterio de `events_3d`: es la verdad contra la que se compara el motor, no lo que el motor detectó. `top_far` es el análogo del cambio de sentido que usa el motor (ADR-017) y `top_height` es el cuadro en que las manos dejan de subir.",
        "camaras": mp.cameras,
        "camaras_nota": "la cámara del protocolo de las dos vistas. Los puntos 3-D son los mismos para las dos; lo único que cambia es desde dónde se mira. Proyectando con cualquiera de las dos se reproduce el `pose.npz` de esa vista dentro de 1 px (test `test_pose3d.py`).",
        "indicador": indicador_lineas(),
        "angulos": {**angulos_doc(), "resumen": angulos_resumen(P, mp.cameras, {"address": t3["address"], "top": t3["top_far"], "impact": t3["impact"]}, (t3["address"], t3["impact"]))},
        "rotulos": rotulos(prov["trial"]),
        "atribucion": prov["attribution"],
        "licencia": "ver data/examples/cmu-mocap/ATRIBUCION.md",
        "run_at": prov["run_at"],
    }


def write_pose3d(mp: MocapPose, take_dir: Path, *, events: dict[str, int] | None = None) -> Path:
    """`pose3d.json`: el mismo swing que el `pose.npz`, con la profundidad
    adentro. Lo lee el visor 3-D de la pantalla (`web/src/components/Visor3D.tsx`).

    Los puntos se escriben con una línea por cuadro: con `indent` serían 35.000
    líneas y compacto entero sería una sola. El encabezado va indentado, que es
    lo que alguien va a leer a ojo."""
    doc = pose3d_doc(mp, events=events)
    # Las series van acá y no en `pose3d_doc` para que el documento se pueda
    # mirar en un test sin arrastrar 448 × 26 puntos y 448 × 39 ángulos.
    doc["angulos_3d"] = {k: _serie_angulo(v) for k, v in angulos_3d(mp.points_m).items()}
    doc["angulos_3d_nota"] = "los once ángulos cuadro por cuadro sobre los puntos 3-D: son los verdaderos. Ver `angulos.definiciones`."
    doc["angulos_proyectados"] = {vista: {k: _serie_angulo(v) for k, v in angulos_proyectados(_proyectar_con(mp.points_m, cam)).items()} for vista, cam in mp.cameras.items()}
    doc["angulos_proyectados_nota"] = "los mismos once medidos sobre la proyección de cada cámara del protocolo: lo que el motor calcularía si el swing se hubiera filmado desde ahí."
    marca = "@@PUNTOS@@"
    doc["puntos"] = marca
    filas = ",\n    ".join("[" + ",".join("[" + ",".join(_n(float(v)) for v in pt) + "]" for pt in frame) + "]" for frame in mp.points_m)
    text = _json_legible(doc).replace(f'"{marca}"', f"[\n    {filas}\n  ]")
    take_dir.mkdir(parents=True, exist_ok=True)
    path = take_dir / POSE3D_JSON
    path.write_text(text + "\n", encoding="utf-8")
    return path


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


# --- la tabla: cuánto se equivoca la proyección, sobre los diez trials --------

ANGULOS_EVENTOS = ("address", "top", "impact")


def angles_table(subject: str, trials: list[str] | None = None) -> dict:
    """Sesgo medio y límites de acuerdo de la proyección contra el 3-D, por
    ángulo y por vista, en los tres eventos y en el peor cuadro de la
    repetición, sobre TODOS los trials del sujeto que estén en `data/examples/`.

    **Un sujeto, N swings.** Sale una media con límites de acuerdo de este
    golfista y de esta geometría de cámara; no sale ningún MDC, ninguna
    referencia y ningún ideal, y nada de esto entra al registro de métricas
    (ADR-009 nivel 1 mide la matemática y la convención, no el estimador).

    Los eventos son los leídos en 3-D (`events_3d`): son el **mismo cuadro**
    para las dos vistas, así que la diferencia que aparece es sólo error de
    proyección, sin el error de detección de eventos adentro."""
    trials = trials or sorted(p.stem for p in EXAMPLES.glob(f"{subject}_*.amc"))
    if not trials:
        raise ValueError(f"no hay ningún {subject}_NN.amc en {EXAMPLES}")
    defs = angulos_doc()["definiciones"]
    filas: list[dict] = []
    for trial in trials:
        mp = build(trial, VIEWS[0])
        P = mp.points_m
        t3 = events_3d(P)
        ev = {"address": t3["address"], "top": t3["top_far"], "impact": t3["impact"]}
        res = angulos_resumen(P, mp.cameras, ev, (t3["address"], t3["impact"]))
        filas.append({"trial": trial, "cuadros": int(P.shape[0]), "eventos": ev, "por_vista": res["por_vista"]})
    resumen: dict[str, dict] = {}
    for vista in VIEWS:
        por_angulo = {}
        for nombre in defs:
            col = {}
            for campo in (*ANGULOS_EVENTOS, "peor_dif"):
                v = np.array([f["por_vista"][vista][nombre][campo] for f in filas if f["por_vista"][vista][nombre][campo] is not None], float)
                sd = float(v.std(ddof=1)) if v.size > 1 else float("nan")
                col[campo] = {"n": int(v.size), "sesgo": round(float(v.mean()), 2), "loa": [round(float(v.mean()) - 1.96 * sd, 2), round(float(v.mean()) + 1.96 * sd, 2)], "abs_max": round(float(np.abs(v).max()), 2)}
            por_angulo[nombre] = col
        resumen[vista] = por_angulo
    return {
        "sujeto": subject, "n_trials": len(filas), "n_sujetos": 1, "trials": [f["trial"] for f in filas],
        "aviso": "Diez swings de UN solo sujeto (CMU 64), con la cámara virtual del protocolo. Es una medición de la GEOMETRÍA de la proyección, no del estimador de pose: no hay video ni modelo en el medio. No sale de acá ningún MDC, ninguna referencia y ningún ideal.",
        "definicion_sesgo": "`proyectado − 3-D` en grados (contra el valor absoluto del 3-D en los dos giros, que el proyectado no puede firmar). Límites de acuerdo de Bland-Altman: media ± 1,96 · SD entre trials (ADR-009 §Formato de reporte).",
        "eventos_nota": "los tres eventos son los de `events_3d`, el mismo cuadro para las dos vistas: lo que se mide es sólo error de proyección. `peor_dif` es el cuadro de mayor |diferencia| entre el address y el impacto de cada trial.",
        "unidad": "grados",
        "por_trial": filas,
        "resumen": resumen,
    }


def print_angles_table(t: dict) -> None:
    defs = angulos_doc()["definiciones"]
    print(f"\n  ÁNGULOS · sujeto {t['sujeto']} · {t['n_trials']} trials — {t['aviso']}")
    print(f"  {t['definicion_sesgo']}")
    print(f"  {t['eventos_nota']}")
    for vista in t["resumen"]:
        print(f"\n  desde {vista}: sesgo [límites de acuerdo], en grados")
        print(f"  {'ángulo':<24}" + "".join(f"{k:>26}" for k in (*ANGULOS_EVENTOS, "peor de la repetición")))
        for nombre, col in t["resumen"][vista].items():
            fila = f"  {nombre:<24}"
            for campo in (*ANGULOS_EVENTOS, "peor_dif"):
                r = col[campo]
                fila += f"{r['sesgo']:>9.1f} [{r['loa'][0]:>6.1f},{r['loa'][1]:>6.1f}]"
            print(fila)
    print(f"\n  los dos giros ({', '.join(k for k, v in defs.items() if v['comparar'] == 'abs')}) no son el mismo ángulo medido de dos formas:")
    print("  en la imagen no hay giro alrededor del eje vertical que medir, y el proyectado es el estimado por acortamiento (procedencia `estimacion`).")


# --- la escala: cuántos píxeles mide la estatura declarada ---------------------

# Las candidatas a divisor de `px_to_cm`, todas geométricas: ninguna fija un
# factor ajustado a este sujeto. Cada una devuelve píxeles por estatura.
#   a  la anterior: altura cabeza→tobillos del cuadro de address
#   b  suma de largos de segmento proyectados en el address
#   c  máxima extensión vertical cabeza→tobillos dentro de la repetición
#   d  máximo de la cadena de segmentos dentro de la repetición  ← la implementada
#   e  ídem d, arrancando en el talón en vez del tobillo (informativa: en el
#      mocap el talón lo CONSTRUYE `to_halpe26`, así que mide nuestra propia
#      aproximación y no la anatomía)
#   z  la escala exacta, que sólo existe porque hay verdad 3-D: la altura
#      cabeza→tobillos del address en px dividida por lo que mide en metros.
#      Es el piso: con ella, lo que queda es error de PROYECCIÓN, no de escala.
SCALE_CANDIDATES = ("a_cabeza_tobillos_address", "b_cadena_address", "c_vertical_max_rep", "d_cadena_max_rep", "e_cadena_talon_max_rep", "z_escala_exacta")


def _scale_divisors(kp: np.ndarray, fps: float, address: int, start: int, end: int, cociente: float) -> dict[str, float]:
    """Los divisores de las candidatas, en px, para una toma ya analizada."""
    from kinelab.metrics.core import STATURE_CHAIN, _link_point, stature_chain_px
    from kinelab.perception.framing import _rolling_nanmedian, body_height_px

    bh = body_height_px(kp, fps)
    chain = stature_chain_px(kp, fps)
    talon = ((H.LEFT_HEEL, H.RIGHT_HEEL), *STATURE_CHAIN)
    pts = [_link_point(kp, j) for j in talon]
    con_talon = np.zeros(kp.shape[0])
    for a, b in zip(pts, pts[1:]):
        d = b - a
        con_talon += np.hypot(d[:, 0], d[:, 1])
    con_talon = _rolling_nanmedian(con_talon, int(round(0.25 * fps)))
    sl = slice(start, end + 1)
    return {
        "a_cabeza_tobillos_address": float(bh[address]),
        "b_cadena_address": float(chain[address]),
        "c_vertical_max_rep": float(np.nanmax(bh[sl])),
        "d_cadena_max_rep": float(np.nanmax(chain[sl])),
        "e_cadena_talon_max_rep": float(np.nanmax(con_talon[sl])),
        "z_escala_exacta": float(bh[address]) / cociente,
    }


def scale_table(subject: str, view: str = "face_on", trials: list[str] | None = None) -> dict:
    """El sesgo de las métricas en cm contra la verdad 3-D, por candidata de
    escala, sobre TODOS los trials del sujeto que estén en `data/examples/`.

    Un sujeto, N swings: sale una media con límites de acuerdo de **este**
    golfista, no un MDC ni una referencia (ADR-009 nivel 1 mide la matemática
    y la convención, no el estimador).
    """
    import tempfile

    from kinelab.analysis import build_analysis, swing_signals
    from kinelab.explore import prepare_take_from_pose
    from kinelab.ingest.gate import CaptureJson
    from kinelab.perception.gaps import interpolate_gaps
    from kinelab.perception.posestore import load_pose
    from sports import get_sport

    trials = trials or sorted(p.stem for p in EXAMPLES.glob(f"{subject}_*.amc"))
    if not trials:
        raise ValueError(f"no hay ningún {subject}_NN.amc en {EXAMPLES}")
    filas: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="kinelab-escala-") as tmp:
        for trial in trials:
            mp = build(trial, view)
            take = Path(tmp) / trial
            write_pose(mp, take)
            prepare_take_from_pose(take / "pose.npz", take, view=view, note=fps_note(trial))
            capture = CaptureJson.model_validate_json((take / "capture.json").read_text(encoding="utf-8"))
            pose = load_pose(take)
            analysis = build_analysis(take, capture, pose, get_sport("golf"), height_m=mp.height_m)
            if not analysis["reps"]:
                filas.append({"trial": trial, "error": "0 repeticiones"})
                continue
            rep, ev0 = analysis["reps"][0], analysis["events"][0]
            ev = {k: (ev0[k] or {}).get("frame") for k in ("address", "top", "impact", "follow_end")}
            kp = interpolate_gaps(pose.keypoints, 5)
            P = mp.points_m
            ank = (P[ev["address"], H.LEFT_ANKLE, 1] + P[ev["address"], H.RIGHT_ANKLE, 1]) / 2.0
            aparente = float(P[ev["address"], H.HEAD, 1] - ank)
            cociente = aparente / float(mp.height_m)
            div = _scale_divisors(kp, CMU_FPS, ev["address"], rep["frame_start"], rep["frame_end"], cociente)
            metricas = {}
            for mid, (joints, axis, zero, at) in L1_DISPLACEMENTS.items():
                if mid not in rep["metrics"] or rep["metrics"][mid]["value"] is None:
                    continue
                f0, f1 = ev[zero], ev[at]
                signo = -1.0 if axis == 1 else 1.0  # y de imagen crece hacia abajo
                eje_img = 0 if axis in (0, 2) else 1
                d_px = float((kp[f1, list(joints)].mean(axis=0) - kp[f0, list(joints)].mean(axis=0))[eje_img] * signo)
                pt3 = P[:, list(joints)].mean(axis=1)
                metricas[mid] = {
                    "d_px": round(d_px, 3),
                    "verdad_3d_cm": round(100.0 * float(pt3[f1, axis] - pt3[f0, axis]), 3),
                    "motor_cm": rep["metrics"][mid]["value"],
                    "mdc": rep["metrics"][mid]["mdc"],
                    "cm": {c: round(d_px / div[c] * mp.height_m * 100.0, 3) for c in SCALE_CANDIDATES},
                }
            filas.append({
                "trial": trial, "cuadros": int(kp.shape[0]), "eventos": ev,
                "repeticion": [rep["frame_start"], rep["frame_end"]],
                "estatura_m": round(float(mp.height_m), 4),
                "cabeza_tobillos_m_en_address": round(aparente, 4),
                "aparente_sobre_estatura": round(cociente, 4),
                "divisores_px": {k: round(v, 1) for k, v in div.items()},
                "metricas": metricas,
            })
    ok = [f for f in filas if "error" not in f]
    ids = sorted({m for f in ok for m in f["metricas"]})
    resumen = {}
    for c in SCALE_CANDIDATES:
        por_metrica = {}
        for mid in ids:
            b = np.array([f["metricas"][mid]["cm"][c] - f["metricas"][mid]["verdad_3d_cm"] for f in ok if mid in f["metricas"]])
            sd = float(b.std(ddof=1)) if b.size > 1 else float("nan")
            por_metrica[mid] = {"n": int(b.size), "sesgo": round(float(b.mean()), 3), "loa": [round(float(b.mean()) - 1.96 * sd, 3), round(float(b.mean()) + 1.96 * sd, 3)]}
        abs_medio = float(np.mean([abs(por_metrica[m]["sesgo"]) for m in ids]))
        resumen[c] = {"por_metrica": por_metrica, "sesgo_abs_medio": round(abs_medio, 3), "sesgo_abs_max": round(max(abs(por_metrica[m]["sesgo"]) for m in ids), 3), "divisor_medio_px": round(float(np.mean([f["divisores_px"][c] for f in ok])), 1)}
    base = resumen["a_cabeza_tobillos_address"]
    for c in SCALE_CANDIDATES:
        peor = max(abs(resumen[c]["por_metrica"][m]["sesgo"]) - abs(base["por_metrica"][m]["sesgo"]) for m in ids)
        resumen[c]["empeora_mas_cm"] = round(peor, 3)
        resumen[c]["cumple_criterio"] = bool(resumen[c]["sesgo_abs_medio"] < base["sesgo_abs_medio"] / 2 and peor <= 1.0)
    coc = np.array([f["aparente_sobre_estatura"] for f in ok])
    return {
        "sujeto": subject, "vista": view, "n_trials": len(ok), "n_sujetos": 1,
        "aviso": "Diez swings de UN solo sujeto (CMU 64). Sale una media con límites de acuerdo de este golfista; no sale ningún MDC, ninguna referencia y ningún ideal.",
        "criterio": "la candidata entra si baja el |sesgo| medio a menos de la mitad del actual y no empeora ninguna métrica más de 1 cm (encargo 14)",
        "aparente_sobre_estatura": {"media": round(float(coc.mean()), 4), "sd": round(float(coc.std(ddof=1)), 4), "min": round(float(coc.min()), 4), "max": round(float(coc.max()), 4)},
        "trials": filas, "resumen": resumen,
    }


def print_scale_table(t: dict) -> None:
    ids = sorted(t["resumen"]["a_cabeza_tobillos_address"]["por_metrica"])
    print(f"\n  ESCALA · sujeto {t['sujeto']} · {t['vista']} · {t['n_trials']} trials — {t['aviso']}")
    c = t["aparente_sobre_estatura"]
    print(f"  cabeza→tobillos en address / estatura: media {c['media']:.4f} (sd {c['sd']:.4f}, {c['min']:.4f}–{c['max']:.4f}) → la escala vieja sobre-lee ×{1 / c['media']:.4f}")
    print(f"  {'trial':<8}{'apar/est':>9}{'addr':>6}{'rep':>12}" + "".join(f"{k.split('_')[0]:>9}" for k in SCALE_CANDIDATES))
    for f in t["trials"]:
        if "error" in f:
            print(f"  {f['trial']:<8}{f['error']}")
            continue
        print(f"  {f['trial']:<8}{f['aparente_sobre_estatura']:>9.4f}{f['eventos']['address']:>6}{str(f['repeticion']):>12}" + "".join(f"{f['divisores_px'][k]:>9.0f}" for k in SCALE_CANDIDATES))
    print(f"\n  sesgo medio [límites de acuerdo], en cm, contra la verdad 3-D en los cuadros del motor:")
    print(f"  {'métrica':<24}" + "".join(f"{k:>26}" for k in SCALE_CANDIDATES))
    for mid in ids:
        fila = f"  {mid:<24}"
        for k in SCALE_CANDIDATES:
            r = t["resumen"][k]["por_metrica"][mid]
            fila += f"{r['sesgo']:>9.2f} [{r['loa'][0]:>6.2f},{r['loa'][1]:>6.2f}]"
        print(fila)
    for campo, etiqueta in (("sesgo_abs_medio", "|sesgo| medio"), ("sesgo_abs_max", "|sesgo| max"), ("empeora_mas_cm", "empeora más"), ("divisor_medio_px", "divisor medio px")):
        print(f"  {etiqueta:<24}" + "".join(f"{t['resumen'][k][campo]:>26.3f}" for k in SCALE_CANDIDATES))
    print(f"  {'cumple el criterio':<24}" + "".join(f"{('SÍ' if t['resumen'][k]['cumple_criterio'] else 'no'):>26}" for k in SCALE_CANDIDATES))
    print(f"  criterio: {t['criterio']}")


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
    ap.add_argument("trial", help="id del trial, p. ej. 64_01 (el ASF se busca al lado: 64.asf). Con --escala alcanza con el sujeto: 64")
    ap.add_argument("--vista", default="face_on", choices=("face_on", "down_the_line"))
    ap.add_argument("--out", type=Path, default=None, help="carpeta de salida (la toma). Obligatoria salvo con --escala")
    ap.add_argument("--escala", action="store_true", help="la tabla de escala: sesgo de las métricas en cm contra la verdad 3-D, por candidata de divisor, sobre TODOS los trials del sujeto")
    ap.add_argument("--angulos", action="store_true", help="la tabla de ángulos: cuánto se equivoca la proyección contra el 3-D, por ángulo, vista y evento, sobre TODOS los trials del sujeto")
    ap.add_argument("--tabla", type=Path, default=None, help="con --escala o --angulos, dónde escribir la tabla en JSON")
    ap.add_argument("--asf", type=Path, default=None)
    ap.add_argument("--amc", type=Path, default=None)
    ap.add_argument("--solo-pose", action="store_true", help="escribir pose.npz y parar (sin eventos ni overlay)")
    ap.add_argument("--nivel1", action="store_true", help="además, la comparación 2-D contra la verdad 3-D (ADR-009 nivel 1)")
    ap.add_argument("--etiqueta", default=None, help="rótulo del trabajo.json del ejemplo; sin él no se escribe trabajo.json")
    ap.add_argument("--deporte", default="golf")
    args = ap.parse_args(argv)

    if args.escala or args.angulos:
        if args.escala and args.angulos:
            ap.error("--escala y --angulos son dos tablas distintas: una por corrida")
        tabla = scale_table(args.trial.split("_")[0], args.vista) if args.escala else angles_table(args.trial.split("_")[0])
        (print_scale_table if args.escala else print_angles_table)(tabla)
        if args.tabla:
            args.tabla.write_text(json.dumps(tabla, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {args.tabla}")
        return 0
    if args.out is None:
        ap.error("--out es obligatoria (salvo con --escala)")

    mp = build(args.trial, args.vista, asf=args.asf, amc=args.amc)
    pose_path = write_pose(mp, args.out)
    print(f"{pose_path}")
    print(f"  {mp.provenance['frames']} cuadros a {CMU_FPS:g} fps · estatura {mp.height_m:.3f} m · cuerpo {mp.body_height_px:.0f} px ({mp.body_height_px / mp.provenance['frame_size'][1] * 100:.1f} % del alto)")
    print(f"  cámara {args.vista} · f {mp.provenance['camera']['fx']:.1f} px · cuadro de referencia {mp.ref_frame}")
    if args.solo_pose:
        print(f"  {write_pose3d(mp, args.out)}")
        return 0

    from kinelab.explore import explore
    from sports import get_sport

    r = explore(None, args.out, get_sport(args.deporte), height_m=mp.height_m, view=args.vista, pose_npz=pose_path, nota_fuente=fps_note(args.trial), banner=banner_text(args.trial))
    print(f"  eventos {r['eventos_frame']} · {r['eventos_t_s']}")
    print(f"  duraciones {r['duraciones']}")
    # El 3-D va con los cuadros de evento que detectó el motor: son los mismos
    # que muestra el reproductor, así el visor y el video van al mismo cuadro.
    p3 = write_pose3d(mp, args.out, events=r["eventos_frame"])
    for f in [*r["archivos"], str(p3)]:
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
        # Una fila con `motor_2d` en `null` —una métrica que la vista no
        # habilita, como el thrust desde `face_on`— sigue mostrando la verdad.
        col = lambda v, w: f"{'—' if v is None else v:>{w}}"  # noqa: E731
        for f in tabla["filas"]:
            print(f"  {f['metrica']:<24}{col(f['motor_2d'], 10)}{col(f['verdad_3d_en_cuadros_del_motor'], 11)}{col(f['sesgo_solo_medicion'], 8)}   {col(f['verdad_3d_en_cuadros_3d'], 10)}{col(f['sesgo_total'], 8)}   {str(f['mdc']):>7}")
        print(f"  {args.out / 'nivel1-mocap.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
