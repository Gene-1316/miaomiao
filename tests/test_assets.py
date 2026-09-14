import json

import numpy as np
from PIL import Image

from pet.catalog import ACTION_NAMES, ASSETS
from tools.prepare_assets import key_green


def test_key_keeps_neutral_fur_and_removes_green():
    colors = np.array([[[0, 255, 0], [205, 210, 198], [34, 34, 34], [255, 255, 255]]], dtype=np.uint8)
    result = key_green(colors)
    assert result[0, 0, 3] == 0
    assert list(result[0, 1:, 3]) == [255, 255, 255]


def test_soft_edge_has_partial_alpha_and_no_green_spill():
    result = key_green(np.array([[[100, 147, 100]]], dtype=np.uint8))[0, 0]
    assert 0 < result[3] < 255
    assert result[1] <= max(result[0], result[2]) + 3


def test_every_animation_decodes_and_has_transparency():
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["clips"]) == 27
    assert {c["action"] for c in manifest["clips"]} == set(ACTION_NAMES)
    for clip in manifest["clips"]:
        with Image.open(ASSETS / clip["animation"]) as im:
            assert im.n_frames == clip["frames"]
            assert im.size == (clip["width"], clip["height"])
            samples = range(im.n_frames) if clip["action"] == 7 else (0, im.n_frames // 2, im.n_frames - 1)
            for frame in samples:
                im.seek(frame)
                pixels = np.asarray(im.convert("RGBA")).astype(np.int16)
                assert (pixels[..., 3] == 0).mean() > .1, clip["id"]
                assert (pixels[..., 3] == 255).mean() > .08, clip["id"]
                strong_green = (pixels[..., 1] - np.maximum(pixels[..., 0], pixels[..., 2]) > 60) & (pixels[..., 3] > 100)
                assert strong_green.mean() < .001, clip["id"]
