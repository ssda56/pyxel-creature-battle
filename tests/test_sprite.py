"""assets_gen 烘焙器测试。"""

import unittest

from src.assets_gen import sprite_base
from src.assets_gen.sprite_base import Canvas, SpriteMatrix
from src.assets_gen.sprites import ALL_SPRITES, creatures, player, tileset
from tests import helpers


class BakeSizeTest(unittest.TestCase):
    """烘焙尺寸。"""

    def setUp(self):
        helpers.ensure_init()

    def test_tile_is_16x16(self):
        img = sprite_base.bake(tileset.TILE_0_GRASS)
        self.assertEqual((img.width, img.height), (16, 16))

    def test_player_is_16x16(self):
        img = sprite_base.bake(player.PLAYER_DOWN_0)
        self.assertEqual((img.width, img.height), (16, 16))

    def test_creature_battle_is_32x32(self):
        img = sprite_base.bake(creatures.CREATURE_BATTLE[1])
        self.assertEqual((img.width, img.height), (32, 32))

    def test_creature_icon_is_16x16(self):
        img = sprite_base.bake(creatures.CREATURE_ICON[1])
        self.assertEqual((img.width, img.height), (16, 16))

    def test_every_sprite_bakes_to_its_own_size(self):
        sprite_base.bake_all()
        for sprite in ALL_SPRITES:
            img = sprite_base.get(sprite.name)
            self.assertEqual((img.width, img.height), (sprite.width, sprite.height))

    def test_expected_sprite_names_exist(self):
        sprite_base.bake_all()
        names = set(sprite_base.REGISTRY)
        for i in range(10):
            self.assertIn(f"tile_{i}_", "".join(n for n in names if n.startswith(f"tile_{i}_")))
        for direction in ("down", "up", "left", "right"):
            for frame in (0, 1):
                self.assertIn(f"player_{direction}_{frame}", names)
        for sid in range(1, 9):
            self.assertIn(f"creature_{sid}_battle", names)
            self.assertIn(f"creature_{sid}_icon", names)


class ValidationTest(unittest.TestCase):
    """行宽一致性 / 透明点 / 幂等。"""

    def setUp(self):
        helpers.ensure_init()

    def test_row_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            SpriteMatrix("bad_sprite", ["..", "..."], {".": None}).bake()

    def test_error_message_contains_name_and_row_number(self):
        with self.assertRaises(sprite_base.SpriteRowLengthError) as ctx:
            SpriteMatrix("my_thing", ["..", "...", "...."], {".": None}).bake()
        message = str(ctx.exception)
        self.assertIn("my_thing", message)
        self.assertIn("2", message)

    def test_dot_is_not_written(self):
        img = sprite_base.bake(SpriteMatrix("dot_test", ["..", ".X"], {".": None, "X": 7}))
        self.assertEqual(img.pget(0, 0), 0)
        self.assertEqual(img.pget(1, 0), 0)
        self.assertEqual(img.pget(1, 1), 7)

    def test_bake_is_idempotent(self):
        first = sprite_base.bake(tileset.TILE_0_GRASS)
        second = sprite_base.bake(tileset.TILE_0_GRASS)
        self.assertIs(first, second)

    def test_get_unknown_name_raises(self):
        with self.assertRaises(KeyError):
            sprite_base.get("no_such_sprite_here")

    def test_unknown_char_raises(self):
        with self.assertRaises(KeyError):
            SpriteMatrix("bad_char", ["@"], {".": None}).bake()


class PaletteCompletenessTest(unittest.TestCase):
    """每个素材用到的字符都必须在它自己的 palette 里声明。"""

    def test_all_chars_are_declared(self):
        for sprite in ALL_SPRITES:
            used = set("".join(sprite.rows))
            missing = used - set(sprite.palette)
            self.assertFalse(missing, f"{sprite.name} 用了未声明的字符 {sorted(missing)}")

    def test_transparent_char_is_always_allowed(self):
        for sprite in ALL_SPRITES:
            self.assertIn(".", sprite.palette)


class CanvasTest(unittest.TestCase):
    """绘图辅助画布。"""

    def test_ellipse_fills_center(self):
        canvas = Canvas(8, 8)
        canvas.ellipse(4, 4, 2, 2, "X")
        self.assertEqual(canvas.grid[4][4], "X")
        self.assertEqual(canvas.grid[0][0], ".")

    def test_outline_wraps_shape(self):
        canvas = Canvas(5, 5)
        canvas.rect(1, 1, 3, 3, "X")
        canvas.outline("K")
        # 描边画在形状**外面**
        self.assertEqual(canvas.grid[0][1], "K")
        self.assertEqual(canvas.grid[1][0], "K")
        self.assertEqual(canvas.grid[1][1], "X")
        self.assertEqual(canvas.grid[2][2], "X")

    def test_rows_are_uniform_width(self):
        canvas = Canvas(6, 4)
        canvas.rect(0, 0, 6, 4, "X")
        rows = canvas.rows()
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(len(row), 6)


if __name__ == "__main__":
    unittest.main()
