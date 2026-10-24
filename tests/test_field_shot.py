"""地图场景截图：docs/shots/batch1_village.png / batch1_moving.png。"""

from __future__ import annotations

import os
import unittest

import pyxel

from tests import field_helpers, helpers

VILLAGE_SHOT = field_helpers.shot_path("batch1_village.png")
MOVING_SHOT = field_helpers.shot_path("batch1_moving.png")


class FieldShotTest(unittest.TestCase):
    """无窗口跑 FieldScene 并截图。"""

    def setUp(self):
        helpers.ensure_init()

    def test_village_screenshot(self):
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        helpers.run_frames(game.update, game.draw, 20,
                           shot_path=VILLAGE_SHOT, scale=2)
        self.assertTrue(os.path.exists(VILLAGE_SHOT), "村庄截图没有生成")
        self.assertGreater(os.path.getsize(VILLAGE_SHOT), 1000)
        self.assertEqual(helpers.png_size(VILLAGE_SHOT), (480, 432))

    def test_moving_screenshot(self):
        """走路中截图：能看到走路动画帧。"""
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"up": 60}], x=15, y=10)
        helpers.run_frames(game.update, game.draw, 18,
                           shot_path=MOVING_SHOT, scale=2)
        self.assertTrue(os.path.exists(MOVING_SHOT), "移动截图没有生成")
        self.assertGreater(os.path.getsize(MOVING_SHOT), 1000)
        self.assertEqual(helpers.png_size(MOVING_SHOT), (480, 432))

    def test_dialogue_screenshot(self):
        """对话画面截图（放到 docs/shots/batch1_dialogue.png，方便肉眼核对中文）。"""
        path = field_helpers.shot_path("batch1_dialogue.png")
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"confirm": 1}, {"up": 40}], x=10, y=9, facing="up")
        helpers.run_frames(game.update, game.draw, 3, shot_path=path, scale=2)
        self.assertTrue(os.path.exists(path))


class DrawSmokeTest(unittest.TestCase):
    """画一帧不报错。"""

    def test_draw_runs_for_both_maps(self):
        for map_id in (1, 2):
            game, scene = field_helpers.make_field(map_id=map_id)
            helpers.run_frames(game.update, game.draw, 3)


if __name__ == "__main__":
    unittest.main()
