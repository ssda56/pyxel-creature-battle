"""特殊招式测试（T3b）：治疗 / 能力下降（§3 的威力 0 招式）。"""

from __future__ import annotations

import unittest

from src.model import Creature
from src.scenes.battle_scene import BattleScene
from tests import battle_helpers as bh
from tests import helpers


class HealSkillTest(unittest.TestCase):
    """治愈波动：回复自身最大 HP 的 25%（最少 12），并清除能力下降。"""

    def setUp(self):
        helpers.ensure_init()
        # 独角兽 Lv5 的初始技能是「圣光」「治愈波动」
        party = [Creature(5, level=5)]
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=3, party=party)
        self.active = self.scene.active

    def test_heal_restores_hp_and_clears_debuff(self):
        self.active.hp = 20
        self.active.apply_atk_mod(0.75, 3)
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "confirm")      # -> SKILL_SELECT
        bh.press(self.game, "down")         # 治愈波动
        bh.press(self.game, "confirm")      # 使用
        ok = bh.advance_until(
            self.game,
            lambda: bool(self.scene.message)
            and "恢复" in (self.scene.message or ""))
        self.assertTrue(ok, "没有出现治疗消息")
        self.assertGreater(self.active.hp, 20)
        # 能力下降被清除
        self.assertEqual(self.active.atk_mod, 1.0)
        self.assertEqual(self.active.mod_rounds, 0)
        # 消耗了 MP
        self.assertLess(self.active.mp, self.active.mp_max)


class DebuffSkillTest(unittest.TestCase):
    """吼叫：敌方 ATK × 0.75，持续 3 回合。"""

    def setUp(self):
        helpers.ensure_init()
        # 三头犬 Lv5 的初始技能是「暗影咬」「吼叫」
        party = [Creature(6, level=5)]
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=3, party=party)

    def test_howl_lowers_enemy_attack_for_3_rounds(self):
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "confirm")      # -> SKILL_SELECT
        bh.press(self.game, "down")         # 吼叫
        bh.press(self.game, "confirm")      # 使用
        ok = bh.advance_until(
            self.game,
            lambda: bool(self.scene.message)
            and "攻击下降" in (self.scene.message or ""))
        self.assertTrue(ok, "没有出现减益消息")
        self.assertEqual(self.enemy.atk_mod, 0.75)
        self.assertEqual(self.enemy.mod_rounds, 3)

    def test_mod_expires_after_turn(self):
        bh.press(self.game, "confirm")
        bh.press(self.game, "confirm")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")
        bh.advance_until(
            self.game,
            lambda: bool(self.scene.message)
            and "攻击下降" in (self.scene.message or ""))
        # 这一回合结束 -> tick_mods -> 剩余回合数 -1
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)
        self.assertTrue(ok, "回合没有结束")
        self.assertEqual(self.enemy.mod_rounds, 2)
