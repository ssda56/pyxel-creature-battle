"""ui/text.py 的度量与折行测试。"""

import unittest

from src.ui import text


class TextWidthTest(unittest.TestCase):
    """字体度量（simhei 12px：全角 12px / 半角 6px）。"""

    def test_cjk_four_chars_is_48(self):
        self.assertEqual(text.width("精灵对战"), 48)

    def test_two_ascii_chars_is_12(self):
        self.assertEqual(text.width("AB"), 12)

    def test_single_ascii_char_is_6(self):
        self.assertEqual(text.width("A"), 6)

    def test_single_cjk_char_is_12(self):
        self.assertEqual(text.width("精"), 12)

    def test_mixed_string(self):
        self.assertEqual(text.width("精灵对战abc"), 48 + 18)

    def test_empty_string(self):
        self.assertEqual(text.width(""), 0)


class WrapTest(unittest.TestCase):
    """按像素宽度折行。"""

    def test_no_line_exceeds_max_width(self):
        lines = text.wrap("精灵对战精灵对战精灵对战ABCDEFG", 48)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(text.width(line), 48)

    def test_explicit_newline_is_kept(self):
        lines = text.wrap("第一行\n第二行", 48)
        self.assertEqual(lines, ["第一行", "第二行"])

    def test_char_wider_than_max_px_gets_own_line(self):
        lines = text.wrap("精", 6)
        self.assertEqual(lines, ["精"])

    def test_empty_line_is_preserved(self):
        self.assertEqual(text.wrap("a\n\nb", 48), ["a", "", "b"])

    def test_invalid_max_px_raises(self):
        with self.assertRaises(ValueError):
            text.wrap("abc", 0)


class FontSourceTest(unittest.TestCase):
    """字体来源必须是 Windows 中文字体，不能是素材目录里的日文字体。"""

    def test_font_path_is_not_japanese_asset(self):
        path = text.font_path()
        self.assertTrue(path.lower().endswith((".ttf", ".ttc")))
        self.assertNotIn("umplus", path.lower())
        self.assertNotIn("PixelMplus", path)

    def test_init_font_is_idempotent(self):
        self.assertIs(text.init_font(), text.init_font())


if __name__ == "__main__":
    unittest.main()
