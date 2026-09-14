from __future__ import annotations

import math
import random
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

INK = "#233d36"
MUTED = "#7d8b83"
GREEN = "#387e67"


def label(text, size=12, color=INK, bold=False):
    item = QLabel(text)
    item.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{600 if bold else 400};background:transparent;")
    return item


def button(text, callback=None, primary=False):
    item = QPushButton(text)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    item.setMinimumHeight(38)
    item.setProperty("primary", primary)
    if callback:
        item.clicked.connect(callback)
    return item


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


class StatCard(Card):
    def __init__(self, name, color):
        super().__init__()
        box = QVBoxLayout(self)
        box.setContentsMargins(15, 12, 15, 12)
        box.setSpacing(8)
        row = QHBoxLayout()
        row.addWidget(label(name, 12, MUTED))
        self.value_label = label("80", 16, INK, True)
        row.addStretch()
        row.addWidget(self.value_label)
        box.addLayout(row)
        self.bar = Meter(color)
        box.addWidget(self.bar)
        self.setMinimumHeight(74)

    def set_value(self, value):
        self.value_label.setText(str(round(value)))
        self.bar.value = value
        self.bar.update()


class Meter(QWidget):
    def __init__(self, color=GREEN):
        super().__init__()
        self.setFixedHeight(6)
        self.value = 0
        self.color = color

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#eef0eb"))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        p.setBrush(QColor("#d28b65" if self.value < 20 else self.color))
        p.drawRoundedRect(QRectF(0, 0, self.width() * min(100, max(0, self.value)) / 100, 6), 3, 3)


def draw_pet(painter, pixmap, rectangle, mirrored=False):
    if pixmap.isNull():
        return
    size = pixmap.size().scaled(rectangle.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
    target = QRectF(rectangle.center().x() - size.width() / 2, rectangle.bottom() - size.height(), size.width(), size.height())
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if mirrored:
        painter.translate(2 * target.center().x(), 0)
        painter.scale(-1, 1)
    painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
    painter.restore()


class Room(QWidget):
    clicked = Signal()

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.pet_name = "miaomiao"
        self.setMinimumSize(340, 315)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        player.frame_changed.connect(self.update)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 20, 20)
        p.setClipPath(clip)
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0, QColor("#dce9dd"))
        gradient.setColorAt(1, QColor("#eef1df"))
        p.fillRect(self.rect(), gradient)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#f7f5e9"))
        p.drawRect(QRectF(0, h * .73, w, h * .27))
        # Soft afternoon light through a little arched window.
        p.setBrush(QColor(255, 255, 244, 135))
        p.drawRoundedRect(QRectF(w - 124, 52, 83, 132), 40, 40)
        p.setPen(QPen(QColor("#faf9ed"), 5))
        p.drawLine(QPointF(w - 82, 57), QPointF(w - 82, 180))
        p.drawLine(QPointF(w - 123, 117), QPointF(w - 42, 117))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e0dbc8"))
        p.drawEllipse(QRectF(w * .15, h - 64, w * .70, 36))
        p.setBrush(QColor("#ede6d4"))
        p.drawEllipse(QRectF(w * .16, h - 66, w * .68, 30))
        # Plant uses native vector painting and is intentionally behind the cat.
        p.setPen(QPen(QColor("#77927b"), 3))
        p.drawLine(QPointF(46, h * .70), QPointF(46, h * .46))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#8fa789"))
        p.drawEllipse(QRectF(26, h * .50, 22, 12))
        p.drawEllipse(QRectF(46, h * .55, 22, 12))
        p.drawEllipse(QRectF(35, h * .43, 16, 26))
        p.setBrush(QColor("#c6bca1"))
        pot = QPainterPath(QPointF(28, h * .66))
        pot.lineTo(64, h * .66)
        pot.lineTo(59, h * .76)
        pot.lineTo(34, h * .76)
        pot.closeSubpath()
        p.drawPath(pot)
        p.setPen(QColor(INK))
        p.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.DemiBold))
        p.drawText(QRectF(22, 20, w - 44, 23), "一只小猫的慢生活")
        p.setFont(QFont("Microsoft YaHei UI", 8))
        p.setPen(QColor("#78917d"))
        p.drawText(QRectF(22, 47, 190, 20), "MIAO  /  LITTLE MOMENTS")
        draw_pet(p, self.player.frame, QRectF(48, 88, w - 96, h - 140))
        p.setPen(QColor("#758272"))
        p.drawText(QRectF(0, h - 29, w, 22), Qt.AlignmentFlag.AlignCenter, "轻轻点一下，摸摸小脑袋")


class DesktopPet(QWidget):
    petted = Signal()
    panel_requested = Signal()
    menu_requested = Signal(QPoint)
    position_changed = Signal()

    def __init__(self, player, size):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.player = player
        self.mirrored = False
        self.drag_offset = None
        self.drag_start = None
        self.dragged = False
        self.message = "你好呀，我是miaomiao。"
        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.clear_bubble)
        self.resize(size, size + 62)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        player.frame_changed.connect(self.update)

    def say(self, message):
        self.message = message
        self.bubble_timer.start(4500)
        self.update()

    def clear_bubble(self):
        self.message = ""
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_pet(p, self.player.frame, QRectF(8, 62, self.width() - 16, self.height() - 70), self.mirrored)
        if self.message:
            p.setPen(QPen(QColor("#e0e6d8"), 1))
            p.setBrush(QColor(255, 254, 247, 247))
            p.drawRoundedRect(QRectF(7, 3, self.width() - 14, 52), 16, 16)
            p.setFont(QFont("Microsoft YaHei UI", 9))
            p.setPen(QColor(INK))
            p.drawText(QRectF(18, 7, self.width() - 36, 43), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.drag_start = event.globalPosition().toPoint()
            self.dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            if (event.globalPosition().toPoint() - self.drag_start).manhattanLength() > 5:
                self.dragged = True
            if self.dragged:
                self.move(event.globalPosition().toPoint() - self.drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self.dragged:
                self.position_changed.emit()
            else:
                self.petted.emit()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.panel_requested.emit()

    def contextMenuEvent(self, event):
        self.menu_requested.emit(event.globalPos())


class BallGame(QDialog):
    completed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("追追球 · 和小猫玩 20 秒")
        self.setFixedSize(540, 430)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.seconds = 20
        self.score = 0
        self.finished_reward = False
        self.ball = QPointF(270, 240)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.move_timer = QTimer(self)
        self.move_timer.setInterval(1100)
        self.move_timer.timeout.connect(self.new_ball)
        self.move_timer.start()

    def new_ball(self):
        self.ball = QPointF(random.randint(52, 488), random.randint(145, 332))
        self.update()

    def tick(self):
        self.seconds -= 1
        if self.seconds <= 0:
            self.timer.stop()
            self.move_timer.stop()
            self.finish_reward()
            QTimer.singleShot(1800, self.accept)
        self.update()

    def finish_reward(self):
        if not self.finished_reward:
            self.finished_reward = True
            self.completed.emit(min(15, self.score))

    def done(self, result):
        self.timer.stop()
        self.move_timer.stop()
        self.finish_reward()
        super().done(result)

    def mousePressEvent(self, event):
        if self.seconds > 0 and math.hypot(event.position().x() - self.ball.x(), event.position().y() - self.ball.y()) <= 28:
            self.score += 1
            self.new_ball()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#f7f8ef"))
        p.setPen(QColor(INK))
        p.setFont(QFont("Microsoft YaHei UI", 19, QFont.Weight.Bold))
        p.drawText(QRectF(30, 27, 480, 40), "追追球")
        p.setFont(QFont("Microsoft YaHei UI", 10))
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(30, 72, 480, 30), f"点中小球，陪小猫练习捕猎。    剩余 {self.seconds} 秒")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e3e9d9"))
        p.drawRoundedRect(QRectF(22, 119, 496, 242), 20, 20)
        if self.seconds > 0:
            p.setBrush(QColor("#cf9675"))
            p.drawEllipse(self.ball, 28, 28)
            p.setPen(QPen(QColor("#f3d5b4"), 3))
            p.drawArc(QRectF(self.ball.x() - 22, self.ball.y() - 22, 44, 44), 35 * 16, 225 * 16)
            p.drawLine(self.ball + QPointF(-18, 17), self.ball + QPointF(17, -18))
        else:
            p.setPen(QColor(GREEN))
            p.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
            p.drawText(QRectF(25, 194, 490, 80), Qt.AlignmentFlag.AlignCenter, f"配合得真好！\n获得 {min(15, self.score)} 枚喵币")
        p.setPen(QColor(INK))
        p.setFont(QFont("Microsoft YaHei UI", 11))
        p.drawText(QRectF(30, 379, 480, 30), f"已追到 {self.score} 次     ·     每局最多获得 15 枚喵币")
