"""标题画面：无窗口跑 10 帧并截图到 docs/shots/batch1_title.png。"""

import os
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.scenes.title_scene import MENU_ITEMS
from tests import helpers

#: 截图输出路径
SHOT_PATH = os.path.join(helpers.PROJECT_ROOT, "docs", "shots", "batch1_title.png")


class TitleShotTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()

    def test_screenshot_file_is_created(self):
        game = Game()
        game.input = FakeInput()
        helpers.run_frames(game.update, game.draw, 10, shot_path=SHOT_PATH, scale=2)

        self.assertTrue(os.path.exists(SHOT_PATH), "截图文件没有生成")
        self.assertGreater(os.path.getsize(SHOT_PATH), 1000, "截图文件太小")

    def test_screenshot_is_480x432_png(self):
        game = Game()
        game.input = FakeInput()
        helpers.run_frames(game.update, game.draw, 10, shot_path=SHOT_PATH, scale=2)

        width, height = helpers.png_size(SHOT_PATH)
        self.assertEqual((width, height), (480, 432))


class TitleSceneBehaviourTest(unittest.TestCase):
    """标题画面的菜单交互（用假输入驱动）。"""

    def setUp(self):
        helpers.ensure_init()
        self.game = Game()
        self.scene = self.game.scenes.current

    def test_start_scene_is_title(self):
        from src.scenes.title_scene import TitleScene

        self.assertIsInstance(self.scene, TitleScene)
        self.assertEqual(self.scene.index, 0)

    def test_down_moves_cursor(self):
        self.game.input = FakeInput(script=[{"down": 1}])
        self.game.update()
        self.assertEqual(self.scene.index, 1)

    def test_up_wraps_around(self):
        self.game.input = FakeInput(script=[{"up": 1}])
        self.game.update()
        self.assertEqual(self.scene.index, len(MENU_ITEMS) - 1)

    def test_confirm_does_not_crash(self):
        self.game.input = FakeInput(script=[{"confirm": 1}])
        self.game.update()
        self.assertIs(self.game.scenes.current, self.scene)

    def test_draw_runs_without_error(self):
        self.game.input = FakeInput()
        helpers.run_frames(self.game.update, self.game.draw, 3)


if __name__ == "__main__":
    unittest.main()
