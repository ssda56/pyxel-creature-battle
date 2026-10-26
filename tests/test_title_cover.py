"""标题封面美术（T17）的回归测试。

守四条最容易在后续改动里被破坏的东西：

1. **确定性**：整张封面烘焙两次必须逐像素一致（截图回归靠它）；
2. **色 0 不许出现在画面里**：色 0 是 blt(colkey=0) 的透明键，
   画上去会在贴图时变成窟窿；
3. **可导入的名字**：TITLE_TEXT / MENU_ITEMS 仍是原来的值，
   底部版本号（FOOTER_TEXT / FOOTER_Y）已按需求删除；
4. **行为不变**：标题场景能正常绘制、读档失败仍给三种提示文案。
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest

import pyxel

from src.core.game import Game
from src.core.input import FakeInput
from src.model import save_io
from src.scenes import title_scene
from src.ui import title_art
from tests import helpers


def _digest(img) -> str:
    """把一张图逐像素哈希（不依赖 Pillow）。"""
    h = hashlib.sha256()
    for y in range(img.height):
        h.update(bytes(img.pget(x, y) for x in range(img.width)))
    return h.hexdigest()


class CoverArtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helpers.ensure_init()

    def test_background_size(self):
        img = title_art.bake_background()
        self.assertEqual((img.width, img.height),
                         (title_art.SCREEN_W, title_art.SCREEN_H))

    def test_background_is_deterministic(self):
        """连烘焙两次必须完全一致（固定表 / 坐标哈希，不用 random / 时间）。"""
        first = _digest(title_art.bake_background())
        title_art._CACHE.clear()
        try:
            second = _digest(title_art.bake_background())
        finally:
            title_art._CACHE.clear()
            title_art.bake_background()          # 把缓存恢复回去
        self.assertEqual(first, second)

    def test_no_color_zero_anywhere(self):
        """色 0 是透明键，封面图里一个像素都不能有。"""
        img = title_art.bake_background()
        offenders = [
            (x, y)
            for y in range(img.height)
            for x in range(img.width)
            if img.pget(x, y) == 0
        ]
        self.assertEqual(offenders[:5], [], f"封面里出现了 {len(offenders)} 个色 0 像素")

    def test_title_sprite_has_outline_and_bevel(self):
        """标题小图要同时出现 面色 / 立体底边色 / 描边色 三种颜色。"""
        sprite = title_art.render_title("精灵对战")
        colors = {sprite.pget(x, y)
                  for y in range(sprite.height)
                  for x in range(sprite.width)}
        self.assertIn(palette_yellow(), colors)
        self.assertIn(palette_orange(), colors)
        self.assertIn(palette_dark_purple(), colors)

    def test_title_is_wider_than_plain_text(self):
        """2 倍放大的标题至少是原文字宽度的两倍（描边 + 放大）。"""
        from src.ui import text

        sprite = title_art.render_title("精灵对战")
        self.assertGreaterEqual(sprite.width, text.width("精灵对战") * title_art.TITLE_SCALE)


def palette_yellow() -> int:
    from src.assets_gen import palette
    return palette.YELLOW


def palette_orange() -> int:
    from src.assets_gen import palette
    return palette.ORANGE


def palette_dark_purple() -> int:
    from src.assets_gen import palette
    return palette.DARK_PURPLE


class TitleSceneShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helpers.ensure_init()

    def test_public_names_kept(self):
        self.assertEqual(title_scene.TITLE_TEXT, "精灵对战")
        self.assertEqual(title_scene.MENU_ITEMS, ("新游戏", "继续游戏"))
        self.assertEqual(title_scene.HINT_FRAMES, 120)

    def test_footer_version_text_removed(self):
        """底部版本号已按需求删除（连同绘制一起）。"""
        self.assertFalse(hasattr(title_scene, "FOOTER_TEXT"))
        self.assertFalse(hasattr(title_scene, "FOOTER_Y"))

    def test_draw_runs(self):
        game = Game(input=FakeInput())
        helpers.run_frames(game.update, game.draw, 3)

    def test_menu_still_inside_panel(self):
        """菜单文字与光标都要落在深色面板里（保证对比度）。"""
        for i in range(len(title_scene.MENU_ITEMS)):
            y = title_scene.MENU_Y + i * title_scene.MENU_STEP
            self.assertGreaterEqual(y, title_art.MENU_PANEL_Y0)
            self.assertLessEqual(y + 12, title_art.MENU_PANEL_Y1)
        self.assertGreaterEqual(title_scene.CURSOR_X, title_art.MENU_PANEL_X0)


class LoadErrorHintsTest(unittest.TestCase):
    """三种读档失败仍然都能给文案（行为零改动）。"""

    @classmethod
    def setUpClass(cls):
        helpers.ensure_init()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = save_io.SAVE_PATH

    def tearDown(self):
        save_io.SAVE_PATH = self._old
        self._tmp.cleanup()

    def _hint_for(self, filename: str, payload: str | None) -> str:
        path = os.path.join(self._tmp.name, filename)
        if payload is not None:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(payload)
        save_io.SAVE_PATH = path
        game = Game(input=FakeInput())
        scene = game.scenes.current
        scene.index = 1
        scene._continue_game()
        game.draw()
        return scene.hint

    def test_no_file(self):
        self.assertEqual(self._hint_for("missing.json", None), "没有找到存档")

    def test_bad_version(self):
        self.assertEqual(
            self._hint_for("badver.json", '{"version": 999}'),
            "存档版本不兼容",
        )

    def test_corrupt(self):
        self.assertEqual(self._hint_for("broken.json", "{ not json"),
                         "存档已损坏")


if __name__ == "__main__":
    unittest.main()
