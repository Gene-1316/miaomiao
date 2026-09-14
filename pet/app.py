from __future__ import annotations

import random
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from .animation import AnimationPlayer
from .catalog import ASSETS
from .model import Game
from .panel import Panel
from .widgets import BallGame, DesktopPet


class Companion(QObject):
    def __init__(self, save_path: Path, show_panel=True):
        super().__init__()
        self.game = Game(save_path)
        self.player = AnimationPlayer(self)
        self.pet = DesktopPet(self.player, self.game.state.scale)
        self.pet.setWindowTitle("喵伴 · 桌面小猫")
        self.panel = Panel(self.game, self.player)
        self.busy_until = 0.0
        self.idle_at = time.monotonic() + 12
        self.walking = False
        self.direction = 1
        self.last_tick = time.monotonic()
        self.minigame = None
        self.exiting = False
        self.pet.petted.connect(lambda: self.action("pet"))
        self.pet.panel_requested.connect(self.show_panel)
        self.pet.menu_requested.connect(self.context_menu)
        self.pet.position_changed.connect(self.on_dragged)
        self.panel.action_requested.connect(self.action)
        self.panel.buy_requested.connect(self.buy)
        self.panel.claim_requested.connect(self.claim)
        self.panel.check_in_requested.connect(self.check_in)
        self.panel.preview_requested.connect(self.preview)
        self.panel.settings_changed.connect(self.apply_settings)
        self.panel.desktop_requested.connect(self.to_desktop)
        self.panel.quit_requested.connect(self.quit)
        self.player.clip_changed.connect(self.panel.refresh)
        self.tray = QSystemTrayIcon(QIcon(str(ASSETS / "posters" / "08_loop.png")), self)
        self.tray.setToolTip("喵伴 MIAO · 双击打开养成面板")
        self.tray_menu = self.make_menu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        self.place_pet()
        self.pet.show()
        if self.game.state.sleeping:
            self.player.play(2)
        self.pet.say(f"你好呀，我是{self.game.state.name}。")
        if show_panel:
            self.show_panel()
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start()
        self.walk_timer = QTimer(self)
        self.walk_timer.setInterval(40)
        self.walk_timer.timeout.connect(self.walk)
        self.walk_timer.start()
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(30000)
        self.save_timer.timeout.connect(self.save)
        self.save_timer.start()
        QApplication.instance().screenRemoved.connect(lambda *_: self.place_pet(reset=True))
        if self.game.notice:
            self.notify(self.game.notice)

    def make_menu(self):
        menu = QMenu()
        menu.addAction("打开养成面板", self.show_panel)
        menu.addSeparator()
        for key, title in [("feed", "喂一份猫粮"), ("water", "喝点水"), ("pet", "摸摸头"), ("play", "玩追追球"), ("clean", "梳理毛发"), ("toilet", "清理猫砂盆"), ("sleep", "睡觉 / 叫醒"), ("explore", "桌面小探索")]:
            menu.addAction(title, lambda checked=False, k=key: self.action(k))
        menu.addSeparator()
        self.roam_action = QAction("自由散步", menu)
        self.roam_action.setCheckable(True)
        self.roam_action.setChecked(self.game.state.roaming)
        self.roam_action.triggered.connect(self.panel.roam_check.setChecked)
        menu.addAction(self.roam_action)
        menu.addAction("找回猫咪", lambda: self.place_pet(reset=True))
        menu.addAction("保存并退出", self.quit)
        return menu

    def context_menu(self, point):
        self.tray_menu.popup(point)

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_panel()

    def show_panel(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.panel.resize(min(1080, screen.width() - 40), min(780, screen.height() - 60))
        self.panel.move(screen.center() - self.panel.rect().center())
        self.panel.showNormal()
        self.panel.raise_()
        self.panel.activateWindow()

    def to_desktop(self):
        self.panel.hide()
        self.pet.show()
        self.pet.say("我就在这里，忙完了记得摸摸我。")

    def place_pet(self, reset=False):
        screen = QApplication.primaryScreen().availableGeometry()
        pos = self.game.state.position
        if pos and not reset:
            self.pet.move(*pos)
        else:
            self.pet.move(screen.right() - self.pet.width() - 28, screen.bottom() - self.pet.height() - 18)
        self.clamp_pet()
        self.pet.show()

    def clamp_pet(self):
        screen = QApplication.screenAt(self.pet.geometry().center()) or QApplication.primaryScreen()
        rect = screen.availableGeometry()
        x = max(rect.left(), min(self.pet.x(), rect.right() - self.pet.width() + 1))
        y = max(rect.top(), min(self.pet.y(), rect.bottom() - self.pet.height() + 1))
        self.pet.move(x, y)

    def on_dragged(self):
        self.walking = False
        self.idle_at = time.monotonic() + 10
        self.clamp_pet()
        self.save()

    def apply_settings(self):
        s = self.game.state
        old_bottom = self.pet.geometry().bottom()
        self.pet.resize(s.scale, s.scale + 62)
        self.pet.move(self.pet.x(), old_bottom - self.pet.height() + 1)
        self.clamp_pet()
        self.roam_action.setChecked(s.roaming)
        if not s.roaming:
            self.walking = False
        self.panel.refresh()
        self.save()

    def notify(self, message):
        self.pet.say(message)
        self.panel.notify(message)

    def action(self, action):
        if self.minigame is not None:
            self.minigame.raise_()
            return
        if time.monotonic() < self.busy_until and action != "sleep":
            self.notify("等我把这个小动作做完，马上就来。")
            return
        ok, message, clip = self.game.perform(action)
        if ok:
            self.walking = action == "explore" and self.game.state.roaming
            self.direction = random.choice([-1, 1])
            self.pet.mirrored = self.walking and self.direction < 0
            self.player.play(clip)
            duration = self.player.current["duration_ms"] / 1000
            self.busy_until = time.monotonic() + duration
            self.idle_at = self.busy_until
            self.save()
            if action == "play":
                self.minigame = BallGame(self.panel)
                self.minigame.completed.connect(self.game_reward)
                self.minigame.finished.connect(self.game_closed)
                self.minigame.show()
        self.notify(message)

    def game_reward(self, reward):
        self.game.state.coins += reward
        self.game.log(f"追追球一起追到了快乐，获得 {reward} 枚喵币。")
        self.notify(f"玩得好开心！收到 {reward} 枚喵币。")
        self.save()

    def game_closed(self, *_):
        self.minigame = None
        self.busy_until = 0
        self.idle_at = time.monotonic()

    def buy(self, item):
        _, message = self.game.buy(item)
        self.notify(message)
        self.save()

    def claim(self, quest):
        _, message = self.game.claim(quest)
        self.notify(message)
        self.save()

    def check_in(self):
        ok, message = self.game.check_in()
        if ok and not self.game.state.sleeping and time.monotonic() >= self.busy_until and self.minigame is None:
            self.player.play(9)
            self.walking = False
            self.busy_until = time.monotonic() + self.player.current["duration_ms"] / 1000
            self.idle_at = self.busy_until
        self.notify(message)
        self.save()

    def preview(self, clip_id):
        if self.minigame is not None or time.monotonic() < self.busy_until:
            self.notify("等当前动作结束，就可以欣赏下一个动作啦。")
            return
        self.walking = False
        self.pet.mirrored = False
        self.player.play(8, clip_id=clip_id)
        self.busy_until = time.monotonic() + self.player.current["duration_ms"] / 1000
        self.idle_at = self.busy_until

    def tick(self):
        now = time.monotonic()
        elapsed = now - self.last_tick
        self.last_tick = now
        # A suspended desktop receives the same gentle treatment as offline time.
        self.game.advance(elapsed, offline=elapsed > 120)
        self.game.reset_day()
        if self.minigame is None and now >= self.busy_until:
            if self.game.state.sleeping:
                if self.player.current["action"] != 2:
                    self.player.play(2)
                self.walking = False
            elif now >= self.idle_at:
                self.choose_idle()
        self.panel.refresh()

    def choose_idle(self):
        s = self.game.state
        self.walking = False
        if s.energy < 20:
            clip = 12
        elif min(s.food, s.water) < 25:
            clip = 3
            self.pet.say("肚子有点空啦。" if s.food < s.water else "想喝一点水，咕嘟咕嘟。")
        elif s.roaming and random.random() < .26:
            clip = 6
            self.walking = True
            self.direction = random.choice([-1, 1])
        else:
            clip = random.choices([1, 3, 4, 5, 7, 8, 11, 13, 14], weights=[3, 1, 1, 2, 1, 5, 1, 1, 1])[0]
        self.pet.mirrored = self.walking and self.direction < 0
        self.player.play(clip)
        self.idle_at = time.monotonic() + random.uniform(8, 15)

    def walk(self):
        if not self.walking or not self.game.state.roaming or self.pet.drag_offset is not None or self.tray_menu.isVisible():
            return
        screen = QApplication.screenAt(self.pet.geometry().center()) or QApplication.primaryScreen()
        rect = screen.availableGeometry()
        x = self.pet.x() + self.direction * 2
        if x <= rect.left() or x + self.pet.width() >= rect.right():
            self.direction *= -1
            self.pet.mirrored = self.direction < 0
            x = max(rect.left(), min(x, rect.right() - self.pet.width()))
        self.pet.move(x, self.pet.y())

    def save(self):
        try:
            self.game.state.position = [self.pet.x(), self.pet.y()]
            self.game.save()
            self.panel.save_status.setText("已保存  " + time.strftime("%H:%M"))
            return True
        except OSError as error:
            self.panel.save_status.setText("存档失败，请检查目录权限")
            self.panel.message.setText(f"存档暂时无法写入：{error}")
            return False

    def quit(self):
        if self.exiting:
            return
        if self.minigame:
            self.minigame.reject()
        if not self.save():
            QMessageBox.warning(self.panel, "暂时无法保存", "存档无法写入，程序仍在运行。请检查存档目录权限后再次退出。")
            return
        self.exiting = True
        self.tick_timer.stop()
        self.walk_timer.stop()
        self.save_timer.stop()
        self.tray.hide()
        self.pet.hide()
        QApplication.instance().quit()
