"""传送阵图块测试（批 5 / T10 · 改动一）。

出口从「普通道路」改成「传送阵图标」：

- 图块 10（传送阵）与图块 11（洞窟地面）已经画进 tileset，尺寸 16x16；
- map1 的 (28,10) 与 map2 的 (1,15) 两个出入口格的图块值 == 10；
- 传送阵**必须可走**（不然玩家走不上去）；
- 图块本身没有透明像素、不使用索引 0（和其它图块一样的硬性约定）。
"""

from __future__ import annotations

import unittest

from src.assets_gen.sprites import tileset
from src.data import map_data


class PortalTileDataTest(unittest.TestCase):
    """数据层：出入口格 == 传送阵图块，且可走。"""

    def test_portal_cells_use_portal_tile(self):
        """两个出入口格的图块值都等于 10（不再是普通道路 4）。"""
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                self.assertEqual(
                    map_data.tile_at(map_id, portal["x"], portal["y"]), 10,
                    f"地图 {map_id} 的出入口 ({portal['x']},{portal['y']}) "
                    f"不是传送阵图块（10）")

    def test_portal_cells_are_walkable(self):
        """传送阵必须可走。"""
        self.assertIn(10, map_data.WALKABLE_TILES)
        self.assertNotIn(10, map_data.BLOCKED_TILES)
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                self.assertTrue(
                    map_data.is_walkable(map_id, portal["x"], portal["y"]),
                    f"地图 {map_id} 的出入口不可走")

    def test_known_portal_cells(self):
        """钉死两个出入口的坐标与图块（地图改了这里会红）。"""
        self.assertEqual(map_data.tile_at(1, 28, 10), 10)
        self.assertEqual(map_data.tile_at(2, 1, 15), 10)

    def test_old_road_tile_replaced(self):
        """出入口格不再是普通道路 4。"""
        self.assertNotEqual(map_data.tile_at(1, 28, 10), 4)
        self.assertNotEqual(map_data.tile_at(2, 1, 15), 4)


class PortalTileSpriteTest(unittest.TestCase):
    """素材层：tile_10_portal 的形状与颜色。"""

    def test_tile_10_exists(self):
        self.assertIn(10, tileset.TILES_BY_ID)
        sprite = tileset.TILES_BY_ID[10]
        self.assertEqual(sprite.name, "tile_10_portal")
        self.assertEqual((sprite.width, sprite.height), (16, 16))

    def test_tile_ids_are_contiguous(self):
        """图块 ID 0..11 必须连续（TILES_BY_ID 按 SPRITES 下标生成）。"""
        self.assertEqual(sorted(tileset.TILES_BY_ID), list(range(12)))

    def test_portal_has_no_transparent_pixels(self):
        """图块满铺不透明：不能有 '.'（透明）像素。"""
        sprite = tileset.TILES_BY_ID[10]
        for row in sprite.rows:
            self.assertNotIn(".", row, "传送阵图块不能有透明像素")

    def test_portal_uses_bright_colors(self):
        """传送阵要用亮色（黄 / 白 / 浅蓝）+ 深蓝描边，一眼能认出来。"""
        sprite = tileset.TILES_BY_ID[10]
        used = set("".join(sprite.rows))
        for ch, label in (("Y", "黄色"), ("W", "白色"), ("B", "浅蓝"), ("c", "深蓝描边")):
            self.assertIn(ch, used, f"传送阵图块缺少{label}")

    def test_portal_has_corner_runes(self):
        """四角要有符纹：玩家站在图块上时，主角轮廓之外的像素还看得见。"""
        sprite = tileset.TILES_BY_ID[10]
        rows = sprite.rows
        for x, y, label in ((0, 0, "左上"), (15, 0, "右上"),
                            (0, 15, "左下"), (15, 15, "右下")):
            self.assertIn(rows[y][x], ("Y", "W"),
                          f"传送阵的{label}角没有符纹")

    def test_portal_is_not_a_solid_block(self):
        """不能画成障碍：法阵中心是亮色（可走的地面，不是实心墙）。"""
        sprite = tileset.TILES_BY_ID[10]
        center = sprite.rows[7][7] + sprite.rows[8][8]
        self.assertIn(center[0], ("Y", "W"), "传送阵中心应当是亮色光点")
        self.assertIn(center[1], ("Y", "W"), "传送阵中心应当是亮色光点")


if __name__ == "__main__":
    unittest.main()
