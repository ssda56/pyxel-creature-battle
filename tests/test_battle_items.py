"""战斗中的道具 / 换人测试（T3b）。

注：T3b 时的「标题画面测试战斗」调试入口已在 T4（明雷遇敌）删除，
对应的 :class:`TitleDebugEntryTest` 一并移除（入口本身是临时脚手架）。
"""

from __future__ import annotations

import unittest

from src.model import Creature
from src.scenes.battle_scene import BattleScene
from tests import battle_helpers as bh
from tests import helpers

#: 伤药 / 蓝药水 / 复活草的道具 ID（《数值设定.md》§7.1）
POTION_ID = 2
BLUE_POTION_ID = 4


class ItemUseTest(unittest.TestCase):
    """5.1：道具指令消耗背包里的东西，用完敌方行动。"""

    def setUp(self):
        helpers.ensure_init()
        self.game, self.scene, self.enemy = bh.make_battle(enemy_species=5)

    def _open_item_menu(self):
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "right")        # 精灵球
        bh.press(self.game, "down")         # 道具
        self.assertEqual(self.scene.command_menu.selected.get("id"), "item")
        bh.press(self.game, "confirm")      # -> ITEM_SELECT
        self.assertEqual(self.scene.state, BattleScene.ITEM_SELECT)

    def test_item_menu_lists_battle_items_only(self):
        self._open_item_menu()
        labels = [it["label"] for it in self.scene.item_menu.items]
        self.assertTrue(any("伤药" in x for x in labels))
        self.assertTrue(any("蓝药水" in x for x in labels))
        self.assertFalse(any("精灵球" in x for x in labels),
                         "精灵球有独立指令，不该出现在道具列表里")

    def test_using_potion_heals_and_consumes_one(self):
        self.scene.active.hp = 10
        before = self.game.player.item_count(POTION_ID)
        self._open_item_menu()
        bh.press(self.game, "confirm")      # 使用伤药
        self.assertEqual(self.game.player.item_count(POTION_ID), before - 1)
        self.assertEqual(self.scene.active.hp, self.scene.active.hp_max)
        self.assertEqual(self.scene.state, BattleScene.MESSAGE)
        # 敌方随后行动 -> 回到五指令
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)
        self.assertTrue(ok, "用完道具后应该回到五指令")

    def test_empty_bag_shows_message(self):
        self.game.player.bag.clear()
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "right")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")      # 道具 -> 没有可用道具
        self.assertEqual(self.scene.state, BattleScene.MESSAGE)
        self.assertIn("没有可用道具", self.scene.message)
        bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)


class SwitchTest(unittest.TestCase):
    """5.1 / 5.4：精灵指令（主动换人）消耗一回合。"""

    def setUp(self):
        helpers.ensure_init()
        party = [Creature(1, level=5), Creature(2, level=5)]
        self.game, self.scene, self.enemy = bh.make_battle(
            enemy_species=5, party=party)

    def test_switch_lists_alive_party_members(self):
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "down")         # 精灵
        self.assertEqual(self.scene.command_menu.selected.get("id"), "party")
        bh.press(self.game, "confirm")      # -> PARTY_SELECT
        self.assertEqual(self.scene.state, BattleScene.PARTY_SELECT)
        names = [it["creature"] for it in self.scene.party_menu.items]
        self.assertEqual(len(names), 1)
        self.assertIs(names[0], self.game.player.party[1])

    def test_switching_changes_active_creature(self):
        bh.press(self.game, "confirm")
        bh.press(self.game, "down")
        bh.press(self.game, "confirm")      # -> PARTY_SELECT
        bh.press(self.game, "confirm")      # 确认换人
        self.assertIs(self.scene.active, self.game.player.party[1])
        # 换完敌方行动 -> 回到五指令
        ok = bh.advance_until(
            self.game, lambda: self.scene.state == BattleScene.COMMAND)
        self.assertTrue(ok, "换人后应该回到五指令")

    def test_no_other_member_shows_message(self):
        self.game.player.party = [self.game.player.party[0]]
        bh.press(self.game, "confirm")      # INTRO -> COMMAND
        bh.press(self.game, "down")         # 精灵
        bh.press(self.game, "confirm")
        self.assertEqual(self.scene.state, BattleScene.MESSAGE)
        self.assertIn("没有可以换的精灵", self.scene.message)


if __name__ == "__main__":
    unittest.main()
