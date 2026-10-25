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
from src.model.player import PARTY_LIMIT, PARTY_MIN, Player


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


class StorageExchangeTest(unittest.TestCase):
    """队伍 <-> 仓库 互换（README §8.6 缺口）。

    硬规则由数据层保证：

    - 队伍上限 PARTY_LIMIT（6 只）：满了不能再从仓库换进来；
    - 队伍下限 PARTY_MIN（1 只）：只剩一只时不能再移进仓库；
    - 仓库无上限。
    """

    def _player(self, party_size: int = 1, storage_size: int = 0) -> Player:
        """造一个队伍 party_size 只、仓库 storage_size 只的玩家。"""
        p = Player.new_game(1)
        while len(p.party) < party_size:
            p.party.append(Creature(2, level=5))
        while len(p.storage) < storage_size:
            p.storage.append(Creature(3, level=4))
        return p

    # ---------------------------------------------------- 仓库 -> 队伍
    def test_move_to_party_when_party_not_full(self):
        """队伍没满时，仓库 -> 队伍成功，两边数量正确。"""
        p = self._player(party_size=2, storage_size=3)
        creature = p.storage[0]

        self.assertTrue(p.move_to_party(0))

        self.assertEqual(len(p.party), 3)
        self.assertEqual(len(p.storage), 2)
        self.assertIs(p.party[2], creature)
        self.assertNotIn(creature, p.storage)

    def test_move_to_party_rejected_when_party_full(self):
        """队伍满 6 只时，仓库 -> 队伍被拒绝，数量不变。"""
        p = self._player(party_size=PARTY_LIMIT, storage_size=2)
        before_party = list(p.party)
        before_storage = list(p.storage)

        self.assertFalse(p.move_to_party(0))
        self.assertFalse(p.can_move_to_party(0))

        self.assertEqual(len(p.party), PARTY_LIMIT)
        self.assertEqual(len(p.storage), 2)
        self.assertEqual(p.party, before_party)
        self.assertEqual(p.storage, before_storage)

    def test_move_to_party_rejected_on_bad_index(self):
        """下标越界一律拒绝。"""
        p = self._player(party_size=1, storage_size=2)
        self.assertFalse(p.move_to_party(5))
        self.assertFalse(p.move_to_party(-1))
        self.assertEqual(len(p.storage), 2)

    # ---------------------------------------------------- 队伍 -> 仓库
    def test_move_to_storage_when_party_has_more_than_one(self):
        """队伍多于 1 只时，队伍 -> 仓库成功。"""
        p = self._player(party_size=3, storage_size=1)
        creature = p.party[1]

        self.assertTrue(p.move_to_storage(1))

        self.assertEqual(len(p.party), 2)
        self.assertEqual(len(p.storage), 2)
        self.assertIs(p.storage[-1], creature)
        self.assertNotIn(creature, p.party)

    def test_move_to_storage_rejected_when_only_one_left(self):
        """队伍只剩 1 只时，队伍 -> 仓库被拒绝，数量不变。"""
        p = self._player(party_size=1, storage_size=2)
        before_party = list(p.party)
        before_storage = list(p.storage)

        self.assertFalse(p.move_to_storage(0))
        self.assertFalse(p.can_move_to_storage(0))

        self.assertEqual(len(p.party), 1)
        self.assertEqual(len(p.storage), 2)
        self.assertEqual(p.party, before_party)
        self.assertEqual(p.storage, before_storage)

    def test_move_to_storage_rejected_on_bad_index(self):
        p = self._player(party_size=2, storage_size=0)
        self.assertFalse(p.move_to_storage(9))
        self.assertFalse(p.move_to_storage(-1))
        self.assertEqual(len(p.party), 2)

    # ---------------------------------------------------- 往返
    def test_round_trip_move_keeps_same_creature(self):
        """来回搬一次，精灵对象还是同一只。"""
        p = self._player(party_size=2, storage_size=1)
        creature = p.storage[0]
        self.assertTrue(p.move_to_party(0))
        self.assertIs(p.party[-1], creature)
        self.assertTrue(p.move_to_storage(len(p.party) - 1))
        self.assertIs(p.storage[-1], creature)
        self.assertEqual(len(p.party), 2)
        self.assertEqual(len(p.storage), 1)

    def test_storage_has_no_upper_limit(self):
        """仓库无上限：反复搬进搬出都能超过 6 只。"""
        p = self._player(party_size=1, storage_size=0)
        for _ in range(12):
            p.storage.append(Creature(4, level=3))
        self.assertEqual(len(p.storage), 12)
        # 队伍满了就搬不动，但仓库照旧无限
        p.party.append(Creature(2, level=5))
        self.assertTrue(p.move_to_storage(0))
        self.assertEqual(len(p.storage), 13)

    # ---------------------------------------------------- 存档往返
    def test_save_round_trip_after_exchange(self):
        """搬动之后存档往返，队伍与仓库内容一致。"""
        p = self._player(party_size=3, storage_size=2)
        self.assertTrue(p.move_to_party(0))        # 仓库 -> 队伍
        self.assertTrue(p.move_to_storage(0))      # 队伍 -> 仓库

        restored = Player.from_dict(p.to_dict())

        self.assertEqual(len(restored.party), len(p.party))
        self.assertEqual(len(restored.storage), len(p.storage))
        self.assertEqual([c.species_id for c in restored.party],
                         [c.species_id for c in p.party])
        self.assertEqual([c.species_id for c in restored.storage],
                         [c.species_id for c in p.storage])
        self.assertEqual([c.level for c in restored.storage],
                         [c.level for c in p.storage])
        self.assertEqual(restored.to_dict(), p.to_dict())

    def test_party_min_constant(self):
        self.assertEqual(PARTY_MIN, 1)
        self.assertEqual(Player.PARTY_MIN, 1)


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
