"""精灵个体模型测试（src/model/creature.py）。

覆盖《数值设定.md》§1.3 / §5.4 / §6.1 / §6.3 / §9 / §11：

- 派生属性（上限值按等级派生）；
- 升级：连续升级、升级即回满、Lv8 / Lv16 自动学技能；
- 存档 round-trip（to_dict → from_dict → to_dict 完全一致）；
- 倒下 / 复活语义；
- MP 语义（够不够用、扣减不低于 0）；
- "吼叫"能力下降（不叠加、回合结束恢复）。
"""

from __future__ import annotations

import unittest

from src.data.skill_data import get_skill
from src.data.species_data import need_exp
from src.model.creature import Creature


class DerivedStatsTest(unittest.TestCase):
    """§1.3 派生属性。"""

    def test_lv5_starter_stats(self):
        c = Creature(1)
        self.assertEqual(c.species_id, 1)
        self.assertEqual(c.level, 5)
        self.assertEqual(c.hp_max, 34)
        self.assertEqual(c.mp_max, 16)
        self.assertEqual(c.attack, 19)
        self.assertEqual(c.defense, 13)
        self.assertEqual(c.speed, 14)
        self.assertEqual(c.hp, 34)
        self.assertEqual(c.mp, 16)

    def test_stats_follow_level(self):
        c = Creature(1, level=10)
        self.assertEqual(c.hp_max, 50)
        self.assertEqual(c.mp_max, 21)
        self.assertEqual(c.attack, 26)
        c.level = 20
        self.assertEqual(c.hp_max, 82)
        self.assertEqual(c.attack, 41)

    def test_level_is_clamped(self):
        self.assertEqual(Creature(1, level=0).level, 1)
        self.assertEqual(Creature(1, level=99).level, 20)

    def test_default_skills_from_learnset(self):
        self.assertEqual(Creature(1).skills, [3, 1])
        self.assertEqual(Creature(5).skills, [17, 19])
        self.assertEqual(Creature(7).skills, [4, 25])

    def test_nickname_defaults_to_species_name(self):
        self.assertEqual(Creature(1).nickname, "小火狮")
        self.assertEqual(Creature(1, nickname="小炎").nickname, "小炎")

    def test_skills_capped_at_four(self):
        c = Creature(1)
        c.skills = [1, 2, 3, 4, 5]
        self.assertEqual(len(c.skills), 4)


class ExpAndLevelTest(unittest.TestCase):
    """§6.1 / §6.3 升级。"""

    def test_exp_to_next(self):
        self.assertEqual(Creature(1, level=5).exp_to_next(), need_exp(5))
        self.assertEqual(Creature(1, level=5).exp_to_next(), 101)

    def test_gain_exp_levels_up(self):
        c = Creature(1, level=5)
        events = c.gain_exp(101)
        self.assertEqual(c.level, 6)
        self.assertEqual(c.exp, 0)
        self.assertEqual(events, ["升到 Lv6！"])

    def test_gain_exp_partial_progress(self):
        c = Creature(1, level=5)
        events = c.gain_exp(50)
        self.assertEqual(c.level, 5)
        self.assertEqual(c.exp, 50)
        self.assertEqual(events, [])

    def test_level_up_heals_hp_and_mp(self):
        """§6.3：升级时 HP / MP 全回复。"""
        c = Creature(1, level=5)
        c.hp = 1
        c.mp = 0
        c.gain_exp(101)
        self.assertEqual(c.hp, c.hp_max)
        self.assertEqual(c.mp, c.mp_max)

    def test_learns_skill_at_lv8(self):
        c = Creature(1, level=5)
        total = need_exp(5) + need_exp(6) + need_exp(7)
        events = c.gain_exp(total)
        self.assertEqual(c.level, 8)
        self.assertIn(4, c.skills)
        self.assertIn("学会了 烈焰！", events)
        self.assertEqual(events[0], "升到 Lv6！")
        self.assertEqual(events[-1], "学会了 烈焰！")

    def test_learns_skill_at_lv16(self):
        c = Creature(1, level=5)
        total = sum(need_exp(lv) for lv in range(5, 16))
        events = c.gain_exp(total)
        self.assertEqual(c.level, 16)
        self.assertIn(4, c.skills)
        self.assertIn(5, c.skills)
        self.assertEqual(len(c.skills), 4)
        self.assertIn("学会了 天火燎原！", events)

    def test_learn_skill_event_text_format(self):
        """事件字符串格式固定：升到 LvN！ / 学会了 <技能名>！。"""
        c = Creature(2, level=5)
        events = c.gain_exp(need_exp(5) + need_exp(6) + need_exp(7))
        self.assertEqual(events[0], "升到 Lv6！")
        self.assertEqual(events[-1], "学会了 水之波动！")
        self.assertEqual(c.level, 8)
        self.assertIn(9, c.skills)

    def test_gain_exp_zero_or_negative(self):
        c = Creature(1)
        self.assertEqual(c.gain_exp(0), [])
        self.assertEqual(c.gain_exp(-10), [])
        self.assertEqual(c.level, 5)

    def test_max_level_does_not_level_up(self):
        c = Creature(1, level=20)
        self.assertEqual(c.gain_exp(100000), [])
        self.assertEqual(c.level, 20)
        self.assertEqual(c.exp_to_next(), 0)


class SaveRoundTripTest(unittest.TestCase):
    """§11 存档。"""

    def test_to_dict_fields_match_doc(self):
        d = Creature(1).to_dict()
        self.assertEqual(set(d), {"species_id", "nickname", "level", "exp",
                                  "hp", "mp", "skills", "atk_mod"})

    def test_round_trip_is_identical(self):
        c = Creature(3, level=12, exp=77, hp=20, mp=9, nickname="豆豆")
        d = c.to_dict()
        again = Creature.from_dict(d).to_dict()
        self.assertEqual(again, d)

    def test_round_trip_keeps_state(self):
        c = Creature(6, level=9, exp=33, hp=11, mp=4)
        restored = Creature.from_dict(c.to_dict())
        self.assertEqual(restored.level, 9)
        self.assertEqual(restored.exp, 33)
        self.assertEqual(restored.hp, 11)
        self.assertEqual(restored.mp, 4)
        self.assertEqual(restored.skills, c.skills)
        self.assertEqual(restored.atk_mod, 1.0)

    def test_from_dict_recomputes_limits(self):
        """上限值按 level 重新派生，不信存档里的旧值。"""
        d = {"species_id": 1, "level": 10, "exp": 0, "hp": 999,
             "mp": 999, "skills": [3, 1], "atk_mod": 1.0}
        c = Creature.from_dict(d)
        self.assertEqual(c.hp_max, 50)
        self.assertEqual(c.mp_max, 21)
        self.assertEqual(c.hp, 50)     # 夹到上限
        self.assertEqual(c.mp, 21)

    def test_from_dict_clamps_negative_hp(self):
        d = {"species_id": 1, "level": 5, "exp": 0, "hp": -8,
             "mp": -3, "skills": [3, 1], "atk_mod": 1.0}
        c = Creature.from_dict(d)
        self.assertEqual(c.hp, 0)
        self.assertEqual(c.mp, 0)
        self.assertTrue(c.fainted)

    def test_from_dict_keeps_atk_mod(self):
        d = {"species_id": 1, "level": 5, "exp": 0, "hp": 30, "mp": 12,
             "skills": [3, 1], "atk_mod": 0.75}
        c = Creature.from_dict(d)
        self.assertEqual(c.atk_mod, 0.75)
        self.assertEqual(c.to_dict()["atk_mod"], 0.75)


class CombatStateTest(unittest.TestCase):
    """HP / MP / 倒下 / 能力下降。"""

    def test_take_damage_returns_actual(self):
        c = Creature(1)
        self.assertEqual(c.take_damage(10), 10)
        self.assertEqual(c.hp, 24)
        self.assertEqual(c.take_damage(1000), 24)
        self.assertEqual(c.hp, 0)

    def test_fainted_flag(self):
        c = Creature(1)
        self.assertFalse(c.fainted)
        c.take_damage(999)
        self.assertTrue(c.fainted)
        self.assertEqual(c.hp, 0)

    def test_revive_restores_half_hp(self):
        c = Creature(1)
        c.take_damage(999)
        self.assertTrue(c.fainted)
        c.revive()
        self.assertFalse(c.fainted)
        self.assertEqual(c.hp, 17)     # int(34 × 0.5)
        self.assertGreater(c.hp, 0)

    def test_revive_on_living_creature_does_nothing(self):
        c = Creature(1)
        c.revive()
        self.assertEqual(c.hp, 34)

    def test_heal_hp_capped_at_max(self):
        c = Creature(1)
        c.take_damage(30)
        self.assertEqual(c.heal_hp(100), 30)
        self.assertEqual(c.hp, 34)
        self.assertEqual(c.heal_hp(5), 0)

    def test_heal_mp_capped_at_max(self):
        c = Creature(1)
        self.assertEqual(c.heal_mp(5), 0)
        c.spend_mp(3)
        self.assertEqual(c.heal_mp(100), 4)
        self.assertEqual(c.mp, 16)

    def test_hp_write_is_clamped(self):
        c = Creature(1)
        c.hp = 9999
        self.assertEqual(c.hp, 34)
        c.hp = -5
        self.assertEqual(c.hp, 0)

    def test_can_use_and_spend_mp(self):
        c = Creature(1)
        self.assertTrue(c.can_use(1))          # 撞击，0 MP
        self.assertTrue(c.can_use(4))          # 烈焰，10 MP
        c.spend_mp(4)
        self.assertEqual(c.mp, 6)
        self.assertFalse(c.can_use(4))
        c.spend_mp(4)                          # MP 不足也不低于 0
        self.assertEqual(c.mp, 0)

    def test_skill_mp_cost_matches_table(self):
        c = Creature(1)
        for skill_id in (1, 3, 4):
            cost = get_skill(skill_id).mp
            before = c.mp
            c.spend_mp(skill_id)
            self.assertEqual(c.mp, before - cost)

    def test_atk_mod_debuff(self):
        c = Creature(1)
        c.apply_atk_mod(0.75, 3)
        self.assertEqual(c.atk_mod, 0.75)
        self.assertEqual(c.mod_rounds, 3)
        c.tick_mods()
        self.assertEqual(c.atk_mod, 0.75)
        self.assertEqual(c.mod_rounds, 2)
        c.tick_mods()
        self.assertEqual(c.atk_mod, 0.75)
        c.tick_mods()
        self.assertEqual(c.atk_mod, 1.0)
        self.assertEqual(c.mod_rounds, 0)

    def test_atk_mod_does_not_stack(self):
        c = Creature(1)
        c.apply_atk_mod(0.75, 3)
        c.apply_atk_mod(0.75, 3)
        self.assertEqual(c.mod_rounds, 3)
        self.assertEqual(c.atk_mod, 0.75)

    def test_tick_mods_without_debuff(self):
        c = Creature(1)
        c.tick_mods()
        self.assertEqual(c.atk_mod, 1.0)
        self.assertEqual(c.mod_rounds, 0)

    def test_heal_full(self):
        c = Creature(1)
        c.take_damage(20)
        c.spend_mp(3)
        c.heal_full()
        self.assertEqual(c.hp, c.hp_max)
        self.assertEqual(c.mp, c.mp_max)


if __name__ == "__main__":
    unittest.main()
