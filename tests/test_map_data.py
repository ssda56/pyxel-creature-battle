"""地图数据测试（src/data/map_data.py）。

覆盖《数值设定.md》§10.1 / §10.2：
- 地图尺寸与声明一致、每行长度 == w；
- 每格图块 ID ∈ 0..9；
- 出生点可走、边界一圈不可走；
- map1 / map2 的 portal 互指有效（目标格存在且可走）；
- NPC 站立的格子可走，且从出生点能走到。
"""

from __future__ import annotations

import unittest
from collections import deque

from src.data import map_data


def reachable(m: dict, start: tuple[int, int]) -> set[tuple[int, int]]:
    """从 start 出发能走到的所有可走格。"""
    w, h = m["w"], m["h"]
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in seen:
                continue
            if 0 <= nx < w and 0 <= ny < h and m["tiles"][ny][nx] in map_data.WALKABLE_TILES:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


class MapSizeTest(unittest.TestCase):
    """尺寸与图块取值。"""

    def test_maps_exist(self):
        self.assertIn(1, map_data.MAPS)
        self.assertIn(2, map_data.MAPS)

    def test_declared_size_matches_tiles(self):
        for map_id, m in map_data.MAPS.items():
            self.assertEqual(len(m["tiles"]), m["h"], f"地图 {map_id} 行数与 h 不一致")
            for y, row in enumerate(m["tiles"]):
                self.assertEqual(len(row), m["w"], f"地图 {map_id} 第 {y} 行长度与 w 不一致")

    def test_documented_sizes(self):
        """《数值设定.md》§10.1：新手村 30x20、野外 40x30。"""
        self.assertEqual((map_data.MAPS[1]["w"], map_data.MAPS[1]["h"]), (30, 20))
        self.assertEqual((map_data.MAPS[2]["w"], map_data.MAPS[2]["h"]), (40, 30))

    def test_tile_ids_are_in_range(self):
        for map_id, m in map_data.MAPS.items():
            for y, row in enumerate(m["tiles"]):
                for x, value in enumerate(row):
                    self.assertTrue(0 <= value <= 9,
                                    f"地图 {map_id} ({x},{y}) 的图块 {value} 不在 0..9")

    def test_walkable_and_blocked_partition_tile_ids(self):
        self.assertEqual(map_data.WALKABLE_TILES, {0, 1, 4, 6, 8, 9})
        self.assertEqual(map_data.BLOCKED_TILES, {2, 3, 5, 7})
        self.assertEqual(map_data.WALKABLE_TILES & map_data.BLOCKED_TILES, set())
        self.assertEqual(map_data.WALKABLE_TILES | map_data.BLOCKED_TILES, set(range(10)))

    def test_map_names(self):
        self.assertEqual(map_data.MAPS[1]["name"], "新手村")
        self.assertEqual(map_data.MAPS[2]["name"], "野外")


class MapContentTest(unittest.TestCase):
    """出生点 / 边界 / 可达性。"""

    def test_spawn_is_walkable(self):
        for map_id, m in map_data.MAPS.items():
            sx, sy = m["spawn"]
            self.assertTrue(map_data.is_walkable(map_id, sx, sy),
                            f"地图 {map_id} 的出生点 ({sx},{sy}) 不可走")

    def test_border_is_blocked(self):
        for map_id, m in map_data.MAPS.items():
            w, h = m["w"], m["h"]
            for x in range(w):
                self.assertIn(m["tiles"][0][x], map_data.BLOCKED_TILES,
                              f"地图 {map_id} 上边界 ({x},0) 可走")
                self.assertIn(m["tiles"][h - 1][x], map_data.BLOCKED_TILES,
                              f"地图 {map_id} 下边界 ({x},{h - 1}) 可走")
            for y in range(h):
                self.assertIn(m["tiles"][y][0], map_data.BLOCKED_TILES,
                              f"地图 {map_id} 左边界 (0,{y}) 可走")
                self.assertIn(m["tiles"][y][w - 1], map_data.BLOCKED_TILES,
                              f"地图 {map_id} 右边界 ({w - 1},{y}) 可走")

    def test_npcs_stand_on_walkable_tiles(self):
        for map_id, m in map_data.MAPS.items():
            for npc in m["npcs"]:
                self.assertTrue(map_data.is_walkable(map_id, npc["x"], npc["y"]),
                                f"地图 {map_id} 的 NPC {npc['name']} 所在格不可走")
                self.assertTrue(npc["lines"], "NPC 必须有台词")
                for line in npc["lines"]:
                    self.assertTrue(line.strip(), "NPC 台词不能是空行")

    def test_npcs_and_portals_are_reachable_from_spawn(self):
        for map_id, m in map_data.MAPS.items():
            reach = reachable(m, m["spawn"])
            for npc in m["npcs"]:
                self.assertIn((npc["x"], npc["y"]), reach,
                              f"地图 {map_id} 的 NPC {npc['name']} 从出生点走不到")
            for portal in m["portals"]:
                self.assertIn((portal["x"], portal["y"]), reach,
                              f"地图 {map_id} 的出入口从出生点走不到")

    def test_village_has_house_door_road_and_npc(self):
        """新手村要有：房屋墙 5、门 6、道路 4、草地 0、树 2、花丛 9。"""
        flat = [v for row in map_data.MAPS[1]["tiles"] for v in row]
        for tile_id, label in ((0, "草地"), (2, "树"), (4, "道路"), (5, "墙"), (6, "门"), (9, "花")):
            self.assertIn(tile_id, flat, f"新手村缺少 {label}（{tile_id}）")

    def test_field_has_grass_tallgrass_water_tree_highland(self):
        """野外要有：草地 0、草丛 1、水 3、树 2、高地 8。"""
        flat = [v for row in map_data.MAPS[2]["tiles"] for v in row]
        for tile_id, label in ((0, "草地"), (1, "草丛"), (2, "树"), (3, "水"), (8, "高地")):
            self.assertIn(tile_id, flat, f"野外缺少 {label}（{tile_id}）")


class PortalTest(unittest.TestCase):
    """出入口互指。"""

    def test_portal_source_tile_is_walkable(self):
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                self.assertTrue(map_data.is_walkable(map_id, portal["x"], portal["y"]),
                                f"地图 {map_id} 的出入口格不可走")

    def test_portal_target_exists_and_is_walkable(self):
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                target = portal["to_map"]
                self.assertIn(target, map_data.MAPS)
                self.assertTrue(
                    map_data.is_walkable(target, portal["to_x"], portal["to_y"]),
                    f"地图 {map_id} 的出入口落点 ({target}, {portal['to_x']},"
                    f"{portal['to_y']}) 不可走")

    def test_village_and_field_lead_to_each_other(self):
        """map1 的出口 -> map2，map2 的入口 -> map1。"""
        p1 = map_data.MAPS[1]["portals"][0]
        self.assertEqual(p1["to_map"], 2)
        p2 = map_data.MAPS[2]["portals"][0]
        self.assertEqual(p2["to_map"], 1)
        # 落点分别落在对方地图的出入口旁边（双向可回）
        self.assertEqual(p1["to_x"], 2)
        self.assertEqual(p1["to_y"], 15)
        self.assertEqual(p2["to_x"], 27)
        self.assertEqual(p2["to_y"], 10)


class HelperTest(unittest.TestCase):
    """map_data 的查询 helper。"""

    def test_get_map_unknown_raises(self):
        with self.assertRaises(KeyError):
            map_data.get_map(99)

    def test_tile_at_out_of_range_returns_none(self):
        self.assertIsNone(map_data.tile_at(1, -1, 0))
        self.assertIsNone(map_data.tile_at(1, 0, -1))
        self.assertIsNone(map_data.tile_at(1, 30, 0))
        self.assertIsNone(map_data.tile_at(1, 0, 20))

    def test_map_pixel_size(self):
        self.assertEqual(map_data.map_pixel_size(1), (480, 320))
        self.assertEqual(map_data.map_pixel_size(2), (640, 480))

    def test_is_walkable_matches_tiles(self):
        for map_id, m in map_data.MAPS.items():
            for y in range(m["h"]):
                for x in range(m["w"]):
                    expected = m["tiles"][y][x] in map_data.WALKABLE_TILES
                    self.assertEqual(map_data.is_walkable(map_id, x, y), expected)


if __name__ == "__main__":
    unittest.main()
