"""道具与商品数据（《数值设定.md》§7）。

本模块是**商品价格与道具效果的唯一来源**：5 件道具的买入价 / 卖出价 / 效果
全部用**字面量**写死，运行期只读不改。

道具效果分类（`effect`）
--------------------------
===== ========== ======================================================
效果     value    语义
===== ========== ======================================================
ball     0        战斗中使用，进入捕捉判定（球倍率 1.0）
heal_hp  30/70    回复 HP（不超过上限）
heal_mp  20       回复 MP（不超过上限）
revive   0        复活一只倒下的精灵并回复 50% 最大 HP
===== ========== ======================================================

卖出价一律是买入价的 50%（向下取整，《数值设定.md》§7）。

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """一件道具 / 商品。

    属性说明
    --------
    - `id`：道具 ID（1..5）。
    - `name`：道具名。
    - `price`：买入价。
    - `sell`：卖出价（买入价的 50%，向下取整）。
    - `effect`：效果类型，"ball" / "heal_hp" / "heal_mp" / "revive"。
    - `value`：效果数值（精灵球 0、伤药 30、好伤药 70、蓝药水 20、复活草 0）。
    - `desc`：界面用一句话说明。
    """

    id: int
    name: str
    price: int
    sell: int
    effect: str
    value: int = 0
    desc: str = ""


#: 5 件道具（《数值设定.md》§7.1），运行期只读
ITEMS: dict[int, Item] = {
    1: Item(1, "精灵球", 50, 25, "ball", 0, "战斗中使用，进捕捉判定。"),
    2: Item(2, "伤药", 80, 40, "heal_hp", 30, "回复 30 HP（不超过上限）。"),
    3: Item(3, "好伤药", 180, 90, "heal_hp", 70, "回复 70 HP（不超过上限）。"),
    4: Item(4, "蓝药水", 100, 50, "heal_mp", 20, "回复 20 MP（不超过上限）。"),
    5: Item(5, "复活草", 300, 150, "revive", 0, "复活一只倒下的精灵并回复 50% HP。"),
}

#: 初始背包（《数值设定.md》§7.2）：精灵球 ×5、伤药 ×2、蓝药水 ×1
INITIAL_BAG: dict[int, int] = {1: 5, 2: 2, 4: 1}

#: 初始金币（《数值设定.md》§7）
INITIAL_DOLLARS: int = 300


def get_item(item_id: int) -> Item:
    """按 ID 取道具定义；不存在时抛 KeyError。"""
    try:
        return ITEMS[item_id]
    except KeyError:
        raise KeyError(f"没有编号为 {item_id} 的道具，可用：{sorted(ITEMS)}") from None


def sell_price(item_id: int) -> int:
    """取道具卖出价（买入价的 50%，向下取整）。"""
    return get_item(item_id).sell
