"""新增 10 只精灵的数据层测试（§10.3「建议新增测试」）。

对照《02-新增10只精灵规划.md》：

- §4.1–§4.10：10 只新精灵（ID 9–18）在 Lv5 / Lv10 / Lv20 的派生属性
  **逐格相等**（10 只 × 3 个等级 × 5 项属性 = 150 格）；
- §六：每只新精灵 4 个技能（Lv1 两个 / Lv8 一个 / Lv16 一个）；
- §五：7 个新技能（ID 29–35）全部是 damage，威力 ≤ 125、MP ≤ 17；
- §8.1 / §8.2：野外与洞窟两张遇敌表权重和 = 100、等级区间合法；
- §8.3：洞窟深处仍然只刷不死鸟（deep_species = [7]，点位不变）；
- 存档往返：Creature(9..18) 可构造，to_dict → from_dict → to_dict 一致；
- §3.1：18 只精灵的属性分布。

> 已知偏差：§10.3 建议「每只新精灵 Lv1 至少 1 个 0MP 技能」，但 §四/§六 的
> 学习表里灯火鳅、荆星芽、雏羽啾、夜幕翼、绒医团、导线蛇的 Lv1 两招都
> 需要 MP（这两招本身就是它们的设计定位）。学习表按 §六 逐条实现，
> 该条断言改为「除下列 6 只外，Lv1 至少 1 个 0MP 技能」，例外名单
> 本身也被断言锁定，改学习表就会红。
"""

from __future__ import annotations

import unittest
from collections import Counter

from src.data import map_data
from src.data.skill_data import SKILLS, get_skill
from src.data.species_data import SPECIES, STAT_KEYS, get_species, stat_at
from src.model.creature import Creature

#: 新增 10 只精灵的 ID
NEW_SPECIES_IDS: tuple[int, ...] = tuple(range(9, 19))

#: §4 各只新精灵的 Lv5 派生属性表（HP / MP / ATK / DEF / SPD）
DOC_LV5 = {
    9: (29, 17, 19, 11, 22),
    10: (47, 21, 12, 19, 8),
    11: (36, 27, 14, 14, 15),
    12: (31, 18, 20, 13, 19),
    13: (47, 16, 21, 18, 7),
    14: (34, 20, 14, 13, 20),
    15: (35, 24, 17, 14, 20),
    16: (42, 28, 12, 17, 14),
    17: (35, 19, 18, 15, 16),
    18: (39, 28, 20, 14, 11),
}

#: §4 各只新精灵的 Lv10 派生属性表
DOC_LV10 = {
    9: (43, 22, 26, 16, 31),
    10: (68, 27, 17, 25, 12),
    11: (53, 36, 19, 19, 20),
    12: (46, 23, 28, 18, 26),
    13: (67, 21, 30, 24, 10),
    14: (50, 26, 19, 18, 27),
    15: (51, 31, 23, 19, 27),
    16: (61, 37, 17, 23, 19),
    17: (50, 25, 25, 21, 22),
    18: (56, 37, 28, 19, 15),
}

#: §4 各只新精灵的 Lv20 派生属性表
DOC_LV20 = {
    9: (70, 33, 41, 25, 48),
    10: (110, 40, 26, 38, 19),
    11: (87, 54, 29, 29, 31),
    12: (75, 34, 44, 28, 41),
    13: (108, 31, 47, 37, 16),
    14: (82, 38, 29, 28, 42),
    15: (83, 46, 36, 30, 42),
    16: (99, 55, 26, 36, 29),
    17: (81, 37, 39, 33, 34),
    18: (91, 55, 44, 29, 23),
}

#: §四 / §六 学习表：ID -> (Lv1 两个技能, Lv8 技能, Lv16 技能)
DOC_LEARNSET = {
    9: ([3, 1], [4], [29]),
    10: ([8, 1], [9], [10]),
    11: ([8, 19], [9], [30]),
    12: ([11, 1], [12], [31]),
    13: ([11, 24], [12], [32]),
    14: ([2, 25], [15], [16]),
    15: ([21, 24], [22], [33]),
    16: ([18, 19], [25], [20]),
    17: ([26, 24], [27], [34]),
    18: ([26, 1], [27], [35]),
}

#: §五 新增技能表：ID -> (名称, 属性, 威力, MP)
DOC_NEW_SKILLS = {
    29: ("狐火燎原", "火", 110, 15),
    30: ("灯芯回响", "水", 85, 11),
    31: ("千瓣斩", "草", 105, 13),
    32: ("荆星坠", "草", 115, 15),
    33: ("月蚀低语", "暗", 100, 13),
    34: ("串联雷网", "雷", 95, 12),
    35: ("雷云审判", "雷", 125, 17),
}

#: §8.1 野外（地图 2）遇敌表：species_id -> (level_min, level_max, weight)
DOC_FIELD_TABLE = {
    3: (2, 5, 20),
    1: (3, 6, 16),
    2: (3, 6, 14),
    4: (4, 7, 10),
    8: (3, 6, 8),
    10: (2, 5, 10),
    9: (4, 7, 8),
    14: (2, 4, 8),
    12: (5, 8, 4),
    17: (4, 7, 2),
}

#: §8.2 洞窟（地图 3）遇敌表：species_id -> (level_min, level_max, weight)
DOC_CAVE_TABLE = {
    6: (8, 12, 20),
    5: (9, 13, 18),
    4: (7, 10, 12),
    8: (8, 11, 12),
    7: (15, 18, 5),
    11: (8, 12, 8),
    13: (10, 14, 8),
    15: (9, 13, 8),
    16: (9, 12, 5),
    18: (12, 16, 4),
}

#: §3.1 属性分布：属性 -> 数量
DOC_TYPE_COUNTS = {
    "火": 3, "水": 3, "草": 3, "风": 2, "光": 2, "暗": 2, "雷": 3,
}

#: §10.3「Lv1 至少 1 个 0MP 技能」的例外名单（见模块文档字符串）
ZERO_MP_LV1_EXCEPTIONS = frozenset({11, 13, 14, 15, 16, 17})


class NewSpeciesDerivedStatsTest(unittest.TestCase):
    """§4 派生属性逐格相等（150 格）。"""

    def test_all_new_species_exist(self):
        for sid in NEW_SPECIES_IDS:
            self.assertIn(sid, SPECIES, f"缺少新精灵 {sid}")

    def _check_table(self, table: dict, level: int) -> int:
        checked = 0
        for sid, expected in table.items():
            for idx, key in enumerate(STAT_KEYS):
                self.assertEqual(
                    stat_at(sid, key, level), expected[idx],
                    f"§4 Lv{level} {get_species(sid).name} {key} 不一致",
                )
                checked += 1
        return checked

    def test_lv5_table(self):
        self.assertEqual(self._check_table(DOC_LV5, 5), 50)

    def test_lv10_table(self):
        self.assertEqual(self._check_table(DOC_LV10, 10), 50)

    def test_lv20_table(self):
        self.assertEqual(self._check_table(DOC_LV20, 20), 50)

    def test_total_cells_checked_is_150(self):
        total = sum(
            len(table) * len(STAT_KEYS)
            for table in (DOC_LV5, DOC_LV10, DOC_LV20)
        )
        self.assertEqual(total, 150)

    def test_new_species_names_and_types(self):
        expected = {
            9: ("雾尾狐", "火"),
            10: ("涟漪豚", "水"),
            11: ("灯火鳅", "水"),
            12: ("花刃忍", "草"),
            13: ("荆星芽", "草"),
            14: ("雏羽啾", "风"),
            15: ("夜幕翼", "暗"),
            16: ("绒医团", "光"),
            17: ("导线蛇", "雷"),
            18: ("雷云团", "雷"),
        }
        for sid, (name, type_name) in expected.items():
            self.assertEqual(get_species(sid).name, name, f"种族 {sid} 名称")
            self.assertEqual(get_species(sid).type, type_name, f"种族 {sid} 属性")

    def test_catch_coef_within_range(self):
        """§11.1：捕捉系数不高于 0.55、不低于 0.25。"""
        for sid in NEW_SPECIES_IDS:
            coef = get_species(sid).catch_coef
            self.assertGreaterEqual(coef, 0.25, f"种族 {sid} 捕捉系数过低")
            self.assertLessEqual(coef, 0.55, f"种族 {sid} 捕捉系数过高")


class NewSpeciesLearnsetTest(unittest.TestCase):
    """§六 学习表。"""

    def test_learnset_matches_doc(self):
        for sid, (lv1, lv8, lv16) in DOC_LEARNSET.items():
            sp = get_species(sid)
            self.assertEqual(sp.learnset.get(1), lv1, f"种族 {sid} Lv1 技能")
            self.assertEqual(sp.learnset.get(8), lv8, f"种族 {sid} Lv8 技能")
            self.assertEqual(sp.learnset.get(16), lv16, f"种族 {sid} Lv16 技能")

    def test_skill_total_is_four(self):
        for sid in NEW_SPECIES_IDS:
            total = sum(len(v) for v in get_species(sid).learnset.values())
            self.assertEqual(total, 4, f"种族 {sid} 技能总数应为 4")

    def test_learnset_levels_are_1_8_16(self):
        for sid in NEW_SPECIES_IDS:
            self.assertEqual(sorted(get_species(sid).learnset), [1, 8, 16],
                             f"种族 {sid} 学习等级")

    def test_lv1_has_two_skills(self):
        for sid in NEW_SPECIES_IDS:
            self.assertEqual(len(get_species(sid).learnset.get(1, [])), 2,
                             f"种族 {sid} Lv1 应学 2 个技能")

    def test_lv1_has_a_zero_mp_skill(self):
        """§10.3 的建议断言（例外名单见 ZERO_MP_LV1_EXCEPTIONS）。"""
        for sid in NEW_SPECIES_IDS:
            lv1 = get_species(sid).learnset.get(1, [])
            has_free = any(get_skill(s).mp == 0 for s in lv1)
            if sid in ZERO_MP_LV1_EXCEPTIONS:
                self.assertFalse(has_free, f"种族 {sid} 不该再算进例外名单")
            else:
                self.assertTrue(has_free, f"种族 {sid} Lv1 至少要有 1 个 0MP 技能")

    def test_exception_list_matches_learnset(self):
        """例外名单必须与 §六 学习表一致（改了学习表就会红）。"""
        actual = {
            sid for sid in NEW_SPECIES_IDS
            if not any(get_skill(s).mp == 0
                       for s in get_species(sid).learnset.get(1, []))
        }
        self.assertEqual(actual, set(ZERO_MP_LV1_EXCEPTIONS))

    def test_all_learned_skills_exist(self):
        for sid in NEW_SPECIES_IDS:
            for level, skill_ids in get_species(sid).learnset.items():
                for skill_id in skill_ids:
                    self.assertIn(skill_id, SKILLS,
                                  f"种族 {sid} Lv{level} 技能 {skill_id} 不存在")


class NewSkillTest(unittest.TestCase):
    """§五 7 个新技能。"""

    def test_new_skill_ids_exist(self):
        for sid in DOC_NEW_SKILLS:
            self.assertIn(sid, SKILLS, f"缺少技能 {sid}")

    def test_new_skill_rows_match_doc(self):
        for sid, (name, type_name, power, mp) in DOC_NEW_SKILLS.items():
            sk = get_skill(sid)
            self.assertEqual(sk.name, name, f"技能 {sid} 名称")
            self.assertEqual(sk.type, type_name, f"技能 {sid} 属性")
            self.assertEqual(sk.power, power, f"技能 {sid} 威力")
            self.assertEqual(sk.mp, mp, f"技能 {sid} MP")

    def test_all_new_skills_are_damage(self):
        for sid in DOC_NEW_SKILLS:
            self.assertEqual(get_skill(sid).effect, "damage",
                             f"技能 {sid} 效果必须是 damage")

    def test_power_and_mp_within_cap(self):
        """§5.2 / §10.3：威力 ≤ 125、MP ≤ 17。"""
        for sid in DOC_NEW_SKILLS:
            sk = get_skill(sid)
            self.assertLessEqual(sk.power, 125, f"技能 {sid} 威力超过 125")
            self.assertLessEqual(sk.mp, 17, f"技能 {sid} MP 超过 17")

    def test_new_skills_do_not_exceed_old_max(self):
        """新技能不能盖过旧最高：凤凰天翔 130 / 18MP。"""
        for sid in DOC_NEW_SKILLS:
            sk = get_skill(sid)
            self.assertLess(sk.power, get_skill(7).power, f"技能 {sid} 威力超过凤凰天翔")
            self.assertLess(sk.mp, get_skill(7).mp, f"技能 {sid} MP 超过凤凰天翔")

    def test_new_skills_desc_present_and_unique(self):
        descs = [get_skill(sid).desc for sid in DOC_NEW_SKILLS]
        for sid, desc in zip(DOC_NEW_SKILLS, descs):
            self.assertTrue(desc.strip(), f"技能 {sid} 缺少说明")
        self.assertEqual(len(set(descs)), len(descs), "新技能说明不能重复")
        all_descs = [sk.desc for sk in SKILLS.values()]
        self.assertEqual(len(set(all_descs)), len(all_descs), "技能说明不能重复")

    def test_new_skill_names_unique(self):
        names = [sk.name for sk in SKILLS.values()]
        self.assertEqual(len(set(names)), len(names), "技能名不能重复")


class EncounterTableTest(unittest.TestCase):
    """§8 两张新遇敌表。"""

    def _table_of(self, map_id: int) -> list[dict]:
        enc = map_data.encounters_of(map_id)
        self.assertIsNotNone(enc, f"地图 {map_id} 应当有遇敌表")
        return enc["table"]

    def _check_table(self, map_id: int, doc: dict, label: str):
        table = self._table_of(map_id)
        self.assertEqual(len(table), len(doc), f"{label} 行数")
        got = {
            int(r["species_id"]): (int(r["level_min"]), int(r["level_max"]),
                                   int(r["weight"]))
            for r in table
        }
        self.assertEqual(got, doc, f"{label} 与文档不一致")
        total = sum(int(r["weight"]) for r in table)
        self.assertEqual(total, 100, f"{label} 权重之和必须是 100")
        for r in table:
            sid = int(r["species_id"])
            self.assertIn(sid, SPECIES, f"{label} 种族 {sid} 不在 SPECIES 里")
            lo, hi = int(r["level_min"]), int(r["level_max"])
            self.assertLessEqual(lo, hi, f"{label} 种族 {sid} 等级区间反了")
            self.assertGreaterEqual(lo, 1, f"{label} 种族 {sid} 等级下界 < 1")
            self.assertLessEqual(hi, 20, f"{label} 种族 {sid} 等级上界 > 20")

    def test_field_table(self):
        self._check_table(2, DOC_FIELD_TABLE, "野外遇敌表")

    def test_cave_table(self):
        self._check_table(3, DOC_CAVE_TABLE, "洞窟遇敌表")

    def test_new_species_all_reachable(self):
        """新增的 10 只都要出现在某张表里。"""
        field_ids = {int(r["species_id"]) for r in self._table_of(2)}
        cave_ids = {int(r["species_id"]) for r in self._table_of(3)}
        reachable = field_ids | cave_ids
        for sid in NEW_SPECIES_IDS:
            self.assertIn(sid, reachable, f"新精灵 {sid} 两张表里都没出现")

    def test_deep_area_still_only_phoenix(self):
        """§8.3：深处只刷不死鸟，deep_species = [7]，点位不变。"""
        self.assertEqual(map_data.deep_species_of(3), [7])
        self.assertEqual(map_data.deep_spawn_points_of(3),
                         [(28, 3), (29, 6), (32, 6), (33, 3)])

    def test_field_level_range_covers_new_species(self):
        """§8.5：野外等级 2–8、洞窟 7–18。"""
        field = self._table_of(2)
        self.assertEqual(min(int(r["level_min"]) for r in field), 2)
        self.assertEqual(max(int(r["level_max"]) for r in field), 8)
        cave = self._table_of(3)
        self.assertEqual(min(int(r["level_min"]) for r in cave), 7)
        self.assertEqual(max(int(r["level_max"]) for r in cave), 18)


class CreatureRoundTripTest(unittest.TestCase):
    """存档往返。"""

    def test_creature_can_be_constructed(self):
        for sid in NEW_SPECIES_IDS:
            c = Creature(sid)
            self.assertEqual(c.species_id, sid)
            self.assertEqual(c.skills, get_species(sid).learnset.get(1, []),
                             f"种族 {sid} 默认技能应为 Lv1 两招")

    def test_to_dict_from_dict_round_trip(self):
        for sid in NEW_SPECIES_IDS:
            for level in (5, 10, 20):
                c = Creature(sid, level=level)
                data = c.to_dict()
                back = Creature.from_dict(data)
                self.assertEqual(back.to_dict(), data,
                                 f"种族 {sid} Lv{level} 存档往返不一致")

    def test_round_trip_keeps_stats(self):
        for sid in NEW_SPECIES_IDS:
            c = Creature(sid, level=20)
            back = Creature.from_dict(c.to_dict())
            self.assertEqual(back.hp_max, c.hp_max, f"种族 {sid} HP 上限")
            self.assertEqual(back.mp_max, c.mp_max, f"种族 {sid} MP 上限")
            self.assertEqual(back.attack, c.attack, f"种族 {sid} ATK")
            self.assertEqual(back.defense, c.defense, f"种族 {sid} DEF")
            self.assertEqual(back.speed, c.speed, f"种族 {sid} SPD")


class RosterTest(unittest.TestCase):
    """§3.1 属性分布。"""

    def test_species_count_is_18(self):
        self.assertEqual(len(SPECIES), 18)

    def test_type_distribution(self):
        counter = Counter(sp.type for sp in SPECIES.values())
        self.assertEqual(dict(counter), DOC_TYPE_COUNTS)


if __name__ == "__main__":
    unittest.main()
