"""音效 / BGM / 静音测试（T8b · M7 收尾）。

覆盖任务书里的验收点：

- sound.init() 在无头环境下**不抛异常**，并且**幂等**；
- 每个音效名都能播（monkeypatch pyxel.play 计数），**未知名字安静忽略**；
- BGM：新手村 / 野外 = field，洞窟 = cave，战斗 = battle，
  **同一首正在播不会重启**；
- 按 M 静音后 pyxel.play 不再被调用，取消静音后恢复；
- 战斗里的伤害路径**真的**调用了 sound.play_sfx；
- 连跑 300 帧不崩。
"""

from __future__ import annotations

import os
import sys
import unittest

import pyxel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.input import ACTIONS, keys_of  # noqa: E402
from src.ui import sound  # noqa: E402
from tests import battle_helpers, field_helpers, helpers  # noqa: E402

#: 两个 ogg 的字节数（与素材目录里的原文件一致）
BGM1_SIZE = 356191
BGM2_SIZE = 375740


class SoundTestBase(unittest.TestCase):
    """公共准备：无头初始化 + 记录 pyxel.play / pyxel.stop 的调用。"""

    def setUp(self) -> None:
        helpers.ensure_init()
        sound.init()
        # BGM 状态清干净，保证「同一首不重启」的判定不受上一个用例影响
        sound.reset()
        self.calls: list[tuple] = []
        self._old_play = pyxel.play
        self._old_stop = pyxel.stop
        pyxel.play = self._record_play
        pyxel.stop = self._record_stop
        self._muted_before = sound.is_muted()

    def tearDown(self) -> None:
        pyxel.play = self._old_play
        pyxel.stop = self._old_stop
        sound.set_mute(self._muted_before)
        sound.reset()
        sound.reset_init()
        sound.init()

    # ------------------------------------------------------------ 记录器
    def _record_play(self, *args, **kwargs) -> None:
        self.calls.append(("play",) + args)

    def _record_stop(self, *args, **kwargs) -> None:
        self.calls.append(("stop",) + args)

    # ------------------------------------------------------------ 工具
    def plays(self) -> list[tuple]:
        """所有 play 调用。"""
        return [c for c in self.calls if c[0] == "play"]

    def play_args(self) -> list[tuple]:
        """所有 play 调用的 (通道, 声音) 部分。"""
        return [c[1:3] for c in self.plays()]


class AssetTest(SoundTestBase):
    """音频素材入库。"""

    def test_bgm_files_exist_with_expected_size(self) -> None:
        for name, size in (("bgm1.ogg", BGM1_SIZE), ("bgm2.ogg", BGM2_SIZE)):
            path = os.path.join(sound.AUDIO_DIR, name)
            self.assertTrue(os.path.isfile(path), f"缺少素材 {path}")
            self.assertEqual(os.path.getsize(path), size,
                             f"{name} 的大小与原文件不一致")


class InitTest(SoundTestBase):
    """init()。"""

    def test_init_does_not_raise(self) -> None:
        sound.init()          # 不抛异常
        sound.init()          # 幂等
        self.assertTrue(sound.is_initialized())

    def test_init_is_available_in_headless(self) -> None:
        # 无头环境下 Pyxel 的音频接口本身是可用的
        self.assertTrue(sound.is_available(),
                        "无头环境下音频应该可用（否则音效全部变 no-op）")

    def test_unavailable_audio_is_silent_noop(self) -> None:
        """音频不可用时所有播放都变 no-op（不崩、不调用 pyxel.play）。"""
        old = sound._available
        sound._available = False
        try:
            sound.play_sfx("confirm")
            sound.play_bgm("field")
            sound.stop_bgm()
        finally:
            sound._available = old
        self.assertEqual(self.plays(), [], "音频不可用时不应该播放任何声音")

    def test_init_degrades_when_bgm_asset_missing(self) -> None:
        """素材缺失时 init() 不抛异常，并安静降级成「不可用」。"""
        old_files = dict(sound.BGM_FILES)
        old_dir = sound.AUDIO_DIR
        try:
            sound.BGM_FILES[60] = "不存在的文件.ogg"
            sound.reset_init()
            sound.init()                       # 不抛异常
            self.assertFalse(sound.is_available(), "素材缺失时应该不可用")
            # 降级后播放全是 no-op
            sound.play_sfx("confirm")
            sound.play_bgm("field")
            self.assertEqual(self.plays(), [])
        finally:
            sound.BGM_FILES.clear()
            sound.BGM_FILES.update(old_files)
            sound.AUDIO_DIR = old_dir
            sound.reset_init()
            sound.init()
        self.assertTrue(sound.is_available())


class SfxTest(SoundTestBase):
    """音效。"""

    def test_every_sfx_name_plays(self) -> None:
        if not sound.is_available():
            self.skipTest("本机音频不可用")
        for name in sound.SFX_NAMES:
            self.calls.clear()
            sound.play_sfx(name)
            self.assertEqual(len(self.plays()), 1, f"音效 {name} 没播")
            channel, index = self.play_args()[0]
            self.assertEqual(index, sound.SFX_SPECS[name][0])
            self.assertEqual(channel, sound.SFX_SPECS[name][2])

    def test_unknown_sfx_name_is_ignored(self) -> None:
        sound.play_sfx("不存在的音效")
        sound.play_sfx("")
        self.assertEqual(self.plays(), [], "未知音效名不应该播放任何声音")

    def test_sfx_channels_are_separated_from_bgm(self) -> None:
        for name, (_index, _mml, channel) in sound.SFX_SPECS.items():
            self.assertIn(channel, sound.SFX_CHANNELS, f"{name} 用错了通道")
        self.assertNotIn(sound.BGM_CHANNEL, sound.SFX_CHANNELS)


class BgmTest(SoundTestBase):
    """BGM 切换。"""

    def test_play_bgm_uses_bgm_channel(self) -> None:
        sound.play_bgm("field")
        self.assertEqual(self.play_args(), [(sound.BGM_CHANNEL,
                                             sound.BGM_SPECS["field"])])

    def test_same_bgm_is_not_restarted(self) -> None:
        sound.play_bgm("field")
        sound.play_bgm("field")
        sound.play_bgm("field")
        self.assertEqual(len(self.plays()), 1, "同一首 BGM 不应该重启")

    def test_switching_bgm_plays_again(self) -> None:
        sound.play_bgm("field")
        sound.play_bgm("cave")
        self.assertEqual(len(self.plays()), 2)
        self.assertEqual(self.play_args()[1],
                         (sound.BGM_CHANNEL, sound.BGM_SPECS["cave"]))

    def test_unknown_bgm_name_is_ignored(self) -> None:
        sound.play_bgm("不存在的曲子")
        self.assertEqual(self.plays(), [])

    def test_stop_bgm_stops_channel(self) -> None:
        sound.play_bgm("field")
        self.calls.clear()
        sound.stop_bgm()
        self.assertTrue(any(c[0] == "stop" and c[1] == sound.BGM_CHANNEL
                            for c in self.calls))
        self.assertIsNone(sound.current_bgm())

    def test_field_scene_bgm_by_map(self) -> None:
        """新手村 / 野外 = field，洞窟 = cave。"""
        for map_id, expected in ((1, "field"), (2, "field"), (3, "cave")):
            with self.subTest(map_id=map_id):
                sound.reset()
                self.calls.clear()
                field_helpers.make_field(map_id=map_id)
                self.assertEqual(sound.requested_bgm(), expected)
                self.assertEqual(len(self.plays()), 1)
                self.assertEqual(self.play_args()[0],
                                 (sound.BGM_CHANNEL, sound.BGM_SPECS[expected]))

    def test_battle_scene_plays_battle_bgm(self) -> None:
        sound.reset()
        self.calls.clear()
        battle_helpers.make_battle(enemy_species=3, seed=1)
        self.assertEqual(sound.requested_bgm(), "battle")
        self.assertEqual(len(self.plays()), 1)
        self.assertEqual(self.play_args()[0],
                         (sound.BGM_CHANNEL, sound.BGM_SPECS["battle"]))


class MuteTest(SoundTestBase):
    """静音。"""

    def test_mute_blocks_all_playback(self) -> None:
        sound.set_mute(True)
        self.assertTrue(sound.is_muted())
        self.calls.clear()
        sound.play_sfx("confirm")
        sound.play_bgm("field")
        self.assertEqual(self.plays(), [], "静音时不应该有任何播放")

    def test_unmute_restores_playback(self) -> None:
        sound.set_mute(True)
        sound.set_mute(False)
        self.assertFalse(sound.is_muted())
        self.calls.clear()
        sound.play_sfx("confirm")
        self.assertEqual(len(self.plays()), 1)

    def test_toggle_mute_returns_new_state(self) -> None:
        before = sound.is_muted()
        self.assertEqual(sound.toggle_mute(), not before)
        self.assertEqual(sound.toggle_mute(), before)

    def test_mute_action_is_bound_to_m(self) -> None:
        self.assertIn("mute", ACTIONS)
        self.assertEqual(keys_of("mute"), (pyxel.KEY_M,))

    def test_pressing_m_toggles_mute_in_game(self) -> None:
        from src.core.game import Game
        from src.core.input import FakeInput

        game = Game(input=FakeInput(script=[{"mute": 1}]))
        before = sound.is_muted()
        game.update()
        self.assertEqual(sound.is_muted(), not before, "按 M 应该切换静音")
        game.input = FakeInput(script=[{"mute": 1}])
        game.update()
        self.assertEqual(sound.is_muted(), before, "再按 M 应该切回来")

    def test_mute_hint_is_shown_and_fades(self) -> None:
        from src.core.game import Game
        from src.core.input import FakeInput

        game = Game(input=FakeInput(script=[{"mute": 1}]))
        game.update()
        self.assertGreater(game.mute_hint_timer, 0, "切换静音后应该给个提示")
        for _ in range(game.mute_hint_timer + 2):
            game.update()
        self.assertEqual(game.mute_hint_timer, 0, "提示 60 帧后应该消失")


class WiringTest(SoundTestBase):
    """接线：场景里真的调用了 sound.play_sfx / play_bgm。"""

    def _record_sfx(self, names: list[str]):
        """把 sound.play_sfx 换成记录器，返回原函数。"""
        original = sound.play_sfx

        def spy(name):
            names.append(name)
            original(name)

        return original, spy

    def test_battle_damage_path_plays_hit_sound(self) -> None:
        from src.data import skill_data as sk

        game, scene, enemy = battle_helpers.make_battle(enemy_species=3, seed=1)
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            # 我方打敌方：伤害路径 -> hit / hit_super
            damage_skill = None
            for sid in scene.active.skills:
                info = sk.get_skill(sid)
                if info.effect == "damage":
                    damage_skill = info
                    break
            self.assertIsNotNone(damage_skill, "出战精灵没有攻击技能")
            scene._apply_attack(scene.active, enemy, damage_skill)
            self.assertIn(names[-1], ("hit", "hit_super"),
                          f"攻击命中应该播 hit / hit_super，实际 {names}")
            # 敌方打我方：伤害路径 -> hurt
            names.clear()
            scene._apply_attack(enemy, scene.active, damage_skill)
            self.assertEqual(names[-1], "hurt", "我方受击应该播 hurt")
        finally:
            sound.play_sfx = original

    def test_level_up_sound(self) -> None:
        """升级时播 level_up（胜利结算 / 捕捉后升级两条路径）。"""
        from src.model import Creature

        game, scene, enemy = battle_helpers.make_battle(enemy_species=3, seed=1)
        creature = Creature(scene.active.species_id, level=5)
        creature.exp = creature.exp_needed() - 1 if hasattr(creature, "exp_needed") else 0
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            events = creature.gain_exp(1000)
            self.assertTrue(any(str(e).startswith("升到") for e in events),
                            f"应该升级了，实际 {events}")
            scene._play_level_up(events)
            self.assertIn("level_up", names, "升级应该播 level_up")
        finally:
            sound.play_sfx = original

    def test_battle_flow_plays_sfx(self) -> None:
        game, scene, enemy = battle_helpers.make_battle(enemy_species=3, seed=1)
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            for _ in range(12):
                battle_helpers.press(game, "confirm")
        finally:
            sound.play_sfx = original
        self.assertTrue(names, "战斗流程里应该播过音效")
        self.assertTrue(any(n in ("hit", "hit_super", "hurt") for n in names),
                        f"战斗流程里应该播命中音，实际 {names}")

    def test_field_scene_plays_sfx_on_events(self) -> None:
        game, scene = field_helpers.make_field(map_id=1)
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            # 打开菜单 -> confirm
            field_helpers.run(game, 1)
            from src.core.input import FakeInput
            game.input = FakeInput(script=[{"menu": 1}])
            field_helpers.run(game, 1)
            self.assertIn("confirm", names, "打开菜单应该播确认音")
        finally:
            sound.play_sfx = original

    def test_field_scene_plays_encounter_and_heal(self) -> None:
        from src.core.input import FakeInput

        game, scene = field_helpers.make_field(map_id=1)
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            # 遇敌：撞上野生精灵 -> encounter
            scene._start_battle({"species_id": 1, "level": 3, "gx": scene.gx,
                                  "gy": scene.gy, "alive": True,
                                  "spawn_index": 0})
            self.assertIn("encounter", names, "遇敌应该播 encounter")
            # 治疗 -> heal
            names.clear()
            scene._start_heal({"name": "护士", "kind": "heal"})
            self.assertIn("heal", names, "治疗应该播 heal")
        finally:
            sound.play_sfx = original

    def test_title_menu_plays_cursor_and_confirm(self) -> None:
        from src.core.game import Game
        from src.core.input import FakeInput

        game = Game(input=FakeInput(script=[{"down": 1}]))
        names: list[str] = []
        original, spy = self._record_sfx(names)
        sound.play_sfx = spy
        try:
            game.update()
            self.assertIn("cursor", names, "标题画面移动光标应该播 cursor")
            names.clear()
            game.input = FakeInput(script=[{"confirm": 1}])
            game.update()
            self.assertIn("confirm", names, "标题画面确认应该播 confirm")
        finally:
            sound.play_sfx = original


class StabilityTest(SoundTestBase):
    """长时间跑不崩。"""

    def test_run_300_frames_in_field(self) -> None:
        game, scene = field_helpers.make_field(map_id=2)
        field_helpers.run(game, 300)

    def test_run_300_frames_in_title(self) -> None:
        from src.core.game import Game
        from src.core.input import FakeInput

        game = Game(input=FakeInput(script=[{"down": 2, "confirm": 2}]))
        for _ in range(300):
            game.update()
            game.draw()


if __name__ == "__main__":
    unittest.main()
