"""菜单场景（批 3 / T5）。

功能
----
- **主菜单**五项：精灵 / 仓库 / 道具 / 存档 / 返回；
- **精灵**：看队伍、查详情、调换顺序（confirm 选中一只 -> 再选一只 -> 交换）；
- **仓库**：队伍与仓库互相搬运（←→ 切页签，↑↓ 选精灵，confirm 移动）；
- **道具**：看背包；伤药 / 好伤药 / 蓝药水 / 复活草要先选精灵才能用；
- **存档**：写入 saves/save1.json 并提示结果。

与地图的关系
------------
菜单是**压栈**进来的覆盖层（``scenes.push(MenuScene(game))``），
关闭时 ``scenes.pop()``，地图场景只是被 reveal 一下（``resume()``），
**位置 / 野外刷怪状态 / 计时器全部保留**。

布局（240x216）
---------------
- 顶部：标题 + 金币；
- 左侧浅灰面板：竖排列表（▶ 黄色光标）；
- 右侧浅灰面板：详情；
- 底部：提示条。

**仓库界面**多一行页签（队伍 / 仓库），面板整体下移 10px；
仓库没有上限，名单超过一屏时自动滚动。
"""

from __future__ import annotations

import pyxel

from src.assets_gen import palette, sprite_base
from src.data import item_data, skill_data
from src.model import save_io
from src.model.player import PARTY_LIMIT, PARTY_MIN
from src.scenes.scene_base import Scene
from src.ui import sound, text
from src.ui.widgets import MenuList, draw_bar

#: 画面尺寸（与 main.py 锁定值一致）
SCREEN_W = 240
SCREEN_H = 216

#: 主菜单五项
MAIN_ITEMS: tuple[str, ...] = ("精灵", "仓库", "道具", "存档", "返回")

#: 菜单的几种模式
MODE_MAIN = "main"        # 主菜单
MODE_PARTY = "party"      # 队伍列表
MODE_BAG = "bag"          # 背包列表
MODE_TARGET = "target"    # 选精灵（用道具时）
MODE_STORAGE = "storage"  # 仓库（队伍 <-> 仓库 双页签）

#: 仓库界面的两个页签
TAB_PARTY = "party"       # 队伍页签
TAB_STORE = "store"       # 仓库页签

#: 存档位名字（显示用）
SAVE_SLOT_NAME = "存档 1"

# ---------------------------------------------------------------- 布局
HEADER_Y = 8              # 顶部标题
HINT_Y = 24               # 顶部第二行提示

#: 左侧列表面板
LEFT_X, LEFT_Y, LEFT_W, LEFT_H = 0, 30, 128, 156
#: 右侧详情面板
RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H = 128, 30, 112, 156
#: 面板内边距
PAD = 4

#: 列表项坐标
LIST_X, LIST_Y, LIST_STEP = 12, 38, 18
MAIN_X, MAIN_Y, MAIN_STEP = 30, 54, 24

#: 底部提示条
MSG_Y = 190

#: 仓库界面：页签行（占掉顶部第二行 HINT_Y 的位置）
TAB_Y = HINT_Y
#: 仓库界面：左侧列表面板（比菜单矮一行，给页签让位）
DEPOT_LEFT_X, DEPOT_LEFT_Y, DEPOT_LEFT_W, DEPOT_LEFT_H = 0, 40, 128, 146
#: 仓库界面：右侧详情面板
DEPOT_RIGHT_X, DEPOT_RIGHT_Y, DEPOT_RIGHT_W, DEPOT_RIGHT_H = 128, 40, 112, 146
#: 仓库界面：列表项坐标与行距
DEPOT_LIST_X, DEPOT_LIST_Y, DEPOT_LIST_STEP = 12, 50, 18
#: 仓库界面：一屏显示几行（仓库无上限，要能滚动）
DEPOT_VISIBLE_ROWS = 7

#: 仓库界面底部默认提示（没有新消息时显示）
DEPOT_HINT = "←→换页签 ↑↓选精灵 Z移动 X返回"

#: 仓库界面拒绝移动时的提示
MSG_PARTY_FULL = "队伍已满，请先移出一只"
MSG_PARTY_MIN = "队伍至少要保留一只"

#: 提示信息持续的帧数（240 帧 @60fps = 4 秒，与 120 帧 @30fps 一致）
MESSAGE_FRAMES = 240


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


class MenuScene(Scene):
    """菜单覆盖层。

    生命周期
    --------
    - ``enter()``：重置光标与提示（每次打开菜单都是干净状态）；
    - ``resume()``：什么都不做（状态保留）；
    - ``exit()``：什么都不做（关菜单不丢任何东西）。
    """

    def __init__(self, game):
        super().__init__(game)
        #: 当前模式
        self.mode: str = MODE_MAIN
        #: 主菜单光标
        self.main_index: int = 0
        #: 队伍列表光标
        self.party_index: int = 0
        #: 背包列表光标
        self.bag_index: int = 0
        #: 选目标光标
        self.target_index: int = 0
        #: 调换顺序：已选中的那只（None = 没在调换）
        self.swap_from: int | None = None
        #: 等待选目标的道具 ID
        self.pending_item: int | None = None
        #: 底部提示文字 / 剩余帧数
        self.message: str = ""
        self.message_timer: int = 0
        #: 仓库界面当前页签（队伍 / 仓库）
        self.storage_tab: str = TAB_PARTY

        #: 三个竖排列表
        self.main_menu = MenuList(MAIN_X, MAIN_Y, [])
        self.party_menu = MenuList(LIST_X, LIST_Y, [])
        self.bag_menu = MenuList(LIST_X, LIST_Y, [])
        self.target_menu = MenuList(LIST_X, LIST_Y, [])
        #: 仓库界面的两个列表
        self.storage_party_menu = MenuList(DEPOT_LIST_X, DEPOT_LIST_Y, [])
        self.storage_box_menu = MenuList(DEPOT_LIST_X, DEPOT_LIST_Y, [])

    # ------------------------------------------------------------ 生命周期
    def enter(self, **kwargs) -> None:
        """进入菜单：重置光标与提示。"""
        sprite_base.bake_all()
        self.mode = MODE_MAIN
        self.main_index = 0
        self.party_index = 0
        self.bag_index = 0
        self.target_index = 0
        self.swap_from = None
        self.pending_item = None
        self.message = ""
        self.message_timer = 0
        self.storage_tab = TAB_PARTY

    def resume(self) -> None:
        """重新回到前台：状态保留，不重置。"""

    def exit(self) -> None:
        """退出：不用清理（存档由「存档」菜单项单独触发）。"""

    # ------------------------------------------------------------ 数据
    def _player(self):
        """取玩家对象（还没开局时是 None）。"""
        return getattr(self.game, "player", None)

    def _party(self) -> list:
        """队伍列表（副本，元素是同一只精灵对象）。"""
        player = self._player()
        return list(player.party) if player is not None else []

    def _storage(self) -> list:
        """仓库列表。"""
        player = self._player()
        return list(player.storage) if player is not None else []

    def _bag_items(self) -> list[int]:
        """背包里的道具 ID（按 ID 升序）。"""
        player = self._player()
        if player is None:
            return []
        return sorted(player.bag.keys())

    def _dollars(self) -> int:
        """当前金币。"""
        player = self._player()
        if player is not None:
            return int(player.dollars)
        state = getattr(self.game, "player_state", None) or {}
        return int(state.get("dollars", 0))

    # ------------------------------------------------------------ 文本
    def party_label(self, index: int, creature=None) -> str:
        """队伍列表的一行（例："1. 小火狮 Lv5 34/34"）。"""
        party = self._party()
        if creature is None:
            if not (0 <= index < len(party)):
                return ""
            creature = party[index]
        raw = (f"{index + 1}. {creature.display_name} Lv{creature.level} "
               f"{creature.hp}/{creature.hp_max}")
        return _fit(raw, LEFT_W - LIST_X - 2)

    def depot_party_label(self, index: int, creature=None) -> str:
        """仓库界面「队伍」页签的一行（和 storage_label 同样的格式）。"""
        party = self._party()
        if creature is None:
            if not (0 <= index < len(party)):
                return ""
            creature = party[index]
        raw = (f"{index + 1}. {creature.display_name} Lv{creature.level} "
               f"{creature.hp}/{creature.hp_max}")
        return _fit(raw, DEPOT_LEFT_W - DEPOT_LIST_X - 2)

    def storage_label(self, index: int, creature=None) -> str:
        """仓库列表的一行（例："1. 小火狮 Lv5 34/34"）。"""
        storage = self._storage()
        if creature is None:
            if not (0 <= index < len(storage)):
                return ""
            creature = storage[index]
        raw = (f"{index + 1}. {creature.display_name} Lv{creature.level} "
               f"{creature.hp}/{creature.hp_max}")
        # 和普通队伍列表用同一个宽度上限，行为保持一致
        return _fit(raw, DEPOT_LEFT_W - DEPOT_LIST_X - 2)

    def bag_label(self, index: int, item_id: int | None = None) -> str:
        """背包列表的一行（例："精灵球 x5"）。"""
        player = self._player()
        if player is None:
            return ""
        if item_id is None:
            ids = self._bag_items()
            if not (0 <= index < len(ids)):
                return ""
            item_id = ids[index]
        item = item_data.get_item(item_id)
        return f"{item.name} x{player.item_count(item_id)}"

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
            return
        if inp.pressed("confirm"):
            self._on_confirm()
            return

        if self.mode == MODE_MAIN:
            before = self.main_menu.index
            if inp.pressed("up"):
                self.main_menu.move(-1)
            elif inp.pressed("down"):
                self.main_menu.move(1)
            if self.main_menu.index != before:
                sound.play_sfx("cursor")
            self.main_index = self.main_menu.index
        elif self.mode in (MODE_PARTY, MODE_TARGET):
            menu = self.party_menu if self.mode == MODE_PARTY else self.target_menu
            before = menu.index
            if menu.count:
                if inp.pressed("up"):
                    menu.move(-1)
                elif inp.pressed("down"):
                    menu.move(1)
            if menu.index != before:
                sound.play_sfx("cursor")
            if self.mode == MODE_PARTY:
                self.party_index = menu.index
            else:
                self.target_index = menu.index
        elif self.mode == MODE_BAG:
            before = self.bag_menu.index
            if self.bag_menu.count:
                if inp.pressed("up"):
                    self.bag_menu.move(-1)
                elif inp.pressed("down"):
                    self.bag_menu.move(1)
            if self.bag_menu.index != before:
                sound.play_sfx("cursor")
            self.bag_index = self.bag_menu.index
        elif self.mode == MODE_STORAGE:
            self._update_storage(inp)

    # ------------------------------------------------------------ 仓库界面
    def _update_storage(self, inp) -> None:
        """仓库界面：←→ 切页签，↑↓ 移光标。"""
        if inp.pressed("left"):
            self.storage_tab = TAB_PARTY
            self._clamp_cursors()
            sound.play_sfx("cursor")
        elif inp.pressed("right"):
            self.storage_tab = TAB_STORE
            self._clamp_cursors()
            sound.play_sfx("cursor")
        else:
            menu = self._storage_menu()
            if menu.count:
                before = menu.index
                if inp.pressed("up"):
                    menu.move(-1)
                elif inp.pressed("down"):
                    menu.move(1)
                if menu.index != before:
                    sound.play_sfx("cursor")

    def _storage_menu(self) -> MenuList:
        """当前页签对应的列表（两个页签各一个 MenuList，光标互不干扰）。"""
        return (self.storage_party_menu if self.storage_tab == TAB_PARTY
                else self.storage_box_menu)

    @property
    def storage_index(self) -> int:
        """仓库界面**当前页签**的光标位置（只读）。"""
        return self._storage_menu().index

    def _clamp_cursors(self) -> None:
        """把两个页签的光标都夹到各自列表范围内。"""
        for menu, items in ((self.storage_party_menu, self._party()),
                             (self.storage_box_menu, self._storage())):
            menu.index = max(0, min(menu.index, max(0, len(items) - 1)))

    def _on_cancel(self) -> None:
        """取消键：返回上一级 / 关闭菜单。"""
        sound.play_sfx("cancel")
        if self.mode == MODE_MAIN:
            self.close()
        elif self.mode == MODE_PARTY:
            if self.swap_from is not None:
                self.swap_from = None
                self._say("已取消交换")
            else:
                self.mode = MODE_MAIN
        elif self.mode == MODE_BAG:
            self.mode = MODE_MAIN
        elif self.mode == MODE_TARGET:
            self.pending_item = None
            self.mode = MODE_BAG
        elif self.mode == MODE_STORAGE:
            self.mode = MODE_MAIN

    def _on_confirm(self) -> None:
        """确认键：按当前模式分发。"""
        sound.play_sfx("confirm")
        if self.mode == MODE_MAIN:
            self._confirm_main()
        elif self.mode == MODE_PARTY:
            self._confirm_party()
        elif self.mode == MODE_BAG:
            self._confirm_bag()
        elif self.mode == MODE_TARGET:
            self._confirm_target()
        elif self.mode == MODE_STORAGE:
            self._confirm_storage()

    def _confirm_main(self) -> None:
        """主菜单确认。"""
        item = MAIN_ITEMS[self.main_index]
        if item == "精灵":
            self.mode = MODE_PARTY
            self.party_index = 0
            self.party_menu.index = 0
            self.swap_from = None
        elif item == "仓库":
            self.mode = MODE_STORAGE
            self.storage_tab = TAB_PARTY
            self._clamp_cursors()
        elif item == "道具":
            self.mode = MODE_BAG
            self.bag_index = 0
            self.bag_menu.index = 0
        elif item == "存档":
            self.do_save()
        else:
            self.close()

    def _confirm_party(self) -> None:
        """队伍列表确认：第一次选中，第二次交换。"""
        party = self._party()
        if not party:
            self._say("队伍里没有精灵")
            return
        if self.swap_from is None:
            self.swap_from = self.party_index
            self._say(f"选择要和「{party[self.party_index].display_name}」交换的精灵")
            return
        if self.swap_from == self.party_index:
            self.swap_from = None
            self._say("已取消交换")
            return
        self.swap_party(self.swap_from, self.party_index)
        self.swap_from = None
        self._say("已交换位置")

    def _confirm_storage(self) -> None:
        """仓库界面确认：把选中的精灵在队伍与仓库之间搬一下。

        - 「队伍」页签：队伍 -> 仓库（队伍只剩一只时拒绝）；
        - 「仓库」页签：仓库 -> 队伍（队伍已满 6 只时拒绝）。

        真正的规则在 Player.move_to_storage / Player.move_to_party（数据层），
        这里只负责调用与提示。
        """
        if self.storage_tab == TAB_PARTY:
            self._move_party_to_storage()
        else:
            self._move_storage_to_party()

    def _move_party_to_storage(self) -> bool:
        """把队伍里选中的那只移进仓库。"""
        party = self._party()
        if not party:
            self._say("队伍里没有精灵")
            return False
        index = max(0, min(self.storage_party_menu.index, len(party) - 1))
        player = self._player()
        if player is None:
            self._say("还没有开始游戏")
            return False
        if len(party) <= PARTY_MIN:
            self._say(MSG_PARTY_MIN)
            return False
        name = party[index].display_name
        if not player.move_to_storage(index):
            self._say(MSG_PARTY_MIN)
            return False
        self._say(f"{name} 移到了仓库")
        self._clamp_cursors()
        return True

    def _move_storage_to_party(self) -> bool:
        """把仓库里选中的那只移进队伍。"""
        storage = self._storage()
        if not storage:
            self._say("仓库是空的")
            return False
        index = max(0, min(self.storage_box_menu.index, len(storage) - 1))
        player = self._player()
        if player is None:
            self._say("还没有开始游戏")
            return False
        if len(player.party) >= PARTY_LIMIT:
            self._say(MSG_PARTY_FULL)
            return False
        name = storage[index].display_name
        if not player.move_to_party(index):
            self._say(MSG_PARTY_FULL)
            return False
        self._say(f"{name} 移到了队伍")
        self._clamp_cursors()
        return True

    def swap_party(self, a: int, b: int) -> bool:
        """交换队伍里第 a 只与第 b 只的位置（成功返回 True）。"""
        player = self._player()
        if player is None:
            return False
        party = player.party
        if not (0 <= a < len(party)) or not (0 <= b < len(party)):
            return False
        party[a], party[b] = party[b], party[a]
        return True

    def _confirm_bag(self) -> None:
        """背包列表确认：能用的道具进选目标界面。"""
        ids = self._bag_items()
        if not ids:
            self._say("背包是空的")
            return
        item_id = ids[self.bag_index]
        item = item_data.get_item(item_id)
        if item.effect == "ball":
            self._say("现在不能使用")
            return
        player = self._player()
        if player is None or player.item_count(item_id) <= 0:
            self._say(f"没有{item.name}了")
            return
        self.pending_item = item_id
        self.target_index = 0
        self.target_menu.index = 0
        self.mode = MODE_TARGET

    def _confirm_target(self) -> None:
        """选目标界面确认：对选中的精灵使用道具。"""
        item_id = self.pending_item
        if item_id is None:
            self.mode = MODE_BAG
            return
        self._say(self.use_item(item_id, self.target_index))
        self.pending_item = None
        self.mode = MODE_BAG

    def use_item(self, item_id: int, target_index: int) -> str:
        """对队伍第 target_index 只精灵使用道具，返回提示文字。

    规则（《数值设定.md》§7.1 / §9）：

    - 伤药 / 好伤药：回复 30 / 70 HP（不超上限）；
    - 蓝药水：回复 20 MP（不超上限）；
    - 复活草：只对**已倒下**的精灵生效（活着的用不了）；
    - 精灵球：只能在战斗里用，这里返回「现在不能使用」；
    - 背包里没有 / 已经满血满蓝：**不消耗**道具，只给提示。
    """
        player = self._player()
        if player is None:
            return "还没有开始游戏"
        party = player.party
        if not (0 <= target_index < len(party)):
            return "没有可以使用的精灵"
        try:
            item = item_data.get_item(item_id)
        except KeyError:
            return "没有这个道具"
        if player.item_count(item_id) <= 0:
            return f"没有{item.name}了"
        creature = party[target_index]

        if item.effect == "heal_hp":
            healed = creature.heal_hp(item.value)
            if healed <= 0:
                return f"{creature.display_name} 的 HP 已经满了"
            player.remove_item(item_id, 1)
            return f"{creature.display_name} 回复了 {healed} 点 HP"

        if item.effect == "heal_mp":
            restored = creature.heal_mp(item.value)
            if restored <= 0:
                return f"{creature.display_name} 的 MP 已经满了"
            player.remove_item(item_id, 1)
            return f"{creature.display_name} 回复了 {restored} 点 MP"

        if item.effect == "revive":
            if not creature.fainted:
                return "现在不能使用"
            creature.revive()
            player.remove_item(item_id, 1)
            return f"{creature.display_name} 复活了！"

        return "现在不能使用"

    def do_save(self) -> bool:
        """写存档（成功返回 True，提示文字会自动显示）。"""
        ok = save_io.save_game(self.game)
        self._say(f"已保存到 {SAVE_SLOT_NAME}" if ok else "保存失败")
        return ok

    def _say(self, message: str, frames: int = MESSAGE_FRAMES) -> None:
        """显示一条底部提示。"""
        self.message = message
        self.message_timer = frames

    def close(self) -> None:
        """关闭菜单：弹栈回到地图场景（地图状态不变）。"""
        self.game.scenes.pop()

    # ------------------------------------------------------------ 刷新
    def _refresh(self) -> None:
        """按当前数据重建三个列表的内容。"""
        self.main_menu.items = [
            {"label": name, "x": MAIN_X, "y": MAIN_Y + i * MAIN_STEP}
            for i, name in enumerate(MAIN_ITEMS)
        ]
        party = self._party()
        storage = self._storage()
        items = [
            {"label": self.party_label(i, c), "x": LIST_X, "y": LIST_Y + i * LIST_STEP}
            for i, c in enumerate(party)
        ]
        self.party_menu.items = items
        self.target_menu.items = list(items)
        ids = self._bag_items()
        self.bag_menu.items = [
            {"label": self.bag_label(i, iid), "x": LIST_X, "y": LIST_Y + i * LIST_STEP}
            for i, iid in enumerate(ids)
        ]

        self.main_index = max(0, min(self.main_index, len(MAIN_ITEMS) - 1))
        self.main_menu.index = self.main_index
        if party:
            self.party_index = max(0, min(self.party_index, len(party) - 1))
            self.target_index = max(0, min(self.target_index, len(party) - 1))
        else:
            self.party_index = 0
            self.target_index = 0
        self.party_menu.index = self.party_index
        self.target_menu.index = self.target_index
        self.bag_index = max(0, min(self.bag_index, max(0, len(ids) - 1)))
        self.bag_menu.index = self.bag_index

        # 仓库界面：两个页签各一个列表（队伍 / 仓库）
        self.storage_party_menu.items = [
            {"label": self.depot_party_label(i, c),
             "x": DEPOT_LIST_X, "y": DEPOT_LIST_Y + i * DEPOT_LIST_STEP}
            for i, c in enumerate(party)
        ]
        self.storage_box_menu.items = [
            {"label": self.storage_label(i, c),
             "x": DEPOT_LIST_X, "y": DEPOT_LIST_Y + i * DEPOT_LIST_STEP}
            for i, c in enumerate(storage)
        ]
        self._clamp_cursors()

    # ------------------------------------------------------------ 绘制
    def draw(self) -> None:
        """绘制整个菜单。"""
        pyxel.cls(palette.DEEP_BLUE)
        self._refresh()
        self._draw_header()
        if self.mode == MODE_MAIN:
            self._draw_main()
        elif self.mode == MODE_BAG:
            self._draw_bag()
        elif self.mode == MODE_STORAGE:
            self._draw_storage()
        else:
            self._draw_party()
        self._draw_message()

    def _panel(self, x: int, y: int, w: int, h: int) -> None:
        """画一个浅灰面板。"""
        pyxel.rect(x, y, w, h, palette.LIGHT_GRAY)
        pyxel.rectb(x, y, w, h, palette.DARK_PURPLE)

    def _draw_header(self) -> None:
        """顶部：标题 + 金币 + 一行提示。"""
        titles = {
            MODE_MAIN: "菜单",
            MODE_PARTY: "精灵",
            MODE_BAG: "道具",
            MODE_TARGET: "选择精灵",
            MODE_STORAGE: "仓库",
        }
        text.draw(8, HEADER_Y, titles.get(self.mode, "菜单"), palette.YELLOW)
        money = f"金币 {self._dollars()}"
        text.draw(SCREEN_W - text.width(money) - 8, HEADER_Y, money, palette.WHITE)
        hint = self._hint_text()
        if hint:
            text.draw(8, HINT_Y, _fit(hint, SCREEN_W - 16), palette.WHITE)

    def _hint_text(self) -> str:
        """顶部第二行的提示文字。"""
        if self.mode == MODE_TARGET and self.pending_item is not None:
            item = item_data.get_item(self.pending_item)
            return f"给「{item.name}」选择目标"
        if self.mode == MODE_PARTY and self.swap_from is not None:
            return "选择要交换的精灵"
        return ""

    def _draw_main(self) -> None:
        """主菜单：左边四项，右边说明。"""
        self._panel(LEFT_X, LEFT_Y, LEFT_W, LEFT_H)
        self._panel(RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H)
        self.main_menu.draw()
        y = RIGHT_Y + 10
        for line in self._main_detail():
            if line:
                text.draw(RIGHT_X + PAD, y, _fit(line, RIGHT_W - PAD * 2), palette.BLACK)
            y += 16

    def _main_detail(self) -> list[str]:
        """主菜单右侧的说明文字。"""
        item = MAIN_ITEMS[self.main_index]
        party = self._party()
        storage = self._storage()
        bag = self._bag_items()
        if item == "精灵":
            return ["队伍", f"{len(party)} 只", "", "仓库", f"{len(storage)} 只",
                    "", "确认键查看精灵"]
        if item == "仓库":
            return ["队伍", f"{len(party)}/{PARTY_LIMIT} 只", "", "仓库",
                    f"{len(storage)} 只", "", "确认键管理仓库"]
        if item == "道具":
            return ["背包", f"{len(bag)} 种", "", "确认键使用道具"]
        if item == "存档":
            exists = save_io.has_save()
            return [SAVE_SLOT_NAME, "", "状态", "已保存" if exists else "还没有存档",
                    "", "确认键写入存档"]
        return ["关闭菜单", "", "确认键回到地图"]

    def _draw_party(self) -> None:
        """队伍 / 选目标：左边列表，右边精灵详情。"""
        self._panel(LEFT_X, LEFT_Y, LEFT_W, LEFT_H)
        self._panel(RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H)
        if self.mode == MODE_TARGET:
            self.target_menu.draw()
        else:
            self.party_menu.draw()
        self._draw_creature_detail()

    def _draw_creature_detail(self) -> None:
        """右侧：选中精灵的 HP / MP / 三围 / 技能。"""
        party = self._party()
        if not party:
            text.draw(RIGHT_X + PAD, RIGHT_Y + 10, "没有精灵", palette.BLACK)
            return
        idx = self.target_index if self.mode == MODE_TARGET else self.party_index
        if not (0 <= idx < len(party)):
            idx = 0
        c = party[idx]
        x = RIGHT_X + PAD

        text.draw(x, RIGHT_Y + 6, _fit(c.display_name, 60), palette.BLACK)
        lv = f"Lv{c.level}"
        text.draw(RIGHT_X + RIGHT_W - PAD - text.width(lv), RIGHT_Y + 6, lv, palette.BLACK)

        hp_ratio = (c.hp / c.hp_max) if c.hp_max else 0.0
        draw_bar(x, RIGHT_Y + 24, 90, 5, hp_ratio, palette.RED, palette.LIGHT_GREEN)
        pyxel.text(x, RIGHT_Y + 32, f"{c.hp}/{c.hp_max}", palette.BLACK)

        mp_ratio = (c.mp / c.mp_max) if c.mp_max else 0.0
        draw_bar(x, RIGHT_Y + 46, 60, 4, mp_ratio, palette.DEEP_BLUE, palette.LIGHT_BLUE)
        pyxel.text(x, RIGHT_Y + 52, f"{c.mp}/{c.mp_max}", palette.BLACK)

        text.draw(x, RIGHT_Y + 68, f"攻{c.attack} 防{c.defense} 速{c.speed}",
                  palette.BLACK)

        text.draw(x, RIGHT_Y + 86, "技能", palette.BLACK)
        y = RIGHT_Y + 102
        for skill_id in c.skills[:4]:
            skill = skill_data.get_skill(skill_id)
            text.draw(x, y, f"{skill.name} MP{skill.mp}", palette.BLACK)
            y += 13

    def _draw_bag(self) -> None:
        """背包：左边列表，右边道具说明。"""
        self._panel(LEFT_X, LEFT_Y, LEFT_W, LEFT_H)
        self._panel(RIGHT_X, RIGHT_Y, RIGHT_W, RIGHT_H)
        self.bag_menu.draw()

        ids = self._bag_items()
        if not ids:
            text.draw(RIGHT_X + PAD, RIGHT_Y + 10, "背包是空的", palette.BLACK)
            return
        idx = max(0, min(self.bag_index, len(ids) - 1))
        item = item_data.get_item(ids[idx])
        player = self._player()
        count = player.item_count(ids[idx]) if player is not None else 0
        x = RIGHT_X + PAD
        text.draw(x, RIGHT_Y + 6, item.name, palette.BLACK)
        text.draw(x, RIGHT_Y + 24, f"数量 x{count}", palette.BLACK)
        text.draw_wrapped(x, RIGHT_Y + 46, item.desc, RIGHT_W - PAD * 2, palette.BLACK)

    # ------------------------------------------------------------ 仓库界面
    def _draw_storage(self) -> None:
        """仓库界面：页签 + 左侧名单 + 右侧详情。"""
        self._panel(DEPOT_LEFT_X, DEPOT_LEFT_Y, DEPOT_LEFT_W, DEPOT_LEFT_H)
        self._panel(DEPOT_RIGHT_X, DEPOT_RIGHT_Y, DEPOT_RIGHT_W, DEPOT_RIGHT_H)
        self._draw_storage_tabs()

        menu = self._storage_menu()
        rows = self._storage_rows()
        if not rows:
            text.draw(DEPOT_LIST_X, DEPOT_LIST_Y, "（这里是空的）",
                      palette.DARK_PURPLE)
        else:
            cursor = max(0, min(self.storage_index, len(menu.items) - 1))
            for row, index in enumerate(rows):
                item = menu.items[index]
                px = DEPOT_LIST_X
                py = DEPOT_LIST_Y + row * DEPOT_LIST_STEP
                color = (palette.BLACK if index == cursor
                         else palette.DARK_PURPLE)
                text.draw(px, py, str(item.get("label", "")), color)
                if index == cursor:
                    pyxel.tri(px - 9, py + 1, px - 9, py + 11, px - 2, py + 6,
                              palette.YELLOW)
        self._draw_storage_detail()

    def _draw_storage_tabs(self) -> None:
        """页签行：「队伍」和「仓库」，当前页签高亮。"""
        x = 8
        for tab, name in ((TAB_PARTY, "队伍"), (TAB_STORE, "仓库")):
            active = (tab == self.storage_tab)
            color = palette.YELLOW if active else palette.WHITE
            text.draw(x, TAB_Y, name, color)
            if active:
                # 当前页签下面画一条黄色下划线
                w = text.width(name)
                pyxel.rect(x, TAB_Y + 13, w, 1, palette.YELLOW)
            x += text.width(name) + 16
        count = len(self._party()) if self.storage_tab == TAB_PARTY else len(self._storage())
        info = f"{count} 只"
        text.draw(SCREEN_W - text.width(info) - 8, TAB_Y, info, palette.WHITE)

    def _storage_rows(self) -> list[int]:
        """当前页签要显示的行（列表下标），超过一屏就滚动。"""
        total = len(self._storage_items())
        if total == 0:
            return []
        index = max(0, min(self.storage_index, total - 1))
        top = 0
        if total > DEPOT_VISIBLE_ROWS:
            top = max(0, min(index - DEPOT_VISIBLE_ROWS // 2,
                          total - DEPOT_VISIBLE_ROWS))
        return list(range(top, min(top + DEPOT_VISIBLE_ROWS, total)))

    def _storage_items(self) -> list:
        """当前页签的精灵列表（队伍或仓库）。"""
        return (self._party() if self.storage_tab == TAB_PARTY
                else self._storage())

    def _draw_storage_detail(self) -> None:
        """右侧：当前选中的精灵详情（队伍页签看队伍，仓库页签看仓库）。"""
        if self.storage_tab == TAB_PARTY:
            creatures = self._party()
            index = self.storage_party_menu.index
            empty = "队伍里没有精灵"
        else:
            creatures = self._storage()
            index = self.storage_box_menu.index
            empty = "仓库是空的"
        if not creatures:
            text.draw(DEPOT_RIGHT_X + PAD, DEPOT_RIGHT_Y + 10, empty, palette.DARK_PURPLE)
            text.draw(DEPOT_RIGHT_X + PAD, DEPOT_RIGHT_Y + 26,
                      "抓到的精灵会先放在仓库", palette.DARK_PURPLE)
            return
        idx = max(0, min(index, len(creatures) - 1))
        c = creatures[idx]
        x = DEPOT_RIGHT_X + PAD

        text.draw(x, DEPOT_RIGHT_Y + 6, _fit(c.display_name, 60), palette.BLACK)
        lv = f"Lv{c.level}"
        text.draw(DEPOT_RIGHT_X + DEPOT_RIGHT_W - PAD - text.width(lv),
                  DEPOT_RIGHT_Y + 6, lv, palette.BLACK)

        hp_ratio = (c.hp / c.hp_max) if c.hp_max else 0.0
        draw_bar(x, DEPOT_RIGHT_Y + 24, 90, 5, hp_ratio, palette.RED,
                 palette.LIGHT_GREEN)
        pyxel.text(x, DEPOT_RIGHT_Y + 32, f"{c.hp}/{c.hp_max}", palette.BLACK)

        mp_ratio = (c.mp / c.mp_max) if c.mp_max else 0.0
        draw_bar(x, DEPOT_RIGHT_Y + 46, 60, 4, mp_ratio, palette.DEEP_BLUE,
                 palette.LIGHT_BLUE)
        pyxel.text(x, DEPOT_RIGHT_Y + 52, f"{c.mp}/{c.mp_max}", palette.BLACK)

        text.draw(x, DEPOT_RIGHT_Y + 68, f"攻{c.attack} 防{c.defense} 速{c.speed}",
                  palette.BLACK)

        action = "Z 移到仓库" if self.storage_tab == TAB_PARTY else "Z 移到队伍"
        text.draw(x, DEPOT_RIGHT_Y + 88, action, palette.DARK_PURPLE)
        limit = (f"队伍 {len(self._party())}/{PARTY_LIMIT} 只"
                 if self.storage_tab == TAB_PARTY
                 else f"仓库 {len(self._storage())} 只")
        text.draw(x, DEPOT_RIGHT_Y + 102, limit, palette.DARK_PURPLE)

    def _draw_message(self) -> None:
        """底部提示条。仓库界面没有新消息时显示默认按键提示。"""
        message = self.message
        if not message and self.mode == MODE_STORAGE:
            message = DEPOT_HINT
        if not message:
            return
        pyxel.rect(0, MSG_Y, SCREEN_W, SCREEN_H - MSG_Y, palette.LIGHT_GRAY)
        pyxel.rectb(0, MSG_Y, SCREEN_W, SCREEN_H - MSG_Y, palette.DARK_PURPLE)
        text.draw(6, MSG_Y + 7, _fit(message, SCREEN_W - 12), palette.BLACK)