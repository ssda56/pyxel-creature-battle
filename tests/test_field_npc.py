"""NPC 对话测试。

- 面向相邻格的 NPC 按确认键 -> 打开底部对话框；
- 逐句显示，再按确认键翻页 / 关闭；
- 对话期间玩家不能移动。
"""

from __future__ import annotations

import unittest

from src.data import map_data
from tests import field_helpers

#: 护士（精灵中心）在新手村的位置
NURSE = (10, 8)
#: 玩家站在护士正下方、面向她时的位置
NURSE_FRONT = (10, 9)


class NpcDialogueTest(unittest.TestCase):
    """对话流程。"""

    def test_confirm_opens_dialogue(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 40}],
            x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")

        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue, "面向 NPC 按确认键应该打开对话")
        self.assertEqual(scene.dialogue["page"], 0)
        self.assertEqual(scene.dialogue["npc"]["name"], "护士")
        self.assertTrue(scene.dialogue["lines"])

    def test_dialogue_lines_are_chinese_text(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 40}],
            x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        field_helpers.run(game, 1)
        line = scene.dialogue["lines"][0]
        self.assertTrue(line.strip())
        self.assertTrue(any("\u4e00" <= ch <= "\u9fff" for ch in line),
                        "对话应该是中文")

    def test_dialogue_pages_and_closes(self):
        """确认键逐句翻页，翻完关闭。

        脚本：frame0 确认（开对话）-> 1..40 按住 up（对话期间不能动）
        -> 41 确认（翻页）-> 42 按 up -> 43 确认（翻完关闭）。
        """
        game, scene = field_helpers.make_field(
            map_id=1,
            script=[{"confirm": 1}, {"up": 40}, {"confirm": 1}, {"up": 1}, {"confirm": 1}],
            x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        field_helpers.run(game, 1)
        total = len(scene.dialogue["lines"])

        field_helpers.run(game, 40)          # 对话期间按住 up
        self.assertEqual(scene.dialogue["page"], 0)
        self.assertEqual((scene.gx, scene.gy), NURSE_FRONT)

        field_helpers.run(game, 1)           # 翻页
        self.assertIsNotNone(scene.dialogue)
        self.assertEqual(scene.dialogue["page"], 1)

        field_helpers.run(game, 2)           # 再翻一页 -> 关闭
        self.assertIsNone(scene.dialogue, "翻完所有台词后对话应该关闭")

        self.assertGreaterEqual(total, 1)

    def test_player_cannot_move_during_dialogue(self):
        """对话期间按住方向键也不动。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 40}],
            x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue)

        field_helpers.run(game, 30)
        self.assertEqual((scene.gx, scene.gy), NURSE_FRONT)
        self.assertIsNotNone(scene.dialogue)

    def test_cancel_closes_dialogue(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"cancel": 1}],
            x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue)
        field_helpers.run(game, 1)
        self.assertIsNone(scene.dialogue)

    def test_no_dialogue_without_npc_in_front(self):
        """面前没 NPC 时按确认键不打开对话。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 20}],
            x=15, y=10, facing="up")
        field_helpers.run(game, 1)
        self.assertIsNone(scene.dialogue)

    def test_shop_npc_is_reachable_and_dialogue_works(self):
        """商店 NPC（22,8）也能对话。"""
        shop = [n for n in map_data.MAPS[1]["npcs"] if n["kind"] == "shop"][0]
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 40}],
            x=shop["x"], y=shop["y"] + 1, facing="up")
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue)
        self.assertEqual(scene.dialogue["npc"]["kind"], "shop")

    def test_npc_in_front_returns_npc(self):
        game, scene = field_helpers.make_field(
            map_id=1, x=NURSE_FRONT[0], y=NURSE_FRONT[1], facing="up")
        npc = scene.npc_in_front()
        self.assertIsNotNone(npc)
        self.assertEqual((npc["x"], npc["y"]), NURSE)

        scene.facing = "down"
        self.assertIsNone(scene.npc_in_front())


class HudTest(unittest.TestCase):
    """HUD 与 menu 提示。"""

    def test_menu_key_shows_hint(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"menu": 1}, {"up": 80}], x=15, y=10)
        field_helpers.run(game, 1)
        self.assertGreater(scene.hint_timer, 0)
        field_helpers.run(game, 60)
        self.assertEqual(scene.hint_timer, 0)

    def test_hud_reads_dollars_from_player_state(self):
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        self.assertEqual(game.player_state["dollars"], 300)
        game.player_state["dollars"] = 1234
        field_helpers.run(game, 1)
        scene.draw()   # 不报错即可（文字由 text 模块渲染）


if __name__ == "__main__":
    unittest.main()
