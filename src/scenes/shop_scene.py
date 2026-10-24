"""商店场景（批 3 / T6）。

功能
----
- **主菜单**：买入 / 卖出 / 返回；
- **买入**：5 件道具全列（《数值设定.md》§7.1），每行显示买入价与持有数；
  金币不够的行**整行置灰（色 5）**，确认键不成交并提示「金币不足」；
- **卖出**：**只列持有数量 > 0** 的道具，每行显示回收价与持有数；
  卖光之后该行自动从列表消失；
- 顶部固定显示金币，底部提示条显示操作结果。

与地图的关系
------------
商店是**压栈**进来的覆盖层（game.scenes.push(ShopScene(game, npc))），
关闭时 game.scenes.pop()，地图场景只是被 reveal 一下（resume()），
**玩家位置 / 野外刷怪状态 / 计时器全部保留**。

为什么用 push 而不是 replace
----------------------------
商店关掉以后必须回到**原来的地图、原坐标**，野外的 wanderers /
game.wild_state 一个都不能丢。replace 会把地图场景整个丢掉再重建
（战斗结束就是这么干的），会重置地图状态，所以这里必须 push / pop。

价格来源
--------
- 买入价 = item_data.get_item(id).price；
- 卖出价 = item_data.get_item(id).sell（买入价的 50%，已在 T3a 配好）。

**本模块不硬编码任何价格**，改价只需要改 src/data/item_data.py。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette, sprite_base
from src.data import item_data
from src.scenes.scene_base import Scene
from src.ui import text
from src.ui.widgets import MenuList

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 三种界面
MODE_MAIN = "main"        # 主菜单（买入 / 卖出 / 返回）
MODE_BUY = "buy"          # 买入列表
MODE_SELL = "sell"        # 卖出列表

#: 主菜单三项
MAIN_ITEMS: tuple[str, ...] = ("买入", "卖出", "返回")

# ---------------------------------------------------------------- 布局
#: 顶部标题行
HEADER_Y = 6
#: 顶部第二行提示
HINT_Y = 22

#: 主菜单：左列表 / 右详情
LEFT_X, LEFT_Y, LEFT_W, LEFT_H = 4, 34, 120, 96
RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H = 128, 34, 108, 96
#: 主菜单三行的位置
MAIN_ROW_X, MAIN_ROW_Y, MAIN_ROW_STEP = 24, 48, 24

#: 买入 / 卖出：整幅列表面板
LIST_X, LIST_Y, LIST_W, LIST_H = 4, 34, 232, 96
#: 列表行的位置
ROW_X, ROW_Y, ROW_STEP = 18, 42, 18

#: 选中道具的详情（列表面板下方）
DETAIL_Y = 134

#: 底部提示条
MSG_Y = 190
#: 提示持续的帧数
MESSAGE_FRAMES = 120

#: 卖出列表为空时的提示
EMPTY_SELL_TEXT = "没有可以卖的东西"
#: 金币不足时的提示
NO_MONEY_TEXT = "金币不足"


def _fit(s: str, max_px: int) -> str:
    """把字符串截断到不超过 max_px 像素宽（超出部分用 ... 代替）。"""
    s = str(s)
    if max_px <= 0:
        return ""
    if text.width(s) <= max_px:
        return s
    out = ""
    for ch in s:
        if text.width(out + ch) > max_px - 18:
            break
        out += ch
    return out + "..."


class ShopScene(Scene):
    """商店覆盖层。

    生命周期
    --------
    - enter()：重置界面与提示（每次进商店都是干净状态）；
    - resume()：什么都不做（状态保留）；
    - exit()：什么都不做（关商店不丢任何东西）。
    """

    def __init__(self, game, npc=None):
        super().__init__(game)
        #: 店主 NPC 数据（可选，只是显示用）
        self.npc: dict = npc if isinstance(npc, dict) else {}
        #: 当前界面
        self.mode: str = MODE_MAIN
        #: 主菜单光标
        self.main_index: int = 0
        #: 买入 / 卖出列表光标
        self.list_index: int = 0
        #: 底部提示文字 / 剩余帧数
        self.message: str = ""
        self.message_timer: int = 0

        #: 两个竖排列表
        self.main_menu = MenuList(MAIN_ROW_X, MAIN_ROW_Y, [])
        self.item_menu = MenuList(ROW_X, ROW_Y, [])

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入商店：回到主菜单，清空提示。"""
        sprite_base.bake_all()
        self.mode = MODE_MAIN
        self.main_index = 0
        self.list_index = 0
        self.message = ""
        self.message_timer = 0

    def resume(self) -> None:
        """重新回到前台：状态保留，不重置。"""

    def exit(self) -> None:
        """退出：不用清理。"""

    # ------------------------------------------------------------ 数据
    def _player(self):
        """取玩家对象（还没开局时是 None）。"""
        return getattr(self.game, "player", None)

    def _dollars(self) -> int:
        """当前金币（以 player.dollars 为准）。"""
        player = self._player()
        if player is not None:
            return int(player.dollars)
        state = getattr(self.game, "player_state", None) or {}
        return int(state.get("dollars", 0))

    def _set_dollars(self, value: int) -> None:
        """写回金币，并同步到 game.player_state["dollars"]（HUD / 存档读它）。"""
        amount = int(value)
        player = self._player()
        if player is not None:
            player.dollars = amount
        state = getattr(self.game, "player_state", None)
        if isinstance(state, dict):
            state["dollars"] = amount

    def _count(self, item_id: int) -> int:
        """背包里某种道具的数量。"""
        player = self._player()
        if player is None:
            return 0
        return int(player.item_count(item_id))

    def buy_ids(self) -> list[int]:
        """买入列表的道具 ID（全部商品，按 ID 升序）。"""
        return sorted(item_data.ITEMS.keys())

    def sell_ids(self) -> list[int]:
        """卖出列表的道具 ID（**只列持有数量 > 0** 的，按 ID 升序）。"""
        return [i for i in sorted(item_data.ITEMS.keys()) if self._count(i) > 0]

    def buy_label(self, index: int, item_id: int | None = None) -> str:
        """买入列表的一行（例：精灵球  50 金币  持有 5）。"""
        if item_id is None:
            ids = self.buy_ids()
            if not (0 <= index < len(ids)):
                return ""
            item_id = ids[index]
        item = item_data.get_item(item_id)
        return f"{item.name}  {item.price} 金币  持有 {self._count(item_id)}"

    def sell_label(self, index: int, item_id: int | None = None) -> str:
        """卖出列表的一行（例：精灵球  25 金币  持有 5）。"""
        if item_id is None:
            ids = self.sell_ids()
            if not (0 <= index < len(ids)):
                return ""
            item_id = ids[index]
        item = item_data.get_item(item_id)
        return f"{item.name}  {item.sell} 金币  持有 {self._count(item_id)}"

    # ------------------------------------------------------------ 每帧
    def update(self, inp) -> None:
        """每帧逻辑更新。"""
        self._refresh()

        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.message_timer = 0
                self.message = ""

        if inp.pressed("cancel"):
            self._on_cancel()
        elif inp.pressed("confirm"):
            self._on_confirm()
        elif self.mode == MODE_MAIN:
            if inp.pressed("up"):
                self.main_menu.move(-1)
            elif inp.pressed("down"):
                self.main_menu.move(1)
            self.main_index = self.main_menu.index
        else:
            if self.item_menu.count:
                if inp.pressed("up"):
                    self.item_menu.move(-1)
                elif inp.pressed("down"):
                    self.item_menu.move(1)
            self.list_index = self.item_menu.index

        # 帧末再刷新一次：本帧的输入可能改了界面（换页 / 买 / 卖），
        # 刷新后列表内容与光标立刻与数据一致。
        self._refresh()

    # ------------------------------------------------------------ 操作
    def _on_cancel(self) -> None:
        """取消键：列表 -> 主菜单 -> 关闭商店。"""
        if self.mode == MODE_MAIN:
            self.close()
        else:
            self.mode = MODE_MAIN
            self.list_index = 0

    def _on_confirm(self) -> None:
        """确认键：按当前界面分发。"""
        if self.mode == MODE_MAIN:
            self._confirm_main()
        elif self.mode == MODE_BUY:
            self._confirm_buy()
        else:
            self._confirm_sell()

    def _confirm_main(self) -> None:
        """主菜单确认。"""
        item = MAIN_ITEMS[self.main_index]
        if item == "买入":
            self.mode = MODE_BUY
            self.list_index = 0
        elif item == "卖出":
            self.mode = MODE_SELL
            self.list_index = 0
        else:
            self.close()

    def _confirm_buy(self) -> None:
        """买入列表确认：买 1 个当前选中的道具。"""
        ids = self.buy_ids()
        if not ids:
            self._say("没有可以买的东西")
            return
        idx = max(0, min(self.list_index, len(ids) - 1))
        self.buy(ids[idx])

    def _confirm_sell(self) -> None:
        """卖出列表确认：卖 1 个当前选中的道具。"""
        ids = self.sell_ids()
        if not ids:
            self._say(EMPTY_SELL_TEXT)
            return
        idx = max(0, min(self.list_index, len(ids) - 1))
        self.sell(ids[idx])

    # ------------------------------------------------------------ 交易
    def buy(self, item_id: int) -> bool:
        """买 1 个道具，成功返回 True。

        规则（《数值设定.md》§7）：

        - 金币不足：**不成交**，只提示「金币不足」；
        - 成交：金币 -= 买入价，背包 += 1，提示「购买了 X」。
        """
        player = self._player()
        if player is None:
            self._say("还没有开始游戏")
            return False
        item = item_data.get_item(item_id)
        dollars = self._dollars()
        if dollars < item.price:
            self._say(NO_MONEY_TEXT)
            return False
        self._set_dollars(dollars - item.price)
        player.add_item(item.id, 1)
        self._say(f"购买了{item.name}")
        return True

    def sell(self, item_id: int) -> bool:
        """卖 1 个道具，成功返回 True。

        规则（《数值设定.md》§7「商店卖出价 = 买入价的 50%」）：

        - 背包里没有：不成交，提示「没有可以卖的东西」；
        - 成交：背包 -= 1，金币 += 回收价，提示「卖出了 X」。
        """
        player = self._player()
        if player is None:
            self._say("还没有开始游戏")
            return False
        item = item_data.get_item(item_id)
        if player.item_count(item.id) <= 0:
            self._say(EMPTY_SELL_TEXT)
            return False
        player.remove_item(item.id, 1)
        self._set_dollars(self._dollars() + item.sell)
        self._say(f"卖出了{item.name}")
        return True

    def _say(self, message: str, frames: int = MESSAGE_FRAMES) -> None:
        """显示一条底部提示。"""
        self.message = message
        self.message_timer = frames

    def close(self) -> None:
        """关闭商店：弹栈回到地图场景（地图状态不变）。"""
        self.game.scenes.pop()

    # ------------------------------------------------------------ 刷新
    def _refresh(self) -> None:
        """按当前数据重建两个列表的内容。"""
        self.main_menu.items = [
            {"label": name, "x": MAIN_ROW_X, "y": MAIN_ROW_Y + i * MAIN_ROW_STEP}
            for i, name in enumerate(MAIN_ITEMS)
        ]
        self.main_index = max(0, min(self.main_index, len(MAIN_ITEMS) - 1))
        self.main_menu.index = self.main_index

        if self.mode == MODE_BUY:
            dollars = self._dollars()
            items = []
            for i, item_id in enumerate(self.buy_ids()):
                item = item_data.get_item(item_id)
                items.append({
                    "label": self.buy_label(i, item_id),
                    "x": ROW_X, "y": ROW_Y + i * ROW_STEP,
                    # 金币不够的行整行置灰（色 5），确认键不成交
                    "enabled": dollars >= item.price,
                })
            self.item_menu.items = items
        elif self.mode == MODE_SELL:
            items = []
            for i, item_id in enumerate(self.sell_ids()):
                items.append({
                    "label": self.sell_label(i, item_id),
                    "x": ROW_X, "y": ROW_Y + i * ROW_STEP,
                    "enabled": True,
                })
            self.item_menu.items = items
        else:
            self.item_menu.items = []

        if self.item_menu.count:
            self.list_index = max(0, min(self.list_index, self.item_menu.count - 1))
        else:
            self.list_index = 0
        self.item_menu.index = self.list_index

    # ------------------------------------------------------------ 绘制
    def draw(self) -> None:
        """绘制整个商店。"""
        pyxel.cls(palette.DEEP_BLUE)
        self._refresh()
        self._draw_header()
        if self.mode == MODE_MAIN:
            self._draw_main()
        else:
            self._draw_list()
        self._draw_message()

    def _panel(self, x: int, y: int, w: int, h: int) -> None:
        """画一个浅灰面板。"""
        pyxel.rect(x, y, w, h, palette.LIGHT_GRAY)
        pyxel.rectb(x, y, w, h, palette.DARK_PURPLE)

    def _draw_header(self) -> None:
        """顶部：标题 + 金币 + 一行提示。"""
        title = "商店"
        if self.npc.get("name"):
            title = f"{self.npc['name']}的店"
        text.draw(8, HEADER_Y, title, palette.YELLOW)
        money = f"金币 {self._dollars()}"
        text.draw(SCREEN_W - text.width(money) - 8, HEADER_Y, money, palette.WHITE)
        hint = self._hint_text()
        if hint:
            text.draw(8, HINT_Y, _fit(hint, SCREEN_W - 16), palette.WHITE)

    def _hint_text(self) -> str:
        """顶部第二行的提示文字。"""
        if self.mode == MODE_BUY:
            return "确认键买入，取消键返回"
        if self.mode == MODE_SELL:
            return "回收价 = 买入价 50%，确认键卖出"
        return "确认键选择，取消键离开商店"

    def _draw_main(self) -> None:
        """主菜单：左边三项，右边说明。"""
        self._panel(LEFT_X, LEFT_Y, LEFT_W, LEFT_H)
        self._panel(RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H)
        self.main_menu.draw()

        x = RIGHT_X + 4
        y = RIGHT_Y + 8
        text.draw(x, y, _fit(self.npc.get("name", "店员"), RIGHT_W - 8), palette.BLACK)
        y += 16
        text.draw(x, y, "欢迎光临", palette.BLACK)
        y += 16
        text.draw(x, y, f"金币 {self._dollars()}", palette.BLACK)
        y += 16
        text.draw(x, y, "买入价", palette.BLACK)
        text.draw(x + 48, y, "道具表", palette.BLACK)
        y += 14
        text.draw(x, y, "回收价", palette.BLACK)
        text.draw(x + 48, y, "买入价 50%", palette.BLACK)

    def _draw_list(self) -> None:
        """买入 / 卖出：整幅列表 + 下方详情。"""
        self._panel(LIST_X, LIST_Y, LIST_W, LIST_H)
        if not self.item_menu.count:
            text.draw(LIST_X + 14, LIST_Y + 30, EMPTY_SELL_TEXT, palette.BLACK)
            return
        self.item_menu.draw()
        self._draw_detail()

    def _draw_detail(self) -> None:
        """列表下方：当前选中道具的价格与说明。"""
        ids = self.buy_ids() if self.mode == MODE_BUY else self.sell_ids()
        if not ids:
            return
        idx = max(0, min(self.list_index, len(ids) - 1))
        item = item_data.get_item(ids[idx])
        x = 8
        if self.mode == MODE_BUY:
            line = f"{item.name}  买入 {item.price} 金币  回收 {item.sell} 金币"
        else:
            line = f"{item.name}  回收价 {item.sell} 金币"
        text.draw(x, DETAIL_Y, _fit(line, SCREEN_W - 16), palette.WHITE)
        text.draw(x, DETAIL_Y + 14, f"持有 {self._count(item.id)}", palette.LIGHT_GRAY)
        text.draw_wrapped(x, DETAIL_Y + 28, item.desc, SCREEN_W - 16,
                          palette.LIGHT_GRAY)

    def _draw_message(self) -> None:
        """底部提示条。"""
        if not self.message:
            return
        pyxel.rect(0, MSG_Y, SCREEN_W, SCREEN_H - MSG_Y, palette.LIGHT_GRAY)
        pyxel.rectb(0, MSG_Y, SCREEN_W, SCREEN_H - MSG_Y, palette.DARK_PURPLE)
        text.draw(6, MSG_Y + 7, _fit(self.message, SCREEN_W - 12), palette.BLACK)
