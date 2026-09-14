"""Opt-in end-to-end check, also usable inside the standalone executable."""
from pathlib import Path
import json
import sys
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QApplication

from .catalog import ASSETS
from .model import Game
from .paths import default_save


def schedule_self_test(companion, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    frame_at_start = companion.player.movie.currentFrameNumber()

    def check():
        report = {"frozen": bool(getattr(sys, "frozen", False)), "platform": QApplication.platformName(), "default_save": str(default_save()), "resource_root": str(ASSETS.parent), "name": companion.game.state.name}
        code = 0
        try:
            assert companion.pet.isVisible() and companion.panel.isVisible()
            assert companion.player.movie.currentFrameNumber() != frame_at_start
            report["animation_playing"] = True
            companion.game.state.roaming = False
            # Native Qt decoding must work for every embedded clip, including
            # the last frame: this catches missing WebP plugins or truncation.
            checked = []
            for clip in companion.player.clips:
                movie = QMovie(str(ASSETS / clip["animation"]))
                assert movie.isValid(), clip["id"]
                assert movie.frameCount() == clip["frames"], clip["id"]
                # WebP's streaming Qt decoder does not reliably produce a
                # pixmap on a direct seek; decode in playback order instead.
                for frame_number in range(clip["frames"]):
                    assert movie.jumpToNextFrame(), (clip["id"], frame_number)
                    assert not movie.currentPixmap().isNull(), (clip["id"], frame_number)
                assert movie.currentFrameNumber() == clip["frames"] - 1
                checked.append(clip["id"])
            report["decoded_clips"] = checked
            for i, page in enumerate(["home", "shop", "quests", "gallery", "profile"]):
                companion.panel.nav.button(i).click()
                QApplication.processEvents()
                assert companion.panel.pages.currentIndex() == i
                assert companion.panel.grab().save(str(output / f"{page}.png"))
            companion.panel.nav.button(0).click()
            companion.game.state.food = 50
            companion.game.state.sleeping = False
            companion.game.state.inventory["kibble"] = 2
            companion.game.state.cooldowns = {}
            companion.busy_until = 0
            companion.panel.action_buttons["feed"].click()
            assert companion.game.state.inventory["kibble"] == 1
            assert companion.game.state.food == 78
            companion.panel.action_buttons["sleep"].click()
            assert companion.game.state.sleeping
            companion.panel.action_buttons["sleep"].click()
            assert not companion.game.state.sleeping
            companion.busy_until = 0
            companion.panel.action_buttons["play"].click()
            assert companion.minigame is not None
            coins = companion.game.state.coins
            companion.minigame.score = 2
            companion.minigame.reject()
            assert companion.game.state.coins == coins + 2
            assert companion.save()
            loaded = Game(companion.game.path)
            assert loaded.state.inventory == companion.game.state.inventory
            assert loaded.state.coins == companion.game.state.coins
            assert loaded.state.name == companion.game.state.name
            companion.panel.close()
            assert not companion.panel.isVisible() and companion.pet.isVisible()
            companion.show_panel()
            assert companion.panel.isVisible()
            report["checks"] = ["windows visible", "animated playback", "27 embedded clips decoded through Qt", "five pages", "feed inventory", "sleep and wake", "minigame reward", "save and reload", "panel hide and restore"]
            report["passed"] = True
        except Exception:
            report["passed"] = False
            report["error"] = traceback.format_exc()
            code = 1
        finally:
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            QApplication.instance().exit(code)

    QTimer.singleShot(1800, check)
