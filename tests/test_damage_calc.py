"""伤害公式测试（src/battle/damage_calc.py）。

覆盖《数值设定.md》§4.1 / §4.2：

- §4.2 战斗节奏表的 5 个场景（不计浮动的期望伤害 + 浮动区间）；
- 伤害公式的边界：最小伤害 1、威力 0 返回 0、"无"属性恒 1.0 倍；
- 治疗量公式 max(min_heal, ceil(max_hp * value))。
"""

from __future__ import annotations

import math
import random
import unittest

from src.battle.damage_calc import damage, expected_damage, heal_amount
from src.battle.type_chart import multiplier
from src.data.skill_data import get_skill

#: §4.2 战斗节奏表：(场景, ATK, DEF, 技能属性, 威力, 防御方属性, 期望伤害)
#: 场景中的 ATK / DEF 均取 Lv5 同级精灵的派生值。
DOC_RHYTHM = [
    ("克制命中（火→草，火花 p40）", 19, 12, "火", 40, "草", 20.8),
    ("普通命中（火→火，火花 p40）", 19, 13, "火", 40, "火", 10.0),
    ("抵抗命中（草→火，飞叶 p40）", 15, 13, "草", 40, "火", 3.4),
    ("抵抗时改用撞击（无属性 p35）", 19, 13, "无", 35, "火", 8.8),
    ("终极技（烈焰 p90，1.0×）", 21, 14, "火", 90, "暗", 25.2),
]


class RhythmTableTest(unittest.TestCase):
    """§4.2 节奏表。"""

    def test_expected_damage_matches_doc(self):
        for name, atk, dfd, stype, power, dtype, expect in DOC_RHYTHM:
            got = expected_damage(atk, dfd, stype, power, dtype)
            # §4.2 表格按 1 位小数书写（如 8.75 记作 8.8）
            self.assertEqual(round(got, 1), expect, msg=f"§4.2 {name}")

    def test_damage_falls_in_variance_interval(self):
        """固定种子采样，伤害必落在 [floor(e×0.9), floor(e×1.1)] 区间内。"""
        for name, atk, dfd, stype, power, dtype, expect in DOC_RHYTHM:
            lo = int(math.floor(expect * 0.90))
            hi = int(math.floor(expect * 1.10))
            rng = random.Random(20261023)
            for _ in range(200):
                dmg = damage(atk, dfd, stype, power, dtype, rng=rng)
                self.assertGreaterEqual(dmg, lo, f"§4.2 {name} 伤害低于下限")
                self.assertLessEqual(dmg, hi, f"§4.2 {name} 伤害高于上限")

    def test_sampled_mean_in_expected_band(self):
        """Lv5 小火狮 火花 vs 兔小子（2.0×）：均值落在 19~23，且覆盖 20 / 21。"""
        rng = random.Random(20261023)
        values = [damage(19, 12, "火", 40, "草", rng=rng) for _ in range(2000)]
        mean = sum(values) / len(values)
        self.assertGreaterEqual(mean, 19.0, "均值低于 19")
        self.assertLessEqual(mean, 23.0, "均值高于 23")
        self.assertIn(20, values, "采样未覆盖伤害 20")
        self.assertIn(21, values, "采样未覆盖伤害 21")


class DamageFormulaTest(unittest.TestCase):
    """§4.1 落地公式。"""

    def test_zero_power_returns_zero(self):
        self.assertEqual(damage(19, 12, "火", 0, "草"), 0)
        self.assertEqual(damage(19, 12, "光", 0, "草"), 0)

    def test_negative_power_returns_zero(self):
        self.assertEqual(damage(19, 12, "火", -5, "草"), 0)

    def test_minimum_damage_is_one(self):
        """基础伤害被防御减到 0 时，最终伤害仍为 1。"""
        self.assertEqual(damage(1, 100, "火", 40, "草"), 1)
        self.assertEqual(damage(5, 100, "火", 40, "火"), 1)

    def test_damage_never_negative(self):
        for atk in (0, 1, 5, 19, 50):
            for dfd in (0, 7, 13, 100):
                self.assertGreaterEqual(damage(atk, dfd, "火", 40, "草"), 1)

    def test_neutral_type_multiplier_is_one(self):
        """无属性招式对任何防御方都是 1.0 倍。"""
        for dtype in ("火", "水", "草", "风", "光", "暗", "雷", "无"):
            self.assertEqual(multiplier("无", dtype), 1.0)
        base = damage(19, 12, "无", 35, "火", rng=random.Random(1))
        other = damage(19, 12, "无", 35, "草", rng=random.Random(1))
        self.assertEqual(base, other, "无属性招式不应受防御方属性影响")

    def test_atk_mod_reduces_damage(self):
        """被吼叫后 ATK ×0.75：int(19 × 0.75) = 14。"""
        normal = expected_damage(19, 12, "火", 40, "草")
        debuffed = expected_damage(19, 12, "火", 40, "草", atk_mod=0.75)
        self.assertAlmostEqual(normal, 20.8, places=6)
        self.assertAlmostEqual(debuffed, 12.8, places=6)
        self.assertLess(debuffed, normal)

    def test_formula_matches_manual_computation(self):
        """逐项手算：max(1, int(基础 × 系数 × 克制 × 浮动))。"""
        atk, dfd, power, mult = 19, 12, 40, 2.0
        base = max(0, int(atk * 1.0) - dfd / 2)
        self.assertEqual(base, 13)
        coef = power / 50.0
        self.assertEqual(coef, 0.8)
        rng_a = random.Random(7)
        rng_b = random.Random(7)
        for _ in range(50):
            roll = rng_a.uniform(0.90, 1.10)
            expect = max(1, int(base * coef * mult * roll))
            self.assertEqual(damage(atk, dfd, "火", power, "草", rng=rng_b), expect)

    def test_defense_halves_effect(self):
        """防御越高伤害越低。"""
        weak = expected_damage(19, 6, "火", 40, "草")
        strong = expected_damage(19, 12, "火", 40, "草")
        self.assertGreater(weak, strong)

    def test_power_scales_damage(self):
        low = expected_damage(19, 12, "火", 40, "草")
        high = expected_damage(19, 12, "火", 90, "草")
        self.assertAlmostEqual(high / low, 90 / 40, places=6)


class HealAmountTest(unittest.TestCase):
    """治疗量：max(min_heal, ceil(max_hp × value))。"""

    def test_heal_wave(self):
        skill = get_skill(19)
        self.assertEqual(heal_amount(skill, 34), 12)     # ceil(8.5)=9，取最小 12
        self.assertEqual(heal_amount(skill, 100), 25)    # ceil(25)=25

    def test_sanctuary(self):
        skill = get_skill(20)
        self.assertEqual(heal_amount(skill, 34), 25)     # ceil(17)=17，取最小 25
        self.assertEqual(heal_amount(skill, 100), 50)

    def test_regen(self):
        skill = get_skill(25)
        self.assertEqual(heal_amount(skill, 34), 15)     # ceil(10.2)=11，取最小 15
        self.assertEqual(heal_amount(skill, 100), 30)

    def test_matches_formula(self):
        for skill_id in (19, 20, 25):
            skill = get_skill(skill_id)
            for max_hp in (18, 34, 44, 104):
                expect = max(skill.min_heal, math.ceil(max_hp * skill.value))
                self.assertEqual(heal_amount(skill, max_hp), expect)


if __name__ == "__main__":
    unittest.main()
