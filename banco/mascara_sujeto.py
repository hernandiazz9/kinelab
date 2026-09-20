"""¿Qué compra sacar el fondo del video, y qué cuesta? Medido, no discutido.

Script de **banco**: mide, escribe números y no es parte del motor. Nada de
`kinelab/` lo importa, ninguna métrica lo lee, y no toca `analysis.json` ni
`pose.npz`.

La pregunta que contesta (encargo 32) no es «¿se ve lindo?» sino tres cosas
concretas, cada una con su número:

1. **El palo.** El error de eventos más grande medido es manos contra palo
   (4–16 cuadros, auditoría del 16/9 §1). El motor mide manos porque no ve el
   palo. Si una máscara de primer plano aísla el shaft como un componente fino
   y largo pegado a las manos, y una recta ajustada por cuadro coincide con lo
   que se ve, el top y el impacto **del palo** están al alcance.
2. **La escala.** El encargo 14 dejó un **+4,4 % residual** porque la cadena de
   la estatura arranca en el tobillo y la estatura declarada arranca en el
   piso. La extensión vertical de la máscara va de coronilla a suela y no tiene
   ese hueco.
3. **Etiquetas.** Una máscara del palo por cuadro abarata las etiquetas humanas
   que hacen falta para medir el error de eventos contra el palo.

Lo que **no** compra, y por eso no se intenta acá: ángulos articulares (una
silueta no tiene articulaciones) y correr pose sobre cuadros enmascarados (el
modelo se entrenó con fondos; lo medido dice que el error va por el bbox y la
plausibilidad, no por la entrada — `AGENTS.md` §Cosas que muerden).

## El método

Todo pasa en el marco del **cuadro de referencia**, estabilizado con la misma
homografía del fondo que mide la deriva de cámara (encargo 29): este script
**importa** `kinelab.tools.camera_drift` (`mascara`, `estimar`,
`alto_cuerpo_px`, `primer_cuadro_con_pose`) en vez de copiarlo. Sin estabilizar
no hay modelo de fondo posible: la imagen se corre hasta 119 px en el censo del
29, y un fondo que se corre 20 px es primer plano en todos sus bordes.

1. **Modelo de fondo = mediana temporal por píxel** sobre cuadros muestreados y
   estabilizados, **descartando de cada muestra los píxeles donde está el
   sujeto**. La ocupación del sujeto no es el `bbox` —es demasiado grande y
   deja al golfista sin fondo detrás en el 7,6 % del cuadro— sino una
   **silueta aproximada desde la pose**: los huesos de Halpe26 engrosados, el
   tronco relleno y un disco en la cabeza, todo dilatado. El palo **no** se
   enmascara acá: pasa por cada píxel en uno o dos cuadros de la muestra y la
   mediana no lo ve.
2. **Umbral por píxel**, no global: `max(--umbral, k · 1,4826 · MAD)` con el
   MAD temporal del propio modelo. El pasto y los árboles con viento tienen MAD
   alto y dejan de ser primer plano; el cielo tiene MAD ~0 y el palo se separa
   con 12 niveles de gris.
3. **Dos máscaras del mismo umbral**: la del **sujeto** (apertura chica +
   cierre grande, para la silueta y la extensión vertical) y la **fina**
   (apertura chica y nada más, menos lo que sobrevive a una apertura del
   grosor de un brazo): lo fino y largo, que es donde vive el palo.
4. **El palo** se busca con una Hough anclada en las muñecas —el ángulo que
   junta más píxeles finos en una banda que pasa por la mano— y se refina con
   `cv2.fitLine`. Anclar en la mano es lo que aguanta que el shaft salga
   punteado por el desenfoque de movimiento.

Además del fondo **global** (muestras de todo el clip) el script construye
fondos **locales** (mediana de una ventana de ±N cuadros alrededor de un
evento). Los dos miden cosas distintas y las dos hacen falta: el global no
tiene fondo detrás del golfista —nunca se corre del lugar— y el local sí lo
tiene, porque en media segundo el cuerpo casi no se mueve; a cambio, el local
sólo ve lo **rápido**, que es justamente el palo.

## Procedencias

- La **máscara**, la recta del palo y la extensión vertical son `medido_aqui`.
- Las **etiquetas a ojo** del shaft son `estimacion`, hechas por la sesión
  mirando el PNG. No son una medición y no se las llama así en ningún lado.
- Los umbrales (`--umbral`, `--k-mad`, grosores, radios) son `estimacion`: no
  salen de ningún barrido, se eligieron del orden de lo medido acá.

Uso:

    python banco/mascara_sujeto.py VIDEO --pose DIR [--cada 10] [--palo 1284 --palo 1364]

Deja todo en `<video>.kinelab/mascara/` (o en `--salida`): el JSON con los
números, los PNG de los cuadros etiquetados con la recta dibujada, y los
recortes con grilla para poner las etiquetas a ojo (`--recortes`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from kinelab.perception.keypoints import H, HALPE26_LIMBS
from kinelab.perception.posestore import POSE_FILE, PoseData, finite_or_none, load_pose
from kinelab.perception.video import iter_frames
from kinelab.tools.camera_drift import (
    Params as DriftParams,
    alto_cuerpo_px,
    estimar,
    mascara as mascara_fondo_sift,
    primer_cuadro_con_pose,
)
from kinelab.tools.fps_truth import FfprobeError, probe_declared
from kinelab.tools.interpolar import ascii_para_quemar

# Todos los tamaños van en **altos de cuerpo**, no en píxeles: el mismo número
# tiene que servir en un cuerpo de 691 px (cortado3-lento) y en uno de 1104
# (vid1, UHD). Procedencia de todos: `estimacion`.
GROSOR_HUESO = 0.07       # ancho de un hueso al dibujar la silueta de ocupación
RADIO_CABEZA = 0.09       # disco de la cabeza en esa silueta
DILATACION_SILUETA = 0.04  # cuánto se dilata la silueta antes de usarla
APERTURA = 0.005          # apertura morfológica de la máscara cruda
CIERRE = 0.022            # cierre de la máscara del sujeto
CIERRE_FINO = 0.010       # cierre, más chico, antes de separar fino de cuerpo
GROSOR_BRAZO = 0.028      # radio de la apertura que separa «fino» de «cuerpo»
AREA_MIN = 0.02           # lado mínimo de un componente, en altos de cuerpo
AREA_MIN_FINA = 0.015     # ídem, para la máscara fina (el shaft sale en pedazos)
BANDA_PALO = 0.012        # medio ancho de la banda de la Hough anclada
LARGO_MAX_PALO = 1.05     # hasta dónde se busca shaft desde las muñecas
LARGO_MIN_PALO = 0.05     # y desde dónde: adentro de la mano no hay recta
UMBRAL = 12.0             # piso del umbral de diferencia, en niveles de 0–255
K_MAD = 3.0               # múltiplos de MAD (×1,4826) por encima del piso
MUESTRAS_FONDO = 64
VENTANA_LOCAL = 120       # ±cuadros del fondo local
PASO_LOCAL = 4            # cada cuántos cuadros se muestrea esa ventana


class MascaraError(RuntimeError):
    """El clip, la pose o los parámetros no permiten medir."""


@dataclass(frozen=True)
class Params:
    umbral: float = UMBRAL
    k_mad: float = K_MAD
    grosor_hueso: float = GROSOR_HUESO
    radio_cabeza: float = RADIO_CABEZA
    dilatacion_silueta: float = DILATACION_SILUETA
    apertura: float = APERTURA
    cierre: float = CIERRE
    cierre_fino: float = CIERRE_FINO
    grosor_brazo: float = GROSOR_BRAZO
    area_min: float = AREA_MIN
    area_min_fina: float = AREA_MIN_FINA
    banda_palo: float = BANDA_PALO
    largo_max_palo: float = LARGO_MAX_PALO
    largo_min_palo: float = LARGO_MIN_PALO
    color: bool = True
    # Cómo se dibuja «acá está el sujeto» para sacarlo de la mediana del fondo.
    # `silueta` es la del método; las otras dos están para medir qué cuesta
    # elegir mal, que es lo que decidió este parámetro (ver el informe del 32).
    ocupacion: str = "silueta"   # silueta | bbox | bbox-y-palo

    def __post_init__(self) -> None:
        if self.ocupacion not in ("silueta", "bbox", "bbox-y-palo"):
            raise ValueError(f"--ocupacion tiene que ser silueta, bbox o bbox-y-palo; llegó {self.ocupacion!r}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["unidad_de_los_tamanos"] = "altos de cuerpo (alto_cuerpo_px)"
        d["procedencia_umbrales"] = "estimacion"
        return d


def _impar(v: float, minimo: int = 3) -> int:
    n = int(round(v))
    if n % 2 == 0:
        n += 1
    return max(minimo, n)


def _elipse(lado: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (lado, lado))


# ---------------------------------------------------------------- silueta

def silueta_pose(shape: tuple[int, int], pose: PoseData, frame: int, alto_px: float, p: Params) -> np.ndarray:
    """255 donde la pose dice que está el sujeto, 0 donde no.

    Es una silueta **aproximada**, dibujada desde los keypoints: no mide nada,
    sólo decide qué píxeles de cada muestra no entran a la mediana del fondo.
    El palo queda afuera a propósito (ver el encabezado del módulo).
    """
    alto, ancho = shape[:2]
    if p.ocupacion != "silueta":
        # Los dos controles: el `bbox` crudo, y el `bbox` con el disco del palo
        # del encargo 29 encima. `mascara` devuelve 255 en el FONDO, así que se
        # invierte, y el disco del palo se enciende o se apaga con `con_palo`.
        dp = DriftParams(dilatacion=0.0, con_palo=(p.ocupacion == "bbox-y-palo"))
        return 255 - mascara_fondo_sift((alto, ancho), pose, frame, alto_px, dp)
    s = np.zeros((alto, ancho), np.uint8)
    k = np.asarray(pose.keypoints[frame], dtype=float)
    grosor = max(3, int(round(p.grosor_hueso * alto_px)))
    for a, b in HALPE26_LIMBS:
        if np.isfinite(k[a]).all() and np.isfinite(k[b]).all():
            cv2.line(s, tuple(k[a].round().astype(int)), tuple(k[b].round().astype(int)), 255, grosor)
    tronco = [H.LEFT_SHOULDER, H.RIGHT_SHOULDER, H.RIGHT_HIP, H.LEFT_HIP]
    if np.isfinite(k[tronco]).all():
        cv2.fillPoly(s, [k[tronco].round().astype(np.int32)], 255)
    if np.isfinite(k[H.HEAD]).all():
        cv2.circle(s, tuple(k[H.HEAD].round().astype(int)), int(round(p.radio_cabeza * alto_px)), 255, -1)
    if p.dilatacion_silueta > 0:
        s = cv2.dilate(s, _elipse(_impar(2 * p.dilatacion_silueta * alto_px + 1)))
    return s


# ---------------------------------------------------------------- fondo

@dataclass
class Fondo:
    """El modelo de fondo en el marco del cuadro de referencia."""

    mediana: np.ndarray       # (H,W,3) o (H,W) uint8
    mad: np.ndarray           # lo mismo, float32
    sin_fondo: np.ndarray     # (H,W) bool: ningún cuadro mostró ese píxel sin sujeto
    libre_frac: np.ndarray    # (H,W) float32
    n: int
    frames: tuple[int, ...]
    etiqueta: str
    segundos: float

    def resumen(self) -> dict:
        return {
            "etiqueta": self.etiqueta,
            "cuadros": self.n,
            "primer_cuadro": self.frames[0] if self.frames else None,
            "ultimo_cuadro": self.frames[-1] if self.frames else None,
            "sin_fondo_frac_del_cuadro": float(self.sin_fondo.mean()),
            "sin_fondo_px": int(self.sin_fondo.sum()),
            "libre_frac_mediana": float(np.median(self.libre_frac)),
            "mad_mediano": float(np.median(self.mad[~self.sin_fondo])) if (~self.sin_fondo).any() else None,
            "segundos": self.segundos,
        }


def _median_enmascarada(
    pila: np.ndarray, libre: np.ndarray, banda: int = 96,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Mediana y MAD por píxel sobre las muestras donde el píxel estaba libre.

    Dos cuidados, los dos por memoria y por tiempo:

    - se recorre por **franjas de filas**: un `abs(pila − mediana)` entero en
      float32 son 1,6 GB en FHD con 64 muestras, y 6,4 en UHD;
    - los píxeles libres en **todas** las muestras (la enorme mayoría) van por
      la mediana rápida de numpy y sólo los que tienen alguna muestra tapada
      pasan por `nanmedian`, que es un orden de magnitud más lenta. El
      resultado es el mismo; lo que cambia es que un clip tarda segundos y no
      minutos.
    """
    forma = pila.shape[1:]
    alto = forma[0]
    mediana = np.zeros(forma, np.float32)
    mad = np.zeros(forma, np.float32)
    for y0 in range(0, alto, banda):
        y1 = min(alto, y0 + banda)
        sub = pila[:, y0:y1]
        lib = libre[:, y0:y1]
        siempre = lib.all(axis=0)
        alguna = lib.any(axis=0)
        med = np.median(sub, axis=0).astype(np.float32)
        dev = np.median(np.abs(sub.astype(np.float32) - med), axis=0).astype(np.float32)
        parcial = alguna & ~siempre
        if parcial.any():
            s = sub[:, parcial].astype(np.float32)          # (n, m[, 3])
            l = lib[:, parcial]                              # (n, m)
            if s.ndim == 3:
                l = l[:, :, None]
            s[~np.broadcast_to(l, s.shape)] = np.nan
            with np.errstate(all="ignore"):
                m = np.nanmedian(s, axis=0)
                d = np.nanmedian(np.abs(s - m), axis=0)
            med[parcial] = np.nan_to_num(m)
            dev[parcial] = np.nan_to_num(d)
            del s, l
        # Sin ninguna muestra libre no hay fondo: queda la mediana cruda —que
        # es el propio sujeto— para poder dibujarla, y el píxel se marca.
        dev[~alguna] = 0.0
        mediana[y0:y1] = med
        mad[y0:y1] = dev
    sin = ~libre.any(axis=0)
    libre_frac = libre.mean(axis=0, dtype=np.float32)
    return mediana.astype(np.uint8), mad, sin, libre_frac


def construir_fondo(
    imagenes: dict[int, np.ndarray],
    homografias: dict[int, np.ndarray],
    pose: PoseData,
    alto_px: float,
    p: Params,
    *,
    etiqueta: str,
    enmascarar: bool,
    forma: tuple[int, int],
) -> Fondo:
    """La mediana temporal de los cuadros estabilizados al marco de referencia.

    `enmascarar=False` deja al sujeto adentro del modelo a propósito: sobre una
    ventana corta el cuerpo casi no se mueve, entra en la mediana, y lo que
    queda de primer plano es sólo lo **rápido** — el palo.
    """
    t0 = time.time()
    frames = tuple(sorted(i for i in imagenes if i in homografias))
    if not frames:
        raise MascaraError(f"fondo «{etiqueta}»: ningún cuadro de la muestra tiene homografía")
    alto, ancho = forma
    muestra = imagenes[frames[0]]
    canales = () if muestra.ndim == 2 else (muestra.shape[2],)
    pila = np.zeros((len(frames), alto, ancho, *canales), np.uint8)
    libre = np.zeros((len(frames), alto, ancho), bool)
    inv = cv2.WARP_INVERSE_MAP
    for k, i in enumerate(frames):
        m = homografias[i]
        pila[k] = cv2.warpPerspective(imagenes[i], m, (ancho, alto), flags=inv | cv2.INTER_LINEAR)
        if enmascarar:
            sil = 255 - silueta_pose((alto, ancho), pose, i, alto_px, p)
        else:
            sil = np.full((alto, ancho), 255, np.uint8)
        libre[k] = cv2.warpPerspective(sil, m, (ancho, alto), flags=inv | cv2.INTER_NEAREST) > 127
    mediana, mad, sin, libre_frac = _median_enmascarada(pila, libre)
    del pila, libre
    return Fondo(mediana, mad, sin, libre_frac, len(frames), frames, etiqueta, time.time() - t0)


# ---------------------------------------------------------------- máscara

@dataclass(frozen=True)
class Mascaras:
    sujeto: np.ndarray   # uint8 0/255, con cierre: la silueta
    fina: np.ndarray     # uint8 0/255, lo fino y largo: donde vive el palo
    valido: np.ndarray   # bool: dónde el modelo de fondo dice algo
    ms: float


def primer_plano(
    imagen: np.ndarray,
    homografia: np.ndarray,
    fondo: Fondo,
    alto_px: float,
    p: Params,
    *,
    pose: PoseData | None = None,
    frame: int | None = None,
) -> Mascaras:
    """La máscara de primer plano de un cuadro contra el modelo de fondo.

    Devuelve dos máscaras del **mismo** umbral: la del sujeto (con cierre, para
    la silueta) y la fina (lo que no sobrevive a una apertura del grosor de un
    brazo, menos la silueta de la pose, que es donde vive el palo).
    """
    t0 = time.time()
    alto, ancho = imagen.shape[:2]
    m = homografia
    bg = cv2.warpPerspective(fondo.mediana, m, (ancho, alto), flags=cv2.INTER_LINEAR).astype(np.float32)
    mad = cv2.warpPerspective(fondo.mad, m, (ancho, alto), flags=cv2.INTER_LINEAR)
    dentro = cv2.warpPerspective(np.full(fondo.sin_fondo.shape, 255, np.uint8), m, (ancho, alto), flags=cv2.INTER_NEAREST) > 127
    con_fondo = cv2.warpPerspective((~fondo.sin_fondo).astype(np.uint8) * 255, m, (ancho, alto), flags=cv2.INTER_NEAREST) > 127
    valido = dentro & con_fondo

    dif = np.abs(imagen.astype(np.float32) - bg)
    umbral = np.maximum(p.umbral, p.k_mad * 1.4826 * mad)
    cruda = (dif > umbral)
    if cruda.ndim == 3:
        cruda = cruda.any(axis=2)
    cruda = (cruda & valido).astype(np.uint8) * 255

    cruda = cv2.morphologyEx(cruda, cv2.MORPH_OPEN, _elipse(_impar(p.apertura * alto_px)))
    sujeto = cv2.morphologyEx(cruda, cv2.MORPH_CLOSE, _elipse(_impar(p.cierre * alto_px)))
    sujeto = _sin_motas(sujeto, (p.area_min * alto_px) ** 2)
    # Lo fino: primero un cierre chico —sin él la máscara del cuerpo, que sale
    # rota, «es fina» entera— y después lo que no sobrevive a una apertura del
    # grosor de un brazo.
    base = cv2.morphologyEx(cruda, cv2.MORPH_CLOSE, _elipse(_impar(p.cierre_fino * alto_px)))
    cuerpo = cv2.morphologyEx(base, cv2.MORPH_OPEN, _elipse(_impar(2 * p.grosor_brazo * alto_px + 1)))
    fina = cv2.bitwise_and(base, cv2.bitwise_not(cuerpo))
    if pose is not None and frame is not None:
        fina = cv2.bitwise_and(fina, cv2.bitwise_not(silueta_pose(fina.shape, pose, frame, alto_px, p)))
    fina = _sin_motas(fina, (p.area_min_fina * alto_px) ** 2)
    return Mascaras(sujeto, fina, valido, 1000.0 * (time.time() - t0))


def _sin_motas(m: np.ndarray, area_min: float) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return m
    chico = np.zeros(n, bool)
    chico[1:] = stats[1:, cv2.CC_STAT_AREA] < area_min
    out = m.copy()
    out[chico[lab]] = 0
    return out


# ------------------------------------------------------- indicadores del punto 1

@dataclass(frozen=True)
class Indicadores:
    frame: int
    cobertura_bbox: float | None
    keypoints_en_mascara: int | None
    keypoints_visibles: int | None
    agujeros: int | None
    agujeros_area_frac: float | None
    componentes: int | None
    mascara_frac_del_cuadro: float
    ms: float
    null_reason: str | None = None


def indicadores(m: Mascaras, pose: PoseData, frame: int) -> Indicadores:
    """Cuánto de lo que la pose dice que es el sujeto cubre la máscara."""
    alto, ancho = m.sujeto.shape[:2]
    frac = float((m.sujeto > 0).mean())
    caja = np.asarray(pose.bbox[frame], dtype=float)
    cobertura = None
    if np.isfinite(caja).all():
        x0, y0, x1, y1 = [int(round(v)) for v in caja]
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(ancho, x1), min(alto, y1)
        if x1 > x0 and y1 > y0:
            cobertura = float((m.sujeto[y0:y1, x0:x1] > 0).mean())
    k = np.asarray(pose.keypoints[frame], dtype=float)
    s = np.asarray(pose.scores[frame], dtype=float)
    vis = np.isfinite(k).all(axis=1) & (s > 0.3)
    dentro = 0
    for x, y in k[vis].round().astype(int):
        if 0 <= y < alto and 0 <= x < ancho and m.sujeto[y, x] > 0:
            dentro += 1
    # Agujeros: componentes del complemento que no tocan el borde de la imagen,
    # dentro del componente más grande de la máscara.
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m.sujeto, 8)
    agujeros, area_ag = None, None
    if n > 1:
        mayor = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        cuerpo = (lab == mayor).astype(np.uint8) * 255
        relleno = cuerpo.copy()
        h, w = relleno.shape
        cv2.floodFill(relleno, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
        # Lo que quedó en 0 no es cuerpo y tampoco se alcanza desde afuera: es
        # un agujero. (El `floodFill` arranca en (0,0), que está fuera de la
        # máscara: si algún día no lo estuviera, esto contaría de más.)
        huecos = cv2.bitwise_not(relleno)
        nh, _, sh, _ = cv2.connectedComponentsWithStats(huecos, 8)
        agujeros = max(0, nh - 1)
        area_cuerpo = float(stats[mayor, cv2.CC_STAT_AREA])
        area_ag = float(sh[1:, cv2.CC_STAT_AREA].sum() / area_cuerpo) if nh > 1 and area_cuerpo else 0.0
    return Indicadores(frame, cobertura, dentro, int(vis.sum()), agujeros, area_ag,
                       None if n <= 1 else n - 1, frac, m.ms)


# ------------------------------------------------------- el palo (punto 2)

@dataclass(frozen=True)
class Recta:
    frame: int
    modelo: str                       # «global» o «local»
    angulo_deg: float | None          # de la recta, 0–180, x a la derecha e y hacia ABAJO
    largo_px: float | None            # extremo a extremo del shaft VISIBLE en la máscara
    largo_desde_mano_px: float | None  # de la muñeca proyectada a la punta
    mango_px: tuple[float, float] | None   # extremo más cercano a las muñecas
    punta_px: tuple[float, float] | None   # el otro: la cabeza del palo
    pixeles: int | None
    munecas_px: tuple[float, float] | None
    null_reason: str | None = None

    def to_dict(self) -> dict:
        return finite_or_none(asdict(self))


def _angulo(u: np.ndarray) -> float:
    """Ángulo de una dirección **no orientada**, en [0, 180)."""
    a = float(np.degrees(np.arctan2(u[1], u[0])))
    return a % 180.0


def dif_angular(a: float, b: float) -> float:
    """Diferencia entre dos ángulos de recta no orientada, en [0, 90]."""
    d = abs(a - b) % 180.0
    return float(min(d, 180.0 - d))


def buscar_palo(
    fina: np.ndarray,
    pose: PoseData,
    frame: int,
    alto_px: float,
    p: Params,
    *,
    modelo: str,
) -> Recta:
    """La recta del shaft: Hough anclada en las muñecas y refinada con `fitLine`.

    Anclar en la mano es lo que aguanta el shaft punteado: en el impacto el
    palo barre decenas de píxeles durante la exposición y la máscara lo devuelve
    en pedazos, que ninguna componente conexa junta. Lo que sí los junta es que
    todos caen sobre una recta que pasa por la mano.
    """
    mun = np.nanmean(np.asarray(pose.keypoints[frame, [H.LEFT_WRIST, H.RIGHT_WRIST], :], dtype=float), axis=0)
    if not np.isfinite(mun).all():
        return Recta(frame, modelo, None, None, None, None, None, None, None, "sin muñecas en la pose")
    ys, xs = np.nonzero(fina)
    if xs.size == 0:
        return Recta(frame, modelo, None, None, None, None, None, 0, (float(mun[0]), float(mun[1])), "la máscara fina está vacía")
    pts = np.stack([xs, ys], axis=1).astype(np.float32)
    rel = pts - mun
    d = np.linalg.norm(rel, axis=1)
    dentro = (d >= p.largo_min_palo * alto_px) & (d <= p.largo_max_palo * alto_px)
    if dentro.sum() < 20:
        return Recta(frame, modelo, None, None, None, None, None, int(dentro.sum()), (float(mun[0]), float(mun[1])),
                     f"{int(dentro.sum())} píxeles finos alrededor de la mano; hacen falta 20")
    rel, pts = rel[dentro].astype(np.float32), pts[dentro]
    banda = p.banda_palo * alto_px
    # Hough anclada: el ángulo que junta más píxeles en una banda por la mano.
    thetas = np.radians(np.arange(0.0, 180.0, 0.5))
    u = np.stack([np.cos(thetas), np.sin(thetas)], axis=1).astype(np.float32)   # (A,2)
    perp = np.array([[0.0, 1.0], [-1.0, 0.0]], np.float32)
    cruz = np.abs(rel @ perp @ u.T)                                  # |rel × u| por ángulo
    proy = rel @ u.T
    en_banda = cruz <= banda
    # Un lado solo: el shaft sale de la mano hacia un lado, no hacia los dos.
    conteo = np.maximum((en_banda & (proy > 0)).sum(axis=0), (en_banda & (proy < 0)).sum(axis=0))
    mejor = int(np.argmax(conteo))
    if conteo[mejor] < 20:
        return Recta(frame, modelo, None, None, None, None, None, int(conteo[mejor]), (float(mun[0]), float(mun[1])),
                     f"el mejor ángulo junta {int(conteo[mejor])} píxeles; hacen falta 20")
    signo = 1.0 if (en_banda[:, mejor] & (proy[:, mejor] > 0)).sum() >= (en_banda[:, mejor] & (proy[:, mejor] < 0)).sum() else -1.0
    sel = en_banda[:, mejor] & (signo * proy[:, mejor] > 0)
    # Refinar, y volver a elegir los píxeles con la recta refinada. La banda
    # anclada en la muñeca se queda corta en la punta: la muñeca que predice la
    # red no está sobre el eje del shaft, y 2° de error a 400 px son 14 px, más
    # que la banda entera. Con la recta suelta la punta vuelve a entrar.
    dirn = np.array([np.cos(thetas[mejor]), np.sin(thetas[mejor])], dtype=float) * signo
    base = mun.astype(float)
    for _ in range(3):
        inl = pts[sel]
        if inl.shape[0] < 20:
            break
        vx, vy, x0, y0 = [float(v) for v in cv2.fitLine(inl, cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()]
        nueva = np.array([vx, vy], dtype=float)
        dirn = nueva if nueva @ dirn >= 0 else -nueva          # sin invertir el lado
        base = np.array([x0, y0], dtype=float)
        rel_b = pts - base
        dist = np.abs(rel_b[:, 0] * dirn[1] - rel_b[:, 1] * dirn[0])
        t = rel_b @ dirn
        t_mun = float((mun - base) @ dirn)
        otra = (dist <= banda) & (t - t_mun > 0) & (t - t_mun <= p.largo_max_palo * alto_px)
        if otra.sum() < 20 or np.array_equal(otra, sel):
            sel = otra if otra.sum() >= 20 else sel
            break
        sel = otra
    inl = pts[sel]
    t = (inl - base) @ dirn
    t_mun = float((mun - base) @ dirn)
    mango = base + dirn * t.min()
    punta = base + dirn * t.max()
    return Recta(
        frame, modelo, _angulo(dirn), float(t.max() - t.min()), float(t.max() - t_mun),
        (float(mango[0]), float(mango[1])), (float(punta[0]), float(punta[1])),
        int(sel.sum()), (float(mun[0]), float(mun[1])), None,
    )


# ------------------------------------------------------- la escala (punto 3)

@dataclass(frozen=True)
class Extension:
    frame: int
    alto_mascara_px: float | None
    y_arriba: float | None
    y_abajo: float | None
    area_px: int | None
    cociente_contra_cadena: float | None
    # Contra qué se compara cada extremo: la coronilla tiene que quedar ARRIBA
    # del punto `head` de Halpe26 (que es la cara, no la coronilla) y la suela
    # ABAJO del tobillo. Si sobra mucho por abajo, lo que entró es la sombra.
    y_head_kp: float | None = None
    y_tobillo_kp: float | None = None
    sobra_arriba_px: float | None = None
    sobra_abajo_px: float | None = None
    null_reason: str | None = None


def extension_vertical(m: Mascaras, pose: PoseData, frame: int, scale_px: float | None) -> Extension:
    """Coronilla a suela del componente de la máscara que contiene al sujeto."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m.sujeto, 8)
    if n <= 1:
        return Extension(frame, None, None, None, None, None, "la máscara del sujeto está vacía")
    k = np.asarray(pose.keypoints[frame], dtype=float)
    s = np.asarray(pose.scores[frame], dtype=float)
    vis = np.isfinite(k).all(axis=1) & (s > 0.3)
    alto_img, ancho_img = m.sujeto.shape[:2]
    votos: dict[int, int] = {}
    for x, y in k[vis].round().astype(int):
        if 0 <= y < alto_img and 0 <= x < ancho_img and lab[y, x] > 0:
            votos[int(lab[y, x])] = votos.get(int(lab[y, x]), 0) + 1
    if not votos:
        return Extension(frame, None, None, None, None, None, "ningún keypoint cae adentro de la máscara")
    etiqueta = max(votos, key=lambda e: votos[e])
    y0 = float(stats[etiqueta, cv2.CC_STAT_TOP])
    alto_m = float(stats[etiqueta, cv2.CC_STAT_HEIGHT])
    y_head = float(k[H.HEAD, 1]) if np.isfinite(k[H.HEAD, 1]) else None
    tob = np.asarray(k[[H.LEFT_ANKLE, H.RIGHT_ANKLE], 1], dtype=float)
    y_tob = float(np.nanmean(tob)) if np.isfinite(tob).any() else None
    return Extension(
        frame, alto_m, y0, y0 + alto_m, int(stats[etiqueta, cv2.CC_STAT_AREA]),
        None if not scale_px else alto_m / scale_px,
        y_head, y_tob,
        None if y_head is None else y_head - y0,
        None if y_tob is None else (y0 + alto_m) - y_tob,
    )


# ---------------------------------------------------------------- dibujo

def _rotulo(img: np.ndarray, texto: str, x: int, y: int, color, fs: float) -> None:
    t = ascii_para_quemar(texto)
    cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, t, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, color, 1, cv2.LINE_AA)


def dibujar_palo(
    destino: Path, imagen: np.ndarray, m: Mascaras, r: Recta, etiqueta: dict | None,
    alto_px: float, titulo: str,
) -> Path:
    """El cuadro con la máscara encima, la recta ajustada y la etiqueta a ojo."""
    img = imagen.copy() if imagen.ndim == 3 else cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)
    img[m.sujeto > 0] = (0.55 * img[m.sujeto > 0] + np.array([0, 0, 110])).clip(0, 255).astype(np.uint8)
    img[m.fina > 0] = (0.35 * img[m.fina > 0] + np.array([60, 200, 60])).clip(0, 255).astype(np.uint8)
    if r.mango_px and r.punta_px:
        cv2.line(img, tuple(np.round(r.mango_px).astype(int)), tuple(np.round(r.punta_px).astype(int)),
                 (255, 80, 255), 2, cv2.LINE_AA)
        cv2.circle(img, tuple(np.round(r.punta_px).astype(int)), 7, (255, 80, 255), 2, cv2.LINE_AA)
    if etiqueta and etiqueta.get("mango") and etiqueta.get("punta"):
        cv2.line(img, tuple(np.round(etiqueta["mango"]).astype(int)), tuple(np.round(etiqueta["punta"]).astype(int)),
                 (60, 220, 255), 2, cv2.LINE_AA)
        cv2.circle(img, tuple(np.round(etiqueta["punta"]).astype(int)), 7, (60, 220, 255), 2, cv2.LINE_AA)
    alto, ancho = img.shape[:2]
    fs = max(0.5, alto / 1800.0)
    lineas = [titulo,
              (f"recta: {r.angulo_deg:.1f} grados, {r.largo_px:.0f} px, {r.pixeles} px finos"
               if r.angulo_deg is not None else f"sin recta: {r.null_reason}"),
              "magenta: recta ajustada (medida) · amarillo: etiqueta a ojo (estimacion)",
              "rojo: mascara del sujeto · verde: mascara fina"]
    for j, t in enumerate(lineas):
        _rotulo(img, t, 10, int(30 * fs * (j + 1) * 1.3), (255, 255, 255), fs)
    if r.munecas_px:
        cv2.circle(img, tuple(np.round(r.munecas_px).astype(int)), int(0.02 * alto_px), (255, 255, 255), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(destino), img):
        raise MascaraError(f"no se pudo escribir {destino}")
    return destino


def dibujar_extension(
    destino: Path, imagen: np.ndarray, m: Mascaras, e: Extension, pose: PoseData, frame: int,
    scale_px: float | None,
) -> Path:
    """La máscara con sus dos extremos verticales dibujados, para ver qué mide.

    Es la pregunta del punto 3: si la extensión de la máscara va de coronilla a
    suela, el cociente contra la cadena de la estatura tendría que dar 1,044.
    Lo que sobre por abajo —una sombra, por ejemplo— infla el número sin que
    nada lo delate, así que se dibuja.
    """
    img = imagen.copy() if imagen.ndim == 3 else cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)
    img[m.sujeto > 0] = (0.55 * img[m.sujeto > 0] + np.array([0, 0, 110])).clip(0, 255).astype(np.uint8)
    ancho = img.shape[1]
    fs = max(0.5, img.shape[0] / 1800.0)
    for y, color, rot in ((e.y_arriba, (60, 220, 255), "arriba de la mascara"),
                          (e.y_abajo, (60, 220, 255), "abajo de la mascara"),
                          (e.y_head_kp, (255, 255, 255), "punto head de Halpe26 (la cara, no la coronilla)"),
                          (e.y_tobillo_kp, (255, 255, 255), "tobillos")):
        if y is None:
            continue
        cv2.line(img, (0, int(y)), (ancho, int(y)), color, 2, cv2.LINE_AA)
        _rotulo(img, f"{rot}: y {y:.0f}", 10, int(y) - 6, color, fs)
    lineas = [f"cuadro {frame} · mascara {e.alto_mascara_px:.0f} px" if e.alto_mascara_px else f"cuadro {frame} · sin mascara",
              (f"cadena de la estatura {scale_px:.1f} px · cociente {e.cociente_contra_cadena:.4f} "
               f"(si fuera coronilla a suela: 1.044)") if e.cociente_contra_cadena else "sin escala con que comparar"]
    for j, t in enumerate(lineas):
        _rotulo(img, t, 10, int(30 * fs * (j + 1) * 1.3), (255, 255, 255), fs)
    if not cv2.imwrite(str(destino), img):
        raise MascaraError(f"no se pudo escribir {destino}")
    return destino


def recorte_con_grilla(
    destino: Path, imagen: np.ndarray, pose: PoseData, frame: int, alto_px: float,
    *, radio: float = 0.85, zoom: float = 1.0,
) -> Path:
    """El recorte alrededor de las muñecas con una grilla rotulada en coordenadas
    del cuadro entero, para poner las etiquetas a ojo sin convertir nada."""
    img = imagen.copy() if imagen.ndim == 3 else cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGR)
    alto, ancho = img.shape[:2]
    mun = np.nanmean(np.asarray(pose.keypoints[frame, [H.LEFT_WRIST, H.RIGHT_WRIST], :], dtype=float), axis=0)
    if not np.isfinite(mun).all():
        caja = np.asarray(pose.bbox[frame], dtype=float)
        mun = np.array([(caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2])
    r = int(round(radio * alto_px))
    x0, y0 = int(max(0, mun[0] - r)), int(max(0, mun[1] - r))
    x1, y1 = int(min(ancho, mun[0] + r)), int(min(alto, mun[1] + r))
    sub = img[y0:y1, x0:x1].copy()
    # La grilla va en una capa aparte y se mezcla al 45 %: una grilla opaca tapa
    # justo lo que hay que mirar, que es un shaft de 4 px de ancho.
    capa = sub.copy()
    paso = 100
    for x in range(int(np.ceil(x0 / paso)) * paso, x1, paso):
        cv2.line(capa, (x - x0, 0), (x - x0, y1 - y0), (0, 255, 255), 1, cv2.LINE_AA)
    for y in range(int(np.ceil(y0 / paso)) * paso, y1, paso):
        cv2.line(capa, (0, y - y0), (x1 - x0, y - y0), (0, 255, 255), 1, cv2.LINE_AA)
    sub = cv2.addWeighted(capa, 0.45, sub, 0.55, 0)
    if zoom != 1.0:
        sub = cv2.resize(sub, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_CUBIC)
    for x in range(int(np.ceil(x0 / paso)) * paso, x1, paso):
        _rotulo(sub, str(x), int((x - x0) * zoom) + 3, int(18 * max(1.0, zoom)), (0, 255, 255), 0.45 * max(1.0, zoom))
    for y in range(int(np.ceil(y0 / paso)) * paso, y1, paso):
        _rotulo(sub, str(y), 3, int((y - y0) * zoom) - 4, (0, 255, 255), 0.45 * max(1.0, zoom))
    _rotulo(sub, f"cuadro {frame} · coordenadas del cuadro entero · grilla 100 px · zoom x{zoom:g}",
            3, sub.shape[0] - 10, (255, 255, 255), 0.5 * max(1.0, zoom))
    if not cv2.imwrite(str(destino), sub):
        raise MascaraError(f"no se pudo escribir {destino}")
    return destino


# ---------------------------------------------------------------- corrida

def _homografias(
    imagenes: dict[int, np.ndarray], gris_ref: np.ndarray, mask_ref: np.ndarray,
    pose: PoseData, alto_px: float, dp: DriftParams, sift, ref_pre,
) -> tuple[dict[int, np.ndarray], dict[int, str]]:
    hs, fallas = {}, {}
    for i, img in imagenes.items():
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        m = mascara_fondo_sift(g.shape, pose, i, alto_px, dp)
        modelo, razon = estimar(gris_ref, mask_ref, g, m, dp, sift=sift, ref_precomputado=ref_pre)
        if modelo is None:
            fallas[i] = razon or "sin homografía"
        else:
            hs[i] = modelo.matriz
    return hs, fallas


def _decodificar(video: Path, rot: int, display: tuple[int, int], quiero: set[int], color: bool) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    if not quiero:
        return out
    tope = max(quiero)
    for i, f in iter_frames(video, rotation_deg=rot, display_size=display):
        if i in quiero:
            out[i] = f if color else cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if i >= tope:
            break
    return out


def _grupos_de_palo(centros: Sequence[int], n: int, total: int) -> dict[int, tuple[int, ...]]:
    """`n` cuadros alrededor de cada centro: `centro−n//2 … centro+n−n//2−1`."""
    out = {}
    for c in centros:
        lo = c - n // 2
        out[c] = tuple(i for i in range(lo, lo + n) if 0 <= i < total)
    return out


def correr(
    video: Path,
    pose_path: Path,
    *,
    cada: int = 10,
    ref: int | None = None,
    muestras_fondo: int = MUESTRAS_FONDO,
    palo: Sequence[int] = (),
    palo_n: int = 10,
    ventana_local: int = VENTANA_LOCAL,
    paso_local: int = PASO_LOCAL,
    escala: Sequence[int] = (),
    scale_px: float | None = None,
    params: Params | None = None,
    salida: Path | None = None,
    etiquetas: dict | None = None,
    recortes: bool = False,
    recorte_radio: float = 0.85,
    recorte_zoom: float = 1.0,
    solo_recortes: bool = False,
    progreso=None,
) -> dict:
    p = params or Params()
    t_total = time.time()
    pose_dir = Path(pose_path).parent if Path(pose_path).name == POSE_FILE else Path(pose_path)
    pose = load_pose(pose_dir)
    total = int(pose.keypoints.shape[0])
    try:
        d = probe_declared(video)
    except FfprobeError as e:
        raise MascaraError(str(e)) from e
    dp = DriftParams()
    alto_px = alto_cuerpo_px(pose)
    if ref is None:
        ref, ref_metodo = primer_cuadro_con_pose(pose)
    else:
        ref_metodo = "pedido con --ref"
    if not 0 <= ref < total:
        raise MascaraError(f"--ref {ref} queda fuera de los {total} cuadros de la pose")

    display = d.display_size
    base = _decodificar(video, d.rotation_deg, display, {ref}, p.color)
    if ref not in base:
        raise MascaraError(f"{video}: el cuadro de referencia {ref} no se pudo decodificar")
    img_ref = base[ref]
    forma = img_ref.shape[:2]
    gris_ref = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY) if img_ref.ndim == 3 else img_ref
    mask_ref = mascara_fondo_sift(gris_ref.shape, pose, ref, alto_px, dp)
    sift = cv2.SIFT_create(nfeatures=dp.nfeatures)
    ref_pre = sift.detectAndCompute(gris_ref, mask_ref)

    grupos = _grupos_de_palo(palo, palo_n, total)
    dir_salida = salida or (Path(str(video) + ".kinelab") / "mascara")
    dir_salida.mkdir(parents=True, exist_ok=True)
    if solo_recortes:
        # Etiquetar primero y medir después: escribir los recortes no necesita
        # ningún modelo de fondo, y los modelos son lo que tarda dos minutos.
        cuadros = sorted({f for g in grupos.values() for f in g} | set(escala))
        imgs = _decodificar(video, d.rotation_deg, display, set(cuadros), p.color)
        escritos = [str(recorte_con_grilla(dir_salida / f"recorte-{i}.png", imgs[i], pose, i, alto_px,
                                           radio=recorte_radio, zoom=recorte_zoom))
                    for i in cuadros if i in imgs]
        return {"herramienta": "banco/mascara_sujeto.py", "solo_recortes": True, "video": str(video),
                "alto_cuerpo_px": alto_px, "archivos": escritos, "segundos": time.time() - t_total,
                "cobertura": {}, "fondos": [], "palo": [], "escala": [], "palo_contra_etiquetas": {},
                "frames": total, "ancho_alto": [int(forma[1]), int(forma[0])], "ref": ref,
                "ref_metodo": ref_metodo, "cada": cada}
    ventanas = {c: tuple(range(max(0, min(g) - ventana_local), min(total, max(g) + ventana_local + 1), paso_local))
                for c, g in grupos.items() if g}

    # --- pase 1: los cuadros que arman los modelos de fondo. Un modelo por
    # pasada de decodificación, a propósito: tener las muestras de todos los
    # modelos en memoria a la vez son 3,1 GB en UHD, y la pila de la mediana va
    # encima. Decodificar dos veces cuesta 20 s; quedarse sin memoria, todo.
    fallas1: dict[int, str] = {}

    def modelo_de_fondo(frames: Sequence[int], *, etiqueta: str, enmascarar: bool) -> Fondo:
        if progreso:
            progreso(f"fondo {etiqueta}: {len(frames)} cuadros")
        imgs = _decodificar(video, d.rotation_deg, display, set(frames), p.color)
        hs, malas = _homografias(imgs, gris_ref, mask_ref, pose, alto_px, dp, sift, ref_pre)
        fallas1.update(malas)
        f = construir_fondo(imgs, hs, pose, alto_px, p, etiqueta=etiqueta, enmascarar=enmascarar, forma=forma)
        del imgs, hs
        return f

    m_globales = sorted(set(np.linspace(0, total - 1, min(muestras_fondo, total)).round().astype(int).tolist()) | {ref})
    global_ = modelo_de_fondo(m_globales, etiqueta="global", enmascarar=True)
    locales: dict[int, Fondo] = {
        c: modelo_de_fondo(v, etiqueta=f"local±{ventana_local}@{c}", enmascarar=False)
        for c, v in ventanas.items()
    }

    # --- pase 2: los cuadros que se evalúan
    evaluados = sorted(set(range(0, total, cada)) | {f for g in grupos.values() for f in g} | set(escala))
    if progreso:
        progreso(f"máscara en {len(evaluados)} cuadros")
    inds: list[Indicadores] = []
    rectas: list[Recta] = []
    extensiones: list[Extension] = []
    escritos: list[str] = []
    fallas2: dict[int, str] = {}
    de_palo = {f: c for c, g in grupos.items() for f in g}
    pendientes, tope = set(evaluados), max(evaluados)
    hecho = 0
    for i, frame in iter_frames(video, rotation_deg=d.rotation_deg, display_size=display):
        if i not in pendientes:
            if i > tope:
                break
            continue
        img = frame if p.color else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        msk = mascara_fondo_sift(g.shape, pose, i, alto_px, dp)
        modelo, razon = estimar(gris_ref, mask_ref, g, msk, dp, sift=sift, ref_precomputado=ref_pre)
        if modelo is None:
            fallas2[i] = razon or "sin homografía"
            inds.append(Indicadores(i, None, None, None, None, None, None, 0.0, 0.0, razon))
            continue
        mg = primer_plano(img, modelo.matriz, global_, alto_px, p, pose=pose, frame=i)
        inds.append(indicadores(mg, pose, i))
        if i in escala:
            e = extension_vertical(mg, pose, i, scale_px)
            extensiones.append(e)
            escritos.append(str(dibujar_extension(dir_salida / f"escala-{i}.png", img, mg, e, pose, i, scale_px)))
        if i in de_palo:
            c = de_palo[i]
            ml = primer_plano(img, modelo.matriz, locales[c], alto_px, p, pose=pose, frame=i)
            for nombre, m in (("global", mg), ("local", ml)):
                r = buscar_palo(m.fina, pose, i, alto_px, p, modelo=nombre)
                rectas.append(r)
                eti = (etiquetas or {}).get(str(i))
                destino = dir_salida / f"palo-{nombre}-{i}.png"
                titulo = f"{video.name} · cuadro {i} · fondo {nombre}"
                escritos.append(str(dibujar_palo(destino, img, m, r, eti, alto_px, titulo)))
            if recortes:
                escritos.append(str(recorte_con_grilla(dir_salida / f"recorte-{i}.png", img, pose, i, alto_px,
                                                       radio=recorte_radio, zoom=recorte_zoom)))
        hecho += 1
        if progreso and hecho % 50 == 0:
            progreso(f"  {hecho}/{len(evaluados)}")
        if i >= tope:
            break

    cv2.imwrite(str(dir_salida / "fondo-global.png"), global_.mediana)
    escritos.append(str(dir_salida / "fondo-global.png"))
    cv2.imwrite(str(dir_salida / "sin-fondo.png"), (global_.sin_fondo * 255).astype(np.uint8))
    escritos.append(str(dir_salida / "sin-fondo.png"))

    salida_json = {
        "herramienta": "banco/mascara_sujeto.py",
        "encargo": 32,
        "video": str(video),
        "pose": str(pose_dir / POSE_FILE),
        "frames": total,
        "alto_cuerpo_px": alto_px,
        "ref": ref,
        "ref_metodo": ref_metodo,
        "ancho_alto": [int(forma[1]), int(forma[0])],
        "color": p.color,
        "cada": cada,
        "scale_px_del_analisis": scale_px,
        "params": p.to_dict(),
        "params_homografia": DriftParams().to_dict(),
        "fondos": [global_.resumen()] + [f.resumen() for f in locales.values()],
        "homografias_fallidas": {"fondo": fallas1, "evaluacion": fallas2},
        "cobertura": _resumen_cobertura(inds),
        "indicadores": [asdict(x) for x in inds],
        "palo": [r.to_dict() for r in rectas],
        "palo_contra_etiquetas": _errores_palo(rectas, etiquetas or {}),
        "escala": [asdict(x) for x in extensiones],
        "archivos": escritos,
        "segundos": time.time() - t_total,
    }
    (dir_salida / "mascara.json").write_text(
        json.dumps(finite_or_none(salida_json), ensure_ascii=False, indent=2), encoding="utf-8")
    return salida_json


def _resumen_cobertura(inds: Sequence[Indicadores]) -> dict:
    ok = [x for x in inds if x.cobertura_bbox is not None]
    if not ok:
        return {"cuadros": len(inds), "con_mascara": 0}
    cob = np.array([x.cobertura_bbox for x in ok], dtype=float)
    kp = np.array([(x.keypoints_en_mascara or 0) / max(1, x.keypoints_visibles or 1) for x in ok], dtype=float)
    ms = np.array([x.ms for x in inds if x.ms > 0], dtype=float)
    ag = np.array([x.agujeros for x in ok if x.agujeros is not None], dtype=float)
    agf = np.array([x.agujeros_area_frac for x in ok if x.agujeros_area_frac is not None], dtype=float)
    return {
        "cuadros_evaluados": len(inds),
        "cuadros_con_mascara": len(ok),
        "cobertura_bbox_mediana": float(np.median(cob)),
        "cobertura_bbox_minima": float(cob.min()),
        "cobertura_bbox_maxima": float(cob.max()),
        "keypoints_en_mascara_mediana": float(np.median(kp)),
        "keypoints_en_mascara_minima": float(kp.min()),
        "agujeros_mediana": float(np.median(ag)) if ag.size else None,
        "agujeros_maximo": float(ag.max()) if ag.size else None,
        "agujeros_area_frac_mediana": float(np.median(agf)) if agf.size else None,
        "ms_por_cuadro_mediana": float(np.median(ms)) if ms.size else None,
        "ms_por_cuadro_maxima": float(ms.max()) if ms.size else None,
    }


def _errores_palo(rectas: Sequence[Recta], etiquetas: dict) -> dict:
    """La recta ajustada contra la etiqueta a ojo. La etiqueta es `estimacion`."""
    filas = []
    for r in rectas:
        eti = etiquetas.get(str(r.frame))
        if eti is None:
            continue
        fila: dict = {"frame": r.frame, "modelo": r.modelo,
                      "etiqueta_visible": bool(eti.get("visible", True)),
                      "etiqueta_parcial": bool(eti.get("parcial", False))}
        if not eti.get("visible", True) or not eti.get("mango") or not eti.get("punta"):
            fila["null_reason"] = eti.get("nota") or "la etiqueta a ojo dice que el shaft no se ve"
            filas.append(fila)
            continue
        mango = np.array(eti["mango"], dtype=float)
        punta = np.array(eti["punta"], dtype=float)
        fila["etiqueta_angulo_deg"] = _angulo(punta - mango)
        fila["etiqueta_largo_px"] = float(np.linalg.norm(punta - mango))
        if r.angulo_deg is None:
            fila["null_reason"] = r.null_reason
            filas.append(fila)
            continue
        fila["angulo_deg"] = r.angulo_deg
        fila["largo_px"] = r.largo_px
        fila["largo_desde_mano_px"] = r.largo_desde_mano_px
        fila["error_angulo_deg"] = dif_angular(r.angulo_deg, fila["etiqueta_angulo_deg"])
        fila["error_punta_px"] = float(np.linalg.norm(np.array(r.punta_px) - punta))
        fila["error_mango_px"] = float(np.linalg.norm(np.array(r.mango_px) - mango))
        fila["error_largo_px"] = float(r.largo_px - fila["etiqueta_largo_px"])
        # La distancia PERPENDICULAR de la punta etiquetada a la recta separa
        # «la recta apunta a otro lado» de «la recta está bien y llega menos
        # lejos», que es lo que pasa cuando la máscara pierde la cabeza del palo.
        u = np.array(r.punta_px, dtype=float) - np.array(r.mango_px, dtype=float)
        n = float(np.linalg.norm(u))
        if n > 0:
            u = u / n
            d = punta - np.array(r.mango_px, dtype=float)
            # Producto cruz en 2-D a mano: `np.cross` de vectores 2-D salió en numpy 2.
            fila["error_perp_punta_px"] = float(abs(u[0] * d[1] - u[1] * d[0]))
        filas.append(fila)
    res: dict = {"filas": filas}
    for modelo in ("global", "local"):
        v = [f for f in filas if f["modelo"] == modelo and "error_angulo_deg" in f]
        # El largo y la punta sólo se comparan contra una etiqueta ENTERA. Con
        # una etiqueta parcial —sólo se ve un tramo del shaft— el ángulo sigue
        # valiendo y el largo no: el que mide de menos es el ojo, no la recta.
        enteras = [f for f in v if not f["etiqueta_parcial"]]
        clave = f"resumen_{modelo}"
        if not v:
            res[clave] = {"n": 0,
                          "etiquetas_con_shaft_visible": sum(1 for f in filas if f["modelo"] == modelo and f["etiqueta_visible"]),
                          "etiquetas": sum(1 for f in filas if f["modelo"] == modelo)}
            continue
        res[clave] = {
            "n": len(v),
            "etiquetas": sum(1 for f in filas if f["modelo"] == modelo),
            "etiquetas_con_shaft_visible": sum(1 for f in filas if f["modelo"] == modelo and f["etiqueta_visible"]),
            "etiquetas_enteras": len(enteras),
            "error_angulo_mediano_deg": float(np.median([f["error_angulo_deg"] for f in v])),
            "error_angulo_maximo_deg": float(max(f["error_angulo_deg"] for f in v)),
            "error_angulo_bajo_5_deg": sum(1 for f in v if f["error_angulo_deg"] < 5.0),
        }
        if enteras:
            res[clave].update({
                "error_punta_mediano_px": float(np.median([f["error_punta_px"] for f in enteras])),
                "error_punta_maximo_px": float(max(f["error_punta_px"] for f in enteras)),
                "error_mango_mediano_px": float(np.median([f["error_mango_px"] for f in enteras])),
                "error_largo_mediano_px": float(np.median([f["error_largo_px"] for f in enteras])),
                "error_perp_punta_mediano_px": float(np.median([f["error_perp_punta_px"] for f in enteras if "error_perp_punta_px" in f])),
                "error_perp_punta_maximo_px": float(max(f["error_perp_punta_px"] for f in enteras if "error_perp_punta_px" in f)),
            })
    return res


# ---------------------------------------------------------------- CLI

def format_human(s: dict) -> str:
    if s.get("solo_recortes"):
        return f"{s['video']} · {len(s['archivos'])} recortes en {Path(s['archivos'][0]).parent} · {s['segundos']:.1f} s"
    c = s["cobertura"]
    lin = [
        f"{s['video']} · {s['frames']} cuadros · {s['ancho_alto'][0]}x{s['ancho_alto'][1]} · "
        f"cuerpo {s['alto_cuerpo_px']:.0f} px · ref {s['ref']}",
    ]
    for f in s["fondos"]:
        lin.append(f"  fondo {f['etiqueta']}: {f['cuadros']} cuadros · sin fondo en "
                   f"{100 * f['sin_fondo_frac_del_cuadro']:.2f} % del cuadro ({f['sin_fondo_px']} px) · "
                   f"MAD mediano {f['mad_mediano']:.1f} · {f['segundos']:.1f} s")
    if c.get("cuadros_con_mascara"):
        lin += [
            f"  cobertura del bbox en {c['cuadros_con_mascara']}/{c['cuadros_evaluados']} cuadros "
            f"(cada {s['cada']}): mediana {c['cobertura_bbox_mediana']:.3f} · mínimo {c['cobertura_bbox_minima']:.3f} · "
            f"máximo {c['cobertura_bbox_maxima']:.3f}",
            f"  keypoints adentro de la máscara: mediana {100 * c['keypoints_en_mascara_mediana']:.0f} % · "
            f"mínimo {100 * c['keypoints_en_mascara_minima']:.0f} %",
            f"  agujeros del componente mayor: mediana {c['agujeros_mediana']} · máximo {c['agujeros_maximo']} · "
            f"área {100 * (c['agujeros_area_frac_mediana'] or 0):.1f} % del componente",
            f"  máscara por cuadro: mediana {c['ms_por_cuadro_mediana']:.0f} ms · máximo {c['ms_por_cuadro_maxima']:.0f} ms",
        ]
    for r in s["palo"]:
        if r["angulo_deg"] is None:
            lin.append(f"  palo c{r['frame']} ({r['modelo']}): sin recta — {r['null_reason']}")
        else:
            lin.append(f"  palo c{r['frame']} ({r['modelo']}): {r['angulo_deg']:.1f}° · {r['largo_px']:.0f} px · "
                       f"{r['pixeles']} px finos")
    for modelo in ("global", "local"):
        res = s["palo_contra_etiquetas"].get(f"resumen_{modelo}", {})
        if res.get("n"):
            lin.append(f"  contra etiquetas a ojo ({modelo}, n={res['n']} de {res['etiquetas']}, "
                       f"{res['etiquetas_con_shaft_visible']} con shaft visible): ángulo mediano "
                       f"{res['error_angulo_mediano_deg']:.1f}° (máx {res['error_angulo_maximo_deg']:.1f}°) · "
                       f"bajo 5° en {res['error_angulo_bajo_5_deg']}/{res['n']}")
            if res.get("etiquetas_enteras"):
                lin.append(f"    con etiqueta entera (n={res['etiquetas_enteras']}): punta "
                           f"{res['error_punta_mediano_px']:.0f} px (máx {res['error_punta_maximo_px']:.0f}) · "
                           f"perpendicular {res['error_perp_punta_mediano_px']:.0f} px · "
                           f"largo {res['error_largo_mediano_px']:+.0f} px")
        elif res.get("etiquetas"):
            lin.append(f"  contra etiquetas a ojo ({modelo}): 0 comparables de {res['etiquetas']} etiquetas, "
                       f"{res['etiquetas_con_shaft_visible']} con shaft visible a ojo")
    for e in s["escala"]:
        if e["alto_mascara_px"] is None:
            lin.append(f"  escala c{e['frame']}: null — {e['null_reason']}")
        else:
            coc = f" · contra la cadena {e['cociente_contra_cadena']:.4f}" if e["cociente_contra_cadena"] else ""
            sob = ""
            if e.get("sobra_arriba_px") is not None:
                sob = (f" · sobra {e['sobra_arriba_px']:+.0f} px arriba del punto head y "
                       f"{e['sobra_abajo_px']:+.0f} px abajo del tobillo")
            lin.append(f"  escala c{e['frame']}: máscara {e['alto_mascara_px']:.0f} px "
                       f"(y {e['y_arriba']:.0f} → {e['y_abajo']:.0f}){coc}{sob}")
    lin.append(f"  {s['segundos']:.1f} s · salida en {Path(s['archivos'][0]).parent if s['archivos'] else '—'}")
    return "\n".join(lin)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python banco/mascara_sujeto.py",
        description="Qué compra y qué cuesta una máscara del sujeto: silueta, palo y escala, medidos. Experimento, no producto.",
    )
    ap.add_argument("video", type=Path)
    ap.add_argument("--pose", type=Path, required=True, help="pose.npz (o la carpeta que lo contiene)")
    ap.add_argument("--cada", type=int, default=10, help="evaluar la máscara un cuadro cada N (por defecto 10)")
    ap.add_argument("--ref", type=int, default=None, help="cuadro de referencia (por defecto el primero con pose)")
    ap.add_argument("--muestras-fondo", type=int, default=MUESTRAS_FONDO, help=f"cuadros de la mediana global (por defecto {MUESTRAS_FONDO})")
    ap.add_argument("--palo", type=int, action="append", default=[], metavar="FRAME", help="centro de un grupo de cuadros donde buscar el shaft (repetible)")
    ap.add_argument("--palo-n", type=int, default=10, help="cuántos cuadros por grupo (por defecto 10)")
    ap.add_argument("--ventana-local", type=int, default=VENTANA_LOCAL, help=f"±cuadros del fondo local (por defecto {VENTANA_LOCAL})")
    ap.add_argument("--paso-local", type=int, default=PASO_LOCAL, help=f"cada cuántos cuadros se muestrea esa ventana (por defecto {PASO_LOCAL})")
    ap.add_argument("--escala", type=int, action="append", default=[], metavar="FRAME", help="cuadro donde medir la extensión vertical (repetible)")
    ap.add_argument("--scale-px", type=float, default=None, help="la escala del análisis contra la que comparar (px)")
    ap.add_argument("--umbral", type=float, default=UMBRAL, help=f"piso del umbral de diferencia (por defecto {UMBRAL})")
    ap.add_argument("--k-mad", type=float, default=K_MAD, help=f"múltiplos de MAD por encima del piso (por defecto {K_MAD})")
    ap.add_argument("--gris", action="store_true", help="modelo de fondo en gris en vez de color (menos memoria)")
    ap.add_argument("--ocupacion", choices=("silueta", "bbox", "bbox-y-palo"), default="silueta",
                    help="cómo se marca dónde está el sujeto al armar el fondo (por defecto silueta; las otras dos son controles)")
    ap.add_argument("--recortes", action="store_true", help="escribir los recortes con grilla para etiquetar a ojo")
    ap.add_argument("--recorte-radio", type=float, default=0.85, help="radio del recorte, en altos de cuerpo (por defecto 0.85)")
    ap.add_argument("--recorte-zoom", type=float, default=1.0, help="ampliación del recorte (por defecto 1.0)")
    ap.add_argument("--solo-recortes", action="store_true", help="escribir sólo los recortes para etiquetar, sin construir ningún fondo")
    ap.add_argument("--etiquetas", type=Path, default=None, help="JSON con las etiquetas a ojo del shaft")
    ap.add_argument("--salida", type=Path, default=None, help="carpeta de salida (por defecto <video>.kinelab/mascara/)")
    args = ap.parse_args(argv)

    if not args.video.exists():
        print(f"no existe: {args.video}", file=sys.stderr)
        return 2
    etiquetas = None
    if args.etiquetas is not None:
        if not args.etiquetas.is_file():
            print(f"no existe: {args.etiquetas}", file=sys.stderr)
            return 2
        etiquetas = json.loads(args.etiquetas.read_text(encoding="utf-8")).get("etiquetas", {})

    def progreso(t: str) -> None:
        print(f"  {t}", flush=True)

    try:
        s = correr(
            args.video, args.pose, cada=args.cada, ref=args.ref, muestras_fondo=args.muestras_fondo,
            palo=args.palo, palo_n=args.palo_n, ventana_local=args.ventana_local, paso_local=args.paso_local,
            escala=args.escala, scale_px=args.scale_px,
            params=Params(umbral=args.umbral, k_mad=args.k_mad, color=not args.gris, ocupacion=args.ocupacion),
            salida=args.salida, etiquetas=etiquetas, recortes=args.recortes,
            recorte_radio=args.recorte_radio, recorte_zoom=args.recorte_zoom,
            solo_recortes=args.solo_recortes, progreso=progreso,
        )
    except (MascaraError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(format_human(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
