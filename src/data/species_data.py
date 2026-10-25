"""精灵种族数据（《数值设定.md》§1 / §6.1）。

本模块是**精灵种族数值的唯一来源**：18 只精灵的基础值 / 成长值 / 种族捕捉系数 /
技能学习表全部在这里用**字面量**写死，运行期只读不改。

- 编号 1–8：《数值设定.md》§1.2；
- 编号 9–18：《02-新增10只精灵规划.md》§4（新增 10 只精灵）。

成长公式（《数值设定.md》§1.1）
--------------------------------
    属性值(等级) = floor( 基础值 + (等级 - 1) × 成长值 )
    等级上限 = 20

派生属性：`HP_max` / `MP_max` / `ATK` / `DEF` / `SPD`。

十八只精灵（1–8《数值设定.md》§1.2；9–18《02-新增10只精灵规划.md》§4）
--------------------------------
===== ==== ==== ======== ======== ======== ======== ======== ======== ======== ===
ID    名称  属性  定位      HP基/长 MP基/长 ATK基/长 DEF基/长 SPD基/长 捕捉系数
===== ==== ==== ======== ======== ======== ======== ======== ======== ======== ===
1     小火狮 火    攻击型     22/3.2  12/1.0  13/1.5   9/1.1  10/1.2  0.40
2     水滴滴 水    均衡型     26/3.8  14/1.1  10/1.1  11/1.3   8/0.9  0.55
3     兔小子 草    速度型     20/2.8  13/1.0  11/1.2   8/1.0  14/1.6  0.55
4     小狮鹫 风    速攻型     19/2.6  12/1.0  12/1.4   8/1.0  15/1.5  0.40
5     独角兽 光    治疗/特攻  28/4.0  18/1.6  13/1.3  12/1.2   9/1.0  0.25
6     三头犬 暗    攻击型     24/3.4  12/1.0  16/1.8  10/1.1  11/1.2  0.25
7     不死鸟 火    稀有强力   24/3.4  20/1.8  15/1.7  12/1.2  14/1.4  0.10
8     闪电小子 雷    速攻型     18/2.6  14/1.1  12/1.3   7/0.9  17/1.8  0.40
9     雾尾狐 火    高速游击   19/2.7  13/1.1  13/1.5   8/0.9  16/1.7  0.40
10    涟漪豚 水    物理水盾   31/4.2  16/1.3  9/0.9    14/1.3 6/0.7   0.55
11    灯火鳅 水    治疗/法系  23/3.4  20/1.8  10/1.0   10/1.0 11/1.1  0.40
12    花刃忍 草    高速刺客   20/2.9  14/1.1  14/1.6   9/1.0  13/1.5  0.40
13    荆星芽 草    重装炮台   31/4.1  12/1.0  15/1.7   13/1.3 5/0.6   0.25
14    雏羽啾 风    辅助/续航  22/3.2  16/1.2  10/1.0   9/1.0  14/1.5  0.55
15    夜幕翼 暗    法系速攻   23/3.2  18/1.5  12/1.3   10/1.1 14/1.5  0.40
16    绒医团 光    医护/续航  27/3.8  21/1.8  9/0.9    12/1.3 10/1.0  0.40
17    导线蛇 雷    均衡削弱   23/3.1  15/1.2  13/1.4   11/1.2 12/1.2  0.40
18    雷云团 雷    慢速爆发   25/3.5  21/1.8  14/1.6   10/1.0 8/0.8   0.25
===== ==== ==== ======== ======== ======== ======== ======== ======= ======== ===

经验曲线（《数值设定.md》§6.1）
--------------------------------
    need(L) = floor( 10 × L^1.40 ) + 6      # 从 L 升到 L+1 所需

本模块**不 import 任何 UI / 引擎模块**（约束：数据层必须能脱离 Pyxel 直接导入与测试）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

#: 等级下限 / 上限（《数值设定.md》§1.1「等级上限 = 20」）
MIN_LEVEL = 1
MAX_LEVEL = 20

#: 派生属性的键名（顺序即展示顺序：HP / MP / ATK / DEF / SPD）
STAT_KEYS: tuple[str, ...] = ("HP", "MP", "ATK", "DEF", "SPD")


@dataclass(frozen=True)
class Species:
    """一个精灵种族（种族 = 同种精灵的模板）。

    属性说明
    --------
    - `id`：种族 ID（1..18）。
    - `name`：种族名。
    - `type`：属性名，取值见 src.battle.type_chart.TYPES（火/水/草/风/光/暗/雷）。
    - `role`：定位，仅用于界面展示。
    - `base`：Lv1 基础属性，键取自 STAT_KEYS。
    - `growth`：每级成长值，键与 base 相同。
    - `catch_coef`：种族捕捉系数（《数值设定.md》§8）。
    - `learnset`：等级 -> 该等级学会的技能 ID 列表（《数值设定.md》§3.1）。
    """

    id: int
    name: str
    type: str
    role: str
    base: dict[str, float] = field(default_factory=dict)
    growth: dict[str, float] = field(default_factory=dict)
    catch_coef: float = 0.0
    learnset: dict[int, list[int]] = field(default_factory=dict)


#: 18 只精灵（1–8《数值设定.md》§1.2；9–18《02-新增10只精灵规划.md》§4），运行期只读
SPECIES: dict[int, Species] = {
    1: Species(
        id=1, name="小火狮", type="火", role="攻击型",
        base={"HP": 22, "MP": 12, "ATK": 13, "DEF": 9, "SPD": 10},
        growth={"HP": 3.2, "MP": 1.0, "ATK": 1.5, "DEF": 1.1, "SPD": 1.2},
        catch_coef=0.40,
        learnset={1: [3, 1], 8: [4], 16: [5]},
    ),
    2: Species(
        id=2, name="水滴滴", type="水", role="均衡型",
        base={"HP": 26, "MP": 14, "ATK": 10, "DEF": 11, "SPD": 8},
        growth={"HP": 3.8, "MP": 1.1, "ATK": 1.1, "DEF": 1.3, "SPD": 0.9},
        catch_coef=0.55,
        learnset={1: [8, 1], 8: [9], 16: [10]},
    ),
    3: Species(
        id=3, name="兔小子", type="草", role="速度型",
        base={"HP": 20, "MP": 13, "ATK": 11, "DEF": 8, "SPD": 14},
        growth={"HP": 2.8, "MP": 1.0, "ATK": 1.2, "DEF": 1.0, "SPD": 1.6},
        catch_coef=0.55,
        learnset={1: [11, 1], 8: [12], 16: [13]},
    ),
    4: Species(
        id=4, name="小狮鹫", type="风", role="速攻型",
        base={"HP": 19, "MP": 12, "ATK": 12, "DEF": 8, "SPD": 15},
        growth={"HP": 2.6, "MP": 1.0, "ATK": 1.4, "DEF": 1.0, "SPD": 1.5},
        catch_coef=0.40,
        learnset={1: [14, 2], 8: [15], 16: [16]},
    ),
    5: Species(
        id=5, name="独角兽", type="光", role="治疗/特攻",
        base={"HP": 28, "MP": 18, "ATK": 13, "DEF": 12, "SPD": 9},
        growth={"HP": 4.0, "MP": 1.6, "ATK": 1.3, "DEF": 1.2, "SPD": 1.0},
        catch_coef=0.25,
        learnset={1: [17, 19], 8: [18], 16: [20]},
    ),
    6: Species(
        id=6, name="三头犬", type="暗", role="攻击型",
        base={"HP": 24, "MP": 12, "ATK": 16, "DEF": 10, "SPD": 11},
        growth={"HP": 3.4, "MP": 1.0, "ATK": 1.8, "DEF": 1.1, "SPD": 1.2},
        catch_coef=0.25,
        learnset={1: [21, 24], 8: [22], 16: [23]},
    ),
    7: Species(
        id=7, name="不死鸟", type="火", role="稀有强力",
        base={"HP": 24, "MP": 20, "ATK": 15, "DEF": 12, "SPD": 14},
        growth={"HP": 3.4, "MP": 1.8, "ATK": 1.7, "DEF": 1.2, "SPD": 1.4},
        catch_coef=0.10,
        learnset={1: [4, 25], 8: [6], 16: [7]},
    ),
    8: Species(
        id=8, name="闪电小子", type="雷", role="速攻型",
        base={"HP": 18, "MP": 14, "ATK": 12, "DEF": 7, "SPD": 17},
        growth={"HP": 2.6, "MP": 1.1, "ATK": 1.3, "DEF": 0.9, "SPD": 1.8},
        catch_coef=0.40,
        learnset={1: [26, 1], 8: [27], 16: [28]},
    ),
    9: Species(
        id=9, name="雾尾狐", type="火", role="高速游击",
        base={"HP": 19, "MP": 13, "ATK": 13, "DEF": 8, "SPD": 16},
        growth={"HP": 2.7, "MP": 1.1, "ATK": 1.5, "DEF": 0.9, "SPD": 1.7},
        catch_coef=0.40,
        learnset={1: [3, 1], 8: [4], 16: [29]},
    ),
    10: Species(
        id=10, name="涟漪豚", type="水", role="物理水盾",
        base={"HP": 31, "MP": 16, "ATK": 9, "DEF": 14, "SPD": 6},
        growth={"HP": 4.2, "MP": 1.3, "ATK": 0.9, "DEF": 1.3, "SPD": 0.7},
        catch_coef=0.55,
        learnset={1: [8, 1], 8: [9], 16: [10]},
    ),
    11: Species(
        id=11, name="灯火鳅", type="水", role="治疗/法系",
        base={"HP": 23, "MP": 20, "ATK": 10, "DEF": 10, "SPD": 11},
        growth={"HP": 3.4, "MP": 1.8, "ATK": 1.0, "DEF": 1.0, "SPD": 1.1},
        catch_coef=0.40,
        learnset={1: [8, 19], 8: [9], 16: [30]},
    ),
    12: Species(
        id=12, name="花刃忍", type="草", role="高速刺客",
        base={"HP": 20, "MP": 14, "ATK": 14, "DEF": 9, "SPD": 13},
        growth={"HP": 2.9, "MP": 1.1, "ATK": 1.6, "DEF": 1.0, "SPD": 1.5},
        catch_coef=0.40,
        learnset={1: [11, 1], 8: [12], 16: [31]},
    ),
    13: Species(
        id=13, name="荆星芽", type="草", role="重装炮台",
        base={"HP": 31, "MP": 12, "ATK": 15, "DEF": 13, "SPD": 5},
        growth={"HP": 4.1, "MP": 1.0, "ATK": 1.7, "DEF": 1.3, "SPD": 0.6},
        catch_coef=0.25,
        learnset={1: [11, 24], 8: [12], 16: [32]},
    ),
    14: Species(
        id=14, name="雏羽啾", type="风", role="辅助/续航",
        base={"HP": 22, "MP": 16, "ATK": 10, "DEF": 9, "SPD": 14},
        growth={"HP": 3.2, "MP": 1.2, "ATK": 1.0, "DEF": 1.0, "SPD": 1.5},
        catch_coef=0.55,
        learnset={1: [2, 25], 8: [15], 16: [16]},
    ),
    15: Species(
        id=15, name="夜幕翼", type="暗", role="法系速攻",
        base={"HP": 23, "MP": 18, "ATK": 12, "DEF": 10, "SPD": 14},
        growth={"HP": 3.2, "MP": 1.5, "ATK": 1.3, "DEF": 1.1, "SPD": 1.5},
        catch_coef=0.40,
        learnset={1: [21, 24], 8: [22], 16: [33]},
    ),
    16: Species(
        id=16, name="绒医团", type="光", role="医护/续航",
        base={"HP": 27, "MP": 21, "ATK": 9, "DEF": 12, "SPD": 10},
        growth={"HP": 3.8, "MP": 1.8, "ATK": 0.9, "DEF": 1.3, "SPD": 1.0},
        catch_coef=0.40,
        learnset={1: [18, 19], 8: [25], 16: [20]},
    ),
    17: Species(
        id=17, name="导线蛇", type="雷", role="均衡削弱",
        base={"HP": 23, "MP": 15, "ATK": 13, "DEF": 11, "SPD": 12},
        growth={"HP": 3.1, "MP": 1.2, "ATK": 1.4, "DEF": 1.2, "SPD": 1.2},
        catch_coef=0.40,
        learnset={1: [26, 24], 8: [27], 16: [34]},
    ),
    18: Species(
        id=18, name="雷云团", type="雷", role="慢速爆发",
        base={"HP": 25, "MP": 21, "ATK": 14, "DEF": 10, "SPD": 8},
        growth={"HP": 3.5, "MP": 1.8, "ATK": 1.6, "DEF": 1.0, "SPD": 0.8},
        catch_coef=0.25,
        learnset={1: [26, 1], 8: [27], 16: [35]},
    ),
}

#: 御三家种族 ID（玩家开局三选一：小火狮 / 水滴滴 / 兔小子）
STARTER_IDS: tuple[int, ...] = (1, 2, 3)


# ---------------------------------------------------------------- 经验曲线
def need_exp(level: int) -> int:
    """从 `level` 升到 `level + 1` 所需的经验（《数值设定.md》§6.1）。

    公式：`need(L) = floor(10 × L^1.40) + 6`。

    参数
    ----
    level
        当前等级（1..19）。

    返回
    ----
    int
        升级所需经验；等级低于 1 时按 1 计算。
    """
    lv = max(MIN_LEVEL, int(level))
    return int(math.floor(10 * lv ** 1.40) + 6)


#: 等级 -> 升级所需经验（Lv1..Lv19），等价于 need_exp()
EXP_TABLE: dict[int, int] = {lv: need_exp(lv) for lv in range(MIN_LEVEL, MAX_LEVEL)}


# ---------------------------------------------------------------- 查询 helper
def get_species(species_id: int) -> Species:
    """按 ID 取种族定义；不存在时抛 KeyError。"""
    try:
        return SPECIES[species_id]
    except KeyError:
        raise KeyError(
            f"没有编号为 {species_id} 的精灵种族，可用：{sorted(SPECIES)}"
        ) from None


def stat_at(species_id: int, key: str, level: int) -> int:
    """取某种族在某等级的单项派生属性。

    计算式（《数值设定.md》§1.1）：`floor(基础值 + (等级 - 1) × 成长值)`。

    参数
    ----
    species_id
        种族 ID。
    key
        属性键，取值 STAT_KEYS 之一（"HP"/"MP"/"ATK"/"DEF"/"SPD"）。
    level
        等级。

    异常
    ----
    KeyError
        种族不存在，或 `key` 不是合法属性键。
    """
    sp = get_species(species_id)
    if key not in sp.base:
        raise KeyError(f"未知属性键 {key!r}，可用：{STAT_KEYS}")
    lv = max(MIN_LEVEL, int(level))
    return int(math.floor(sp.base[key] + (lv - 1) * sp.growth[key]))


def stats_at(species_id: int, level: int) -> dict[str, int]:
    """取某种族在某等级的**全部**派生属性，返回 `{键: 值}`。"""
    return {key: stat_at(species_id, key, level) for key in STAT_KEYS}


def learnset_at(species_id: int, level: int) -> list[int]:
    """取某种族在指定等级学会的技能 ID 列表（没有则返回空列表）。"""
    return list(get_species(species_id).learnset.get(int(level), []))
