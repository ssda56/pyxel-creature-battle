"""字体字形覆盖：确保游戏里用到的每一个汉字都能真的画出来。

背景：随项目分发的点阵字体不保证覆盖全部汉字。实测 Ark Pixel 简体版缺
"药/然/即/既/热/毁/紧/缘" 等 31 个常用字，缺字会渲染成空心方块（豆腐块）。
`text.draw` 里的逐字回退负责补上这些字。

本文件把那件事固化成回归测试，防止以后再换字体时静默退化。
"""

from __future__ import annotations

import glob
import os
import unittest

from tests import helpers

helpers.ensure_init()

import pyxel  # noqa: E402

from src.ui import text  # noqa: E402


def _project_chars() -> set[str]:
    """收集 src/ 下所有源文件里出现的非 ASCII 字符。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chars: set[str] = set()
    for path in glob.glob(os.path.join(root, "src", "**", "*.py"), recursive=True):
        with open(path, encoding="utf-8") as f:
            chars.update(ch for ch in f.read() if ord(ch) > 0x2000)
    return chars


def _render(ch: str, use_fallback: bool) -> tuple[int, ...]:
    font = text.init_font()
    pyxel.cls(0)
    if use_fallback:
        text.draw(0, 0, ch, 7)
    else:
        pyxel.text(0, 0, ch, 7, font)
    return tuple(pyxel.screen.pget(x, y) for y in range(14) for x in range(14))


class GlyphCoverageTest(unittest.TestCase):
    def test_notdef_bitmap_is_the_empty_box(self):
        """确认"缺字"长什么样：空框。后面的断言都以它为基准。"""
        codes = text.covered_codepoints()
        if codes is None:
            self.skipTest("主字体不是内置点阵字体，本用例不适用")
        uncovered = [ch for ch in "药然即既热" if ord(ch) not in codes]
        if not uncovered:
            self.skipTest("该字体已覆盖这些字，无需回退")
        box = _render(uncovered[0], use_fallback=False)
        for ch in uncovered:
            self.assertEqual(_render(ch, use_fallback=False), box,
                             f"{ch} 在主字体下应当是同一个缺字方框")

    def test_no_game_character_renders_as_a_box(self):
        """**核心回归测试**：游戏里用到的每一个字都不能渲染成方块。"""
        codes = text.covered_codepoints()
        if codes is None:
            self.skipTest("主字体不是内置点阵字体，本用例不适用")
        if text.fallback_font() is None:
            self.skipTest("系统里没有可用的回退字体，无法补齐缺字")
        chars = _project_chars()
        self.assertGreater(len(chars), 500, "应当扫到大量中文字符")
        uncovered = [ch for ch in chars if ord(ch) not in codes]
        box = _render("药", use_fallback=False) if (
            ord("药") not in codes) else None
        if box is None:
            self.skipTest("该字体覆盖了「药」，找不到方块样本")
        broken = [ch for ch in uncovered if _render(ch, use_fallback=True) == box]
        self.assertEqual(broken, [], f"这些字仍然渲染成方块：{''.join(broken)}")

    def test_fallback_does_not_change_width(self):
        """逐字回退不能改变字宽，否则折行和居中会全乱。"""
        for s in ["伤药", "好伤药", "蓝药水", "凤凰天翔", "雾尾狐"]:
            expected = sum(12 if ord(ch) > 0x2000 else 6 for ch in s)
            self.assertEqual(text.width(s), expected, f"{s} 宽度不对")

    def test_covered_characters_use_the_crisp_font(self):
        """有覆盖的字必须仍走主字体（不能用回退把它糊了）。"""
        codes = text.covered_codepoints()
        if codes is None:
            self.skipTest("主字体不是内置点阵字体，本用例不适用")
        for ch in "精灵对战商店伤蓝":
            if ord(ch) in codes:
                self.assertEqual(_render(ch, use_fallback=True),
                                 _render(ch, use_fallback=False),
                                 f"{ch} 有覆盖，不该走回退字体")


if __name__ == "__main__":
    unittest.main()
