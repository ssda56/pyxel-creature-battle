"""出入口（portal）传送测试。

- map1 (28,10) -> map2，落点 (2,15)；
- map2 (1,15) -> map1，落点 (27,10)；
- 传送必须走淡入淡出（fade）。
"""

from __future__ import annotations

import unittest

from src.scenes.field_scene import FADE_FRAMES, STEP_FRAMES
from tests import field_helpers


class PortalTravelTest(unittest.TestCase):
    """双向互通。"""

    def test_village_to_field(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 12}], x=27, y=10)
        self.assertEqual(scene.map_id, 1)

        # 走一格踩上传送格
        field_helpers.run(game, STEP_FRAMES)
        self.assertEqual((scene.gx, scene.gy), (28, 10))
        self.assertTrue(scene.fade.is_active, "踩上传送格必须开始淡出转场")
        self.assertEqual(scene.map_id, 1)

        # 淡出结束 -> 已经换到野外
        field_helpers.run(game, FADE_FRAMES + 2)
        self.assertEqual(scene.map_id, 2)
        self.assertEqual((scene.gx, scene.gy), (2, 15))

    def test_field_back_to_village(self):
        game, scene = field_helpers.make_field(
            map_id=2, script=[{"left": 12}], x=2, y=15)
        self.assertEqual(scene.map_id, 2)

        field_helpers.run(game, STEP_FRAMES)
        self.assertEqual((scene.gx, scene.gy), (1, 15))
        self.assertTrue(scene.fade.is_active)

        field_helpers.run(game, FADE_FRAMES + 2)
        self.assertEqual(scene.map_id, 1)
        self.assertEqual((scene.gx, scene.gy), (27, 10))

    def test_round_trip(self):
        """来回走一趟，回到新手村。"""
        from src.core.input import FakeInput

        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 12}], x=27, y=10)
        field_helpers.run(game, STEP_FRAMES + FADE_FRAMES + 2)
        self.assertEqual(scene.map_id, 2)
        self.assertEqual((scene.gx, scene.gy), (2, 15))

        # 等淡入结束，再往左走回新手村
        field_helpers.run(game, FADE_FRAMES + 2)
        game.input = FakeInput(script=[{"left": 40}])
        field_helpers.run(game, STEP_FRAMES)     # 踩上传送格
        self.assertEqual((scene.gx, scene.gy), (1, 15))
        field_helpers.run(game, FADE_FRAMES + 2)
        self.assertEqual(scene.map_id, 1)
        self.assertEqual((scene.gx, scene.gy), (27, 10))

    def test_player_state_tracks_map_change(self):
        game, scene = field_helpers.make_field(
            map_id=1, script=[{"right": 12}], x=27, y=10)
        field_helpers.run(game, STEP_FRAMES + FADE_FRAMES + 2)
        self.assertEqual(game.player_state["map_id"], 2)
        self.assertEqual(game.player_state["x"], 2)
        self.assertEqual(game.player_state["y"], 15)


class FadeTest(unittest.TestCase):
    """淡入淡出本身。"""

    def test_fade_out_then_in(self):
        from src.ui.transition import Fade

        fade = Fade()
        self.assertFalse(fade.is_active)
        self.assertFalse(fade.is_black)

        done = []
        fade.start_out(10, on_done=lambda: done.append("out"))
        self.assertTrue(fade.is_active)
        for _ in range(9):
            fade.update()
            self.assertFalse(fade.is_black)
        fade.update()
        self.assertTrue(fade.is_black)
        self.assertFalse(fade.is_active)
        self.assertEqual(done, ["out"])

        fade.start_in(10)
        self.assertTrue(fade.is_black)
        for _ in range(10):
            fade.update()
        self.assertFalse(fade.is_active)
        self.assertFalse(fade.is_black)

    def test_fade_levels_change_gradually(self):
        """黑度是逐档变化的（肉眼可见渐变），不是一步黑到底。"""
        from src.ui.transition import Fade

        fade = Fade()
        fade.start_out(8)
        levels = []
        for _ in range(8):
            fade.update()
            levels.append(fade.level)
        self.assertEqual(levels, sorted(levels))
        self.assertGreater(len(set(levels)), 2)
        self.assertEqual(levels[-1], 16)


if __name__ == "__main__":
    unittest.main()
