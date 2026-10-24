"""NPC 交互范围测试（批 5 / T10 · 改动二）。

原来 :meth:`FieldScene.npc_in_front` 只认「面朝方向的紧邻 1 格」，
玩家必须精确站到 NPC 正对面才聊得到天。现在改成：

- :meth:`FieldScene.nearby_npc`：**上下左右四条轴**上 1~4 格内的 NPC 都能对话；
- 同距离时按 **上 → 下 → 左 → 右** 选最近的；
- 靠近时右下角出现「Z 与 XX 交谈」提示。
"""

from __future__ import annotations

import unittest

from src.scenes import field_scene
from tests import field_helpers

#: 护士（精灵中心）在新手村的位置
NURSE = (10, 8)
#: 店员（商店）在新手村的位置
SHOP = (22, 8)

#: 护士上下左右各 4 格（都必须是可走格）
AXIS_CASES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("up-1", (10, 9)),
    ("up-2", (10, 10)),
    ("up-3", (10, 11)),
    ("up-4", (10, 12)),
    ("down-1", (10, 9)),
    ("down-2", (10, 10)),
    ("down-3", (10, 11)),
    ("down-4", (10, 12)),
    ("left-1", (9, 8)),
    ("left-2", (8, 8)),
    ("left-3", (7, 8)),
    ("left-4", (6, 8)),
    ("right-1", (11, 8)),
    ("right-2", (12, 8)),
    ("right-3", (13, 8)),
    ("right-4", (14, 8)),
)

#: 距离 5 格（超出范围）的位置
OUT_OF_RANGE_CASES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("up-5", (10, 13)),
    ("down-5", (10, 3)),
    ("left-5", (5, 8)),
    ("right-5", (15, 8)),
)

#: 斜向（dx、dy 都非 0）—— 不算
DIAGONAL_CASES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("diag-1-1", (11, 9)),
    ("diag-2-2", (12, 10)),
    ("diag-3-1", (13, 9)),
)


def make_field_with_npcs(npcs, x: int, y: int, facing: str = "down", script=None):
    """建一个地图场景，并把 NPC 表换成自定义的（不污染 map_data 的全局数据）。"""
    game, scene = field_helpers.make_field(map_id=1, script=script,
                                          x=x, y=y, facing=facing)
    scene.map = dict(scene.map)
    scene.map["npcs"] = list(npcs)
    return game, scene


class TalkRangeConstantTest(unittest.TestCase):
    """常量本身。"""

    def test_talk_range_is_four(self):
        self.assertEqual(field_scene.NPC_TALK_RANGE, 4)


class NearbyNpcTest(unittest.TestCase):
    """nearby_npc() 的判定规则。"""

    def test_distance_1_to_4_on_every_axis(self):
        """上下左右各 1~4 格都能找到 NPC。"""
        for label, (x, y) in AXIS_CASES:
            with self.subTest(case=label):
                game, scene = field_helpers.make_field(map_id=1, x=x, y=y)
                self.assertEqual((scene.gx, scene.gy), (x, y),
                                 f"{label} 的落点不可走（被退回出生点了）")
                npc = scene.nearby_npc()
                self.assertIsNotNone(npc, f"{label} 应该能交互")
                self.assertEqual(npc["name"], "护士")

    def test_distance_5_is_out_of_range(self):
        """距离 5 格不能交互。"""
        for label, (x, y) in OUT_OF_RANGE_CASES:
            with self.subTest(case=label):
                game, scene = field_helpers.make_field(map_id=1, x=x, y=y)
                self.assertEqual((scene.gx, scene.gy), (x, y))
                self.assertIsNone(scene.nearby_npc(), f"{label} 不该能交互")

    def test_diagonal_does_not_count(self):
        """斜向不算（四条轴之外）。"""
        for label, (x, y) in DIAGONAL_CASES:
            with self.subTest(case=label):
                game, scene = field_helpers.make_field(map_id=1, x=x, y=y)
                self.assertEqual((scene.gx, scene.gy), (x, y))
                self.assertIsNone(scene.nearby_npc(), f"{label} 不该能交互")

    def test_nearest_npc_wins(self):
        """两个 NPC 都在范围内时选**最近**的那个。"""
        far = {"x": 10, "y": 8, "kind": "npc", "name": "远的", "lines": ["远"]}
        near = {"x": 10, "y": 11, "kind": "npc", "name": "近的", "lines": ["近"]}
        game, scene = make_field_with_npcs([far, near], 10, 12)
        npc = scene.nearby_npc()
        self.assertIsNotNone(npc)
        self.assertEqual(npc["name"], "近的")

    def test_same_distance_priority_up_down_left_right(self):
        """同距离时：上 → 下 → 左 → 右。"""
        up = {"x": 10, "y": 8, "kind": "npc", "name": "上", "lines": ["上"]}
        down = {"x": 10, "y": 12, "kind": "npc", "name": "下", "lines": ["下"]}
        left = {"x": 8, "y": 10, "kind": "npc", "name": "左", "lines": ["左"]}
        right = {"x": 12, "y": 10, "kind": "npc", "name": "右", "lines": ["右"]}

        game, scene = make_field_with_npcs([right, down, left, up], 10, 10)
        self.assertEqual(scene.nearby_npc()["name"], "上",
                         "同距离时应优先选「上」")

        game, scene = make_field_with_npcs([right, down, left], 10, 10)
        self.assertEqual(scene.nearby_npc()["name"], "下",
                         "没有「上」时应选「下」")

        game, scene = make_field_with_npcs([right, left], 10, 10)
        self.assertEqual(scene.nearby_npc()["name"], "左",
                         "没有「上/下」时应选「左」")

        game, scene = make_field_with_npcs([right], 10, 10)
        self.assertEqual(scene.nearby_npc()["name"], "右")


class TalkWithoutFacingTest(unittest.TestCase):
    """按确认键就能对话，**不要求朝向**。"""

    def test_confirm_opens_dialogue_from_4_tiles_away(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}], x=10, y=12, facing="down")
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue, "4 格外按确认键应该能对话")
        self.assertEqual(scene.dialogue["npc"]["name"], "护士")

    def test_confirm_works_while_facing_away(self):
        """背对着 NPC 也照样能聊。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}], x=10, y=10, facing="left")
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue, "不要求朝向")
        self.assertEqual(scene.dialogue["npc"]["name"], "护士")

    def test_confirm_out_of_range_opens_nothing(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}], x=10, y=13, facing="up")
        field_helpers.run(game, 1)
        self.assertIsNone(scene.dialogue, "5 格外不应该打开对话")


class NpcHintTest(unittest.TestCase):
    """右下角提示。"""

    def test_hint_appears_in_range(self):
        game, scene = field_helpers.make_field(map_id=1, x=10, y=11)
        hint = scene.npc_hint()
        self.assertIsNotNone(hint, "范围内应该有提示")
        self.assertIn("护士", hint)
        self.assertIn("Z", hint)

    def test_hint_disappears_out_of_range(self):
        game, scene = field_helpers.make_field(map_id=1, x=10, y=13)
        self.assertIsNone(scene.npc_hint(), "范围外不该有提示")

    def test_hint_hidden_while_dialogue_open(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}], x=10, y=10)
        field_helpers.run(game, 1)
        self.assertIsNotNone(scene.dialogue)
        self.assertIsNone(scene.npc_hint(), "对话中不该再显示提示")

    def test_hint_draw_does_not_crash(self):
        """有提示 / 没提示两种情况画一帧都不报错。"""
        game, scene = field_helpers.make_field(map_id=1, x=10, y=10)
        field_helpers.run(game, 1)
        game, scene2 = field_helpers.make_field(map_id=1, x=10, y=13)
        field_helpers.run(game, 1)


if __name__ == "__main__":
    unittest.main()
