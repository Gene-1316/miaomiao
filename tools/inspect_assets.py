"""Create a contact sheet and report without modifying source media."""
from pathlib import Path
import hashlib
import json
import re

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
OUT.mkdir(exist_ok=True)
font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
items = sorted((ROOT / "首帧图及其含义").glob("*.png"), key=lambda p: int(re.search(r"\d+", p.name)[0]))
sheet = Image.new("RGB", (5 * 260, 4 * 280), "#f7f4ef")
draw = ImageDraw.Draw(sheet)
for index, path in enumerate(items):
    im = Image.open(path).convert("RGB")
    im.thumbnail((246, 246))
    x, y = (index % 5) * 260, (index // 5) * 280
    sheet.paste(im, (x + (260 - im.width) // 2, y))
    draw.text((x + 10, y + 250), path.stem.replace("_绿幕", ""), font=font, fill="#333333")
sheet.save(OUT / "source_contact_sheet.jpg")
report = []
video_sheet = Image.new("RGB", (7 * 190, 4 * 215), "#f7f4ef")
draw = ImageDraw.Draw(video_sheet)
for index, path in enumerate(sorted(ROOT.glob("*.mp4"), key=lambda p: (int(re.search(r"\d+", p.name)[0]), p.name))):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    ok, frame = cap.read()
    if not ok:
        raise RuntimeError(f"Cannot read {path}")
    report.append(dict(file=path.name, width=frame.shape[1], height=frame.shape[0], fps=fps, frames=count, seconds=count / fps, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    im.thumbnail((185, 185))
    x, y = index % 7 * 190, index // 7 * 215
    video_sheet.paste(im, (x, y))
    draw.text((x + 5, y + 188), path.stem, font=font, fill="#333333")
    cap.release()
video_sheet.save(OUT / "video_contact_sheet.jpg")
(OUT / "source_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
