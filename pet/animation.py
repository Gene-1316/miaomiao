from __future__ import annotations

import json
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QMovie, QPixmap
from .catalog import ASSETS


class AnimationPlayer(QObject):
    frame_changed = Signal()
    clip_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        self.clips = manifest["clips"]
        self.notes = manifest.get("notes", [])
        self.movie = None
        self.frame = QPixmap()
        self.current = None
        self.play(8)

    def choose(self, number):
        choices = [c for c in self.clips if c["action"] == number]
        return next((c for c in choices if c["id"].endswith("_loop")), choices[0])

    def play(self, number, clip_id=None):
        clip = next(c for c in self.clips if c["id"] == clip_id) if clip_id else self.choose(number)
        if self.current and self.current["id"] == clip["id"] and self.movie.state() == QMovie.MovieState.Running:
            return
        if self.movie:
            self.movie.stop()
            self.movie.deleteLater()
        self.current = clip
        self.movie = QMovie(str(ASSETS / clip["animation"]), parent=self)
        # CacheNone bounds decoded memory; one decoder serves both windows.
        self.movie.setCacheMode(QMovie.CacheMode.CacheNone)
        if not self.movie.isValid():
            raise RuntimeError(f"透明动画无法解码：{clip['animation']}")
        self.movie.frameChanged.connect(self._on_frame)
        self.movie.jumpToFrame(0)
        self._on_frame()
        self.movie.start()
        self.clip_changed.emit()

    def _on_frame(self, *_):
        self.frame = self.movie.currentPixmap()
        self.frame_changed.emit()
