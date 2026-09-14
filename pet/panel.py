from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLineEdit,
    QMainWindow, QScrollArea, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)
from .catalog import ASSETS, ACTION_NAMES, ACTION_USES
from .model import QUESTS, SHOP, STATS
from .widgets import Card, GREEN, INK, MUTED, Meter, Room, StatCard, button, label

STYLE = """
QMainWindow, QWidget#root { background: #f7f8f2; }
QWidget { font-family: 'Microsoft YaHei UI'; font-size: 13px; color: #233d36; }
QFrame#sidebar { background: #eef2e8; border: none; border-right: 1px solid #e2e8dc; }
QFrame#card { background: #fffefa; border: 1px solid #e7eadf; border-radius: 15px; }
QPushButton { background: #fffefa; border: 1px solid #e0e6d9; border-radius: 10px; padding: 8px 13px; color: #355647; }
QPushButton:hover { background: #e8f0df; border-color: #abc5ad; }
QPushButton:pressed { background: #d5e5d4; }
QPushButton:disabled { color: #9ca797; background: #f0f2ea; border-color: #e8ecdf; }
QPushButton[primary="true"] { background: #387e67; border-color: #387e67; color: #ffffff; }
QPushButton[primary="true"]:hover { background: #2e6a55; }
QPushButton[primary="true"]:disabled { background: #abc2b0; border-color: #abc2b0; }
QPushButton[nav="true"] { text-align: left; background: transparent; border: none; padding: 12px 15px; color: #748578; }
QPushButton[nav="true"]:checked { background: #dae6d7; color: #2f654f; font-weight: 600; }
QLineEdit, QComboBox { background: #fffefa; border: 1px solid #dce3d5; border-radius: 8px; padding: 9px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 0; }
QScrollBar::handle:vertical { background: #d1dacb; border-radius: 3px; min-height: 35px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSlider::groove:horizontal { background: #e1e8da; height: 5px; border-radius: 2px; }
QSlider::handle:horizontal { background: #387e67; width: 16px; margin: -6px 0; border-radius: 8px; }
QToolTip { background: #fffefa; color: #355647; border: 1px solid #dce3d5; padding: 5px; }
"""


class Panel(QMainWindow):
    action_requested = Signal(str)
    buy_requested = Signal(str)
    claim_requested = Signal(str)
    check_in_requested = Signal()
    preview_requested = Signal(str)
    settings_changed = Signal()
    desktop_requested = Signal()
    quit_requested = Signal()

    def __init__(self, game, player):
        super().__init__()
        self.game, self.player = game, player
        self.setWindowTitle("喵伴 MIAO · 桌宠养成")
        self.setWindowIcon(QIcon(str(ASSETS / "posters" / "08_loop.png")))
        self.resize(1080, 780)
        self.setMinimumSize(880, 660)
        self.setStyleSheet(STYLE)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        side = Card()
        side.setObjectName("sidebar")
        side.setFixedWidth(156)
        sidebox = QVBoxLayout(side)
        sidebox.setContentsMargins(18, 29, 18, 22)
        sidebox.setSpacing(10)
        sidebox.addWidget(label("喵  伴", 27, GREEN, True))
        sidebox.addWidget(label("M I A O   C L U B", 9, MUTED))
        sidebox.addSpacing(35)
        self.pages = QStackedWidget()
        self.nav = QButtonGroup(self)
        for i, text in enumerate(["01   陪伴日常", "02   喵喵小铺", "03   今日约定", "04   动作图鉴", "05   宠物档案"]):
            b = button(text)
            b.setProperty("nav", True)
            b.setCheckable(True)
            self.nav.addButton(b, i)
            sidebox.addWidget(b)
        self.nav.idClicked.connect(self.pages.setCurrentIndex)
        self.nav.button(0).setChecked(True)
        sidebox.addStretch()
        sidebox.addWidget(label("陪伴，是慢慢长大。", 10, MUTED))
        self.sidebar_level = label("LV.01  初见的小伙伴", 10, GREEN)
        self.sidebar_level.setWordWrap(True)
        sidebox.addWidget(self.sidebar_level)
        outer.addWidget(side)
        body = QVBoxLayout()
        body.setContentsMargins(27, 24, 27, 17)
        body.setSpacing(17)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(6)
        self.greeting = label("今天，也要好好陪你。", 24, INK, True)
        titles.addWidget(self.greeting)
        self.subtitle = label("一段小小的日常，一只认真爱你的小猫。", 11, MUTED)
        titles.addWidget(self.subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.coins = label("120  喵币", 14, GREEN, True)
        header.addWidget(self.coins)
        header.addSpacing(12)
        self.sign_button = button("今日签到 +40", self.check_in_requested.emit, True)
        header.addWidget(self.sign_button)
        body.addLayout(header)
        self.pages.addWidget(self.home_page())
        self.pages.addWidget(self.shop_page())
        self.pages.addWidget(self.quest_page())
        self.pages.addWidget(self.gallery_page())
        self.pages.addWidget(self.profile_page())
        body.addWidget(self.pages, 1)
        footer = QHBoxLayout()
        footer.addWidget(label("●  桌面陪伴中", 10, GREEN))
        footer.addStretch()
        self.save_status = label("进度会自动保存", 10, MUTED)
        footer.addWidget(self.save_status)
        body.addLayout(footer)
        outer.addLayout(body, 1)
        self.refresh()

    def scroll_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("page")
        host.setStyleSheet("QWidget#page { background: transparent; }")
        box = QVBoxLayout(host)
        box.setContentsMargins(0, 0, 5, 0)
        box.setSpacing(16)
        scroll.setWidget(host)
        return scroll, box

    def home_page(self):
        scroll, layout = self.scroll_page()
        top = QHBoxLayout()
        top.setSpacing(18)
        left = QVBoxLayout()
        scene_card = Card()
        scene_layout = QVBoxLayout(scene_card)
        scene_layout.setContentsMargins(0, 0, 0, 0)
        self.room = Room(self.player)
        self.room.clicked.connect(lambda: self.action_requested.emit("pet"))
        scene_layout.addWidget(self.room, 1)
        scene_info = QHBoxLayout()
        scene_info.setContentsMargins(18, 12, 18, 15)
        self.name_label = label("miaomiao", 19, INK, True)
        scene_info.addWidget(self.name_label)
        scene_info.addStretch()
        self.activity = label("正坐正视", 11, GREEN)
        scene_info.addWidget(self.activity)
        scene_layout.addLayout(scene_info)
        left.addWidget(scene_card)
        left.addWidget(button("回到桌面，陪我一会儿  ↗", self.desktop_requested.emit))
        top.addLayout(left, 1)
        right = QVBoxLayout()
        heading = QHBoxLayout()
        heading.addWidget(label("此刻的小状态", 16, INK, True))
        heading.addStretch()
        heading.addWidget(label("0 — 100", 10, MUTED))
        right.addLayout(heading)
        stats = QGridLayout()
        stats.setSpacing(10)
        self.stat_cards = {}
        colors = ["#c2a075", "#82a9b0", "#abac77", "#ce9d89", "#9daf97", "#6f9e87"]
        for i, ((key, title), color) in enumerate(zip(STATS.items(), colors)):
            widget = StatCard(title, color)
            self.stat_cards[key] = widget
            stats.addWidget(widget, i // 2, i % 2)
        right.addLayout(stats)
        right.addSpacing(5)
        right.addWidget(label("把日常，照顾成喜欢", 15, INK, True))
        grid = QGridLayout()
        grid.setSpacing(8)
        self.action_buttons = {}
        for i, (key, text) in enumerate([("feed", "喂食\n一份猫粮"), ("water", "喝水\n补充水分"), ("play", "玩耍\n追追球"), ("clean", "梳毛\n整理毛发"), ("toilet", "猫砂盆\n清理一下"), ("sleep", "睡觉\n恢复精力")]):
            b = button(text, lambda checked=False, k=key: self.action_requested.emit(k))
            b.setMinimumHeight(60)
            b.setToolTip({"feed": "饱食 +28，消耗 1 份猫粮", "water": "水分 +32，免费", "play": "心情 +12，精力 -8；20 秒点击小游戏", "clean": "清洁 +24，免费", "toilet": "清洁 +18，饱食 -3", "sleep": "睡觉时每分钟恢复 2.4 精力"}[key])
            self.action_buttons[key] = b
            grid.addWidget(b, i // 3, i % 3)
        right.addLayout(grid)
        top.addLayout(right, 1)
        layout.addLayout(top)
        growth = Card()
        growbox = QVBoxLayout(growth)
        growbox.setContentsMargins(18, 15, 18, 15)
        row = QHBoxLayout()
        self.growth_title = label("LV.01  初见的小伙伴", 14, INK, True)
        row.addWidget(self.growth_title)
        row.addStretch()
        self.growth_detail = label("0 / 100 成长", 11, MUTED)
        row.addWidget(self.growth_detail)
        growbox.addLayout(row)
        self.xp_meter = Meter(GREEN)
        growbox.addWidget(self.xp_meter)
        self.bond_label = label("亲密度 12  ·  从一次摸摸头开始，慢慢成为彼此的习惯。", 11, MUTED)
        growbox.addWidget(self.bond_label)
        layout.addWidget(growth)
        note = Card()
        note_row = QHBoxLayout(note)
        note_row.setContentsMargins(17, 14, 17, 14)
        note_row.addWidget(label("小猫来信", 12, GREEN, True))
        self.message = label("你好呀，以后的每个小日子，都一起过吧。", 12, MUTED)
        self.message.setWordWrap(True)
        note_row.addWidget(self.message, 1)
        layout.addWidget(note)
        layout.addStretch()
        return scroll

    def shop_page(self):
        scroll, layout = self.scroll_page()
        layout.addWidget(label("喵喵小铺", 22, INK, True))
        layout.addWidget(label("攒一点喵币，给小日子添一点好吃的。所有商品均使用游戏内喵币。", 12, MUTED))
        self.inventory_labels = {}
        self.buy_buttons = {}
        for key, item in SHOP.items():
            card = Card()
            row = QHBoxLayout(card)
            row.setContentsMargins(24, 23, 24, 23)
            mark = label(item["mark"], 28, GREEN, True)
            mark.setFixedWidth(56)
            row.addWidget(mark)
            details = QVBoxLayout()
            details.addWidget(label(item["name"], 17, INK, True))
            details.addWidget(label(item["description"], 12, MUTED))
            inventory = label("已有 0 份", 11, GREEN)
            self.inventory_labels[key] = inventory
            details.addWidget(inventory)
            row.addLayout(details, 1)
            use = {"kibble": "feed", "fish": "fish", "medicine": "medicine"}[key]
            row.addWidget(button("使用", lambda checked=False, k=use: self.action_requested.emit(k)))
            buy = button(f"{item['price']} 喵币 · 购买", lambda checked=False, k=key: self.buy_requested.emit(k), True)
            self.buy_buttons[key] = buy
            row.addWidget(buy)
            layout.addWidget(card)
        layout.addWidget(button("桌面小探索  ·  精力 -10 / 喵币 +12", lambda: self.action_requested.emit("explore")))
        layout.addWidget(label("免费喝水、梳毛和休息随时可用。每日签到和约定也会送来喵币。", 11, MUTED))
        layout.addStretch()
        return scroll

    def quest_page(self):
        scroll, layout = self.scroll_page()
        layout.addWidget(label("今天的小约定", 22, INK, True))
        layout.addWidget(label("不必赶时间，照顾好眼前的小猫就好。每天重新开始。", 12, MUTED))
        self.quest_widgets = {}
        for key, (name, goal, reward) in QUESTS.items():
            card = Card()
            row = QHBoxLayout(card)
            row.setContentsMargins(22, 20, 22, 20)
            text = QVBoxLayout()
            text.addWidget(label(name, 16, INK, True))
            progress = label(f"0 / {goal}   ·   {reward} 喵币 + 10 成长", 12, MUTED)
            text.addWidget(progress)
            row.addLayout(text, 1)
            claim = button("领取奖励", lambda checked=False, k=key: self.claim_requested.emit(k), True)
            row.addWidget(claim)
            self.quest_widgets[key] = (progress, claim)
            layout.addWidget(card)
        layout.addStretch()
        return scroll

    def gallery_page(self):
        scroll, layout = self.scroll_page()
        layout.addWidget(label("小猫的 19 种表情", 22, INK, True))
        layout.addWidget(label("每个小动作，都有它想说的话。点击卡片播放一次，不改变养成数值。", 12, MUTED))
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (number, name) in enumerate(ACTION_NAMES.items()):
            clip = self.player.choose(number)
            card = Card()
            box = QVBoxLayout(card)
            b = button(f"{number:02d}  {name}", lambda checked=False, c=clip["id"]: self.preview_requested.emit(c))
            b.setIcon(QIcon(str(ASSETS / clip["poster"])))
            from PySide6.QtCore import QSize
            b.setIconSize(QSize(96, 90))
            b.setMinimumHeight(115)
            box.addWidget(b)
            caption = label(ACTION_USES[number], 10, MUTED)
            caption.setWordWrap(True)
            box.addWidget(caption)
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)
        row = QHBoxLayout()
        self.variant_select = QComboBox()
        for clip in self.player.clips:
            self.variant_select.addItem(f"{clip['source']} · {clip['name']}", clip["id"])
        row.addWidget(self.variant_select, 1)
        row.addWidget(button("播放所选片段", lambda: self.preview_requested.emit(self.variant_select.currentData())))
        layout.addLayout(row)
        for note in self.player.notes:
            text = label(note, 11, MUTED)
            text.setWordWrap(True)
            layout.addWidget(text)
        return scroll

    def profile_page(self):
        scroll, layout = self.scroll_page()
        layout.addWidget(label("关于我的小猫", 22, INK, True))
        card = Card()
        box = QVBoxLayout(card)
        box.setContentsMargins(24, 23, 24, 23)
        box.setSpacing(18)
        row = QHBoxLayout()
        row.addWidget(label("给我一个名字", 14, INK, True))
        self.name_edit = QLineEdit(self.game.state.name)
        self.name_edit.setMaxLength(12)
        row.addWidget(self.name_edit, 1)
        row.addWidget(button("保存名字", self.save_name))
        box.addLayout(row)
        self.age_label = label("相伴第 1 天", 12, MUTED)
        box.addWidget(self.age_label)
        self.roam_check = QCheckBox("让小猫在桌面自由散步")
        self.roam_check.setChecked(self.game.state.roaming)
        self.roam_check.toggled.connect(self.set_roaming)
        box.addWidget(self.roam_check)
        box.addWidget(label("桌面猫咪大小", 13, INK, True))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(180, 420)
        self.scale_slider.setValue(self.game.state.scale)
        self.scale_slider.valueChanged.connect(self.set_scale)
        box.addWidget(self.scale_slider)
        help_text = label("单击猫咪：抚摸  ·  拖动：换个位置  ·  双击：打开面板\n右键：快捷照顾菜单  ·  关闭面板后，小猫继续在桌面陪伴\n右下角托盘可以找回猫咪、打开面板或保存退出。", 12, MUTED)
        help_text.setWordWrap(True)
        box.addWidget(help_text)
        layout.addWidget(card)
        layout.addWidget(label("我们的相处日记", 17, INK, True))
        self.journal = label("故事从今天开始。", 12, MUTED)
        self.journal.setWordWrap(True)
        layout.addWidget(self.journal)
        layout.addStretch()
        layout.addWidget(button("保存并退出喵伴", self.quit_requested.emit))
        return scroll

    def save_name(self):
        self.game.state.name = self.name_edit.text().strip() or "miaomiao"
        self.name_edit.setText(self.game.state.name)
        self.settings_changed.emit()

    def set_roaming(self, enabled):
        self.game.state.roaming = enabled
        self.settings_changed.emit()

    def set_scale(self, value):
        self.game.state.scale = value
        self.settings_changed.emit()

    def notify(self, message):
        self.message.setText(message)
        self.statusBar().showMessage(message, 6000)
        self.refresh()

    def refresh(self):
        s = self.game.state
        for key, card in self.stat_cards.items():
            card.set_value(getattr(s, key))
        self.name_label.setText(s.name)
        self.room.pet_name = s.name
        self.coins.setText(f"{s.coins}  喵币")
        self.sign_button.setText("今日已签到" if s.checked_in else "今日签到 +40")
        self.sign_button.setEnabled(not s.checked_in)
        self.activity.setText("正在睡觉" if s.sleeping else self.player.current["name"])
        self.growth_title.setText(f"LV.{s.level:02d}  {s.stage}")
        self.sidebar_level.setText(f"LV.{s.level:02d}  {s.stage}")
        self.growth_detail.setText(f"{s.xp % 100} / 100 成长")
        self.xp_meter.value = s.xp % 100
        self.xp_meter.update()
        self.bond_label.setText(f"亲密度 {round(s.bond)}  ·  从一次摸摸头开始，慢慢成为彼此的习惯。")
        self.action_buttons["sleep"].setText("叫醒\n伸个懒腰" if s.sleeping else "睡觉\n恢复精力")
        self.action_buttons["feed"].setText(f"喂食\n剩余 {s.inventory['kibble']} 份")
        for key in SHOP:
            self.inventory_labels[key].setText(f"已有 {s.inventory[key]} 份")
            self.buy_buttons[key].setEnabled(s.coins >= SHOP[key]["price"])
        for key, (progress, claim) in self.quest_widgets.items():
            _, goal, reward = QUESTS[key]
            count = min(goal, s.counts.get(key, 0))
            progress.setText(f"{count} / {goal}   ·   {reward} 喵币 + 10 成长")
            claim.setText("已领取" if key in s.claimed else "领取奖励" if count >= goal else "进行中")
            claim.setEnabled(count >= goal and key not in s.claimed)
        age = max(1, (datetime.now() - datetime.fromtimestamp(s.created_at)).days + 1)
        self.age_label.setText(f"相伴第 {age} 天  ·  {s.stage}  ·  亲密度 {round(s.bond)}")
        self.journal.setText("\n".join(reversed(s.journal[-10:])) or "故事从今天开始。")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
