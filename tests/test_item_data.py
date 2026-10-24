"""道具与商品数据测试（src/data/item_data.py）。

覆盖《数值设定.md》§7 / §7.1 / §7.2：

- 5 件道具的名称 / 买入价 / 卖出价 / 效果 / 数值逐条相等；
- 卖出价 = 买入价的 50%（向下取整）；
- 初始背包与初始金币。
"""

from __future__ import annotations

import unittest

from src.data.item_data import (
    INITIAL_BAG,
    INITIAL_DOLLARS,
    ITEMS,
    get_item,
)

#: §7.1 商品表：ID -> (名称, 买入价, 卖出价, 效果, 数值)
DOC_ITEMS = {
    1: ("精灵球", 50, 25, "ball", 0),
    2: ("伤药", 80, 40, "heal_hp", 30),
    3: ("好伤药", 180, 90, "heal_hp", 70),
    4: ("蓝药水", 100, 50, "heal_mp", 20),
    5: ("复活草", 300, 150, "revive", 0),
}


class ItemTableTest(unittest.TestCase):
    """§7.1 商品表。"""

    def test_item_ids_are_1_to_5(self):
        self.assertEqual(sorted(ITEMS), list(range(1, 6)))

    def test_item_rows_match_doc(self):
        for item_id, (name, price, sell, effect, value) in DOC_ITEMS.items():
            item = get_item(item_id)
            self.assertEqual(item.name, name, f"道具 {item_id} 名称不一致")
            self.assertEqual(item.price, price, f"道具 {item_id} 买入价不一致")
            self.assertEqual(item.sell, sell, f"道具 {item_id} 卖出价不一致")
            self.assertEqual(item.effect, effect, f"道具 {item_id} 效果不一致")
            self.assertEqual(item.value, value, f"道具 {item_id} 数值不一致")

    def test_sell_is_half_of_price(self):
        for item_id, item in ITEMS.items():
            self.assertEqual(item.sell, item.price // 2, f"道具 {item_id} 卖出价应为买入价一半")

    def test_ball_has_zero_value(self):
        self.assertEqual(get_item(1).value, 0)

    def test_get_item_unknown_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_item(99)


class InitialStateTest(unittest.TestCase):
    """§7.2 初始背包与初始金币。"""

    def test_initial_bag(self):
        self.assertEqual(INITIAL_BAG, {1: 5, 2: 2, 4: 1})

    def test_initial_bag_value(self):
        """精灵球 ×5 + 伤药 ×2 + 蓝药水 ×1，按 §7.1 买入价合计 510。

        注：《数值设定.md》§7.2 括注写的是"价值 450"，与 §7.1 价格表算出来的
        50×5 + 80×2 + 100×1 = 510 对不上。这里**以 §7.1 价格表为准**，
        背包内容仍按 §7.2（精灵球 ×5、伤药 ×2、蓝药水 ×1）。
        """
        total = sum(get_item(i).price * n for i, n in INITIAL_BAG.items())
        self.assertEqual(total, 510)

    def test_initial_dollars(self):
        self.assertEqual(INITIAL_DOLLARS, 300)

    def test_initial_bag_items_exist(self):
        for item_id in INITIAL_BAG:
            self.assertIn(item_id, ITEMS)


if __name__ == "__main__":
    unittest.main()
