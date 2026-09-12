"""Halpe26: el orden se fija contra la definición de rtmlib, y `mirror` es un espejo."""

from __future__ import annotations

import numpy as np
import pytest

from kinelab.perception import keypoints as K


def test_order_matches_rtmlib_definition():
    rtmlib_skel = pytest.importorskip("rtmlib.visualization.skeleton.halpe26")
    info = rtmlib_skel.halpe26["keypoint_info"]
    assert len(info) == K.J == 26
    for i, name in enumerate(K.HALPE26_NAMES):
        assert info[i]["name"] == name, f"índice {i}: kinelab dice {name}, rtmlib dice {info[i]['name']}"
    # Los pares izquierda/derecha son los que rtmlib declara como `swap`.
    swaps = {(i, K.index_of(v["swap"])) for i, v in info.items() if v["swap"]}
    ours = set(K.LEFT_RIGHT_PAIRS) | {(r, l) for l, r in K.LEFT_RIGHT_PAIRS}
    assert swaps == ours


def test_h_indices_match_names():
    for attr in dir(K.H):
        if attr.isupper():
            assert K.HALPE26_NAMES[getattr(K.H, attr)] == attr.lower()


def test_limbs_and_segments_are_valid_and_unique():
    seen = set()
    for a, b in K.HALPE26_LIMBS:
        assert 0 <= a < K.J and 0 <= b < K.J and a != b
        key = (min(a, b), max(a, b))
        assert key not in seen, f"hueso repetido {key}"
        seen.add(key)
    for name, (a, b) in K.SEGMENTS.items():
        assert 0 <= a < K.J and 0 <= b < K.J and a != b, name
    assert set(K.CORE_JOINTS) == {K.H.LEFT_SHOULDER, K.H.RIGHT_SHOULDER, K.H.LEFT_HIP, K.H.RIGHT_HIP}


def _pose(width: int = 200) -> np.ndarray:
    rng = np.random.default_rng(7)
    k = rng.uniform(0, width - 1, size=(3, K.J, 2))
    k[1, K.H.LEFT_WRIST] = np.nan
    return k


def test_mirror_twice_is_identity():
    k = _pose()
    back = K.mirror(K.mirror(k, 200), 200)
    np.testing.assert_allclose(back, k, equal_nan=True)


def test_mirror_swaps_sides_and_flips_x_only():
    k = _pose()
    m = K.mirror(k, 200)
    # El codo derecho de la imagen espejada es el izquierdo original, con x reflejada.
    np.testing.assert_allclose(m[:, K.H.RIGHT_ELBOW, 0], 199 - k[:, K.H.LEFT_ELBOW, 0])
    np.testing.assert_allclose(m[:, K.H.RIGHT_ELBOW, 1], k[:, K.H.LEFT_ELBOW, 1])
    # La nariz no tiene par: sólo se refleja.
    np.testing.assert_allclose(m[:, K.H.NOSE, 0], 199 - k[:, K.H.NOSE, 0])
    np.testing.assert_allclose(m[:, K.H.NOSE, 1], k[:, K.H.NOSE, 1])
    # El NaN de la muñeca izquierda aparece en la derecha.
    assert np.isnan(m[1, K.H.RIGHT_WRIST]).all()
    assert not np.isnan(m[1, K.H.LEFT_WRIST]).any()
    assert not np.shares_memory(m, k)


def test_mirror_rejects_wrong_shape():
    with pytest.raises(ValueError):
        K.mirror(np.zeros((5, 17, 2)), 100)
