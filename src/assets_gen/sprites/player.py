"""主角行走图：4 方向 x 2 帧 = 8 张 16x16。

key 命名：`player_{方向}_{帧号}`，方向为 down / up / left / right。
帧 0 = 站立，帧 1 = 迈步（双腿分开），两帧循环即为走路动画。

本批是**占位图**，但要能一眼看出朝向：
- down：正面，橙色大脸 + 两只眼睛
- up：背面，整颗头都是头发，没有脸
- left：脸朝左（眼睛在头左侧），左侧留空
- right：脸朝右（眼睛在头右侧），右侧留空
"""

from __future__ import annotations

from src.assets_gen.sprite_base import SpriteMatrix

#: 主角共用调色板
PALETTE: dict[str, int] = {
    ".": None,   # 透明
    "K": 5,      # 深紫 描边
    "S": 9,      # 肤色
    "H": 13,     # 棕 头发
    "C": 12,     # 浅蓝 上衣
    "P": 2,      # 蓝 裤子
}

#: 站立帧的腿（两腿并拢）
_LEGS_STAND = [
    "..KPPPPPPPPPPK..",
    "..KKKKKKKKKKKK..",
]
#: 迈步帧的腿（两腿分开）
_LEGS_WALK = [
    "..KPPK..KPPPPK..",
    "..KKKK..KKKKKK..",
]

#: 正面朝下（down）
_DOWN_HEAD = [
    "....KKKKKKKK....",
    "...KHHHHHHHHK...",
    "..KHHHHHHHHHHK..",
    "..KHSSSSSSSSHK..",
    "..KHSSSSSSSSHK..",
    "..KHSSKSSKSSHK..",
    "..KHSSSSSSSSHK..",
    "..KSSSSSSSSSSK..",
]
#: 背面朝上（up）：整颗头都是头发
_UP_HEAD = [
    "....KKKKKKKK....",
    "...KHHHHHHHHK...",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
]
#: 上半身（三个方向共用）
_BODY = [
    "..KCCCCCCCCCCK..",
    ".KSSKCCCCCCKSSK.",
    ".KSKCCCCCCCCKSK.",
    "..KPPPPPPPPPPK..",
    "..KPPPPPPPPPPK..",
    "..KPPPPPPPPPPK..",
]
#: 侧身朝左（left）：脸在头的左侧
_LEFT_HEAD = [
    "......KKKKKK....",
    ".....KHHHHHHK...",
    "....KHHHHHHHHK..",
    "....KHSSSSSSHK..",
    "....KHSSSSSSHK..",
    "....KHSSKSSSHK..",
    "....KHSSSSSSHK..",
    "....KSSSSSSSSK..",
]
_LEFT_BODY = [
    "....KCCCCCCCCK..",
    "....KSKCCCCCCK..",
    "....KSKCCCCCCK..",
    "....KPPPPPPPPK..",
    "....KPPPPPPPPK..",
    "....KPPPPPPPPK..",
]
#: 侧身朝右（right）：脸在头的右侧
_RIGHT_HEAD = [
    "....KKKKKK......",
    "...KHHHHHHK.....",
    "..KHHHHHHHHK....",
    "..KHSSSSSSHK....",
    "..KHSSSSSSHK....",
    "..KHSSSKSSHK....",
    "..KHSSSSSSHK....",
    "..KSSSSSSSSK....",
]
_RIGHT_BODY = [
    "..KCCCCCCCCK....",
    "..KCCCCCCKSK....",
    "..KCCCCCCKSK....",
    "..KPPPPPPPPK....",
    "..KPPPPPPPPK....",
    "..KPPPPPPPPK....",
]


def _frames(head: list[str], body: list[str], legs: list[str]) -> list[str]:
    """拼一帧：头 + 身体 + 腿（各 8 行 = 16 行）。"""
    return head + body + legs


PLAYER_DOWN_0 = SpriteMatrix("player_down_0", _frames(_DOWN_HEAD, _BODY, _LEGS_STAND), PALETTE)
PLAYER_DOWN_1 = SpriteMatrix("player_down_1", _frames(_DOWN_HEAD, _BODY, _LEGS_WALK), PALETTE)
PLAYER_UP_0 = SpriteMatrix("player_up_0", _frames(_UP_HEAD, _BODY, _LEGS_STAND), PALETTE)
PLAYER_UP_1 = SpriteMatrix("player_up_1", _frames(_UP_HEAD, _BODY, _LEGS_WALK), PALETTE)
PLAYER_LEFT_0 = SpriteMatrix("player_left_0", _frames(_LEFT_HEAD, _LEFT_BODY, _LEGS_STAND), PALETTE)
PLAYER_LEFT_1 = SpriteMatrix("player_left_1", _frames(_LEFT_HEAD, _LEFT_BODY, _LEGS_WALK), PALETTE)
PLAYER_RIGHT_0 = SpriteMatrix("player_right_0", _frames(_RIGHT_HEAD, _RIGHT_BODY, _LEGS_STAND), PALETTE)
PLAYER_RIGHT_1 = SpriteMatrix("player_right_1", _frames(_RIGHT_HEAD, _RIGHT_BODY, _LEGS_WALK), PALETTE)

#: 全部主角帧
SPRITES: list[SpriteMatrix] = [
    PLAYER_DOWN_0,
    PLAYER_DOWN_1,
    PLAYER_UP_0,
    PLAYER_UP_1,
    PLAYER_LEFT_0,
    PLAYER_LEFT_1,
    PLAYER_RIGHT_0,
    PLAYER_RIGHT_1,
]

#: (方向, 帧号) -> SpriteMatrix
PLAYER_FRAMES: dict[tuple[str, int], SpriteMatrix] = {
    ("down", 0): PLAYER_DOWN_0,
    ("down", 1): PLAYER_DOWN_1,
    ("up", 0): PLAYER_UP_0,
    ("up", 1): PLAYER_UP_1,
    ("left", 0): PLAYER_LEFT_0,
    ("left", 1): PLAYER_LEFT_1,
    ("right", 0): PLAYER_RIGHT_0,
    ("right", 1): PLAYER_RIGHT_1,
}
