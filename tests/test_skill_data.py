"""技能数据测试（src/data/skill_data.py）。

覆盖《数值设定.md》§3 / §3.1：

- 28 个技能的 ID / 名称 / 属性 / 威力 / MP / 效果逐条相等；
- 治疗技能的回复比例与最小回复量、减益技能的倍率与持续回合；
- §3.1 技能学习表 8 只精灵 × 3 个等级（Lv1 / Lv8 / Lv16）相等。
"""

from __future__ import annotations

import unittest

from src.data.skill_data import SKILLS, get_skill
from src.data.species_data import SPECIES

#: §3 技能表：ID -> (名称, 属性, 威力, MP, 效果)
DOC_SKILLS = {
    1: ("撞击", "无", 35, 0, "damage"),
    2: ("啄击", "风", 32, 2, "damage"),
    3: ("火花", "火", 40, 4, "damage"),
    4: ("烈焰", "火", 90, 10, "damage"),
    5: ("天火燎原", "火", 120, 16, "damage"),
    6: ("涅槃之炎", "火", 75, 8, "damage"),
    7: ("凤凰天翔", "火", 130, 18, "damage"),
    8: ("水枪", "水", 40, 4, "damage"),
    9: ("水之波动", "水", 65, 7, "damage"),
    10: ("激流", "水", 100, 13, "damage"),
    11: ("飞叶", "草", 40, 4, "damage"),
    12: ("藤鞭", "草", 60, 6, "damage"),
    13: ("叶刃风暴", "草", 100, 13, "damage"),
    14: ("风刃", "风", 45, 5, "damage"),
    15: ("疾风斩", "风", 65, 7, "damage"),
    16: ("神风", "风", 105, 14, "damage"),
    17: ("圣光", "光", 85, 10, "damage"),
    18: ("净化之光", "光", 60, 6, "damage"),
    19: ("治愈波动", "光", 0, 8, "heal"),
    20: ("圣域", "光", 0, 12, "heal"),
    21: ("暗影咬", "暗", 50, 5, "damage"),
    22: ("深渊噬咬", "暗", 70, 8, "damage"),
    23: ("三重咬碎", "暗", 110, 14, "damage"),
    24: ("吼叫", "无", 0, 3, "debuff_atk"),
    25: ("再生", "无", 0, 8, "heal"),
    26: ("电击", "雷", 45, 5, "damage"),
    27: ("电光一闪", "雷", 60, 6, "damage"),
    28: ("万雷天牢", "雷", 110, 14, "damage"),
}

#: §3 治疗 / 减益技能的效果参数
DOC_EFFECT_PARAMS = {
    19: {"value": 0.25, "min_heal": 12, "duration": 0},
    20: {"value": 0.5, "min_heal": 25, "duration": 0},
    25: {"value": 0.3, "min_heal": 15, "duration": 0},
    24: {"value": 0.75, "min_heal": 0, "duration": 3},
}

#: §3.1 技能学习表：种族 ID -> (Lv1 初始技能, Lv8 技能, Lv16 技能)
DOC_LEARNSET = {
    1: ([3, 1], [4], [5]),
    2: ([8, 1], [9], [10]),
    3: ([11, 1], [12], [13]),
    4: ([14, 2], [15], [16]),
    5: ([17, 19], [18], [20]),
    6: ([21, 24], [22], [23]),
    7: ([4, 25], [6], [7]),
    8: ([26, 1], [27], [28]),
}


class SkillTableTest(unittest.TestCase):
    """§3 技能表逐条相等。"""

    def test_skill_ids_are_1_to_28(self):
        self.assertEqual(sorted(SKILLS), list(range(1, 29)))

    def test_skill_rows_match_doc(self):
        for sid, (name, type_name, power, mp, effect) in DOC_SKILLS.items():
            sk = get_skill(sid)
            self.assertEqual(sk.name, name, f"技能 {sid} 名称不一致")
            self.assertEqual(sk.type, type_name, f"技能 {sid} 属性不一致")
            self.assertEqual(sk.power, power, f"技能 {sid} 威力不一致")
            self.assertEqual(sk.mp, mp, f"技能 {sid} MP 不一致")
            self.assertEqual(sk.effect, effect, f"技能 {sid} 效果不一致")

    def test_effect_params_match_doc(self):
        for sid, params in DOC_EFFECT_PARAMS.items():
            sk = get_skill(sid)
            self.assertAlmostEqual(sk.value, params["value"], msg=f"技能 {sid} value")
            self.assertEqual(sk.min_heal, params["min_heal"], msg=f"技能 {sid} min_heal")
            self.assertEqual(sk.duration, params["duration"], msg=f"技能 {sid} duration")

    def test_non_effect_fields_are_zero(self):
        for sid, sk in SKILLS.items():
            if sk.effect == "damage":
                self.assertEqual(sk.min_heal, 0, f"技能 {sid} 非治疗技能 min_heal 应为 0")
                self.assertEqual(sk.duration, 0, f"技能 {sid} 非减益技能 duration 应为 0")

    def test_zero_power_skills_are_not_damage(self):
        for sid, sk in SKILLS.items():
            if sk.power == 0:
                self.assertNotEqual(sk.effect, "damage",
                                    f"技能 {sid} 威力 0 不应是 damage")

    def test_get_skill_unknown_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_skill(99)


class LearnsetTest(unittest.TestCase):
    """§3.1 技能学习表。"""

    def test_learnset_matches_doc(self):
        for sid, (lv1, lv8, lv16) in DOC_LEARNSET.items():
            sp = SPECIES[sid]
            self.assertEqual(sp.learnset.get(1), lv1, f"种族 {sid} Lv1 技能不一致")
            self.assertEqual(sp.learnset.get(8), lv8, f"种族 {sid} Lv8 技能不一致")
            self.assertEqual(sp.learnset.get(16), lv16, f"种族 {sid} Lv16 技能不一致")

    def test_learnset_only_has_three_levels(self):
        for sid, sp in SPECIES.items():
            self.assertEqual(sorted(sp.learnset), [1, 8, 16], f"种族 {sid} 学习等级")

    def test_every_learned_skill_exists(self):
        for sid, sp in SPECIES.items():
            for level, skill_ids in sp.learnset.items():
                for skill_id in skill_ids:
                    self.assertIn(skill_id, SKILLS, f"种族 {sid} Lv{level} 技能不存在")

    def test_skill_capacity_is_four(self):
        """每只精灵 2 初始 + 2 升级，正好 4 个。"""
        for sid, sp in SPECIES.items():
            total = sum(len(v) for v in sp.learnset.values())
            self.assertEqual(total, 4, f"种族 {sid} 技能总数应为 4")


if __name__ == "__main__":
    unittest.main()
