"""Exercise the actual Qt widgets offscreen and save reviewable renders."""
from pathlib import Path
import os
import sys
import tempfile
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from pet.app import Companion
from pet.model import Game

app = QApplication([])
from pet.fonts import configure_fonts
configure_fonts(app)
app.setQuitOnLastWindowClosed(False)
with tempfile.TemporaryDirectory(prefix="miao-smoke-") as temp:
    controller = Companion(Path(temp) / "save.json")
    controller.game.state.roaming = False
    controller.panel.resize(1080, 780)
    QTest.qWait(350)
    assert not controller.player.frame.isNull()
    first_frame = controller.player.movie.currentFrameNumber()
    QTest.qWait(200)
    assert controller.player.movie.currentFrameNumber() != first_frame
    for index, name in enumerate(["home", "shop", "quests", "gallery", "profile"]):
        QTest.mouseClick(controller.panel.nav.button(index), Qt.MouseButton.LeftButton)
        QTest.qWait(60)
        assert controller.panel.pages.currentIndex() == index
        controller.panel.grab().save(str(ROOT / "artifacts" / f"ui_{name}.png"))
    controller.panel.nav.button(0).click()
    before = controller.game.state.inventory["kibble"]
    controller.panel.action_buttons["feed"].click()
    assert controller.game.state.inventory["kibble"] == before - 1
    assert controller.player.current["action"] == 18
    assert controller.game.state.food == 100
    controller.busy_until = 0
    controller.panel.action_buttons["sleep"].click()
    assert controller.game.state.sleeping
    assert controller.player.current["action"] == 2
    controller.game.state.energy = 50
    controller.game.advance(60)
    assert controller.game.state.energy > 50
    controller.panel.action_buttons["sleep"].click()
    assert not controller.game.state.sleeping
    controller.busy_until = 0
    controller.panel.action_buttons["play"].click()
    game = controller.minigame
    assert game is not None
    QTest.mouseClick(game, Qt.MouseButton.LeftButton, pos=game.ball.toPoint())
    assert game.score == 1
    game.grab().save(str(ROOT / "artifacts" / "ui_minigame.png"))
    coins = controller.game.state.coins
    game.reject()
    assert controller.minigame is None
    assert controller.game.state.coins == coins + 1
    assert controller.game.state.counts["play"] == 1
    assert controller.save()
    loaded = Game(controller.game.path)
    assert loaded.state.coins == controller.game.state.coins
    assert loaded.state.inventory == controller.game.state.inventory
    controller.busy_until = 0
    controller.preview("15_once")
    QTest.qWait(100)
    assert controller.player.current["action"] == 15
    controller.pet.grab().save(str(ROOT / "artifacts" / "ui_desktop_pet.png"))
    controller.panel.close()
    assert not controller.panel.isVisible()
    assert controller.pet.isVisible()
    controller.show_panel()
    assert controller.panel.isVisible()
    controller.quit()
    print("PASS: animation, five pages, feed, sleep/wake, minigame hit/reward, gallery preview, save reload, panel hide/restore")
