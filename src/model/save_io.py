"""存档读写（《数值设定.md》§11）。

存档路径
--------
    项目根/saves/save1.json

格式
----
严格按《数值设定.md》§11 的字段顺序与结构::

    {
      "save_version": 1,
      "timestamp": "2026-10-23T23:45:00",
      "play_seconds": 1234,
      "dollars": 300,
      "player": {"map_id": 1, "x": 15, "y": 10, "facing": "down"},
      "party":    [ {...}, ... ],
      "storage":  [ ... ],
      "bag":      {"1": 5, "2": 2, "4": 1}
    }

设计要点
--------
1. **只存源头字段**：精灵只存 species_id / nickname / level / exp / hp / mp /
   skills / atk_mod，上限值（hp_max / attack …）一律读档时按等级**重新派生**
   （《数值设定.md》§11 / D8）。
2. **原子写入**：先写同目录的 ".tmp" 文件，写完再 os.replace 覆盖正式文件。
   写一半掉电不会把旧存档弄坏，正式文件也不会残留 .tmp。
3. **读档不抛异常**：文件不存在 -> "no_file"；版本对不上 -> "bad_version"；
   JSON 坏了 -> "corrupt"。三种情况都**不修改**原文件。
4. **就地恢复**：load_game() 只往传入的 game 对象里塞数据，不新建 Game。

本模块**不 import 任何 UI / 引擎模块**（src/model 的硬性约束）。
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from src.model.player import Player

#: 项目根目录（本文件在 <项目根>/src/model/save_io.py）
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 存档目录（《数值设定.md》§11「存档路径：项目根/saves/save1.json」）
SAVE_DIR = os.path.join(PROJECT_ROOT, "saves")

#: 存档文件路径（**运行时读全局**，测试可以临时改掉它）
SAVE_PATH = os.path.join(SAVE_DIR, "save1.json")

#: 存档格式版本（《数值设定.md》§11 的 save_version）
SAVE_VERSION = 1

#: 游戏帧率（《数值设定.md》§13 / main.py 锁定 30 fps）
FPS = 30

#: 读档结果码
RESULT_OK = "ok"
RESULT_NO_FILE = "no_file"
RESULT_BAD_VERSION = "bad_version"
RESULT_CORRUPT = "corrupt"


# ---------------------------------------------------------------- 路径
def resolve_path(path: str | None = None) -> str:
    """返回本次操作要用的存档路径。

    参数
    ----
    path
        显式路径；给 None 时用模块级 SAVE_PATH
        （**调用时**才读全局，所以测试可以临时替换它）。
    """
    if path is None:
        path = SAVE_PATH
    return os.path.abspath(str(path))


def has_save(path: str | None = None) -> bool:
    """存档文件是否存在。"""
    return os.path.isfile(resolve_path(path))


def delete_save(path: str | None = None) -> None:
    """删除存档文件；文件不存在时静默返回。"""
    target = resolve_path(path)
    try:
        os.remove(target)
    except FileNotFoundError:
        pass
    except OSError:
        pass


# ---------------------------------------------------------------- 组装
def _player_of(game):
    """取 game 上的玩家对象（没有就返回 None）。"""
    return getattr(game, "player", None)


def _state_of(game) -> dict:
    """取 game.player_state（没有就返回一个空 dict）。"""
    state = getattr(game, "player_state", None)
    if not isinstance(state, dict):
        state = {}
        try:
            game.player_state = state
        except AttributeError:      # pragma: no cover - 极端情况
            pass
    return state


def build_save_dict(game) -> dict:
    """把 game 的当前状态组装成《数值设定.md》§11 的存档字典。

    返回的 dict 可以直接 json.dump()（背包的 int 键会被 JSON 自动转成
    字符串键，读回来时 Player.from_dict() 会再转回 int）。
    """
    player = _player_of(game)
    state = _state_of(game)

    if player is not None:
        party = [c.to_dict() for c in player.party]
        storage = [c.to_dict() for c in player.storage]
        bag = {k: player.bag[k] for k in sorted(player.bag)}
        dollars = int(player.dollars)
    else:
        party = []
        storage = []
        bag = {}
        dollars = int(state.get("dollars", 0))

    play_frames = int(getattr(game, "play_frames", 0) or 0)

    return {
        "save_version": SAVE_VERSION,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "play_seconds": max(0, play_frames // FPS),
        "dollars": dollars,
        "player": {
            "map_id": int(state.get("map_id", 1)),
            "x": int(state.get("x", 0)),
            "y": int(state.get("y", 0)),
            "facing": str(state.get("facing", "down")),
        },
        "party": party,
        "storage": storage,
        "bag": bag,
    }


# ---------------------------------------------------------------- 写档
def save_game(game, path: str | None = None) -> bool:
    """把 game 的当前状态写进存档文件。

    参数
    ----
    game
        Game 实例（读 player / player_state / play_frames）。
    path
        存档路径；None 时用 SAVE_PATH。

    返回
    ----
    bool
        True 表示写成功；False 表示失败（权限不足 / 磁盘满等）。

    写盘方式：**先写 .tmp 再 os.replace**（原子替换），
    所以任何时刻存档文件要么是旧的完整内容，要么是新的完整内容。
    """
    target = resolve_path(path)
    tmp = target + ".tmp"

    try:
        data = build_save_dict(game)
    except (TypeError, ValueError, KeyError):
        return False

    try:
        folder = os.path.dirname(target)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:       # pragma: no cover - 某些文件系统不支持
                pass
        os.replace(tmp, target)
        return True
    except (OSError, TypeError, ValueError):
        # 写失败：清掉半截的 .tmp，正式文件保持原样
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:           # pragma: no cover
            pass
        return False


# ---------------------------------------------------------------- 读档
def load_game(game, path: str | None = None) -> str:
    """从存档文件恢复 game 的状态。

    参数
    ----
    game
        Game 实例。成功时**就地**写入 game.player / game.player_state /
        game.play_frames。
    path
        存档路径；None 时用 SAVE_PATH。

    返回
    ----
    str
        结果码：

        - "ok"：读档成功，game 已被恢复；
        - "no_file"：存档文件不存在（game 完全没动）；
        - "bad_version"：save_version 对不上（原文件不会被改写）；
        - "corrupt"：文件内容坏了 / 不是合法 JSON（原文件不会被改写）。
    """
    target = resolve_path(path)
    if not os.path.isfile(target):
        return RESULT_NO_FILE

    try:
        with open(target, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return RESULT_CORRUPT

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return RESULT_CORRUPT

    if not isinstance(data, dict):
        return RESULT_CORRUPT

    if data.get("save_version") != SAVE_VERSION:
        return RESULT_BAD_VERSION

    try:
        player = Player.from_dict({
            "dollars": data.get("dollars", 0),
            "party": data.get("party") or [],
            "storage": data.get("storage") or [],
            "bag": data.get("bag") or {},
        })
    except (KeyError, TypeError, ValueError):
        return RESULT_CORRUPT

    pos = data.get("player")
    if not isinstance(pos, dict):
        pos = {}

    # 就地恢复
    game.player = player

    state = _state_of(game)
    state["dollars"] = int(player.dollars)
    state["map_id"] = int(pos.get("map_id", state.get("map_id", 1)))
    state["x"] = int(pos.get("x", state.get("x", 0)))
    state["y"] = int(pos.get("y", state.get("y", 0)))
    state["facing"] = str(pos.get("facing", state.get("facing", "down")))

    try:
        game.play_frames = max(0, int(data.get("play_seconds", 0))) * FPS
    except (TypeError, ValueError):
        game.play_frames = 0

    return RESULT_OK
