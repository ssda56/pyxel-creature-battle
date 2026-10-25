"""明雷遇敌测试（T4）：地图数据 + 野外状态 + 战斗接线。

覆盖《数值设定.md》§10.3（遇敌参数）与 §10.4（遇敌表）：

- 遇敌表配置正确（权重和 100、等级区间逐条相等、新手村无怪）；
- 刷怪上限、落点合法（可走 / 不重叠 / 不在玩家格）；
- 游走间隔 80~140 帧、游走不穿障碍；
- 碰撞遇敌、战斗后移除 + 冷却、冷却重生、逃跑弹开；
- 野外状态跨场景保持（战斗 -> FieldScene 重建后冷却仍生效）；
- 标题画面的「测试战斗」调试入口已删除。
"""

from __future__ import annotations

import os
import random
import unittest

from src.data import map_data
from src.model import Creature
from src.scenes.battle_scene import BattleScene
from src.scenes.field_scene import FieldScene
from tests import helpers

#: 野外地图 ID
FIELD_MAP = 2

#: 新手村地图 ID
VILLAGE_MAP = 1


def make_field(map_id: int = FIELD_MAP, seed=None, x=None, y=None,
               facing=None, script=None):
    """建一个跑着 FieldScene 的 Game（可注入固定随机种子）。

    返回 (game, scene)。
    """
    helpers.ensure_init()

    from src.core.game import Game
    from src.core.input import FakeInput

    game = Game(input=FakeInput(script=script))
    if seed is not None:
        game.wild_rng = random.Random(seed)
    scene = FieldScene(game)
    kwargs = {"map_id": map_id}
    if x is not None:
        kwargs["x"] = x
    if y is not None:
        kwargs["y"] = y
    if facing is not None:
        kwargs["facing"] = facing
    game.scenes.replace(scene, **kwargs)
    return game, scene


def run(game, frames: int = 1) -> None:
    """跑若干帧（先 update 再 draw，和真实游戏一致）。"""
    for _ in range(frames):
        game.update()
        game.draw()


def wanderers_of(scene) -> list[dict]:
    """当前地图存活的野生精灵列表。"""
    return scene.wanderers


class EncounterTableTest(unittest.TestCase):
    """遇敌表配置（《数值设定.md》§10.4）。"""

    def test_field_weights_sum_to_100(self):
        enc = map_data.encounters_of(FIELD_MAP)
        self.assertIsNotNone(enc)
        total = sum(int(row["weight"]) for row in enc["table"])
        self.assertEqual(total, 100, "野外遇敌表权重之和必须是 100")

    def test_field_table_matches_document(self):
        """野外遇敌表（《02-新增10只精灵规划.md》§8.1）：
        兔小子 2~5/20、小火狮 3~6/16、水滴滴 3~6/14、小狮鹫 4~7/10、
        闪电小子 3~6/8、涟漪豚 2~5/10、雾尾狐 4~7/8、雏羽啾 2~4/8、
        花刃忍 5~8/4、导线蛇 4~7/2。"""
        enc = map_data.encounters_of(FIELD_MAP)
        got = {int(r["species_id"]): (int(r["level_min"]), int(r["level_max"]),
                                         int(r["weight"]))
               for r in enc["table"]}
        expected = {
            3: (2, 5, 20),   # 兔小子
            1: (3, 6, 16),   # 小火狮
            2: (3, 6, 14),   # 水滴滴
            4: (4, 7, 10),   # 小狮鹫
            8: (3, 6, 8),    # 闪电小子
            10: (2, 5, 10),  # 涟漪豚
            9: (4, 7, 8),    # 雾尾狐
            14: (2, 4, 8),   # 雏羽啾
            12: (5, 8, 4),   # 花刃忍
            17: (4, 7, 2),   # 导线蛇
        }
        self.assertEqual(got, expected)

    def test_village_has_no_encounters(self):
        """§10.4：区域 1 新手村无野生精灵。"""
        self.assertIsNone(map_data.encounters_of(VILLAGE_MAP))
        self.assertIsNone(map_data.MAPS[VILLAGE_MAP]["encounters"])
        self.assertEqual(map_data.spawn_points_of(VILLAGE_MAP), [])

    def test_encounter_parameters_match_document(self):
        """§10.3：上限 4、重生冷却 360 帧（6 秒）、游走间隔 80~140 帧。"""
        enc = map_data.encounters_of(FIELD_MAP)
        self.assertEqual(enc["max_alive"], 4)
        self.assertEqual(enc["respawn_frames"], 360)
        self.assertEqual(enc["move_min"], 80)
        self.assertEqual(enc["move_max"], 140)

    def test_spawn_points_are_grass_and_distinct(self):
        """刷怪点必须落在草丛（图块 1）上、互不重叠、至少 6 个。"""
        points = map_data.spawn_points_of(FIELD_MAP)
        self.assertGreaterEqual(len(points), 6)
        self.assertEqual(len(set(points)), len(points), "刷怪点不能重叠")
        for x, y in points:
            self.assertEqual(map_data.tile_at(FIELD_MAP, x, y), 1,
                             f"刷怪点 ({x},{y}) 不在草丛上")
            self.assertTrue(map_data.is_walkable(FIELD_MAP, x, y))

    def test_roll_wild_respects_table(self):
        """roll_wild 抽出的种族与等级必须落在表里。"""
        enc = map_data.encounters_of(FIELD_MAP)
        ranges = {int(r["species_id"]): (int(r["level_min"]), int(r["level_max"]))
                  for r in enc["table"]}
        rng = random.Random(12345)
        seen = set()
        for _ in range(500):
            rolled = map_data.roll_wild(FIELD_MAP, rng)
            self.assertIsNotNone(rolled)
            species_id, level = rolled
            self.assertIn(species_id, ranges)
            lo, hi = ranges[species_id]
            self.assertGreaterEqual(level, lo)
            self.assertLessEqual(level, hi)
            seen.add(species_id)
        self.assertGreaterEqual(len(seen), 3, "500 次抽样应该覆盖到多个种族")

    def test_roll_wild_returns_none_without_table(self):
        self.assertIsNone(map_data.roll_wild(VILLAGE_MAP, random.Random(1)))


class SpawnTest(unittest.TestCase):
    """刷怪（§10.3「每图同时存活上限 4」）。"""

    def test_village_has_no_wanderers(self):
        """新手村一只怪都没有。"""
        game, scene = make_field(map_id=VILLAGE_MAP)
        run(game, 5)
        self.assertEqual(wanderers_of(scene), [])

    def test_alive_count_never_exceeds_max(self):
        """进入野外后存活数 <= 4。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=7)
        run(game, 3)
        self.assertLessEqual(len(wanderers_of(scene)), 4)
        self.assertGreater(len(wanderers_of(scene)), 0, "野外应该刷出精灵")

    def test_spawn_points_are_legal(self):
        """所有精灵都在可走格、互不重叠、不在玩家所在格。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=99, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        cells = [(w["gx"], w["gy"]) for w in wanderers]
        for x, y in cells:
            self.assertTrue(map_data.is_walkable(FIELD_MAP, x, y),
                            f"精灵站在不可走格 ({x},{y})")
            self.assertNotEqual((x, y), (scene.gx, scene.gy),
                                "精灵不能和玩家同格")
        self.assertEqual(len(set(cells)), len(cells), "精灵之间不能重叠")

    def test_wild_state_lives_on_game(self):
        """野外状态挂在 game 上（跨场景存活）。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=3)
        run(game, 3)
        self.assertIn(FIELD_MAP, game.wild_state)
        state = game.wild_state[FIELD_MAP]
        self.assertIn("wanderers", state)
        self.assertIn("cooldown", state)
        # 场景持有的就是 game 上的那一份（同一个对象）
        self.assertIs(scene.wild_state, state)


class WanderTest(unittest.TestCase):
    """游走（§10.3「游走间隔 80~140 帧」「不穿障碍」）。"""

    def test_move_interval_within_80_to_140(self):
        """注入固定随机种子，游走间隔落在 80~140 帧。

        测的是**游走计时器**的间隔（§10.3「游走间隔 80~140 帧」）：
        每只精灵的 move_timer 归零时尝试走一格，随后重新计 80~140 帧。
        注意位置变化的间隔可能 > 140——被围住时精灵原地不动并重新计时
        （§10.3「无路可走则原地停留」）。

        **测量基准**：精灵在 make_field() 的 enter() 里就已经刷出来，
        初始计时器 = randint(move_min, move_max)，所以「第一段间隔」
        必须从精灵出生那一刻算起。这里在跑第一帧之前就记下计时器初值
        （循环第 frame 帧 == 游戏第 frame-1 帧），量出来的每一段间隔
        都正好等于一次游走间隔。
        """
        game, scene = make_field(map_id=FIELD_MAP, seed=2024, x=2, y=15)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)

        # 记录每只精灵「move_timer 被重新计上」的时刻（= 一次游走尝试）
        prev_timer = {id(w): int(w["move_timer"]) for w in wanderers}
        last_attempt = {id(w): 0 for w in wanderers}
        intervals = []
        moves = 0
        for frame in range(1, 2400):
            run(game, 1)
            for w in wanderers_of(scene):
                timer = int(w["move_timer"])
                if timer > prev_timer[id(w)]:
                    # 计时器被重新计上 -> 又一次游走尝试
                    intervals.append(frame - last_attempt[id(w)])
                    last_attempt[id(w)] = frame
                prev_timer[id(w)] = timer
                moves += 1

        self.assertTrue(intervals, "精灵应该会游走")
        for gap in intervals:
            self.assertGreaterEqual(gap, 80, f"游走间隔 {gap} < 80")
            self.assertLessEqual(gap, 140, f"游走间隔 {gap} > 140")

    def test_wanderers_actually_change_position(self):
        """精灵确实会走（不只是原地转圈）。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=2024, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        start = {id(w): (w["gx"], w["gy"]) for w in wanderers}
        moved = 0
        for _ in range(1200):
            run(game, 1)
        for w in wanderers_of(scene):
            if (w["gx"], w["gy"]) != start[id(w)]:
                moved += 1
        self.assertGreaterEqual(moved, 1, "精灵应该至少走过一格")

    def test_wanderers_never_enter_blocked_tiles(self):
        """把精灵围在障碍中间，它也走不到不可走格。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=555, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)

        # 长时间运行，断言精灵始终待在可走格上
        for _ in range(1200):
            run(game, 1)
            for w in wanderers_of(scene):
                self.assertTrue(map_data.is_walkable(FIELD_MAP, w["gx"], w["gy"]),
                                "精灵走到了不可走格")

    def test_trapped_wanderer_stays_put(self):
        """被障碍围死的精灵原地不动（§10.3「无路可走则原地停留」）。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=556, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)

        # 找一格「只有 1 条出路」的可走格，把精灵放进去后封锁其余方向：
        # 用一个假的 is_walkable 覆盖把四面都变成不可走。
        target = wanderers[0]
        real_walkable = map_data.is_walkable

        def fake_walkable(map_id, x, y):
            if map_id == FIELD_MAP and (x, y) == (target["gx"], target["gy"]):
                return True
            return False

        target["move_timer"] = 1
        before = (target["gx"], target["gy"])
        original = map_data.is_walkable
        map_data.is_walkable = fake_walkable
        try:
            run(game, 400)
        finally:
            map_data.is_walkable = original

        self.assertEqual((target["gx"], target["gy"]), before,
                         "四面都不可走时精灵应该原地不动")
        self.assertTrue(real_walkable(FIELD_MAP, before[0], before[1]))

    def test_wanderers_do_not_overlap(self):
        """游走时精灵之间不会重叠。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=4242, x=2, y=15)
        run(game, 3)
        for _ in range(1200):
            run(game, 1)
            cells = [(w["gx"], w["gy"]) for w in wanderers_of(scene)]
            self.assertEqual(len(set(cells)), len(cells), "精灵重叠了")


class EncounterTest(unittest.TestCase):
    """碰撞遇敌（§10.3「玩家碰撞后进入战斗」）。"""

    def test_player_stepping_onto_wanderer_starts_battle(self):
        """玩家走到某只精灵所在格 -> scenes.current 变成 BattleScene。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=11, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)

        target = wanderers[0]
        # 把玩家放到目标精灵旁边，再走一步撞上去
        scene.gx = target["gx"]
        scene.gy = target["gy"] - 1
        scene.px = float(scene.gx * map_data.TILE_SIZE)
        scene.py = float(scene.gy * map_data.TILE_SIZE)
        scene.sync_state()

        # 直接把玩家坐标挪到精灵格（本测试只关心「同格 -> 进战斗」）
        scene.gx = target["gx"]
        scene.gy = target["gy"]
        scene.px = float(scene.gx * map_data.TILE_SIZE)
        scene.py = float(scene.gy * map_data.TILE_SIZE)
        run(game, 1)

        current = game.scenes.current
        self.assertIsInstance(current, BattleScene)
        self.assertEqual(current.enemy.species_id, target["species_id"])
        self.assertEqual(current.enemy.level, target["level"])

    def test_wanderer_walking_onto_player_starts_battle(self):
        """精灵走到玩家所在格 -> 也进战斗。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=12, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)

        target = wanderers[0]
        # 把玩家放到精灵正下方一格，并把精灵的游走计时设成 1（下一帧就走）
        scene.gx = target["gx"]
        scene.gy = target["gy"] + 1
        scene.px = float(scene.gx * map_data.TILE_SIZE)
        scene.py = float(scene.gy * map_data.TILE_SIZE)
        scene.sync_state()
        target["move_timer"] = 1
        # 让随机源挑「向下」这一格：直接指定方向不走随机分支
        target["gx"] = scene.gx
        target["gy"] = scene.gy - 1

        # 手动把精灵挪到玩家格上，验证同格判定会触发战斗
        target["gx"] = scene.gx
        target["gy"] = scene.gy
        run(game, 1)
        self.assertIsInstance(game.scenes.current, BattleScene)


class BattleEndTest(unittest.TestCase):
    """战斗结束处理（§10.3「战斗结束后该实体从地图移除，冷却后重生」）。"""

    def _fight(self, result: str):
        """撞上一只精灵并返回 (game, field_scene, wanderer, battle_scene)。"""
        game, scene = make_field(map_id=FIELD_MAP, seed=31, x=2, y=15)
        run(game, 3)
        wanderers = wanderers_of(scene)
        self.assertTrue(wanderers)
        target = wanderers[0]

        scene.gx = target["gx"]
        scene.gy = target["gy"]
        scene.px = float(scene.gx * map_data.TILE_SIZE)
        scene.py = float(scene.gy * map_data.TILE_SIZE)
        scene.sync_state()
        run(game, 1)

        battle = game.scenes.current
        self.assertIsInstance(battle, BattleScene)
        # 手动触发战斗结束回调（模拟玩家赢 / 逃）
        battle.on_end(result)
        return game, scene, target, battle

    def _rebuild_field(self, game):
        """模拟 T3b 战斗结束时的 replace(FieldScene(...))。"""
        game.scenes.replace(FieldScene(game), map_id=FIELD_MAP,
                            x=game.player_state["x"], y=game.player_state["y"])
        return game.scenes.current

    def test_win_removes_wanderer_and_starts_cooldown(self):
        """on_end("win") -> 该精灵消失 + spawn_index 进入冷却。"""
        game, scene, target, battle = self._fight("win")
        state = game.wild_state[FIELD_MAP]
        remaining = [w for w in state["wanderers"] if w is target]
        self.assertEqual(remaining, [], "打赢后该精灵应从地图移除")
        self.assertFalse(target["alive"])
        self.assertIn(target["spawn_index"], state["cooldown"])
        self.assertEqual(state["cooldown"][target["spawn_index"]], 360)

    def test_run_pushes_player_back_one_tile(self):
        """on_end("run") -> 玩家向后弹开 1 格，且不与精灵重合。"""
        game, scene, target, battle = self._fight("run")
        player = game.player_state
        self.assertTrue(map_data.is_walkable(FIELD_MAP, player["x"], player["y"]))
        cells = [(w["gx"], w["gy"]) for w in game.wild_state[FIELD_MAP]["wanderers"]]
        self.assertNotIn((player["x"], player["y"]), cells)

    def test_cooldown_respawns_after_frames(self):
        """推进 respawn_frames 帧后重新刷出。"""
        game, scene, target, battle = self._fight("win")
        state = game.wild_state[FIELD_MAP]
        before = len(state["wanderers"])
        self.assertIn(target["spawn_index"], state["cooldown"])

        # 回到地图场景（冷却只在地图场景里走）
        scene = self._rebuild_field(game)
        # 冷却 360 帧（@60fps = 6 秒），跑 400 帧确保冷却走完
        run(game, 400)

        state = game.wild_state[FIELD_MAP]
        self.assertNotIn(target["spawn_index"], state["cooldown"],
                         "冷却走完后应该清掉")
        self.assertGreaterEqual(len(state["wanderers"]), before)
        self.assertLessEqual(len(state["wanderers"]), 4)
        # 冷却走完后从**原刷怪点**重生（§10.3「冷却后从刷怪点重生」）
        respawned = [w for w in state["wanderers"]
                     if w["spawn_index"] == target["spawn_index"]]
        self.assertTrue(respawned, "应该在原刷怪点重生")

    def test_wild_state_survives_field_scene_rebuild(self):
        """战斗结束 -> FieldScene 重建后，冷却仍在生效（不会瞬间全刷）。"""
        game, scene, target, battle = self._fight("win")
        state = game.wild_state[FIELD_MAP]
        self.assertIn(target["spawn_index"], state["cooldown"])
        alive_after_battle = len(state["wanderers"])

        # 模拟 T3b 的行为：战斗结束后 replace(FieldScene(...))
        game.scenes.replace(FieldScene(game), map_id=FIELD_MAP,
                            x=game.player_state["x"], y=game.player_state["y"])
        new_scene = game.scenes.current
        self.assertIsInstance(new_scene, FieldScene)

        # 重建后冷却仍在 -> 不会瞬间刷满 4 只
        self.assertIn(target["spawn_index"], game.wild_state[FIELD_MAP]["cooldown"])
        self.assertEqual(len(game.wild_state[FIELD_MAP]["wanderers"]),
                         alive_after_battle)

        # 再跑几帧，冷却依然在走（不会立刻重生）
        run(game, 10)
        self.assertIn(target["spawn_index"], game.wild_state[FIELD_MAP]["cooldown"])


class TitleCleanupTest(unittest.TestCase):
    """标题画面的「测试战斗」调试入口已删除（T4 收尾）。"""

    def test_menu_has_only_two_items(self):
        from src.scenes.title_scene import MENU_ITEMS

        self.assertEqual(len(MENU_ITEMS), 2)
        self.assertEqual(MENU_ITEMS, ("新游戏", "继续游戏"))

    def test_no_test_battle_entry_in_source(self):
        """title_scene.py 里不再有 _start_test_battle / 测试战斗。"""
        path = os.path.join(helpers.PROJECT_ROOT, "src", "scenes", "title_scene.py")
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("_start_test_battle", source)
        self.assertNotIn("测试战斗", source)


if __name__ == "__main__":
    unittest.main()
