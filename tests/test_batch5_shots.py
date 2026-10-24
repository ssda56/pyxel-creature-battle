"""批 5 体验改进截图（批 5 / T10）。

产出三张图，方便肉眼核对：

- `batch5_portal.png`   玩家站在传送阵上（法阵光环在主角轮廓外露出来）
- `batch5_npc_hint.png`靠近 NPC 时右下角出现「Z 与 护士 交谈」提示
- `batch5_quit_dialog.png`退出确认弹窗盖在所有内容之上

外加一张 `batch5_portal_near.png`：玩家站在传送阵**旁边一格**，
这时整个法阵圆环都看得见（站在正上方时主角会盖住图块中央）。
"""

from __future__ import annotations

import os
import unittest

from src.core.game import Game
from src.core.input import FakeInput
from src.model import Player
from tests import field_helpers, helpers

PORTAL_SHOT = field_helpers.shot_path("batch5_portal.png")
PORTAL_NEAR_SHOT = field_helpers.shot_path("batch5_portal_near.png")
NPC_HINT_SHOT = field_helpers.shot_path("batch5_npc_hint.png")
QUIT_DIALOG_SHOT = field_helpers.shot_path("batch5_quit_dialog.png")
QUIT_DIALOG_NO_SAVE_SHOT = field_helpers.shot_path("batch5_quit_dialog_no_save.png")

#: 新手村东边的传送阵格
PORTAL_CELL = (28, 10)
#: 护士在新手村的位置
NURSE = (10, 8)


class Batch5ShotTest(unittest.TestCase):
    """无窗口跑几帧并截图。"""

    def setUp(self):
        helpers.ensure_init()

    def _check(self, path: str) -> None:
        self.assertTrue(os.path.exists(path), f"截图没有生成：{path}")
        self.assertGreater(os.path.getsize(path), 1000)
        self.assertEqual(helpers.png_size(path), (480, 432))

    def test_portal_screenshot(self):
        """玩家站在传送阵上。"""
        game, scene = field_helpers.make_field(
            map_id=1, x=PORTAL_CELL[0], y=PORTAL_CELL[1], facing="right")
        self.assertEqual((scene.gx, scene.gy), PORTAL_CELL)
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=PORTAL_SHOT, scale=2)
        self._check(PORTAL_SHOT)

    def test_portal_near_screenshot(self):
        """玩家站在传送阵旁边一格：整个法阵圆环都看得见。"""
        game, scene = field_helpers.make_field(
            map_id=1, x=PORTAL_CELL[0] - 1, y=PORTAL_CELL[1], facing="right")
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=PORTAL_NEAR_SHOT, scale=2)
        self._check(PORTAL_NEAR_SHOT)

    def test_npc_hint_screenshot(self):
        """靠近 NPC 时右下角出现提示。"""
        game, scene = field_helpers.make_field(map_id=1, x=10, y=10, facing="up")
        self.assertIsNotNone(scene.npc_hint(), "截图前应当有 NPC 提示")
        helpers.run_frames(game.update, game.draw, 4,
                           shot_path=NPC_HINT_SHOT, scale=2)
        self._check(NPC_HINT_SHOT)

    def test_quit_dialog_screenshot(self):
        """退出确认弹窗盖在所有内容之上（已开局：存档项可选）。"""
        game, scene = field_helpers.make_field(map_id=1, x=10, y=10, facing="up")
        game.player = Player.new_game(1)
        game.input = FakeInput(script=[{"quit": 1}])
        helpers.run_frames(game.update, game.draw, 3,
                           shot_path=QUIT_DIALOG_SHOT, scale=2)
        self.assertTrue(game.quit_dialog_active)
        self._check(QUIT_DIALOG_SHOT)

    def test_quit_dialog_without_player_screenshot(self):
        """还没开局（标题画面）：存档项是灰的，只有直接退出 / 取消可选。"""
        game = Game(input=FakeInput(script=[{"quit": 1}]))
        helpers.run_frames(game.update, game.draw, 3,
                           shot_path=QUIT_DIALOG_NO_SAVE_SHOT, scale=2)
        self.assertTrue(game.quit_dialog_active)
        self._check(QUIT_DIALOG_NO_SAVE_SHOT)


if __name__ == "__main__":
    unittest.main()
