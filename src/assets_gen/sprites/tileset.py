"""地图图块集：12 种 16x16 图块（批 4 重绘 · 方案 D，批 6 新增洞窟地面）。

key 与《数值设定.md》§10.2 的图块 ID 一一对应：

    tile_0_grass     草地     可走
    tile_1_tallgrass 草丛     可走（明雷遇敌区）
    tile_2_tree      树       障碍
    tile_3_water     水       障碍
    tile_4_road      道路     可走（村庄地面）
    tile_5_wall      房屋墙   障碍
    tile_6_door      门/洞口  可走（传送点）
    tile_7_rock      岩壁     障碍
    tile_8_highland  高地     可走
    tile_9_flower    花丛     可走（装饰）
    tile_10_portal  传送阵   可走（地图出入口）
    tile_11_cavefloor 洞窟地面 可走（洞窟通道地面）

画法
----
逐行手绘 / 程序化生成后固化成**字面量字符画**（运行期零解析开销）。
图块是**满铺不透明**的：没有任何 '.' 像素，且**不使用索引 0**
（色 0 是 blt 的 colkey 透明键，虽然当前图块不传 colkey，也不留隐患）。

能平铺是怎么保证的
------------------
1. 纹理用**逐像素散布**（草点 / 碎石 / 水波），不做"一格一个居中图案"，
   相邻两格之间不会出现整块重复的花纹。
2. 凡是成条的元素（水波、高速草叶、砖缝）都按 16 的模取坐标，
   跨过边界的部分在另一侧续上，接缝两侧图案可以继续。
3. 大色块（草地 / 水面 / 道路 / 高地）以同一种底色打底，相邻格底色一致，
   所以平铺时看不到色块边界；砖墙的横向砖缝正好落在 y=0/4/8/12，
   竖直方向两格相接时砖缝依然对齐。

配色与"能不能走"一眼可分
------------------------
| 类型 | 主色 | 观感 |
|---|---|---|
| 可走 | 绿 4 / 深绿 3 / 浅蓝 12 / 橙 9 / 浅灰 15 | 明亮、低对比 |
| 障碍 | 深绿 3 树冠 + 棕 13 树干 / 深蓝 2 水 / 棕 13 砖 + 灰 6 / 灰 6 岩 + 深蓝 1 暗部 | 深、重、块面闭合 |

色 5（DARK_PURPLE）只留给精灵描边，**图块完全不用色 5**，
避免和主角描边撞色。
"""

from __future__ import annotations

from src.assets_gen.sprite_base import SpriteMatrix

#: 图块共用调色板（字符 -> 调色板索引；**绝不出现索引 0**）
PALETTE: dict[str, int] = {
    ".": None,   # 透明（本项目约定：每个素材的 palette 都要有这一项，图块不使用）
    "g": 3,      # 深绿   草丛底 / 树冠主体
    "G": 4,      # 中绿   草地底 / 树冠碎叶 / 高草过渡
    "l": 11,     # 浅绿   草叶 / 树冠亮面
    "B": 12,     # 浅蓝   水面
    "b": 2,      # 蓝     水的暗部 / 深水条纹
    "W": 7,      # 白     浪花高光 / 白花
    "O": 9,      # 橙     道路 / 砖顶 / 门框
    "D": 13,     # 棕     树干 / 砖块 / 门框 / 碎石
    "d": 6,      # 灰     砖缝 / 岩面
    "T": 15,     # 浅灰   高地台地 / 岩面高光 / 砖棱
    "Y": 10,     # 黄     门把手 / 花芯
    "R": 8,      # 红     红花
    "c": 1,      # 深蓝 DEEP_BLUE：门洞 / 岩壁暗部
    "s": 1,      # 深蓝 DEEP_BLUE：洞窟地面底色（比岩壁暗得多，一眼可分）
}

# ======================================================================
# tile_0_grass —— 草地（可走）
# 用色索引：G=4 中绿底（209 像素）/ l=11 浅绿草叶 / g=3 深绿草点
# 平铺：底色单一，草点逐像素散布，相邻格纹理不重复
# ======================================================================
TILE_0_GRASS = SpriteMatrix(
    "tile_0_grass",
    [
        "GGGlGGgGggGGGGGG",
        "gGGggGGGGGGGGlGG",
        "GGGgGgGGGGGggGGG",
        "GGGGlGGgGGGGGGgG",
        "GlGGlGGGgGGGlGGG",
        "GlGGlGGGGGGGgGGG",
        "GGGGGGGGGlGGGGGG",
        "GGGGGGGGGllGlgGG",
        "GGGlGGGGGGGGlGGG",
        "GGGlGGGGGGGGGGGG",
        "lGGGGGGGGlGGgGlG",
        "lgGGGGGGGllGGGGG",
        "GGGGGGgGGGlGGGGG",
        "gGGGGGGlgGlGGGGG",
        "GGGGGGGGGGgGGGGG",
        "GGGGGGGGGgGgGGGG",
    ],
    PALETTE,
)

# ======================================================================
# tile_1_tallgrass —— 草丛（可走 · 明雷遇敌区）
# 用色索引：g=3 深绿底（188 像素）/ l=11 高草叶（58）/ G=4 过渡叶
# 平铺：草叶按 16 取模，跨上下边界的叶子在另一侧续上
# ======================================================================
TILE_1_TALLGRASS = SpriteMatrix(
    "tile_1_tallgrass",
    [
        "ggglgggllggggglg",
        "gGgllggllggggglg",
        "gggllgglgGgggggg",
        "ggGlggglgGglgllg",
        "glggglgglgglgglg",
        "llggglgglggggglg",
        "ggggglgglggggggg",
        "Ggggglgglggggggg",
        "ggggGlllgggggGgg",
        "ggggggglggggggll",
        "lgggglgggggggglg",
        "lgglllggglggggll",
        "lgggggggglgggggl",
        "ggggggggggggllGg",
        "gggggggglggGgggg",
        "ggggllggllgggglG",
    ],
    PALETTE,
)

# ======================================================================
# tile_2_tree —— 树（障碍）★ 本次重做的重点
# 用色索引：g=3 树冠主体（90）/ l=11 左上亮面 / G=4 碎叶与四周草地（130）/ D=13 树干
# 旧的树冠主色是色 4，和草地完全同色 → 树整块隐形；
# 新版树冠用色 3 深绿打底、色 11 打亮面，四周留一圈色 4 草地，剪影一眼可辨
# ======================================================================
TILE_2_TREE = SpriteMatrix(
    "tile_2_tree",
    [
        "GGGGGGGGGGGGGGGG",
        "GGGGGGgggggGGGGG",
        "GGGgllgggllggGGG",
        "GGgllllllllGggGG",
        "GGGlllllggggggGG",
        "GggllllgGggggggG",
        "GgggggGgggggggGG",
        "GGgggggggggggggG",
        "GGggggggggggggGG",
        "GGGgggGgggggGGGG",
        "GGGGggggggggGGGG",
        "GGGGGGgDDDgGGGGG",
        "GGGGGGGDDDGGGGGG",
        "GGGGGGgDDDgGGGGG",
        "GGGGGGgDDDgGGGGG",
        "GGGGGGgDDDgGGGGG",
    ],
    PALETTE,
)

# ======================================================================
# tile_3_water —— 水（障碍）
# 用色索引：B=12 浅蓝底（205）/ b=2 深水条纹与点 / W=7 白色浪花
# 平铺：浪花按 16 取模，6 处浪花分布在不同的行，不会每格重复同一个图案
# ======================================================================
TILE_3_WATER = SpriteMatrix(
    "tile_3_water",
    [
        "BBbbBBBBbBbBBBBB",
        "BBBbbbBBbBBBbbbB",
        "WBBBBWWWbBBBBBWW",
        "BBBBBBBBBBBBBBBB",
        "BBBBBBBBBBBBBBBB",
        "BWWWBBBBBBBBBBBB",
        "BBBBbbbbBBBBBBBB",
        "BBBbbBBBBBWWWBBB",
        "BBBBBBbbbBBBBBBB",
        "BBBBBBBBBBBbbbbB",
        "BBbbBBBbBBBBWWWB",
        "BBBBBBBBBBBBBBBB",
        "BBBBBBBBBBBBBBBB",
        "BbBBBBBWWWBBBBBB",
        "BBBBBBBBBbBBBBBB",
        "WWWBBBBBBBBBBBBB",
    ],
    PALETTE,
)

# ======================================================================
# tile_4_road —— 道路（可走 · 村庄地面）
# 用色索引：O=9 土黄底（224）/ D=13 棕色碎石与土痕（32）
# 平铺：碎石逐像素散布，不做居中图案，所以走道时看不到格与格的边界
# ======================================================================
TILE_4_ROAD = SpriteMatrix(
    "tile_4_road",
    [
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OOODODOOOOODDOOO",
        "OODOOOOOODDOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOODOOOOODO",
        "OOOOOOOOODOOOOOO",
        "DOOOODDOOODOOOOO",
        "OODOODDOOOOOOOOO",
        "OOOOOOODOOOOOODO",
        "OODDOODDOOOOOOOO",
        "OOOOOOOOOOOOOOOO",
        "OOOOOOOOOOOODODO",
        "DOOOODDOOOOOOOOO",
        "OOOOOOOOOOODOOOO",
        "OOOOOOOODDOODOOO",
    ],
    PALETTE,
)

# ======================================================================
# tile_5_wall —— 房屋墙（障碍）
# 用色索引：D=13 砖块（150）/ d=6 勾缝（82）/ T=15 砖棱高光（24）
# 平铺：横向砖缝落在 y=0/4/8/12，竖向错缝每层轮流，两格相接时砖纹自动对齐
# ======================================================================
TILE_5_WALL = SpriteMatrix(
    "tile_5_wall",
    [
        "dddddddddddddddd",
        "TTTDDDDdTTTDDDDD",
        "DDDDDDDdDDDDDDDD",
        "DDDDDDDdDDDDDDDD",
        "dddddddddddddddd",
        "TTTdDDDDTTTdDDDD",
        "DDDdDDDDDDDdDDDD",
        "DDDdDDDDDDDdDDDD",
        "dddddddddddddddd",
        "TTTDDDDdTTTDDDDD",
        "DDDDDDDdDDDDDDDD",
        "DDDDDDDdDDDDDDDD",
        "dddddddddddddddd",
        "TTTdDDDDTTTdDDDD",
        "DDDdDDDDDDDdDDDD",
        "DDDdDDDDDDDdDDDD",
    ],
    PALETTE,
)

# ======================================================================
# tile_6_door —— 门/洞口（可走 · 传送点）
# 用色索引：b=2 门洞（108）/ D=13 门洞外侧的墙砖（47）/ T=15 门框受光边（40）
#            O=9 门框 / Y=10 门把手
# 四周一圈刻意做成与 tile_5_wall 相同的砖纹，嵌在房屋墙上不会突出来
# ======================================================================
TILE_6_DOOR = SpriteMatrix(
    "tile_6_door",
    [
        "dddddddddddddddd",
        "TTTDDDDdTTTDDDDD",
        "DDTOOccccccOOTDD",
        "DDTOccccccccOTDD",
        "ddTOccccccccOTdd",
        "TTTOccccccccOTDD",
        "DDTOccccccccOTDD",
        "DDTOccccccccOTDD",
        "ddTOccccccccOTdd",
        "TTTOccccccccOTDD",
        "DDTOcccccYccOTDD",
        "DDTOcccccYccOTDD",
        "ddTOccccccccOTdd",
        "TTTOccccccccOTDD",
        "DDTOccccccccOTDD",
        "DDTOccccccccOTDD",
    ],
    PALETTE,
)

# ======================================================================
# tile_7_rock —— 岩壁（障碍）
# 用色索引：d=6 灰岩主体（201）/ c=1 暗部与裂缝（36）/ T=15 高光（19）
# 左上亮面 + 右下暗面 + 几道裂缝，做出石头的体积感；
# 平铺：明暗块都按 16 取模环绕，不会在格子边界上出现硬切线
# ======================================================================
TILE_7_ROCK = SpriteMatrix(
    "tile_7_rock",
    [
        "dTTTTddddddddddd",
        "dTTTTTdddddddddd",
        "dTTTTTdddddddcdd",
        "ddTTTddddddddcdd",
        "dddTdddddddddcdd",
        "dddddddddddddddd",
        "ddddddddcddddddd",
        "ddddddddddddddcd",
        "ddddddddddddcccd",
        "ddddddddddddcccc",
        "dcccdddddddccccc",
        "dccccddddddccccc",
        "ddcccdddddddcccc",
        "dddddddddddddddd",
        "ddddddddddddddTd",
        "dddddddddddddddd",
    ],
    PALETTE,
)

# ======================================================================
# tile_8_highland —— 高地（可走）★ 本次重做
# 用色索引：T=15 浅灰米色台地（206）/ d=6 断续岩层与碎石（42）/ D=13 棕色小石（8）
# 旧版是整片色 13 棕底、只点了几粒绿，和道路几乎同色；
# 新版改成浅灰米色台地，与草地（绿）/道路（橙）/砖墙（棕）全都不同色系
# ======================================================================
TILE_8_HIGHLAND = SpriteMatrix(
    "tile_8_highland",
    [
        "TdTTTTTTTTTddTTT",
        "TTTTTTTTTTTTTTdT",
        "dTTTdTTTTTddTTTd",
        "TTDTTTTTTTTTdTdT",
        "TTdTTTTTTTTTTTTT",
        "TddTdTTTTTTTTTTT",
        "TTdTTTTTDTTTTTTT",
        "TTTTTdTTTTdTTTTT",
        "TTTTTTDTTdTTTddT",
        "dTdTDTTTTDTTdddd",
        "TTTdTTTTTDTTTTTT",
        "dTTTTTdTTTTTTTTd",
        "TDDdTTTddTTTTTTT",
        "TTTTTTTTTTdTTTTT",
        "TTTTTTTTTTTTdddd",
        "TdTTTddTTTTTTTTT",
    ],
    PALETTE,
)

# ======================================================================
# tile_9_flower —— 花丛（可走 · 装饰）
# 用色索引：G=4 草地底（219）/ l=11 草叶 / g=3 草点
#            三朵小花：R=8 红 / Y=10 黄 / W=7 白，花芯用互补色
# 平铺：花按 16 取模裁切，跨边界的花瓣在另一侧补全
# ======================================================================
TILE_9_FLOWER = SpriteMatrix(
    "tile_9_flower",
    [
        "GGGGGGlgGlGGGgGl",
        "GGGGGGlGGGGGGGGg",
        "GGGRGGGGGGGgGGGG",
        "GGRYRGGGGGGGGGGG",
        "GGGRGGGGGGGGGGGl",
        "GGGGGGGgGGGGGGGG",
        "GGGGGGGlGGGGGGGG",
        "GgGgGGGGGGGYGGGG",
        "GGGlGGGGGgYRYGGG",
        "GgGGGGGGGGGYGGGG",
        "GGGGlGGGGGGGGGGG",
        "GGGGGGGWGGGGGGlG",
        "GGGGGGWYWGGGGlGG",
        "GGGGGlGWGGGGGGGG",
        "GGGGGGGGGGGGGGGG",
        "GGGlGGGGGlGGGGGG",
    ],
    PALETTE,
)

# ======================================================================
# tile_10_portal —— 传送阵（可走 · 地图出入口）★ 批 5 新增
# 用色索引：O=9 / D=13 道路底（与 tile_4_road 同款，踩在路上不突兀）
#            B=12 浅蓝光环 / W=7 白色内环 / Y=10 黄色核心与四角符纹
#            c=1 深蓝描边（法阵的暗环）
# 画法：地面上的圆形法阵 —— 中心黄点 + 白晕 + 深蓝暗环 + 浅蓝光环，
#       光环的四个对角方向各有一道黄色符纹；**四角各有一组黄色符纹角标**。
# 为什么光环画到图块边缘 + 四角要有符纹：主角精灵也是 16x16，站在图块上
#       会把图块中间盖住，只有 x=0/1、x=14/15 与第 0 行这些「主角轮廓之外」
#       的像素还露得出来。所以外圈光环顶到图块边缘（上 / 左 / 右三段），
#       四角再各放一组黄色符纹角标 —— 玩家站上传送阵时，脚下依然能看到
#       一圈发光的光环，不会以为那里什么都没有。
# 为什么底色用道路：两个传送阵格（新手村 28,10 / 野外 1,15）都在道路上，
#       底色与周围一致才是「地面上的传送阵」而不是「地上摆了个方块」。
# 可走性：整块是平的地面图案，没有任何实心障碍剪影。
# ======================================================================
TILE_10_PORTAL = SpriteMatrix(
    "tile_10_portal",
    [
        "YYOOOOOBBOOOOOYY",
        "YWOOBBBBBBBBOOWY",
        "OOOYBBBBBBBBYOOO",
        "OOYYYccBBccYYYOO",
        "OBBYcBBBBBBcYBBO",
        "OBBcBBccccBBcBBO",
        "OBBcBcWWWWcBcBBO",
        "BBBBBcWYYWcBBBBB",
        "BBBBBcWYYWcBBBBB",
        "OBBcBcWWWWcBcBBO",
        "OBBcBBccccBBcBBO",
        "OBBYcBBBBBBcYBBO",
        "OOYYYccBBccYYYDO",
        "DOOYBBBBBBBBYOOO",
        "YWOOBBBBBBBBOOWY",
        "YYOOOOOBBDOODOYY",
    ],
    PALETTE,
)

# ======================================================================
# tile_11_cavefloor —— 洞窟地面（可走）★ 批 6 新增
# 用色索引：s=1 深蓝底（洞窟地面的暗色基调）/ D=13 棕色砂砾 / d=6 灰色小石子
# 为什么用**深蓝**而不是棕色：岩壁（tile_7_rock）主体是**浅灰**（色 6 = 0x8A8A96），
#   如果地面也用中明度的棕，两块挨在一起会糊成一片；
#   地面压成很暗的深蓝（色 1 = 0x16213E）之后，「暗地面 / 亮岩壁」的明度差拉满，
#   一眼就能分出哪里能走、哪里是墙（洞窟也更像在洞里）。
# 平铺：砂砾与石子都是逐像素散布，不做居中图案，相邻格纹理不重复。
# 可走性：整块是平的地面图案，没有任何实心障碍剪影。
# ======================================================================
TILE_11_CAVEFLOOR = SpriteMatrix(
    "tile_11_cavefloor",
    [
        "sssssssDsssdssDs",
        "sDssssddssssssss",
        "sssDssdssDssssds",
        "Dsssssssssssssss",
        "ssssssssDssDssss",
        "DssdssssssssssDs",
        "sDsssDssssDsssds",
        "sssssssssssssssD",
        "sDdsssDsssssssss",
        "Dsssssssssssssds",
        "sssssssssDssssss",
        "sDsDsssssssDssss",
        "sssssssssssssDss",
        "sssDssssssssssss",
        "sssssssDssssssss",
        "ssDssDssssssdsss",
    ],
    PALETTE,
)

#: 全部图块（烘焙顺序 = 绘制顺序，也是 §10.2 的 ID 顺序）
SPRITES: list[SpriteMatrix] = [
    TILE_0_GRASS,
    TILE_1_TALLGRASS,
    TILE_2_TREE,
    TILE_3_WATER,
    TILE_4_ROAD,
    TILE_5_WALL,
    TILE_6_DOOR,
    TILE_7_ROCK,
    TILE_8_HIGHLAND,
    TILE_9_FLOWER,
    TILE_10_PORTAL,
    TILE_11_CAVEFLOOR,
]

#: 图块 ID（§10.2）-> SpriteMatrix
TILES_BY_ID: dict[int, SpriteMatrix] = {i: sprite for i, sprite in enumerate(SPRITES)}
# ======================================================================
# 地面变体碎屑 + 边缘过渡图块（A6）
# ----------------------------------------------------------------------
# 为什么要程序化拼出来而不是像上面那样逐行手写：
#   变体 12 张 + 过渡 24 张 = 36 张，全靠手写会是几百行几乎相同的字面量，
#   改一处底色就要改 36 遍。这里改成「在基础图块上叠几个固定像素」，
#   叠的位置是**写死的常量**（可读、可评审），选择哪个变体才用坐标哈希。
#   仍然满足本文件的两条硬约定：满铺不透明、**绝不出现索引 0**。
#
# 生成只发生在 import 时一次（烘焙本来也只在启动时做一次），
# 运行期每帧只是按名字取已经烘焙好的 pyxel.Image，没有额外解析开销。
# ======================================================================

#: 变体叠加的碎屑：(x, y, 字符)。变体 0 恒为空 —— 变体 0 就是原图块本身。
VARIANT_DECOR: dict[int, tuple[tuple[tuple[int, int, str], ...], ...]] = {
    # 草地：v1 多几根浅草叶 / v2 一朵小白花 / v3 两颗灰色小石子
    0: (
        (),
        ((2, 11, "l"), (2, 12, "l"), (7, 3, "l"), (12, 9, "l"), (12, 10, "l"), (5, 6, "g")),
        ((6, 4, "W"), (5, 5, "Y"), (6, 5, "Y"), (7, 5, "Y"), (6, 6, "Y")),
        ((3, 8, "d"), (4, 8, "d"), (4, 9, "d"), (11, 12, "d"), (12, 6, "d")),
    ),
    # 道路（土）：v1 一撮碎石子 / v2 一道车辙 / v3 几粒亮沙
    4: (
        (),
        ((3, 5, "D"), (4, 5, "D"), (4, 6, "D"), (11, 10, "D"), (12, 10, "D")),
        ((2, 12, "D"), (3, 12, "D"), (4, 12, "D"), (5, 12, "D")),
        ((8, 3, "T"), (14, 7, "T"), (6, 13, "T")),
    ),
    # 洞窟地面：v1 一堆石屑 / v2 一道划痕 / v3 两颗小石子
    11: (
        (),
        ((5, 4, "D"), (6, 4, "d"), (6, 5, "D"), (12, 11, "d")),
        ((9, 2, "d"), (9, 3, "d"), (10, 4, "d"), (10, 5, "d")),
        ((2, 9, "d"), (3, 10, "d"), (13, 6, "D")),
    ),
    # 水面：浪花本身就成斜向排列，16 像素一循环在大片水域上非常明显。
    3: (
        (),
        ((4, 8, "W"), (5, 8, "W"), (11, 3, "b")),
        ((13, 13, "W"), (14, 13, "W"), (2, 5, "b"), (3, 5, "b")),
        ((8, 11, "b"), (9, 11, "b"), (9, 12, "b"), (15, 6, "W")),
    ),
    # 岩壁：原图块左上那一大片亮面 16 像素一循环，远看是一排排"箭头"。
    # 变体把亮面抹掉一部分 / 换成裂缝，打断这个周期。
    7: (
        (),
        ((1, 1, "d"), (2, 1, "d"), (1, 2, "d"), (2, 2, "d"), (3, 3, "d"), (4, 4, "d")),
        ((1, 1, "d"), (2, 1, "d"), (1, 2, "d"), (0, 3, "d"), (9, 6, "T"), (10, 6, "T")),
        ((1, 1, "d"), (2, 2, "d"), (3, 3, "d"), (12, 9, "T"), (13, 9, "T"), (13, 10, "T")),
    ),
}

#: 每个变体的「纹理平移量」。
#:
#: 为什么需要平移：基础图块是 16x16 无缝纹理，铺满一片之后会形成一个
#: **16 像素一循环**的可见图案（草地的斜短划、岩壁的亮面箭头都是这么来的）。
#: 只有 4 个变体时，仍有 1/4 的格子是原图块，周期只是被削弱、没有被打破。
#: 给每个变体加一个固定的平移量之后，同一张底纹会被错开拼，视觉周期
#: 从 16 像素变成约 64 像素，眼睛就看不到重复了。
#: 平移后仍然无缝（底纹本来就是环形的），所以不会引入接缝。
VARIANT_SHIFT: dict[int, tuple[tuple[int, int], ...]] = {
    0: ((0, 0), (5, 3), (11, 9), (2, 12)),
    4: ((0, 0), (7, 2), (3, 10), (12, 6)),
    11: ((0, 0), (9, 5), (4, 11), (13, 3)),
    7: ((0, 0), (6, 4), (11, 8), (3, 12)),
    3: ((0, 0), (5, 7), (10, 2), (3, 13)),
}

#: 每种地形的边缘带用什么字符（= 比底色更深一档的颜色）
#: 草地压深绿 3 / 道路压棕 13 / 洞窟压浅灰 15。
#: 洞窟的边带**必须避开色 6**：色 6 正是岩壁的底色，一开始用色 6 压边，
#: 结果整片岩壁被切成一块块"灰砖"，反而更乱。改成浅灰 15 之后，
#: 地面与岩壁之间是一道亮边的石台轮廓，两者还是一眼可分。
EDGE_BAND_CHAR: dict[int, str] = {0: "g", 4: "D", 11: "T"}

#: 边带只画**外侧一条**像素：实测 2 像素会变成粗框，1 像素既清楚又不抢戏。
EDGE_BAND_WIDTH = 1




def _as_grid(rows: list[str]) -> list[list[str]]:
    return [list(r) for r in rows]


def _as_rows(grid: list[list[str]]) -> list[str]:
    return ["".join(r) for r in grid]


def _shift(base: SpriteMatrix, dx: int, dy: int) -> list[list[str]]:
    """把底纹按 (dx, dy) 环绕平移，得到一张无缝的错位底纹。"""
    src = _as_grid(base.rows)
    size = base.width
    if dx == 0 and dy == 0:
        return [row[:] for row in src]
    return [
        [src[(y - dy) % size][(x - dx) % size] for x in range(size)]
        for y in range(size)
    ]


def _make_variant(
    base: SpriteMatrix, deco: tuple, index: int, shift: tuple[int, int] = (0, 0)
) -> SpriteMatrix:
    """先错位底纹、再叠一层碎屑，得到变体 index。"""
    grid = _shift(base, shift[0], shift[1])
    for x, y, ch in deco:
        grid[y][x] = ch
    name = "%s_v%d" % (base.name, index)
    return SpriteMatrix(name, _as_rows(grid), base.palette)


def _make_edge(base: SpriteMatrix, band: str, shape: int) -> SpriteMatrix:
    """在 base 上按形态 shape 压一圈「边缘带」。

    shape 与 src/ui/terrain.py 的 EDGE_* 常量一一对应：
    1 上 / 2 右 / 3 下 / 4 左 / 5 左上 / 6 右上 / 7 左下 / 8 右下 / 9 一圈。
    shape 0 不调用本函数（直接用原图块）。
    """
    grid = _as_grid(base.rows)
    w = h = base.width
    sides = {
        1: ("top",), 2: ("right",), 3: ("bottom",), 4: ("left",),
        5: ("top", "left"), 6: ("top", "right"),
        7: ("bottom", "left"), 8: ("bottom", "right"),
        9: ("top", "right", "bottom", "left"),   # 窄道 / 孤立地块：一圈
    }.get(shape, ())
    if "top" in sides:
        for y in range(EDGE_BAND_WIDTH):
            for x in range(w):
                grid[y][x] = band
    if "bottom" in sides:
        for y in range(h - EDGE_BAND_WIDTH, h):
            for x in range(w):
                grid[y][x] = band
    if "left" in sides:
        for x in range(EDGE_BAND_WIDTH):
            for y in range(h):
                grid[y][x] = band
    if "right" in sides:
        for x in range(w - EDGE_BAND_WIDTH, w):
            for y in range(h):
                grid[y][x] = band
    name = "%s_e%d" % (base.name, shape)
    return SpriteMatrix(name, _as_rows(grid), base.palette)


def _build_terrain_art() -> tuple[
    dict[int, tuple[SpriteMatrix, ...]], dict[int, tuple[SpriteMatrix, ...]]
]:
    """生成（变体表, 过渡表）。下标 0 都是原图块本身。"""
    variants: dict[int, tuple[SpriteMatrix, ...]] = {}
    edges: dict[int, tuple[SpriteMatrix, ...]] = {}
    for tile_id, decos in VARIANT_DECOR.items():
        base_sprite = SPRITES[tile_id]
        shifts = VARIANT_SHIFT.get(tile_id, ((0, 0),) * len(decos))
        bucket = [base_sprite]
        for i, deco in enumerate(decos[1:], start=1):
            bucket.append(_make_variant(base_sprite, deco, i, shifts[i]))
        variants[tile_id] = tuple(bucket)
    for tile_id, band in EDGE_BAND_CHAR.items():
        base_sprite = SPRITES[tile_id]
        bucket = [base_sprite]
        for shape in range(1, 10):
            bucket.append(_make_edge(base_sprite, band, shape))
        edges[tile_id] = tuple(bucket)
    # 防呆：所有变体 / 过渡图块都必须满铺不透明，且不含未声明的字符
    for table in (variants, edges):
        for bucket in table.values():
            for sprite in bucket:
                assert "." not in "".join(sprite.rows), sprite.name
                assert set("".join(sprite.rows)) <= set(sprite.palette), sprite.name
    return variants, edges


#: 图块 ID -> 该图块的变体（下标 0 = 原图块）
TILE_VARIANTS: dict[int, tuple[SpriteMatrix, ...]] = {}
#: 图块 ID -> 该图块的边缘过渡（下标 0 = 原图块）
TILE_EDGES: dict[int, tuple[SpriteMatrix, ...]] = {}

TILE_VARIANTS, TILE_EDGES = _build_terrain_art()

#: 变体 / 过渡图块也要烘焙，但它们**不属于 SPRITES**（TILES_BY_ID 必须保持 0..11）
TERRAIN_SPRITES: list[SpriteMatrix] = [
    s
    for table in (TILE_VARIANTS, TILE_EDGES)
    for bucket in table.values()
    for s in bucket
    if s not in SPRITES
]


def terrain_image(tile_id: int, variant: int = 0, shape: int = 0):
    """取「图块 + 变体 + 过渡形态」对应的已烘焙图片。

    shape != 0 时优先用过渡图块（过渡图块里已经含了完整地面，忽略变体）；
    shape == 0 时用变体图块。全部走 sprite_base 的幂等烘焙缓存。
    """
    from src.assets_gen import sprite_base

    if shape:
        bucket = TILE_EDGES.get(tile_id)
        if bucket is not None and 0 <= shape < len(bucket):
            return sprite_base.bake(bucket[shape])
    bucket = TILE_VARIANTS.get(tile_id)
    if bucket is not None and 0 <= variant < len(bucket):
        return sprite_base.bake(bucket[variant])
    return sprite_base.bake(TILES_BY_ID[tile_id])