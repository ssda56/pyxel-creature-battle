"""精灵种族数据测试（src/data/species_data.py）。

覆盖《数值设定.md》§1.2 / §1.3 / §6.1 / §8：

- §1.3 三张派生属性表**逐格相等**（1–8 号 8 精灵 × Lv5/Lv10/Lv20 × 5 属性 = 120 格；
  新增 9–18 号见 tests/test_new_species_data.py）；
- §1.2 基础值 / 成长值 / 定位 / 属性；
- §6.1 经验表 need(L) 19 个值 + 累计值；
- §8 种族捕捉系数；
- 查询 helper 的异常行为。
"""

from __future__ import annotations

import unittest

from src.data import species_data
from src.data.species_data import (
    EXP_TABLE,
    MAX_LEVEL,
    MAX_SKILLS,
    MIN_LEVEL,
    SPECIES,
    STARTER_IDS,
    STAT_KEYS,
    get_species,
    learnset_at,
    learnset_up_to,
    need_exp,
    stat_at,
)

#: §1.3 Lv5 派生属性表（HP / MP / ATK / DEF / SPD）
DOC_STATS_LV5 = {
    1: (34, 16, 19, 13, 14),
    2: (41, 18, 14, 16, 11),
    3: (31, 17, 15, 12, 20),
    4: (29, 16, 17, 12, 21),
    5: (44, 24, 18, 16, 13),
    6: (37, 16, 23, 14, 15),
    7: (37, 27, 21, 16, 19),
    8: (28, 18, 17, 10, 24),
}

#: §1.3 Lv10 派生属性表
DOC_STATS_LV10 = {
    1: (50, 21, 26, 18, 20),
    2: (60, 23, 19, 22, 16),
    3: (45, 22, 21, 17, 28),
    4: (42, 21, 24, 17, 28),
    5: (64, 32, 24, 22, 18),
    6: (54, 21, 32, 19, 21),
    7: (54, 36, 30, 22, 26),
    8: (41, 23, 23, 15, 33),
}

#: §1.3 Lv20 派生属性表
DOC_STATS_LV20 = {
    1: (82, 31, 41, 29, 32),
    2: (98, 34, 30, 35, 25),
    3: (73, 32, 33, 27, 44),
    4: (68, 31, 38, 27, 43),
    5: (104, 48, 37, 34, 28),
    6: (88, 31, 50, 30, 33),
    7: (88, 54, 47, 34, 40),
    8: (67, 34, 36, 24, 51),
}

#: §1.2 成长表：名称 / 属性 / 定位 / (基础, 成长) / 捕捉系数
DOC_BASE_GROWTH = {
    1: ("小火狮", "火", "攻击型",
        {"HP": (22, 3.2), "MP": (12, 1.0), "ATK": (13, 1.5),
         "DEF": (9, 1.1), "SPD": (10, 1.2)}, 0.40),
    2: ("水滴滴", "水", "均衡型",
        {"HP": (26, 3.8), "MP": (14, 1.1), "ATK": (10, 1.1),
         "DEF": (11, 1.3), "SPD": (8, 0.9)}, 0.55),
    3: ("兔小子", "草", "速度型",
        {"HP": (20, 2.8), "MP": (13, 1.0), "ATK": (11, 1.2),
         "DEF": (8, 1.0), "SPD": (14, 1.6)}, 0.55),
    4: ("小狮鹫", "风", "速攻型",
        {"HP": (19, 2.6), "MP": (12, 1.0), "ATK": (12, 1.4),
         "DEF": (8, 1.0), "SPD": (15, 1.5)}, 0.40),
    5: ("独角兽", "光", "治疗/特攻",
        {"HP": (28, 4.0), "MP": (18, 1.6), "ATK": (13, 1.3),
         "DEF": (12, 1.2), "SPD": (9, 1.0)}, 0.25),
    6: ("三头犬", "暗", "攻击型",
        {"HP": (24, 3.4), "MP": (12, 1.0), "ATK": (16, 1.8),
         "DEF": (10, 1.1), "SPD": (11, 1.2)}, 0.25),
    7: ("不死鸟", "火", "稀有强力",
        {"HP": (24, 3.4), "MP": (20, 1.8), "ATK": (15, 1.7),
         "DEF": (12, 1.2), "SPD": (14, 1.4)}, 0.10),
    8: ("闪电小子", "雷", "速攻型",
        {"HP": (18, 2.6), "MP": (14, 1.1), "ATK": (12, 1.3),
         "DEF": (7, 0.9), "SPD": (17, 1.8)}, 0.40),
    # 以下 10 只见《02-新增10只精灵规划.md》§4
    9: ("雾尾狐", "火", "高速游击",
        {"HP": (19, 2.7), "MP": (13, 1.1), "ATK": (13, 1.5),
         "DEF": (8, 0.9), "SPD": (16, 1.7)}, 0.40),
    10: ("涟漪豚", "水", "物理水盾",
        {"HP": (31, 4.2), "MP": (16, 1.3), "ATK": (9, 0.9),
         "DEF": (14, 1.3), "SPD": (6, 0.7)}, 0.55),
    11: ("灯火鳅", "水", "治疗/法系",
        {"HP": (23, 3.4), "MP": (20, 1.8), "ATK": (10, 1.0),
         "DEF": (10, 1.0), "SPD": (11, 1.1)}, 0.40),
    12: ("花刃忍", "草", "高速刺客",
        {"HP": (20, 2.9), "MP": (14, 1.1), "ATK": (14, 1.6),
         "DEF": (9, 1.0), "SPD": (13, 1.5)}, 0.40),
    13: ("荆星芽", "草", "重装炮台",
        {"HP": (31, 4.1), "MP": (12, 1.0), "ATK": (15, 1.7),
         "DEF": (13, 1.3), "SPD": (5, 0.6)}, 0.25),
    14: ("雏羽啾", "风", "辅助/续航",
        {"HP": (22, 3.2), "MP": (16, 1.2), "ATK": (10, 1.0),
         "DEF": (9, 1.0), "SPD": (14, 1.5)}, 0.55),
    15: ("夜幕翼", "暗", "法系速攻",
        {"HP": (23, 3.2), "MP": (18, 1.5), "ATK": (12, 1.3),
         "DEF": (10, 1.1), "SPD": (14, 1.5)}, 0.40),
    16: ("绒医团", "光", "医护/续航",
        {"HP": (27, 3.8), "MP": (21, 1.8), "ATK": (9, 0.9),
         "DEF": (12, 1.3), "SPD": (10, 1.0)}, 0.40),
    17: ("导线蛇", "雷", "均衡削弱",
        {"HP": (23, 3.1), "MP": (15, 1.2), "ATK": (13, 1.4),
         "DEF": (11, 1.2), "SPD": (12, 1.2)}, 0.40),
    18: ("雷云团", "雷", "慢速爆发",
        {"HP": (25, 3.5), "MP": (21, 1.8), "ATK": (14, 1.6),
         "DEF": (10, 1.0), "SPD": (8, 0.8)}, 0.25),
}

#: §6.1 升级所需经验表：等级 -> 需要
DOC_EXP_NEED = {
    1: 16, 2: 32, 3: 52, 4: 75, 5: 101, 6: 128, 7: 158, 8: 189, 9: 222,
    10: 257, 11: 293, 12: 330, 13: 368, 14: 408, 15: 449, 16: 491, 17: 533,
    18: 577, 19: 622,
}

#: §6.1 累计经验表：等级 -> 从 Lv1 累计到该等级
DOC_EXP_CUM = {
    2: 16, 3: 48, 4: 100, 5: 175, 6: 276, 7: 404, 8: 562, 9: 751, 10: 973,
    11: 1230, 12: 1523, 13: 1853, 14: 2221, 15: 2629, 16: 3078, 17: 3569,
    18: 4102, 19: 4679, 20: 5301,
}


class SpeciesTableTest(unittest.TestCase):
    """§1.2 成长表本身。"""

    def test_species_ids_are_1_to_18(self):
        self.assertEqual(sorted(SPECIES), list(range(1, 19)))

    def test_base_and_growth_match_doc(self):
        for sid, (name, type_name, role, stats, coef) in DOC_BASE_GROWTH.items():
            sp = get_species(sid)
            self.assertEqual(sp.name, name, f"种族 {sid} 名称不一致")
            self.assertEqual(sp.type, type_name, f"种族 {sid} 属性不一致")
            self.assertEqual(sp.role, role, f"种族 {sid} 定位不一致")
            self.assertEqual(sorted(sp.base), sorted(STAT_KEYS))
            self.assertEqual(sorted(sp.growth), sorted(STAT_KEYS))
            for key, (base, growth) in stats.items():
                self.assertAlmostEqual(sp.base[key], base, msg=f"{sid}.{key} 基础值")
                self.assertAlmostEqual(sp.growth[key], growth, msg=f"{sid}.{key} 成长值")

    def test_catch_coef_matches_doc(self):
        for sid, (_n, _t, _r, _s, coef) in DOC_BASE_GROWTH.items():
            self.assertAlmostEqual(SPECIES[sid].catch_coef, coef, msg=f"种族 {sid} 捕捉系数")

    def test_starter_ids(self):
        self.assertEqual(STARTER_IDS, (1, 2, 3))
        for sid in STARTER_IDS:
            self.assertIn(sid, SPECIES)

    def test_get_species_unknown_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_species(99)


class DerivedStatsTest(unittest.TestCase):
    """§1.3 三张派生属性表逐格相等（120 格）。"""

    def _check_table(self, table: dict, level: int):
        for sid, expected in table.items():
            for idx, key in enumerate(STAT_KEYS):
                self.assertEqual(
                    stat_at(sid, key, level), expected[idx],
                    f"§1.3 Lv{level} {get_species(sid).name} {key} 不一致",
                )

    def test_lv5_table(self):
        self._check_table(DOC_STATS_LV5, 5)

    def test_lv10_table(self):
        self._check_table(DOC_STATS_LV10, 10)

    def test_lv20_table(self):
        self._check_table(DOC_STATS_LV20, 20)

    def test_table_cell_count(self):
        """确认断言覆盖了 8 × 3 × 5 = 120 格。"""
        total = 0
        for table in (DOC_STATS_LV5, DOC_STATS_LV10, DOC_STATS_LV20):
            total += len(table) * len(STAT_KEYS)
        self.assertEqual(total, 120)

    def test_stat_at_follows_formula(self):
        """实现必须严格等于 floor(base + (level-1) * growth)。"""
        import math
        for sid, sp in SPECIES.items():
            for level in range(1, MAX_LEVEL + 1):
                for key in STAT_KEYS:
                    expect = int(math.floor(sp.base[key] + (level - 1) * sp.growth[key]))
                    self.assertEqual(stat_at(sid, key, level), expect,
                                     f"{sid} Lv{level} {key}")

    def test_stat_at_invalid_key_raises(self):
        with self.assertRaises(KeyError):
            stat_at(1, "ATK2", 5)


class ExpCurveTest(unittest.TestCase):
    """§6.1 经验表。"""

    def test_need_exp_matches_doc(self):
        for level, need in DOC_EXP_NEED.items():
            self.assertEqual(need_exp(level), need, f"need({level}) 不一致")

    def test_need_exp_count_is_19(self):
        self.assertEqual(len(DOC_EXP_NEED), 19)
        self.assertEqual(sorted(EXP_TABLE), list(range(1, 20)))

    def test_cumulative_matches_doc(self):
        total = 0
        for level in range(1, 20):
            total += need_exp(level)
            self.assertEqual(total, DOC_EXP_CUM[level + 1],
                             f"累计到 Lv{level + 1} 不一致")

    def test_key_cumulative_values(self):
        self.assertEqual(DOC_EXP_CUM[8], 562)
        self.assertEqual(DOC_EXP_CUM[16], 3078)
        self.assertEqual(DOC_EXP_CUM[20], 5301)
        self.assertEqual(sum(need_exp(lv) for lv in range(1, 8)), 562)
        self.assertEqual(sum(need_exp(lv) for lv in range(1, 16)), 3078)
        self.assertEqual(sum(need_exp(lv) for lv in range(1, 20)), 5301)


class LearnsetUpToTest(unittest.TestCase):
    """learnset_up_to()：按等级累积、去重、上限 4（《数值设定.md》§3.1）。

    对应《02-新增10只精灵规划.md》§9.4 方案 B：野生精灵应该带上
    「到该等级为止累计学会的技能」，而不是只有 Lv1 两招。
    """

    def test_lv1_only_has_initial_skills(self):
        """Lv1 仍然只有 Lv1 的两招（不能变）。"""
        for sid in SPECIES:
            self.assertEqual(learnset_up_to(sid, 1),
                             learnset_at(sid, 1),
                             f"种族 {sid} Lv1 技能应等于 Lv1 初始技能")

    def test_phoenix_accumulates_by_level(self):
        """不死鸟 {1: [4, 25], 8: [6], 16: [7]}：Lv15 三招、Lv16 四招。"""
        self.assertEqual(learnset_up_to(7, 1), [4, 25])
        self.assertEqual(learnset_up_to(7, 7), [4, 25])
        self.assertEqual(learnset_up_to(7, 8), [4, 25, 6])
        self.assertEqual(learnset_up_to(7, 15), [4, 25, 6])
        self.assertEqual(learnset_up_to(7, 16), [4, 25, 6, 7])
        self.assertEqual(learnset_up_to(7, 20), [4, 25, 6, 7])

    def test_every_species_accumulates_monotonically(self):
        """每只精灵的技能集合随等级只增不减，且是 Lv1 技能的子集扩展。"""
        for sid, sp in SPECIES.items():
            previous: list[int] = []
            for level in range(MIN_LEVEL, MAX_LEVEL + 1):
                current = learnset_up_to(sid, level)
                # 单调递增：低等级的招不会被丢掉
                for skill_id in previous:
                    self.assertIn(skill_id, current,
                                  f"种族 {sid} Lv{level} 丢了之前的技能")
                previous = current

    def test_no_duplicates_and_cap_at_four(self):
        """任意等级都不超过 4 个技能，且没有重复。"""
        for sid in SPECIES:
            for level in range(MIN_LEVEL, MAX_LEVEL + 1):
                skills = learnset_up_to(sid, level)
                self.assertLessEqual(len(skills), MAX_SKILLS,
                                     f"种族 {sid} Lv{level} 技能超过 {MAX_SKILLS} 个")
                self.assertEqual(len(skills), len(set(skills)),
                                 f"种族 {sid} Lv{level} 技能有重复：{skills}")

    def test_max_skills_parameter_is_respected(self):
        """max_skills 可以调小（截断到前 N 个）。"""
        self.assertEqual(learnset_up_to(7, 20, max_skills=0), [])
        self.assertEqual(learnset_up_to(7, 20, max_skills=2), [4, 25])
        self.assertEqual(learnset_up_to(7, 20, max_skills=3), [4, 25, 6])

    def test_level_below_min_is_clamped(self):
        """等级低于 1 时按 Lv1 计算。"""
        self.assertEqual(learnset_up_to(7, 0), learnset_up_to(7, 1))
        self.assertEqual(learnset_up_to(7, -5), learnset_up_to(7, 1))

    def test_unknown_species_raises_keyerror(self):
        with self.assertRaises(KeyError):
            learnset_up_to(99, 5)

    def test_order_is_stable_across_calls(self):
        """同一输入两次调用结果一致（顺序稳定）。"""
        for sid in SPECIES:
            for level in (1, 8, 15, 16, 20):
                self.assertEqual(learnset_up_to(sid, level),
                                 learnset_up_to(sid, level))


if __name__ == "__main__":
    unittest.main()
