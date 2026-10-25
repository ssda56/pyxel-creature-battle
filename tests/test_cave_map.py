"""第三张地图「洞窟」测试（批 6 / T8a）。

覆盖《数值设定.md》§10.1 / §10.2 / §10.4 区域 3：

- map3 尺寸 36 x 28、每行长度 == w、边界整圈不可走；
- **BFS：从入口出生点能走到所有可走格**（含两个 portal 与全部刷怪点）；
- 两个新 portal（野外东南高地 <-> 洞窟入口洞室）互指有效；
- 遇敌表 5 条与 §10.4 逐项相等、权重和 = 100；
- **普通刷怪点刷不出不死鸟；深处刷怪点只会刷不死鸟**；
- map3 连跑 3000 帧：存活数 <= 4、坐标始终可走、无重叠。
"""

from __future__ import annotations

import random
import unittest
from collections import deque

from src.data import map_data
from src.scenes.field_scene import FieldScene

#: 洞窟地图 ID
CAVE_MAP = 3

#: 野外地图 ID
FIELD_MAP = 2

#: 洞窟地面图块 ID
CAVE_FLOOR = 11

#: 洞窟岩壁图块 ID
ROCK = 7

#: 视口宽度（格）：240 / 16
VIEW_TILES = 15


def reachable(m: dict, start) -> set:
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


class CaveShapeTest(unittest.TestCase):
    """洞窟地图的尺寸与地形。"""

    def test_cave_map_exists(self):
        self.assertIn(CAVE_MAP, map_data.MAPS)
        m = map_data.MAPS[CAVE_MAP]
        self.assertEqual(m["name"], "洞窟")
        self.assertEqual((m["w"], m["h"]), (36, 28))

    def test_cave_row_widths(self):
        m = map_data.MAPS[CAVE_MAP]
        self.assertEqual(len(m["tiles"]), 28)
        for y, row in enumerate(m["tiles"]):
            self.assertEqual(len(row), 36, "第 %d 行长度不对" % y)

    def test_cave_border_is_rock(self):
        """边界整圈都是岩壁（不可走）。"""
        m = map_data.MAPS[CAVE_MAP]
        w, h = m["w"], m["h"]
        for x in range(w):
            self.assertEqual(m["tiles"][0][x], ROCK, "上边界 (%d,0)" % x)
            self.assertEqual(m["tiles"][h - 1][x], ROCK, "下边界 (%d,%d)" % (x, h - 1))
        for y in range(h):
            self.assertEqual(m["tiles"][y][0], ROCK, "左边界 (0,%d)" % y)
            self.assertEqual(m["tiles"][y][w - 1], ROCK, "右边界 (%d,%d)" % (w - 1, y))

    def test_cave_uses_rock_and_cave_floor(self):
        """洞窟只由岩壁 7 + 洞窟地面 11 + 传送阵 10 组成。"""
        flat = [v for row in map_data.MAPS[CAVE_MAP]["tiles"] for v in row]
        self.assertIn(ROCK, flat)
        self.assertIn(CAVE_FLOOR, flat)
        self.assertIn(10, flat)
        self.assertEqual(set(flat) - {ROCK, CAVE_FLOOR, 10}, set(),
                         "洞窟里不该出现其它图块")

    def test_cave_is_not_an_open_field(self):
        """洞窟必须像洞穴：可走面积不到全图的一半，且要有窄走廊。"""
        m = map_data.MAPS[CAVE_MAP]
        floor = [1 for row in m["tiles"] for v in row if v in (CAVE_FLOOR, 10)]
        self.assertLess(len(floor), m["w"] * m["h"] // 2,
                        "洞窟不该是一大片空旷地")
        narrow_rows = 0
        for row in m["tiles"]:
            runs = []
            cur = 0
            for v in row:
                if v in (CAVE_FLOOR, 10):
                    cur += 1
                else:
                    if cur:
                        runs.append(cur)
                    cur = 0
            if cur:
                runs.append(cur)
            if runs and max(runs) <= 8:
                narrow_rows += 1
        self.assertGreaterEqual(narrow_rows, 8,
                                "洞窟应当有多条窄走廊（通道感）")

    def test_cave_floor_tile_is_walkable(self):
        """图块 11 是可走图块。"""
        self.assertIn(CAVE_FLOOR, map_data.WALKABLE_TILES)
        self.assertNotIn(CAVE_FLOOR, map_data.BLOCKED_TILES)


class CaveReachabilityTest(unittest.TestCase):
    """可达性：从入口出生点能走到每一个可走格。"""

    def setUp(self):
        self.m = map_data.MAPS[CAVE_MAP]
        self.reach = reachable(self.m, self.m["spawn"])

    def test_all_walkable_cells_reachable(self):
        """BFS：所有可走格都能从出生点走到（没有孤立区域）。"""
        walkable = {(x, y) for y in range(self.m["h"])
                    for x in range(self.m["w"])
                    if self.m["tiles"][y][x] in map_data.WALKABLE_TILES}
        self.assertTrue(walkable)
        missing = sorted(walkable - self.reach)
        self.assertEqual(missing, [], "这些可走格从出生点走不到")

    def test_spawn_points_reachable(self):
        for x, y in map_data.spawn_points_of(CAVE_MAP):
            self.assertIn((x, y), self.reach,
                          "刷怪点 (%d,%d) 从出生点走不到" % (x, y))

    def test_portals_reachable(self):
        for portal in self.m["portals"]:
            self.assertIn((portal["x"], portal["y"]), self.reach,
                          "出入口从出生点走不到")

    def test_spawn_is_walkable(self):
        sx, sy = self.m["spawn"]
        self.assertTrue(map_data.is_walkable(CAVE_MAP, sx, sy))


class CavePortalTest(unittest.TestCase):
    """野外东南高地 <-> 洞窟入口洞室 的双向传送。"""

    def test_field_portal_is_on_the_highland_far_end(self):
        """野外的洞窟入口在高地范围内（东南角）。"""
        portal = [p for p in map_data.MAPS[FIELD_MAP]["portals"]
                  if p["to_map"] == CAVE_MAP]
        self.assertEqual(len(portal), 1, "野外应当只有一个通往洞窟的出入口")
        p = portal[0]
        m = map_data.MAPS[FIELD_MAP]
        highland = {(x, y) for y in range(m["h"]) for x in range(m["w"])
                    if m["tiles"][y][x] == 8}
        # 高地共 51 格，传送阵占掉其中一格 -> 还剩 50 格
        self.assertEqual(len(highland), 50)
        xs = [x for x, _ in highland]
        ys = [y for _, y in highland]
        self.assertEqual((min(xs), max(xs)), (21, 32))
        self.assertEqual((min(ys), max(ys)), (23, 27))
        # 传送阵格落在高地范围内，且四面至少两面还是高地
        self.assertTrue(21 <= p["x"] <= 32 and 23 <= p["y"] <= 27,
                        "入口格必须落在高地范围内")
        around = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                     if (p["x"] + dx, p["y"] + dy) in highland)
        self.assertGreaterEqual(around, 2,
                                "入口格应当嵌在高地里（四面至少两面是高地）")
        # 且在高地的东端（远端），不是高地中间的某一格
        self.assertGreaterEqual(p["x"], max(xs) - 1,
                                "入口要在高地的东端（远端）")

    def test_field_portal_reachable_from_field_spawn(self):
        """野外那个传送阵从野外出生点走得到。"""
        m = map_data.MAPS[FIELD_MAP]
        reach = reachable(m, m["spawn"])
        p = [q for q in m["portals"] if q["to_map"] == CAVE_MAP][0]
        self.assertIn((p["x"], p["y"]), reach,
                      "野外的洞窟入口从出生点走不到")

    def test_field_portal_uses_portal_tile_and_is_walkable(self):
        p = [p for p in map_data.MAPS[FIELD_MAP]["portals"]
             if p["to_map"] == CAVE_MAP][0]
        self.assertEqual(map_data.tile_at(FIELD_MAP, p["x"], p["y"]), 10)
        self.assertTrue(map_data.is_walkable(FIELD_MAP, p["x"], p["y"]))

    def test_cave_portal_points_back_to_the_field_highland(self):
        """洞窟入口洞室的传送阵指回野外的高地入口格旁边。"""
        portals = map_data.MAPS[CAVE_MAP]["portals"]
        self.assertEqual(len(portals), 1)
        p = portals[0]
        self.assertEqual(p["to_map"], FIELD_MAP)
        self.assertEqual(map_data.tile_at(CAVE_MAP, p["x"], p["y"]), 10,
                         "洞窟入口必须也是传送阵图块（10）")
        self.assertTrue(map_data.is_walkable(CAVE_MAP, p["x"], p["y"]))
        self.assertTrue(map_data.is_walkable(FIELD_MAP, p["to_x"], p["to_y"]),
                        "落点必须在野外可走")
        field_portal = [q for q in map_data.MAPS[FIELD_MAP]["portals"]
                        if q["to_map"] == CAVE_MAP][0]
        self.assertNotEqual((p["to_x"], p["to_y"]),
                            (field_portal["x"], field_portal["y"]),
                            "落点不能是野外那个传送阵本身（否则立刻弹回去）")

    def test_portal_targets_exist(self):
        for map_id, m in map_data.MAPS.items():
            for portal in m["portals"]:
                self.assertIn(portal["to_map"], map_data.MAPS)
                self.assertTrue(
                    map_data.is_walkable(portal["to_map"],
                                         portal["to_x"], portal["to_y"]),
                    "地图 %d 的出入口落点不可走" % map_id)

    def test_cave_portal_cell_is_in_the_entrance_chamber(self):
        """洞窟的传送阵格必须在入口洞室里（离出生点很近）。"""
        p = map_data.MAPS[CAVE_MAP]["portals"][0]
        sx, sy = map_data.MAPS[CAVE_MAP]["spawn"]
        self.assertLessEqual(abs(p["x"] - sx) + abs(p["y"] - sy), 4,
                             "传送阵应当就在入口洞室里")


class CaveEncounterTableTest(unittest.TestCase):
    """遇敌表（《数值设定.md》§10.4 区域 3）。"""

    def test_table_matches_document(self):
        """洞窟遇敌表（《02-新增10只精灵规划.md》§8.2）：
        三头犬 8~12/20、独角兽 9~13/18、小狮鹫 7~10/12、闪电小子 8~11/12、
        不死鸟 15~18/5、灯火鳅 8~12/8、荆星芽 10~14/8、夜幕翼 9~13/8、
        绒医团 9~12/5、雷云团 12~16/4。"""
        enc = map_data.encounters_of(CAVE_MAP)
        self.assertIsNotNone(enc)
        got = {int(r["species_id"]): (int(r["level_min"]), int(r["level_max"]),
                                      int(r["weight"]))
               for r in enc["table"]}
        expected = {
            6: (8, 12, 20),    # 三头犬
            5: (9, 13, 18),    # 独角兽
            4: (7, 10, 12),    # 小狮鹫
            8: (8, 11, 12),    # 闪电小子
            7: (15, 18, 5),    # 不死鸟
            11: (8, 12, 8),    # 灯火鳅
            13: (10, 14, 8),   # 荆星芽
            15: (9, 13, 8),    # 夜幕翼
            16: (9, 12, 5),    # 绒医团
            18: (12, 16, 4),   # 雷云团
        }
        self.assertEqual(got, expected)
        self.assertEqual(len(enc["table"]), 10, "遇敌表应当正好 10 条")

    def test_weights_sum_to_100(self):
        enc = map_data.encounters_of(CAVE_MAP)
        total = sum(int(row["weight"]) for row in enc["table"])
        self.assertEqual(total, 100, "洞窟遇敌表权重之和必须是 100")

    def test_encounter_parameters_match_document(self):
        """§10.3：上限 4、重生冷却 360 帧、游走间隔 80~140 帧。"""
        enc = map_data.encounters_of(CAVE_MAP)
        self.assertEqual(enc["max_alive"], 4)
        self.assertEqual(enc["respawn_frames"], 360)
        self.assertEqual(enc["move_min"], 80)
        self.assertEqual(enc["move_max"], 140)

    def test_spawn_points_on_cave_floor(self):
        """刷怪点全部落在洞窟地面（11）上、互不重叠、至少 8 个。"""
        points = map_data.spawn_points_of(CAVE_MAP)
        self.assertGreaterEqual(len(points), 8)
        self.assertEqual(len(set(points)), len(points), "刷怪点不能重叠")
        for x, y in points:
            self.assertEqual(map_data.tile_at(CAVE_MAP, x, y), CAVE_FLOOR,
                             "刷怪点 (%d,%d) 不在洞窟地面上" % (x, y))
            self.assertTrue(map_data.is_walkable(CAVE_MAP, x, y))

    def test_deep_spawn_points_configured(self):
        """深处区刷怪点与深处专属种族都配好了。"""
        deep = map_data.deep_spawn_points_of(CAVE_MAP)
        self.assertTrue(deep, "洞窟必须配置深处区刷怪点")
        self.assertEqual(map_data.deep_species_of(CAVE_MAP), [7],
                         "洞窟的深处专属种族应当只有不死鸟（7）")
        points = set(map_data.spawn_points_of(CAVE_MAP))
        for p in deep:
            self.assertIn(p, points, "深处点必须也在刷怪点列表里")
            self.assertEqual(map_data.tile_at(CAVE_MAP, p[0], p[1]), CAVE_FLOOR)

    def test_deep_points_are_in_the_deepest_chamber(self):
        """深处刷怪点必须在最深处洞室（东北角），普通点不在那里。"""
        deep = set(map_data.deep_spawn_points_of(CAVE_MAP))
        normal = set(map_data.spawn_points_of(CAVE_MAP)) - deep
        for x, y in deep:
            self.assertGreaterEqual(x, 28, "深处刷怪点应在最深处洞室里")
            self.assertLessEqual(y, 6)
        for x, y in normal:
            self.assertFalse(x >= 28 and y <= 6,
                             "普通刷怪点 (%d,%d) 不该落在最深处洞室" % (x, y))

    def test_deep_chamber_is_hidden_from_the_entrance(self):
        """最深处不能一眼看到：与入口的距离超过一个视口。"""
        m = map_data.MAPS[CAVE_MAP]
        sx, sy = m["spawn"]
        for x, y in map_data.deep_spawn_points_of(CAVE_MAP):
            self.assertGreater(max(abs(x - sx), abs(y - sy)), VIEW_TILES,
                               "最深处离入口太近，入口一眼就能看到")

    def test_normal_points_never_roll_phoenix(self):
        """普通刷怪点刷不出不死鸟。"""
        deep = set(map_data.deep_spawn_points_of(CAVE_MAP))
        normal = [p for p in map_data.spawn_points_of(CAVE_MAP) if p not in deep]
        self.assertTrue(normal)
        rng = random.Random(20240607)
        for x, y in normal:
            for _ in range(60):
                rolled = map_data.roll_wild(CAVE_MAP, rng, (x, y))
                self.assertIsNotNone(rolled)
                self.assertNotEqual(rolled[0], 7,
                                    "普通刷怪点 (%d,%d) 刷出了不死鸟" % (x, y))

    def test_deep_points_only_roll_phoenix(self):
        """深处刷怪点只会刷不死鸟。"""
        rng = random.Random(99001)
        for x, y in map_data.deep_spawn_points_of(CAVE_MAP):
            for _ in range(60):
                rolled = map_data.roll_wild(CAVE_MAP, rng, (x, y))
                self.assertIsNotNone(rolled)
                self.assertEqual(rolled[0], 7,
                                 "深处刷怪点 (%d,%d) 刷出了别的种族" % (x, y))
                self.assertGreaterEqual(rolled[1], 15)
                self.assertLessEqual(rolled[1], 18)

    def test_roll_wild_without_point_never_rolls_phoenix(self):
        """不指定点位时（普通区语义）也不会刷出不死鸟。"""
        rng = random.Random(5150)
        for _ in range(300):
            rolled = map_data.roll_wild(CAVE_MAP, rng)
            self.assertIsNotNone(rolled)
            self.assertNotEqual(rolled[0], 7)

    def test_roll_wild_respects_level_ranges(self):
        enc = map_data.encounters_of(CAVE_MAP)
        ranges = {int(r["species_id"]): (int(r["level_min"]), int(r["level_max"]))
                  for r in enc["table"]}
        rng = random.Random(31415)
        seen = set()
        for _ in range(500):
            species_id, level = map_data.roll_wild(CAVE_MAP, rng, (4, 25))
            lo, hi = ranges[species_id]
            self.assertGreaterEqual(level, lo)
            self.assertLessEqual(level, hi)
            seen.add(species_id)
        self.assertGreaterEqual(len(seen), 2, "普通区应当能刷出多种种族")


class CaveSceneTest(unittest.TestCase):
    """真机接线：FieldScene 刷怪时按点位选种族。"""

    def _make_cave(self, seed=7, x=5, y=21):
        from tests.test_wild_encounter import make_field

        return make_field(map_id=CAVE_MAP, seed=seed, x=x, y=y)

    def test_scene_spawns_phoenix_at_deep_point(self):
        """深处点位的精灵是**不死鸟**（走 FieldScene 的真实刷怪路径）。"""
        game, scene = self._make_cave(seed=3)
        points = map_data.spawn_points_of(CAVE_MAP)
        deep = map_data.deep_spawn_points_of(CAVE_MAP)
        for target in deep:
            idx = points.index(target)
            scene._wild_state()["wanderers"].clear()
            w = scene._spawn_wanderer(idx, target)
            self.assertIsNotNone(w)
            self.assertEqual(w["species_id"], 7,
                             "深处点位必须刷出不死鸟")
            self.assertGreaterEqual(w["level"], 15)
            self.assertLessEqual(w["level"], 18)

    def test_scene_never_spawns_phoenix_at_normal_point(self):
        """普通点位永远刷不出不死鸟（真实刷怪路径）。"""
        game, scene = self._make_cave(seed=4)
        points = map_data.spawn_points_of(CAVE_MAP)
        deep = set(map_data.deep_spawn_points_of(CAVE_MAP))
        for target in points:
            if target in deep:
                continue
            idx = points.index(target)
            scene._wild_state()["wanderers"].clear()
            w = scene._spawn_wanderer(idx, target)
            self.assertIsNotNone(w)
            self.assertNotEqual(w["species_id"], 7,
                                "普通点位刷出了不死鸟")

    def test_cave_populates_wanderers(self):
        """进洞窟会刷出野生精灵（上限 4）。"""
        game, scene = self._make_cave(seed=11)
        for _ in range(3):
            game.update()
            game.draw()
        self.assertTrue(scene.wanderers, "洞窟应该刷出精灵")
        self.assertLessEqual(len(scene.wanderers), 4)


class CaveLongRunTest(unittest.TestCase):
    """在洞窟连跑 3000 帧：存活数、坐标、重叠。"""

    FRAMES = 3000

    def setUp(self):
        from tests.test_wild_encounter import make_field

        self.game, self.scene = make_field(map_id=CAVE_MAP, seed=20240607,
                                           x=5, y=21)

    def test_long_run_stays_legal(self):
        """3000 帧：存活数 <= 4、坐标始终可走、互不重叠。"""
        for _ in range(self.FRAMES):
            self.game.update()
            self.game.draw()
            wanderers = self.scene.wanderers
            self.assertLessEqual(len(wanderers), 4, "存活数超过上限")
            cells = [(w["gx"], w["gy"]) for w in wanderers]
            for x, y in cells:
                self.assertTrue(map_data.is_walkable(CAVE_MAP, x, y),
                                "精灵走到了不可走格 (%d,%d)" % (x, y))
            self.assertEqual(len(set(cells)), len(cells), "精灵之间重叠了")

    def test_long_run_stays_in_field_scene(self):
        """玩家不动时不会莫名其妙进战斗（场景始终是地图）。"""
        for _ in range(600):
            self.game.update()
            self.game.draw()
        self.assertIsInstance(self.game.scenes.current, FieldScene)
