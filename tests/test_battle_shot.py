"""战斗画面截图（docs/shots/batch2_battle_*.png）。

四张：

- batch2_battle_command.png：五指令界面；
- batch2_battle_skill.png：技能列表（含一个 MP 不足被置灰的招）；
- batch2_battle_damage.png：攻击后的圆圈飘字；
- batch2_battle_status.png：双方信息框 + HP/MP 双条（4 倍放大当特写）。
"""

from __future__ import annotations

import os
import unittest

from tests import battle_helpers as bh
from tests import helpers

SHOTS_DIR = os.path.join(helpers.PROJECT_ROOT, "docs", "shots")
COMMAND_SHOT = os.path.join(SHOTS_DIR, "batch2_battle_command.png")
SKILL_SHOT = os.path.join(SHOTS_DIR, "batch2_battle_skill.png")
DAMAGE_SHOT = os.path.join(SHOTS_DIR, "batch2_battle_damage.png")
STATUS_SHOT = os.path.join(SHOTS_DIR, "batch2_battle_status.png")

#: 独角兽 Lv5 SPD 13 < 小火狮 Lv5 SPD 14 -> 我方先手，飘字先出现在敌方身上
FASTER_ENEMY = 5


class BattleShotTest(unittest.TestCase):
    def setUp(self):
        helpers.ensure_init()

    def _shot(self, game, path, scale=2, frames=2):
        helpers.run_frames(game.update, game.draw, frames,
                           shot_path=path, scale=scale)
        self.assertTrue(os.path.exists(path), "截图没有生成：" + path)
        self.assertGreater(os.path.getsize(path), 1000)

    def test_command_screenshot(self):
        game, scene, enemy = bh.make_battle()
        bh.press(game, "confirm")      # INTRO -> COMMAND
        self.assertEqual(scene.state, "COMMAND")
        self._shot(game, COMMAND_SHOT, scale=2)
        self.assertEqual(helpers.png_size(COMMAND_SHOT), (480, 432))

    def test_skill_screenshot_has_greyed_skill(self):
        game, scene, enemy = bh.make_battle()
        scene.active.mp = 0             # 火花（MP 4）置灰
        bh.press(game, "confirm")      # INTRO -> COMMAND
        bh.press(game, "confirm")      # -> SKILL_SELECT
        self.assertEqual(scene.state, "SKILL_SELECT")
        self._shot(game, SKILL_SHOT, scale=2)
        self.assertEqual(helpers.png_size(SKILL_SHOT), (480, 432))

    def test_damage_screenshot(self):
        # 伤害有浮动（走无种子 RNG 的话每次不同），固定 seed 才能保证截图可复现
        game, scene, enemy = bh.make_battle(enemy_species=FASTER_ENEMY, seed=1)
        bh.press(game, "confirm")      # INTRO -> COMMAND
        bh.press(game, "confirm")      # -> SKILL_SELECT
        bh.press(game, "down")         # 撞击
        bh.press(game, "confirm")      # 使用
        bh.press(game, "confirm")      # 伤害结算（飘字出现）
        self.assertEqual(scene.numbers.count, 1)
        bh.idle(game, 10)              # 让飘字往上飘一点（10 帧 @60fps = 原来的 5 帧 @30fps）
        self._shot(game, DAMAGE_SHOT, scale=2)
        self.assertEqual(helpers.png_size(DAMAGE_SHOT), (480, 432))

    def test_status_screenshot_is_zoomed(self):
        game, scene, enemy = bh.make_battle(enemy_species=FASTER_ENEMY)
        bh.press(game, "confirm")      # INTRO -> COMMAND
        self._shot(game, STATUS_SHOT, scale=4)
        self.assertEqual(helpers.png_size(STATUS_SHOT), (960, 864))


if __name__ == "__main__":
    unittest.main()
