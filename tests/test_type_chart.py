"""属性克制表测试（src/battle/type_chart.py）。

覆盖《数值设定.md》§2：8×8 = **64 格**逐格相等，"无" 整行整列恒 1.0。
"""

from __future__ import annotations

import unittest

from src.battle.type_chart import (
    NEUTRAL_TYPE,
    TYPES,
    TYPE_CHART,
    multiplier,
)

#: §2 克制表（行 = 攻击方属性，列 = 防御方属性）
DOC_CHART = {
    "火": {"火": 1.0, "水": 0.5, "草": 2.0, "风": 1.0, "光": 1.0, "暗": 1.0, "雷": 1.0, "无": 1.0},
    "水": {"火": 2.0, "水": 1.0, "草": 0.5, "风": 1.0, "光": 1.0, "暗": 1.0, "雷": 1.0, "无": 1.0},
    "草": {"火": 0.5, "水": 2.0, "草": 1.0, "风": 1.0, "光": 1.0, "暗": 1.0, "雷": 1.0, "无": 1.0},
    "风": {"火": 1.0, "水": 1.0, "草": 2.0, "风": 1.0, "光": 1.0, "暗": 1.0, "雷": 0.5, "无": 1.0},
    "光": {"火": 1.0, "水": 1.0, "草": 1.0, "风": 1.0, "光": 0.5, "暗": 2.0, "雷": 1.0, "无": 1.0},
    "暗": {"火": 1.0, "水": 1.0, "草": 1.0, "风": 1.0, "光": 2.0, "暗": 0.5, "雷": 1.0, "无": 1.0},
    "雷": {"火": 1.0, "水": 2.0, "草": 1.0, "风": 0.5, "光": 1.0, "暗": 1.0, "雷": 1.0, "无": 1.0},
    "无": {"火": 1.0, "水": 1.0, "草": 1.0, "风": 1.0, "光": 1.0, "暗": 1.0, "雷": 1.0, "无": 1.0},
}


class TypeChartTest(unittest.TestCase):
    """§2 克制表。"""

    def test_types_tuple(self):
        self.assertEqual(TYPES, ("火", "水", "草", "风", "光", "暗", "雷"))

    def test_neutral_type(self):
        self.assertEqual(NEUTRAL_TYPE, "无")

    def test_chart_has_8_rows_and_8_cols(self):
        self.assertEqual(len(TYPE_CHART), 8)
        for row in TYPE_CHART.values():
            self.assertEqual(len(row), 8)

    def test_all_64_cells_match_doc(self):
        for atk, row in DOC_CHART.items():
            for dfd, expect in row.items():
                self.assertAlmostEqual(
                    multiplier(atk, dfd), expect,
                    msg=f"§2 {atk} → {dfd} 克制系数不一致",
                )

    def test_neutral_row_and_column_are_all_one(self):
        for col in DOC_CHART["无"]:
            self.assertEqual(TYPE_CHART["无"][col], 1.0, f"无 → {col}")
        for row in TYPE_CHART:
            self.assertEqual(TYPE_CHART[row]["无"], 1.0, f"{row} → 无")

    def test_supereffective_and_resist_pairs(self):
        self.assertEqual(multiplier("火", "草"), 2.0)
        self.assertEqual(multiplier("水", "火"), 2.0)
        self.assertEqual(multiplier("草", "水"), 2.0)
        self.assertEqual(multiplier("风", "草"), 2.0)
        self.assertEqual(multiplier("光", "暗"), 2.0)
        self.assertEqual(multiplier("暗", "光"), 2.0)
        self.assertEqual(multiplier("雷", "水"), 2.0)
        self.assertEqual(multiplier("火", "水"), 0.5)
        self.assertEqual(multiplier("风", "雷"), 0.5)

    def test_same_type_multipliers(self):
        """§2 原表：火/水/草/风/雷 同属性为 1.0，光与暗同属性是 0.5。"""
        for type_name in ("火", "水", "草", "风", "雷"):
            self.assertEqual(multiplier(type_name, type_name), 1.0)
        self.assertEqual(multiplier("光", "光"), 0.5)
        self.assertEqual(multiplier("暗", "暗"), 0.5)

    def test_unknown_type_raises_keyerror(self):
        with self.assertRaises(KeyError):
            multiplier("土", "火")
        with self.assertRaises(KeyError):
            multiplier("火", "土")

    def test_documented_pairs_match_doc(self):
        """文档里明确列出的克制 / 抵抗关系（注意：整表并非严格对称）。"""
        self.assertEqual(multiplier("火", "草"), 2.0)
        self.assertEqual(multiplier("草", "火"), 0.5)
        self.assertEqual(multiplier("水", "火"), 2.0)
        self.assertEqual(multiplier("火", "水"), 0.5)
        self.assertEqual(multiplier("草", "水"), 2.0)
        self.assertEqual(multiplier("水", "草"), 0.5)
        self.assertEqual(multiplier("光", "暗"), 2.0)
        self.assertEqual(multiplier("暗", "光"), 2.0)
        self.assertEqual(multiplier("雷", "水"), 2.0)
        self.assertEqual(multiplier("水", "雷"), 1.0)
        self.assertEqual(multiplier("风", "雷"), 0.5)
        self.assertEqual(multiplier("雷", "风"), 0.5)


if __name__ == "__main__":
    unittest.main()
