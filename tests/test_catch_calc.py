"""捕捉概率测试（src/battle/catch_calc.py）。

覆盖《数值设定.md》§8：

- 8 只精灵的**满血捕捉率**与**1 HP 捕捉率**（文档表格值）；
- 概率夹取到 [0, 1]；
- try_catch 的判定语义。
"""

from __future__ import annotations

import random
import unittest

from src.battle.catch_calc import BALL_MULTIPLIER, catch_chance, try_catch
from src.data.species_data import SPECIES, stat_at

#: §8 表格：种族 ID -> (种族系数, 满血捕捉率, 1HP 捕捉率)
#: 满血率为文档精确值；1HP 率为文档的近似值（文档用 ~ 标注）。
DOC_CATCH = {
    1: ("小火狮", 0.40, 0.120, 0.39),
    2: ("水滴滴", 0.55, 0.165, 0.54),
    3: ("兔小子", 0.55, 0.165, 0.53),
    4: ("小狮鹫", 0.40, 0.120, 0.39),
    5: ("独角兽", 0.25, 0.075, 0.25),
    6: ("三头犬", 0.25, 0.075, 0.25),
    7: ("不死鸟", 0.10, 0.030, 0.10),
    8: ("闪电小子", 0.40, 0.120, 0.39),
}


class CatchChanceTest(unittest.TestCase):
    """§8 捕捉率表格。"""

    def test_ball_multiplier_is_one(self):
        self.assertEqual(BALL_MULTIPLIER, 1.0)

    def test_full_hp_chance_matches_doc(self):
        """满血捕捉率：文档值 ±0.005。"""
        for sid, (_name, coef, full_hp, _one_hp) in DOC_CATCH.items():
            hp_max = stat_at(sid, "HP", 5)
            got = catch_chance(hp_max, hp_max, coef)
            self.assertAlmostEqual(got, full_hp, delta=0.005,
                                   msg=f"{_name} 满血捕捉率不一致")

    def test_one_hp_chance_matches_doc(self):
        """1 HP 捕捉率：文档近似值 ±0.01（文档该列用 ~ 标注）。"""
        for sid, (name, coef, _full_hp, one_hp) in DOC_CATCH.items():
            hp_max = stat_at(sid, "HP", 5)
            got = catch_chance(1, hp_max, coef)
            self.assertAlmostEqual(got, one_hp, delta=0.01,
                                   msg=f"{name} 1HP 捕捉率不一致")

    def test_one_hp_chance_matches_formula(self):
        """1 HP 捕捉率严格等于 (1 - 1/hp_max × 0.7) × 系数。"""
        for sid, (name, coef, _full_hp, _one_hp) in DOC_CATCH.items():
            hp_max = stat_at(sid, "HP", 5)
            expect = (1 - (1 / hp_max) * 0.7) * coef
            got = catch_chance(1, hp_max, coef)
            self.assertAlmostEqual(got, expect, places=12, msg=f"{name}")

    def test_harder_species_have_lower_rate(self):
        """不死鸟最难抓，小火狮 / 闪电小子次之。"""
        self.assertLess(catch_chance(1, 37, 0.10), catch_chance(1, 34, 0.40))
        self.assertLess(catch_chance(1, 34, 0.40), catch_chance(1, 41, 0.55))

    def test_lower_hp_is_easier_to_catch(self):
        hp_max = stat_at(1, "HP", 5)
        rates = [catch_chance(hp, hp_max, 0.40) for hp in range(0, hp_max + 1)]
        self.assertEqual(rates, sorted(rates, reverse=True))
        self.assertGreater(rates[0], rates[-1])

    def test_chance_is_clamped(self):
        self.assertEqual(catch_chance(0, 0, 0.4), 0.0)          # hp_max 非法
        self.assertEqual(catch_chance(100, 34, 0.4), 0.0)        # 超血量 -> 夹到 0
        self.assertEqual(catch_chance(0, 34, 0.4, ball_mult=99), 1.0)  # 夹到 1

    def test_ball_multiplier_scales_rate(self):
        base = catch_chance(1, 34, 0.40)
        double = catch_chance(1, 34, 0.40, ball_mult=2.0)
        self.assertAlmostEqual(double, base * 2, places=12)


class TryCatchTest(unittest.TestCase):
    """try_catch 的判定语义。"""

    def test_deterministic_with_seeded_rng(self):
        rng = random.Random(42)
        results = [try_catch(1, 34, 0.40, rng=rng) for _ in range(200)]
        self.assertIn(True, results)
        self.assertIn(False, results)

    def test_always_success_when_chance_is_one(self):
        rng = random.Random(1)
        for _ in range(50):
            self.assertTrue(try_catch(1, 34, 10.0, ball_mult=1.0, rng=rng))

    def test_always_fail_when_chance_is_zero(self):
        rng = random.Random(1)
        for _ in range(50):
            self.assertFalse(try_catch(34, 34, 0.0, rng=rng))

    def test_empirical_rate_close_to_formula(self):
        """大样本下实测成功率接近公式值。"""
        hp_max = stat_at(2, "HP", 5)
        coef = SPECIES[2].catch_coef
        expect = catch_chance(1, hp_max, coef)
        rng = random.Random(20261023)
        hits = sum(1 for _ in range(20000)
                   if try_catch(1, hp_max, coef, rng=rng))
        self.assertAlmostEqual(hits / 20000, expect, delta=0.01)


if __name__ == "__main__":
    unittest.main()
