"""UI-independent care, economy, daily quests and crash-safe persistence."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
import json
import math
import os
from pathlib import Path
import time


def today(now: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if now is None else now).strftime("%Y-%m-%d")


STATS = {"food": "饱食", "water": "水分", "energy": "精力", "mood": "心情", "hygiene": "清洁", "health": "健康"}
SHOP = {
    "kibble": dict(name="营养猫粮", price=12, amount=3, description="3 份日常口粮 · 每份饱食 +28", mark="粮"),
    "fish": dict(name="三文鱼小食", price=20, amount=1, description="饱食 +40 · 心情 +12", mark="鱼"),
    "medicine": dict(name="健康补给", price=35, amount=1, description="健康 +30 · 需要时使用", mark="护"),
}
QUESTS = {
    "feed": ("认真吃一顿饭", 1, 20),
    "water": ("记得补充水分", 2, 15),
    "pet": ("摸摸小脑袋", 3, 20),
    "play": ("一起玩一次", 1, 25),
    "clean": ("梳理一次毛发", 1, 15),
}


@dataclass
class PetState:
    name: str = "miaomiao"
    food: float = 78
    water: float = 72
    energy: float = 86
    mood: float = 82
    hygiene: float = 90
    health: float = 100
    bond: float = 12
    xp: int = 0
    coins: int = 120
    inventory: dict = field(default_factory=lambda: {"kibble": 5, "fish": 1, "medicine": 1})
    sleeping: bool = False
    roaming: bool = True
    scale: int = 290
    position: list | None = None
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    day: str = field(default_factory=today)
    counts: dict = field(default_factory=dict)
    claimed: list = field(default_factory=list)
    checked_in: bool = False
    cooldowns: dict = field(default_factory=dict)
    journal: list = field(default_factory=list)

    @property
    def level(self):
        return 1 + self.xp // 100

    @property
    def stage(self):
        return "初见的小伙伴" if self.level < 3 else "默契的好朋友" if self.level < 6 else "形影不离的家人"


class Game:
    def __init__(self, path: Path, now: float | None = None):
        self.path = path
        self.notice = ""
        self.state = self._load()
        now = time.time() if now is None else now
        elapsed = max(0, min(now - self.state.last_seen, 8 * 3600))
        self.advance(elapsed, offline=True)
        self.state.last_seen = now
        self.reset_day(now)
        self.normalize()

    def _load(self):
        if not self.path.exists():
            return PetState()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Save must be an object")
            allowed = {f.name for f in fields(PetState)}
            state = PetState(**{k: v for k, v in raw.items() if k in allowed})
            for key in [*STATS, "bond", "xp", "coins", "created_at", "last_seen", "scale"]:
                value = getattr(state, key)
                if not isinstance(value, (float, int)) or not math.isfinite(value):
                    raise ValueError(f"Invalid field: {key}")
            for key in ["inventory", "counts", "cooldowns"]:
                value = getattr(state, key)
                if not isinstance(value, dict) or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in value.values()):
                    raise ValueError(f"Invalid field: {key}")
            if not isinstance(state.name, str) or not isinstance(state.day, str) or not isinstance(state.claimed, list) or not isinstance(state.journal, list):
                raise ValueError("Invalid text/list fields")
            if not all(isinstance(getattr(state, k), bool) for k in ("sleeping", "roaming", "checked_in")):
                raise ValueError("Invalid settings")
            if any(not isinstance(line, str) for line in state.journal):
                raise ValueError("Invalid journal")
            if state.position is not None and (not isinstance(state.position, list) or len(state.position) != 2 or any(not isinstance(v, int) for v in state.position)):
                state.position = None
            return state
        except (ValueError, TypeError, OSError) as error:
            backup = self.path.with_name(f"{self.path.stem}.corrupt-{time.time_ns()}.json")
            try:
                self.path.replace(backup)
            except OSError:
                # Never overwrite an unreadable save that could not be preserved.
                raise OSError(f"无法备份损坏的存档 {self.path}，请检查文件权限。") from error
            self.notice = f"旧存档格式异常，已保留备份 {backup.name}，为你建立了新存档。"
            return PetState()

    def normalize(self):
        s = self.state
        for name in [*STATS, "bond"]:
            setattr(s, name, max(0.0, min(100.0, float(getattr(s, name)))))
        s.xp, s.coins = max(0, int(s.xp)), max(0, int(s.coins))
        s.scale = max(180, min(420, int(s.scale)))
        s.name = s.name.strip()[:12] or "miaomiao"
        s.inventory = {key: max(0, int(s.inventory.get(key, 0))) for key in SHOP}
        s.counts = {key: max(0, int(s.counts.get(key, 0))) for key in QUESTS}
        s.journal = s.journal[-40:]

    def save(self, now: float | None = None):
        self.normalize()
        self.state.last_seen = time.time() if now is None else now
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(asdict(self.state), stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(self.path)

    def reset_day(self, now=None):
        if self.state.day != today(now):
            self.state.day = today(now)
            self.state.counts = {}
            self.state.claimed = []
            self.state.checked_in = False

    def log(self, message):
        self.state.journal.append(datetime.now().strftime("%H:%M") + "  " + message)
        self.state.journal = self.state.journal[-40:]

    def advance(self, seconds: float, offline=False):
        if seconds <= 0:
            return
        s = self.state
        minutes = min(seconds, 8 * 3600) / 60
        factor = 0.3 if offline else 1.0
        # Offline absence is gentle; health never decays while the app is shut.
        for key, rate in [("food", .18), ("water", .23), ("hygiene", .10), ("mood", .07)]:
            old = getattr(s, key)
            floor = min(old, 15) if offline else 0
            setattr(s, key, max(floor, old - minutes * rate * factor))
        s.energy += minutes * (2.4 if s.sleeping else -.13) * factor
        if not offline:
            if min(s.food, s.water, s.hygiene) < 15:
                s.health -= minutes * .2
            elif min(s.food, s.water, s.hygiene) > 60:
                s.health += minutes * .06
        if s.sleeping and s.energy >= 100:
            s.sleeping = False
        self.normalize()

    def perform(self, action: str, now: float | None = None):
        """Return (success, friendly message, source action number)."""
        now = time.time() if now is None else now
        self.reset_day(now)
        s = self.state
        if action == "sleep":
            s.sleeping = not s.sleeping
            message = "晚安，我会梦到小鱼干。" if s.sleeping else "睡醒啦，伸个懒腰！"
            self.log(message)
            return True, message, 2 if s.sleeping else 11
        if s.sleeping:
            return False, "我正在睡觉，先点「叫醒」吧。", 2
        cooldown = {"pet": 8, "feed": 12, "fish": 12, "water": 12, "clean": 15, "toilet": 30, "play": 60, "explore": 120, "medicine": 15}
        if action not in cooldown:
            return False, "还不认识这个动作。", 8
        group = "feed" if action == "fish" else action
        remaining = s.cooldowns.get(group, 0) - now
        if remaining > 0:
            return False, f"稍等 {math.ceil(remaining)} 秒，再陪我做这件事吧。", 5
        if action in ("play", "explore") and s.energy < 15:
            return False, "有点困啦，先让我睡一会儿。", 12
        if action in ("feed", "fish") and s.food >= 96:
            return False, "肚子饱饱的，留着下一顿吃吧。", 3
        if action == "water" and s.water >= 96:
            return False, "刚喝饱水，过会儿再来吧。", 3
        if action == "medicine" and s.health >= 96:
            return False, "我现在很健康，这份补给先留着吧。", 8
        item = {"feed": "kibble", "fish": "fish", "medicine": "medicine"}.get(action)
        if item and s.inventory.get(item, 0) <= 0:
            return False, f"{SHOP[item]['name']}用完了，去小铺补充一些吧。", 3
        if item:
            s.inventory[item] -= 1
        effects = {
            "feed": ({"food": 28, "bond": 1}, 18, "吃饱了，连胡须都很开心。"),
            "fish": ({"food": 40, "mood": 12, "bond": 2}, 18, "是最喜欢的小鱼！呼噜呼噜～"),
            "water": ({"water": 32}, 17, "咕嘟咕嘟，喝水也要乖乖的。"),
            "pet": ({"mood": 6, "bond": 1}, 15, "再摸一下嘛，最喜欢你了。"),
            "clean": ({"hygiene": 24, "mood": 3}, 13, "毛毛梳顺了，今天也是漂亮小猫。"),
            "toilet": ({"hygiene": 18, "food": -3}, 19, "猫砂盆收拾好啦，舒舒服服。"),
            "play": ({"mood": 12, "energy": -8, "bond": 1}, 10, "来玩追追球！看我有多厉害。"),
            "explore": ({"mood": 8, "energy": -10}, 16, "桌面巡逻完成，找到 12 枚喵币！"),
            "medicine": ({"health": 30}, 13, "补充营养，慢慢恢复精神。"),
        }
        changes, clip, message = effects[action]
        for key, delta in changes.items():
            setattr(s, key, getattr(s, key) + delta)
        s.xp += 3 if action == "pet" else 8
        if action == "explore":
            s.coins += 12
        s.cooldowns[group] = now + cooldown[action]
        s.counts[group] = s.counts.get(group, 0) + 1
        self.normalize()
        self.log(message)
        return True, message, clip

    def buy(self, item):
        if item not in SHOP:
            return False, "没有找到这件商品。"
        product = SHOP[item]
        if self.state.coins < product["price"]:
            return False, "喵币不够啦，签到、完成任务或探索都能获得喵币。"
        self.state.coins -= product["price"]
        self.state.inventory[item] += product["amount"]
        message = f"收到 {product['amount']} 份{product['name']}。"
        self.log(message)
        return True, message

    def check_in(self, now=None):
        self.reset_day(now)
        if self.state.checked_in:
            return False, "今天已经签到，明天再来见面吧。"
        self.state.checked_in = True
        self.state.coins += 40
        self.state.xp += 10
        message = "今天也见到你啦！喵币 +40，成长 +10。"
        self.log(message)
        return True, message

    def claim(self, quest, now=None):
        self.reset_day(now)
        if quest not in QUESTS:
            return False, "任务不存在。"
        name, goal, reward = QUESTS[quest]
        if quest in self.state.claimed:
            return False, "这个奖励已经领过啦。"
        if self.state.counts.get(quest, 0) < goal:
            return False, "再陪我一会儿，就能完成这个任务。"
        self.state.claimed.append(quest)
        self.state.coins += reward
        self.state.xp += 10
        message = f"完成「{name}」，喵币 +{reward}，成长 +10。"
        self.log(message)
        return True, message
