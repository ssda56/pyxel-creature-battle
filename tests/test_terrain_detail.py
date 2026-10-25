"""地形细节测试（A6 · 图块变体碎屑 + 边缘自动拼接）。

覆盖四件事：

1. 变体选择是纯函数：同一格坐标永远同一结果，不会每帧抖动；
2. 边缘拼接只看四邻接、只看白名单里的邻格，不碰障碍（否则会变成棋盘框）；
3. 生成的变体 / 过渡图块仍然满足图块硬约定：满铺不透明、不用索引 0；
4. 可通行性与地图数据完全没被这次改动影响。
"""

from __future__ import annotations

import unittest

from src.data import map_data
from src.ui import terrain


def make_tile_at(tiles, w, h):
    """按二维 tiles 造一个邻格查询函数（越界返回 None）。"""

    def tile_at(gx, gy):
        if gx < 0 or gy < 0 or gx >= w or gy >= h:
            return None
        return tiles[gy][gx]

    return tile_at


class VariantHashTest(unittest.TestCase):
    """变体碎屑按坐标哈希选择。"""

    def test_same_cell_always_same_variant(self):
        """同一格两次调用必须一样（否则地图会每帧闪）。"""
        for gx, gy in ((0, 0), (7, 13), (39, 29), (123, 456)):
            first = terrain.variant_index(gx, gy, 0, 4)
            for _ in range(5):
                self.assertEqual(terrain.variant_index(gx, gy, 0, 4), first)

    def test_variant_is_in_range(self):
        for gx in range(50):
            for gy in range(50):
                v = terrain.variant_index(gx, gy, 0, 4)
                self.assertGreaterEqual(v, 0)
                self.assertLess(v, 4)

    def test_single_variant_always_zero(self):
        self.assertEqual(terrain.variant_index(3, 9, 0, 1), 0)
        self.assertEqual(terrain.variant_index(3, 9, 0, 0), 0)

    def test_all_variants_get_used(self):
        """四个变体都要用上，否则等于没做。"""
        seen = {terrain.variant_index(x, y, 0, 4) for x in range(60) for y in range(60)}
        self.assertEqual(seen, {0, 1, 2, 3})

    def test_variants_are_balanced(self):
        """分布要均匀，不能某一种变体占绝大多数（那样就成了补丁）。"""
        counts = [0, 0, 0, 0]
        total = 0
        for x in range(60):
            for y in range(60):
                counts[terrain.variant_index(x, y, 0, 4)] += 1
                total += 1
        for c in counts:
            self.assertLess(abs(c / total - 0.25), 0.06, f"变体分布不均：{counts}")

    def test_neighbouring_cells_differ(self):
        """相邻两格不应总是同一个变体（否则看不出碎屑）。"""
        same = 0
        for x in range(40):
            for y in range(40):
                if terrain.variant_index(x, y, 0, 4) == terrain.variant_index(x + 1, y, 0, 4):
                    same += 1
        self.assertLess(same / (40 * 40), 0.4, "相邻格变体太容易撞在一起")

    def test_ground_tiles_have_variants(self):
        """草地 / 道路 / 洞窟地面 / 岩壁 都要有 3~4 个变体。"""
        for tile_id in (0, 4, 11, 7):
            self.assertGreaterEqual(terrain.variant_count(tile_id), 3, tile_id)
            self.assertLessEqual(terrain.variant_count(tile_id), 4, tile_id)

    def test_obstacles_without_variants(self):
        """树 / 砖墙 不做碎屑（它们本身就是"一个明确的物件"，错位会散架）。

        水是例外：它是**成片**的地形，浪花 16 像素一循环在大片水面上很扎眼，
        所以水也有变体（只错位 + 极少量浪花，不改变"水"的辨识度）。
        """
        for tile_id in (2, 5):
            self.assertEqual(terrain.variant_count(tile_id), 1)
        self.assertGreater(terrain.variant_count(3), 1)

    def test_solid_obstacles_keep_their_shape(self):
        """树 / 砖墙 的图块必须是唯一的，保证障碍剪影不被切碎。"""
        from src.assets_gen.sprites import tileset
        for tile_id in (2, 5):
            self.assertNotIn(tile_id, tileset.TILE_VARIANTS)


class EdgeSignatureTest(unittest.TestCase):
    """边缘自动拼接：四邻接 + 白名单。"""

    def test_island_grass_has_no_edge(self):
        """四周全是草地 -> 不画过渡。"""
        tiles = [[0] * 5 for _ in range(5)]
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(0, 2, 2, at), 0)

    def test_single_side_edge(self):
        """只有上方是水 -> 上边形态。"""
        tiles = [[0] * 5 for _ in range(5)]
        tiles[1][2] = 3
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(0, 2, 2, at), terrain.EDGE_TOP)

    def test_four_sides_are_mapped(self):
        """四个方向分别落到四个不同的形态上。"""
        cases = (
            ((0, -1), terrain.EDGE_TOP),
            ((1, 0), terrain.EDGE_RIGHT),
            ((0, 1), terrain.EDGE_BOTTOM),
            ((-1, 0), terrain.EDGE_LEFT),
        )
        for (dx, dy), shape in cases:
            tiles = [[0] * 5 for _ in range(5)]
            tiles[2 + dy][2 + dx] = 3
            at = make_tile_at(tiles, 5, 5)
            self.assertEqual(terrain.edge_signature(0, 2, 2, at), shape, (dx, dy))

    def test_corner_shapes(self):
        """两侧相邻缺边 -> 角形态。"""
        cases = (
            ((0, -1), (-1, 0), terrain.EDGE_TOP_LEFT),
            ((0, -1), (1, 0), terrain.EDGE_TOP_RIGHT),
            ((0, 1), (-1, 0), terrain.EDGE_BOTTOM_LEFT),
            ((0, 1), (1, 0), terrain.EDGE_BOTTOM_RIGHT),
        )
        for (a, b, expected) in cases:
            tiles = [[0] * 5 for _ in range(5)]
            tiles[2 + a[1]][2 + a[0]] = 3
            tiles[2 + b[1]][2 + b[0]] = 3
            at = make_tile_at(tiles, 5, 5)
            self.assertEqual(terrain.edge_signature(0, 2, 2, at), expected)

    def test_relative_sides_make_ring(self):
        """上下都缺（一格宽窄道）-> 一圈形态，不能抛 KeyError。"""
        tiles = [[0] * 5 for _ in range(5)]
        tiles[1][2] = 3
        tiles[3][2] = 3
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(0, 2, 2, at), terrain.EDGE_RING)

    def test_three_or_more_sides_make_ring(self):
        tiles = [[0] * 5 for _ in range(5)]
        for (dx, dy) in ((0, -1), (1, 0), (0, 1)):
            tiles[2 + dy][2 + dx] = 3
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(0, 2, 2, at), terrain.EDGE_RING)

    def test_out_of_bounds_neighbour_is_ignored(self):
        """地图边界外不算过渡（否则整张地图四周会多出一圈框）。"""
        tiles = [[0] * 5 for _ in range(5)]
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(0, 0, 0, at), 0)
        self.assertEqual(terrain.edge_signature(0, 4, 4, at), 0)

    def test_obstacles_do_not_trigger_edges(self):
        """障碍（树 / 砖墙 / 岩壁）不该给草地加边，否则每格都像加了框。"""
        for blocker in (2, 5, 7):
            tiles = [[0] * 5 for _ in range(5)]
            tiles[1][2] = blocker
            at = make_tile_at(tiles, 5, 5)
            self.assertEqual(terrain.edge_signature(0, 2, 2, at), 0,
                             f"图块 {blocker} 不该触发草地边缘")

    def test_same_family_does_not_trigger(self):
        """草地挨着花丛 / 草丛仍然是草地，不该出现过渡边。"""
        for kin in (1, 9):
            tiles = [[0] * 5 for _ in range(5)]
            tiles[1][2] = kin
            at = make_tile_at(tiles, 5, 5)
            self.assertEqual(terrain.edge_signature(0, 2, 2, at), 0)

    def test_road_edge_against_grass(self):
        """道路与草地交界：由道路一侧画边。"""
        tiles = [[4] * 5 for _ in range(5)]
        tiles[2][3] = 0
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(4, 2, 2, at), terrain.EDGE_RIGHT)
        # 草地这一侧**不画**：两侧都画会让中间出现两倍宽的深色线，
        # 统一由「后铺上去的地形」（道路）负责画边。
        self.assertEqual(terrain.edge_signature(0, 3, 2, at), 0)

    def test_cave_floor_edge_against_rock(self):
        """洞窟地面与岩壁交界要画边（岩壁是障碍，但这里是有意画过渡）。"""
        tiles = [[11] * 5 for _ in range(5)]
        tiles[1][2] = 7
        at = make_tile_at(tiles, 5, 5)
        self.assertEqual(terrain.edge_signature(11, 2, 2, at), terrain.EDGE_TOP)

    def test_non_ground_tiles_never_get_edges(self):
        """树 / 水 / 砖墙 / 传送阵自己不做边缘过渡。"""
        tiles = [[0] * 5 for _ in range(5)]
        at = make_tile_at(tiles, 5, 5)
        for tile_id in (2, 3, 5, 10):
            self.assertEqual(terrain.edge_signature(tile_id, 2, 2, at), 0)

    def test_edge_shapes_count(self):
        self.assertEqual(terrain.EDGE_SHAPES, 10)

    def test_shape_names_are_unique(self):
        names = [terrain.edge_kind_name(i) for i in range(terrain.EDGE_SHAPES)]
        self.assertEqual(len(set(names)), terrain.EDGE_SHAPES)


class BlitRectTest(unittest.TestCase):
    """绘制裁剪（纯数学）。"""

    def test_fully_visible(self):
        self.assertEqual(terrain.blit_rect(10, 20, 16, 240, 216), (10, 20, 16, 16))

    def test_off_screen_left_top(self):
        self.assertEqual(terrain.blit_rect(-5, -3, 16, 240, 216), (0, 0, 11, 13))

    def test_off_screen_right_bottom(self):
        self.assertEqual(terrain.blit_rect(230, 210, 16, 240, 216), (230, 210, 10, 6))

    def test_completely_outside(self):
        self.assertIsNone(terrain.blit_rect(-16, 0, 16, 240, 216))
        self.assertIsNone(terrain.blit_rect(0, 216, 16, 240, 216))

    def test_source_skips_clipped_top_left(self):
        """格子跑到屏幕左上外面时，源矩形要跳过被裁掉的那部分。

        否则会把图块的上 / 左边界重复画一遍（旧实现就漏了这一步）。
        """
        sx, sy, sw, sh = terrain.blit_source(-5, -3, 16)
        self.assertEqual((sx, sy), (5, 3))
        self.assertEqual((sw, sh), (11, 13))
        # 右下被裁时源矩形不变，只裁目标矩形
        self.assertEqual(terrain.blit_source(230, 210, 16), (0, 0, 16, 16))

    def test_source_size_never_exceeds_tile(self):
        for (dx, dy) in ((-15, -15), (-1, 0), (0, 0), (15, 15)):
            sx, sy, sw, sh = terrain.blit_source(dx, dy, 16)
            self.assertGreaterEqual(sx, 0)
            self.assertGreaterEqual(sy, 0)
            self.assertLessEqual(sx + sw, 16)
            self.assertLessEqual(sy + sh, 16)


class TerrainSpriteTest(unittest.TestCase):
    """生成的变体 / 过渡图块仍然满足图块硬约定。"""

    def setUp(self):
        from tests import helpers
        helpers.ensure_init()
        from src.assets_gen.sprites import tileset
        self.tileset = tileset

    def test_tile_ids_still_contiguous(self):
        """变体不能挤进 TILES_BY_ID：它必须还是 0..11。"""
        self.assertEqual(sorted(self.tileset.TILES_BY_ID), list(range(12)))

    def test_variant_zero_is_the_original(self):
        for tile_id, bucket in self.tileset.TILE_VARIANTS.items():
            self.assertIs(bucket[0], self.tileset.TILES_BY_ID[tile_id])

    def test_generated_sprites_are_opaque(self):
        """变体 / 过渡图块必须满铺不透明（没有点号像素）。"""
        for sprite in self.tileset.TERRAIN_SPRITES:
            self.assertNotIn(".", "".join(sprite.rows), sprite.name)

    def test_generated_sprites_avoid_color_zero(self):
        """色 0 是 blt 的透明键，绝不能出现在画面里。"""
        for sprite in self.tileset.TERRAIN_SPRITES:
            self.assertNotIn(0, sprite.palette.values(), sprite.name)
            for row in sprite.rows:
                for ch in row:
                    self.assertNotEqual(sprite.palette[ch], 0,
                                        "%s 用了色 0" % sprite.name)

    def test_generated_sprites_are_16x16(self):
        for sprite in self.tileset.TERRAIN_SPRITES:
            self.assertEqual((sprite.width, sprite.height), (16, 16), sprite.name)

    def test_variant_names_are_unique(self):
        names = [s.name for s in self.tileset.TERRAIN_SPRITES]
        self.assertEqual(len(names), len(set(names)), "变体图块重名")

    def test_terrain_image_falls_back_to_base(self):
        """没有变体的图块也能取到图（回退到原图块）。"""
        from src.assets_gen import sprite_base
        img = self.tileset.terrain_image(2, 0, 0)
        self.assertIs(img, sprite_base.bake(self.tileset.TILES_BY_ID[2]))

    def test_bake_is_idempotent_for_variants(self):
        first = self.tileset.terrain_image(0, 1, 0)
        second = self.tileset.terrain_image(0, 1, 0)
        self.assertIs(first, second)


class WalkabilityUntouchedTest(unittest.TestCase):
    """A6 只是画面改动，可通行性与地图数据必须一点没变。"""

    def test_walkable_and_blocked_unchanged(self):
        self.assertEqual(map_data.WALKABLE_TILES, {0, 1, 4, 6, 8, 9, 10, 11})
        self.assertEqual(map_data.BLOCKED_TILES, {2, 3, 5, 7})

    def test_map_dimensions_unchanged(self):
        expected = {1: (30, 20), 2: (40, 30), 3: (36, 28)}
        for map_id, (w, h) in expected.items():
            m = map_data.MAPS[map_id]
            self.assertEqual((m["w"], m["h"]), (w, h))

    def test_portals_still_walkable(self):
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                self.assertTrue(
                    map_data.is_walkable(map_id, portal["x"], portal["y"]))

    def test_tile_rows_still_rectangular(self):
        for map_id, m in map_data.MAPS.items():
            for y, row in enumerate(m["tiles"]):
                self.assertEqual(len(row), m["w"],
                                 "地图 %d 第 %d 行长度不对" % (map_id, y))


if __name__ == "__main__":
    unittest.main()
