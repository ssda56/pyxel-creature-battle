"""技能数据（《数值设定.md》§3）。

本模块是**技能表与技能学习表的唯一来源**：35 个技能的属性 / 威力 / MP 消耗 /
效果全部用**字面量**写死，运行期只读不改。

技能效果分类（`effect`）
-------------------------
===== ============ ==========================================================
效果     威力     语义
===== ============ ==========================================================
damage   >0       造成伤害，走《数值设定.md》§4.1 伤害公式
heal     0        回复自身最大 HP 的 `value` 比例（至少 `min_heal`）
debuff_atk 0      敌方 ATK × `value`，持续 `duration` 回合
===== ============ ==========================================================

本模块**不 import 任何 UI / 引擎模块**。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    """一个技能。

    属性说明
    --------
    - `id`：技能 ID（1..35）。
    - `name`：技能名。
    - `type`：属性名，"无" 表示通用招式（克制系数恒 1.0）。
    - `power`：威力，0 表示不造成伤害。
    - `mp`：MP 消耗。
    - `effect`：效果类型，"damage" / "heal" / "debuff_atk"。
    - `value`：heal 为回复比例（0.25/0.3/0.5）；debuff_atk 为攻击倍率（0.75）。
    - `min_heal`：heal 的最小回复量（12/15/25），非治疗技能填 0。
    - `duration`：debuff_atk 的持续回合（3），其余填 0。
    - `desc`：界面用一句话说明。
    """

    id: int
    name: str
    type: str
    power: int
    mp: int
    effect: str
    value: float = 0.0
    min_heal: int = 0
    duration: int = 0
    desc: str = ""


#: 35 个技能（1–28《数值设定.md》§3；29–35《02-新增10只精灵规划.md》§五），运行期只读
SKILLS: dict[int, Skill] = {
    1: Skill(1, "撞击", "无", 35, 0, "damage", desc="用身体猛烈撞击对手，没有属性加成。"),
    2: Skill(2, "啄击", "风", 32, 2, "damage", desc="用尖锐的喙啄击对手。"),
    3: Skill(3, "火花", "火", 40, 4, "damage", desc="喷出火焰灼烧对手。"),
    4: Skill(4, "烈焰", "火", 90, 10, "damage", desc="释放炽热的烈焰，造成大量伤害。"),
    5: Skill(5, "天火燎原", "火", 120, 16, "damage", desc="召唤天火覆盖战场，造成巨大伤害。"),
    6: Skill(6, "涅槃之炎", "火", 75, 8, "damage", desc="浴火重生的凤凰之炎。"),
    7: Skill(7, "凤凰天翔", "火", 130, 18, "damage", desc="凤凰展翅翱翔，掀起火焰风暴。"),
    8: Skill(8, "水枪", "水", 40, 4, "damage", desc="喷出高压水流攻击对手。"),
    9: Skill(9, "水之波动", "水", 65, 7, "damage", desc="操纵水流形成冲击波。"),
    10: Skill(10, "激流", "水", 100, 13, "damage", desc="召唤狂暴激流冲刷敌人。"),
    11: Skill(11, "飞叶", "草", 40, 4, "damage", desc="射出锋利的叶片。"),
    12: Skill(12, "藤鞭", "草", 60, 6, "damage", desc="用藤蔓缠绕并抽打对手。"),
    13: Skill(13, "叶刃风暴", "草", 100, 13, "damage", desc="卷起叶片风暴撕裂敌人。"),
    14: Skill(14, "风刃", "风", 45, 5, "damage", desc="斩出锋利的风刃。"),
    15: Skill(15, "疾风斩", "风", 65, 7, "damage", desc="以疾风之势连斩。"),
    16: Skill(16, "神风", "风", 105, 14, "damage", desc="召唤神风撕裂一切。"),
    17: Skill(17, "圣光", "光", 85, 10, "damage", desc="降下神圣的光芒造成伤害。"),
    18: Skill(18, "净化之光", "光", 60, 6, "damage", desc="用圣光净化对手。"),
    19: Skill(19, "治愈波动", "光", 0, 8, "heal", 0.25, 12, 0,
              "回复自身 25% 最大 HP（最少 12），清除自身能力下降"),
    20: Skill(20, "圣域", "光", 0, 12, "heal", 0.5, 25, 0,
              "回复自身 50% 最大 HP（最少 25），清除自身能力下降"),
    21: Skill(21, "暗影咬", "暗", 50, 5, "damage", desc="从暗影中猛咬对手。"),
    22: Skill(22, "深渊噬咬", "暗", 70, 8, "damage", desc="深渊之牙撕裂对手。"),
    23: Skill(23, "三重咬碎", "暗", 110, 14, "damage", desc="连续三次重咬，粉碎敌人。"),
    24: Skill(24, "吼叫", "无", 0, 3, "debuff_atk", 0.75, 0, 3,
              "敌方 ATK ×0.75，持续 3 回合（不叠加，只刷新回合数）"),
    25: Skill(25, "再生", "无", 0, 8, "heal", 0.3, 15, 0,
              "回复自身 30% 最大 HP（最少 15）"),
    26: Skill(26, "电击", "雷", 45, 5, "damage", desc="放出电流电击对手。"),
    27: Skill(27, "电光一闪", "雷", 60, 6, "damage", desc="化身电光瞬间突袭。"),
    28: Skill(28, "万雷天牢", "雷", 110, 14, "damage", desc="降下天雷困锁敌人。"),
    29: Skill(29, "狐火燎原", "火", 110, 15, "damage", desc="甩动狐尾卷起烟焰，火势燎原。"),
    30: Skill(30, "灯芯回响", "水", 85, 11, "damage", desc="尾灯的清响化作水波，回荡不止。"),
    31: Skill(31, "千瓣斩", "草", 105, 13, "damage", desc="千片花瓣凝作利刃，一齐斩落。"),
    32: Skill(32, "荆星坠", "草", 115, 15, "damage", desc="召来星形花苞当空坠下，沉重一击。"),
    33: Skill(33, "月蚀低语", "暗", 100, 13, "damage", desc="月蚀之影低语缠身，啃噬生机。"),
    34: Skill(34, "串联雷网", "雷", 95, 12, "damage", desc="导电蛇身织成雷网，串联放电。"),
    35: Skill(35, "雷云审判", "雷", 125, 17, "damage", desc="雷云聚成审判之雷，一击降下。"),
}


def get_skill(skill_id: int) -> Skill:
    """按 ID 取技能定义；不存在时抛 KeyError。"""
    try:
        return SKILLS[skill_id]
    except KeyError:
        raise KeyError(f"没有编号为 {skill_id} 的技能，可用：{sorted(SKILLS)}") from None


def skill_name(skill_id: int) -> str:
    """取技能名（不存在时抛 KeyError）。"""
    return get_skill(skill_id).name
