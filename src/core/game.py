"""App 主类：update / draw 分发到当前场景（规划文档 §二 core/game.py）。

职责
----
- 启动时加载字体、烘焙全部素材；
- 持有场景栈（SceneManager）与输入（Input）；
- 每帧把 update / draw 分发给当前场景。

`self.input` 默认是 `RealInput()`，测试时可以直接替换成 `FakeInput`：

    game = Game()
    game.input = FakeInput(script=[{"confirm": 3}])
"""

from __future__ import annotations

import os
import traceback

import pyxel

from src.assets_gen import sprite_base
from src.core import focus
from src.core.input import ACTIONS, Input, RealInput
from src.core.scene_manager import SceneManager
from src.data import map_data
from src.scenes.title_scene import TitleScene
from src.ui import text


#: 运行日志路径（项目根/_runtime_log.txt）；`--debug-input` 时启用
_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "_runtime_log.txt",
)


class Game:
    """游戏主对象。"""

    #: 运行日志文件句柄（None 表示未启用）
    _log_file = None
    #: 日志采样间隔（帧）
    LOG_EVERY = 10
    #: 自己维护的帧计数（headless 手动循环时 pyxel.frame_count 不推进）
    _frame_no = 0
    #: 上一帧的焦点状态（None = 还没测过）
    _last_focus: bool | None = None
    #: 上次尝试抢焦点的帧号
    _last_refocus: int = -1000

    def __init__(self, input: Input | None = None):
        # 字体与素材必须先准备好，后面任何一帧绘制都要用
        text.init_font()
        sprite_base.bake_all()

        #: 输入源，测试可替换
        self.input: Input = input if input is not None else RealInput()
        #: 场景栈
        self.scenes = SceneManager()
        #: 玩家状态（存档 / HUD 读它；后续批次继续扩字段）
        # 初始金币 300（《数值设定.md》§7.1），起始地图 1 新手村
        # （出生点 15, 10，与 §11 存档格式里的 player 字段一致）。
        self.player_state: dict = {
            "dollars": 300,
            "map_id": map_data.START_MAP_ID,
            "x": 15,
            "y": 10,
            "facing": "down",
        }

        if RealInput.DEBUG:
            try:
                self._log_file = open(_LOG_PATH, "w", encoding="utf-8")
                self._log("=== 运行日志开始 ===")
            except OSError:
                self._log_file = None

        self.scenes.push(TitleScene(self))

    # ------------------------------------------------------------ 运行日志
    def _log(self, text: str) -> None:
        """写一行运行日志并立刻落盘（进程被杀也能留下）。"""
        if self._log_file is None:
            return
        try:
            self._log_file.write(text + "\n")
            self._log_file.flush()
        except OSError:
            self._log_file = None

    # ------------------------------------------------------------ 每帧
    def update(self) -> None:
        """分发一帧逻辑更新。

        顺序：先跑场景逻辑，再让输入推进到下一帧
        （这样第 N 帧的场景看到的就是第 N 帧的输入状态）。
        """
        scene = self.scenes.current
        if scene is not None:
            try:
                scene.update(self.input)
            except Exception:
                # 把异常写进日志再抛出：PyCharm 控制台的输出可能看不到，
                # 但日志文件一定留下完整 traceback。
                self._log(f"!!! 场景 update 抛异常 (scene={type(scene).__name__})")
                self._log(traceback.format_exc())
                raise
        self.input.update()
        self._frame_no += 1
        self._watch_focus()
        self._log_tick(scene)

    def _watch_focus(self) -> None:
        """监控窗口焦点：记录丢失事件，并在诊断模式下自动抢回。

        窗口一旦不是前台窗口，SDL 就收不到键盘事件——画面照常、人物不走。
        诊断模式（`RealInput.DEBUG`）下每 2 秒尝试抢回一次。
        """
        if not RealInput.DEBUG:
            return
        now = focus.is_focused()
        if self._last_focus is None:
            self._last_focus = now
            self._log(f"FOCUS_INIT={int(now)}")
            return
        if now != self._last_focus:
            self._log(f"FOCUS {'GAINED' if now else 'LOST'} at f={self._frame_no}")
            self._last_focus = now
        if not now and self._frame_no - self._last_refocus >= 60:
            self._last_refocus = self._frame_no
            ok = focus.grab_focus()
            self._log(f"REFOCUS_TRY f={self._frame_no} ok={int(ok)}")

    def draw(self) -> None:
        """分发一帧绘制。"""
        scene = self.scenes.current
        if scene is not None:
            scene.draw()
        if RealInput.DEBUG:
            self._draw_debug_overlay()

    def _log_tick(self, scene) -> None:
        """每 LOG_EVERY 帧记录一次运行状态。"""
        if self._log_file is None or self._frame_no % self.LOG_EVERY:
            return
        held = [a for a in ACTIONS if self.input.held(a)]
        seen = getattr(self.input, "seen_count", "-")
        parts = [
            f"f={self._frame_no}",
            f"scn={type(scene).__name__ if scene else 'None'}",
            f"seen={seen}",
            f"held={','.join(held) or '-'}",
        ]
        for attr in ("facing", "moving", "gx", "gy"):
            if scene is not None and hasattr(scene, attr):
                parts.append(f"{attr}={getattr(scene, attr)}")
        fade = getattr(scene, "fade", None) if scene is not None else None
        if fade is not None:
            parts.append(f"fade={int(fade.is_active)}|{fade.level}")
        parts.append(f"focus={int(focus.is_focused())}")
        self._log(" ".join(parts))

    # ------------------------------------------------------------ 诊断
    def _draw_debug_overlay(self) -> None:
        """把输入与场景状态画在屏幕上（`--debug-input` 时启用）。

        用来在不看终端的情况下判断：按键到底有没有被收到（held/prs 两行），
        以及场景卡在什么状态（fade / moving / facing）。
        """
        held = [a for a in ACTIONS if self.input.held(a)]
        pressed = [a for a in ACTIONS if self.input.pressed(a)]
        cur = self.scenes.current
        rows = [
            f"scn {type(cur).__name__ if cur else 'None'}",
            f"held {','.join(held) if held else '-'}",
            f"prs  {','.join(pressed) if pressed else '-'}",
        ]
        if isinstance(self.input, RealInput):
            last = self.input.last_action or "-"
            rows.append(f"seen={self.input.seen_count} last={last}@{self.input.last_frame}")
        rows.append(f"focus={int(focus.is_focused())}")
        head = []
        for attr in ("facing", "moving"):
            if cur is not None and hasattr(cur, attr):
                head.append(f"{attr}={getattr(cur, attr)}")
        tail = []
        for attr in ("gx", "gy", "map_id"):
            if cur is not None and hasattr(cur, attr):
                tail.append(f"{attr}={getattr(cur, attr)}")
        fade = getattr(cur, "fade", None) if cur is not None else None
        if fade is not None:
            tail.append(f"fade={int(fade.is_active)}|{fade.level}")
        if head:
            rows.append(" ".join(head))
        if tail:
            rows.append(" ".join(tail))

        y = 2
        for row in rows:
            pyxel.rect(0, y - 1, 240, 12, 0)
            text.draw(2, y, row, 7)
            y += 12
