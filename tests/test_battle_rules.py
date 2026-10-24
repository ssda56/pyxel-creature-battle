"""战斗规则测试（T3b）：胜利结算 / 捕捉 / 逃跑 / 战败 / 道具 / 换人。

数值全部来自《数值设定.md》§5 与 §8。
"""

from __future__ import annotations

import unittest

from src.model import Creature
from src.scenes.battle_scene import (
    BattleScene,
    catch_exp,
    escape_chance,
    mp_recover_amount,
    victory_dollars,
    victory_exp,
)
from src.scenes.field_scene import FieldScene
from tests import battle_helpers as bh
from tests import helpers

#: 精灵球道具 ID
BALL_ID = 1


class RewardFormulaTest(unittest.TestCase):
    """5.7 的几个公式（纯函数）。"""

    def test_victory_exp(self):
        self.assertEqual(victory_exp(6), 110)      # 20 + 15 * 6
        self.assertEqual(victory_exp(5), 95)       # 20 + 15 * 5

    def test_victory_dollars(self):
        self.assertEqual(victory_dollars(6), 30)   # 6 + 4 * 6
        self.assertEqual(victory_dollars(5), 26)   # 6 + 4 * 5

    def test_mp_recover_is_ten_percent_rounded_up(self):
        self.assertEqual(mp_recover_amount(30), 3)  # ceil(3.0)
        self.assertEqual(mp_recover_amount(16), 2)  # ceil(1.6)
        self.assertEqual(mp_recover_amount(17), 2)  # ceil(1.7)
        self.assertEqual(mp_recover_amount(18), 2)  # ceil(1.8)

    def test_catch_exp(self):
        self.assertEqual(catch_exp(5), 15)         # 3 * 5
        self.assertEqual(catch_exp(6), 18)         # 3 * 6


class VictoryRewardTest(unittest.TestCase):
    """5.7：胜利给经验、金币，并回复 10% 最大 MP。"""

    def setUp(self):
        helpers.ensure_init()
        self.results = []
        # 用 Lv19 的小火狮：+110 经验不会升级，MP 回复值可精确断言
        party = [Creature(1, level=19)]
        party[0].mp = 10
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=5, enemy_level=6, party=party,
            on_end=self.results.append)
        self.party = self.game.player.party
        self.enemy.hp = 1          # 一击就倒

    def _win(self):
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "confirm")   # -> SKILL_SELECT
        bh.press(self.game, "down")      # 撞击
        bh.press(self.game, "confirm")   # 使用
        ok = bh.advance_until(self.game,
                               lambda: self.scene.result == "win")
        self.assertTrue(ok, "战斗没有正常结束")

    def test_victory_gives_exp_dollars_and_mp(self):
        self._win()
        self.assertEqual(self.scene.result, "win")
        self.assertEqual(self.results, ["win"])
        # 经验 20 + 15 * 6 = 110
        self.assertEqual(self.party[0].exp, 110)
        # 金币 6 + 4 * 6 = 30
        self.assertEqual(self.game.player.dollars, 330)
        # MP 回复 10%（Lv19 最大 MP = 30 -> 3 点）
        self.assertEqual(self.party[0].mp, 13)
        # 写回 player_state（FieldScene 的 HUD 读它）
        self.assertEqual(self.game.player_state["dollars"], 330)

    def test_victory_returns_to_field_scene(self):
        self._win()
        self.assertIsInstance(self.game.scenes.current, FieldScene)


class EscapeChanceTest(unittest.TestCase):
    """5.5：p = clamp(0.55 + 速度差 * 0.02, 0.20, 0.95)。"""

    def test_same_speed_is_base(self):
        self.assertAlmostEqual(escape_chance(10, 10), 0.55)

    def test_faster_player_raises_chance(self):
        self.assertAlmostEqual(escape_chance(15, 10), 0.65)
        self.assertAlmostEqual(escape_chance(20, 10), 0.75)

    def test_slower_player_lowers_chance(self):
        self.assertAlmostEqual(escape_chance(5, 10), 0.45)

    def test_clamped_to_max(self):
        self.assertEqual(escape_chance(100, 1), 0.95)
        self.assertEqual(escape_chance(999, 999), 0.55)

    def test_clamped_to_min(self):
        self.assertEqual(escape_chance(1, 100), 0.20)
        self.assertEqual(escape_chance(0, 999), 0.20)


class EscapeSceneTest(unittest.TestCase):
    """5.5：逃跑成功 -> 战斗结束（result = run）。"""

    def setUp(self):
        helpers.ensure_init()
        self.results = []
        self.game, self.scene, self.enemy = bh.make_battle(
            seed=1, on_end=self.results.append)

    def test_running_away_ends_battle(self):
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "down")      # 精灵
        bh.press(self.game, "down")      # 逃跑
        self.assertEqual(self.scene.command_menu.selected.get("id"), "run")
        bh.press(self.game, "confirm")   # 逃跑
        ok = bh.advance_until(self.game,
                               lambda: self.scene.result == "run")
        self.assertTrue(ok, "逃跑没有正常结束")
        self.assertEqual(self.results, ["run"])
        self.assertIsInstance(self.game.scenes.current, FieldScene)

    def test_battle_ends_keeps_map_and_position(self):
        self.game.player_state.update({"map_id": 2, "x": 5, "y": 7})
        bh.press(self.game, "confirm")
        bh.press(self.game, "down")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")
        bh.advance_until(self.game,
                         lambda: self.scene.result == "run")
        field = self.game.scenes.current
        self.assertIsInstance(field, FieldScene)
        self.assertEqual(field.map_id, 2)
        self.assertEqual((field.gx, field.gy), (5, 7))


class CatchTest(unittest.TestCase):
    """8 + 5.7：捕捉成功进队伍、给 3 倍等级经验、不给金币；失败消耗 1 个球。"""

    def setUp(self):
        helpers.ensure_init()
        self.results = []

    def _use_ball(self):
        bh.press(self.game, "confirm")   # INTRO -> COMMAND
        bh.press(self.game, "right")     # 移动到「精灵球」
        self.assertEqual(self.scene.command_menu.selected.get("id"), "ball")
        bh.press(self.game, "confirm")   # 抛出精灵球

    def test_catch_success(self):
        # random.Random(1).random() = 0.134 < 成功率 -> 成功
        self.game, self.scene, self.enemy = bh.make_battle(
            seed=1, on_end=self.results.append)
        self.enemy.hp = 1
        balls = self.game.player.item_count(BALL_ID)
        self._use_ball()
        ok = bh.advance_until(self.game,
                               lambda: self.scene.result == "catch")
        self.assertTrue(ok, "捕捉没有结束")
        self.assertEqual(self.scene.result, "catch")
        self.assertEqual(self.results, ["catch"])
        # 进了队伍
        self.assertEqual(len(self.game.player.party), 2)
        self.assertIs(self.game.player.party[1], self.enemy)
        # 不给金币
        self.assertEqual(self.game.player.dollars, 300)
        # 战精灵得 3 * 5 = 15 经验
        self.assertEqual(self.game.player.party[0].exp, 15)
        # 精灵球消耗 1 个
        self.assertEqual(self.game.player.item_count(BALL_ID), balls - 1)

    def test_catch_failure_consumes_one_ball(self):
        # random.Random(2).random() = 0.956 > 成功率 -> 失败
        self.game, self.scene, self.enemy = bh.make_battle(
            seed=2, on_end=self.results.append)
        self.enemy.hp = 1
        balls = self.game.player.item_count(BALL_ID)
        self._use_ball()
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)
        self.assertTrue(ok, "捕捉失败后应该继续战斗")
        self.assertEqual(self.game.player.item_count(BALL_ID), balls - 1)
        self.assertEqual(len(self.game.player.party), 1)
        self.assertEqual(self.game.player.dollars, 300)
        self.assertIsNone(self.scene.result)


class DefeatTest(unittest.TestCase):
    """5.6：全队倒下 -> 回新手村、全队恢复、不扣金币。"""

    def setUp(self):
        helpers.ensure_init()
        self.results = []
        party = [Creature(1, level=5)]
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=5, party=party, on_end=self.results.append)
        self.party = self.game.player.party
        self.party[0].hp = 1
        # 先出一招，让敌方打回来把我方打倒
        bh.press(self.game, "confirm")
        bh.press(self.game, "confirm")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")

    def test_defeat_returns_to_village_and_heals_party(self):
        ok = bh.advance_until(
            self.game,
            lambda: isinstance(self.game.scenes.current, FieldScene))
        self.assertTrue(ok, "战败后没有回到地图")
        field = self.game.scenes.current
        self.assertIsInstance(field, FieldScene)
        # 新手村出生点 (15, 10)
        self.assertEqual(field.map_id, 1)
        self.assertEqual((field.gx, field.gy), (15, 10))
        # 全队 HP / MP 满
        self.assertEqual(self.party[0].hp, self.party[0].hp_max)
        self.assertEqual(self.party[0].mp, self.party[0].mp_max)
        # 不扣金币
        self.assertEqual(self.game.player.dollars, 300)
        self.assertEqual(self.game.player_state["dollars"], 300)
        # on_end 回调
        self.assertEqual(self.results, ["lose"])
        self.assertEqual(self.scene.result, "lose")
