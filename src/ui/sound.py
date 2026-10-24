"""音效与背景音乐（T8b / M7 收尾）。

这一层把「Pyxel 音频」包成**一个安全的全局单例**：

- 所有音效用 MML 字符串定义（比四字符串格式好读得多）；
- BGM 用 ogg 文件（assets/audio/bgm1.ogg / bgm2.ogg）当 PCM 循环播放；
- **任何一步失败都只是「没声音」，绝不让游戏或测试崩溃**。

通道分配
--------
===================== ======== ==========================================
用途                  通道    说明
===================== ======== ==========================================
音效（界面）          0       光标 / 确认 / 取消 / 金币 / 升级
音效（战斗）          1       命中 / 受击 / 捕捉
音效（事件）          2       治疗 / 遇敌 / 胜利 / 战败 / 逃跑
BGM                   3       循环播放的音乐
===================== ======== ==========================================

静音
----
静音状态放在**本模块的全局变量**里（_MUTED）：所有播放函数
（play_sfx / play_bgm）都先检查它，静音时直接 return，
**一个 pyxel.play 都不会被调用**。静音时还会停掉 BGM 通道（channel 3），
取消静音时把之前请求的那首 BGM 重新放起来。

无头 / 无声环境
--------------
sound.init() 把所有初始化包在 try/except 里：只要有一处失败
（比如没有初始化 Pyxel、音频设备不可用、素材文件缺失），
就把 is_available() 置成 False，之后所有播放都变成**安静的 no-op**。
"""

from __future__ import annotations

import os

import pyxel

# ---------------------------------------------------------------- 路径
#: 项目根目录（本文件在 src/ui/ 下，往上三层）
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#: 音频素材目录（ogg 放在这里，项目自包含，不依赖外部素材目录）
AUDIO_DIR = os.path.join(_PROJECT_ROOT, "assets", "audio")

# ---------------------------------------------------------------- 通道
#: BGM 专用通道（音效只用 0~2）
BGM_CHANNEL = 3
#: 音效通道
SFX_CHANNELS: tuple[int, ...] = (0, 1, 2)
#: 音效通道音量（Pyxel 默认 0.125，这里调高一点听得清）
SFX_GAIN = 0.3
#: BGM 通道音量（比音效高，但不至于盖住音效）
BGM_GAIN = 0.6

# ---------------------------------------------------------------- 音效表
#: 音效名 -> (声音槽位, MML 字符串, 播放通道)
#:
#: MML 速查（Pyxel 2.9.9 的 Sound.mml 方言）：
#:
#: - T<数>  速度（每分钟四分音符数，越大越快）
#: - V<数>  音量 0~100
#: - O<数>  八度 0~9
#: - L<数>  后续音符的默认时值（1=全音符 2=二分 4=四分 8=八分 16=十六分）
#: - 音符字母 A~G，**后面紧跟的数字是时值**（不是八度！），点号附点，
#:   # 升号、- 降号、r 休止符。
SFX_SPECS: dict[str, tuple[int, str, int]] = {
    # 界面音（通道 0）
    "cursor": (0, "T800 V70 O6 L8 E8 G8", 0),
    "confirm": (1, "T400 V90 O5 L4 G4 O6 C4 E4", 0),
    "cancel": (2, "T400 V80 O5 L8 E8 C8", 0),
    "coin": (3, "T800 V90 O6 L8 B8 E8", 0),
    # 战斗音（通道 1）
    "hit": (4, "T350 V100 O5 L8 G8 E8 C8", 1),
    "hit_super": (5, "T450 V100 O6 L8 E8 C8 G8 E8", 1),
    "hurt": (6, "T300 V100 O4 L8 A8 F8 D8", 1),
    "catch_ok": (7, "T400 V90 O5 L8 G8 C8 E8 G8", 1),
    "catch_fail": (8, "T350 V80 O5 L8 E8 C8 A8", 1),
    # 事件音（通道 2）
    "heal": (9, "T400 V80 O5 L8 C8 E8 G8 C8", 2),
    "level_up": (10, "T400 V90 O5 L8 C8 E8 G8 C8 E8", 0),
    "encounter": (11, "T600 V100 O5 L8 C8 G8 E8 C8", 2),
    "victory": (12, "T400 V90 O5 L8 G8 C8 E8 G8", 2),
    "escape": (13, "T600 V85 O5 L8 G8 C8 E8", 2),
    "defeat": (14, "T250 V90 O3 L8 G8 E8 C8", 2),
}

#: 全部音效名（测试用）
SFX_NAMES: tuple[str, ...] = tuple(SFX_SPECS.keys())

# ---------------------------------------------------------------- BGM 表
#: BGM 名 -> 声音槽位（PCM）
#:
#: - field   新手村 / 野外（bgm1.ogg，明亮）
#: - cave    洞窟（bgm2.ogg，阴暗）
#: - battle  战斗（bgm2.ogg，与洞窟同一首；战斗时地面 BGM 会被它顶掉，
#:   战斗结束后地图场景会按地图重新切回 field / cave）
BGM_SPECS: dict[str, int] = {
    "field": 60,
    "cave": 61,
    "battle": 61,
}

#: 声音槽位 -> ogg 文件名
BGM_FILES: dict[int, str] = {
    60: "bgm1.ogg",
    61: "bgm2.ogg",
}

#: 全部 BGM 名（测试用）
BGM_NAMES: tuple[str, ...] = tuple(BGM_SPECS.keys())

# ---------------------------------------------------------------- 全局状态
#: 是否已经初始化过（保证 init() 幂等）
_initialized: bool = False
#: 音频是否可用（初始化失败时为 False，之后所有播放都是 no-op）
_available: bool = False
#: 初始化失败的重试次数上限（避免素材永久缺失时反复重读 ogg）
_MAX_INIT_ATTEMPTS = 3
#: 已经尝试初始化过几次
_init_attempts: int = 0
#: 是否静音
_muted: bool = False
#: 最近一次**请求**的 BGM 名（静音时也记录，取消静音时用它恢复）
_requested_bgm: str | None = None
#: 当前**正在播放**的 BGM 名
_playing_bgm: str | None = None


# ---------------------------------------------------------------- 初始化
def init() -> None:
    """定义全部音效 + 载入 BGM + 设置各通道音量（**幂等**）。

    任何一步失败都不会抛异常：失败时 is_available() 返回 False，
    之后所有播放函数都变成安静的 no-op。
    """
    global _initialized, _available, _init_attempts
    if _initialized and _available:
        return
    if _init_attempts >= _MAX_INIT_ATTEMPTS:
        return                      # 已经试过多次都失败：安静降级，不再重试
    _init_attempts += 1
    try:
        for index, mml_text, _channel in SFX_SPECS.values():
            pyxel.sounds[index].mml(mml_text)
        _load_bgm()
        for channel in SFX_CHANNELS:
            pyxel.channels[channel].gain = SFX_GAIN
        pyxel.channels[BGM_CHANNEL].gain = BGM_GAIN
        _available = True
        _initialized = True
    except Exception:
        # 音频不可用（没初始化 Pyxel / 没有声卡 / 素材缺失）——安静降级：
        # is_available() 变 False，之后所有播放都是 no-op，绝不抛异常。
        _available = False
        # Pyxel 还没初始化（宽度为 0）时允许以后重试；已经初始化了还失败
        # 说明素材真的有问题，标记成「试过了」。
        _initialized = bool(getattr(pyxel, "width", 0))


def _load_bgm() -> None:
    """把两个 ogg 装进 PCM 槽位（60 / 61）。"""
    for slot, filename in BGM_FILES.items():
        path = os.path.join(AUDIO_DIR, filename)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"缺少 BGM 素材：{path}")
        # 用正斜杠：Windows 路径里的反斜杠在部分 SDL 版本上会出问题
        pyxel.sounds[slot].pcm(path.replace(os.sep, "/"))


def is_available() -> bool:
    """音频是否可用。

    False 表示初始化失败（没初始化 Pyxel、音频设备不可用、素材缺失等），
    此时所有播放都是 no-op。
    """
    return _available


def is_initialized() -> bool:
    """是否已经调用过 init()。"""
    return _initialized


# ---------------------------------------------------------------- 音效
def play_sfx(name: str) -> None:
    """按名字播放音效；**未知名字安静忽略**（不抛异常）。

    静音或音频不可用时什么也不做（不会调用 pyxel.play）。
    """
    if not _initialized:
        init()
    if not _available or _muted:
        return
    spec = SFX_SPECS.get(name)
    if spec is None:
        return                      # 未知音效名：安静忽略
    index, _mml_text, channel = spec
    try:
        pyxel.play(channel, index)
    except Exception:
        pass                       # 播放失败也不能让游戏崩


# ---------------------------------------------------------------- BGM
def play_bgm(name: str) -> None:
    """切换 BGM。

    - **同一首正在播则不重启**（不会打断正在进行的音乐）；
    - 静音时只记录请求，不真的播放；
    - 未知名字安静忽略。
    """
    global _requested_bgm
    if not _initialized:
        init()
    if name not in BGM_SPECS:
        return                      # 未知 BGM 名：安静忽略
    _requested_bgm = name
    if not _available or _muted:
        return
    if _playing_bgm == name:
        return                      # 同一首：不重启
    _start_bgm(name)


def _start_bgm(name: str) -> None:
    """真正在 BGM 通道上放一首曲子。"""
    global _playing_bgm
    index = BGM_SPECS.get(name)
    if index is None:
        return
    try:
        pyxel.stop(BGM_CHANNEL)
        pyxel.play(BGM_CHANNEL, index, loop=True)
        _playing_bgm = name
    except Exception:
        pass


def stop_bgm() -> None:
    """停止 BGM（通道 3）。"""
    global _playing_bgm, _requested_bgm
    _playing_bgm = None
    _requested_bgm = None
    if not _available:
        return
    try:
        pyxel.stop(BGM_CHANNEL)
    except Exception:
        pass


def current_bgm() -> str | None:
    """当前正在播放的 BGM 名（None = 没在放）。"""
    return _playing_bgm


def requested_bgm() -> str | None:
    """最近一次请求的 BGM 名（静音时也会记录）。"""
    return _requested_bgm


def reset() -> None:
    """清掉 BGM 的播放状态（**测试用**）：不改变静音状态。

    正常游戏里不需要调用；测试里用来保证「同一首不重启」的判定
    不受上一个用例的影响。
    """
    global _playing_bgm, _requested_bgm
    _playing_bgm = None
    _requested_bgm = None


def reset_init() -> None:
    """把初始化状态清回「未初始化」（**测试用**）。

    正常游戏里不需要调用；测试里用来验证 init() 的幂等与降级路径。
    """
    global _initialized, _available, _init_attempts
    _initialized = False
    _available = False
    _init_attempts = 0


# ---------------------------------------------------------------- 静音
def is_muted() -> bool:
    """当前是否静音。"""
    return _muted


def set_mute(on: bool) -> None:
    """设置静音状态。

    - 静音：**停掉 BGM**，之后不再播放任何音效；
    - 取消静音：把之前请求的那首 BGM 重新放起来。
    """
    global _muted, _playing_bgm
    on = bool(on)
    if on == _muted:
        return
    _muted = on
    if on:
        _playing_bgm = None
        if _available:
            try:
                pyxel.stop(BGM_CHANNEL)
            except Exception:
                pass
        return
    # 取消静音：恢复之前请求的 BGM
    if _available and _requested_bgm:
        _start_bgm(_requested_bgm)


def toggle_mute() -> bool:
    """切换静音状态，返回**切换后**的状态（True = 已静音）。"""
    set_mute(not _muted)
    return _muted
