"""存档读写测试（批 3 / T5，《数值设定.md》§11）。

- round-trip：2 只队伍 + 1 只仓库 + 非默认背包 + 金币 -> 存 -> 读 -> 逐字段相等；
- 原子写入：存完目录里不残留 .tmp；
- 没有存档 -> "no_file"，game 状态不变；
- 版本不兼容 -> "bad_version"，**原文件内容不被改写**；
- 损坏文件 -> "corrupt"，不抛异常；
- 存档 JSON 的字段与 §11 逐字一致（顺序 / 名字 / bag 的键是字符串）。
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

from src.core.game import Game
from src.model import save_io
from src.model.creature import Creature
from src.model.player import Player
from tests import helpers

#: 《数值设定.md》§11 的顶层字段（顺序也是一样的）
DOC_KEYS = ["save_version", "timestamp", "play_seconds", "dollars",
            "player", "party", "storage", "bag"]

#: §11 里 player 的字段
DOC_PLAYER_KEYS = ["map_id", "x", "y", "facing"]

#: §11 里精灵的字段
DOC_CREATURE_KEYS = ["species_id", "nickname", "level", "exp", "hp", "mp",
                     "skills", "atk_mod"]


class SaveIoTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "save1.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------ 造数据
    def _game(self) -> Game:
        """造一个「不默认」的存档数据：2 只队伍 + 1 只仓库 + 非默认背包。"""
        game = Game()
        game.player = Player(
            dollars=777,
            party=[
                Creature(1, level=6, exp=3, hp=20, mp=5, skills=[3, 1]),
                Creature(2, level=7, exp=11, hp=41, mp=18),
            ],
            storage=[Creature(3, level=4, hp=12, mp=7)],
            bag={1: 5, 2: 2, 4: 1, 5: 1},
        )
        game.player_state.update({"map_id": 2, "x": 7, "y": 9, "facing": "left"})
        game.play_frames = 95
        return game

    # ------------------------------------------------------------ round-trip
    def test_round_trip_keeps_player_and_state_equal(self):
        game = self._game()
        self.assertTrue(save_io.save_game(game, self.path))

        other = Game()
        self.assertEqual(save_io.load_game(other, self.path), "ok")

        # 玩家整体逐字段相等
        self.assertEqual(other.player.to_dict(), game.player.to_dict())
        self.assertEqual(other.player.dollars, 777)
        self.assertEqual(other.player.bag, {1: 5, 2: 2, 4: 1, 5: 1})
        self.assertEqual(len(other.player.party), 2)
        self.assertEqual(len(other.player.storage), 1)

        # 精灵逐字段相等（等级 / 经验 / HP / MP / 技能）
        for a, b in zip(other.player.party, game.player.party):
            self.assertEqual(a.species_id, b.species_id)
            self.assertEqual(a.level, b.level)
            self.assertEqual(a.exp, b.exp)
            self.assertEqual(a.hp, b.hp)
            self.assertEqual(a.mp, b.mp)
            self.assertEqual(a.skills, b.skills)
            self.assertEqual(a.nickname, b.nickname)
        self.assertEqual(other.player.storage[0].species_id, 3)
        self.assertEqual(other.player.storage[0].hp, 12)

        # 位置 / 朝向 / 金币
        self.assertEqual(other.player_state["map_id"], 2)
        self.assertEqual(other.player_state["x"], 7)
        self.assertEqual(other.player_state["y"], 9)
        self.assertEqual(other.player_state["facing"], "left")
        self.assertEqual(other.player_state["dollars"], 777)

    def test_round_trip_across_processes(self):
        """跨进程：另起一个解释器读档，逐字段比对。"""
        import subprocess
        import sys

        game = self._game()
        self.assertTrue(save_io.save_game(game, self.path))

        code = (
            "import json, sys;"
            "sys.path.insert(0, r'" + helpers.PROJECT_ROOT + "');"
            "from src.model import save_io;"
            "from src.model.player import Player;"
            "data = json.load(open(r'" + self.path + "', encoding='utf-8'));"
            "p = Player.from_dict({'dollars': data['dollars'],"
            " 'party': data['party'], 'storage': data['storage'],"
            " 'bag': data['bag']});"
            "print(json.dumps({'player': p.to_dict(), 'pos': data['player']},"
            " ensure_ascii=True, sort_keys=True))"
        )
        result = subprocess.run([sys.executable, "-c", code],
                                cwd=helpers.PROJECT_ROOT,
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 0, result.stderr)
        got = json.loads(result.stdout.strip().splitlines()[-1])
        # JSON 里 int 键会变成字符串键，比对前先归一化
        expected = json.loads(json.dumps(game.player.to_dict()))
        self.assertEqual(got["player"], expected)
        self.assertEqual(got["pos"], {"map_id": 2, "x": 7, "y": 9, "facing": "left"})

    # ------------------------------------------------------------ 原子写入
    def test_save_leaves_no_tmp_file(self):
        game = self._game()
        self.assertTrue(save_io.save_game(game, self.path))
        self.assertTrue(os.path.isfile(self.path))
        self.assertFalse(os.path.exists(self.path + ".tmp"))
        self.assertEqual(os.listdir(self.tmp), ["save1.json"])

    def test_save_creates_missing_directory(self):
        game = self._game()
        deep = os.path.join(self.tmp, "a", "b", "save1.json")
        self.assertTrue(save_io.save_game(game, deep))
        self.assertTrue(os.path.isfile(deep))

    # ------------------------------------------------------------ 各种失败
    def test_no_file_returns_no_file_and_keeps_game(self):
        game = self._game()
        result = save_io.load_game(game, self.path)
        self.assertEqual(result, "no_file")
        # game 状态不变
        self.assertEqual(game.player.dollars, 777)
        self.assertEqual(game.player_state["map_id"], 2)

    def test_bad_version_is_reported_and_file_untouched(self):
        payload = {
            "save_version": 999,
            "timestamp": "2026-10-23T23:45:00",
            "play_seconds": 10,
            "dollars": 300,
            "player": {"map_id": 1, "x": 15, "y": 10, "facing": "down"},
            "party": [],
            "storage": [],
            "bag": {},
        }
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        with open(self.path, "rb") as fh:
            before = fh.read()

        game = self._game()
        self.assertEqual(save_io.load_game(game, self.path), "bad_version")
        with open(self.path, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after, "版本不兼容时原文件不能被改写")

    def test_corrupt_file_returns_corrupt(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("{不是合法 json")
        game = self._game()
        self.assertEqual(save_io.load_game(game, self.path), "corrupt")

    def test_empty_file_returns_corrupt(self):
        open(self.path, "w", encoding="utf-8").close()
        game = self._game()
        self.assertEqual(save_io.load_game(game, self.path), "corrupt")

    def test_json_array_is_corrupt(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("[1, 2, 3]")
        game = self._game()
        self.assertEqual(save_io.load_game(game, self.path), "corrupt")

    def test_write_failure_returns_false(self):
        game = self._game()
        # 目录当成文件写 -> 一定失败，但不能抛异常
        bad = os.path.join(self.tmp, "not_a_dir")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("x")
        self.assertFalse(save_io.save_game(game, os.path.join(bad, "save1.json")))

    # ------------------------------------------------------------ 其它接口
    def test_has_save_and_delete_save(self):
        game = self._game()
        self.assertFalse(save_io.has_save(self.path))
        self.assertTrue(save_io.save_game(game, self.path))
        self.assertTrue(save_io.has_save(self.path))
        save_io.delete_save(self.path)
        self.assertFalse(save_io.has_save(self.path))
        # 删不存在的文件也不报错
        save_io.delete_save(self.path)

    def test_play_seconds_is_frames_over_30(self):
        game = self._game()
        game.play_frames = 95
        save_io.save_game(game, self.path)
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["play_seconds"], 3)

    # ------------------------------------------------------------ 存档结构
    def test_saved_json_matches_doc_section_11(self):
        game = self._game()
        save_io.save_game(game, self.path)
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)

        self.assertEqual(list(data.keys()), DOC_KEYS)
        self.assertEqual(data["save_version"], 1)
        self.assertEqual(data["dollars"], 777)
        self.assertEqual(list(data["player"].keys()), DOC_PLAYER_KEYS)
        self.assertEqual(data["player"], {"map_id": 2, "x": 7, "y": 9, "facing": "left"})
        self.assertEqual(len(data["party"]), 2)
        self.assertEqual(len(data["storage"]), 1)
        for creature in data["party"] + data["storage"]:
            self.assertEqual(list(creature.keys()), DOC_CREATURE_KEYS)
        # 背包的键在 JSON 里是字符串
        self.assertEqual(data["bag"], {"1": 5, "2": 2, "4": 1, "5": 1})
        for key in data["bag"]:
            self.assertIsInstance(key, str)

    def test_bag_keys_come_back_as_int(self):
        game = self._game()
        save_io.save_game(game, self.path)
        other = Game()
        save_io.load_game(other, self.path)
        for key in other.player.bag:
            self.assertIsInstance(key, int)

    def test_derived_stats_are_not_stored(self):
        """存档只存源头字段：hp_max / attack 这些派生值不写进去（§11 / D8）。"""
        game = self._game()
        save_io.save_game(game, self.path)
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        for creature in data["party"] + data["storage"]:
            for forbidden in ("hp_max", "mp_max", "attack", "defense", "speed"):
                self.assertNotIn(forbidden, creature)

    def test_player_none_still_saves(self):
        """还没开局（player 是 None）时存档也不能崩。"""
        game = Game()
        self.assertIsNone(game.player)
        self.assertTrue(save_io.save_game(game, self.path))
        with open(self.path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["party"], [])
        self.assertEqual(data["bag"], {})


if __name__ == "__main__":
    unittest.main()
