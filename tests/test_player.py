"""玩家模型测试（src/model/player.py）。

覆盖《数值设定.md》§7 / §8 / §11：

- 新游戏初始状态（Lv5 精灵 + 300 金币 + 初始背包）；
- 队伍上限 6 只，超出进仓库；
- 全灭判定与治疗点全队回复；
- 背包增删查；
- 存档 round-trip。
"""

from __future__ import annotations

import unittest

from src.data.item_data import INITIAL_BAG, INITIAL_DOLLARS
from src.model.creature import Creature
from src.model.player import PARTY_LIMIT, Player


class NewGameTest(unittest.TestCase):
    """§6.2 / §7.2 新游戏初始状态。"""

    def test_new_game_defaults(self):
        p = Player.new_game(1)
        self.assertEqual(p.dollars, 300)
        self.assertEqual(p.dollars, INITIAL_DOLLARS)
        self.assertEqual(p.bag, {1: 5, 2: 2, 4: 1})
        self.assertEqual(p.bag, INITIAL_BAG)
        self.assertEqual(len(p.party), 1)
        self.assertEqual(p.storage, [])

    def test_new_game_starter_is_lv5(self):
        p = Player.new_game(1)
        starter = p.party[0]
        self.assertEqual(starter.species_id, 1)
        self.assertEqual(starter.level, 5)
        self.assertEqual(starter.skills, [3, 1])
        self.assertEqual(starter.hp, starter.hp_max)

    def test_new_game_each_starter(self):
        for sid, skills in ((1, [3, 1]), (2, [8, 1]), (3, [11, 1])):
            p = Player.new_game(sid)
            self.assertEqual(p.party[0].species_id, sid)
            self.assertEqual(p.party[0].skills, skills)

    def test_new_game_unknown_species_raises(self):
        with self.assertRaises(KeyError):
            Player.new_game(99)


class PartyTest(unittest.TestCase):
    """队伍与仓库。"""

    def test_party_limit_is_six(self):
        self.assertEqual(PARTY_LIMIT, 6)

    def test_add_creature_to_party_then_storage(self):
        p = Player.new_game(1)
        for _ in range(5):
            self.assertEqual(p.add_creature(Creature(2)), "party")
        self.assertEqual(len(p.party), 6)
        self.assertEqual(p.add_creature(Creature(3)), "storage")
        self.assertEqual(len(p.party), 6)
        self.assertEqual(len(p.storage), 1)

    def test_storage_has_no_limit(self):
        p = Player.new_game(1)
        for _ in range(30):
            p.add_creature(Creature(4))
        self.assertEqual(len(p.storage), 25)

    def test_alive_party_and_all_fainted(self):
        p = Player.new_game(1)
        p.add_creature(Creature(2))
        self.assertEqual(len(p.alive_party()), 2)
        self.assertFalse(p.all_fainted())
        for c in p.party:
            c.take_damage(999)
        self.assertEqual(p.alive_party(), [])
        self.assertTrue(p.all_fainted())

    def test_heal_all_restores_party(self):
        p = Player.new_game(1)
        p.add_creature(Creature(2))
        for c in p.party:
            c.take_damage(999)
            c.spend_mp(3)
        p.heal_all()
        for c in p.party:
            self.assertEqual(c.hp, c.hp_max)
            self.assertEqual(c.mp, c.mp_max)
            self.assertFalse(c.fainted)


class BagTest(unittest.TestCase):
    """背包。"""

    def test_add_item(self):
        p = Player.new_game(1)
        p.add_item(3)
        self.assertEqual(p.item_count(3), 1)
        p.add_item(3, 4)
        self.assertEqual(p.item_count(3), 5)

    def test_remove_item(self):
        p = Player.new_game(1)
        self.assertTrue(p.remove_item(1, 2))
        self.assertEqual(p.item_count(1), 3)

    def test_remove_item_not_enough_returns_false(self):
        p = Player.new_game(1)
        self.assertFalse(p.remove_item(1, 99))
        self.assertEqual(p.item_count(1), 5)

    def test_item_count_missing_item(self):
        p = Player.new_game(1)
        self.assertEqual(p.item_count(3), 0)


class SaveRoundTripTest(unittest.TestCase):
    """§11 存档。"""

    def _sample_player(self) -> Player:
        p = Player.new_game(1)
        p.add_creature(Creature(5, level=8, exp=12, hp=20, mp=10))
        p.dollars = 1234
        p.add_item(3, 2)
        return p

    def test_to_dict_fields_match_doc(self):
        d = self._sample_player().to_dict()
        self.assertEqual(set(d), {"dollars", "party", "storage", "bag"})

    def test_round_trip_is_identical(self):
        p = self._sample_player()
        d = p.to_dict()
        again = Player.from_dict(d).to_dict()
        self.assertEqual(again, d)

    def test_round_trip_keeps_values(self):
        p = self._sample_player()
        restored = Player.from_dict(p.to_dict())
        self.assertEqual(restored.dollars, p.dollars)
        self.assertEqual(restored.bag, p.bag)
        self.assertEqual(len(restored.party), len(p.party))
        self.assertEqual(restored.party[0].level, p.party[0].level)
        self.assertEqual(restored.party[0].hp, p.party[0].hp)

    def test_from_dict_accepts_string_bag_keys(self):
        """JSON 读回来的背包键是字符串。"""
        d = {"dollars": 300, "party": [], "storage": [],
             "bag": {"1": 5, "2": 2, "4": 1}}
        p = Player.from_dict(d)
        self.assertEqual(p.bag, {1: 5, 2: 2, 4: 1})
        self.assertEqual(p.item_count(1), 5)


if __name__ == "__main__":
    unittest.main()
