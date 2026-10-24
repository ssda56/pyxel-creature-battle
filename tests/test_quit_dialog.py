"""退出确认弹窗测试（批 5 / T10 · 改动三）。

按 Esc 不再「立刻消失」，而是弹出确认框：

- Esc 打开弹窗（`game.quit_dialog_active` 可查）；
- 弹窗期间**游戏逻辑暂停**（按方向键玩家不动）；
- X 取消 -> 弹窗关闭、游戏恢复；
- Z 存档并退出 -> 调 `save_io.save_game`（**路径重定向到临时目录**），
  写档成功才调退出（桩）；
- 写档失败 -> **不退出**，失败原因显示在弹窗里；
- `game.player is None`（还没开局）-> 存档项置灰，只有「直接退出 / 取消」可选。

**绝不碰仓库里的存档**：本文件在 setUp 里把 `save_io.SAVE_PATH`
改到临时目录，tearDown 还原；并用 sha256 前后比对确认仓库存档没被动过。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import unittest

import pyxel

from src.assets_gen import palette
from src.core.game import Game
from src.core.input import FakeInput
from src.model import Player
from src.model import save_io
from tests import field_helpers, helpers

#: 仓库里真正的存档文件（本文件**只读**它做前后比对）
REPO_SAVE = os.path.join(helpers.PROJECT_ROOT, "saves", "save1.json")


def sha256_of(path: str) -> str | None:
    """算文件 sha256；文件不存在返回 None。"""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class QuitDialogTestBase(unittest.TestCase):
    """公共准备：存档路径重定向到临时目录 + 退出桩。"""

    def setUp(self):
        helpers.ensure_init()
        self._tmp = tempfile.mkdtemp(prefix="dsh_quit_test_")
        self._old_save_path = save_io.SAVE_PATH
        save_io.SAVE_PATH = os.path.join(self._tmp, "save1.json")
        self.repo_hash_before = sha256_of(REPO_SAVE)
        self.quit_calls: list[str] = []

    def tearDown(self):
        save_io.SAVE_PATH = self._old_save_path
        shutil.rmtree(self._tmp, ignore_errors=True)
        self.assertEqual(sha256_of(REPO_SAVE), self.repo_hash_before,
                         "仓库里的存档被改了！")

    def make_game(self, script=None, with_player: bool = True) -> Game:
        """建一个 Game，并装上退出桩（桩替代 pyxel.quit，不会结束进程）。"""
        game = Game(input=FakeInput(script=script))
        if with_player:
            game.player = Player.new_game(1)
        game._do_quit = lambda: self.quit_calls.append("quit")
        return game


class QuitDialogOpenTest(QuitDialogTestBase):
    """Esc 打开弹窗。"""

    def test_escape_opens_dialog(self):
        game = self.make_game(script=[{"quit": 1}])
        self.assertFalse(game.quit_dialog_active)
        game.update()
        self.assertTrue(game.quit_dialog_active, "Esc 应该打开退出确认弹窗")

    def test_dialog_opens_in_title_scene_without_player(self):
        """标题画面（还没开局）也能弹。"""
        game = self.make_game(script=[{"quit": 1}], with_player=False)
        game.update()
        self.assertTrue(game.quit_dialog_active)

    def test_dialog_opens_in_field_scene(self):
        """地图场景也能弹（Game 层的弹窗对所有场景生效）。"""
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        game.input = FakeInput(script=[{"quit": 1}])
        game.update()
        self.assertTrue(game.quit_dialog_active)


class QuitDialogPauseTest(QuitDialogTestBase):
    """弹窗期间游戏逻辑暂停。"""

    def test_direction_key_does_not_move_player(self):
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        game.input = FakeInput(script=[{"quit": 1}, {"right": 40}])
        game.update()
        self.assertTrue(game.quit_dialog_active)
        for _ in range(10):
            game.update()
        self.assertEqual((scene.gx, scene.gy), (15, 10),
                         "弹窗打开时玩家不该能走动")

    def test_scene_update_is_not_called_while_dialog_open(self):
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        calls = []
        original = scene.update
        scene.update = lambda inp: (calls.append(1), original(inp))[1]
        game.input = FakeInput(script=[{"quit": 1}, {"right": 40}])
        game.update()                      # 打开弹窗
        game.update()                      # 弹窗中
        self.assertEqual(calls, [], "弹窗打开时不该调用 scene.update()")

    def test_cancel_closes_dialog_and_resumes(self):
        game, scene = field_helpers.make_field(map_id=1, x=15, y=10)
        game.input = FakeInput(script=[{"quit": 1}, {"cancel": 1}, {"right": 40}])
        game.update()
        self.assertTrue(game.quit_dialog_active)
        game.update()
        self.assertFalse(game.quit_dialog_active, "X 应该关闭弹窗")
        self.assertEqual(self.quit_calls, [], "取消不该退出")
        # 恢复之后能正常走动
        for _ in range(25):
            game.update()
        self.assertEqual(scene.gx, 16, "取消后应该能正常移动")


class QuitSaveTest(QuitDialogTestBase):
    """存档并退出。"""

    def test_save_and_quit_calls_save_then_quit(self):
        game = self.make_game(script=[{"quit": 1}, {"confirm": 1}])
        saved: list[str] = []
        real_save = save_io.save_game

        def spy(g, path=None):
            saved.append("called")
            return real_save(g, path)

        save_io.save_game = spy
        try:
            game.update()                  # 打开弹窗
            game.update()                  # Z -> 存档并退出
        finally:
            save_io.save_game = real_save

        self.assertEqual(saved, ["called"], "应该调用 save_io.save_game")
        self.assertEqual(self.quit_calls, ["quit"], "存完档应该退出一次")
        self.assertTrue(os.path.isfile(save_io.SAVE_PATH),
                        "存档文件应该写到临时目录")

    def test_save_failure_does_not_quit(self):
        game = self.make_game(script=[{"quit": 1}, {"confirm": 1}])
        real_save = save_io.save_game
        save_io.save_game = lambda g, path=None: False
        try:
            game.update()                  # 打开弹窗
            game.update()                  # Z -> 存档失败
        finally:
            save_io.save_game = real_save

        self.assertEqual(self.quit_calls, [], "存档失败不能退出")
        self.assertTrue(game.quit_dialog_active, "存档失败后弹窗要留着")
        self.assertTrue(game.quit_message, "存档失败要在弹窗里说明原因")

    def test_direct_quit_does_not_save(self):
        game = self.make_game(script=[{"quit": 1}, {"menu": 1}])
        real_save = save_io.save_game
        saved: list[str] = []
        save_io.save_game = lambda g, path=None: (saved.append("called"), False)[1]
        try:
            game.update()                  # 打开弹窗
            game.update()                  # C -> 直接退出
        finally:
            save_io.save_game = real_save

        self.assertEqual(saved, [], "直接退出不该写档")
        self.assertEqual(self.quit_calls, ["quit"])


class QuitWithoutPlayerTest(QuitDialogTestBase):
    """还没开局（player is None）时的处理。"""

    def test_save_option_is_disabled(self):
        game = self.make_game(script=[{"quit": 1}], with_player=False)
        game.update()
        self.assertTrue(game.quit_dialog_active)
        options = game.quit_options()
        save_opt = [o for o in options if o["action"] == "save"][0]
        self.assertFalse(save_opt["enabled"], "没开局时存档项应当置灰")
        enabled = [o for o in options if o["enabled"]]
        self.assertEqual([o["action"] for o in enabled], ["quit", "cancel"],
                         "没开局时只有「直接退出 / 取消」可选")

    def test_pressing_save_does_nothing(self):
        game = self.make_game(script=[{"quit": 1}, {"confirm": 1}],
                              with_player=False)
        game.update()
        game.update()
        self.assertEqual(self.quit_calls, [], "没开局时按 Z 不能退出")
        self.assertTrue(game.quit_dialog_active, "弹窗应该还开着")

    def test_can_still_cancel_or_quit_directly(self):
        game = self.make_game(script=[{"quit": 1}, {"cancel": 1}],
                              with_player=False)
        game.update()
        game.update()
        self.assertFalse(game.quit_dialog_active)


class QuitDialogDrawTest(QuitDialogTestBase):
    """弹窗绘制在所有内容之上。"""

    def test_dialog_is_drawn_over_the_scene(self):
        game = self.make_game(script=[{"quit": 1}])
        game.update()
        game.draw()
        # 标题画面底色是深蓝；弹窗区域必须被浅灰的对话框盖住
        self.assertEqual(pyxel.pget(180, 90), palette.LIGHT_GRAY)

    def test_draw_without_dialog_is_unchanged(self):
        game = self.make_game()
        game.draw()
        self.assertNotEqual(pyxel.pget(180, 90), palette.LIGHT_GRAY)


if __name__ == "__main__":
    unittest.main()
