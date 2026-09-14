"""Key MP4 green screens into transparent animated WebP files.

Original files remain intact. Each clip uses one fixed crop across all frames,
so changing silhouettes do not cause frame-to-frame zoom or position jitter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pet.catalog import ROOT, ASSETS, ACTION_NAMES, ACTION_USES

PIPELINE_VERSION = 3


def key_green(rgb: np.ndarray) -> np.ndarray:
    """Soft green-dominance matte with edge despill; keep neutral coat opaque."""
    values = rgb.astype(np.float32)
    red, green, blue = values[..., 0], values[..., 1], values[..., 2]
    neutral = np.maximum(red, blue)
    excess = green - neutral
    # Green eyes and warm fur have little green dominance. Background pixels
    # and the antialiased green mixture at the silhouette have much more.
    key = np.clip((excess - 12.0) / 68.0, 0.0, 1.0)
    key = key * key * (3.0 - 2.0 * key)
    # Clip 07 dims its screen midway through. Saturation recognizes even the
    # dark green background, while low-saturation coat colors stay protected.
    relative_green = excess / np.maximum(green, 1.0)
    saturated_key = np.clip((relative_green - .28) / .42, 0.0, 1.0)
    saturated_key *= np.clip((excess - 8.0) / 20.0, 0.0, 1.0)
    key = np.maximum(key, saturated_key)
    corners = np.concatenate([values[:8, :8].reshape(-1, 3), values[:8, -8:].reshape(-1, 3), values[-8:, :8].reshape(-1, 3), values[-8:, -8:].reshape(-1, 3)])
    background = np.median(corners, axis=0)
    if background[1] < 30 and background[1] > max(background[0], background[2]) + 1:
        # The supplied 07 video briefly fades to almost-black green. Recover
        # the screen by chroma ratio, then remove border-connected black
        # compression specks without removing isolated dark stripes on fur.
        dim_key = np.clip((relative_green - .28) / .42, 0, 1) * np.clip(excess / 3, 0, 1)
        key = np.maximum(key, dim_key)
        candidate = ((key > .98) | (values.max(axis=2) < 12)).astype(np.uint8)
        _, components = cv2.connectedComponents(candidate, connectivity=8)
        border_labels = np.unique(np.concatenate([components[0], components[-1], components[:, 0], components[:, -1]]))
        border_labels = border_labels[border_labels != 0]
        key[np.isin(components, border_labels)] = 1
    alpha = np.rint((1.0 - key) * 255).astype(np.uint8)
    spill = np.clip((excess - 3.0) / 24.0, 0.0, 1.0)
    values[..., 1] = green - np.maximum(excess, 0) * spill
    rgba = np.dstack((np.clip(values, 0, 255).astype(np.uint8), alpha))
    rgba[alpha == 0, :3] = 0
    return rgba


def prepare_clip(path: Path, size: int, fps: int) -> dict:
    number = int(re.match(r"\d+", path.name)[0])
    variant = "once" if "非循环" in path.stem else ("loop2" if path.stem.endswith("2") else "loop")
    clip_id = f"{number:02d}_{variant}"
    destination = ASSETS / "animations" / f"{clip_id}.webp"
    meta_file = destination.with_suffix(".json")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    signature = dict(sha256=digest, size=size, fps=fps, pipeline=PIPELINE_VERSION)
    if meta_file.exists() and destination.exists():
        cached = json.loads(meta_file.read_text(encoding="utf-8"))
        if cached.get("signature") == signature:
            return cached
    cap = cv2.VideoCapture(str(path))
    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or source_fps <= 0:
        raise RuntimeError(f"无法读取视频: {path}")
    actual_fps = min(fps, source_fps)
    frame_index = 0
    next_sample = 0.0
    frames = []
    bbox = None
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            if frame_index + 1e-4 >= next_sample:
                h, w = bgr.shape[:2]
                scaled = cv2.resize(bgr, (round(w * size / max(w, h)), round(h * size / max(w, h))), interpolation=cv2.INTER_AREA)
                rgba = key_green(cv2.cvtColor(scaled, cv2.COLOR_BGR2RGB))
                frame = Image.fromarray(rgba)
                visible = Image.fromarray((rgba[..., 3] > 12).astype(np.uint8) * 255).getbbox()
                if visible:
                    bbox = visible if bbox is None else (min(bbox[0], visible[0]), min(bbox[1], visible[1]), max(bbox[2], visible[2]), max(bbox[3], visible[3]))
                frames.append(frame)
                next_sample += source_fps / actual_fps
            frame_index += 1
    finally:
        cap.release()
    if not frames or not bbox:
        raise RuntimeError(f"没有检测到前景: {path}")
    bbox = (max(0, bbox[0] - 5), max(0, bbox[1] - 5), min(frames[0].width, bbox[2] + 5), min(frames[0].height, bbox[3] + 5))
    frames = [frame.crop(bbox) for frame in frames]
    duration_ms = round(frame_index / source_fps * 1000)
    durations = [round((i + 1) * duration_ms / len(frames)) - round(i * duration_ms / len(frames)) for i in range(len(frames))]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp.webp")
    frames[0].save(temporary, format="WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=1 if variant == "once" else 0, quality=88, method=3, minimize_size=False, allow_mixed=True)
    temporary.replace(destination)
    poster = ASSETS / "posters" / f"{clip_id}.png"
    poster.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(poster)
    result = dict(id=clip_id, action=number, name=ACTION_NAMES[number], use=ACTION_USES[number], source=path.name, loop=variant != "once", animation=str(destination.relative_to(ASSETS)).replace("\\", "/"), poster=str(poster.relative_to(ASSETS)).replace("\\", "/"), frames=len(frames), duration_ms=duration_ms, width=frames[0].width, height=frames[0].height, crop=list(bbox), signature=signature)
    meta_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def contact_sheet(clips: list[dict]) -> None:
    sheet = Image.new("RGB", (1200, 4 * 238), "#eee9e0")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15) if Path("C:/Windows/Fonts/msyh.ttc").exists() else ImageFont.load_default()
    for i, number in enumerate(ACTION_NAMES):
        matches = [c for c in clips if c["action"] == number]
        if not matches:
            continue
        clip = next((c for c in matches if c["id"].endswith("_loop")), matches[0])
        x, y = i % 5 * 240, i // 5 * 238
        draw.rounded_rectangle((x + 6, y + 6, x + 234, y + 232), radius=12, fill="#fffdf9")
        for cy in range(y + 12, y + 204, 12):
            for cx in range(x + 12, x + 228, 12):
                if ((cx - x) // 12 + (cy - y) // 12) % 2 == 0:
                    draw.rectangle((cx, cy, cx + 11, cy + 11), fill="#edf0f1")
        im = Image.open(ASSETS / clip["poster"]).convert("RGBA")
        im.thumbnail((206, 183), Image.Resampling.LANCZOS)
        sheet.paste(im, (x + (240 - im.width) // 2, y + 201 - im.height), im)
        draw.text((x + 16, y + 209), f"{number:02d}  {ACTION_NAMES[number]}", font=font, fill="#283b36")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    sheet.save(ROOT / "artifacts" / "transparent_contact_sheet.jpg", quality=93)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--only", type=int, help="只处理一个动作编号；不会覆盖完整清单")
    args = parser.parse_args()
    if args.size < 64 or not 1 <= args.fps <= 60:
        parser.error("size 至少 64，fps 应在 1 到 60 之间")
    sources = sorted(ROOT.glob("*.mp4"), key=lambda p: (int(re.match(r"\d+", p.name)[0]), p.name))
    if args.only:
        sources = [p for p in sources if int(re.match(r"\d+", p.name)[0]) == args.only]
    clips = []
    for index, path in enumerate(sources, 1):
        print(f"[{index}/{len(sources)}] {path.name}", flush=True)
        clip = prepare_clip(path, args.size, args.fps)
        clips.append(clip)
        print(f"  -> {clip['id']}: {clip['frames']} frames, {clip['width']}x{clip['height']}", flush=True)
    if args.only and (ASSETS / "manifest.json").exists():
        manifest_path = ASSETS / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        by_id = {c["id"]: c for c in clips}
        manifest["clips"] = [by_id.get(c["id"], c) for c in manifest["clips"]]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        contact_sheet(manifest["clips"])
    if not args.only:
        missing = set(ACTION_NAMES) - {c["action"] for c in clips}
        if missing:
            raise RuntimeError(f"缺少动作: {missing}")
        manifest = dict(version=1, clips=clips, notes=["4循环.mp4 与 5循环.mp4 的 SHA-256 完全相同；保留两个语义编号，但显示的是同一段歪头动画。", "动作名称来自首帧图及其含义文件夹；01 图片实际为低坐姿，沿用原标签。"])
        (ASSETS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        contact_sheet(clips)
        print(f"完成：{len(clips)} 段透明动画，{len(ACTION_NAMES)} 种动作。", flush=True)


if __name__ == "__main__":
    main()
