"""地图图块集：11 种 16x16 图块（批 4 重绘 · 方案 D）。

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
]

#: 图块 ID（§10.2）-> SpriteMatrix
TILES_BY_ID: dict[int, SpriteMatrix] = {i: sprite for i, sprite in enumerate(SPRITES)}
