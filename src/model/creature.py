"""精灵个体模型（《数值设定.md》§1 / §5 / §6 / §11）。

:class:`Creature` 是**一只具体的精灵**（种族 + 等级 + 当前 HP/MP + 技能 + 昵称），
是战斗与存档的核心单位。

设计要点
--------
1. **上限值一律派生**：HP/MP 上限与 ATK/DEF/SPD 由"种族 + 等级"按公式算出，
   不存储、不作为存档字段（《数值设定.md》§11 / D8）。
2. **HP/MP 写入即夹取**：任何来源（道具、伤害、存档）写入的 HP/MP 都会被夹到
   `[0, 上限]`。
3. **升级即回满**：升级时 HP/MP 全回复（《数值设定.md》§6.3），并自动学会
   Lv8 / Lv16 的新技能。
4. **能力下降不叠加**：apply_atk_mod() 只刷新倍率与剩余回合数。

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

from src.data.skill_data import get_skill
from src.data.species_data import (
    MAX_LEVEL,
    MIN_LEVEL,
    Species,
    get_species,
    need_exp,
    stat_at,
)


class Creature:
    """一只精灵个体。

    参数
    ----
    species_id
        种族 ID（1..8）；不存在时抛 KeyError。
    level
        等级，默认 5（初始精灵等级，《数值设定.md》§6.2），夹取到 1..20。
    exp
        当前等级内的经验进度（《数值设定.md》§6.1：need(L) 是从 L 升到 L+1 所需）。
    hp
        当前 HP；None 表示满血。写入时夹到 [0, 上限]。
    mp
        当前 MP；None 表示满蓝。写入时夹到 [0, 上限]。
    skills
        已学会的技能 ID 列表；None 表示按种族学习表取 Lv1 初始技能。最多 4 个。
    nickname
        昵称；留空时默认取种族名。
    """

    #: 最多同时记住的技能数（《数值设定.md》§3.1）
    MAX_SKILLS: int = 4

    #: 从存档读回能力下降状态时假定的剩余回合数（存档不记回合数，§11 / D8）
    DEFAULT_MOD_ROUNDS: int = 3

    def __init__(self, species_id: int, level: int = 5, exp: int = 0,
                 hp: int | None = None, mp: int | None = None,
                 skills: list[int] | None = None, nickname: str = ""):
        self._species: Species = get_species(int(species_id))
        self._species_id: int = int(species_id)
        self._level: int = max(MIN_LEVEL, min(MAX_LEVEL, int(level)))
        self._exp: int = max(0, int(exp))
        self._nickname: str = nickname or self._species.name
        self._atk_mod: float = 1.0
        self._mod_rounds: int = 0

        if skills is None:
            self._skills: list[int] = list(self._species.learnset.get(1, []))
        else:
            self._skills = [int(s) for s in skills][: self.MAX_SKILLS]

        self._hp: int = self.hp_max if hp is None else max(0, min(int(hp), self.hp_max))
        self._mp: int = self.mp_max if mp is None else max(0, min(int(mp), self.mp_max))

    # ------------------------------------------------------------ 只读属性
    @property
    def species_id(self) -> int:
        """种族 ID。"""
        return self._species_id

    @property
    def species(self) -> Species:
        """种族定义对象。"""
        return self._species

    @property
    def name(self) -> str:
        """种族名（不含昵称）。"""
        return self._species.name

    @property
    def display_name(self) -> str:
        """界面显示名：昵称优先，没有昵称则用种族名。"""
        return self._nickname or self._species.name

    @property
    def nickname(self) -> str:
        """昵称。"""
        return self._nickname

    @nickname.setter
    def nickname(self, value: str) -> None:
        self._nickname = str(value)

    @property
    def level(self) -> int:
        """等级（1..20）。"""
        return self._level

    @level.setter
    def level(self, value: int) -> None:
        self._level = max(MIN_LEVEL, min(MAX_LEVEL, int(value)))
        self._hp = min(self._hp, self.hp_max)
        self._mp = min(self._mp, self.mp_max)

    @property
    def exp(self) -> int:
        """当前等级内的经验进度。"""
        return self._exp

    @exp.setter
    def exp(self, value: int) -> None:
        self._exp = max(0, int(value))

    @property
    def hp(self) -> int:
        """当前 HP。"""
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        self._hp = max(0, min(int(value), self.hp_max))

    @property
    def mp(self) -> int:
        """当前 MP。"""
        return self._mp

    @mp.setter
    def mp(self, value: int) -> None:
        self._mp = max(0, min(int(value), self.mp_max))

    @property
    def hp_max(self) -> int:
        """HP 上限（按等级派生）。"""
        return stat_at(self._species_id, "HP", self._level)

    @property
    def mp_max(self) -> int:
        """MP 上限（按等级派生）。"""
        return stat_at(self._species_id, "MP", self._level)

    @property
    def attack(self) -> int:
        """ATK（按等级派生）。"""
        return stat_at(self._species_id, "ATK", self._level)

    @property
    def defense(self) -> int:
        """DEF（按等级派生）。"""
        return stat_at(self._species_id, "DEF", self._level)

    @property
    def speed(self) -> int:
        """SPD（按等级派生）。"""
        return stat_at(self._species_id, "SPD", self._level)

    @property
    def skills(self) -> list[int]:
        """已学会的技能 ID 列表（最多 4 个）。"""
        return self._skills

    @skills.setter
    def skills(self, value: list[int]) -> None:
        self._skills = [int(s) for s in value][: self.MAX_SKILLS]

    @property
    def atk_mod(self) -> float:
        """攻击倍率（1.0 或 0.75）。"""
        return self._atk_mod

    @atk_mod.setter
    def atk_mod(self, value: float) -> None:
        mult = float(value)
        self._atk_mod = mult if mult > 0 else 1.0

    @property
    def mod_rounds(self) -> int:
        """能力下降剩余回合数（0 表示无减益）。"""
        return self._mod_rounds

    @mod_rounds.setter
    def mod_rounds(self, value: int) -> None:
        self._mod_rounds = max(0, int(value))

    @property
    def fainted(self) -> bool:
        """是否已倒下（HP == 0）。"""
        return self._hp <= 0

    # ------------------------------------------------------------ 经验与升级
    def exp_to_next(self) -> int:
        """升到下一级所需经验（已满级返回 0）。"""
        if self._level >= MAX_LEVEL:
            return 0
        return need_exp(self._level)

    def gain_exp(self, amount: int) -> list[str]:
        """获得经验，返回**战斗结算界面可直接显示**的事件列表。

        事件字符串格式（固定，供 T3b 直接渲染）：

        - 升级：`"升到 Lv6！"`
        - 学会技能：`"学会了 烈焰！"`

        规则
        ----
        - 经验按 need_exp() 逐级扣除，可连续升多级。
        - 每升一级，HP / MP **全回复**（《数值设定.md》§6.3）。
        - 到达 Lv8 / Lv16 自动学会该种族的新技能（技能最多 4 个，装满则跳过）。
        - 已满级（Lv20）时不再累积经验，返回空列表。
        """
        events: list[str] = []
        gain = int(amount)
        if gain <= 0 or self._level >= MAX_LEVEL:
            return events
        self._exp += gain
        while self._level < MAX_LEVEL:
            need = need_exp(self._level)
            if self._exp < need:
                break
            self._exp -= need
            self._level += 1
            events.append(f"升到 Lv{self._level}！")
            self.heal_full()
            events.extend(self._learn_for_level(self._level))
        return events

    def _learn_for_level(self, level: int) -> list[str]:
        """处理"到达某等级时自动学技能"，返回事件列表。"""
        events: list[str] = []
        for skill_id in self._species.learnset.get(int(level), []):
            if skill_id in self._skills:
                continue
            if len(self._skills) >= self.MAX_SKILLS:
                continue
            self._skills.append(int(skill_id))
            events.append(f"学会了 {get_skill(int(skill_id)).name}！")
        return events

    # ------------------------------------------------------------ HP / MP
    def take_damage(self, dmg: int) -> int:
        """受到伤害，返回**实际扣血量**（HP 不会低于 0）。"""
        amount = int(dmg)
        if amount <= 0:
            return 0
        actual = min(amount, self._hp)
        self._hp -= actual
        return actual

    def heal_hp(self, n: int) -> int:
        """回复 HP，返回**实际回复量**（不超过上限）。"""
        amount = int(n)
        if amount <= 0:
            return 0
        actual = min(amount, self.hp_max - self._hp)
        self._hp += actual
        return actual

    def heal_mp(self, n: int) -> int:
        """回复 MP，返回**实际回复量**（不超过上限）。"""
        amount = int(n)
        if amount <= 0:
            return 0
        actual = min(amount, self.mp_max - self._mp)
        self._mp += actual
        return actual

    def heal_full(self) -> None:
        """HP / MP 全满（治疗点、升级时使用）。"""
        self._hp = self.hp_max
        self._mp = self.mp_max

    def revive(self, hp_ratio: float = 0.5) -> None:
        """复活：HP 恢复为最大 HP 的 hp_ratio 倍（至少 1 点）。

        已经活着的精灵调用本方法**不做任何事**（复活草不能用在活着的精灵身上）。
        """
        if self._hp > 0:
            return
        self._hp = max(1, int(self.hp_max * float(hp_ratio)))

    # ------------------------------------------------------------ 技能与 MP
    def can_use(self, skill_id: int) -> bool:
        """MP 是否够用这个技能（够用返回 True）。"""
        return self._mp >= get_skill(int(skill_id)).mp

    def spend_mp(self, skill_id: int) -> None:
        """消耗技能 MP（MP 不会低于 0）。"""
        cost = get_skill(int(skill_id)).mp
        self._mp = max(0, self._mp - int(cost))

    # ------------------------------------------------------------ 能力下降
    def apply_atk_mod(self, mult: float, rounds: int) -> None:
        """施加攻击倍率减益（"吼叫"）。

        **不叠加**：再次施加只会刷新倍率与剩余回合数。
        """
        self._atk_mod = float(mult)
        self._mod_rounds = max(0, int(rounds))

    def tick_mods(self) -> None:
        """回合结束调用：剩余回合数减 1，归零后恢复 1.0。"""
        if self._mod_rounds > 0:
            self._mod_rounds -= 1
            if self._mod_rounds <= 0:
                self._mod_rounds = 0
                self._atk_mod = 1.0

    def clear_mods(self) -> None:
        """清除自身能力下降（"治愈波动" / "圣域" 的附带效果）。"""
        self._atk_mod = 1.0
        self._mod_rounds = 0

    # ------------------------------------------------------------ 存档
    def to_dict(self) -> dict:
        """转成存档字典，字段与《数值设定.md》§11 完全一致。

        只存 species_id / nickname / level / exp / hp / mp / skills / atk_mod；
        上限值（HP_max / ATK …）一律**派生不存**。
        """
        return {
            "species_id": self._species_id,
            "nickname": self._nickname,
            "level": self._level,
            "exp": self._exp,
            "hp": self._hp,
            "mp": self._mp,
            "skills": list(self._skills),
            "atk_mod": self._atk_mod,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Creature":
        """从存档字典还原。

        只信 level / exp / hp / mp / skills / nickname / atk_mod（外加 species_id）；
        上限值按 level 重新派生，hp / mp 夹到 [0, 上限]。
        """
        raw_skills = data.get("skills")
        skills = [int(s) for s in raw_skills] if raw_skills else None
        creature = cls(
            species_id=int(data["species_id"]),
            level=int(data.get("level", 5)),
            exp=int(data.get("exp", 0)),
            hp=data.get("hp"),
            mp=data.get("mp"),
            skills=skills,
            nickname=str(data.get("nickname", "")),
        )
        mod = float(data.get("atk_mod", 1.0))
        creature._atk_mod = mod if mod > 0 else 1.0
        creature._mod_rounds = (
            cls.DEFAULT_MOD_ROUNDS if creature._atk_mod != 1.0 else 0
        )
        return creature
