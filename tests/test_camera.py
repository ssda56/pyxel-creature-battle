"""摄像机测试。

规则（src/scenes/field_scene.py::compute_camera）：
- 玩家居中；
- 夹在地图边界内；
- 地图比视口小则整张地图居中。
"""

from __future__ import annotations

import unittest

from src.scenes.field_scene import SCREEN_H, SCREEN_W, compute_camera
from tests import field_helpers

#: 地图 1 像素尺寸
MAP1_W, MAP1_H = 480, 320
#: 地图 2 像素尺寸
MAP2_W, MAP2_H = 640, 480


class ComputeCameraTest(unittest.TestCase):
    """纯函数：夹取与居中。"""

    def test_top_left_is_clamped_to_zero(self):
        self.assertEqual(compute_camera(24, 24, MAP1_W, MAP1_H), (0, 0))

    def test_bottom_right_is_clamped_to_map_edge(self):
        # 玩家在地图右下角附近（28,18）-> 精灵中心 (456, 296)
        self.assertEqual(compute_camera(456, 296, MAP1_W, MAP1_H), (240, 104))

    def test_center_of_map_is_not_clamped(self):
        # 出生点 (15,10) -> 精灵中心 (248, 168)
        self.assertEqual(compute_camera(248, 168, MAP1_W, MAP1_H), (128, 60))

    def test_smaller_map_is_centered(self):
        """地图比视口小：整张地图居中（摄像机为负）。"""
        self.assertEqual(compute_camera(80, 80, 160, 160), (-40, -28))

    def test_bigger_map_uses_player_position(self):
        self.assertEqual(compute_camera(248, 168, MAP2_W, MAP2_H), (128, 60))
        self.assertEqual(compute_camera(632, 472, MAP2_W, MAP2_H), (400, 264))


class SceneCameraTest(unittest.TestCase):
    """场景里的摄像机跟随玩家。"""

    def test_camera_at_map_top_left(self):
        game, scene = field_helpers.make_field(map_id=1, x=1, y=1)
        self.assertEqual(scene.camera, (0, 0))
        self.assertEqual(scene.camera_x, 0)
        self.assertEqual(scene.camera_y, 0)

    def test_camera_at_map_bottom_right(self):
        game, scene = field_helpers.make_field(map_id=1, x=28, y=18)
        self.assertEqual(scene.camera_x, MAP1_W - SCREEN_W)
        self.assertEqual(scene.camera_y, MAP1_H - SCREEN_H)

    def test_camera_follows_player(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 60}], x=15, y=10)
        before = scene.camera_x
        field_helpers.run(game, 60)   # 60 帧 @60fps = 1 秒（与原来的 30 帧 @30fps 等长）
        self.assertGreater(scene.camera_x, before)

    def test_camera_never_leaves_map(self):
        """任何位置摄像机的可视区域都必须在地图内（地图比视口大时）。"""
        for map_id, (mw, mh) in ((1, (MAP1_W, MAP1_H)), (2, (MAP2_W, MAP2_H))):
            for x, y in ((0, 0), (1, 1), (5, 5)):
                game, scene = field_helpers.make_field(map_id=map_id, x=x, y=y)
                cx, cy = scene.camera
                self.assertGreaterEqual(cx, 0)
                self.assertGreaterEqual(cy, 0)
                self.assertLessEqual(cx + SCREEN_W, mw)
                self.assertLessEqual(cy + SCREEN_H, mh)


if __name__ == "__main__":
    unittest.main()
