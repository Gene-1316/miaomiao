import json
import time

import pytest

from pet.model import Game, QUESTS


@pytest.fixture
def game(tmp_path):
    return Game(tmp_path / "pet.json")


def test_feed_consumes_one_item_and_caps_food(game):
    game.state.food = 80
    previous = game.state.inventory["kibble"]
    assert game.perform("feed")[0]
    assert game.state.food == 100
    assert game.state.inventory["kibble"] == previous - 1


def test_rejected_feed_never_spends_or_rewards(game):
    game.state.inventory["kibble"] = 0
    before = game.state.xp
    assert not game.perform("feed")[0]
    assert game.state.xp == before


def test_food_variants_share_cooldown(game):
    game.state.food = 5
    now = time.time()
    assert game.perform("feed", now)[0]
    assert not game.perform("fish", now + 1)[0]


def test_sleep_restores_energy_and_blocks_feeding(game):
    game.state.energy = 20
    assert game.perform("sleep")[2] == 2
    assert not game.perform("feed")[0]
    game.advance(600)
    assert game.state.energy == pytest.approx(44)
    assert game.perform("sleep")[2] == 11


def test_full_sleep_wakes_up(game):
    game.state.sleeping = True
    game.state.energy = 99
    game.advance(120)
    assert game.state.energy == 100
    assert not game.state.sleeping


def test_negative_time_does_not_change_state(game):
    food = game.state.food
    game.advance(-900)
    assert game.state.food == food


def test_offline_is_capped_and_does_not_damage_health(game):
    game.state.last_seen = time.time() - 30 * 86400
    game.state.health = 41
    game.save(now=game.state.last_seen)
    loaded = Game(game.path)
    assert loaded.state.food > 45
    assert loaded.state.health == 41


def test_offline_does_not_magically_refill_empty_food(game):
    game.state.food = 2
    game.advance(60, offline=True)
    assert game.state.food <= 2


def test_quest_reward_only_once(game):
    game.state.counts["feed"] = 1
    coins = game.state.coins
    assert game.claim("feed")[0]
    assert game.state.coins == coins + QUESTS["feed"][2]
    assert not game.claim("feed")[0]


def test_daily_rollover_resets_quests_and_checkin(game):
    game.state.day = "2000-01-01"
    game.state.counts = {"pet": 3}
    game.state.claimed = ["pet"]
    game.state.checked_in = True
    game.reset_day()
    assert game.state.counts == {}
    assert not game.state.claimed
    assert not game.state.checked_in


def test_checkin_cannot_be_farmed(game):
    coins = game.state.coins
    assert game.check_in()[0]
    assert not game.check_in()[0]
    assert game.state.coins == coins + 40


def test_shop_cannot_overdraw(game):
    game.state.coins = 11
    stock = game.state.inventory.copy()
    assert not game.buy("kibble")[0]
    assert game.state.coins == 11
    assert game.state.inventory == stock


def test_shop_delivers_correct_amount(game):
    coins = game.state.coins
    stock = game.state.inventory["kibble"]
    assert game.buy("kibble")[0]
    assert game.state.inventory["kibble"] == stock + 3
    assert game.state.coins == coins - 12


def test_exploration_requires_energy_and_has_cooldown(game):
    game.state.energy = 5
    assert not game.perform("explore")[0]
    game.state.energy = 30
    now = time.time()
    assert game.perform("explore", now)[0]
    assert game.state.energy == 20
    assert not game.perform("explore", now + 1)[0]


def test_save_roundtrip_preserves_progress(game):
    game.state.name = "团子"
    game.perform("pet")
    game.buy("fish")
    game.state.position = [13, 28]
    game.save()
    loaded = Game(game.path)
    assert loaded.state.name == "团子"
    assert loaded.state.inventory == game.state.inventory
    assert loaded.state.xp == game.state.xp
    assert loaded.state.position == [13, 28]
    assert not game.path.with_suffix(".tmp").exists()


@pytest.mark.parametrize("payload", ["{broken", "[]", '{"food":"oops"}', '{"energy":NaN}', '{"inventory":[]}', '{"sleeping":"yes"}'])
def test_invalid_save_is_preserved(tmp_path, payload):
    path = tmp_path / "pet.json"
    path.write_text(payload, encoding="utf-8")
    game = Game(path)
    backups = list(tmp_path.glob("pet.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == payload
    assert game.notice
    game.save()
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "miaomiao"


def test_future_fields_do_not_break_save(game):
    game.path.write_text('{"name":"糯米","future_version_field":true}', encoding="utf-8")
    assert Game(game.path).state.name == "糯米"
