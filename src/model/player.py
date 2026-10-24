"""玩家模型（《数值设定.md》§5 / §7 / §11）。

:class:`Player` 持有：金币、**队伍**（最多 6 只）、**仓库**（无上限）、
**背包**（道具 -> 数量）。

存档字典结构与《数值设定.md》§11 的顶层字段一致（不含 save_version /
timestamp / player 位置，那部分由场景层负责）。

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

from src.data.item_data import INITIAL_BAG, INITIAL_DOLLARS
from src.model.creature import Creature

#: 队伍上限（《数值设定.md》§8 / §11）
PARTY_LIMIT: int = 6


class Player:
    """玩家状态。

    参数
    ----
    dollars
        金币数量，默认 300（《数值设定.md》§7）。
    party
        队伍，最多 PARTY_LIMIT 只；超出部分自动进仓库。
    storage
        仓库中的精灵，无上限。
    bag
        背包：`{道具 ID: 数量}`。
    """

    #: 队伍上限（《数值设定.md》§8 / §11），与模块级常量一致
    PARTY_LIMIT: int = PARTY_LIMIT

    def __init__(self, dollars: int = INITIAL_DOLLARS, party=None, storage=None, bag=None):
        self.dollars: int = int(dollars)
        party_list = list(party) if party else []
        storage_list = list(storage) if storage else []
        self.party: list[Creature] = party_list[: self.PARTY_LIMIT]
        self.storage: list[Creature] = party_list[self.PARTY_LIMIT:] + storage_list
        self.bag: dict[int, int] = {
            int(k): int(v) for k, v in (bag or {}).items() if int(v) > 0
        }

    # ------------------------------------------------------------ 队伍
    def add_creature(self, c: Creature) -> str:
        """加入一只精灵。

        返回
        ----
        str
            `"party"` 表示进了队伍，`"storage"` 表示队伍已满进了仓库。
        """
        if len(self.party) < self.PARTY_LIMIT:
            self.party.append(c)
            return "party"
        self.storage.append(c)
        return "storage"

    def alive_party(self) -> list[Creature]:
        """队伍中还没倒下的精灵。"""
        return [c for c in self.party if not c.fainted]

    def all_fainted(self) -> bool:
        """队伍是否全灭（没有存活精灵即视为全灭，空队伍也算）。"""
        return not self.alive_party()

    def heal_all(self) -> None:
        """全队 HP / MP 全满（治疗点使用）。"""
        for c in self.party:
            c.heal_full()

    # ------------------------------------------------------------ 背包
    def add_item(self, item_id: int, n: int = 1) -> None:
        """增加道具数量。"""
        count = int(n)
        if count <= 0:
            return
        self.bag[int(item_id)] = self.bag.get(int(item_id), 0) + count

    def remove_item(self, item_id: int, n: int = 1) -> bool:
        """消耗道具；数量不足时**不做任何事**并返回 False。"""
        count = int(n)
        if count <= 0:
            return True
        have = self.bag.get(int(item_id), 0)
        if have < count:
            return False
        left = have - count
        if left > 0:
            self.bag[int(item_id)] = left
        else:
            del self.bag[int(item_id)]
        return True

    def item_count(self, item_id: int) -> int:
        """某种道具的数量（没有则 0）。"""
        return self.bag.get(int(item_id), 0)

    # ------------------------------------------------------------ 存档
    def to_dict(self) -> dict:
        """转成存档字典（对应《数值设定.md》§11 的 dollars / party / storage / bag）。"""
        return {
            "dollars": self.dollars,
            "party": [c.to_dict() for c in self.party],
            "storage": [c.to_dict() for c in self.storage],
            "bag": {k: self.bag[k] for k in sorted(self.bag)},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """从存档字典还原（背包的键既支持 int 也支持 JSON 里的 str）。"""
        bag_raw = data.get("bag") or {}
        bag = {int(k): int(v) for k, v in bag_raw.items()}
        return cls(
            dollars=int(data.get("dollars", INITIAL_DOLLARS)),
            party=[Creature.from_dict(d) for d in data.get("party") or []],
            storage=[Creature.from_dict(d) for d in data.get("storage") or []],
            bag=bag,
        )

    # ------------------------------------------------------------ 新游戏
    @classmethod
    def new_game(cls, starter_species_id: int) -> "Player":
        """开新游戏：一只 Lv5 初始精灵 + 300 金币 + 初始背包。

        参数
        ----
        starter_species_id
            初始精灵种族 ID（御三家为 1 / 2 / 3）。

        异常
        ----
        KeyError
            种族不存在。
        """
        starter = Creature(int(starter_species_id), level=5)
        return cls(
            dollars=INITIAL_DOLLARS,
            party=[starter],
            storage=[],
            bag=dict(INITIAL_BAG),
        )
